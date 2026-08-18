# Professional v2 upgrade architecture

## Design proposition

PRO v2 changes the suite from eight useful prototypes into a coordinated professional learning system. The central design problem was not visual polish; it was how to preserve a learner’s reasoning across digital design, physical making, testing, revision, historical interpretation and moderation.

The platform therefore has three layers:

1. **Specialist studios** — eight independent, offline tools with subject-specific engines.
2. **Studio platform** — common project schema, Maker Passport, mission codes and representation relays.
3. **Professional control rooms** — commission planning, resource-aware orchestration and moderation.

## Shared enquiry architecture

Every app uses the same six-stage spine:

**Understand → Predict → Make → Test → Revise → Explain**

The common engine provides:

- BUILD / GROW / LAUNCH calibration without changing the status of the final artefact;
- deterministic challenge seeding from a mission code;
- prediction lock before diagnostic reveal;
- confidence calibration rather than answer-only scoring;
- baseline and Design A checkpoints;
- A/B state, metric and visual replay;
- undo, redo and decision timeline;
- local evidence capture, including optional visual snapshots;
- a four-level source-status ladder;
- `.makerlab` import/export and printable dossier;
- local autosave, focus mode, teacher lens and IWB controls;
- a postMessage bridge for the Studio Shell.

## Audited Trials

An Audited Trial is a structured causal record:

1. the learner identifies the variable or design decision under test;
2. the learner locks an expected direction, estimate, confidence and reason;
3. the result remains concealed until commitment;
4. the app records the diagnostic outcome;
5. the learner compares expectation with evidence;
6. the revision is frozen and explained.

This creates evidence of judgement under uncertainty. It does not infer a fixed ability label from one trial.

## Maker Passport and shell protocol

`STUDIO_SHELL.html` embeds the current specialist app and communicates through the channel:

`MBM_MAKER_PRO_SHELL_V2`

The shell can:

- hydrate learner alias, commission, question, mission code, pathway and source status;
- request the current project state;
- broadcast the current enquiry stage;
- open a studio record;
- track a whole-session evidence constellation;
- export/import `.makerstudio` records;
- perform explicit representation handoffs.

The iframe is sandboxed for scripts, forms, downloads, modals and pointer interaction without granting same-origin access.

## Representation relays

A professional workflow often transforms the same idea between representations. PRO v2 makes these transformations explicit:

### Token → Economy

A fictional token’s visual identity and denomination are passed from the Foundry into the Economy Lab. The recipient treats it as a designed artefact inside a counterfactual model, never as evidence that a named historical company used it.

### Seabed survey → Navigation field

The Hydro-Board’s model seabed is resampled into the Smuggling Rig’s route grid. The transferred field is visibly labelled synthetic so pupils can investigate how survey design affects route confidence without confusing generated data with an authentic 1780 chart.

### Relief composition → Print matrix

Architectural relief components are translated into collagraph material categories. This supports discussion of what survives or changes when mass, depth and light are transformed into printable texture.

## Control rooms

### Compatibility director route

`STUDIO_DIRECTOR.html` preserves older links and directs users to the dedicated Studio Shell, Teacher Studio Director and Portfolio Moderation Hub. Separating these responsibilities keeps learner operation, live logistics and moderation from competing on one screen.

### Teacher Studio Director

Plans groups and rounds against shared resources. It forecasts printer, lamp and mess-bay collisions, supports magnetic-material and cold-only constraints, balances route profiles, creates station cards and runs a live workshop pulse.

### Portfolio Moderation Hub

Groups project records by learner and mission, supports blind aliases, distinguishes authorship signals, audits calibration and revision, detects version conflicts and generates a balanced moderation sample. It organises evidence but does not grade it.

## Specialist originality

1. **Shadow Rig** — local physical-photo comparator, tolerance storm, highest-impact-node diagnosis and sensitivity-ranked assembly order.
2. **Token Foundry** — two-sided registration, topology X-ray, safe abstract flow/release theatre and downstream economy handoff.
3. **Smuggling Rig** — limited reconnaissance, tide-window navigation, cutter behaviour, uncertainty-aware route autopsy and synthetic seabed receipt.
4. **Architectural Relief** — raking-light legibility, distance testing, inverse-mould complexity, release X-ray, virtual weathering and print-matrix relay.
5. **Steelplate CAM** — geometric constraint diagnosis, punch-route optimisation, repeated tolerance trials and calibrated tiled 1:1 output.
6. **Hydro-Board** — active sounding selection, uncertainty-guided probing, interpolated surface, hidden truth/error reveal, layer nesting and conceptual cam synthesis.
7. **Collagraph Engine** — material matrix, proof heatmap, cumulative edition wear, photographed proof-region comparison and sensory/mess planning.
8. **Economy Lab** — 12-week counterfactual ledger, concealed shock deck, reform comparison, source board, multi-perspective tribunal and token receipt.

## Technical boundary

All production files are standalone HTML, CSS and JavaScript. No runtime network request, external library, service worker, account system or backend is required. The portable file formats are intentionally readable JSON rather than proprietary binary packages.
