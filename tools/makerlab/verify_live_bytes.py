#!/usr/bin/env python3
"""Prove the Maker Lab suite serves exactly the bytes that were merged.

Pages publishes asynchronously, so this waits: it re-fetches until every file
matches or the attempts run out, and reports the attempt it succeeded on. The
inventory is the payload manifest, not a list typed here — a file added to the
suite without a manifest record would otherwise be silently unproven.

Every request is cache-busted with the merge SHA and sent with no-store, so a
match cannot be a CDN copy of the previous deploy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MANIFEST = "_release-docs/teesside-maker-lab-pro-v2.1/PAYLOAD_MANIFEST.json"
RUNTIME_PREFIX = "Teesside_Maker_Lab_PRO/"
HEADERS = {
    "Cache-Control": "no-cache, no-store, max-age=0",
    "Pragma": "no-cache",
    "User-Agent": "MadeByMatt-MakerLab-Deploy-Proof/1",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> tuple[bytes, int, str]:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read(), response.status, response.headers.get("Content-Type", "")


def check(records: list[dict], base: str, sha: str, attempt: int) -> list[dict]:
    rows = []
    for record in records:
        url = urllib.parse.urljoin(base, record["path"])
        url += f"?source={urllib.parse.quote(sha)}&attempt={attempt}"
        try:
            body, status, ctype = fetch(url)
            served = sha256(body)
            html_ok = not record["path"].endswith(".html") or "text/html" in ctype.lower()
            rows.append({
                "path": record["path"],
                "url": url,
                "http": status,
                "content_type": ctype,
                "expected_sha256": record["sha256"],
                "served_sha256": served,
                "match": served == record["sha256"] and html_ok,
            })
        except Exception as error:  # noqa: BLE001 - any failure is a failed proof
            rows.append({"path": record["path"], "url": url, "match": False, "error": str(error)})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--base", required=True, help="published Apps root, e.g. https://.../Matt-s-Apps-/")
    parser.add_argument("--sha", required=True, help="merge commit being proven")
    parser.add_argument("--attempts", type=int, default=60)
    parser.add_argument("--sleep", type=float, default=10)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    manifest = json.loads((args.repo_root.resolve() / MANIFEST).read_text(encoding="utf-8"))
    records = [r for r in manifest["records"] if r["path"].startswith(RUNTIME_PREFIX)]
    if not records:
        raise SystemExit(f"no runtime records under {RUNTIME_PREFIX} in {MANIFEST}")

    base = args.base if args.base.endswith("/") else args.base + "/"
    rows: list[dict] = []
    attempt = 0
    passed = False
    for attempt in range(1, args.attempts + 1):
        rows = check(records, base, args.sha, attempt)
        if all(row["match"] for row in rows):
            passed = True
            break
        if attempt < args.attempts:
            time.sleep(args.sleep)

    report = {
        "status": "PASS" if passed else "FAIL",
        "base": base,
        "merge_sha": args.sha,
        "attempt": attempt,
        "files_proven": len(rows),
        "files": rows,
    }
    print(json.dumps(report, indent=2))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
