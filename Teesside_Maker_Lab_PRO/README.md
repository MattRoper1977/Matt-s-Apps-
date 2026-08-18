# Teesside Cross-Curricular Maker Lab PRO v2

**Version:** 2.0.0  
**Release date:** 15 August 2026  
**Delivery:** offline, zero-dependency browser platform

## What this release is

Maker Lab PRO v2 is a coordinated Art × Design & Technology × Humanities studio platform built around eight specialist applications. It is not merely a launcher containing unrelated activities. A common professional workflow follows the learner across the suite:

**commission → understand → predict → make → test → revise → explain → moderate**

Each specialist studio remains a standalone HTML application, while the platform control rooms add whole-session orchestration, live handoffs between representations, portable project records and moderation support.

## Start points

- `index.html` — release dashboard and route chooser.
- `STUDIO_SHELL.html` — learner-facing travelling Maker Passport, live station switching and direct app-to-app relays.
- `STUDIO_DIRECTOR.html` — compatibility route that redirects older bookmarks to the three current control rooms.
- `TEACHER_STUDIO_DIRECTOR.html` — bottleneck-aware classroom routing, shared-resource forecasting, station cards and live workshop pulse.
- `PORTFOLIO_MODERATION_HUB.html` — cross-app evidence review, authorship audit, blind sampling, conflict detection and dossier export.
- `RELEASE_SELF_CHECK.html` — local SHA-256 package integrity check after extraction.

## The eight specialist studios

1. **Anamorphic Shadow Rig Studio** — three-plane armature design, tolerance storm, sensitivity-ranked node revision and physical shadow-photo comparison.
2. **Ironopolis Token Foundry Studio** — two-sided fictional token design, topology X-ray, safe abstract fill/release diagnostics and registration testing.
3. **Tees Smuggling & Hydrographic Rig** — limited soundings, changing-tide route planning, Revenue-cutter pressure, route autopsy and hidden-channel export.
4. **Cyber-Industrial Architectural Relief Lab** — raking-light theatre, viewing-distance test, mould-release X-ray, virtual patina watershed and exhibition interpretation.
5. **Dorman Long Steelplate & Rivet CAM** — editable classroom geometry, layout constraints, punch-route optimisation, tolerance analysis and tiled true-scale pattern output.
6. **Tees Tidal Contour Relief & Hydro-Board** — active survey design, interpolated seabed, hidden-truth error map, contour nesting and conceptual cam synthesis.
7. **Brutalist Collagraph Matrix Engine** — digital matrix construction, proof modelling, edition-wear memory, photographed proof comparison and sensory station planning.
8. **Truck System “Tommy Shop” Economy Lab** — 12-week restricted-payment counterfactual, prediction-locked shocks, reform comparison, source board and perspective tribunal.

## Original professional systems

### Audited Trials

Learners commit to an expected direction, estimate, confidence and reason before a diagnostic result is revealed. The record retains the prediction, the test result, the numerical or categorical error, and the learner’s subsequent explanation. This assesses calibration and revision rather than rewarding a lucky final answer.

### Design Replay

A baseline and Design A can be frozen before revision. The application retains the state, measures and visual preview so the pupil can compare the current artefact with the earlier decision and explain the causal effect of a change.

### Maker Passport

The Studio Shell carries learner alias, commission, essential question, pathway, mission code and source status between stations. It can request live state from each application and export a portable `.makerstudio` record without a server.

### Representation Relays

Three direct handoffs convert one project representation into another:

- Token Foundry → Economy Lab;
- Hydro-Board → Smuggling Rig;
- Architectural Relief → Collagraph Engine.

Every relay is labelled as a **model transformation**, not historical proof or automatic equivalence.

### Teacher Orchestration

The Teacher Studio Director generates rotations that consider printer, lamp, magnetic-material and mess-bay constraints. It also balances route profiles such as calm start, low mess, movement first and low fine-motor demand while keeping the same high-status artefact across BUILD, GROW and LAUNCH.

### Moderation without automatic grading

The Portfolio Moderation Hub separates pupil voice, prediction, observation, test, revision, humanities claim and teacher verification. It highlights missing or duplicated evidence, supports blinded aliases and creates a balanced moderation sample. Its readiness indicator is an organisational prompt, not an attainment grade.

## Portable formats

- `.makerlab` — one specialist-studio project record (`MBM_MAKER_PRO_V2`).
- `.makerstudio` — travelling cross-studio passport and shell record.
- `.makerclass` — Teacher Studio Director session plan and rotation state.
- `.makerhub` — moderation-hub workspace and imported project index.
- `MBM_TOKEN_TRANSFER_V1` — explicitly fictional token handoff from App 02 to App 08.

These files are JSON using different filename extensions so staff can identify their purpose. Exported files, rather than browser storage, are the reliable transfer and backup mechanism.

## Installation and operation

1. Extract the complete release folder without renaming or separating its contents.
2. Open `RELEASE_SELF_CHECK.html` and choose the extracted folder.
3. Open `index.html` and select the appropriate route.
4. Prefer learner aliases and a reproducible mission code.
5. Export the relevant portable record before moving device, browser profile or workstation.

No package manager, account, analytics service, font download, CDN or internet connection is required at runtime.

## Safety, truth and assessment boundary

The suite models, visualises and documents decisions. It is not a process authorisation, risk assessment, engineering specification, navigation chart, historical proof, material safety data sheet or qualification decision.

Hot-metal casting, powered machinery and reactive chemical patination are outside the operational scope. The software contains abstract or virtual diagnostics instead of melt settings, quench instructions, oxidiser recipes, powder specifications or load-rated mechanism data. Steelplate ratios are classroom geometry heuristics, not structural-design rules.

See `SAFETY_TRUTH_AND_PROFESSIONAL_BOUNDARY.md` before planning physical work.

## Privacy

No information is transmitted by the suite. Local browser storage and user-exported files are used. Photographs may contain personal or contextual information, so staff should review images, prefer aliases and apply their setting’s normal access, retention and deletion controls.

See `DATA_PRIVACY_AND_RETENTION.md`.

## Verification

- `VERIFICATION_REPORT.md` — release QA method and results.
- `qa/STATIC_CHECK_RESULTS.json` — machine-readable static audit.
- `qa/PROFESSIONAL_QA_RESULTS.json` — machine-readable desktop interaction results across all control rooms and specialist engines.
- `qa/MOBILE_QA_RESULTS.json` — machine-readable mobile-layout boot results.
- `qa/PORTABLE_EXPORT_QA_RESULTS.json` — portable-record export and round-trip import results.
- `qa/SUITE_PRO_V2_MONTAGE.jpg` — visual QA overview.
- `RELEASE_MANIFEST.json` and `SHA256SUMS.txt` — release file inventory and hashes.

The browser tests validate boot and representative interactions. They do not certify every possible classroom sequence or any physical process.
