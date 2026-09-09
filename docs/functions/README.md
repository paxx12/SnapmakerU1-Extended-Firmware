# Cloudflare Pages Functions

Server-side endpoints for `snapmakeru1-extended-firmware.pages.dev`, deployed
by `.github/workflows/cloudflare_pages.yaml`. Wrangler looks for `functions/`
next to its own working directory, not inside the deployed static output —
so the deploy step runs with `workingDirectory: docs` and deploys `../_site`,
letting this `docs/functions/` directory ship alongside it.

## `GET /api/device/firmware/latest`

Consumed by the `firmware-imposter` `LD_PRELOAD` shim
(`overlays/firmware-extended/38-feature-upgrade-firmware/`), which rewrites
`unisrv`'s real `.../api/device/firmware/latest` check to this same path on
our own host when `components.upgrade` in `extended2.cfg` is `stable`,
`testing`, or `develop` (`none` stays on stock). `?channel=stable` resolves
the latest GitHub release; `?channel=testing` resolves the latest of either
a release or pre-release, whichever is newer; `?channel=develop` resolves
the rolling `rolling`-tagged pre-release that
`.github/workflows/develop.yaml` overwrites (via `ncipollo/release-action`'s
`allowUpdates`) on every push to `develop`, so it always tracks the tip of
that branch ahead of any tag. See [`firmware_upgrade.md`](../firmware_upgrade.md)
for the user-facing description of the channels.

`develop`'s release keeps a fixed tag (`rolling`, named distinctly from the
`develop` branch to avoid the ambiguous-ref footgun of a tag and branch
sharing a name) so CI can keep editing the same release, so `release.name`
(not `tag_name`) is what carries the real build version — both endpoints
below read `release.name || release.tag_name` accordingly. Its `name` is
prefixed `Rolling: ` (e.g. `Rolling: v1.4.1-paxx12-20-gabcdef1`) to
distinguish it from `stable`/`testing` release names in the GitHub UI, so
both endpoints strip an optional leading `Rolling: ` along with the `v`
when deriving `fullversion`. `findRelease()` in `_lib/github-releases.js`
also excludes that tag from the `testing` lookup, otherwise the
constantly-refreshed `develop` release would always look like the newest
release-or-pre-release overall. Each push also force-moves the `rolling`
git tag itself to the new build's commit before the release step runs,
since GitHub only positions a release's target from a tag's current
commit — updating just the release (not the tag) would leave the tag,
and therefore the release, anchored to a stale commit.
Its body is generated each push from [`RELEASE.dev.md`](../../RELEASE.dev.md)
(the rolling-build notice, plus a `## New Features and Key Changes` section
the workflow fills in with every PR merged into `develop` that isn't in
`main` yet), before `.github/scripts/gen_upgrade_desc.js` reads that
section into the `upgrade_desc.json` asset described below.

`?build_profile=` (`extended` or `extended-afc`, defaulting to `extended`)
picks which release asset to offer — `findAsset()` in
`_lib/github-releases.js` matches on both the `U1_extended_`/`U1_extended-afc_`
filename prefix CI gives each profile and the shared `_upgrade.bin` suffix.
`?build_version=` is the device's own `/etc/BUILD_VERSION`
(`<fullversion>-<git abbrev>`, e.g. `1.4.1-paxx12-20-gabcdef1`); if it
already starts with the resolved release's version, the device is already
running this exact build and the endpoint responds with `data: null`
instead of an update descriptor (mirroring how stock Snapmaker's API
reports "no update available").

Mirrors Snapmaker's `ApiDeviceFirmwareLatest` shape (minus `authDevices`,
which is unrelated to this flow):

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": 342972029,
    "name": "v1.4.1-paxx12-20",
    "note": "https://github.com/.../U1_extended_1.4.1-paxx12-20_upgrade_desc.json",
    "url": "https://github.com/.../U1_extended_1.4.1-paxx12-20_upgrade.bin",
    "status": 200,
    "version": "1.4.1-paxx12-20",
    "createDate": "2026-06-21T20:57:51",
    "modifiedDate": "2026-06-23T15:21:32"
  }
}
```

When the device is already on this build, `data` is `null` instead (see
above) — no `note`/`url` to follow.

`note` and `url` both point straight at GitHub release assets rather than
anything on this host — `findAsset()` in `_lib/github-releases.js` matches
`url` on the `U1_extended_`/`U1_extended-afc_` filename prefix CI gives each
profile plus the shared `_upgrade.bin` suffix, and `note` the same prefix
plus `_upgrade_desc.json`. `unisrv` fetches both with its own `curl` handle
(not intercepted by the shim), so it still attaches its Snapmaker
`Authorization: Bearer` header — modern libcurl (device ships 8.6.0) strips
that header by default on any cross-host redirect, so it never reaches
GitHub.

On failure, the status mirrors whatever GitHub returned (e.g. `403` on
rate-limit), falling back to `502` for network errors.

## The `upgrade_desc` asset

The `note` URL above. Each CI workflow that publishes a release
(`.github/workflows/develop.yaml`, `pre_release.yaml`) runs
`.github/scripts/gen_upgrade_desc.js` against the `.bin` it just built
and uploads the result as a release asset alongside it, named the same
as the `.bin` but ending `_upgrade_desc.json` instead of `_upgrade.bin`:

```json
{
  "name": "v1.4.1-paxx12-20",
  "version": "1.4.1-paxx12-20",
  "fullversion": "1.4.1-paxx12-20",
  "size": 290327624,
  "md5": "8f14e45fceea167a5a36dedd4bea2543",
  "sha256": "8ddb1d6dc889f8c11d6ac708dd4858439b13e830d3bf93064e857433a70ff3c3",
  "release_notes": { "en-GB": ["Quick Actions panel...", "..."] }
}
```

`md5`/`sha256`/`size` are computed straight from the built `.bin`, once, in
CI — `unisrv` verifies the downloaded firmware's MD5 against this field and
fails the update on a mismatch, so unlike the dummy value this endpoint
used to serve, it must be real. `release_notes.en-GB` is scraped from that
workflow's own release-notes file (`RELEASE.dev.md` for `develop`,
`RELEASE.md` for `stable`/`testing`) at build time, via the same
`## New Features and Key Changes` bullet-list parsing `extractSection()`
used to do in `_lib/github-releases.js`. This means it's frozen at whatever
that file said when CI ran: `develop`'s notes are always fully
CI-generated already, so this is a non-issue there, but `stable`/`testing`
release notes are normally hand-edited in the GitHub UI on the draft
release *after* `pre_release.yaml` runs — those edits are **not** reflected
in `upgrade_desc.json`, which keeps whatever `RELEASE.md` said at build time
(usually the literal `- TBD` placeholder) unless something re-generates and
re-uploads the asset afterwards.

## Caching & config

`latest.js` caches every response at Cloudflare's edge (Cache API), success
or error alike, keyed on the full request URL (so per `channel`).
Successful responses use `CACHE_SECONDS` (5 min); errors — bad input, no
matching release, GitHub rate-limited or unreachable — use the shorter
`NEGATIVE_CACHE_SECONDS` (1 min, both in `_lib/github-releases.js`), so a
burst of devices hitting a broken or rate-limited state only causes one
GitHub API call per TTL instead of one per request.

| Env var        | Required | Purpose                                                                    |
|----------------|----------|-------------------------------------------------------------------------------|
| `GITHUB_REPO`  | No       | `owner/repo`; defaults to `paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware`  |
| `GITHUB_TOKEN` | No       | Lifts GitHub's 60 req/hour unauthenticated rate limit                         |

Set both in the Cloudflare Pages dashboard (Settings → Environment
variables), not in this repo.
