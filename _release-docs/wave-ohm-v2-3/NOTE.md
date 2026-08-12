# WAVE & OHM v2.3 — release archive, and the pristine sources the builds read

Everything the v2.3 release shipped, at the bytes it shipped. Every hash in
these documents (`PACKAGE-SHA256-V2-3.txt`, `QA-RESULTS-V2-3.json`) describes
the PRE-SPLASH bytes; the published files are rebuilt from the pristine copies
here by `tools/wave_ohm_publish.py`, which is the authority on published hashes.

**Provenance of the bridge.** `mbm-master-hub-bridge-v2-3.js` was absent from
the release archive. It was re-extracted byte-exact from script block 0 of
`mbm-master-hub-integration-preview-v2-3.html` (strip + trailing newline) and
its sha256 `c3fb4dea1e1dd3b98114fcff97bd2b5a3839d48c575c7ecf0a98954b8cfb416e`
matches the manifest's pin. The build refuses to install any bridge bytes that
do not hash to that value.

**Recorded absences** (never reconstructed, never blocked on):
`README-V2-3.md` (manifest pins `9e1c5b76…`) and `STATIC-QA-V2-3.json`
(manifest pins `c643db63…`) are missing from everything Matt holds.

**Not published, archived here:**
- `made-by-matt-wave-ohm-offline-lesson-v2-3.html` — the core deck, 99.85%
  identical to the complete deck, which supersedes it.
- `mbm-master-hub-integration-preview-v2-3.html` — a dev demo shell, not an
  estate page.
