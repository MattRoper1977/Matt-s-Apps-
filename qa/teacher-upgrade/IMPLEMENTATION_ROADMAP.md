# Implementation roadmap — small, reversible PRs

This roadmap separates urgent integrity work from optional app redesign. It assumes no direct commit to `main`, no deletion and no live-deployment claim until the repository and public URL have both been tested.

## PR 1 — integrity, catalogue and shared foundation

**Purpose:** land the smallest coherent improvement with the highest time-saving value.

### Add

- `Data_Manager_Studio.html`
- `teacher-workflow.js`
- `teacher-workflow.css`
- `evidence-schema-v2.json`
- `awarding-body-templates.json`

### Modify

- `Evidence_Binder.html` — stable outcome identity and linked-unit deletion guard; shared context bridge.
- `Classroom_Toolkit.html` — shared context/roster bridge.
- `Seating_Studio.html` — shared context/roster bridge.
- `Rubric_Studio.html` — shared roster and assessment-draft bridge.
- `Exit_Ticket.html` — anonymous class-check bridge.
- `Writing_Frames.html` — writing-draft bridge.
- `Quiz_Studio.html` — diagnostic-result bridge.
- `Graph_Studio.html`, `Whiteboard.html`, `PDF_Studio.html`, `ChoreoStudio.html` — teacher context bridge only.
- `apps.json` — add Data Manager Studio once, at the top of Teacher tools.
- `index.html` — remove stale manual count and classify Data Manager as teacher admin.
- `README.md` — current entry point, Data Manager and evidence/privacy boundary.
- `suite-health.html` — replace retired inline-catalogue parser with v2.

### Must not modify

- Feelings Check-in;
- Regulation Station;
- lesson wording, ordering, answers or assessment content;
- external UAS, ASDAN or Voxel applications;
- deployment ownership or custom-domain routing.

### Gates

1. Run the patcher in dry-run and review the exact diff.
2. Run patcher unit tests.
3. Apply on a branch; verify the generated timestamped backup.
4. Run the static verifier with zero failures.
5. Run the browser smoke test with zero failures.
6. Manually test existing Evidence Binder backup/restore and portfolio export using non-sensitive fixtures.
7. Manually test all eleven bridged apps at desktop and mobile sizes.
8. Confirm Feelings Check-in and Regulation Station have no launcher, roster or outbox code.
9. Open a draft PR. Do not merge from a content review alone.

## PR 2 — Evidence Binder migration and compatibility

**Purpose:** allow existing Binder users to adopt stable IDs and Data Manager without abandoning old backups.

### Proposed additions

- read-only Binder v1 migration preview;
- learner-name matching report with explicit conflict resolution;
- unit/outcome mapping preview;
- imported evidence remains `draft`;
- attachment checksum and missing-blob report;
- export a migration receipt;
- no write to the original Binder database until confirmation.

### Gates

- fixtures with reordered outcomes;
- duplicate names;
- renamed learners;
- missing attachments;
- linked outcomes removed from current unit wording;
- rollback from the pre-migration backup.

## PR 3 — Rubric and assessment quality

**Purpose:** turn Rubric Studio into a versioned assessment drafting tool without making automatic qualification decisions.

### Proposed changes

- rubric IDs and versions;
- stable criterion IDs and optional official criterion code/source;
- archive replaced rubrics;
- shared cohort roster with stable learner ID;
- assessor, date, moderation state and rationale;
- evidence locator links;
- side-by-side “student work / criterion / decision / rationale” review;
- structured hand-off to Data Manager;
- generated feedback clearly labelled as a draft.

### Gates

- criterion reorder does not move marks;
- rubric version migration;
- duplicated learner display names remain distinct;
- moderation state is not achievement/certification state;
- print/PDF feedback accessibility.

## PR 4 — classroom organisation

### Classroom Toolkit

- named class presets;
- named timer sequences such as starter, modelling, practice and review;
- group constraints and deterministic replay seed;
- shared cohort selection;
- explicit reset and undo;
- noise meter continues to store no audio.

### Seating Plan Studio

- stable learner IDs;
- multiple named plans per cohort;
- archive/restore plans;
- staff-only constraints separated from display/export data;
- duplicate-name handling;
- keyboard alternative to drag-and-drop;
- print-safe versions.

### Exit Ticket

- lesson ID/title;
- question bank by lesson;
- teacher “next teaching action” field;
- repeat-check comparison;
- remain anonymous by default;
- no individual evidence conversion.

## PR 5 — lesson-artifact hand-offs

Work through creation apps in bounded groups. Each app receives the same minimum contract:

- lesson ID/title/path;
- learner/cohort selected only in explicit teacher mode;
- project title and source app/version;
- artifact export plus small JSON metadata sidecar;
- reflection/process note;
- hand-off status always `draft`;
- no automatic criterion match unless staff select it;
- no external upload.

Suggested order:

1. Art Studio, Design Studio, Photo Studio, Comic Studio.
2. Graph Studio, Writing Frames, Mind-Map Studio, Message Studio.
3. Animation, Audio, Video and Music Studio, with storage/quota testing.
4. Craft Studio and Web Studio, with strong positive-control security tests.

## PR 6 — lesson repository integration

This belongs in `MattRoper1977/Lessons`, not in the apps PR.

### Proposed contract

Lessons may publish a small versioned context record containing:

- lesson ID and path;
- lesson title;
- subject/suite;
- BUILD/GROW/LAUNCH pathway;
- tier;
- current activity/tool link;
- exact criterion codes only where already present in the approved lesson;
- no learner data.

Apps read the context only after a teacher opens them. They do not alter lesson content or lesson sequence.

### Gates

- all existing lessons still run with the context script absent;
- no content or answer changes;
- no new awarding-body claims;
- no automatic evidence decision;
- direct app links still work;
- context keys are versioned and bounded.

## PR 7 — data governance hardening

Only after staff pilot feedback:

- centre-configurable retention review date;
- encrypted export option using a centre-selected passphrase and Web Crypto;
- clear recovery warning: lost passphrase means lost backup;
- optional pseudonymous display mode;
- export audit receipt;
- attachment duplicate detection by hash;
- storage quota management;
- documented data-controller responsibilities;
- no cloud service until the centre has selected, approved and governed it.

## Release discipline

Every PR should include:

- a before/after file manifest;
- no-deletion statement;
- exact test commands and outputs;
- screenshots only for changed interfaces;
- a privacy impact note;
- an awarding-body boundary note where relevant;
- migration and rollback notes;
- a draft PR until review is complete.

Do not combine a content change with a change to the test that judges that content. A failing positive-control fixture must be fixed in the implementation, not weakened in the gate.
