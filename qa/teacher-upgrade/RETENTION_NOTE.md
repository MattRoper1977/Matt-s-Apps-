# Retention note — QA pack for Pass TW-1

This directory retains the teacher upgrade QA pack so the checks and browser
evidence survive beyond the session that ran them. It is **QA only**. Nothing
here is served to pupils or loaded by any studio at runtime.

Retained after the Pass TW-1 merge (`main` at `298c4381982ef44e69f6b4f20b9dc015bb5ed96d`,
merging PR #3 no-ff per R-SEMH01).

## `proposed/` mirrors merged `main`, not the pack as shipped

This is load-bearing. `tools/apply_teacher_upgrade.py` treats `proposed/` as the
source of truth for the five upgrade-owned files. Those files were retained at
their **post-correction** state, byte-identical to what is on `main`.

Had the pack's original `proposed/` been retained instead, re-running the
installer against this repository would have tried to **revert** estate
corrections C1, C5 and C6. As retained, a re-run reports zero changed files.

Verify that at any time:

```bash
python qa/teacher-upgrade/tools/apply_teacher_upgrade.py .
# expect: 0 file(s) would change
```

`--strict-baseline` will now refuse, correctly: the source blobs have
legitimately moved on from the audited baseline
`c69895423ecaaf4fa859bd6fef6bc717d2a94863`. That refusal is the tool working,
not a fault.

## Two harness fixes, both disclosed in PR #3

Neither weakens a gate. Both are in `tests/browser_smoke.py`.

**1. The C5 fixture asserted the behaviour the estate ruling forbids.**
It selected the `aqa-uas` profile and typed the scheme's own name,
`"Unit Award Scheme"`, into the **Level / size** box — the exact confusion the
ruling corrects, since UAS records achievement and has no grade and no level.
The assertion was not deleted. It was replaced with a **stricter positive
control**, `UAS has no level (C5)`, which fails if the Level field is ever
editable or non-empty while the UAS profile is active.

**2. The fixture site served no `/hud.js`.**
Correction C1 gave Data Manager Studio the estate hud loader that all 28 other
studios already carry. `/hud.js` is served from the domain root and is not a
file in this repository, so the isolated fixture site 404ed and the
"no console errors" assertion failed against an environment that does not exist
in production. A stub is now written into the fixture site. The assertion itself
is untouched.

Because of fix 1 the harness reports **19 checks, not the pack's original 18**.

## MANIFEST.sha256 was regenerated

The shipped manifest covered the pack as published. `proposed/`,
`tests/browser_smoke.py` and `reports/` have all legitimately changed since,
so the manifest was regenerated over this retained tree and `sha256sum -c`
passes here. It no longer matches the original published pack, and it is no
longer evidence of the upstream download's integrity — that check was performed
and passed during Pass TW-1 against the original archive
(`8ee7c95f…711a9`).

The `.github/workflows/teacher-upgrade-contract.yml` entry is absent from the
regenerated manifest because the workflow lives at the repository's own
`.github/` path, not inside this directory.

## `reports/` holds measured evidence from this estate, not the pack's claims

`reports/BROWSER_SMOKE_RESULTS.json` is the run against the corrected files on
this branch: **19 passed, 0 failed**, Chromium at `/opt/pw-browsers/chromium`.
The pack's own 18/18 was independently reproduced before the corrections were
applied, rather than copied.

## Running it

```bash
cd qa/teacher-upgrade
python tools/test_apply_teacher_upgrade.py
python tools/test_verify_teacher_upgrade.py
python tools/verify_teacher_upgrade.py ../..
python tests/browser_smoke.py --browser-executable /path/to/chromium
```

The CI workflow is `workflow_dispatch` only — it never runs on push or on pull
request. Start it from the Actions tab.

## Still outstanding

- **Tools-hub card** for Data Manager Studio belongs in the main site repo
  (`tools/index.html`, utilities 11 → 12, ChoreoStudio precedent). Cross-repo,
  not done here.
- The estate **theme port** of the studios remains a separate parked pass.
  Correction C2 is a first-boot seed-read only.
