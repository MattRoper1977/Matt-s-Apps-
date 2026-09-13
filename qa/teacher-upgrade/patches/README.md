# Patch output directory

The repository patch is generated from the **real checkout** rather than shipping a brittle precomputed diff.

Dry-run and emit the exact unified diff:

```bash
python ../tools/apply_teacher_upgrade.py /path/to/Matt-s-Apps- \
  --emit-diff generated-against-checkout.patch
```

The default command writes only the patch file you requested. It does not modify the checkout.

Apply only after review:

```bash
python ../tools/apply_teacher_upgrade.py /path/to/Matt-s-Apps- --apply
```

The generated patch should contain five additions, fifteen modifications and no deletion headers. The installer also creates a timestamped sibling backup before it writes any existing file.

`EVIDENCE_BINDER_SAFETY_PATCH.md` explains the two highest-risk invariants in human-readable form.
