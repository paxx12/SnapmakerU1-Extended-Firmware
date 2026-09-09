export const DEFAULT_REPO = "paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware";
export const CACHE_SECONDS = 300;
// Shorter TTL for error responses (bad channel, no release, GitHub rate-limited,
// etc). Still cached at the edge — mainly to stop a burst of devices hitting a
// broken/rate-limited state from all re-querying the GitHub API — but kept
// short so a transient failure clears quickly once the underlying cause does.
export const NEGATIVE_CACHE_SECONDS = 60;

// Tag of the single rolling pre-release that `.github/workflows/develop.yaml`
// overwrites (via `ncipollo/release-action`'s `allowUpdates`) on every push
// to `develop`. Its `name` carries the real build version; the tag itself
// stays fixed so CI keeps editing the same release instead of creating one
// per push.
export const DEVELOP_RELEASE_TAG = "rolling";

async function githubApi(path, env) {
  const headers = {
    "User-Agent": "snapmakeru1-extended-firmware-worker",
    "Accept": "application/vnd.github+json"
  };
  if (env.GITHUB_TOKEN) headers.authorization = `Bearer ${env.GITHUB_TOKEN}`;

  const res = await fetch(`https://api.github.com${path}`, { headers });
  if (!res.ok) {
    const err = new Error(`GitHub API ${path} returned ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

// `stable` uses GitHub's dedicated "latest release" endpoint, which already
// excludes drafts and pre-releases. `testing` takes whatever GitHub says is
// newest overall — release or pre-release, whichever was published last —
// skipping the rolling `develop` release, which is otherwise always the
// newest since CI overwrites it on every push. `develop` fetches that
// rolling release directly by its fixed tag.
export async function findRelease(channel, env) {
  const repo = env.GITHUB_REPO || DEFAULT_REPO;

  if (channel === "stable") {
    return getReleaseById("latest", env);
  }

  if (channel === "develop") {
    return getReleaseById(`tags/${DEVELOP_RELEASE_TAG}`, env);
  }

  const releases = await githubApi(`/repos/${repo}/releases?per_page=5`, env);
  const release = releases.find((r) => r.tag_name !== DEVELOP_RELEASE_TAG);
  if (!release) {
    const err = new Error("no releases found");
    err.status = 404;
    throw err;
  }
  return release;
}

export async function getReleaseById(id, env) {
  const repo = env.GITHUB_REPO || DEFAULT_REPO;
  return githubApi(`/repos/${repo}/releases/${id}`, env);
}

export function findAsset(release, prefix, suffix) {
  return release.assets.find((asset) => asset.name.startsWith(prefix) && asset.name.endsWith(suffix));
}

// Fetches and parses a small JSON release asset (the `_upgrade_desc.json`
// descriptor). Public assets need no auth. The browser can't fetch this itself —
// GitHub asset downloads send no CORS header — which is why the Worker inlines
// the descriptor into the `latest` response. Returns null on any failure so the
// endpoint degrades gracefully to the `note` URL alone instead of erroring.
export async function fetchAssetJson(asset) {
  try {
    const res = await fetch(asset.browser_download_url, {
      headers: { "User-Agent": "snapmakeru1-extended-firmware-worker" },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (_) {
    return null;
  }
}
