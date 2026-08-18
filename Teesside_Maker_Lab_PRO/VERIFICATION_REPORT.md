# Verification report

**Release:** Teesside Cross-Curricular Maker Lab PRO v2.0.0  
**Verification date:** 15 August 2026  
**Outcome:** **PASS**

## Scope

The release was checked as a static, zero-dependency browser platform containing eight standalone specialist applications, a suite portal, Studio Shell, Teacher Studio Director, Portfolio Moderation Hub and compatibility route.

The QA does not authorise or certify any physical workshop process. It verifies the software package and representative digital workflows only.

## Static verification

The final static audit checks:

- inline JavaScript syntax using `node --check`;
- missing local links and package files;
- duplicate HTML IDs;
- zero-byte files;
- external script, stylesheet and media dependencies;
- runtime network primitives such as `fetch`, `XMLHttpRequest`, `WebSocket` and `EventSource`;
- required portable-format and platform files.

Result: **PASS**. The eight specialist apps and platform pages have no external runtime dependency or network call.

Machine-readable result: `qa/STATIC_CHECK_RESULTS.json`.

## Browser interaction verification

A managed Chromium harness loaded the production HTML and exercised representative workflows.

### Specialist apps

All **8/8** applications passed:

- boot and application API initialisation;
- Studio Record drawer;
- commission and source-boundary capture;
- baseline and Design A checkpointing;
- prediction lock;
- a specialist diagnostic or mission run;
- calibration or tested-state creation;
- A/B replay;
- pupil-voice evidence capture;
- project-state retention;
- screenshot capture;
- zero uncaught browser errors and zero console warnings.

Representative specialist checks included the Shadow Rig tolerance storm, Token Foundry virtual cast, Smuggling Rig route run, Relief Lab weathering reveal, Steelplate tolerance trial, Hydro-Board hidden-seabed reveal, Collagraph proof pull and Economy Lab concealed shock.

### Platform control rooms

All control rooms passed:

- **Suite portal:** eight-engine catalogue and current platform routes.
- **Studio Shell:** eight-engine rail, Maker Passport synchronisation, evidence constellation and cross-app constraint relay.
- **Teacher Studio Director:** resource-aware rotation, station cards and live workshop pulse.
- **Portfolio Moderation Hub:** `.makerlab` import, sampling engine and dossier assembly.
- **Compatibility route:** links older bookmarks to the current three control rooms.

Machine-readable result: `qa/PROFESSIONAL_QA_RESULTS.json`.


## Portable record verification

All four professional record types were exported through their production controls, parsed as JSON, checked for the explicit v2 format identifier and re-imported into the originating control:

- `.makerlab` — `MBM_MAKER_PRO_V2`;
- `.makerstudio` — `MBM_MAKER_STUDIO_V2`;
- `.makerclass` — `MBM_MAKER_CLASS_V2`;
- `.makerhub` — `MBM_MAKER_HUB_V2`.

Result: **4/4 PASS**, including round-trip import and zero browser errors or warnings.

Machine-readable result: `qa/PORTABLE_EXPORT_QA_RESULTS.json`.

## Responsive verification

The suite portal, all three control rooms and all eight specialist apps were tested at a 412 × 915 mobile viewport.

Result: **12/12 PASS**, with zero page-level horizontal overflow, uncaught errors or console warnings. Canvas workspaces may intentionally scroll inside their own bounded panel where required.

Machine-readable result: `qa/MOBILE_QA_RESULTS.json`.

## Visual verification

Desktop captures are retained for the portal, control rooms and every specialist engine. The combined overview is:

- `qa/SUITE_PRO_V2_MONTAGE.jpg`
- `qa/SUITE_VISUAL_QA_MONTAGE.jpg`

Representative mobile captures are retained for the portal and App 01.

## Test-environment note

The managed browser environment blocks direct navigation to local and local-server URLs. The QA therefore loaded the exact production HTML into an in-memory document and supplied a temporary local-storage shim. Relative-file existence and link integrity were checked separately by the static audit. This limitation affects the harness route, not the packaged files or their standalone source.

## Known operating boundaries

- `file://` local-storage persistence varies by browser and device policy; exported records are the reliable handoff and backup mechanism.
- Print outputs must be printed at 100% and checked against the included calibration mark before physical transfer.
- Browser downloads and image permissions remain subject to managed-device policy.
- Automated evidence-readiness and sampling indicators support professional judgement; they are not grades or accreditation decisions.
- Historical scenarios, tokens, charts, economic data and some material behaviours are explicitly synthetic or creative unless separately sourced.

## Release-integrity verification

After extraction, open `RELEASE_SELF_CHECK.html`, select the complete release folder and run the local SHA-256 comparison. The expected inventory is also recorded in `RELEASE_MANIFEST.json` and `SHA256SUMS.txt`.
