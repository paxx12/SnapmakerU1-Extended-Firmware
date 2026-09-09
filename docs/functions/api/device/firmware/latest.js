// SPDX-License-Identifier: GPL-3.0-or-later
// SPDX-PackageHomePage: https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware
// SPDX-FileCopyrightText: Copyright (c) 2026 @paxx12
// 
import {
  CACHE_SECONDS,
  NEGATIVE_CACHE_SECONDS,
  fetchAssetJson,
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
      // The firmware-config web page fetches this cross-origin from the printer,
      // so the browser needs CORS to read the body. Safe to be permissive: this
      // is a public, read-only lookup of published release metadata.
      "access-control-allow-origin": "*",
    },
  });
}

// CORS preflight. A plain GET with no custom headers won't trigger one, but a
// stricter client (or one that adds headers) will — answer it cheaply.
export function onRequestOptions() {
  return new Response(null, {
    status: 204,
    headers: {
      "access-control-allow-origin": "*",
      "access-control-allow-methods": "GET, OPTIONS",
      "access-control-allow-headers": "*",
      "access-control-max-age": "86400",
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

  // Inline the descriptor so the browser gets the checksum + release notes in
  // this one CORS-enabled call — it can't fetch `note` itself (GitHub asset
  // downloads carry no CORS header). `note` is kept unchanged for the native
  // `unisrv` path; the extra fields are additive, so any client that ignores
  // unknown keys (unisrv included) is unaffected. Falls back to note-only.
  const descriptor = await fetchAssetJson(descAsset);

  const body = {
    code: 200,
    msg: "success",
    data: {
      id: release.id,
      name: release.name || release.tag_name,
      note: descAsset.browser_download_url,
      url: binAsset.browser_download_url,
      status: 200,
      version: newVersion,
      createDate: toApiTimestamp(release.created_at),
      modifiedDate: toApiTimestamp(release.published_at || release.created_at),
      ...(descriptor && {
        md5: descriptor.md5,
        sha256: descriptor.sha256,
        size: descriptor.size,
        release_notes: descriptor.release_notes,
      }),
    },
  };

  return cached(cache, waitUntil, request, jsonResponse(body));
}
