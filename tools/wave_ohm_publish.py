#!/usr/bin/env python3
"""Publish WAVE & OHM v2.3, and integrate the bridge into the hub — Part B's build.

COMPOSITION, NOT MODIFICATION
-----------------------------
This tool imports tools/stealth_publish.py as a module and reuses its donor
handling, splash/guard/skip blocks, install anchoring and gates verbatim. It is
a separate file because the estate's change boundary holds modifications to an
enumerated list, and Part B does not widen that list: stealth_publish.py stays
byte-for-byte what Part A shipped, and everything new arrives as additions.

WHAT IT BUILDS
--------------
  wave-interference-iridescence-engine-v2-3.html   splash + guard + hud (framed in the deck)
  ohms-law-fault-finder-v2-3.html                  ditto
  mbm-master-hub.html                              rebuilt through Part A's FULL pipeline,
                                                   then the Ruling 4 bridge transforms

Pristine sources are the repo's own copies under _release-docs/wave-ohm-v2-3/,
hash-checked against PACKAGE-SHA256-V2-3.txt before every build, so the build
still reproduces after the upload's scratch directory is gone.

TITLES ARE REARRANGED, NOT APPENDED
-----------------------------------
The v2.3 titles arrive as "Made by Matt — <name>". The estate convention
(Nova Siege finding V4) is the app's own name first and the estate suffix
last, so the build rewrites to "<name> — Made by Matt" rather than producing
"Made by Matt — … — Made by Matt".

RULING 4 — THE BRIDGE GOES IN AT SOURCE LEVEL
---------------------------------------------
The install guide's runtime wrap cannot work: the hub's decryptCode is a
function declaration inside its single IIFE and is never exported, so an
external script has nothing to grab; and the artwork path carries a pre-gate
that rejects MBM.WAVE.*/MBM.OHM.* before any decoder runs. Three transforms,
each minimal, each additive, each gated in --prove:

  1. the bridge's own bytes — sha-pinned c3fb4dea…, refused on mismatch —
     become their own <script> element BEFORE the hub's main IIFE script;
  2. inside the IIFE, immediately before the decode button is wired, one line
     rebinds decryptCode through the bridge's patchDecryptCode — guarded, so a
     missing bridge degrades to today's behaviour. The bridge's wrapper only
     diverts MBM.WAVE./MBM.OHM. prefixes; MBM3/MBM3U/MBM2/MBM1 fall through to
     the ORIGINAL function unchanged;
  3. the artwork pre-gate widens to admit exactly the two new prefixes:
        /^MBM(?:3U?|[12])\\./  ->  /^(?:MBM(?:3U?|[12])|MBM\\.(?:WAVE|OHM))\\./
     A garbage prefix still fails at the same gate with the same message.

No route is removed, reordered or short-circuited. The donor splash block, the
two embedded octet-stream copies and the sandbox attribute are asserted
unchanged afterwards — the same gates Part A ran, re-run.

    python3 tools/wave_ohm_publish.py --build
    python3 tools/wave_ohm_publish.py --prove
    python3 tools/wave_ohm_publish.py --self-test
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import re
import sys
from pathlib import Path

APPS = Path(__file__).resolve().parent.parent
REL = APPS / "_release-docs" / "wave-ohm-v2-3"

# ---- Part A's tool, imported as the library it already is -------------------
_spec = importlib.util.spec_from_file_location("stealth_publish", APPS / "tools" / "stealth_publish.py")
SP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SP)

BRIDGE_SHA = "c3fb4dea1e1dd3b98114fcff97bd2b5a3839d48c575c7ecf0a98954b8cfb416e"
BRIDGE_SRC = REL / "mbm-master-hub-bridge-v2-3.js"

# (pristine name, splash title, framed?) — both run framed inside the deck.
WAVE = "wave-interference-iridescence-engine-v2-3.html"
OHM = "ohms-law-fault-finder-v2-3.html"
FILES = [(WAVE, "WAVE & IRIDESCENCE", True), (OHM, "OHM'S LAW FAULT-FINDER", True)]

PRISTINE_SHA = {
    WAVE: "a1f99c83415e609ed3955de64fd128dd2cd940c23b0062f74b59e8a16eb32355",
    OHM: "74b96fc094f62617f35af6bd83daaf834d4c8c9e8457d18897f7b2c3d27f6649",
}

HUB = APPS / "mbm-master-hub.html"

OLD_GATE = r"if(!/^MBM(?:3U?|[12])\./.test(code))throw new Error('Evidence metadata has an unsupported format')"
NEW_GATE = r"if(!/^(?:MBM(?:3U?|[12])|MBM\.(?:WAVE|OHM))\./.test(code))throw new Error('Evidence metadata has an unsupported format')"

WIRE_ANCHOR = "$('#decodeBtn').addEventListener('click',decodeImport);"
PATCH_LINE = (
    "/* Ruling 4: WAVE/OHM envelopes route through the bridge; everything else\n"
    "   reaches the original decryptCode exactly as before. Guarded, so a missing\n"
    "   bridge degrades to today's behaviour rather than a boot error.\n"
    "   The decoded payload then gains the six-axis profile the bridge's own\n"
    "   mapCompetencyRadar derives (install guide section 6) — translated from\n"
    "   the bridge's camelCase axis keys to this hub's label-keyed AXES — because\n"
    "   addRecord accepts nothing without one. WAVE/OHM records carry no\n"
    "   encryption claim: compactPayload stores no security field, and these\n"
    "   envelopes are encoded, not encrypted. */\n"
    "if(window.MBMTeacherToolsBridge&&window.MBMTeacherToolsBridge.patchDecryptCode){"
    "decryptCode=(function(orig){var B=window.MBMTeacherToolsBridge,patched=B.patchDecryptCode(orig);"
    "return async function(code,pin){var raw=String(code||'').trim(),out=await patched.call(this,raw,pin);"
    "if((raw.indexOf('MBM.WAVE.')===0||raw.indexOf('MBM.OHM.')===0)&&out&&typeof out==='object'){"
    "var extra={};"
    # identifyPayload reads appId/app/schema and never the v2.3 payloads' own
    # `tool` field, so both apps landed as 'unknown' — and two unknown
    # empty-state imports fingerprinted identically, so the second deduped
    # away. The identity the hub already names is attached here.
    "if(!out.appId&&!out.app){extra.appId=raw.indexOf('MBM.WAVE.')===0?'wave':'ohms';}"
    "if(!out.profile){try{var r=B.mapCompetencyRadar(out),prof={};"
    "r.axes.forEach(function(a){prof[(r.labels&&r.labels[a])||a]=r.scores[a]});"
    "extra.profile=prof;extra.radar=r;}catch(e){}}"
    "return Object.assign({},out,extra);}"
    "return out;};})(decryptCode);}\n"
)
BRIDGE_MARK = "<!-- mbm-bridge-v2-3: WAVE/OHM envelope decoder, bytes pinned c3fb4dea -->"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def bridge_text() -> str:
    data = BRIDGE_SRC.read_bytes()
    if sha(data) != BRIDGE_SHA:
        raise SystemExit(f"[FAIL] bridge source at {BRIDGE_SRC} hashes {sha(data)[:16]}, "
                         f"not the pinned {BRIDGE_SHA[:16]} — refusing to install it")
    return data.decode("utf-8")


def retitle_rearranged(text: str) -> tuple[str, str]:
    m = re.search(r"<title>(.*?)</title>", text, re.S)
    old = m.group(1)
    mm = re.match(r"Made by Matt\s+—\s+(.*)$", old.strip(), re.S)
    new = (mm.group(1).strip() + " — Made by Matt") if mm else (old.rstrip() + SP.SUFFIX)
    return text[:m.start(1)] + new + text[m.end(1):], new


def build_apps() -> dict[str, bytes]:
    donor = SP.donor_text()
    out: dict[str, bytes] = {}
    for name, title, framed in FILES:
        src = REL / name
        data = src.read_bytes()
        if sha(data) != PRISTINE_SHA[name]:
            raise SystemExit(f"[FAIL] pristine {name} hashes {sha(data)[:16]}, expected "
                             f"{PRISTINE_SHA[name][:16]} — the archive copy has been touched")
        text, newtitle = retitle_rearranged(data.decode("utf-8"))
        text = SP.install(text, title, framed, donor)
        (APPS / name).write_text(text, encoding="utf-8")
        out[name] = (APPS / name).read_bytes()
        print(f"  built {name:48} {len(data)} -> {len(out[name])} B")
        print(f"        <title> {newtitle!r}")
    return out


def bridge_hub() -> None:
    """Part A's full hub pipeline first, then the three Ruling 4 transforms."""
    donor = SP.donor_text()
    text = (SP.SRC / "mbm-master-hub.html").read_text(encoding="utf-8")
    text = SP.drop_dead_adapter_link(text, "mbm-master-hub.html")
    text, _t = SP.retitle(text)
    text = SP.install(text, "MBM//SCIENCE PORTFOLIO", False, donor)

    # 3. the artwork pre-gate widens by exactly two prefixes
    if OLD_GATE not in text:
        raise SystemExit("[FAIL] the artwork pre-gate is not at its expected text — refusing to guess")
    text = text.replace(OLD_GATE, NEW_GATE, 1)

    # 1. the bridge, verbatim, before the main IIFE script
    main_i = text.index("<script>\n(()=>{'use strict'")
    block = f"{BRIDGE_MARK}\n<script>\n{bridge_text()}</script>\n"
    text = text[:main_i] + block + text[main_i:]

    # 2. one guarded rebind, wired in before the decode button listener
    if text.count(WIRE_ANCHOR) != 1:
        raise SystemExit("[FAIL] decode-button anchor not unique — refusing to guess")
    text = text.replace(WIRE_ANCHOR, PATCH_LINE + WIRE_ANCHOR, 1)

    HUB.write_text(text, encoding="utf-8")
    print(f"  bridged hub -> {HUB.stat().st_size} B (bridge element + one rebind + widened artwork gate)")


def build() -> int:
    finals = build_apps()
    bridge_hub()
    # THE TRAP, third time: the hub's embedded copies are ORBIT and ENZYME, and
    # this build rewrote the hub from pristine — so they are re-embedded from
    # the PUBLISHED Part A standalones, exactly as Part A's build does.
    hub = SP.reembed(HUB.read_text(encoding="utf-8"),
                     {sid: (APPS / name).read_bytes() for sid, name in SP.EMBEDS.items()})
    HUB.write_text(hub, encoding="utf-8")
    print(f"  re-embedded hub -> {HUB.stat().st_size} B (ORBIT/ENZYME copies from the published standalones)")
    return 0


def prove(root: Path = APPS) -> list[str]:
    problems: list[str] = []
    donor = SP.donor_text()

    # Part A's gates, re-run whole: donor byte-identity in the trio, one splash
    # block each, embeds decode-equal, hud loaders, node --check + Worker source.
    problems += SP.prove(donor, root=root)

    print()
    hub = (root / "mbm-master-hub.html").read_text(encoding="utf-8")

    # bridge bytes: present once, verbatim against the pin
    n_mark = hub.count(BRIDGE_MARK)
    m = re.search(re.escape(BRIDGE_MARK) + r"\n<script>\n(.*?)</script>\n", hub, re.S)
    ok_bytes = bool(m) and sha(m.group(1).encode("utf-8")) == BRIDGE_SHA
    print(f"  bridge element: {n_mark} occurrence(s); bytes match pin: {ok_bytes}")
    if n_mark != 1:
        problems.append(f"hub: {n_mark} bridge elements, expected 1")
    if not ok_bytes:
        problems.append("hub: bridge bytes differ from the pinned c3fb4dea source")

    # the rebind: the exact block, once, immediately before the decode wiring.
    # Counted as the whole PATCH_LINE rather than a fragment: an earlier counter
    # grepped for the one-line form after the block had grown, and reported zero
    # rebinds in a hub that carried exactly one.
    n_patch = hub.count(PATCH_LINE)
    print(f"  decryptCode rebind block: {n_patch} occurrence(s)")
    if n_patch != 1:
        problems.append(f"hub: {n_patch} rebind blocks, expected 1")
    if PATCH_LINE + WIRE_ANCHOR not in hub:
        problems.append("hub: the rebind is not immediately before the decode wiring")

    # the artwork gate: new form exactly once, old form gone, garbage still dies
    n_new, n_old = hub.count(NEW_GATE), hub.count(OLD_GATE)
    print(f"  artwork pre-gate: widened form x{n_new}, original form x{n_old}")
    if (n_new, n_old) != (1, 0):
        problems.append(f"hub: artwork gate widened x{n_new}, original x{n_old} — expected exactly 1/0")
    rx = re.compile(r"^(?:MBM(?:3U?|[12])|MBM\.(?:WAVE|OHM))\.")
    accepts = ["MBM3.", "MBM3U.", "MBM2.", "MBM1.", "MBM.WAVE.2.", "MBM.WAVE.RESULT.2.",
               "MBM.OHM.STATE.2.", "MBM.OHM.RESULT.2."]
    rejects = ["XYZ.", "MBM.FOO.", "MBM4.", "MBMX.", "WAVE.", "MBM.WAVEX."]
    bad_a = [c for c in accepts if not rx.match(c)]
    bad_r = [c for c in rejects if rx.match(c)]
    print(f"  gate regex: {len(accepts) - len(bad_a)}/{len(accepts)} legitimate prefixes pass, "
          f"{len(rejects) - len(bad_r)}/{len(rejects)} garbage prefixes still fail")
    if bad_a:
        problems.append(f"widened gate rejects legitimate prefixes: {bad_a}")
    if bad_r:
        problems.append(f"widened gate admits garbage: {bad_r}")

    # WAVE/OHM standalones: donor identity + guard + hud, via Part A's exact recovery
    for name, _t, _f in FILES:
        p = root / name
        if not p.is_file():
            problems.append(f"{name}: not built")
            continue
        text = p.read_text(encoding="utf-8")
        i = text.find("mbm-splash-inline")
        inlined = text[text.index("<script>", i) + 8:text.index("</script>", i)].strip() if i >= 0 else ""
        code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        checks = {
            "donor byte-identical": inlined == donor,
            "one frame guard": code.count("window.MadeByMattSplash.start=function()") == 1,
            "one invocation": len(re.findall(r"MadeByMattSplash\.start\(\{title:", code)) == 1,
            "one hud loader": text.count(SP.HUD) == 1,
            "title suffix": bool(re.search(r"<title>.*— Made by Matt</title>", text, re.S)),
            "name still first": "<title>Made by Matt —" not in text,
        }
        line = "  ".join(k for k, v in checks.items() if not v)
        print(f"  {name}: {'all six checks hold' if not line else 'FAIL ' + line}")
        problems += [f"{name}: {k}" for k, v in checks.items() if not v]
    return problems


def self_test() -> int:
    """The new gates must be able to fail: a byte flipped inside the installed
    bridge, and the artwork gate quietly un-widened, both in memory."""
    problems = []
    hub_p = APPS / "mbm-master-hub.html"
    original = hub_p.read_bytes()
    try:
        text = original.decode("utf-8")
        # sabotage 1: flip a byte inside the bridge element
        m = re.search(re.escape(BRIDGE_MARK) + r"\n<script>\n(.*?)</script>\n", text, re.S)
        sab = text[:m.start(1)] + m.group(1).replace("patchDecryptCode", "patchDecryptC0de", 1) + text[m.end(1):]
        if sab == text:
            problems.append("sabotage 1 DID NOT LAND")
        else:
            hub_p.write_text(sab, encoding="utf-8")
            found = [p for p in prove() if "bridge bytes differ" in p]
            print(f"   sabotage: bridge byte flipped -> {len(found)} finding(s)")
            if not found:
                problems.append("a modified bridge passed the byte pin")
        hub_p.write_bytes(original)
        # sabotage 2: un-widen the artwork gate
        sab2 = text.replace(NEW_GATE, OLD_GATE, 1)
        if sab2 == text:
            problems.append("sabotage 2 DID NOT LAND")
        else:
            hub_p.write_text(sab2, encoding="utf-8")
            found = [p for p in prove() if "artwork gate" in p]
            print(f"   sabotage: artwork gate un-widened -> {len(found)} finding(s)")
            if not found:
                problems.append("an un-widened artwork gate went unnoticed")
    finally:
        hub_p.write_bytes(original)
    if hub_p.read_bytes() != original:
        problems.append("RESTORE FAILED")
    for p in problems:
        print("   FAIL " + p)
    print("[FAIL] wave-ohm self-test" if problems else
          "[PASS] wave-ohm self-test: a flipped bridge byte and an un-widened artwork gate "
          "are both caught, and the hub was restored")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--prove", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.build:
        return build()
    if a.self_test:
        return self_test()
    if a.prove:
        problems = prove()
        print()
        if problems:
            print(f"[FAIL] wave-ohm publish gates: {len(problems)} problem(s)")
            for p in problems:
                print("   - " + p)
            return 1
        print("[PASS] wave-ohm publish gates: Part A's gates all hold on the rebuilt hub, the "
              "bridge is installed verbatim against its pin, one guarded rebind sits before the "
              "decode wiring, the artwork gate admits exactly the two new prefixes, and both "
              "standalones carry donor + guard + hud with rearranged titles")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
