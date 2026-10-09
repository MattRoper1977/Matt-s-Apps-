# Matt’s Apps — teacher workflow and evidence audit

**Repository:** `MattRoper1977/Matt-s-Apps-`  
**Audited branch:** `main`  
**Audited head:** `c69895423ecaaf4fa859bd6fef6bc717d2a94863`  
**Audit date:** 5 August 2026  
**Repository writes made during this task:** none

## Executive finding

The suite already has a strong classroom identity: most tools are single-file, local-first, touch-friendly and deliberately low-pressure. The main time cost is not a missing visual theme. It is that teacher context and learner identity are repeatedly re-entered across separate local stores, while evidence and assessment outputs stop at each app boundary.

The highest-value upgrade is therefore a **shared, versioned teacher-workflow layer** rather than a wholesale rewrite. This pack adds:

1. a standalone **Data Manager Studio** for cohorts, stable learner IDs, programme/unit/criterion mapping, evidence metadata and attachments, coverage, review queues, CSV reports and full local backup/restore;
2. a deliberately small **shared roster/context/evidence hand-off bridge** for selected apps;
3. two urgent Evidence Binder data-integrity guards;
4. a catalogue-driven Suite Health page;
5. an editable evidence interchange schema and current-framework workflow profiles;
6. a non-destructive patch generator, verifier and real-browser test.

No proposed component certifies achievement, submits to an awarding body or uploads data automatically.

## Measured repository baseline

The current `main` tree contains **34 tracked artefacts**:

- **30 HTML pages**: 27 local app pages, the Creator Hub, Suite Health and the 404 page;
- `apps.json`;
- `README.md`;
- one SVG background;
- one PNG image.

The live catalogue contains **30 entries**: **27 local targets** and **3 external targets**. A source search measured **23 HTML tools writing to `localStorage`** and **3 using IndexedDB**. Their record shapes and keys are largely independent.

The complete audited file list and selected Git blob IDs are in `BASELINE_MANIFEST.json`.

## Audit depth

The review used three levels and does not pretend every app received the same depth:

- **Deep source audit:** Evidence Binder, Rubric Studio, Exit Ticket, Classroom Toolkit, Seating Plan Studio and Writing Frames Studio.
- **Targeted source/integration review:** Quiz Studio, Graph Studio, Whiteboard, PDF Studio, ChoreoStudio, the hub, `apps.json`, README and Suite Health.
- **Catalogue-level workflow review:** the remaining local tools and external integrations. These receive bounded recommendations, not unsupported claims about internal implementation.

`APP_UPGRADE_MATRIX.csv` records the depth, priority, recommended patch and acceptance gate for every existing catalogue entry plus the proposed Data Manager Studio.

## Load-bearing findings

### 1. Learner identity is fragmented

Classroom Toolkit, Seating Plan Studio and Rubric Studio each maintain their own name list. The lesson repository also uses the legacy `ps_coldcall_roster` key. Names are useful display labels but are not stable identifiers: spelling corrections, preferred-name changes and duplicate names can disconnect or conflate records.

**Upgrade response:** Data Manager Studio generates stable internal learner IDs, keeps centre learner IDs optional, supports cohort membership and archives rather than destructively deleting learners. The shared roster record carries IDs and display names while retaining the legacy plain-name roster for existing lesson compatibility.

### 2. Evidence Binder can silently mis-attach evidence after outcome reordering

The current unit editor preserves outcome IDs by array position. If a teacher reorders unchanged outcome lines, evidence can remain attached to the old positional ID while the displayed wording changes. That is a silent integrity failure.

**Upgrade response:** the generated patch preserves IDs by normalised exact wording first, uses same-position fallback only for an intentional wording edit, rejects duplicate outcome lines and blocks removal of an outcome that is linked to evidence.

### 3. Evidence Binder can orphan evidence when deleting a unit

The current delete path warns that linked evidence will remain but lose unit tags, then permits the deletion. The stored items are not deleted, but their qualification context is orphaned.

**Upgrade response:** the generated safety patch blocks deletion of a unit that has linked evidence. Empty units may still be removed. Data Manager Studio uses archive states for learners, programmes, units, criteria and evidence records.

### 4. Rubric decisions and evidence collection are disconnected

Rubric Studio stores pupils and marks inside its own rubric data. It cannot reuse a stable cohort roster or queue a structured assessment draft for evidence review.

**Upgrade response:** the shared layer can copy an explicitly selected roster into the current rubric and can queue an **assessment-decision draft**. The hand-off records criterion/level text and assessor context but always uses `not-assessed` until a teacher reviews it in Data Manager Studio.

### 5. Exit Ticket is appropriately anonymous, but its teaching decision is lost

Exit Ticket is a strong formative class check because it records aggregate understanding rather than named pupil performance. Turning it into individual accreditation evidence would damage that privacy boundary.

**Upgrade response:** the bridge queues only an anonymous `class-check` draft containing the question, counts and lesson context. The recommended next patch adds a teacher field for “what I will reteach/change next”, not pupil identity.

### 6. The hub and health documentation have drifted

- The hub metadata advertises 28 studios while `apps.json` contains 30 catalogue entries.
- README says 23 tools and refers to `Suite_Hub.html`, which is not in the audited tree.
- Suite Health still searches `index.html` for the retired inline `f:"…"` catalogue format even though catalogue data now lives in `apps.json`. This can produce an empty inventory and a false-looking pass.

**Upgrade response:** the patch removes manual counts from descriptive metadata, documents the real `index.html` entry point, catalogues Data Manager Studio and replaces Suite Health with a positive-control checker that fails on an empty catalogue and reads `apps.json` directly.

### 7. Storage is local-first but not a complete records-management strategy

Local browser storage supports privacy and offline use, but it can be cleared, is device-specific and does not itself provide encryption, role-based access, retention enforcement or audit-grade centre governance.

**Upgrade response:** Data Manager Studio visibly reports this boundary, requests persistent browser storage only when staff choose it, stores attachment SHA-256 hashes, keeps a bounded audit trail and creates full backup files. The backup file itself is **not encrypted**; the UI directs staff to an approved encrypted or managed location.

## Awarding-body alignment approach

The app must support multiple live frameworks rather than hard-code one “awarding body form”. The included profiles configure prompts and fields only. Staff paste exact current wording from official centre-controlled documents.

### AQA Unit Award Scheme

The AQA workflow profile provides unit code/title, outcome code and exact wording, evidence-needed text, achieved date, educator confirmation and summary-sheet status. AQA’s official pages remain authoritative:

- https://www.aqa.org.uk/programmes/unit-award-scheme/about
- https://www.aqa.org.uk/programmes/unit-award-scheme/certification

The app deliberately distinguishes “ready for centre claim preparation” from “certified”.

### ASDAN Short Courses

The Short Course profile provides module/challenge references and prompts for supporting evidence, planning/review, achievement summary, skills development and personal statement. Course-specific current materials remain authoritative:

- https://www.asdan.org.uk/courses/expressive-arts-short-course/
- https://www.asdan.org.uk/living-independently-short-course/

### ASDAN Personal Effectiveness Qualifications

The PEQ profile records qualification size/level, unit/criterion, portfolio evidence, assessment decision and quality-assurance sample status. It recognises the six core skills but does not replace registration, assessment plans, specification documents or EQA processes:

- https://www.asdan.org.uk/news/personal-effectiveness-qualifications-launch-updates-training-and-free-resources/

### Arts Award

The Arts Award profile includes award level/part, criterion, evidence locator, adviser assessment and witness/observation details. The workflow highlights signed witness references where used and treats the current Arts Award witness-statement policy as authoritative:

- https://www.artsaward.org.uk/accessandinclusion

## What the proposed Data Manager does

### Learners and cohorts

- stable UUID-style internal learner IDs;
- optional centre learner ID;
- one learner can belong to several cohorts;
- bulk paste with centre-ID-first matching and normalised-name fallback;
- archive/restore rather than destructive delete;
- explicit publication to the shared roster.

### Programmes, units and criteria

- generic, AQA UAS, ASDAN Short Course, ASDAN PEQ and Arts Award workflow profiles;
- awarding body, qualification, level/size and specification/version fields;
- unit/module code, title and official source/version reference;
- criteria entered as `code | exact wording | evidence needed`;
- criterion identity preserved by code;
- a removed linked criterion is archived rather than discarded.

### Evidence register

- learner evidence, assessment-decision draft, witness/observation, lesson artefact, anonymous class check and administrative note;
- draft, review, ready, submitted, returned and archived states;
- learner(s), unit, criteria, date, assessor, decision, independence/support and witness fields;
- lesson ID/title/path and source-app context;
- local attachments with size, media type and SHA-256 hash;
- append-only record audit notes within a bounded suite audit list.

### Coverage and review

- learner-by-criterion matrix;
- linked-record count and strongest workflow status;
- explicit statement that a count is not achievement;
- review queue with missing-context checks;
- CSV learners, evidence index and coverage exports.

### Backup and restore

- full JSON backup including base64 attachment bytes;
- merge as the safe default;
- replace requires typed confirmation;
- preview shows record counts before any restore;
- current-backup revision indicator;
- browser-storage estimate and optional persistence request.

## Shared workflow bridge

The bridge uses these versioned local keys:

- `mbm.teacher.v1.context`
- `mbm.teacher.v1.rosters`
- `mbm.teacher.v1.outbox`

It remains compatible with `ps_coldcall_roster`.

It is injected only into the first reviewed integration set:

- Evidence Binder;
- Classroom Toolkit;
- Seating Plan Studio;
- Rubric Studio;
- Exit Ticket;
- Writing Frames Studio;
- Flashcards & Quiz;
- Graph & Data Studio;
- Whiteboard;
- PDF Studio;
- ChoreoStudio.

Automatic adapters are deliberately narrow:

- Classroom Toolkit and Seating Plan Studio can copy a shared roster;
- Rubric Studio can copy a roster and queue an assessment draft;
- Writing Frames can queue a writing artefact draft;
- Exit Ticket can queue an anonymous class-check draft;
- Quiz Studio can queue a diagnostic result draft.

Feelings Check-in and Regulation Station are both excluded by source patching **and** by a runtime deny-list. They receive no roster, context or evidence controls.

## Visual and accessibility direction

The new layer follows the existing Made by Matt visual language—navy, cream, mint and amber—without recolouring every app. It adds a consistent floating teacher-context control only where enabled.

Implemented accessibility contracts include:

- minimum 44-pixel buttons and interactive controls;
- visible focus styles;
- focus moved into dialogs and returned to the opening control;
- semantic labels and live status regions;
- no disabled page zoom;
- responsive tables and mobile layouts;
- non-colour status text and icons;
- `prefers-reduced-motion` handling;
- print rules that hide controls and retain report content.

## Test evidence

The pack currently passes:

- patcher contract test: dry-run, exact diff, backup, no-delete, conflict refusal, Evidence Binder safety and idempotence;
- verifier positive control: valid synthetic applied checkout accepted;
- verifier negative control: a teacher bridge deliberately injected into Feelings Check-in is rejected;
- static JSON and JavaScript syntax checks;
- **18 real Chromium checks** covering full teacher workflow, attachment hashing, backup, fresh-context restore, roster reuse, writing hand-off, wellbeing exclusion, Suite Health, mobile layout, 44-pixel controls and zero console/network errors.

Machine-readable browser results are in `reports/BROWSER_SMOKE_RESULTS.json`. Current screenshots are in `reports/data-manager-desktop.png` and `reports/data-manager-mobile.png`.

## Limits and recommended review

- The pack has not been committed, pushed, deployed or tested against the live external UAS/ASDAN tools.
- The framework profiles were checked against public official information on 5 August 2026, but the centre must confirm the exact current documents in use before deployment.
- Data Manager Studio is intentionally a single-file app to match this repository. A later maintainability PR may split modules only if the deployment contract remains zero-build and offline-first.
- The shared bridge is a foundation. The app-by-app roadmap should be delivered in small PRs with content-preservation and positive-control tests rather than one broad visual rewrite.
