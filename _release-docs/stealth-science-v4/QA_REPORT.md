# Stealth Science Ecosystem v4 — QA and Verification Report

**Release:** Stealth Science Ecosystem v4  
**Date:** 12 August 2026  
**Owner:** Matt Roper / Made by Matt  
**Outcome:** **PASS**, with the model, security, browser and accessibility qualifications stated below.

## 1. Release scope

The verified release contains:

- `orbit-vector-diagnostic.html` — ORBIT//VECTOR v4;
- `enzyme-reactor-overdrive.html` — ENZYME//OVERDRIVE v4;
- `mbm-master-hub.html` — MBM//SCIENCE PORTFOLIO v4;
- `mbm-legacy-adapter.js` — telemetry-v3 bridge for older apps;
- release documentation, checksums and machine-readable QA evidence.

The v4 audit exercised the following additions:

| Upgrade | Result |
|---|---|
| Velocity Verlet central-gravity integrator | PASS |
| Velocity Verlet Monte Carlo Worker path | PASS |
| Live orbital energy-drift HUD | PASS |
| Optional Lineweaver–Burk diagnostic | PASS |
| Competitive vs non-competitive visual signatures | PASS |
| Fixed 16-byte `mbm-telemetry-v3.0` packet | PASS |
| 33 × 33 encrypted QR target | PASS |
| 25 × 25 fail-soft QR | PASS |
| CRC-8 packet guard | PASS |
| Shared six-axis app/hub/adapter schema | PASS |
| Sandboxed Blob iframe mounting | PASS |
| Sans-serif UI / monospace-data hierarchy | PASS |
| High-contrast canvas under-strokes | PASS |
| Printable worksheet SVG from both apps | PASS |
| Worksheet/art metadata import into hub | PASS |
| ARIA live narrator mirror | PASS |
| Responsive and touch-target regression | PASS |
| Existing 81-record archive workflow | PASS |

## 2. QA environment

- Chromium `144.0.7559.96` on Debian GNU/Linux 13;
- Python `3.13.5`;
- Node.js `v22.16.0`;
- viewport tests at 320, 360, 768, 1024 and 1440 CSS pixels;
- runtime tests over local HTTP and direct `file://` navigation;
- browser downloads enabled for worksheet and archive verification.

This is a release regression in one recorded environment, not a formal certification across every school browser, WebView, operating system, assistive technology or device camera.

## 3. Source integrity and dependency checks

All JavaScript blocks were extracted and passed `node --check`.

Static inspection confirmed:

- no external `<script src>` dependency;
- no external stylesheet or font dependency;
- no application `fetch`, `XMLHttpRequest`, `WebSocket`, `EventSource` or `sendBeacon` path;
- no direct network URL required at runtime;
- all QR code generation is vendored inside each app;
- the master hub’s embedded app copies exactly match the packaged standalone HTML files;
- the hub frame sources are created with `URL.createObjectURL(new Blob(...))`;
- the iframe sandbox is `allow-scripts allow-modals allow-downloads` and does not include `allow-same-origin`.

The only browser requests observed in direct-file testing were the opened `file://` document and locally created `blob:` resources. No HTTP or HTTPS request was emitted.

## 4. Direct offline and Blob-frame verification

All three HTML files were opened directly through `file://`.

| File | Page errors | Console errors | Root overflow | WebCrypto |
|---|---:|---:|---:|---:|
| ORBIT//VECTOR | 0 | 0 | 0 px | available |
| ENZYME//OVERDRIVE | 0 | 0 | 0 px | available |
| Master Hub | 0 | 0 | 0 px | available |

The hub created two `blob:file:///…` iframe URLs. Both isolated frames announced:

- `READY v4.0` for ORBIT;
- `READY v4.0` for ENZYME.

No direct `src="orbit-vector-diagnostic.html"` or `src="enzyme-reactor-overdrive.html"` frame navigation remains.

The standalone apps retain localStorage persistence. The sandboxed lesson-deck instances operate as isolated in-memory sessions and deliver evidence through the event bus.

## 5. ORBIT//VECTOR v4 physics verification

### 5.1 Browser mission run

The Kepler laboratory was configured at:

- injection pitch: `45°`;
- speed: `53 m/s`;
- payload mass: `5 kg`.

The run completed as a sustained orbit:

> `Mean radius 91.1, radial span 2.0.`

The live HUD reported:

> `VERLET ΔE 1.9e-5%`

This is the relative specific-energy change recorded across that deliberately slightly non-circular 18-second run.

### 5.2 Extended integrator comparison

A separate numerical regression used:

- `μ = 250000`;
- initial radius `r = 90`;
- circular reference speed `sqrt(μ/r)`;
- timestep `Δt = 0.008`;
- 20 analytical orbital periods (`214.5871065` model seconds).

| Metric | Velocity Verlet | Explicit Euler |
|---|---:|---:|
| Relative energy drift | `7.53 × 10⁻15` | `3.96 × 10⁻1` |
| Relative angular-momentum drift | `3.64 × 10⁻15` | `2.86 × 10⁻1` |
| Radius span | `0.000988` | `60.4457` |
| Final radius | `90.0000000` | `150.4457441` |

In this reference case, Velocity Verlet reduced measured relative energy drift by approximately `5.26 × 10¹³` compared with explicit Euler.

### 5.3 Qualification

Velocity Verlet is symplectic and produces bounded energy error for the model. It does not make all numerical trajectories exactly closed. Closure also depends on the timestep, initial state and whether the simulation ends at an exact integer number of numerical periods. The app therefore exposes measured drift rather than asserting exact conservation.

### 5.4 Monte Carlo path

Static and runtime checks confirmed that the inline 100-run, ±3% uncertainty Worker uses the same Velocity Verlet position/acceleration/velocity sequence for orbital missions.

The uncertainty fan remains a visual pre-commit estimate. It does not alter the committed deterministic trajectory or learner score.

## 6. ENZYME//OVERDRIVE v4 kinetics verification

### 6.1 Double-reciprocal overlay

The optional Lineweaver–Burk panel opened successfully, painted a non-empty canvas and updated its accessible description.

At inhibitor level `50` with the model’s `Ki = 25`:

#### Competitive inhibitor

- apparent `Km = 75.0`;
- effective `Vmax = 100.0`;
- interpretation: steeper slope with the same y-intercept.

#### Non-competitive inhibitor

- apparent `Km = 25.0`;
- effective `Vmax = 33.3`;
- interpretation: higher y-intercept and lower effective ceiling.

The reference and current values were present in the canvas ARIA label as well as the visual plot.

### 6.2 Q₁₀ reference regression

With temperature `30°C`, pH `7.0`, substrate `50 mM`, no inhibitor and all other controls fixed:

| Q₁₀ | Output |
|---:|---:|
| `1.2` | `20.0 model MW` |
| `3.0` | `50.0 model MW` |

The larger Q₁₀ therefore produced the intuitively larger pre-denaturation rate increase.

### 6.3 Model qualification

The kinetics model is deliberately conceptual. The Lineweaver–Burk display is used to compare intercept and slope signatures; it is not intended as a modern experimental fitting method or a quantitative laboratory analysis package.

## 7. Compact telemetry and QR verification

### 7.1 Encrypted `MBM3`

Both apps generated:

- a fixed 16-byte plaintext packet;
- a 52-byte encrypted envelope;
- a 75-character `MBM3.` transfer code;
- a Version 4-L, `33 × 33` module QR symbol;
- a separate six-digit PIN.

The encrypted codes were independently decoded with:

- PBKDF2-HMAC-SHA-256;
- 60,000 iterations;
- AES-GCM;
- the app-displayed PIN.

Decoded packet checks:

| App | Packet bytes | Magic | Schema | App code | CRC-8 |
|---|---:|---:|---:|---:|---:|
| ORBIT | 16 | `0xB3` | 3 | 1 | valid |
| ENZYME | 16 | `0xB3` | 3 | 2 | valid |

An incorrect PIN was rejected by the master hub with no record added.

### 7.2 Fail-soft `MBM3U`

WebCrypto was deliberately disabled before either app loaded.

Both apps then produced:

- `MBM3U` rather than `MBM3`;
- a 28-character transfer code;
- a `25 × 25` module QR symbol;
- `NOT USED` in the PIN field;
- a visible **Unencrypted Offline Mode** warning;
- zero page or console errors.

The hub successfully decoded a synthetic CRC-valid WAVE `MBM3U` packet into the standard six-axis portfolio shape.

### 7.3 Security qualification

The six-digit PIN has limited entropy. AES-GCM protects the payload during brief transfer, but the PIN is not suitable for long-term confidential storage. `MBM3U` is intentionally unencrypted and should only be used for deliberate same-room hand-off. Neither transfer format includes a learner name automatically.

## 8. Telemetry-schema harmonisation

Event-bus collection from the two embedded apps created two hub records. Both records contained:

- `telemetrySchema: "mbm-telemetry-v3.0"`;
- all six common competency axes;
- finite scores for every axis;
- the app-specific source information retained separately.

The legacy adapter browser regression used a complete OHM mapping and produced:

- schema `mbm-telemetry-v3.0`;
- adapter schema `mbm-legacy-adapter-2.0`;
- all six axis names;
- a complete-coverage flag;
- a CRC-valid 16-byte packet;
- app code `4`.

The adapter deliberately withholds compact packet output when one or more axes are unmapped. Missing values remain `null`; they are not converted into invented zero scores.

## 9. Hub integration and art-as-assessment

The end-to-end hub run completed these routes:

1. collected both isolated lesson-deck apps through `mbm-export-all`;
2. rejected an ORBIT `MBM3` code with the wrong PIN;
3. imported the same code with the correct PIN;
4. imported an ENZYME SVG containing `metadata#mbm-eval`;
5. imported a WAVE `MBM3U` packet;
6. retained all records with the exact six-axis schema.

Final portfolio count for that integration run: **5 records**.

Both generated worksheet SVGs passed content checks:

### ORBIT worksheet

- white background;
- trajectory path;
- `vₓ` and `vᵧ` labels;
- next-variable annotation line;
- MBM3 evidence metadata.

### ENZYME worksheet

- white background;
- active-site structure;
- activation-energy paths;
- reference/current Lineweaver–Burk lines;
- `Km` and `Vmax` values;
- MBM3 evidence metadata.

## 10. Event-bus verification

The hub received confirmations for:

- high-contrast theme application;
- low-stimulus mode;
- pause;
- resume;
- export.

The status readouts now distinguish:

- **LOW-STIM** from **FULL VISUAL**;
- **PAUSED** from **RESUMED**;
- the selected theme.

No frame-access exception occurred under the opaque sandbox.

## 11. Evidence-register resilience

The hub was seeded with 81 records.

Before archive:

> `LOCAL ONLY // 81 EVIDENCE RECORDS`

The storage warning and **Archive & Purge** button were visible. The action downloaded an archive containing all 81 records under schema `mbm-master-hub-4.0`, then started a clean zero-record register and saved `lastArchiveAt`.

No `slice(-80)` truncation path is present.

## 12. Typography, contrast and accessible status verification

Computed typography checks confirmed:

- body/UI font: system sans-serif stack;
- telemetry/data font: system monospace stack.

Canvas source and runtime inspection confirmed dark under-strokes around dynamic text and target geometry in:

- ORBIT main canvas and teacher radar;
- ENZYME main canvas, Lineweaver–Burk canvas and teacher radar;
- hub radar.

When VOICE was enabled, both apps wrote:

> `Audio descriptions on.`

into the hidden polite live region, independent of whether audible speech output was available.

The automated visible-control check found:

- zero unnamed visible buttons;
- zero tested visible buttons below the 40 px smoke threshold after final touch-target corrections;
- 44 px minimum target rules for primary and compact action controls.

This is not a complete WCAG audit. It did not reproduce every screen reader, high zoom level, switch-control workflow, colour-vision condition or browser accessibility tree.

## 13. Responsive verification

All three HTML files were rendered at:

- 320 px;
- 360 px;
- 768 px;
- 1024 px;
- 1440 px.

At every width:

- root horizontal overflow was false;
- page-error collection was empty;
- console-error collection was empty.

## 14. Final outcome

**PASS**

The release meets the stated v4 goals in the recorded QA environment:

- substantially improved orbital energy behaviour;
- correct conceptual inhibitor signatures;
- low-density compact QR transfer;
- one common six-axis telemetry contract;
- direct-file offline execution;
- Blob-isolated lesson-deck frames;
- professional font hierarchy;
- outlined canvas labels and targets;
- printable evidence-bearing worksheet SVGs;
- assistive-technology status mirroring;
- no external runtime dependency or observed network request.

The package remains educational modelling software. Its telemetry is classroom evidence of observed interaction patterns, not a diagnostic judgement about a learner.
