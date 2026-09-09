// SPDX-License-Identifier: GPL-3.0-or-later
// SPDX-PackageHomePage: https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware
// SPDX-FileCopyrightText: Copyright (c) 2026 @paxx12
// 
import {
  CACHE_SECONDS,
  NEGATIVE_CACHE_SECONDS,
  findAsset,
  findRelease,
} from "../../../_lib/github-releases.js";

const CHANNELS = ["stable", "testing", "develop"];
const BIN_ASSET_PREFIX = "U1_";
const BIN_ASSET_SUFFIX = "_upgrade.bin";
const DESC_ASSET_SUFFIX = "_upgrade_desc.json";

function jsonResponse(body, status = 200) {
  const maxAge = status < 400 ? CACHE_SECONDS : NEGATIVE_CACHE_SECONDS;
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json",
      "cache-control": `public, max-age=${maxAge}`,
    },
  });
}

// Caches every response — success or error alike — so a burst of identical
// requests (e.g. many printers on the same channel) only hits the GitHub API
// once per TTL, whichever TTL `jsonResponse()` picked for that status.
function cached(cache, waitUntil, request, response) {
  waitUntil(cache.put(request, response.clone()));
  return response;
}

// Trims the fractional-seconds/`Z` suffix GitHub timestamps carry, to match
// the plain `YYYY-MM-DDTHH:MM:SS` shape of Snapmaker's own API responses.
function toApiTimestamp(iso) {
  return iso.replace(/\.\d+Z$/, "").replace(/Z$/, "");
}

export async function onRequestGet(context) {
  const { request, env, waitUntil } = context;
  const url = new URL(request.url);
  const channel = (url.searchParams.get("channel") || "stable").toLowerCase();
  const fullversion = url.searchParams.get("fullversion") || "";
  const buildProfile = url.searchParams.get("build_profile") || "extended";
  const buildVersion = url.searchParams.get("build_version") || "";

  const cache = caches.default;
  const hit = await cache.match(request);
  if (hit) return hit;

  if (!CHANNELS.includes(channel)) {
    return cached(cache, waitUntil, request, jsonResponse(
      { code: 400, msg: `invalid channel '${channel}', expected one of: ${CHANNELS.join(", ")}`, data: null },
      400,
    ));
  }

  let release;
  try {
    release = await findRelease(channel, env);
  } catch (err) {
    const status = err.status || 502;
    return cached(cache, waitUntil, request, jsonResponse({ code: status, msg: String(err.message || err), data: null }, status));
  }

  const binAsset = findAsset(release, `${BIN_ASSET_PREFIX}${buildProfile}_`, BIN_ASSET_SUFFIX);

  if (!binAsset) {
    return cached(cache, waitUntil, request, jsonResponse(
      { code: 404, msg: `release '${release.tag_name}' has no '${buildProfile}' asset`, data: null },
      404,
    ));
  }

  // Built by `.github/scripts/gen_upgrade_desc.js` and uploaded as a release asset
  // alongside the `.bin` it describes — see that script for why (mainly:
  // real `md5`, computed once at build time instead of never).
  const descAsset = findAsset(release, `${BIN_ASSET_PREFIX}${buildProfile}_`, DESC_ASSET_SUFFIX);

  if (!descAsset) {
    return cached(cache, waitUntil, request, jsonResponse(
      { code: 404, msg: `release '${release.tag_name}' has no '${buildProfile}' upgrade descriptor`, data: null },
      404,
    ));
  }

  let newVersion = (release.name || release.tag_name).replace(/^(?:Rolling:\s*)?v/, "");

  // HACK:
  // The device already reported it's running this exact build (its
  // `BUILD_VERSION` is `<newVersion>-<git abbrev>`, so match on the
  // `newVersion` prefix) — nothing to offer, so respond the way stock
  // Snapmaker's API does when there's no pending update.
  const isCurrentVersion = buildVersion && (buildVersion === newVersion || buildVersion.startsWith(`${newVersion}-`));

  const body = {
    code: 200,
    msg: "success",
    data: {
      id: release.id,
      name: release.name || release.tag_name,
      note: descAsset.browser_download_url,
      url: binAsset.browser_download_url,
      status: 200,
      // If the device is already running this exact build, report the version it's running
      // (so it doesn't try to "upgrade" to the same build again) — otherwise report the new version.
      version: isCurrentVersion && fullversion ? fullversion : newVersion,
      createDate: toApiTimestamp(release.created_at),
      modifiedDate: toApiTimestamp(release.published_at || release.created_at),
    },
  };

  return cached(cache, waitUntil, request, jsonResponse(body));
}
