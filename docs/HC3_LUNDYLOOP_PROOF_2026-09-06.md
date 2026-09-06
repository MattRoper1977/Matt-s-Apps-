# HC3 LundyLoop publication proof repair

Measured failure: Apps publication 34057674086 succeeded at 7d95a4425873f7239d0c0b8b7d3e22eac538d206, but live verifier 34057673750 compared raw source HTML with built adult pages. The pinned builder adds the approved 324-byte support treatment to four files. Exact reconstruction reproduced all four live hashes; five remaining payloads match raw bytes.

Repair plan: retain raw source-manifest checks, retrieve the successful publication artifact bound to this exact Apps source and deploy attempt through the existing pinned Site provenance helper, and compare complete live bytes. Missing or mismatched publication is inconclusive. Redirects, wrong MIME types and changed bytes fail. No application content or support policy changes.

Rollback: 7d95a4425873f7239d0c0b8b7d3e22eac538d206. Real/planted-byte/restored controls plus source, source-SHA, artifact and redirect rejection controls. Applicable PR gates must pass. Postmerge proof must bind the new Apps SHA and publication artifact; browser workflow remains required.
