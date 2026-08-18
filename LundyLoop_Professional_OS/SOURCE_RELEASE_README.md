# LundyLoop Pro — Participation & Influence Operating System

**Release:** v2 professional prototype suite  
**Build date:** 15 August 2026  
**Format:** offline-first, zero-dependency HTML applications

LundyLoop Pro turns pupil participation from a one-off consultation into a visible organisational workflow:

> **Safe Space → Voice Fidelity → Accountable Audience → Decision → Feedback Returned → Pupil Review**

The flagship treats every unanswered promise as **participation debt owned by adults and systems**, not as a deficit in the pupil. A loop does not close merely because somebody listened, held a vote or recorded a decision. It closes only after a specific response has returned to the learner and they have had a genuine chance to review or reopen it.

## Open the suite

Start with:

- `LundyLoop_PRO_LAUNCHER.html` or `index.html` — suite launcher
- `LundyLoop_PRO_Participation_Operating_System.html` — flagship operational system

The four focused pupil tools remain in `pupil_tools/`.

## Flagship workspaces

### 1. Dashboard

Shows open organisational obligations, overdue adult actions, decisions not yet returned, pupil reviews due, recent cases, workflow bottlenecks and live process-integrity warnings.

The **Participation Debt** dial deliberately counts adult/system responses still owed. It is not a pupil score.

### 2. Pupil Capture

Provides an alias-first, voluntary capture kiosk with:

- calm-space choices;
- typed, exact-scribed, symbol/phrase-tile and optional local-audio routes;
- “not now” and stop-without-saving routes;
- a clear safety exit;
- a live pupil-readable loop receipt.

Audio, where the browser supports it, is stored locally and is never automatically transcribed.

### 3. Route & Promise

Adds the professional mechanics that ordinary suggestion forms omit:

- **Decision Envelope:** Open, Limited or Fixed;
- **Voice Fidelity Twin:** exact pupil words remain separate from adult interpretation;
- corrections create a new voice version rather than replacing earlier wording;
- named accountable audience and owner;
- escalation role, due date, return route and explicit promise;
- safeguarding bypass and optional local redaction.

### 4. Decision Desk

Requires the decision-maker to acknowledge the view, record the evidence considered, identify the outcome and explain the action, reason or Plan B.

A **Trial Licence** supports reversible, time-limited change with a review date and success measure. This is useful where a permanent “yes/no” decision would be premature.

### 5. Return & Review

Builds feedback using the 4F lens:

- **Full** — specific view, decision, reasons and next steps;
- **Friendly** — accessible and accurate;
- **Fast** — tied to a promised return date;
- **Followed-up** — named person and review date.

The pupil separately records:

1. whether they felt listened to; and
2. whether the outcome helped.

They can disagree with the outcome, request a different Plan B or reopen the loop without erasing the earlier cycle.

### 6. QA & Audit

Audits the participation process rather than grading pupils. It includes:

- Lundy and participation-requirement matrix;
- audience-concentration and communication-route lenses;
- overdue-promise and unreturned-feedback signals;
- retention queue;
- tamper-evident SHA-256 audit-event chains;
- redacted CSV export;
- printable QA report;
- case timeline inspection.

### 7. Settings, backup and retention

Includes configurable response routes, accessibility modes, privacy shield, presentation blur, retention dates, expired-record purge, plain backup/import and optional encrypted backup using Web Crypto where available.

## Quick start

1. Open the launcher and choose **Open the flagship operating system**.
2. Select **Load demo** and confirm **Replace with demo**.
3. Use the Dashboard priority queue to inspect fictional loops at different stages.
4. Open **Pupil Capture** and create a new loop using an alias.
5. Route it to an accountable audience, record a decision, return feedback and invite a pupil review.
6. Open **QA & Audit** to inspect the workflow and verify the audit chain.
7. Delete the fictional data or close the browser session when finished.

## Storage model

The preferred store is browser **IndexedDB**. If unavailable, the application falls back to local browser storage; in highly restricted or automated environments it can use an in-memory session fallback.

This is not shared cloud storage. Data does not automatically move between devices or browser profiles.

## Professional boundary

This suite is a prototype workflow and evidence aid. It is **not**:

- a safeguarding record;
- a secure MIS or case-management platform;
- a substitute for organisational policy, staff judgement, lawful-basis decisions, a DPIA or data-protection advice;
- a mechanism for diagnosing pupils or automatically deciding whether a request should be accepted;
- proof that browser data is immutable.

Use aliases, collect only what is needed, protect exported files and transfer records requiring formal retention into an approved organisational system.

## Browser guidance

Use a current version of Chrome, Edge, Firefox or Safari. Core functions have no network dependency. Local audio, Web Crypto, speech synthesis, IndexedDB and printing depend on the browser, device permissions and organisational policy.

## Included files

- `LundyLoop_PRO_LAUNCHER.html`
- `index.html`
- `LundyLoop_PRO_Participation_Operating_System.html`
- `PROFESSIONAL_IMPLEMENTATION_GUIDE.md`
- `DATA_PROTECTION_AND_SAFEGUARDING_BOUNDARIES.md`
- `SOURCE_NOTES.md`
- `VERIFICATION_REPORT.md`
- `RELEASE_MANIFEST.json`
- `pupil_tools/` — four focused pupil-facing applications
- `qa/` — screenshots, test outputs and visual QA montage

## Attribution

Professional prototype suite developed for Matt Roper under the **Made by Matt** label. The Lundy model remains the work of Professor Laura Lundy; source and boundary notes are provided separately.
