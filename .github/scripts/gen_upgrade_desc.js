#!/usr/bin/env node
// SPDX-License-Identifier: GPL-3.0-or-later
// SPDX-PackageHomePage: https://github.com/paxx12-snapmaker-u1/SnapmakerU1-Extended-Firmware
// SPDX-FileCopyrightText: Copyright (c) 2026 @paxx12
//
// Builds the `upgrade_desc` JSON `unisrv` downloads after `latest.js` offers
// a firmware build, computing the real `md5`/`sha256` of the `.bin` here
// (at build time, once) instead of hashing a ~300MB asset on every device
// request. Uploaded by CI as a release asset alongside the `.bin` it
// describes; `latest.js` just points devices at it directly.
//
// Usage: gen_upgrade_desc.js <bin-file> <release-notes-md> <name> <version> <out-json>

const fs = require("fs");
const crypto = require("crypto");

const [, , binPath, notesPath, name, version, outPath] = process.argv;

if (!binPath || !notesPath || !name || !version || !outPath) {
  console.error("usage: gen_upgrade_desc.js <bin-file> <release-notes-md> <name> <version> <out-json>");
  process.exit(1);
}

// Mirrors `extractSection()` in `docs/functions/_lib/github-releases.js` —
// pulls the bullet list out of a named `## <heading>` section of a release
// notes file, stopping at the next `##` heading.
function extractSection(body, heading) {
  const lines = body.split(/\r?\n/).map((line) => line.trim());
  const target = `## ${heading}`.toLowerCase();
  const startIndex = lines.findIndex((line) => line.toLowerCase() === target);
  if (startIndex === -1) return [];

  const items = [];
  for (let i = startIndex + 1; i < lines.length; i++) {
    const line = lines[i];
    if (/^##\s/.test(line)) break;
    const bullet = line.match(/^-\s+(.*)$/);
    if (bullet) items.push(bullet[1].trim());
  }
  return items;
}

function hashFile(path, algo) {
  return new Promise((resolve, reject) => {
    const hash = crypto.createHash(algo);
    fs.createReadStream(path)
      .on("data", (chunk) => hash.update(chunk))
      .on("end", () => resolve(hash.digest("hex")))
      .on("error", reject);
  });
}

(async () => {
  const [md5, sha256] = await Promise.all([hashFile(binPath, "md5"), hashFile(binPath, "sha256")]);
  const size = fs.statSync(binPath).size;
  const notes = fs.readFileSync(notesPath, "utf8");

  const body = {
    name,
    version,
    fullversion: version,
    size,
    md5,
    sha256,
    release_notes: {
      "en-GB": extractSection(notes, "New Features and Key Changes"),
    },
  };

  fs.writeFileSync(outPath, JSON.stringify(body, null, 2));
})();
