# Production adaptations

The source release is retained byte-for-byte in the deployment package under `source_release/`.

The deployable browser files make these estate adaptations (r3, 2026-08-18):

1. the root flagship adds links to the Apps hub and complete suite;
2. the suite launcher adds canonical metadata and an Apps-hub return route;
3. the suite flagship adds Suite Home and All Apps routes;
4. each focused pupil tool adds one large Suite Home control;
5. the deployment README accurately describes the reduced public QA set;
6. **v2.1 defect patches to both flagship copies** (see `PATCH_NOTES_v2.1.md`, incl. v2.1.1 P9): PBKDF2 600,000 iterations with header-aware decrypt; CSV formula-injection guard; presentation blur no longer un-blurs on hover/focus; pupil-review actor is chosen, not hard-coded, and a staff-recorded review does not close the loop; Pupil-mode device lock (capture only, press-and-hold exit); import warns when audio cannot be restored; honest "pseudonymised" CSV wording; v2.1 marker in the sub-brand line.

No storage key, safeguarding-transfer, evidence-schema, participation-debt or decision logic was otherwise rewritten. Existing v2.0 encrypted backups still open (decrypt reads the pack's `iterations`, defaulting to 250,000). No external runtime dependency was added.
