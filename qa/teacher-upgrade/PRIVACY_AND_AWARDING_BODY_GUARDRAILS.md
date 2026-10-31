# Privacy, safeguarding and awarding-body guardrails

These rules bind every proposed file and every future Claude Code change based on this pack.

## 1. Local-first does not mean risk-free

Browser storage is device-local, not automatically encrypted, backed up or access-controlled. Learner names, centre IDs, evidence notes, photographs, audio, video and exported backups must be handled under the centre’s approved systems and policies.

The app must never claim that local storage alone is “GDPR compliant”, “secure” or suitable for indefinite records retention.

## 2. No automatic upload

No app may send learner or evidence data to a server, analytics platform, AI endpoint, email service or cloud drive without a separately reviewed centre decision and explicit user action. No hidden telemetry or remote fonts are permitted.

## 3. Backup boundary

A Data Manager backup contains the local state and attachment bytes. It is **not encrypted by the app**. The interface must say this before download and direct staff to a school-approved encrypted or managed location.

Replace restore remains behind typed confirmation. Merge is the default.

## 4. Minimise identity

- Stable internal IDs are the linking key.
- Display names may change without breaking evidence.
- Centre learner IDs are optional.
- Date of birth, home address, personal email, medical data and safeguarding notes are not fields in this design.
- Duplicate display names must remain separable.
- Public-facing creative exports should not automatically embed learner IDs.

## 5. Archive, do not silently delete

Learners, programmes, units, criteria and evidence records use archive/restore states. A linked criterion or unit cannot disappear silently. A future hard-delete function would require a separate export, dependency report and typed confirmation.

## 6. Evidence is not achievement

A file, photograph, quiz result, rubric tick or evidence count does not by itself prove that an awarding-body outcome has been achieved.

The workflow separates:

- artifact captured;
- evidence linked;
- staff review;
- assessment decision;
- ready for centre process;
- submitted;
- externally certified or quality assured outside this app.

The app does not create the final external state.

## 7. Exact current wording

Built-in framework profiles configure fields and prompts only. They are not official forms or specifications. Staff must paste exact current wording from centre-controlled current documents and record the version/source used.

## 8. AQA Unit Award Scheme

Use the current AQA unit as the source of outcome wording and evidence needed. “Ready” means ready for the centre’s claim preparation. The trained centre role and AQA process remain outside the app.

Official sources checked 5 August 2026:

- https://www.aqa.org.uk/programmes/unit-award-scheme/about
- https://www.aqa.org.uk/programmes/unit-award-scheme/certification

## 9. ASDAN Short Courses

The selected student-book or Equitas delivery format/version must be recorded where content differs. Supporting evidence, planning/review records, achievement summary, skills development, personal statement and any course-specific tutor feedback remain governed by current ASDAN materials.

Official examples checked 5 August 2026:

- https://www.asdan.org.uk/courses/expressive-arts-short-course/
- https://www.asdan.org.uk/living-independently-short-course/

## 10. ASDAN Personal Effectiveness Qualifications

The app may support portfolio organisation and centre review. It does not replace registration, assessment planning, specification documents, internal quality assurance or external quality assurance.

Official source checked 5 August 2026:

- https://www.asdan.org.uk/news/personal-effectiveness-qualifications-launch-updates-training-and-free-resources/

## 11. Arts Award witness evidence

Where observation, scribing or a witness statement replaces evidence created by a young person, staff must follow the current formal policy and use the required signed form/reference. The app stores a reference; it does not manufacture a signature or form.

Official source checked 5 August 2026:

- https://www.artsaward.org.uk/accessandinclusion

## 12. Wellbeing firewall

Feelings Check-in and Regulation Station are deliberately outside the evidence system.

They must not receive:

- a shared roster;
- learner identity;
- teacher-context launcher;
- evidence hand-off;
- mood history;
- usage analytics;
- a hidden log.

The verifier contains a negative control that fails if the shared workflow is injected into either app.

## 13. Anonymous formative assessment

Exit Ticket remains anonymous by default. It may save an aggregate class-check draft and a teacher’s next teaching action. It must not silently become an individual attainment or behaviour record.

## 14. Generated text and scores are drafts

Rubric feedback, quiz results, writing-frame output and AI-assisted text in any future version remain drafts until reviewed. The app must preserve the learner’s original work, identify generated material and avoid presenting an automated score as an awarding-body decision.

## 15. Safeguarding and access

No app replaces safeguarding reporting, pastoral records, SEND plans, reasonable-adjustment processes or emergency procedures. Do not store safeguarding disclosures in evidence notes. Use the centre’s approved system.
