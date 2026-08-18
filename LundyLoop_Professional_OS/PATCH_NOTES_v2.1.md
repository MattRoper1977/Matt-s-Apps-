# LundyLoop Professional OS — v2.1 patch notes (2026-08-18)

Applied identically to `LundyLoop_Professional_OS.html` (root) and `LundyLoop_Professional_OS/LundyLoop_PRO_Participation_Operating_System.html` (suite). Every replacement matched exactly once; inline JS syntax-checked; behaviours proven in a DOM harness (0 page errors).

| # | Defect in v2.0 | Patch | Proof |
|---|---|---|---|
| P1 | PBKDF2 250,000 iterations; decrypt hard-coded to 250,000 while writing `iterations` into every pack header | `PBKDF2_ITERS=600000` (OWASP); `deriveBackupKey(...,iters)`; decrypt reads `Number(env.iterations)||250000` | Node WebCrypto: 600k round-trip PASS · legacy 250k pack PASS · headerless→250k PASS · wrong passphrase rejected PASS |
| P2 | `csvCell` escaped only `" , \n` — leading `= + - @ \t \r` reached Excel as formulas (`audience_role` is free text) | Leading formula characters prefixed with `'` and force-quoted; bare `\r` now quoted | 8 vectors PASS |
| P3 | `.presentation .sensitive:hover,:focus-within{filter:none}` — projector blur un-blurred on mouse-over | Rule removed; `pointer-events:none` added | computed style `blur(7px)` / `none` |
| P4 | `appendEvent(...,'Pupil / scribe')` hard-coded; adult alone could create a pupil-attributed review the hash chain then sealed; `CLOSED ⇐ review.reviewedAt` | New "Who is recording this review?" select (pupil-self / pupil-scribe / staff-proxy). Staff-proxy requires a warning modal, logs `REVIEW_RECORDED_BY_STAFF` with `pupilPresent:false`, and **does not close the loop** (`stageOf` returns REVIEW_DUE). `recordedBy` added to case schema + normaliser | stageOf legacy/proxy/scribe = CLOSED / REVIEW_DUE / CLOSED PASS |
| P5 | No pupil-mode lock — nav showed all seven workspaces from the "pupil-facing" kiosk | Header **Pupil mode** button → confirm modal → body `.pupilmode`: only Pupil Capture nav visible, top actions hidden except Shield, nav clicks intercepted, survives reload via `sessionStorage llproPupilMode`, exit = 1.5 s press-and-hold (keyboard: confirm). Framed as a speed bump, not security | DOM: 6/7 nav hidden, dashboard click stays on capture, restored after exit |
| P6 | `importBackup` silently dropped audio when IndexedDB unavailable | Warn toast naming the clip count not restored | code path |
| P7 | "Redacted CSV … without exact pupil words or aliases" oversold anonymity | Toast now says pseudonymised; case IDs re-link | text |
| P8 | No visible version | Sub-brand line shows `· v2.1` | text |

## Deliberately NOT changed (needs Matt's ruling, not a patch)
- **"Participation debt"** remains the dashboard headline metric — a fourth sense of "Influence" in the estate vs the ratified "observable change in the adult's next teaching move". Relabel candidate.
- **Closure theory.** Even with P4, a pupil-recorded review is the closing act for every pathway. The estate's ratified position (LL-I) is pathway-dependent (BUILD = adult receipt; GROW/LAUNCH = pupil-owned, no adult signatory). B2 should land before TAs see this alongside `R_Gate_Calibration_Game`.
- Two near-identical flagship copies (root + suite) are retained because the deploy contract and verifiers expect both; same storage keys, so they share data on one origin.

## v2.1.1 (r4, 2026-08-18) — P9, prompted by the r3 PATCH_TRUTH_FAILED stop
| # | Defect | Patch | Proof |
|---|---|---|---|
| P9 | Two `'Pupil / scribe'` residuals survived P4: the live `VOICE_CAPTURED` event in the capture save path, and the fictional demo-data seeder. r3's gate expected 0 without having been run | Capture path derives the actor from the pupil's own chosen route (`Scribed exact words` → "Pupil via scribe (pupil present)", else "Pupil") and records `scribed` + `pupilPresent:true` in the event detail. Demo seeder relabelled "Pupil via scribe (demo data)" with `demo:true`. Sub-brand → v2.1.1 | `run_patch_truth_gate.sh` executed: 22/22 + VERSION OK; inline JS syntax OK |

**Root cause of the r3 stop, owned:** the r3 gate's `expect 0` for `'Pupil / scribe'` was written from the patch intent, not from a post-patch grep. The executor was right to stop rather than reason it green. r4 ships the gate as a script and records its execution.
