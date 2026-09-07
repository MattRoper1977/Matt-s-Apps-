# Publication-ordered Apps live proof

The Apps LundyLoop live check starts before Education Pages publication finishes. Run 34080015345 attempt 1 exhausted its 240-second artifact retrieval bound; attempt 2 passed all nine exact byte checks after deployment. Trigger live proof from successful same-repository main publication completion, retain PR/push fixtures and all byte/provenance checks, and select the upstream source SHA. Mirror reviewed CI digests in Apps and Lessons.

Rollback before implementation: Matt-s-Apps- main 753baf41f65370f20ef69a4f87999c7f491ce7df; Apps main 753baf41f65370f20ef69a4f87999c7f491ce7df; Lessons main f37fc7414555f0dcb3e70370f957ee63e615ed25.

Firing controls: real workflow contract PASS; one planted push-before-publication live condition FAIL; restored PASS. Check upstream SHA A independently of current HEAD B, unsuccessful/foreign/non-main upstream exclusion, and retained PR/push fixture gates. Existing payload byte controls remain intact.

Served-proof plan: all applicable PR checks green, expected-head merge, Education Pages deploy at the merged source, then workflow_run verification using that source and all nine live byte rows. No branch deletion. This plan-only draft precedes implementation.

Checkpoint 2026-09-07 04:16 UTC: HELD, plan only. The workspace execution service became unavailable before any scheduling implementation or tests. No scheduling behavior or CI digest has changed. The controls above are the required future proof plan, not completed results. Existing deployed releases are preserved. Resume with working execution, verify ownership, implement and prove the paired change before resolving this hold.
