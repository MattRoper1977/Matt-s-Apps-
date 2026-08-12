# Stealth Science v4 — release documents, as shipped

These four files certify the release **as it arrived**, before the estate
splash was installed. Every sha256 inside them describes the PRE-SPLASH bytes:

| file | pre-splash sha256 (these docs) | published sha256 |
|---|---|---|
| orbit-vector-diagnostic.html | `82d13671bde72694…` | see repo — rebuilt by `tools/stealth_publish.py` |
| enzyme-reactor-overdrive.html | `b5283f79024bec24…` | ditto |
| mbm-master-hub.html | `33166bde19714405…` | ditto |

Do not quote these hashes for the published files. `tools/stealth_publish.py
--prove` is the authority on the published bytes.

Two files the release names are **absent from what Matt holds** and were
neither reconstructed nor blocked on:

- `mbm-legacy-adapter.js` (QA_RESULTS pins `1aa3a458d5d57ef5…`) — the hub's
  download link to it was ruled dropped 2026-08-12; the prose now says
  "not included in this release".
- `CHECKSUMS.sha256` — README.md line 15 advertises it; it never arrived.

`THIRD_PARTY_NOTICES.md` (Kazuhiko Arase QR licence) is kept reachable here,
and the in-file attribution comments survived the splash install untouched in
both files that carry them (ORBIT and ENZYME generate QR and embed the licence
comment; the hub only *reads* QR via the browser's native BarcodeDetector and
never carried the library or the comment — 0 hits pristine, 0 published).
