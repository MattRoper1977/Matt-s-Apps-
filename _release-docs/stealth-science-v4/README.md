# Made by Matt — Stealth Science Ecosystem v4

Stealth Science Ecosystem v4 is a fully offline, zero-runtime-dependency classroom suite for turn-based scientific reasoning, boundary testing, low-friction diagnostic play and local teacher evidence.

The release contains:

| File | Purpose |
|---|---|
| `mbm-master-hub.html` | Self-contained portfolio dashboard and Blob-isolated two-app lesson deck |
| `orbit-vector-diagnostic.html` | ORBIT//VECTOR v4 trajectory and inverse-square gravity diagnostic |
| `enzyme-reactor-overdrive.html` | ENZYME//OVERDRIVE v4 enzyme kinetics and failure-boundary simulator |
| `mbm-legacy-adapter.js` | Bridge from older tools to the common six-axis telemetry contract |
| `QA_REPORT.md` | Human-readable verification report and model qualifications |
| `QA_RESULTS.json` | Machine-readable release evidence |
| `CHECKSUMS.sha256` | SHA-256 integrity hashes for every packaged file |
| `THIRD_PARTY_NOTICES.md` | Licence notice for the vendored offline QR encoder |

No account, server, analytics service, package manager, external font, CDN or internet connection is required.

## Start here

Open `mbm-master-hub.html` directly in a current browser. The hub itself contains Base64-embedded copies of both applications and decodes them into local Blob URLs. It therefore does not need to fetch either app when its Lesson Deck opens.

The two standalone HTML files remain useful when a learner needs a dedicated full-screen app with its own local browser persistence.

### Hub views

- **Portfolio** aggregates compatible evidence into a six-axis radar and printable A4 Learning Journey.
- **Lesson Deck** controls both local app frames through the MBM event bus.
- **Hand-off** imports MBM3/MBM3U codes, legacy MBM2/MBM1 codes, JSON, storage records and evidence-bearing SVG artwork.

### Teacher review access

Inside either science app:

- triple-click or triple-tap the glowing logo; or
- press `Alt + Shift + D`.

The review overlay contains a competency radar, plain-language interpretation, recent evidence, JSON/Base64 exports, a compact QR hand-off, procedural art export and worksheet SVG export.

No learner name is collected automatically. The hub includes an optional teacher-entered learner or group reference for a local printout.

# What v4 adds

## 1. Velocity Verlet orbital integration

The central-gravity laboratory in ORBIT//VECTOR now uses a second-order Velocity Verlet update:

```text
x(t + Δt) = x(t) + v(t)Δt + ½a(t)Δt²
v(t + Δt) = v(t) + ½[a(t) + a(t + Δt)]Δt
```

with:

```text
a = −μr / |r|³
```

The core laboratory timestep is `Δt = 0.008` model seconds. The same symplectic update is used in the reduced-resolution Monte Carlo Worker.

Velocity Verlet substantially reduces the artificial energy growth and orbital decay produced by explicit Euler integration. It does not make every numerical orbit mathematically exact: timestep, initial conditions and stopping time still affect closure. The app therefore reports measured relative energy drift in the canvas HUD instead of claiming perfect conservation.

The verified reference tests are recorded in `QA_REPORT.md` and `QA_RESULTS.json`.

## 2. Optional Lineweaver–Burk diagnostic

ENZYME//OVERDRIVE now includes an optional **1/v PLOT** overlay. It compares an uninhibited reference with the current reactor condition using:

```text
1/v = (Km(app) / Vmax(app)) × 1/[S] + 1/Vmax(app)
```

The plot is designed to make two conceptual signatures visible:

- **competitive inhibition:** apparent `Km` rises while `Vmax` is retained, producing a steeper line with the same y-intercept;
- **non-competitive inhibition:** effective `Vmax` falls while the model’s `Km` is retained, raising the y-intercept.

The overlay includes accessible canvas labelling and a live textual interpretation. It is a conceptual teaching model, not a recommendation to use double-reciprocal regression for modern experimental parameter estimation.

## 3. `mbm-telemetry-v3.0` common contract

ORBIT, ENZYME, the hub and the legacy adapter now use the same six axes:

1. Variable Isolation
2. Scale Interpolation
3. Systemic Troubleshooting
4. Boundary Control
5. Failure Reflection
6. Resource Control

Full JSON exports retain app-specific evidence as well as this common profile. Compact QR transfer uses a fixed 16-byte packet.

### 16-byte packet layout

| Byte | Field |
|---:|---|
| `0` | Magic byte `0xB3` |
| `1` | High nibble: schema major `3`; low nibble: app code |
| `2..7` | Six competency scores, each quantised from `0..1` into `0..255` |
| `8..9` | Primary app-specific control, unsigned 16-bit |
| `10..11` | Secondary app-specific control, unsigned 16-bit |
| `12` | Tertiary app-specific control, unsigned 8-bit |
| `13` | Event count, capped at 255 |
| `14` | High nibble: success score; low nibble: state flags |
| `15` | CRC-8 checksum using polynomial `0x07` |

App codes in this release are:

| Code | App |
|---:|---|
| `1` | ORBIT//VECTOR |
| `2` | ENZYME//OVERDRIVE |
| `3` | WAVE ENGINE |
| `4` | OHM’S LAW FAULT FINDER |
| `5` | CALM NOISE MONITOR |
| `6` | OPTICS LAB |

## 4. Low-density MBM3 QR hand-off

### Encrypted mode — `MBM3`

Where WebCrypto is available, the 16-byte packet is protected using:

- AES-GCM-256;
- PBKDF2-HMAC-SHA-256;
- 60,000 derivation iterations;
- an 8-byte random salt;
- a 12-byte random IV;
- a separate six-digit transfer PIN;
- Base64url encoding.

The resulting envelope is 52 bytes and the complete transfer code is 75 characters. In both applications this fits a Version 4-L QR symbol with a **33 × 33** module matrix.

The PIN is suitable for short-lived same-room classroom transfer, not long-term security. Formal records should be moved into the setting’s approved system.

### Fail-soft mode — `MBM3U`

If `crypto.subtle` is unavailable, the apps preserve hand-off by generating a clearly labelled unencrypted packet:

```text
MBM3U.<base64url packet>
```

The fallback is 28 characters and rendered as a **25 × 25** QR symbol in the verified browser simulation. The UI displays **UNENCRYPTED OFFLINE MODE** and shows `NOT USED` rather than pretending a PIN is protecting it.

The hub continues to accept legacy MBM2 and MBM1 transfers.

## 5. Blob-isolated local Lesson Deck

The hub no longer navigates its iframes directly to neighbouring `file://` paths. Instead it:

1. stores a Base64 copy of each complete HTML app inside `mbm-master-hub.html`;
2. decodes that source locally;
3. creates a `text/html` Blob;
4. mounts the Blob URL in a sandboxed iframe.

The frame sandbox allows scripts, modal dialogs and deliberate downloads, but does not grant `allow-same-origin`. This removes the common `allow-scripts + allow-same-origin` sandbox escape warning and keeps lesson-deck frames isolated from the parent DOM.

Because the sandboxed frames have an opaque origin, their embedded-deck state is treated as in-memory session state and handed to the hub through `postMessage`. The standalone HTML apps retain their normal localStorage persistence.

The hub and app event bus supports:

| Incoming message | Behaviour |
|---|---|
| `mbm-set-theme` | Apply dark, light or high-contrast theme |
| `mbm-set-focus` | Apply or remove low-stimulus/high-focus mode |
| `mbm-pause-all` | Pause or resume active playback and controls |
| `mbm-export-all` | Return a local evidence payload |

Each app announces `mbm-app-ready` and replies with explicit applied/export messages.

## 6. Professional typography and canvas contrast

The interface now uses a system sans-serif hierarchy for prose, prompts, controls and headings:

```css
Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
"Segoe UI", sans-serif
```

No Inter font file is downloaded. The browser simply uses Inter if it is already installed, then falls back to the operating system UI font.

Monospace is reserved for telemetry values, coordinate-style readouts, tables and diagnostic logs.

Dynamic canvas labels and active targets use dark under-strokes before their coloured foreground strokes. This includes:

- receiver and orbit-band labels;
- velocity-component labels;
- enzyme structure and telemetry labels;
- activation-energy labels;
- Lineweaver–Burk axes and current/reference values;
- teacher and hub radar labels.

## 7. Worksheet SVG print mode

Both apps now provide **WORKSHEET SVG** from the main action area and teacher overlay.

### ORBIT worksheet

The white-background vector worksheet includes:

- the current deterministic trajectory;
- receiver or target-orbit geometry;
- labelled `vₓ` and `vᵧ` arrows;
- selected control values and integrator name;
- prediction, evidence and next-variable annotation lines.

### ENZYME worksheet

The white-background kinetics worksheet includes:

- an active-site structure outline;
- catalysed and reference activation-energy paths;
- reference and current Lineweaver–Burk lines;
- `Km` and `Vmax` values;
- prediction, evidence and next-variable annotation lines.

Both worksheet SVGs include the same `metadata#mbm-eval` evidence envelope used by procedural art exports. A teacher can print the SVG or drop it back into the hub as an art-as-assessment file.

## 8. ARIA and voice guidance

When **VOICE** is enabled, every narrator call now writes the same cleaned status message to a hidden:

```html
<div role="status" aria-live="polite" aria-atomic="true">
```

The native `window.speechSynthesis` voice remains optional. A browser without speech output can still expose the live status to assistive technology.

# ORBIT//VECTOR v4

Storage key: `mbm_orbit_vector_v1`  
App schema: `orbit-vector-4.0`  
Common telemetry schema: `mbm-telemetry-v3.0`

The app retains:

- five trajectory sectors plus an always-open Kepler laboratory;
- deterministic set → run → observe → adjust phases;
- previous-attempt ghost trace;
- live `vₓ` and `vᵧ` arrows;
- 100-run ±3% uncertainty fan in an inline Blob Worker;
- velocity-to-pitch sonification;
- vacuum mass-dependent adjustment cost without changing gravitational acceleration;
- adaptive one-variable and pause-after-failure prompts;
- low-stimulus mode and panic-free `R` reset.

The central-gravity model uses:

```text
F = GMm/r²

a = GM/r²
```

Payload mass therefore cancels from acceleration. In vacuum it affects operational adjustment energy only:

```text
cost = 1 + floor(payload mass / 4)
```

# ENZYME//OVERDRIVE v4

Storage key: `mbm_enzyme_overdrive_v1`  
App schema: `enzyme-overdrive-4.0`  
Common telemetry schema: `mbm-telemetry-v3.0`

The app retains:

- six mission shifts plus Open Failure Lab;
- Michaelis–Menten-style saturation;
- Q₁₀ scaling anchored at `Tref = 20°C` before denaturation;
- reversible pH distortion;
- competitive and non-competitive inhibitor geometry;
- irreversible thermal damage until catalyst replacement;
- live activation-energy barrier display;
- denaturation-linked WaveShaper sonification;
- adaptive variable, plateau and collapse prompts;
- low-stimulus mode and panic-free `R` reset.

The pre-optimum temperature factor is based on:

```text
Q₁₀^((T − Tref) / 10)
```

with a separate post-optimum structural penalty and commit-time damage model.

# Legacy adapter v2.0

`mbm-legacy-adapter.js` converts an older app’s state into `mbm-telemetry-v3.0`.

A mapping rule can be:

- a dot-path string;
- a fixed numeric value;
- a function receiving the legacy state.

The adapter always exports the same six axis names. Missing mappings remain `null` and are listed under `coverage.missingAxes`; they are not silently converted into false zeroes. A compact packet is produced only when all six axes are available.

Example:

```html
<script>
window.MBM_LEGACY_ADAPTER_CONFIG = {
  appId: 'ohms',
  appCode: 4,
  appName: 'OHM’S LAW FAULT FINDER',
  sourceKey: 'mbm_ohms_fault_finder_v1',
  profile: {
    'Variable Isolation': 'telemetry.variableIsolation',
    'Scale Interpolation': 'telemetry.scalePrecision',
    'Systemic Troubleshooting': 'telemetry.faultIsolation',
    'Boundary Control': 'telemetry.safeBoundaryControl',
    'Failure Reflection': 'telemetry.pauseReflection',
    'Resource Control': 'telemetry.probeEfficiency'
  },
  packet: {
    primary: 'controls.voltage',
    primaryScale: 100,
    secondary: 'controls.resistance',
    secondaryScale: 10,
    tertiary: 'controls.probeMode',
    events: 'telemetry.attempts',
    successRate: 'telemetry.successRate'
  }
};
</script>
<script src="mbm-legacy-adapter.js"></script>
```

For a completely self-contained legacy file, paste the adapter source inline instead of using `src`.

# Evidence-register resilience

The hub retains every record until the teacher removes it or deliberately archives and purges the register.

At 70 records it shows a warning and reveals **Archive & Purge**. That action:

1. downloads the complete timestamped JSON archive;
2. begins a clean register;
3. records the archive timestamp.

The final regression loaded 81 records, archived all 81 and then confirmed a zero-record clean register.

Hub storage key: `mbm_master_portfolio_v1`  
Hub schema: `mbm-master-hub-4.0`

# Privacy and model boundaries

- All evidence remains on the device unless a person deliberately exports or transfers it.
- No app automatically collects a learner name.
- QR and SVG evidence are transport formats, not tamper-proof records.
- The six-digit encrypted-transfer PIN is low-entropy and intended only for brief classroom hand-off.
- Telemetry indicates observed interaction patterns; it is not a psychological, medical or ability diagnosis.
- The simulations are conceptual educational models, not engineering, clinical or laboratory-control software.
- The double-reciprocal plot is a visual comparison tool, not a substitute for robust modern kinetic fitting.

# Browser notes

The final QA covered current headless Chromium over both local HTTP and direct `file://` navigation. Other browsers and managed WebViews may differ in download, clipboard, WebCrypto, speech, BarcodeDetector and print support.

The apps retain JSON and SVG export even when clipboard, camera decoding or speech output is unavailable. WebCrypto failure invokes the explicit MBM3U fallback.

See `QA_REPORT.md` for exact test results and qualifications.
