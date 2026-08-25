#!/usr/bin/env python3
"""The Apps repo's cheapest real invariant (Order TS §2.2, decision D6).

Three limbs, every number with its unit and universe:
  1. apps.json parses and its spaces/items are non-empty — an empty or
     unparseable catalogue is MEASUREMENT INVALID (exit 2), never a pass.
  2. Every catalogue item's file (`f`) exists in this tree — the route census.
  3. Every served .html in the tree parses (html.parser) — a parser crash is
     a failure, not a skip.

Exit 0 all green · 1 a limb failed · 2 the measurement itself is invalid.
"""
import html.parser
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []

# 1 — catalogue parses
try:
    d = json.load(open(os.path.join(ROOT, "apps.json")))
except Exception as e:  # noqa: BLE001
    print(f"FAIL: apps.json does not parse: {e}")
    sys.exit(1)
items = [it for sp in d.get("spaces", []) for it in sp.get("items", [])]
if not items:
    print("MEASUREMENT INVALID: apps.json has no items "
          "(unit: item; universe: spaces[].items[])")
    sys.exit(2)
print(f"catalogue parses: {len(items)} items across {len(d.get('spaces', []))} spaces "
      f"(unit: item; universe: apps.json)")

# 2 — route census. An `f` that is an absolute estate URL points at another
# repo's serve (the site) — declared and counted, not verifiable from this
# tree, and NOT silently dropped: the count prints so a drift shows up.
local = [it for it in items if it.get("f") and not it["f"].startswith(("http://", "https://"))]
cross = [it["f"] for it in items if it.get("f", "").startswith(("http://", "https://"))]
missing = [it["f"] for it in local if not os.path.isfile(os.path.join(ROOT, it["f"]))]
if missing:
    fails.append(f"{len(missing)} catalogue item file(s) missing from the tree: {missing[:10]}")
else:
    print(f"route census: {len(local)}/{len(local)} local item files exist; "
          f"{len(cross)} cross-estate URL items declared, not verifiable from this tree: {cross}")

# 3 — every served .html parses
class P(html.parser.HTMLParser):
    pass

count = bad = 0
for dp, dns, fns in os.walk(ROOT):
    dns[:] = [x for x in dns if x not in (".git", "node_modules", "_attic")]
    for fn in fns:
        if not fn.endswith(".html"):
            continue
        count += 1
        p = os.path.join(dp, fn)
        try:
            pr = P(convert_charrefs=True)
            pr.feed(open(p, encoding="utf-8", errors="replace").read())
            pr.close()
        except Exception as e:  # noqa: BLE001
            bad += 1
            fails.append(f"html.parser crash in {os.path.relpath(p, ROOT)}: {str(e)[:120]}")
if count == 0:
    print("MEASUREMENT INVALID: zero .html files walked — the universe is empty")
    sys.exit(2)
print(f"structural parse: {count - bad}/{count} served .html files parse "
      f"(unit: file; universe: tracked tree minus .git/node_modules/_attic)")

if fails:
    for f in fails:
        print("FAIL:", f)
    sys.exit(1)
print("all three limbs green")
