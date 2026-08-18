# Teesside Cross-Curricular Maker Lab PRO — v2.1.0 patch notes (2026-08-18)

Applied to the v2.0.0 release (SHA256SUMS 50/50 verified before patching). Every replacement matched exactly once; all inline JS syntax-checked after.

| # | Defect in v2.0.0 | Patch | Proof |
|---|---|---|---|
| M1 | `STUDIO_SHELL.html` sandboxed studios **without `allow-same-origin`** → opaque origin → `localStorage` throws inside the frame → every studio opened via the README's own primary route (`STUDIO_SHELL.html?app=N`) shows a permanent "browser storage unavailable" chip; direct-open and shell-open saves land in two stores that never meet | `allow-same-origin` added to the frame sandbox. First-party same-origin files; the sandbox was never a boundary, only a self-inflicted storage failure | grep: `sandbox="allow-same-origin …"` ×1; acceptance test = shell route autosave chip reads "saved HH:MM" |
| M2 | Shell `message` receiver checked only `m.channel` — any window that could post into it could overwrite a Maker Passport (incl. `evidence`/`timeline` the Moderation Hub treats as authored evidence) | Receiver now rejects any message whose `e.source` is not `#appFrame.contentWindow` | grep: `e.source!==fr.contentWindow` ×1 |
| M3 | 0/15 files honoured `prefers-reduced-motion` | Reduced-motion token block inserted before the first `</style>` in all 15 HTML files | grep 15/15 |
| M4 | (v2.0.0 first issue shipped without `STUDIO_DIRECTOR.html`; this re-issue includes a 2 KB "Director moved" router card) | Kept as shipped — its four links (index / Shell / Teacher Director / Hub) all resolve | link check |
| M5 | Patching changes bytes → `RELEASE_SELF_CHECK.html` EXPECTED table and `SHA256SUMS.txt` would go red | Both regenerated from the patched files; `RELEASE_MANIFEST.json` version 2.1.0, `VERSION.txt` 2.1.0 | self-check EXPECTED = fresh sha256 |

## Deliberately NOT changed — for Matt, not a patch
- **Reading demand of the learner-facing panel copy is far above BUILD/GROW.** Measured Flesch–Kincaid on `<p>`/`<h2>` prose only: studios 15.5–18.9 (whole-panel text 17–22). Same class as the AP Arcade finding. A plain-language pass on the eight studios' panel copy is a content job needing Matt's eye, not a byte patch.
- Estate integration (Made by Matt splash, back-link, hud.js) is deploy-time work per the master prompt, not a patch to the release.
- The two flagship-style routes into a studio (direct file vs Shell) still exist; M1 makes them share the same origin so both now read/write the same `MBM_MAKER_PRO_V2_<app>` key. Nothing else about the storage model changed.

## r2 (2026-08-18, same day) — M5 corrected after the first real-browser run
r1's `RELEASE_SELF_CHECK.html` EXPECTED table was regenerated against the *source-release* file list (17 unshipped `qa/` artefacts listed, shipped `PATCH_NOTES_v2.1.md` absent) — 18 red in the executor's browser although every shipped byte matched. r2 regenerates EXPECTED against the **shipped payload set** (33 entries) and `SHA256SUMS.txt` likewise. No runtime file changed; the acceptance test, forged-postMessage control and reduced-motion results from the r1 run are expected to reproduce byte-for-byte.
