# Master Hub Installation Guide — WAVE & OHM v2.3

## 1. Preserve the current production Hub

Make a backup of the current `mbm-master-hub.html` before integration. The supplied bridge is additive and is designed to sit beside the Hub’s existing MBM2 AES-GCM decoder rather than replace it.

## 2. Load the bridge

Place `mbm-master-hub-bridge-v2-3.js` beside the Hub and load it after the Hub’s existing core functions:

```html
<script src="mbm-master-hub-bridge-v2-3.js"></script>
```

For a strict single-file Hub, paste the complete bridge source into a `<script>` element near the end of the document.

The public API is exposed as:

```js
window.MBMTeacherToolsBridge
```

## 3. Storage discovery

The bridge’s `KNOWN` array includes:

```js
{ key: 'mbm_ohms_fault_finder_v2', app: 'OHM’S LAW FAULT-FINDER v2.3', id: 'ohms' }
{ key: 'mbm_wave_iridescence_v2', app: 'WAVE & IRIDESCENCE ENGINE v2.3', id: 'wave' }
```

Scan same-origin records with:

```js
const records = MBMTeacherToolsBridge.scanKnownStorage();
```

A tool opened from a different origin, a different subdomain or a local `file://` path does not share the Hub’s localStorage.

## 4. Extend the current hand-off decoder

Do not remove the production MBM2 route. Wrap it:

```js
const originalDecryptCode = decryptCode;
decryptCode = MBMTeacherToolsBridge.patchDecryptCode(originalDecryptCode);
```

The wrapper bypasses the PIN prompt only for validated `MBM.WAVE.*` and `MBM.OHM.*` envelopes. All other formats continue through the original decoder.

An alternative explicit route is:

```js
const payload = await MBMTeacherToolsBridge.decodeEnvelope(code, {
  pin,
  decryptMBM2: originalDecryptCode
});
```

## 5. Decode with privacy information

Use `decodeEnvelopeRecord()` when the interface should display whether a payload is encrypted:

```js
const record = await MBMTeacherToolsBridge.decodeEnvelopeRecord(code, {
  pin,
  decryptMBM2: originalDecryptCode
});

console.log(record.payload);
console.log(record.security.level);
console.log(record.security.privacyWarning);
```

Possible security labels are:

- `encrypted` — MBM2 AES-GCM route;
- `encoded` — portable but unencrypted WAVE, OHM or MBM1 route;
- `unknown` — unsupported or unidentified format.

## 6. Generate the six-axis radar

```js
const radar = MBMTeacherToolsBridge.mapCompetencyRadar(payload);
drawRadar(radar);
```

The returned object contains:

```js
{
  axes,
  labels,
  scores,
  evidence,
  formulas,
  rulesVersion,
  generatedAt
}
```

Use `evidence` and `formulas` in a details panel so teachers can see why a score was produced.

## 7. Intake evidence PNGs

### Direct file input

```js
const file = fileInput.files[0];
const record = await MBMTeacherToolsBridge.intakePngFile(file, {
  pin,
  decryptMBM2: originalDecryptCode
});

registerRecord(record);
```

### Drag-and-drop target

```js
const uninstall = MBMTeacherToolsBridge.installPngDropTarget(
  document.getElementById('drop-zone'),
  (record, error) => {
    if (error) return showError(error.message);
    registerRecord(record);
  },
  { pin, decryptMBM2: originalDecryptCode }
);
```

Call `uninstall()` when the drop interface is removed.

## 8. Control embedded tools

Broadcast to every iframe:

```js
MBMTeacherToolsBridge.broadcast('mbm-set-theme', 'high-lumen');
MBMTeacherToolsBridge.broadcast('mbm-set-low-stimulus', true);
MBMTeacherToolsBridge.broadcast('mbm-pause-all', true);
MBMTeacherToolsBridge.broadcast('mbm-reset-all', null);
```

Prepare one matching tool only:

```js
MBMTeacherToolsBridge.sendToTool(
  'wave-iridescence',
  'mbm-load-task',
  'wave-brewster'
);
```

## 9. Collect live results

```js
const results = await MBMTeacherToolsBridge.collectResults({
  root: document,
  expectedTools: ['wave-iridescence', 'ohms-fault-finder'],
  timeoutMs: 1300
});
```

The collector limits accepted messages to the currently embedded iframe windows. Each returned item already contains `radar` and, where appropriate, `taskEvidence`.

## 10. Add task-aware packaging

The bridge includes four task definitions in `DEFAULT_LESSON_TASKS`. Three are enabled by default.

```js
const html = MBMTeacherToolsBridge.buildStandaloneLesson({
  title: 'Year 10 WAVE and Circuit Investigation',
  tools: [
    {
      id: 'wave',
      title: 'WAVE & Iridescence',
      tool: 'wave-iridescence',
      html: waveHtml,
      initialHash: ''
    },
    {
      id: 'ohm',
      title: 'Ohm’s Law Fault-Finder',
      tool: 'ohms-fault-finder',
      html: ohmHtml,
      initialHash: ''
    }
  ],
  tasks: MBMTeacherToolsBridge.DEFAULT_LESSON_TASKS
});
```

Or download directly:

```js
MBMTeacherToolsBridge.downloadStandaloneLesson({
  title: 'Year 10 WAVE and Circuit Investigation',
  fileName: 'year-10-wave-circuits.html',
  tools,
  tasks
});
```

## 11. Blob URL cleanup

The generated deck revokes every reconstructed tool Blob URL during page teardown. A custom Hub controller should follow the same rule when replacing frames:

```js
function removeLoadedTool(frame, blobUrl) {
  frame.src = 'about:blank';
  frame.remove();
  URL.revokeObjectURL(blobUrl);
}
```

Also revoke temporary download URLs after clicking them.

## 12. Task completion display

Use the tool’s own evidence when present:

```js
const evidence = payload.lessonTaskEvidence ||
  MBMTeacherToolsBridge.evaluateLessonTask(payload.lessonTask, payload);
```

Never turn the radar into an automatic statutory grade. It is intended to support teacher interpretation, questioning and next-step planning.

## 13. Production acceptance checks

Before replacing the production Hub, verify:

- existing MBM2 PIN decryption still works;
- WAVE and OHM envelopes bypass the PIN only after schema validation;
- malformed envelopes show a controlled error;
- identifying fields trigger a privacy warning;
- PNG drop intake works with original exported files;
- radar scores show their formula and evidence;
- all iframe controls operate from the Hub;
- task setup reaches the intended tool only;
- removing and replacing tools releases Blob URLs;
- the generated standalone lesson reopens offline;
- mobile layout has no horizontal page overflow;
- low-stimulus controls retain 48 px interaction areas.

The supplied `mbm-master-hub-integration-preview-v2-3.html` demonstrates each of these integration surfaces without altering the production Hub.
