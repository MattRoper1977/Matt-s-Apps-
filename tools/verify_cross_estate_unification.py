#!/usr/bin/env python3
"""Verify the Made by Matt Lessons/Apps cross-estate hub contract.

Sentinel: mbm-cross-estate-unification-lessons-apps-2026-08-08
The verifier is intentionally narrow: it protects the common platform shell,
Matt's existing hub wording/logo, URL casing, local/offline shell assets and the
fact that no standalone lesson or studio is changed by this release.
"""
from __future__ import annotations

import argparse
import hashlib
import html as html_module
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

SENTINEL = "mbm-cross-estate-unification-lessons-apps-2026-08-08"
# These pin the bytes THIS repository serves. They are not the cross-estate
# check — that is the --canonical comparison below, which holds these same two
# files against the site repository byte for byte. The distinction is the whole
# reason this table moved in both repositories within one day: the pins cannot
# detect divergence, because each copy of this gate pins its own local bytes and
# is green about them. Three versions coexisted, every pin green — Lessons
# ccfb0fd9/0841046b, Apps e3eb9b83/0958a73a, site b520cf36/095a29e6.
#
# This file is byte-identical in Lessons and Apps, which tools/pin_manifests.py
# documents and asserts after any re-pin. It had stopped being so: the two
# copies pinned different platform digests, and that assertion would have fired
# on the next deliberate manifest change with a message about the wrong thing.
# Both repositories now serve the same canonical bytes, so the table is the same
# in both and this comment can be too. Keep it that way — if the copies ever
# need to disagree, pin_manifests.py needs to learn that first.
#
# How the drift survived, with dates. 2026-08-13 (91a16b8) brought Lessons to
# the canonical copy and pinned ccfb0fd9 / 0841046b. The site then moved twice —
# 6bdeafa on 08-14 and bc67b82 on 08-15 — and nothing in either repository
# changed at either moment, so no path filter fired and both gates stayed green
# behind. The schedule that would have noticed is what theme-parity.yml already
# has, and what this workflow gained in the same pass as this comment.
#
# What 6bdeafa was matters. It inverted adultFeaturesAllowed() to fail closed:
# the account link, the create-account link, the mailing link and the footer
# mailing CTA now need a page to say data-mbm-adult-features="on", where before
# they appeared unless a page said "off". In both repositories index.html is the
# only page that loads mbm-platform.js, and neither declares the marker, so the
# two copies were affected differently and both were measured in Chromium:
#
#   Lessons  before  1440x900 acct=1 mail=2 register=1, mbm-account.js x2
#                     390x844 acct=0 mail=1 register=0, mbm-account.js x2
#            after   0/0/0/0 at both, details 12/14, cards 504, aria-live 2,
#                    pageerrors 0, 404s 0 unchanged
#   Apps     before  0/0/0/0 at both viewports already — the fail-closed reader
#            after   had reached that copy, so the sync changed no metric there
CANONICAL_HASHES = {
    "assets/mbm-platform.css": "b520cf36a9c87af618e03ea534b66c261e8fd05e70d8eb5634f323aee9310698",
    "assets/mbm-platform.js": "095a29e61f8d7d549a5b58dd1aa1dd74b885416ebb09291ddb218d90ea740c28",
    "assets/mbm-theme.js": "5d711139ee95f2a9814917c516ffe674fbd52fd0b42c8fd6e22a1efbc19f002b",
    "assets/mbm-hub.css": "1643f51bcfe7f89923e908cf4f79b36a80d8bfa767779ab1c9cebe2e1a8b513c",
}

# assets/mbm-theme.js is not maintained here. It is generated from the site
# repository's theme.js by tools/sync_theme.py, and is that file verbatim with
# one header line in front. The checks below assert that exact concatenation
# rather than plain byte-identity: equally strict — a byte either side of the
# header still fails — but it lets the copy carry, at the top of itself, the
# notice telling the next person where to edit and what to run.
THEME_COPY = "assets/mbm-theme.js"
GENERATED_HEADER = (
    "/* GENERATED from madebymatt.github.io/theme.js — edit there, run "
    "tools/sync_theme.py. Hand edits will be reverted. */\n"
).encode("utf-8")
SYNC_COMMAND = "python3 tools/sync_theme.py   (in the mattroper1977.github.io checkout)"

PRIMARY_ROUTES = ["/games/", "/Lessons/", "/Matt-s-Apps-/", "/tools/", "/resources/"]
MORE_ROUTES = ["/stats/", "/members/", "/#about", "/privacy/"]
# apps.json is no longer forbidden from changing — it is PINNED.
#
# The old rule was "the source manifest must not change at all". That made adding
# a studio impossible: a studio add IS an apps.json edit, and it also touches
# index.html (AUDMAP + the no-JS lead count), which puts this workflow's path
# filter in play — so the gate fired and refused. A guardrail that forbids the
# repository's ordinary business is not protecting anything.
#
# Retiring the protection outright was the alternative, and it was rejected:
# apps.json would have become silently unguarded. Instead it follows the pattern
# the shared assets here already use and that tools/sync_theme.py established — a
# pinned digest that a TOOL moves in the same run as the deliberate change. Add a
# studio, run tools/pin_apps_manifest.py, and the pin moves in the same commit as
# the manifest: visible in the diff, reviewable, deliberate. Edit apps.json
# without running it and this goes red.
#
# resources.json keeps the blanket rule. Only apps.json was ruled on.
MANIFEST_PINS = {
    "apps.json": "a4a06b999b5f16d19f0a4a87952ea1fe53f4fcbe2c38bc702c51ba89140a6047",
    # Ruled onto the pin 2026-08-12 (Ruling 3): the deck install is a
    # resources.json edit, and the blanket rule forbade it the same way it
    # once forbade studio adds. Same pattern, same tool, same commit rule.
    "resources.json": "e6fc5bfc11a231b9fdba2e3cea21a9ffc49bd98b7f7113db62d8868b489e439c",
}
PIN_COMMAND = "python3 tools/pin_manifests.py   (from either checkout — it writes both gate copies or neither)"

ALLOWED_DIFF = {
    "index.html",
    "apps.json",
    # Guarded by digest, not prohibition — the resources.json half of the same
    # ruling that pinned apps.json. The pin check above is what makes an edit
    # here deliberate-or-red; this entry only stops the boundary check from
    # forbidding the repository's ordinary business outright.
    "resources.json",
    "assets/mbm-platform.css",
    "assets/mbm-platform.js",
    "assets/mbm-theme.js",
    "assets/mbm-hub.css",
    "tools/verify_cross_estate_unification.py",
    "tools/verify_cross_estate_browser.mjs",
    # Git metadata, not a served file. It declares which payload docs carry
    # Markdown hard line breaks so the static-contract whitespace check stops
    # reading them as stray spaces. The first payload to need that ADDED the
    # file, which --diff-filter=MRD ignores; the second MODIFIES it, and a
    # boundary that reds on it would forbid the ordinary business of installing
    # a second bytes-unaltered payload. It cannot change a studio's bytes.
    ".gitattributes",
    ".github/workflows/mbm-cross-estate-unification.yml",
    "docs/MBM_CROSS_ESTATE_UNIFICATION.md",
    # renamed to pin_manifests.py under Ruling 3; the old entry stays so the
    # rename's deletion remains legal in any historical diff span.
    "tools/pin_apps_manifest.py",
    "tools/pin_manifests.py",
    # The pass ledger. It exists to change on every pass — a boundary that reds
    # on the ledger guarantees false failures on exactly the well-behaved passes
    # that record their work. Ruled onto the list 2026-08-12 (Ruling 6). The
    # entry is harmless in the Apps copy, where no such file exists.
    "_teachgreen/DECISIONS.md",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def detect_kind(root: Path) -> str:
    if (root / "resources.json").is_file():
        return "lessons"
    if (root / "apps.json").is_file():
        return "apps"
    raise ValueError("Could not detect Lessons or Apps repository")


def extract(regex: str, text: str, label: str, errors: list[str], flags: int = re.S | re.I) -> str:
    match = re.search(regex, text, flags)
    if not match:
        errors.append(f"missing {label}")
        return ""
    return match.group(1)


def normalized_visible_body(text: str, kind: str) -> str:
    body = re.search(r"<body\b[^>]*>(.*)</body>", text, re.S | re.I)
    value = body.group(1) if body else text
    for tag in ("header", "script", "style", "noscript"):
        value = re.sub(fr"<{tag}\b.*?</{tag}>", " ", value, flags=re.S | re.I)
    value = re.sub(r"<!--.*?-->", " ", value, flags=re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html_module.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    if kind == "apps":
        value = re.sub(
            # Normalised OUT of the wording comparison because the count is derived
            # from apps.json and asserted exactly, below, against number_word(total).
            # The old alternation enumerated "Twenty-eight|Thirty-one", so the next
            # legitimate count stopped matching and the gate reported Matt's authored
            # wording as changed when only the number had.
            r"(Your offline creative workshop\.\s+)"
            r"(?:[A-Z][a-z]+(?:-[a-z]+)?|\d+)"
            r"(\s+single-file studios)",
            r"\1{DERIVED_COUNT}\2",
            value,
            flags=re.I,
        )
    return value


def css_balanced(text: str) -> bool:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    quote = None
    escape = False
    depth = 0
    for char in text:
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in "\"'":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0 and quote is None


def git_text(root: Path, ref: str, path: str) -> str:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"], cwd=root, text=True, capture_output=True
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or f"git show failed for {ref}:{path}")
    return proc.stdout


def number_word(n: int) -> str:
    one = [
        "Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
        "Seventeen", "Eighteen", "Nineteen",
    ]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    if 0 <= n < 20:
        return one[n]
    if 20 <= n < 100:
        return tens[n // 10] + ("-" + one[n % 10].lower() if n % 10 else "")
    return str(n)


def run_checks(
    root: Path,
    *,
    kind: str,
    canonical: Path,
    base_html: str | None = None,
    check_git: bool = False,
    base_ref: str | None = None,
) -> list[str]:
    errors: list[str] = []
    index_path = root / "index.html"
    if not index_path.is_file():
        return ["missing index.html"]
    text = index_path.read_text("utf-8")

    if SENTINEL not in text:
        errors.append("sentinel/version marker missing from index.html")
    expected_body = f'mbm-hub mbm-hub-{kind}'
    if expected_body not in text:
        errors.append(f"missing {expected_body} body classes")
    if 'class="header mbm-site-header"' not in text:
        errors.append("canonical platform header class missing")
    if 'class="menu" id="menu"' not in text or 'aria-controls="nav"' not in text:
        errors.append("responsive menu button contract missing")
    if 'id="nav" aria-label="Site navigation"' not in text:
        errors.append("named site navigation landmark missing")
    if '<summary>More</summary>' not in text or '<summary>Display</summary>' not in text:
        errors.append("More/Display disclosure contract missing")
    if "data-mbm-theme-slot" not in text:
        errors.append("reading-background slot missing")

    primary = extract(r'<div class="mbm-primary-links">(.*?)</div>', text, "primary navigation", errors)
    primary_hrefs = re.findall(r'<a\b[^>]*href="([^"]+)"', primary, re.I)
    if primary_hrefs != PRIMARY_ROUTES:
        errors.append(f"primary route order/casing drift: {primary_hrefs!r}")
    more = extract(r'<div class="mbm-nav-panel">(.*?)</div>', text, "More panel", errors)
    more_hrefs = re.findall(r'<a\b[^>]*href="([^"]+)"', more, re.I)
    if more_hrefs != MORE_ROUTES:
        errors.append(f"More route order/casing drift: {more_hrefs!r}")
    active = re.findall(r'<a\b[^>]*href="([^"]+)"[^>]*aria-current="page"', primary, re.I)
    expected_active = "/Lessons/" if kind == "lessons" else "/Matt-s-Apps-/"
    if active != [expected_active]:
        errors.append(f"active navigation must be exactly {expected_active}: {active!r}")

    ids = re.findall(r'\bid="([^"]+)"', text, re.I)
    duplicates = sorted(k for k, count in Counter(ids).items() if count > 1)
    if duplicates:
        errors.append(f"duplicate IDs: {duplicates}")

    for rel, expected in CANONICAL_HASHES.items():
        path = root / rel
        if not path.is_file():
            errors.append(f"missing shared local asset {rel}")
        elif digest(path) != expected:
            hint = f" — run: {SYNC_COMMAND}" if rel == THEME_COPY else ""
            errors.append(f"shared asset hash drift: {rel}{hint}")
    # Pins are checked on EVERY run, not only when git reports the file changed: a
    # gate that looks only when it is told something moved cannot catch the case
    # where nobody told it.
    for manifest, pinned in MANIFEST_PINS.items():
        path = root / manifest
        if not path.is_file():
            continue          # the other estate does not carry this manifest
        if digest(path) != pinned:
            errors.append(
                f"{manifest} does not match its pinned digest — if you changed it on "
                f"purpose, re-pin it in the same commit: {PIN_COMMAND}")

    theme_path = root / THEME_COPY
    if theme_path.is_file() and not theme_path.read_bytes().startswith(GENERATED_HEADER):
        errors.append(
            f"{THEME_COPY} has lost its generated-file header, so the next person to open "
            f"it has nothing telling them it is output — run: {SYNC_COMMAND}")
    # Unconditional, and that is the point. This block used to sit behind
    # `if canonical:`, with --canonical an optional argument. Run without it the
    # gate skipped every cross-estate comparison and still printed
    # "[PASS] <kind> cross-estate static contract" and exited 0 — a green naming
    # the one thing it had not done. That is how three different versions of
    # mbm-platform.css/js coexisted across the estate with every pin green:
    # Lessons ccfb0fd9/0841046b, Apps e3eb9b83/0958a73a, site b520cf36/095a29e6.
    # `canonical` is now a required parameter with no default, so omitting it is
    # a TypeError here and an argparse error at the boundary, not a quiet pass.
    pairs = {
        "assets/mbm-platform.css": canonical / "assets/mbm-platform.css",
        "assets/mbm-platform.js": canonical / "assets/mbm-platform.js",
        THEME_COPY: canonical / "theme.js",
    }
    for local_rel, reference in pairs.items():
        if not reference.is_file():
            errors.append(f"canonical reference missing: {reference}")
            continue
        expected_bytes = reference.read_bytes()
        if local_rel == THEME_COPY:
            expected_bytes = GENERATED_HEADER + expected_bytes
        if (root / local_rel).read_bytes() == expected_bytes:
            continue
        if local_rel == THEME_COPY:
            errors.append(
                f"{local_rel} is not the generated copy of the canonical theme.js. "
                f"Do not edit it here — edit theme.js in the site repository, then run: "
                f"{SYNC_COMMAND}")
        else:
            errors.append(f"local copy no longer equals canonical source: {local_rel}")

    if 'href="assets/mbm-platform.css"' not in text or 'href="assets/mbm-hub.css"' not in text:
        errors.append("hub must use repo-local CSS assets")
    if 'src="assets/mbm-theme.js"' not in text or 'src="assets/mbm-platform.js"' not in text:
        errors.append("hub must use repo-local JavaScript assets")
    if 'src="/theme.js"' in text or 'src="/assets/mbm-platform' in text:
        errors.append("network/root dependency introduced for the hub shell")
    external_scripts = re.findall(r'<script\b[^>]*\bsrc="(https?:[^"]+)"', text, re.I)
    if external_scripts:
        errors.append(f"unexpected external hub scripts: {external_scripts}")

    for rel in ("assets/mbm-platform.css", "assets/mbm-hub.css"):
        path = root / rel
        if path.is_file() and not css_balanced(path.read_text("utf-8")):
            errors.append(f"unbalanced CSS: {rel}")
    platform_js = (root / "assets/mbm-platform.js").read_text("utf-8") if (root / "assets/mbm-platform.js").is_file() else ""
    theme_js = (root / "assets/mbm-theme.js").read_text("utf-8") if (root / "assets/mbm-theme.js").is_file() else ""
    for required in ("Escape", "pointerdown", "aria-expanded", "ResizeObserver", "mbm-nav-open"):
        if required not in platform_js:
            errors.append(f"platform interaction contract missing {required}")
    if "mbm_reading_theme" not in theme_js:
        errors.append("shared reading-theme storage key missing")

    suspicious = re.findall(
        r"(?i)(?:password\s*=|hard.?coded\s+password|localStorage\.(?:setItem|getItem)\([^)]*(?:auth|login|password)|api[_-]?key\s*=)",
        text + platform_js + theme_js,
    )
    if suspicious:
        errors.append("credential/fake-auth pattern detected")

    if kind == "apps":
        try:
            data = json.loads((root / "apps.json").read_text("utf-8"))
            spaces = data.get("spaces")
            if not isinstance(spaces, list) or not all(isinstance(s.get("items"), list) for s in spaces):
                raise ValueError("invalid spaces")
            total = sum(len(s["items"]) for s in spaces)
            expected_word = number_word(total)
            if f'<span id="leadCount">{expected_word}</span>' not in text:
                errors.append(f"no-JS lead count does not match apps.json ({expected_word})")
            for token in ("numberWord(total)", "leadCount", "${shown} of ${total} studios"):
                if token not in text:
                    errors.append(f"derived Apps count contract missing: {token}")
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(f"invalid apps.json: {exc}")
    else:
        try:
            data = json.loads((root / "resources.json").read_text("utf-8"))
            if not isinstance(data, list) or not data:
                raise ValueError("expected non-empty list")
            years = Counter(item.get("year") for item in data)
            if not years.get("2026-27") or not years.get("2025-26"):
                errors.append(f"academic collection data missing: {dict(years)}")
            for token in ("${a.length} of ${ALL.length} resources", "fillTabCounts", "buildQuicknav"):
                if token not in text:
                    errors.append(f"derived Lessons count contract missing: {token}")
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(f"invalid resources.json: {exc}")

    if base_html is not None:
        base_brand = extract(r'(<a class="brand"[^>]*>.*?</a>)', base_html, "base brand", errors)
        current_brand = extract(r'(<a class="brand"[^>]*>.*?</a>)', text, "current brand", errors)
        if base_brand and current_brand and base_brand != current_brand:
            errors.append("Made by Matt logo/brand markup changed")
        if normalized_visible_body(base_html, kind) != normalized_visible_body(text, kind):
            errors.append("existing authored hub wording changed outside the derived Apps count")

    if check_git and base_ref:
        proc = subprocess.run(
            # M/R/D, not A. The invariant is stated at the top of this file: "no
            # standalone lesson or studio is CHANGED by this release". An ADDED file
            # changes nothing — it cannot modify an existing studio — and counting
            # additions as violations meant every new studio, tool and dotfile had to
            # be hand-added to ALLOWED_DIFF forever. Proven both ways: modifying or
            # deleting an existing studio still reddens this check.
            ["git", "diff", "--name-only", "--diff-filter=MRD", f"{base_ref}...HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
        )
        if proc.returncode:
            errors.append(f"git diff failed: {proc.stderr.strip()}")
        else:
            changed = {line.strip() for line in proc.stdout.splitlines() if line.strip()}
            unexpected = sorted(changed - ALLOWED_DIFF)
            if unexpected:
                errors.append(f"standalone/offline boundary violated by changed files: {unexpected}")
            for manifest in ("resources.json", "apps.json"):
                if manifest in changed and manifest not in MANIFEST_PINS:
                    errors.append(f"source manifest unexpectedly changed: {manifest}")

    return errors


def self_test(root: Path, kind: str, canonical: Path) -> None:
    # The fixture copies this repository's own CANONICAL_HASHES assets, so with
    # the tree in a good state they already equal the canonical ones and the
    # comparison passes. Threading `canonical` through is not bookkeeping for the
    # new required argument: it means the positive control now exercises the
    # cross-estate leg as well, and "fixture was not initially valid" below would
    # catch that leg being broken, not only the local ones.
    with tempfile.TemporaryDirectory(prefix="mbm-cross-estate-positive-control-") as temp:
        fixture = Path(temp)
        for rel in ["index.html", "resources.json" if kind == "lessons" else "apps.json", *CANONICAL_HASHES]:
            src = root / rel
            dst = fixture / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        good = run_checks(fixture, kind=kind, canonical=canonical)
        if good:
            raise RuntimeError(f"positive-control fixture was not initially valid: {good}")
        index = fixture / "index.html"
        text = index.read_text("utf-8")
        index.write_text(text.replace('<a href="/Lessons/"', '<a href="/lessons/"', 1), "utf-8")
        bad = run_checks(fixture, kind=kind, canonical=canonical)
        if not bad:
            raise RuntimeError("positive-control mutation was not detected")
        print(f"positive-control: PASS ({len(bad)} detected error(s))")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--base", help="Git ref used to prove wording/logo and diff boundaries")
    parser.add_argument(
        "--canonical",
        required=True,
        help="Checked-out canonical site repository. Required, and deliberately so: "
             "without it the cross-estate comparison does not run at all, and this "
             "gate would print [PASS] cross-estate static contract having compared "
             "nothing across estates.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    kind = detect_kind(root)
    base_html = git_text(root, args.base, "index.html") if args.base else None
    # required=True stops a missing flag. It does not stop --canonical "" — an
    # empty string satisfies argparse and used to be falsy at the `if canonical:`
    # that no longer exists, so it would have skipped the comparison silently.
    # Nor does it stop a path that is not the site repository, which would fail
    # later as three "canonical reference missing" lines rather than as the one
    # thing that is actually wrong. Both are named here instead.
    if not args.canonical.strip():
        parser.error("--canonical was given an empty path; pass the checked-out site repository")
    canonical = Path(args.canonical).resolve()
    if not (canonical / "assets/mbm-platform.css").is_file():
        parser.error(
            f"--canonical does not look like the site repository: {canonical} "
            f"(no assets/mbm-platform.css under it)")
    errors = run_checks(
        root,
        kind=kind,
        base_html=base_html,
        canonical=canonical,
        check_git=bool(args.base),
        base_ref=args.base,
    )
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1
    print(f"[PASS] {kind} cross-estate static contract")
    if args.self_test:
        self_test(root, kind, canonical)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
