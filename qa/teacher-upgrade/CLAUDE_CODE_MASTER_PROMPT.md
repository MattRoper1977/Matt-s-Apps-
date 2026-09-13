# MASTER PROMPT — Matt’s Apps teacher workflow upgrade

**Sentinel:** `matts-apps-teacher-workflow-2026-08-05`  
**Repository:** `https://github.com/MattRoper1977/Matt-s-Apps-`  
**Audited branch/head:** `main` at `c69895423ecaaf4fa859bd6fef6bc717d2a94863`  
**Input pack:** `Matt-s-Apps-Teacher-Upgrade-Pack.zip`

You are acting as a chief front-end engineer, teacher-workflow designer, evidence-records engineer, accessibility specialist, privacy engineer, QA engineer and release engineer.

Your job is to review and apply this pack on a **new branch**, validate it against the real checkout, and open a **draft pull request**. Do not merge, deploy, delete files or push directly to `main`.

## 0. Standing rules

1. **No deletion.** Preserve every audited file. The intended change set is additions and bounded modifications only.
2. **No content invention.** Do not invent qualification criteria, lesson wording, assessment decisions, certificate states or official forms.
3. **Official documents remain authoritative.** Framework profiles are editable workflow prompts, not specifications.
4. **Evidence is not achievement.** Never convert a file, count, rubric tick or quiz score into an automatic pass/achievement/certification state.
5. **Local-first.** No analytics, accounts, telemetry, remote fonts, cloud sync or hidden upload.
6. **Wellbeing firewall.** Do not inject any roster/context/evidence layer into `Feelings_Checkin.html` or `Regulation_Station.html`.
7. **No gate contamination.** Do not weaken a test because the implementation fails it. Fix the implementation.
8. **No competing implementation.** Use one Data Manager file and one versioned shared workflow layer. Do not create duplicate “v2-final-new” alternatives.
9. **Preserve compatibility.** Existing app data, exports and direct links must continue to work unless a migration is explicitly tested and documented.
10. **Truthful closeout.** Do not claim browser, mobile, print, deployment or live URL success unless measured.

## 1. Establish the real baseline

Before changing anything:

```bash
git status --short --branch
git remote -v
git rev-parse HEAD
git ls-tree -r --name-only HEAD
```

Compare the tree with `BASELINE_MANIFEST.json`.

- If HEAD is the audited commit, run the installer with `--strict-baseline`.
- If HEAD has moved, do not force the old patch. Run a normal dry-run, inspect every source warning and confirm that all patch anchors still describe the real code.
- If the Evidence Binder safety anchors are absent, stop that file’s automatic patch and implement the same invariant manually with tests. Do not use a broad regex guess.

Create a branch such as:

```bash
git switch -c feat/teacher-workflow-data-manager
```

## 2. Inspect the pack before applying

Read, in order:

1. `README-FIRST.md`
2. `AUDIT_REPORT.md`
3. `PRIVACY_AND_AWARDING_BODY_GUARDRAILS.md`
4. `IMPLEMENTATION_ROADMAP.md`
5. `PATCH_PLAN.json`
6. `APP_UPGRADE_MATRIX.csv`

Validate pack files:

```bash
sha256sum -c MANIFEST.sha256
python -m json.tool proposed/evidence-schema-v2.json >/dev/null
python -m json.tool proposed/awarding-body-templates.json >/dev/null
node --check proposed/teacher-workflow.js
python tools/test_apply_teacher_upgrade.py
python tools/test_verify_teacher_upgrade.py
```

Do not continue if the pack checksum or contract tests fail.

## 3. Generate the exact diff first

From the unpacked pack:

```bash
python tools/apply_teacher_upgrade.py /path/to/Matt-s-Apps- \
  --emit-diff patches/generated-against-checkout.patch \
  --json > reports/patch-dry-run.json
```

Review the generated diff. It should plan:

### Five additions

- `Data_Manager_Studio.html`
- `teacher-workflow.js`
- `teacher-workflow.css`
- `evidence-schema-v2.json`
- `awarding-body-templates.json`

### Fifteen bounded modifications

- eleven reviewed app HTML files for the shared workflow layer;
- `apps.json`;
- `index.html`;
- `README.md`;
- `suite-health.html`.

### Zero deletions

The dry-run must make no repository write.

## 4. Apply with backup

Only after diff review:

```bash
python tools/apply_teacher_upgrade.py /path/to/Matt-s-Apps- --apply --json \
  > reports/patch-apply.json
```

The command must report a timestamped sibling backup. Confirm:

- every file listed as modified exists in the backup;
- all original 34 artefacts remain in the checkout;
- all five new files exist;
- the second installer run reports zero changed files.

```bash
python tools/apply_teacher_upgrade.py /path/to/Matt-s-Apps- --apply --json \
  > reports/patch-idempotence.json
```

## 5. Required implementation invariants

### Evidence Binder

- Reordering unchanged outcome lines preserves their IDs by wording.
- A deliberate same-position wording edit preserves the intended ID.
- Duplicate outcome lines are rejected.
- A linked outcome cannot be removed silently.
- A unit with linked evidence cannot be deleted.
- Existing Binder storage, backup, restore and PDF output remain usable.

### Data Manager Studio

- Stable learner IDs survive display-name edits.
- Archive/restore replaces destructive deletion.
- Criteria preserve identity by code.
- Removed linked criteria are archived.
- Evidence starts as a draft unless staff explicitly choose another internal workflow state.
- “Ready” is described as ready for the centre process, not certified.
- Attachments remain local and receive SHA-256 metadata.
- Full backup includes attachment bytes.
- Merge restore is the default; replace requires `REPLACE LOCAL DATA`.
- Backup files are visibly described as not encrypted.

### Shared workflow

- Uses `mbm.teacher.v1.context`, `mbm.teacher.v1.rosters` and `mbm.teacher.v1.outbox`.
- Retains compatibility with `ps_coldcall_roster`.
- Roster transfer is explicit, never automatic.
- Hand-offs are small draft records and never upload files.
- Writing Frames, Rubric, Exit Ticket and Quiz adapters retain their privacy/assessment distinctions.
- Feelings Check-in and Regulation Station remain excluded even if the script were accidentally loaded.

### Hub and Suite Health

- No manual 23/28 tool claim remains.
- Data Manager appears once in Teacher tools.
- Local catalogue targets exist.
- Suite Health reads `apps.json` and fails on an empty catalogue.
- External targets are labelled informational rather than producing false local failures.

## 6. Verification

Run:

```bash
python /path/to/pack/tools/verify_teacher_upgrade.py /path/to/Matt-s-Apps-
```

Zero failures are required.

Run the real-browser smoke test in an environment where local HTTP pages are permitted:

```bash
python /path/to/pack/tests/browser_smoke.py --browser-executable /path/to/chromium
```

The supplied pack baseline passed 18 checks. Your run must independently pass, not copy that claim.

Then manually verify, with fictional data only:

1. existing Evidence Binder opens and restores a legacy backup;
2. unit outcome reorder keeps evidence tags;
3. linked outcome/unit deletion is blocked;
4. cohort creation and bulk learner import;
5. Data Manager programme/unit/criteria setup;
6. evidence record with an image and a document;
7. coverage matrix and CSV exports;
8. full backup, reload and fresh-browser restore;
9. Classroom Toolkit and Seating roster transfer;
10. Rubric/Writing/Quiz/Exit hand-offs import as drafts;
11. Feelings Check-in and Regulation Station show no bridge;
12. desktop, 390px mobile, keyboard-only, reduced-motion and print layouts;
13. zero console errors and failed local requests.

### Optional retained QA assets

The installer adds only runtime files and bounded source modifications. If the project wants the checks retained in-repository, place this pack at `qa/teacher-upgrade/` and copy `.github/workflows/teacher-upgrade-contract.yml` to the repository workflow directory. Record that extra QA-only addition in the PR file count; do not pretend it was part of the five runtime additions.

## 7. Accessibility gates

For changed interfaces:

- no control under 44×44 CSS pixels where it is intended for touch;
- visible keyboard focus;
- dialog focus enters and returns correctly;
- Escape/close works;
- zoom is not disabled;
- status is not communicated by colour alone;
- live messages do not steal focus;
- horizontal page overflow is zero at 390px;
- reduced motion removes non-essential movement;
- print hides controls but preserves report meaning.

Use automated checks as support, not a substitute for keyboard and screen-reader inspection.

## 8. Privacy review

In the PR body, answer explicitly:

- What personal data can each new/changed feature store?
- Where is it stored?
- What leaves the browser? Expected answer for this PR: nothing automatically.
- Is the backup encrypted? Expected answer: no.
- What is the recovery/retention advice?
- Which tools are deliberately excluded and why?
- Which status names are internal workflow states rather than awarding-body states?

## 9. Commit and draft PR

Use intentional commits, for example:

```text
feat: add local teacher data manager and evidence schema
fix: preserve Evidence Binder outcome links
feat: add explicit roster and evidence hand-offs
fix: make suite health catalogue-driven
chore: add teacher workflow verification evidence
```

Open a **draft PR**. Include:

- audited source head and actual branch base;
- exact added/modified/deleted counts;
- backup path created during application, without committing the backup;
- commands and measured results;
- screenshots from the actual branch;
- migration/rollback notes;
- privacy and awarding-body boundaries;
- known limits;
- statement that no live deployment was claimed.

## 10. Stop conditions

Do not merge or close the task as complete when any of these is true:

- a baseline file disappeared;
- an unfamiliar file would be overwritten;
- Evidence Binder tags move after reordering;
- a wellbeing tool receives the shared bridge;
- a backup cannot restore attachment bytes;
- mobile overflow remains;
- a control is inaccessible by keyboard;
- Suite Health can pass an empty catalogue;
- a generated result is described as certified/awarded;
- tests were skipped or inferred;
- the public deployment was not actually checked.

Record the exact blocker and leave the draft PR unmerged.
