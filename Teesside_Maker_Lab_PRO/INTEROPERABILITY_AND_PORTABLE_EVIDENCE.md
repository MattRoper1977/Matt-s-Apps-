# Interoperability and portable evidence

## Why portability matters

Browser storage is useful for resuming work on one device but is not a dependable cross-device evidence system. PRO v2 therefore treats exported project files as the authoritative portable record. All formats are local JSON with human-readable field names.

## `.makerlab` — specialist project

Format identifier: `MBM_MAKER_PRO_V2`

A project contains:

- application identity and format version;
- learner alias, commission, essential question, pathway and mission code;
- source status and source note;
- locked predictions and calibration history;
- baseline and Design A checkpoints;
- decision timeline and evidence entries;
- complete app-specific design state;
- optional local visual snapshots.

The originating app can re-import its project. The directors and moderation hub can inspect cross-app fields without executing the project file.

## `.makerstudio` — travelling passport

Format identifier: `MBM_MAKER_STUDIO_V2`

The Studio Shell exports common passport fields, station snapshots, relay history, whole-session evidence constellation, timing and enquiry-stage information. It is designed to resume a multi-station commission on another browser or device.

## `.makerclass` — session plan

Format identifier: `MBM_MAKER_CLASS_V2`

The Teacher Studio Director exports group definitions, route profiles, selected stations, resource constraints, generated rotation, timing and live-session state.

## `.makerhub` — moderation workspace

Format identifier: `MBM_MAKER_HUB_V2`

The Portfolio Moderation Hub exports its imported record index, blind-alias state, filters, sampling choices and conflict ledger. The underlying `.makerlab` records should still be retained separately as primary evidence files.

## Mission-code reproducibility

The same mission code is hashed into a deterministic seed. This supports paired comparison, whole-class challenges, repeat teacher modelling and fair re-runs without storing pupil data on a server. Reproducibility applies to the teaching model; it does not imply that a generated historical or physical scenario is authentic.

## Shell messaging

Apps and `STUDIO_SHELL.html` communicate over `postMessage` using:

`MBM_MAKER_PRO_SHELL_V2`

Supported message classes include readiness, common-field hydration, state request/synchronisation, stage broadcast, studio-record opening, relay evidence and direct handoff application.

Messages are used only inside the opened local page and iframe. No information is sent to an online endpoint.

## Direct representation handoffs

### `MBM_TOKEN_TRANSFER_V1`

App 02 sends a fictional token identity and design summary to App 08. App 08 retains the label that the token is a designed artefact inside a synthetic economic scenario, not historical proof.

### `hydro_survey`

App 06 passes a model truth grid to App 03. The receiver resamples the 20 × 14 seabed into its 26 × 15 navigation field and marks the environment as transferred synthetic data.

### `relief_matrix`

App 04 passes architectural relief components to App 07. Components are translated into print-planning categories, for example block → card, rib → corrugated texture, bolt → washer and void → cut-away.

A handoff is a documented transformation. It is not a guarantee that both models share identical scales, material behaviour or historical meaning.

## File handling recommendations

- Use aliases rather than full pupil names.
- Keep one read-only original export before editing or merging records.
- Use a naming pattern such as `River_Group_A_Shadow_Rig_2026-09-14.makerlab`.
- Keep project files and photographs within the setting’s approved storage.
- Do not email unreviewed evidence files containing photographs or identifying contextual information.
- Use `RELEASE_SELF_CHECK.html` only to verify the release package, not pupil project files.

## Compatibility boundary

The v2 tools validate their own format identifiers and required structures. They do not promise forward compatibility with future format versions. Retain the release folder used to create a project alongside archived project files where long-term reopening is required.
