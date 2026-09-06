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
    "resources.json": "2e227f569e024f09ba750fabb4fcc00c9f277fdc04570f97bdab261418648b83",
}
PIN_COMMAND = "python3 tools/pin_manifests.py   (from either checkout — it writes both gate copies or neither)"

# Explicit education catalogue release, 2026-09-05. Matt authorised a new
# browsing design, so the old Lessons wording comparison must permit exactly
# the reviewed result. These pins do not exempt a directory or a lesson: every
# named byte set is checked, including additions, on every Lessons gate run.
# Apps retains its original authored-wording comparison. This block is updated
# in both gate copies by tools/catalogue/pin_catalogue_contract.py after review.
# BEGIN REVIEWED CATALOGUE PINS
CATALOGUE_PINS = {
    "visible_body_sha256": "65fcef2607bd18a79fe27942320defa60e7f967568f4daa7ad2b936e40471d76",
    "files": {
        "index.html": "d24c248f5609e6d166045e0a9201964574ad2767713ca079cde0c5d1996108d1",
        "Science_Teesside/index.html": "5c5a5ce568b7ad319d9a5497540d398cbfe35254ca4446922c0aa3935703f4ac",
        "Humanities_Teesside/index.html": "ee2758cd5b9bb69b18c005100292607d9eab9e7eb389425853cbce374ceafd72",
        "humanities_teesside.html": "1e2faab06cb4caf4a26f377200a55cbd380c7f3ceada74f666998b47611896b7",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/index.html": "4e25eb9ca8f9f93c720d88d945f3d6d79580f3362a88698fe7af75d146f01e96",
        "assets/catalogue/catalogue.css": "a11ee200d86a6a8aaf89dc3bc0215bdd345b15122008d11311be6650857d4d30",
        "assets/catalogue/catalogue.js": "62e72770017e72a4a2f212d355d907ad14af924704d6a222093b3ef063661ac8",
        "assets/catalogue/lesson-navigation.js": "eac7081b5c02e450e5baa5200421e275196fb1f0e9599b5ffe9bf101ee593e99",
        "assets/catalogue/science-shelf.css": "f664655e57c086abe35499f5dedf737eddaa0942e6629dd4a7fcf4e801536508",
        "assets/catalogue/science-shelf.js": "b47b998866401f136968a2e1e94cc5beb65be83fbd342f49ff5a811804792651",
        "assets/catalogue/terms-and-styles.json": "80f53f53a26e008df2d3dfe6bfcd1f532cc68c5dbeb11f70d3f63c1c751859b9",
        "assets/catalogue/science-shelf.json": "116a62dd58b0a65822446ff67997095a5cef4403a45c1c6fa5e3862fb9012bb3",
        "assets/catalogue/humanities-shelf.json": "74afc429c5f67a2cf557483715687e9327209c269d70fcd1c6c6495e7516e734",
        "tools/catalogue/build_catalogue.py": "43ab03f58ac1197d37e332e061aec6869d6337498c0b2ec9f619819e8ea863ac",
        "tools/catalogue/build_science_shelf.py": "caea7cd65060bd1a354dc6d3cc14cc4a883a2db9fae6254f4a777ae86362863d",
        "tools/catalogue/build_humanities_shelf.py": "89721c1adf644fd7e5f7a03449ff166eb2c9cfd99fb2aa65482fda6693da48b7",
        "tools/catalogue/check_catalogue_static.py": "4c5728322c88fd1706e30bb1ffacbc80daaad11703cb39bd3dd9ff0aa3f3c02c",
        "tools/catalogue/check_catalogue_dom.cjs": "8ff483960a979b548269246813978c56c91deade611810e50807aeda48ad894d",
        "tools/catalogue/verify_education_navigation.cjs": "3c2732e4d302579fe011745abdf7c36ffa63c062ee22e7777a1eb3876c615580",
        "tools/catalogue/SHELF_SELECTION.json": "d6699b2e420992a15ae9674d1a93c394ec93b66af477fdeb6fd1a857ab8ff935",
        "tools/catalogue/HUMANITIES_SELECTION.json": "a79ff3234a0d504d439b8c9861ad8199f91c61921d7419c05fea2ac2a51cbcb0",
        "tools/easter/science_original_browser.cjs": "650884c0ef6ec714edc429bbf7c5601e26176df44012661462c37ee3de7478d1",
        "tools/prepare_served_publications.py": "e0623cc295854f41e353d521d99b998e9be21568506799f6e01f3b16ce12f7c4",
        "tools/test_served_publications.py": "128f691b0a1f5880a68190540266e3f78993e4849cd75d7f1b6db75e098e1d31",
        ".github/workflows/glv3-verify.yml": "4bf27ca7471a21359e35d1bc7277c5fa0adeb5f31a47c769f192165796037088",
        "_glv3/tools/verify_change_boundary.py": "83abbfb09690729b65da0a0d8adeec1564f6f0f7b198b8de2e2334be5039fcfa",
        "_glv3/tools/browser_verify.mjs": "ce70c354380ed8fedba90714981465dce39fb7d9b6452a12f6a0b2d782969e86",
        "_glv3/tools/chip_gate.mjs": "0f2ffe5e738fb5d5998755e172e47dc3695944b2513dc86da66a5dd2a1c51723",
        "tools/humanities_resources/SOURCE_MANIFEST.json": "e0c8edae9ec76ae48b957ba4b46b5340e7257174084d38816fa12391772930e6",
        "tools/humanities_resources/DOWNLOAD_MANIFEST.json": "1d872aa4e9d01d7f10d26a0e8d182ddcb4513598413314f7c38d055318d39a2f",
        "tools/humanities_resources/CONTENT.json": "335ea55d7964d8095064e2c67c95fbd8d65e28b4d1ddf25f6e4ee812abd29b98",
        "tools/humanities_resources/ORIGINAL_MEMBER_MANIFEST.json": "c4ce9e5a0a5d966ee31f401ae476a2dc10a43aa8dc749e09b2cef87b745db073",
        "tools/humanities_resources/build_resources.py": "d99981a314f152af98fe3a64c48f7ac1bc2afe184bb0e4a2c504b8d00399366f",
        "tools/humanities_resources/check_resources.py": "ec5383e3a34cbff999f190b0014a4a73e00a3a29e2714498f7620fd638dc2aa5",
        "tools/humanities_resources/resource.css": "1aed9aaca0d73a4b200c4e5d0977e73f4e906c747d7340c7a62f4197a8344bae",
        "tools/humanities_resources/resource.js": "ad40afed95490bfcce92dc062da46e1b27bcb96bdc80e37eabdfe02bf6ffc446",
        "tools/catalogue/TERM_AND_STYLE_EVIDENCE.json": "64123b8c85c08eeebff6aa2172ee017e613ef33a2eae19e36bc938db06995894",
        "tools/catalogue/TERM_REVIEW.json": "a1f7226e874474207a4a6f916e1b3e9379d4525da63edfbda6c8d115cc6c6f0e",
        "tools/catalogue/SCIENCE_WEEK_BINDINGS.json": "84a9fccdc0ea27ca9c57287d1dfce5de198420f92df2b1e73a2d2fcd5df79a88",
        "primary/year5/science/autumn/forces/Lesson8_ExploreGravity.html": "20047720bf1d309055abdf232d341b6fd99b833631efa0bcbfb3dabed9671196",
        "primary/year5/science/autumn/forces/Y5_Forces_SoW_and_Plans.docx": "ca36cfd92f1c768ea66f0eb748d47e6227f67569f77b5472d0da13d03f92f2e6",
        "assets/catalogue/science-download-bindings.json": "94ed5a2c351d08c8fa06af89a4592f1931b2ab68d95cfeaf5762d03649a3d2bf",
        "Science_Teesside/Teaching_Packs/BUILD/BUILD_Science_Autumn1_W3-W7_Teaching_Guide.docx": "458be26b36249db369f7874fa1cc4eea1764bcfa68475c6f35554b29b4950ccb",
        "Science_Teesside/Teaching_Packs/BUILD/BUILD_Science_Autumn1_W3-W7_Teaching_Guide.pdf": "6fc4efdfa250d775cf7f61f0057b653b29fb2c3f3263cfa3a530f0732cf4e022",
        "Science_Teesside/Teaching_Packs/BUILD/DOWNLOAD_INDEX.json": "ed7e4a1a1cdddf5ea7234a635ca9b522565d41a281f84a6e71a3e2b25804a510",
        "Science_Teesside/Teaching_Packs/BUILD/SOURCE_MANIFEST.json": "1871cdbd4e50a2ae625e209f2ad65b4b9bc171a2148b4f21562ce40e3986fc15",
        "Science_Teesside/Teaching_Packs/BUILD/START_HERE.txt": "7dc574750bc326685d64d0abbd25b632e9f8a724c7aa84f1123055c7f148ec7c",
        "Science_Teesside/Teaching_Packs/BUILD/assets/made-by-matt-approved.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3-W7_Complete_Pack.zip": "12862e278c4b338b5c1e7981feb55430a6a4c44097721683cb1ce565bbd29312",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3A_Backbones_Lesson_Pack.zip": "369deca2787c6c1b49121e0fbee7c6b82ae48877d722cd4288be59e31a17f375",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Lesson_Pack.zip": "c71470e972f1ee792c7281bb60cb59af39495429b5a6871228c6734fbe13ecf9",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3_Teaching_Pack.zip": "179d46cb49d5f9a3e2c36b4bb6ad05fb2e9b397269f38ed4d8e79b52f14689b0",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Lesson_Pack.zip": "4fac148e4f3194e23101fb38b7b21f4add929d58ddd67d6f90a3b80e967f4124",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W4B_Muscle_Model_Lesson_Pack.zip": "06e1c22c2053454295f052d061fe30e8b2e5060f90d0150b3c3ed83a7221c409",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W4_Teaching_Pack.zip": "0d5a42b5d9ac97f4f0af350f330a9fe9b916336bad313e7609cbab7dad7e5ebb",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W5A_Body_Needs_Lesson_Pack.zip": "e12b94d23134306ccb370b27f727209e7155ee8a78feb39a469e6677ba323c35",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Lesson_Pack.zip": "13d427fce389894551bb742f7b1bfc8f56a16e2b9caedcc8590207486faa5d82",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W5_Teaching_Pack.zip": "315b709ddd5d62b11a34dc6e9367e2e9b505ef4a587e604dc5aad481480b04ca",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W6A_Balanced_Plate_Lesson_Pack.zip": "e9a4fa0bc64f300ae5ae975f8807e6b07413c7edc32e71fdaa7b9c17682ea807",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Lesson_Pack.zip": "38ae5d0784628168c063e891de13237b7048cb3960aadd464211e650b16c7f83",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W6_Teaching_Pack.zip": "75b22d112c036bfb078e2c9a9de4659cdd2b37c694969edf9204014fcc7579fa",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W7A_Food_Sources_Lesson_Pack.zip": "bfef72a01747997638d8785e0e293b688422faa8269351894765f58ba04e95fa",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Lesson_Pack.zip": "dcb4b054b2b36e1d8a7fa1cd33ff651e6bda9270b1ed24edbb62a0d6a53596c5",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W7_Teaching_Pack.zip": "d6ecae6d43271f1fe158072c9bec32dea8e8f709e30991387797a792ded445f8",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones.pdf": "1f0ca49ea1acf6b067f7bf5ff0e9080c27d110e5eb9d19dcb0592c4f584aba19",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones.pptx": "5a5d98676e0be5cd7ecc9a00e209f9f4eecce5054227899366e52130ecb600b7",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones_Pupil.docx": "e590c44fd96e55d3bc92a61d891620220e7f7c4662bde06ae8fc9d705d65c5c0",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones_Pupil.pdf": "9e2869b52891dd5e1de37b41aca77ee19924e63611aa22a61fcc5b9ded1bd04d",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones_Teacher.docx": "6817f0ad0fa0c33c9c92ec456b58ac28fabaaa2cbabd003de9949ceaa8808679",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones_Teacher.pdf": "e94cfc2c8575b4d8c32c226971e397b5103ea14397d82f8a08aeffdfd163e584",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence.pdf": "b1cc30baaef2c45f094c6c39e0773deb41bfd32def8119781e33e81f07b5c9b4",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence.pptx": "39184947783d5468062b4d2d1f8f5a975f46c64b5a4ca8372a039f2fe0fd7c3f",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Pupil.docx": "a2cb2fd4a134c51ac28a2c2cb09de0f82a6779641cd257f1c3d89331f2d88572",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Pupil.pdf": "294402d9ad13dd81e46ed540e5476a0418221fd6b98b6f98aed91f9ad3ba63b6",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Teacher.docx": "a6f287726b3b60cf97a5bbde3eed8502d3c2f12a2b4bc0e6f1c506a5f4b799e4",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Teacher.pdf": "3240771d3cdbc0a2d8ebbebab479b91d9e9a9a3b798496fa059ba2fed06d4cee",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs.pdf": "51d89b697ebf7771ac84c51a411d09fec61ae8b175da30a6d73947db923d72f6",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs.pptx": "a4c7e8455f2418af5f905be3871de2889972c5a8cd583944ac360430eceb096f",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Pupil.docx": "238e91231b59a09e287f676327fb418429fe26cd3f49bb399f855c8e081ea505",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Pupil.pdf": "d96c1cb7e9142cfdbc2bc49ee8417810579ff89d1bf3b761c37179b1ba4cad2b",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Teacher.docx": "0a879a79cc46acd177d16f9d873d680760b26633d0c33ec7e8bd9612328798ff",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Teacher.pdf": "73f3d720d0fe471dc39b92d57106bd62019ba406d1d41298fd32de998cae3a1a",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model.pdf": "0b1566efc540e26bcafa9e72791984de88425f16aa436fe6f0a9e5c1b2f2e5ae",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model.pptx": "b24c0e54d88b5da958d19c12ddb52eadbb23d2d1f3e5393337fcdea5c94ee8e8",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model_Pupil.docx": "3b2289670dcae3ec16549ebf7112699ac143b41c2f55357e16e0ec040e8654ab",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model_Pupil.pdf": "03e09cdd018a84ce834868d02570cd4853b6083c2490828e3f1be082c063df09",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model_Teacher.docx": "3c36d4624a2b399fc58c40c0dc1a97f1ca096f3f74ac9bdd778b4c2deb82c607",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model_Teacher.pdf": "932a4c4d166be520db4c5170ea06dfc2db902f335d9d12e23eda995b90358420",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs.pdf": "a1ac975e3c79bbbf4674be97f2912f0b7d3964bd7ea867baffffd44b3e919791",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs.pptx": "ba3a64adf8823b2091e730ba86945d2b1ab2f48152934470379ce9975f3600e5",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs_Pupil.docx": "d1ec2d9908967b0480c27362b6fdfdf0707c3a2e106d837b1bd0fd700bf3246c",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs_Pupil.pdf": "815a92256411b0b4a78065583e18001ffe7fa87ccb5596ef2dbfe70c5b6fb30b",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs_Teacher.docx": "827c18499a2b23082720f8d0f4f5cdd1a505f424d7662e9b40d810639eda8a9e",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs_Teacher.pdf": "ac5adb8bfd6622721adab980e588e1fff5bf271c9e4727d45d1bade3bd73ed31",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission.pdf": "af30b7c296d44297dfdd452ac3fa54eeeaec111f6cbaf2baf300ff867a4e50f3",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission.pptx": "470b3a8cd7b5fcf46576618096ccc6d48e50d178956c9a135495faf0fbc1fb9f",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Pupil.docx": "1c35956adc140ccc3fd7f062573431d5a0dae587e169cf3dcdad3e46cde40e5c",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Pupil.pdf": "55cc2b449f47fee004c21b9bf2a5f16a5cc0bc782737cf50b27ad52dad56a523",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Teacher.docx": "e0e2d961cc52c9b35de6693cebc5a029cec912ce900117778eaab9213c051e32",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Teacher.pdf": "b886316ff8ced7289908c2dfa82381faeebbbde3e3da7e04c2bc21dbd91f2cc1",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate.pdf": "fa19e297bdda513d905186dbcbad9b6a1246028a8e0e5fbe46fe3206eaf9e991",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate.pptx": "fc5a2a9cdd9ea7c887bbd67e9a232f438d0f206bcb8a5122f3ad08e53995d20b",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate_Pupil.docx": "6708fed893e35dc857979a852eac955cd404bfc57ec96f6ccc369fbc25a59346",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate_Pupil.pdf": "35e335fe516188160a095c07a29611e4590ee31e4fd918433158961bcae552b3",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate_Teacher.docx": "e7af886db2cc21c814d19e269fb94ea829c9d8fecfb606e40f6b8e0be97e0b7b",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate_Teacher.pdf": "2b168fe89512ff480805815d4d36c6e4e8efc4052718785187d401f38863ea57",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison.pdf": "971209f2fa170ce5e068c4925c82c497863e592c19ec15126cdaabaf836b6ea7",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison.pptx": "6ed1d18a2c63330106e4c99803612c2f7d98fdcc9914721ce7b82dbf5b448327",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Pupil.docx": "4f8c4387661495712ed3f75f1c44b120b8cc1c85460366d858fa1ded845cf6fe",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Pupil.pdf": "3e9bb2b7bbf658e6c5e38dfd5e7459760c2022f47be6dd63c141f616e6c40211",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Teacher.docx": "9a21eb7538dd1b69f5466df74c587878e71e0899690c702c93013028b2daf9b9",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Teacher.pdf": "cb15b4b34309b1f3d8ab69fff702ac722441591b81cece4681a30df941bb6c5b",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources.pdf": "a334eafc8b9733eb889b983451ccd49c1227654fb6a92ab2ff78acd4ad8ec271",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources.pptx": "ceb4aa9f21faa2a5124c78cc4f45bed7495214cf0a48b672584bc4a0a7740094",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources_Pupil.docx": "d7a06b89199977cb08944dd4a34ad74bc0521a792c2082a507063da7f27662d9",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources_Pupil.pdf": "f271d9b496c01d005fe89900c021c949f32be70b700d5c7ee0cc475b8d013325",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources_Teacher.docx": "290d1f618e500a69388ac37622e1d901da1f9c2b11a4e31cf410f6e331548f8d",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources_Teacher.pdf": "12e7f1221ee07b7925cd21b84465e859461ab28c500dda36837c158f1ebe3c85",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation.pdf": "12bb6dbd60ce084787bdfa9ea4b2675b59008bd12d46cf7240e4d2943cc04d3c",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation.pptx": "2275427f72ef757fb924bcb3fc2d551ceb44cb8c405696130f248f1d98d9e7ba",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Pupil.docx": "9fa88527a2f29acb308e1df6f6c02752e25b226a031d1f3026be10cc7ec0adbf",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Pupil.pdf": "463b48816d18e87e8b817823be93f2be903a3e545ae89751657839dd92a567c2",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Teacher.docx": "83d1a1f7f68cc59fba049b62456c133aba66b9c7f935ac0ad9008adae64a0a8a",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Teacher.pdf": "f7cfef20b1b5cf898e81a975ce7a29edc218cf50928466b34e291661afb5e70d",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W3_Cards_and_Labels.docx": "3ca40795c97127ce0747a2633506841b51308f1f644e268571cda85f6d7a1f9f",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W3_Cards_and_Labels.pdf": "c160c7552bd94ab125b18463225e507b5c20e124a5533dad3a9c9d15ee13de2b",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W4_Cards_and_Labels.docx": "c476366885cd3810e2bf2ed3d808c9eaf25df70176de0b25a226149559f4cbd0",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W4_Cards_and_Labels.pdf": "70c5bae64f7be13e70539c6da37d0e57f93917a8ed02db371f387ff498ba1493",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W5_Cards_and_Labels.docx": "13926ea62c3cfc1717c3b8179df3adacd98909de665c93cac7a1384c7da6e7e4",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W5_Cards_and_Labels.pdf": "ae50db983aa2176447a45c4ff2946ba83f5581c4eea6a6b857e39a1cd9670b4f",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W6_Cards_and_Labels.docx": "f53598afde91a6fe76fc54101e342025ba6771cd0c19a6f470231fae03c50d00",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W6_Cards_and_Labels.pdf": "d8801d693e4c94a3482611f00a6e54d78060f059c0501494395b014fd0b5856e",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W7_Cards_and_Labels.docx": "be1389beea7a56fa6031a672a9af6c81b708ca209eb5a3130c7a5969616ead2c",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W7_Cards_and_Labels.pdf": "dd6e94af055182f7ed952c3ea26e2257bebbfd136b06b715138845de7acad540",
        "Science_Teesside/Teaching_Packs/GROW/DOWNLOAD_INDEX.json": "0e4213c0b3ad32b48556d587a96849e2132db0aef0269358ca4b0c66a6808f06",
        "Science_Teesside/Teaching_Packs/GROW/SOURCE_MANIFEST.json": "416689f96e249e0e7eb4bc34ab21647622ed3b75fd563acee904f7a656e3e7ab",
        "Science_Teesside/Teaching_Packs/GROW/START_HERE.pdf": "93a7e61be570fa6934e93973b1a4f4eb200df3da24f83b8ba45ec64ccbf80375",
        "Science_Teesside/Teaching_Packs/GROW/START_HERE.txt": "f07e424472d2b73a80ffc68b6756433759010f6d9c214284ebc7381ad22ebcdf",
        "Science_Teesside/Teaching_Packs/GROW/assets/made-by-matt-approved.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3A.zip": "b63aa7af2a3fd020e3f45912c899319ab9d422ceb9b1aa4997bf7bdc9c64db1c",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3B.zip": "341299ec6c83f72daa9efeb74277fd784e7ae0a765b173f2af07722050825b4a",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W4A.zip": "1ca29cdeccbeef9738b7ecda8b04165c902570c2b8a3d62b9830f4ef18285414",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W4B.zip": "04f75505d18379d42bd0bd49cea9711e0ef2b307a3da0489571bf51e522d0ecb",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W5A.zip": "f2ba4544e144388b528855471e2d708711e1bf035f16e83d1dbfd2a5bd01d929",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W5B.zip": "3ecec0ecda17f3b9dfde978c79bc6be4be146bead1cf19ca5673c1f3e0709c1a",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W6A.zip": "6bb47faf87f4615a3d3635d989c532bbf006d6a3f3e119ef91a5cf2721cef240",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W6B.zip": "e339f3a8df58d05514c243cb9c2ab086838eb31bacb1cc018143d555ac038ad2",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W7A.zip": "9ecbea14ac39575fe5e34cee613c8005899f201898f86a589e9fcf30531e398c",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W7B.zip": "c0b87a60c604801974de804bad78a762bbebce76b87f817d9038a0e4186a28ea",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week3.zip": "06cb316346fc16111652a1dbbcb789ddd3ba0de9ad3902d2258a4c2ba711eb55",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week4.zip": "62b992eb73b1bb82395e0ff33628cd593319ecfc49acc9edc5837b1c07431341",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week5.zip": "42a480fe7f6cb78a52f6cc9e1062f0301539e73d70868f3c2f563331c68d5c54",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week6.zip": "d5e895b993f79615ee7c61dfc814bde9dc4f30bfe80a8b8201e82e4349750b0f",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week7.zip": "034b9b5901fe203441b47d353f50e9df8e1f7d59d0e14d77763a2c8bd87be1d5",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Weeks3-7_Teaching_Pack.zip": "533e67e6d99dbc8c3aecc6e6af4383c26ab58dac60442a72c7acc013e6ed68c5",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_Science_Autumn1_W3A_Friction.pdf": "cc4d61d340630d744f3c832386cf1a2fe65d4b24dd7dbbf1334c5a44b6b809d8",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_Science_Autumn1_W3A_Friction.pptx": "4a0b2bb17b547f1aac0e15412c65dfa9392102bb204253634ffe6c7e03479ef0",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Pupil.docx": "3a19c281e5c97c9d857b17ee9f05d61c6cddd462d50df834f9af582d6e2e00ee",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Pupil.pdf": "e92abb03d6672bcbde4406e1f1c3dfee24c4a03b705b215153bcc6d8006b6402",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Teacher.docx": "117a2cd3c8381f392cfe0cad35de475d40a076b055e510ebabd81587b62dd6c5",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Teacher.pdf": "fb5be6c3fbee670c5a75702aad27fa35119838869307884b017e74d9a01cbf23",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/START_HERE.txt": "aecefd50143d87b71dd8733335ff7703a4c9552df45101f917bb2cb82d807685",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test.pdf": "eb2df0fd6891315c9f0cf062d8507f0d4d75de598eb7111c5611985f2da8e4b6",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test.pptx": "a2970b9a51cae6e03145a58e1d5d5b0c0c68c150016ac786a851928f96250bfa",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Pupil.docx": "5157aec918a97f3555f7b852aa73621614062c906faac9b9b1a48adceaea13be",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Pupil.pdf": "f5b02c29acd794994ed68363d00160c75f478adc64cbc38a0be0b61dbd4bbbc9",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Teacher.docx": "40917fcffe6140e87a56900683917c53f98493eeab7e10b4e83a64e074c1e3b3",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Teacher.pdf": "1ef1f1fc59af0f77ca33c1290764c133e91fac6b33990f969368885392ea4881",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_W3B_Friction_Measurements.xlsx": "7ab6650a16051e655dde2f48928810cb2a825e07d4d0a028fea7cc25ee64b1d5",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/START_HERE.txt": "a14214b3e256d5e99396d03292b4b1281b56b56c5a8725386c09d11c275c45f4",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms.pdf": "a349ac6a18474e4b48b039266acd654fc082ac4fa369232937a8ba9ebc92a5b9",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms.pptx": "2b2f4680dcd7f4d0f6d35856e7ab8ab1a4f7f301fb20f2b160d3e6d2953c0b86",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms_Pupil.docx": "3f73976b765d6286c30fcecf4ea380270aba2a8959664402ff380f1eb2c4538e",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms_Pupil.pdf": "23db87e56ebec1431862918f9f9e3d921905897b229ab72d732ec11f3645a6ac",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms_Teacher.docx": "2c8393973e059563ceda7fe13c553e0c13650c97f458bf9116bdb36c2145b30c",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms_Teacher.pdf": "23e6316925351ab42949e020e293c9fa0ebf1b1eadea34e213555dd623a5fb73",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4A/START_HERE.txt": "eb41429cf022ed25c1dfc3cf05d21787608cddc59982cc9d5aa2357135fc842a",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test.pdf": "2f3bef61dcb53ae5d0e0b4f9da653dc8549be21575e2a8a80f609280eb3c202e",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test.pptx": "8dbd3514ff2722a35265d3ec158e090a8e98eb3ce4a23d02616e20e4b2894db8",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test_Pupil.docx": "7777599c6df3e3be96ea05c13dd761b0ab25937f5c4f23403c38a83e095b0c8c",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test_Pupil.pdf": "11f7fdbf849ab15fe8cf48bc17960ca95f87f68c16ede057e34e2752c7c68128",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test_Teacher.docx": "2105eb1fe256010c476dc2848c9e92880793c46a191472654342fe2b50b1d0b1",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test_Teacher.pdf": "dd34d64f23a1ffceb86460cbc483570b2f45481e90aa489779a40b5459b41f04",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4B/START_HERE.txt": "ec3da721d7bce358ce3458b77bbc5bc0c8ab01a305486e2c711d7919cb5daaa7",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test.pdf": "176d615c49db7f431d93d88596fcf1ac593ed12137ba5b106d05e4afba805cc3",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test.pptx": "7b7f9c171d16f73bfd49fb3dc0d8182f0a7b930c346102c3e1cea4a02a6cf3bb",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test_Pupil.docx": "970a042c627703b0b74347fc407be62704b784f499dc852ba303aef3774aefa7",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test_Pupil.pdf": "0ca86b7bb6f7110799dd8b421d7e27a8ea5a2988a3166d0c4443c18cf13542aa",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test_Teacher.docx": "60e72038bfc0ef420fc1a03210005c1477b3f856d522e529a5b691a079c72a20",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test_Teacher.pdf": "0b2f0b87bf918db8bb998d5a869b27b80690a342fa03dbb8323175cb967050e2",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5A/START_HERE.txt": "a290efa290a30a831a30ef59dd7fd7826ff7d8906de67c3698caf19619681ccf",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical.pdf": "20cf34f30732f6c79cec236a53ae1ad1f351cbb36101fe97990c79fbb7f71073",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical.pptx": "8f428b4e044d005f01776b9b2e8b2b2a597fe4e896c807491f52e2882f3335ab",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical_Pupil.docx": "ce5b479257ef70ac62e7b72616633c1fc52f6a8f209cf9a074028ef9312e5ec5",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical_Pupil.pdf": "1c781fac4696d713109a055740176cc6412e022458f3d2dc70eb2e3de8b4fb56",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical_Teacher.docx": "1872149f4fa2134a451464854f656aa0c8252f53fd6bb639b3c6c3f5ba788ab4",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical_Teacher.pdf": "8cfa35478aad3e6439c045c38f215e7bad008300c519b45cedd320a395603773",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/GROW_W5B_Fair_Test_Measurements.xlsx": "746d64a30be2304c439fb5af7ef79b25dbe8f69d51c8de3c12cd22b8f2ac2104",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/START_HERE.txt": "d667aaa4d4c65214655f7f9744b7b8b240d5a5d39539300c35aa5f4abcf65ed1",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets.pdf": "2390f82abd066dfe7e4f1b7ff2729367e76374323ea62d54d98da48cb445cb1d",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets.pptx": "e19a23cdfc5fe7731601822425206ff8498e34457b9fd509b74e471285d0e2ce",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets_Pupil.docx": "ae82024e6ce3a073635f5c6f521281c33e2c489a8eae4dd15dfce1fea72409cd",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets_Pupil.pdf": "4e7100f8729d449661165c4e8cc14006b46b966d85f49af1c542598607dc599d",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets_Teacher.docx": "864d05de1c8e74bd85a1f569a1b81bb636186b8dc4ac530bf2fc3bfa7af65c9c",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets_Teacher.pdf": "9b7a944d3e07ca4ea1659ecfb8b1f4c22c55725904265a45636fa34d12acf3bf",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6A/START_HERE.txt": "922b972648e167684acd8d528e0842294ef89a61478b74b65d74ce22c25e15bd",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets.pdf": "872657063b1d5d2e3fff8cc1ad19b65ccc950700148975909d67c949b384e94b",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets.pptx": "aab2a825735a5e712c3573e51af7d2d4e1e51c363714f1aa37d0769879271b99",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets_Pupil.docx": "3d4cf06e4a524bd159523deb07c838df36c2dcbbfa1d1bab0f185c01b3218959",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets_Pupil.pdf": "dd598955be9919c766d018de14fcb94b1a2f13031088e07a29e617372d8bee03",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets_Teacher.docx": "bcb85781f778029d62e894119ee81a1ea6731831b8f25b553d80ec846c56c8a8",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets_Teacher.pdf": "bcec7dd7559fb5e715d55445ad9dfe1b4d0d1e6b17b7dce572aae377c5f0227c",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6B/START_HERE.txt": "488a26039677af53ef3d8435dd412e98406a807d10534a7725d2261d06869d23",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon.pdf": "01a3baf39ab4ab886d019c8d10a0cd5ffe14562b0aff744c53566cd612abe344",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon.pptx": "04d31d13f08d870c490a41d094c407dfb05fe087fba7d97f6a2ff5036f87bf1d",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon_Pupil.docx": "da040e7929d41e9ee3ecd5ae324e156392e5dc7459d766111dceeff8d4cb1624",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon_Pupil.pdf": "c47f050001b50d77dfeedaf15c2a4cc9f8647912f0c8d3f76a450d0dbc504c95",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon_Teacher.docx": "1b26d4c13ba043878058e066f27aecea28e091235d49dca51353857d471e37d2",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon_Teacher.pdf": "cf04d69a99d8ebc481a6663465d25d21823f97e8cbb1a8ba5398db5dd83f9b7a",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7A/START_HERE.txt": "447de6ad4347b097a16c09d40df429a4908e381b6ed9c36084c2e1cbdf6916a6",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon.pdf": "2db8f92fe0ab1e49a2108630c4a227e6c746c977858666c10a7003177c474cbc",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon.pptx": "92e209589646b2fabbf9b1ac4200cd27cfa786f11894ca6e39c14fbced5c45de",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon_Pupil.docx": "df73b1745646e571c76e869e303a753e48d18124c0701e7c87d9c10b300d9fb5",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon_Pupil.pdf": "b5185b1acbaeffbec69b59a9fa4e3b5b501168d052480e38e7d2ec0bc0a2b926",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon_Teacher.docx": "f3ffa819d39f106153cf36194ecc17d9553bad3de2a68a68bb988f84c5ea632f",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon_Teacher.pdf": "e03def3c15162e8943e22f15f18456a90d4e99fc539f7003af87a2b1160ad1d6",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7B/START_HERE.txt": "10d6ba34be76c3a7d82a346e83a65c86612ecd95505e63fc797a091bed945ee6",
        "Science_Teesside/Teaching_Packs/index.html": "d2957a0b87eda3a3e3e2f8bfc25a9f74d94f1ab1bc789246cdbee26c1ed6cfe0",
        "Science_Teesside/Teaching_Packs/packs.css": "1ec38c42f65437e0f7997e8f9df8bc6084afd20f46bd334b43e4c22c3976b048",
        "tools/science_teaching_packs/BUILD_QA.json": "d5ee55a25c15ca86dbd6324b417c70d672e1d0c19a1fa6462f35cc620927a2ff",
        "tools/science_teaching_packs/BUILD_SOURCE_PROVENANCE.json": "bd3093b818cd94ab74260f28f2c8ae08e77fbac307e8dcd0cf2a77540e299197",
        "tools/science_teaching_packs/GROW_QA.json": "a8cdaa361414a3700c463ea40e0a159029db3fb803024e50b0eb39d082c6f364",
        "tools/science_teaching_packs/build_hub.py": "4c16af77be7961eb89eac9fa1975fdcf1bec3774d731e4675cc8ef2d74bbe827",
        "tools/science_teaching_packs/check_packs.py": "9f0b9cf345b15543eb543988e4472ac37b22c8ec13a984b601b8baef1fc05487",
        "tools/humanities_resources/PUBLIC_LABEL_CHANGES.json": "6ff5c272460a5175a48b6cb98cc1c1a4f8eaccc42da4709ef7e2653c1f6a8179",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/BH_W3.html": "3cb06cdadc3af0b852e54192a10203295be12c6139601e98e86c9496478a79f0",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/BH_W4.html": "ad5f0adbe53b57189e3c9958ec5e79d3f9b91018e6fc85001140141284e5c387",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/BH_W5.html": "c67cf1fbb4e37c3f6bd9f7e6f69e56eeff26150f2afa8447d461a5684dda2665",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/BH_W6.html": "6e13cc25bcf3918309406ec1269b0765117181e90007306d76e115d585319717",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/BH_W7.html": "b8d346263c2a4e3fad004273c2eb37ae02996ae6566eb1d02605aad203aa07d5",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/BR_W3.html": "68433d21e8b4c04a9c38b34b89afd6162fefcbae3b90ced8779b01341f5b7948",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/BR_W4.html": "48856c5185b28621ca9c7a3c4d668fd0402d69039351516753dae80c3b393e65",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/BR_W5.html": "7311ca67b4a83a5356149ed7b7e96c19ef0742c9b6e1fd736a4eefbe97f33796",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/BR_W6.html": "4547ff74bdc25dd5f3de163a57fabf0cdb062ab922b5be13e6a76e4e31f6ac7f",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/BR_W7.html": "7575fb9d4d8e28ca487c89a91dd70b556dff94e67a8723b37b63d06d363c6537",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/GH_W3.html": "8a28b949bd4a6c4e2a7965e5edc07bc20454df22ac0ad4fa6d94950119286bc7",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/GH_W4.html": "f84c91ca65ca730620172ca70b551061bbe568017d6815b2b12df9be0e4dad55",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/GH_W5.html": "d9a0680fa3928b1d7d23333c001bc7a3d70d46bea9612ade3b9588b97ba4bed5",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/GH_W6.html": "5119f8b0b33aeb3d225be4af3c883a88476d62448d2ee5ad5cfa161b231f96d7",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/GH_W7.html": "2839c19f411983273d84b098a6d1db10f30bdd7ac975b83ded2061512157d347",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/GR_W3.html": "df6893b26d5dad94d001e20bd4cd2bddd0dc8861b879fa16fcdf9546f094d1d7",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/GR_W4.html": "9c1bd091b3d792bb8f765c8ef8ab781c46952423d85d2dc7f428d7d66afc7476",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/GR_W5.html": "b750830cc0cb162ab721d4357a882351b7c82c36ba5a5bbdb09da87004cbb19d",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/GR_W6.html": "609c398050b997a8e8f84dcd38e2ae3a4e8e46f444b927f78a7d55de314d5686",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/GR_W7.html": "6c196a0bd2db17728722d456a1af310f17e8220dcd6578bd9b35643aea6fb3f3",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/LH_W3.html": "95856d0bd41abe02aca8a405718ca4b413e7c797673ff5beffeca13b87abe691",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/LH_W4.html": "51ac458f002341ba2610fd5dbdfb3beaec961606c57f953c48b7469baf8f6d73",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/LH_W5.html": "63ed872c7b5534d8d1c4ffde723fdb7742789ae7bef705b2b9cfd3eb2a34993d",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/LH_W6.html": "6ea47b86c65a116d95ce2376b16dfd9fe773c6290fcded2efa072db19be0dd22",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/LH_W7.html": "33ac63f9fbcf9c36d67658e87614f6e1e904de45aa3dc5128ab7fed94579f803"
    }
}
# END REVIEWED CATALOGUE PINS

# These semantic pins are deliberately outside the movable file/manifest block.
# Neither the catalogue pin tool nor the generic manifest pin tool can bless
# an edited, deleted or reordered original resource, or an extra lesson row.
CATALOGUE_ORIGINAL_ROWS = 734
CATALOGUE_ORIGINAL_ROWS_SHA256 = "b8ffcb16f5fd2a413e8a0b06ad2d4b112f450364fa294377869dc32c8235bb2c"
CATALOGUE_SHELF_ROWS = 3
CATALOGUE_SHELF_ROWS_SHA256 = "a8bca8febd5bd9482aa7cd648577159cb69c52f77ff1e754fd041c8c81819621"

# These named review records and review tools can change with their reviewed
# transaction. Tools are not served assets; they are reviewed as executable
# gate logic, rather than recursively hashing themselves. No lesson payload,
# game payload, shared platform asset or arbitrary directory is exempted.
CATALOGUE_RECORD_PATHS = {
    "tools/catalogue/STATIC_CHECK_RESULTS.json",
    "tools/catalogue/DOM_CHECK_RESULTS.json",
    "tools/catalogue/RECOVERY_2026-09-05.md",
    "tools/catalogue/README.md",
    "tools/catalogue/pin_catalogue_contract.py",
    "tools/catalogue/verify_catalogue_contract_controls.py",
}

# The education publisher is executable release configuration, not a hub asset.
# Both callers advance together to the same reviewed Site commit. Permit only
# this named workflow, and require its complete reviewed bytes on every run.
# A broader permission, trigger, job, floating ref or mismatched builder is red.
PUBLICATION_CALLER_PATH = ".github/workflows/education-pages.yml"
# Reviewed Education completion publication caller, Site PR #268, 2026-09-06.
PUBLICATION_CALLER_SHA256 = "dede47d7314afadf97d08e1753a1d4d6e5acecbf3a84ec5fc963bf20385b009f"
PUBLICATION_GATE_WORKFLOW_PATH = ".github/workflows/mbm-cross-estate-unification.yml"


ALLOWED_DIFF = {
    PUBLICATION_CALLER_PATH,
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
    # ORDER AAV-NIGHT, 2026-09-05. The same shape as Ruling 6 above, recurring
    # because the campaign ledger was renamed and the boundary still names the
    # old one. A night order requires a ledger write on EVERY stage, so any pass
    # that touches the shared surface and records its work reds here on the
    # record rather than on the work — which is the failure Ruling 6 identified
    # and fixed for _teachgreen/DECISIONS.md.
    #
    # Every entry below is a file that cannot change a studio's served bytes:
    # two Markdown records, two gate tools that run in CI and ship nothing, the
    # CI job definition itself, and the §6c hub control. None is a served asset,
    # none is in CANONICAL_HASHES, and none can alter the standalone/offline
    # payload this boundary exists to protect.
    "_sownb/vb/EASTER_LEDGER.md",
    "_sownb/vb/EASTER_HUMAN.md",
    "_sownb/vb/tools/g26_reading_band.py",
    "_sownb/vb/tools/g28_cell_existence.py",
    "_sownb/vb/tools/mechanism_battery.py",
    ".github/workflows/fieldops-p2-and-sweep.yml",
    "tools/verify_hub_catalogue.py",
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


def catalogue_errors(root: Path, kind: str, text: str) -> list[str]:
    if kind != "lessons":
        return []
    errors = []
    wanted = CATALOGUE_PINS.get("visible_body_sha256")
    actual = hashlib.sha256(normalized_visible_body(text, kind).encode("utf-8")).hexdigest()
    if actual != wanted:
        errors.append("Lessons hub wording differs from the explicitly reviewed catalogue digest")
    try:
        rows = json.loads((root / "resources.json").read_text("utf-8"))
        if not isinstance(rows, list) or len(rows) != CATALOGUE_ORIGINAL_ROWS + CATALOGUE_SHELF_ROWS:
            errors.append("reviewed catalogue requires the original 734 rows plus exactly three hub rows")
        else:
            def row_digest(value):
                encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                return hashlib.sha256(encoded).hexdigest()
            if row_digest(rows[:CATALOGUE_ORIGINAL_ROWS]) != CATALOGUE_ORIGINAL_ROWS_SHA256:
                errors.append("an original catalogue row was removed, reordered or edited")
            if row_digest(rows[CATALOGUE_ORIGINAL_ROWS:]) != CATALOGUE_SHELF_ROWS_SHA256:
                errors.append("the three reviewed catalogue hub rows changed")
    except (ValueError, OSError) as exc:
        errors.append(f"reviewed catalogue row preservation could not be verified: {exc}")
    pins = CATALOGUE_PINS.get("files", {})
    if not pins or "index.html" not in pins or "humanities_teesside.html" not in pins:
        errors.append("reviewed catalogue file pins are incomplete")
    for rel, expected in pins.items():
        path = root / rel
        if Path(rel).is_absolute() or ".." in Path(rel).parts:
            errors.append(f"invalid reviewed catalogue path: {rel}")
        elif not path.is_file() or digest(path) != expected:
            errors.append(f"reviewed catalogue bytes differ: {rel}")
    return errors


def publication_trigger_errors(root: Path) -> list[str]:
    workflow = root / PUBLICATION_GATE_WORKFLOW_PATH
    if not workflow.is_file():
        return ["education publisher guard workflow is missing"]
    # These existing workflows use explicit YAML block lists. Read only their
    # top-level `on` block; comments or similarly named job text cannot qualify.
    lines = workflow.read_text("utf-8").splitlines()
    starts = [i for i, line in enumerate(lines) if line == "on:"]
    if len(starts) != 1:
        return ["education publisher guard requires one explicit on block"]
    body = []
    for line in lines[starts[0] + 1:]:
        if line and not line[0].isspace() and not line.lstrip().startswith("#"):
            break
        body.append(line)
    errors = []
    for event in ("pull_request", "push"):
        positions = [i for i, line in enumerate(body) if line == "  " + event + ":"]
        if len(positions) != 1:
            errors.append("education publisher guard lacks explicit " + event + " trigger")
            continue
        event_lines = []
        for line in body[positions[0] + 1:]:
            if line.startswith("  ") and not line.startswith("   ") and line.strip() and not line.lstrip().startswith("#"):
                break
            event_lines.append(line)
        paths = [i for i, line in enumerate(event_lines) if line == "    paths:"]
        if len(paths) != 1:
            errors.append("education publisher guard lacks explicit " + event + " paths")
            continue
        values = []
        for line in event_lines[paths[0] + 1:]:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line.startswith("      - "):
                break
            values.append(line[len("      - "):].strip().strip("\"'"))
        if values.count(PUBLICATION_CALLER_PATH) != 1:
            errors.append("education publisher caller must be watched exactly once by " + event)
    return errors


def publication_errors(root: Path) -> list[str]:
    errors = publication_trigger_errors(root)
    caller = root / PUBLICATION_CALLER_PATH
    if not caller.is_file():
        errors.append("reviewed education publication caller is missing")
    elif digest(caller) != PUBLICATION_CALLER_SHA256:
        errors.append("education publication caller differs from the reviewed immutable publisher pin")
    return errors


def boundary_errors(changed: set[str], kind: str) -> list[str]:
    allowed = ALLOWED_DIFF
    if kind == "lessons":
        allowed = allowed | set(CATALOGUE_PINS.get("files", {})) | CATALOGUE_RECORD_PATHS
    unexpected = sorted(changed - allowed)
    return [f"standalone/offline boundary violated by changed files: {unexpected}"] if unexpected else []


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
    errors: list[str] = publication_errors(root)
    index_path = root / "index.html"
    if not index_path.is_file():
        return ["missing index.html"]
    text = index_path.read_text("utf-8")
    errors.extend(catalogue_errors(root, kind, text))

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
        if kind == "apps" and normalized_visible_body(base_html, kind) != normalized_visible_body(text, kind):
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
            errors.extend(boundary_errors(changed, kind))
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
        for rel in set(["index.html", "resources.json" if kind == "lessons" else "apps.json", PUBLICATION_CALLER_PATH, PUBLICATION_GATE_WORKFLOW_PATH, *CANONICAL_HASHES] + (list(CATALOGUE_PINS.get("files", {})) if kind == "lessons" else [])):
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
