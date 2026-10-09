# Evidence Binder safety patch — review note

This change is intentionally small. It does not replace Evidence Binder, change its IndexedDB name, remove existing records, alter the PDF portfolio format or migrate current backups.

## Problem 1 — positional outcome identity

Current behaviour assigns an edited outcome line the ID previously held at the same array index. Reordering lines can therefore leave evidence attached to an ID whose displayed wording has changed.

## Patched invariant

When a unit is saved:

1. Normalise current and new wording by trim + lowercase.
2. Reject duplicate new lines because they cannot be identified unambiguously.
3. Reuse an old ID when the same wording exists, regardless of its new position.
4. Use the old ID at the same position only when the wording is genuinely being edited and that ID has not already been reused.
5. Generate an ID only for a new outcome.
6. Build the set of outcome IDs currently referenced by evidence items.
7. Refuse the save if a referenced old ID would disappear.

Marker inserted once:

```text
mbm-outcome-id-safety:v1
```

## Problem 2 — unit deletion orphans evidence context

Current behaviour allows deletion of a unit with linked evidence after warning that its evidence remains but loses unit tags.

## Patched invariant

- Count linked evidence items.
- When count is non-zero, show a clear message and stop.
- Permit deletion only for an empty unit after confirmation.

Marker inserted once:

```text
mbm-unit-delete-safety:v1
```

## Required regression fixtures

- unchanged outcome list;
- reordered outcomes;
- wording edit at the same position;
- new outcome inserted at the beginning;
- duplicate outcome wording;
- attempt to remove an unlinked outcome;
- attempt to remove a linked outcome;
- delete empty unit;
- delete unit with one linked item;
- delete unit with several linked items;
- legacy backup restore before and after patch;
- portfolio output with pre-patch evidence.

The patcher refuses automatic Evidence Binder modification when the audited anchors are absent. Claude Code must then inspect the actual file and implement these invariants manually rather than broaden the regex.
