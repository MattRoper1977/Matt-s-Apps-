# Read first — Matt’s Apps teacher upgrade pack

This is a **reviewable, non-destructive upgrade pack** for `MattRoper1977/Matt-s-Apps-`.

Nothing in the GitHub repository was changed while this pack was prepared. No file in the intended patch is deleted.

## What is ready

- a new, self-contained `Data_Manager_Studio.html`;
- a shared, additive teacher context / roster / draft-evidence layer;
- a versioned evidence JSON schema;
- editable AQA UAS, ASDAN Short Course, ASDAN PEQ and Arts Award workflow profiles;
- Evidence Binder safety fixes;
- hub, README and Suite Health corrections;
- an all-app recommendation matrix;
- a dry-run-first patch generator;
- static verification and positive-control tests;
- a real Chromium smoke test with desktop and mobile screenshots;
- a Claude Code master prompt for controlled application and draft PR creation.

## Fastest safe review

Read these files:

1. `AUDIT_REPORT.md`
2. `APP_UPGRADE_MATRIX.csv`
3. `PRIVACY_AND_AWARDING_BODY_GUARDRAILS.md`
4. `IMPLEMENTATION_ROADMAP.md`
5. `CLAUDE_CODE_MASTER_PROMPT.md`

Open the proposed app directly:

```text
proposed/Data_Manager_Studio.html
```

The app is designed for HTTP/static hosting. Some browser storage and download features may be restricted when opened as `file://`; use a local static server for testing:

```bash
cd proposed
python3 -m http.server 8000
```

Then open `http://127.0.0.1:8000/Data_Manager_Studio.html`.

## Generate an exact patch against Claude’s checkout

The installer is read-only unless `--apply` is supplied.

```bash
python tools/apply_teacher_upgrade.py /path/to/Matt-s-Apps- \
  --emit-diff patches/generated-against-checkout.patch
```

Review that patch. Then apply with automatic backup:

```bash
python tools/apply_teacher_upgrade.py /path/to/Matt-s-Apps- --apply
```

The installer:

- refuses an unfamiliar checkout;
- warns when an audited source blob has changed;
- can require the exact audited baseline with `--strict-baseline`;
- backs up every modified existing file to a timestamped sibling directory;
- writes atomically;
- adds/modifies only;
- refuses to overwrite an unfamiliar file at a proposed new-file path;
- is idempotent.

## Verify an applied checkout

```bash
python tools/verify_teacher_upgrade.py /path/to/Matt-s-Apps-
```

Run pack contract tests:

```bash
python tools/test_apply_teacher_upgrade.py
python tools/test_verify_teacher_upgrade.py
```

Run the browser smoke test where Chromium is allowed to load local HTTP pages:

```bash
python tests/browser_smoke.py --browser-executable /path/to/chromium
```

## Optional CI template

`.github/workflows/teacher-upgrade-contract.yml` is a template, not part of the automatic app patch. It assumes the review pack is retained in the target repository at `qa/teacher-upgrade/`. Copy the workflow to the repository `.github/workflows/` only when the team wants to retain the QA pack and browser evidence in the PR.

## Intended file operations

- **Add:** 5 files.
- **Modify:** 15 files.
- **Delete:** 0 files.

See `PATCH_PLAN.json` for the exact machine-readable list.

## Important boundary

The framework templates are not specifications or official forms. “Ready” is an internal centre workflow state, not certification, external moderation or quality assurance. Backups contain personal data and attachment bytes and are not encrypted by the app.
