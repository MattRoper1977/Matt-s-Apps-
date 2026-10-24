# Static and contract test results

**Run date:** 5 August 2026  
**Repository writes:** none  
**Pack location tested:** `/mnt/data/Matt-s-Apps-Teacher-Upgrade-Pack`

## Pack checks

Command:

```bash
python tools/run_all_checks.py
```

Result: **17 passed, 0 failed**.

The 17 checks covered:

- Python compilation for all five tool modules and the browser smoke module;
- JSON parsing for the baseline manifest, patch plan, evidence schema, awarding-body templates, audit evidence and browser report;
- Node syntax for `teacher-workflow.js`;
- Node syntax for the inline Data Manager script;
- Node syntax for the inline Suite Health v2 script;
- patcher dry-run/apply/backup/no-delete/conflict/idempotence contract;
- verifier valid-checkout positive control and wellbeing-boundary negative control.

Machine-readable output: `PACK_CHECK_RESULTS.json`.

## Real Chromium checks

Command used in this controlled environment:

```bash
python tests/browser_smoke.py --browser-executable /usr/bin/chromium
```

Result: **18 passed, 0 failed**.

Measured checks:

1. Data Manager dashboard boots.
2. Dialog focus enters the first field.
3. Dialog focus returns to the trigger.
4. Two learners bulk-import with stable records.
5. Shared roster publishes with both learners.
6. AQA UAS-style programme and two coded criteria save.
7. Evidence record saves with one attachment and SHA-256 metadata.
8. Coverage matrix renders two learners by two criteria.
9. Full backup contains learner, evidence, attachment metadata and attachment bytes.
10. Minimum visible button height is 44.0px.
11. IndexedDB state survives reload.
12. Classroom Toolkit fixture receives the shared roster.
13. Writing Frames fixture queues a draft hand-off without an automatic assessment decision.
14. Feelings Check-in fixture receives no launcher or hand-off.
15. Suite Health v2 reports zero failures and treats the external fixture as informational.
16. A clean browser context restores learners, evidence and attachment blob from the backup.
17. 390px mobile layout has zero horizontal overflow and 44.0px minimum buttons.
18. There are no console errors, page errors or failed requests.

Machine-readable output: `BROWSER_SMOKE_RESULTS.json`.

## Screenshots

- `data-manager-desktop.png`
- `data-manager-mobile.png`

## Important limit

These tests use an isolated static fixture site. Claude Code must rerun the verifier and browser/manual gates against the actual branch after applying the patch. Existing app-specific behaviours—especially Evidence Binder legacy backup/restore and portfolio printing—must be regression-tested with fictional data before merge.
