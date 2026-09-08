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
    "resources.json": "ca4ce5ade391130b2dee4a85a8c57363d2c4c6ce175f0a62cbe46e245a8a9e1c",
}
PIN_COMMAND = "python3 tools/pin_manifests.py   (from either checkout — it writes both gate copies or neither)"

# Explicit education catalogue release, 2026-09-05. Matt authorised a new
# browsing design, so the old Lessons wording comparison must permit exactly
# the reviewed result. These pins do not exempt a directory or a lesson: every
# named byte set is checked, including additions, on every Lessons gate run.
# Apps retains its original authored-wording comparison. This block is updated
# in both gate copies by tools/catalogue/pin_catalogue_contract.py after review.
# Apps Creator Hub wording after HC5 D2 (Ko-fi line removed), reviewed 2026-09-07.
APPS_HUB_REVIEWED_WORDING_SHA256 = "696efb97549286f33b9514308bee48d82d3af654cf611e1f522d6362adcedc1e"

# BEGIN REVIEWED CATALOGUE PINS
CATALOGUE_PINS = {
    "visible_body_sha256": "8b140286356c91f346d64c5ad32ca44aa6a9b467d1dd89525eca5e4728d8f444",
    "files": {
        "index.html": "deeaf7df09b256a115d8a9b24637d1d2e787bf90245cbf0f158a438bb5b7bd8a",
        "Science_Teesside/index.html": "47e85a28c6cb17663a051f38646126d0afea0e59d71942671c40553567424fd9",
        "Humanities_Teesside/index.html": "7594ce3f6bd34025e32f556d736d39fd218b409a36511ab57e779c4080c4cd86",
        "humanities_teesside.html": "1e2faab06cb4caf4a26f377200a55cbd380c7f3ceada74f666998b47611896b7",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/index.html": "4e25eb9ca8f9f93c720d88d945f3d6d79580f3362a88698fe7af75d146f01e96",
        "assets/catalogue/catalogue.css": "59abee137c41a8a015e42cf0b32d20b7f4e5fc8e3d236a1cd735322386bf8569",
        "assets/catalogue/catalogue.js": "a0fd3efc8356377effad7249be7222984ce92947a8143259148851dc399de5c7",
        "assets/catalogue/lesson-navigation.js": "eac7081b5c02e450e5baa5200421e275196fb1f0e9599b5ffe9bf101ee593e99",
        "assets/catalogue/science-shelf.css": "f664655e57c086abe35499f5dedf737eddaa0942e6629dd4a7fcf4e801536508",
        "assets/catalogue/science-shelf.js": "b47b998866401f136968a2e1e94cc5beb65be83fbd342f49ff5a811804792651",
        "assets/catalogue/terms-and-styles.json": "1a0d8085e1054e5dfb361eb2e8d473e0ae72f9bff908e599cf19305c75827cf0",
        "assets/catalogue/science-shelf.json": "f933067000b614300df6da45ed0a3169c4ecff9187c7867de408f70bd4701371",
        "assets/catalogue/humanities-shelf.json": "b2facaa50c6781f0fdf19fad5b3b170bfaef54546c030e951956ccf47223f8c0",
        "tools/catalogue/build_catalogue.py": "4a009a17c37ae7336056329e2250c590910d6d054001ad92e57228e157bc8c90",
        "tools/catalogue/build_science_shelf.py": "a06ce779e4331661dadcdeb896b5d533374ca82bba812f605860c6fe53d11335",
        "tools/catalogue/build_humanities_shelf.py": "ef74f9eced59fd6ec33f22c02cf0d39d518ac6f2eb8873aaf21517859fb78662",
        "tools/catalogue/check_catalogue_static.py": "41923331f350007d958703697f4871a06ae07cee1512fba53730399e390329c9",
        "tools/catalogue/check_catalogue_dom.cjs": "ded778b35a0fba80de06cdbd6fd99afc30e126d2f1039033cf07b61472a6dab4",
        "tools/catalogue/verify_education_navigation.cjs": "3c2732e4d302579fe011745abdf7c36ffa63c062ee22e7777a1eb3876c615580",
        "tools/catalogue/SHELF_SELECTION.json": "95def027287e7cc1eb1190bafa21733c9c0999286c15a231dc17dfe7a56331f4",
        "tools/catalogue/HUMANITIES_SELECTION.json": "5df3e69d4d9d3825225bcc80376b3fbebf61656df6e333f6b9a8aaded1893bf4",
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
        "tools/catalogue/TERM_AND_STYLE_EVIDENCE.json": "852ebc9ca7ea616dfa4ae0929c42257dfcbb4f9813fd978e5fa2a297efd24fd1",
        "tools/catalogue/TERM_REVIEW.json": "b0ed0d82fe21a222c75f6a38390b01defc0d5d958fac8e85421b7901ce6d201d",
        "tools/catalogue/SCIENCE_WEEK_BINDINGS.json": "26e0ec9a1aabe2cb7dfefd7ffe92648db4ceeb225ec12e4bea3001f9659ddb06",
        "primary/year5/science/autumn/forces/Lesson8_ExploreGravity.html": "20047720bf1d309055abdf232d341b6fd99b833631efa0bcbfb3dabed9671196",
        "primary/year5/science/autumn/forces/Y5_Forces_SoW_and_Plans.docx": "ca36cfd92f1c768ea66f0eb748d47e6227f67569f77b5472d0da13d03f92f2e6",
        "assets/catalogue/science-download-bindings.json": "efb435f7e0dc4c9083050f5bb3e348494838422fe7de6e809fbdf8f877d9b10d",
        "Science_Teesside/Teaching_Packs/BUILD/BUILD_Science_Autumn1_W3-W7_Teaching_Guide.docx": "c4fd055acdb11a2310fe820b6f473733835dc4789b9151cd3377ec4d251f2196",
        "Science_Teesside/Teaching_Packs/BUILD/BUILD_Science_Autumn1_W3-W7_Teaching_Guide.pdf": "a479821f2de450e28bd414625f8066768d2c72423bd5ff76046536bf8f7a5d7a",
        "Science_Teesside/Teaching_Packs/BUILD/DOWNLOAD_INDEX.json": "8597bde197b2b816d2dd4186726ddf46a873f941e3aa7814d1d437aaa5733eb6",
        "Science_Teesside/Teaching_Packs/BUILD/SOURCE_MANIFEST.json": "5cd6246f8f7238adaff58122c1615b3ac6e4ccf1c1604f31aab080fd91394a95",
        "Science_Teesside/Teaching_Packs/BUILD/START_HERE.txt": "7dc574750bc326685d64d0abbd25b632e9f8a724c7aa84f1123055c7f148ec7c",
        "Science_Teesside/Teaching_Packs/BUILD/assets/made-by-matt-approved.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3-W7_Complete_Pack.zip": "e9d17beee1226ab799ad66a2b8c9d03240021b2f7d172c5da0f272f50e311001",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3A_Backbones_Lesson_Pack.zip": "37019741667b3523a5502fe61eff7edf47b995bbc4fe48a10f2b35dd8e1f3afa",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Lesson_Pack.zip": "5926e1cc19928a3e13cfc9a8301ea9d6bce0db4c9cec2f1df8aa0aef1f9a3708",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3_Teaching_Pack.zip": "ebaea394ec38ced318cbe7316a48aa2b0c43c20b4c625b7ca6e501257ac4923a",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Lesson_Pack.zip": "e01abf29890ee4e27d31139ed5da09856736cff16bd1d61d10d4af804c04060c",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W4B_Muscle_Model_Lesson_Pack.zip": "880f1e3883f13ce72f9f661112cc28c140c4d519f733a83bdd214c621857353f",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W4_Teaching_Pack.zip": "eb69505f3c10a06cb453df0a1bdb07d9f292b546307ba7bab60e1d91f5c32415",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W5A_Body_Needs_Lesson_Pack.zip": "318568f22869fcbbed0c0aa451b2494b8c545c6e7e7af1dec4ec14c43b34cc18",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Lesson_Pack.zip": "61fb1300c15bf6b4ebefd5d2c9a39d99831c89101790357174b01b7538f334ad",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W5_Teaching_Pack.zip": "1165457c99cdda053d39cb4d4d3efb728c826d09cd2357f8acfe8b33481b2d51",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W6A_Balanced_Plate_Lesson_Pack.zip": "f8ea6c9f6be32666c3a3f4027fbbf1b0782738b44d6d4a31b95ab49f161c376f",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Lesson_Pack.zip": "efa0d4ddcfef59785f08be4f196de970f05578b0c3313dc4a9eda8ac25c7ead6",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W6_Teaching_Pack.zip": "4a04b098cef12e0894fe46ffecc8b028e62b77f70d5f4f2981ace88121b50adb",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W7A_Food_Sources_Lesson_Pack.zip": "ab1aa6fc0212bb4d2f99a93c051352073fe800a6fe84762522099cd78888ac03",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Lesson_Pack.zip": "f47ea41f07b1e0fdfbeeb6bc71bcce7d10f62f17de1e0fa841d893e5649a2636",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W7_Teaching_Pack.zip": "d797b0cbca7a8db1815305869004a2b1348ad2e47aa8b59f81f7b8cb2d33c765",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones.pdf": "570c42fdaeef7d4c714e5b78bb49d970cfecee79414a1610b8d6db337d74d635",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones.pptx": "07e840c37da904610ea52fdd1ae0b6826aa0426d2778b82548fb4f006e63f320",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones_Pupil.docx": "58837cc18cfc2d44a1bc7b24be6fab2342d2dde54e6d6647ba082bcc553391da",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones_Pupil.pdf": "4324477322dd593ae260e14c8c3e355ac33a43d9b432aca25af5332f470430ef",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones_Teacher.docx": "a30fbee2586c2b803f07ecfdd7ffa5c2779ef519b0614951258bbee6605a6d15",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones_Teacher.pdf": "6852b465cc9e424cb792f108fa31ccba452f90a71f9252c7302be66247dcd059",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence.pdf": "8d6684d616b4dcdab42f08bd1935eb88f11572756368bf53a912f81b51d5c745",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence.pptx": "19d4cc8166e3a9d995d47dce93352a533e896183f3314a003047d2de8c3930c2",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Pupil.docx": "82f1d04cd6358fdc3f6840ba00cb339b59259b02bc2a4e42bb97410b9e1c0afa",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Pupil.pdf": "9a79a4609822378d5b2fcd4980172de3f24f485789e46dd5ec88efda31003508",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Teacher.docx": "7f849b0158faa1fe8bba0987354f487e6c78022df3e4bd1b5b1d4f1b61c051da",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Teacher.pdf": "8b7f52e865574def5fec30400ab20bb5a9fcb0caa9e9c69ed3df33d508905fc1",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs.pdf": "e33f83b4f6636b4cccbff17c5f05627cb15970fc4ded60269fde2414a86e8a7b",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs.pptx": "36e216298251f9764baa23bd8d894b37c2d415fe38eafdf17b33729cba7f07ab",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Pupil.docx": "0dee5d479908ccc14ac17afe664d8c430996d3ea5aa02ba63db5062285445255",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Pupil.pdf": "7f1c1f45d405743c4c5ab3b4ee1728a2d5e4bc49e0dbe80174ca92527d7713f7",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Teacher.docx": "417d3907c7395c5dd188a2001a0e7578212bb87fcf061490cb9bb2b78d41d681",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Teacher.pdf": "e834c2e011e8236339745cb4bee8499eb652b8f50b349db576f2026b182bb940",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model.pdf": "e905f9f66c1085e5f4dd1dca6a01a9cb12398f7cf58ae72c9f5c0680db86c4fd",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model.pptx": "835302e10c4c9d42b607f8004991e211b37969088a75a8321167686c580c2ea5",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model_Pupil.docx": "2386806265db047de86ee81877131e6eca2d49eb6896cf5e932d05d6fffcfdaa",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model_Pupil.pdf": "62241873d87742418b8e9889f3f21d510b8ca7eec8c066d9cd9a2ed48c61c31a",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model_Teacher.docx": "7929264661f58bd50b6b3d37445efee1aea81c2986f2757e958782febc6eac22",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model_Teacher.pdf": "b58f2f31273f4b5e0fffa7c42c31bb82e741b9a726bc415ec8deaaf353e95beb",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs.pdf": "fd6c8d2f57ebbf3ed3159dc6dce0a87badd45fff85aa9807872cccb0e48b214c",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs.pptx": "61aedc65b748140e93f0a8d33846f22417c9c8dd45f6d7f397c74d199bbb0018",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs_Pupil.docx": "bb1c470bcd7ce4b8d67a5c9b40c2927a6c5e4c45c3a1929f692411244055b835",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs_Pupil.pdf": "400c06df0345091f8106763ef3c87d6827c8c08460ed63e6c3cc6978196ce4e9",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs_Teacher.docx": "3aea73afd099d214959dabad16ccdc5c4fccf9852def555d90b93a4fcb6742e4",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs_Teacher.pdf": "59b102ac7c36b715834e1d4143f71ff19ddca35223370487cd99500ac4f2a23f",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission.pdf": "a44ec33f0c1bf6aa8169b18182a746623ec195d4eb73cd3381875173c7d9f5f6",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission.pptx": "97560a78fbc990ea1446a64a509f01b0a2de0541cc9d82cb56ee557d0b28b223",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Pupil.docx": "5470a602ef06198ac0936289a59633c6ccddd5f57a9e3f69a88467ecf499632a",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Pupil.pdf": "bdd15828211eda839093c742513381f6401c1137f9509755244b832f78d467f0",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Teacher.docx": "cc7f542d1ca6304b1b19d821ad981c4bfbb844da2aaee781d769b0d91d5394a1",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Teacher.pdf": "d101e634948e248cbb81c74d1554e9c525ed1c060672576ecb118839ac75c85a",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate.pdf": "a256991e850c6067ff8ef438d044acb16978bc2ec5eb22f0b4e75e427be145b1",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate.pptx": "f2e49ddde23ee01511021c0c531e67cac435334ac2387ee8cd964fa4f1c09352",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate_Pupil.docx": "5ddd738899464e13f47797484c7b67bb8d180f8dfa54190ce6a5ee6989c481a3",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate_Pupil.pdf": "2c0bd6f86ef08e5566c0d4b0dddb7eb317fd8231fb6d839a1c7ab0e247282811",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate_Teacher.docx": "dd41e08c1dacf4665b8d0738e0ebdd0afd9adcdc9014fc4007a81bcc774509fb",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate_Teacher.pdf": "e38a3490fe006d6b1f5ff54e4b93f02b33f58aa912822d5d31d6c3dfaf5389dc",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison.pdf": "78ba407d2c75bb56c39770ef002350a522868ab35dd49bb91047ea1728e4739a",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison.pptx": "c0c0424d3877f7aebb676b425044ac93880dabd761988368317580ca5adfcab6",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Pupil.docx": "5f6021b68a0d49d75caeee2d2d188913bdbff24bebb5c50e90e7479e0918111e",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Pupil.pdf": "5e35dac7e16dc7548d64aaf8af3b00ffe8e5e554bb8076d89ab47b57975429e9",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Teacher.docx": "32a3c2580e7cb8b6e2e4696419f191255e3e01090f49f7ef0cf066ebed149d70",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Teacher.pdf": "cc6e4a4a9d9510c84ea3dbe1a50c01e5f67721933dc543c14c3236f58f7b345b",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources.pdf": "e2e5d516894e369e93861d63df96a6fbd163b096583c7d26fc0d541f38ff2fba",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources.pptx": "e1b43759dab1b36e2e8da895ee8542713a9763e9f615f859f64b5e227ae11470",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources_Pupil.docx": "9685dc0158aa3b7db919980e4f9347805b494f74d0a3835327577962fabd279f",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources_Pupil.pdf": "c566123241ad7acd6e6a3753abfe459934d320065151ffe83a36d6058ccd0d57",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources_Teacher.docx": "382f902b5c4e99a7043645097e676ec37928f0ed1e1bd9598ec84f7107696ec5",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources_Teacher.pdf": "65c5f93f10a5bc68bb46e904a57cdc0eadf9bdb947c99181b04c31db41bb641c",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation.pdf": "6cb785fb6c253f362d4caf168f6e06bbd77fa33ea41edfc44c29757189c9bfeb",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation.pptx": "4c91daa2018cc0f0df7256ea1933622dfb7505d55ec38002a6b548f3355d0433",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Pupil.docx": "f10192242483ec30446302afa3ce6334f5c54c9782bac2f352e55ef48b9ae4e1",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Pupil.pdf": "bff6a31bba74a70e7875cf823cee12354abc0cf6c0e28672345e758f9f89896e",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Teacher.docx": "b9d84baca89f4f2498fa14e228d9a522b1ed4009c4bee4f90fcb213f1c992ccb",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Teacher.pdf": "3f2816a6722bfe7b18131206002491899b989a530d8509c59ff2b0871fdc7d61",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W3_Cards_and_Labels.docx": "1ecfd3c50271dd3895f9cbdeb5cc29fb92b08090ba040f3736b5936cab1767a4",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W3_Cards_and_Labels.pdf": "cc6c60baa5ba53dad174ec6749ca054c06ae12730b212b255a635acff35eec2e",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W4_Cards_and_Labels.docx": "c21fd7caf1ae81bd24e2d6d8de073d79361df2767ba204e38de3cb3680bb4aaa",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W4_Cards_and_Labels.pdf": "431654dc2a70d637463ac0c3c0627a33efbcd21ba9f55760da5c18151ffcfef9",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W5_Cards_and_Labels.docx": "ceeb395e64389eecf1af8b3e72e46a96f1102093ed95ae872ba8894d9aecbe21",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W5_Cards_and_Labels.pdf": "d198a60d9b24a3a4ab9e05d2cf7f6eff33e05bc411ba4ce32aab3f0410ad727d",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W6_Cards_and_Labels.docx": "be0cbc702aef03707812a2f84e3e02737bdc2299b3e7baecb1cc9cc98c5dc2b9",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W6_Cards_and_Labels.pdf": "da0bbeac4c479fc4f20173691e236a67e7c936856f6b460332847810c6b4fb60",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W7_Cards_and_Labels.docx": "9bfdec7cd96599afba6e9421ad9d80fc7df9e07be01d5334c5b8a61319919aee",
        "Science_Teesside/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W7_Cards_and_Labels.pdf": "68746df0bf740914b914ecf6d6c2a1b4b39252171e50621fa7a0c4aa4d1f141f",
        "Science_Teesside/Teaching_Packs/GROW/DOWNLOAD_INDEX.json": "a1c471c42eb7da80601dda11fcf6c9d191d6457edb69357d82c9de4eb2206b89",
        "Science_Teesside/Teaching_Packs/GROW/SOURCE_MANIFEST.json": "5dc12b000b3c3a9e9bb86b72c12b69023aed2ee9475eacccc55997da55c082eb",
        "Science_Teesside/Teaching_Packs/GROW/START_HERE.pdf": "93a7e61be570fa6934e93973b1a4f4eb200df3da24f83b8ba45ec64ccbf80375",
        "Science_Teesside/Teaching_Packs/GROW/START_HERE.txt": "856bddba97acc3d6389f09d99d3b0dc6224a4948b2be46c885bbaab7d9485c93",
        "Science_Teesside/Teaching_Packs/GROW/assets/made-by-matt-approved.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3A.zip": "d228f95748f2f4d63b6df0bd8d54394baf71640044e33747f8784d776d8ca15d",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3B.zip": "00bcf8f9d32da1e02940ee8f21e3193977ff1bebdc028f94bca0400282576f57",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W4A.zip": "789bc7f2048bba2eeed5dce137c93b1d03cb15841e88b7d7caff3202fb920aa5",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W4B.zip": "ae960df6ee5618ed8583c96399360734365285461cce3268cab20601ecf24750",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W5A.zip": "a45c2101629bee39c6637e7ea571be93e2947d0faad017f6a1878bf4cd19e3c7",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W5B.zip": "29d0aa2492db9d2dc9cfec2d73c1cb6fd8b00658202385f696c0703dc8d9fb03",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W6A.zip": "662b93aaafc83b0fc7766e620f934aaa01ad4f7bb9e7d9500264581e316dc588",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W6B.zip": "f394bfa9bd59fb66abf085b366bda1ba974835f74704aeba7db70cf249e20160",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W7A.zip": "d65c89a82992eec3bec05f855f29688f5d97258884b5affba043e1fb105c580a",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W7B.zip": "fa2e93d7e8832e5741390701bda0b9693a9868f68e3f442db15f8cc4c362691d",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week3.zip": "257d38ffe995004ad0380e2b58ff3b5a1a352c86c673d4e66d4a4599a9c637ef",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week4.zip": "df33780c2dea97c485158d026f8694051244d866663dde06ab8ac2ac14cd84e4",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week5.zip": "fa2c5bd9f4f509b52d1d2510afc8ae25e3f9bbce55fc3fe9eda438882f3663a9",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week6.zip": "6c0c4b0c76e3bf15c104748649c8d501e4ee3f669cf55fa280e3b73768aa6730",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week7.zip": "3fd530bcedb10162514f9d37b785f447c24e8a0ba8c82b4ea94a578b54e33784",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Weeks3-7_Teaching_Pack.zip": "3dbe9ce0d6235f1939ced991ebe33e0548c1160b5fd1aea1280d3ed55a377b47",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_Science_Autumn1_W3A_Friction.pdf": "327a9a2697be3514616c6e6dbdd234f2417bb455c9ae030db1691ad2402853c3",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_Science_Autumn1_W3A_Friction.pptx": "3367b26c579d6e9cfb9601c004aa471f523ea1278ed072eef45cd55201d6d661",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Pupil.docx": "db73d9da72dc284f02a37134ff9d05fb19998cd9c0f5cbc598b1f92b0e14cb57",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Pupil.pdf": "f6fdfc81b303f8d855b0d7d45b2e86ef2993d3590b58eed366ed97891e742d02",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Teacher.docx": "4982121dc03938db039d652b99babddbdf4da1a1052cdd338912068f643af97c",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Teacher.pdf": "02f22fc10c4f5a659dd4ff246ccde6ce867459a79a2635713d4227614b7b8373",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/START_HERE.txt": "aecefd50143d87b71dd8733335ff7703a4c9552df45101f917bb2cb82d807685",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test.pdf": "b7032f8a9934f722ca5f0e8e612746a57b3b7ed1a2e4bc302e5819b43c1dd237",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test.pptx": "a8ca23e3534ae8d8391562563ce5346ea5db48ade65be5b3d5a276072fe104ea",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Pupil.docx": "621a0345bef39ae6f02332a1993a1cc2612d7d8da691b0d51030476fcbae57d6",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Pupil.pdf": "8c994ae90730485680ed9391a5ecedd20989f8cc8ac93075586d6e96eb01fbbd",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Teacher.docx": "7c11362dbe8f30e1f111031282ec8ffdc803fffebbaebc2fe7e7d449555813f8",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Teacher.pdf": "bcb3b02ba71f6b6debd40941e8055a0ca1fc3f91417428d9cce2a11554af49a1",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_W3B_Friction_Measurements.xlsx": "7ab6650a16051e655dde2f48928810cb2a825e07d4d0a028fea7cc25ee64b1d5",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/START_HERE.txt": "a14214b3e256d5e99396d03292b4b1281b56b56c5a8725386c09d11c275c45f4",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms.pdf": "4af5fdcdc9e4d5c651545fbbde812762f924249d42a103d3e41ddfe49c120051",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms.pptx": "394e9a36b4e15708e43346e328c82f89ab3323d4de1df0cb0e2d9743a22d1044",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms_Pupil.docx": "4621245842054aa069124ff174f09c0eff8f8c56769d37c1acea9afe75f3045c",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms_Pupil.pdf": "1b2156236206deff8ec4f909faad3fd552c4caaa0a67cdc703cb900c6eedae08",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms_Teacher.docx": "d6324f71091db4971ca431f635995a5237638871b7a3a4a3455b75a9946425aa",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms_Teacher.pdf": "e7cfbdfcd17ce2734650cd91a04768a3da95156d6acd92bf6956040961d53366",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4A/START_HERE.txt": "eb41429cf022ed25c1dfc3cf05d21787608cddc59982cc9d5aa2357135fc842a",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test.pdf": "a7ce2404efddea8e8e4adef88e7e5a54659cebcafc42805dc299370a06569e6c",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test.pptx": "435e8601d04da39509358516118a7240f1060425c0f4ed78a166566110ac9b35",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test_Pupil.docx": "11f958262f40611264f00fa24bbff2292cd214ed84b03204b398bd017a7802e8",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test_Pupil.pdf": "317ae814fd7d1968d2c23a865df8457e2e00838b68bbf32972de1f59ea650c71",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test_Teacher.docx": "ed27ebae53477ad516ec1580b8b0a67e6c81c2eed031ad5094a291b7a24c5835",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test_Teacher.pdf": "21bbcae5a4fb0667afcb6069ac59ed7c80e12ce15b174aa4de67000a8a8080fa",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W4B/START_HERE.txt": "ec3da721d7bce358ce3458b77bbc5bc0c8ab01a305486e2c711d7919cb5daaa7",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test.pdf": "5057527cb48084fadd02863d9cab017e71818955efe11da514300c5d86743123",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test.pptx": "b9a829b1e5cd38fb891f687b2521de4da4e5e10d433610f614720b21ce14098e",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test_Pupil.docx": "b3a5a3a18ffeb6c72a53b1f23379efa730f8981795509239d072408fa44c99e1",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test_Pupil.pdf": "1e6e19a583143063af3d001a7039c89feaf8aa0bcd9553f8b0dd9e58218aa5e8",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test_Teacher.docx": "5ec3f179b213cba5730070d69c5a46b3d7a20c7bbe665c3049d1f3012e5fc1ec",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test_Teacher.pdf": "adbf06615291d03f65665098eb1aa6a21d7aef15a32dbd2742bd41640d6c3608",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5A/START_HERE.txt": "a290efa290a30a831a30ef59dd7fd7826ff7d8906de67c3698caf19619681ccf",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical.pdf": "3782fa567cc5c389de3801cc57a6c46a425e158fed71cb554507537229b833cd",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical.pptx": "946c83f16a9f5357f5d13241039c48a0869c1406a198daac348f8a1e07392ed9",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical_Pupil.docx": "6569a9920bd4597d4fc41fe10709451062fca39f5419c0eb030ebd0be5d85b00",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical_Pupil.pdf": "06d2ba4a1bd1a1ee3175877c9fdb108f3b60d510fa3c843444f61b7bec591fc6",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical_Teacher.docx": "88bdee24e177ae31505cbfe467083f11dc114c0e3b55c3b200a26fe944839e00",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical_Teacher.pdf": "891c8c64d24767bf85c66c956d9bb85842688424c3ea71eb967e1e6e3207afe2",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/GROW_W5B_Fair_Test_Measurements.xlsx": "746d64a30be2304c439fb5af7ef79b25dbe8f69d51c8de3c12cd22b8f2ac2104",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W5B/START_HERE.txt": "d667aaa4d4c65214655f7f9744b7b8b240d5a5d39539300c35aa5f4abcf65ed1",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets.pdf": "31be861dc9629f03f58665c7e2455c4bb3e1bcf4c0eb954dced62cd6d89608ed",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets.pptx": "1fabda3827fa43febb7fc3836619f5dbb7847deee60736c0c72dbc9047d30982",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets_Pupil.docx": "91bcbcbfbfdfa3039f205b9c08f7583fb126c5bd0953a5968921e1ed5eec681a",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets_Pupil.pdf": "08f14322ca35b6da824b798ef777f1e82a17b8c44ab032ce6da19c87fb12a60b",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets_Teacher.docx": "8568d4650f1adeeb8524c86799e49e2172e39dc282f80304471ba81a2f731c05",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets_Teacher.pdf": "1e1a3882a6716e9933f81a5ec94dea92fe8e0f06384080b3c8fe324287cba086",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6A/START_HERE.txt": "922b972648e167684acd8d528e0842294ef89a61478b74b65d74ce22c25e15bd",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets.pdf": "82649adfce0d1fbf07b3d5ab00719ae0936812fc8b485e66ea58ff47108c46f9",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets.pptx": "90435b48ab9baa82bd2a3b266e963c2710bedfe79f88671deb2989a859be6602",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets_Pupil.docx": "35785f5169326bc4115abea9934d254ff990e7ccaf3b104bb2469bcf8945a16e",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets_Pupil.pdf": "a2bad2d15b930cce103dc59e5e65b15f63b34afecf3c8d54a8358c28126c6940",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets_Teacher.docx": "d29f02f60a8ac61014113416c8c1042520f3b1a6815476f12b830bb72eff6f56",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets_Teacher.pdf": "318cf84513b3ef6daa97918782dc2ec845cc0f4a5905c315e65a4a92bf9eaf08",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W6B/START_HERE.txt": "488a26039677af53ef3d8435dd412e98406a807d10534a7725d2261d06869d23",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon.pdf": "c7cbef511bb242f2155b64c64ed8557724d128a469b21671bcdf2b2ca014a176",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon.pptx": "430e539a95c7c53ee57159ef43f3fd3c88fa175ebd58a5a7b32693314ee5c2a0",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon_Pupil.docx": "d4565fa4adf2bd77cc2288652e0d43e15c066a3501bc7a454edd02eafbe137b2",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon_Pupil.pdf": "bff2ab37b1c04a2afdb9d86f5a17822d3fa63727e76aa3d563e77d2bdcd8ebad",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon_Teacher.docx": "bc036875e5bd9e9ecb6e2f1f52d9dc0adc42f486d6bf04d246d02aa78dfbd763",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon_Teacher.pdf": "64f052a34a5849381178f8a22dce9d865afb2b2602a0f805004e75149b450cc5",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7A/START_HERE.txt": "447de6ad4347b097a16c09d40df429a4908e381b6ed9c36084c2e1cbdf6916a6",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon.pdf": "8a8946342e27252e71994094866df85a98eb52b18c2cc315c48737f7b0c6844f",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon.pptx": "cda721e5dd3c1799c89b8e00b79fe548759b144998b8f9ad2a8c244956ff0acf",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon_Pupil.docx": "8920525bc2020b7a8d6a2e3f935eb77415f8903f55f1a2f7636c49bd8fead9ee",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon_Pupil.pdf": "f11ce921052aa19e98af6741988dae84482cb5cc87caa15cb6d06740db7ba6a4",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon_Teacher.docx": "1d026a3de59ada343c814e3ed895368d5aa9292244ca569a66ba7a53f3cf126c",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon_Teacher.pdf": "ff0c970316fa22f34c67fe22f8b0365b3bba423fef0aefb0e63cbc5a01070f19",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W7B/START_HERE.txt": "10d6ba34be76c3a7d82a346e83a65c86612ecd95505e63fc797a091bed945ee6",
        "Science_Teesside/Teaching_Packs/index.html": "f2d8aa5c6ec5e9a069c1b1e6a12829a76bd68e20b603026b1c7dac027e4f9617",
        "Science_Teesside/Teaching_Packs/packs.css": "70ca73b323e5cabf05b1f5f9f8107694cfcecf4ddf8043f342049ee4c797ce59",
        "tools/science_teaching_packs/BUILD_QA.json": "d5ee55a25c15ca86dbd6324b417c70d672e1d0c19a1fa6462f35cc620927a2ff",
        "tools/science_teaching_packs/BUILD_SOURCE_PROVENANCE.json": "bd3093b818cd94ab74260f28f2c8ae08e77fbac307e8dcd0cf2a77540e299197",
        "tools/science_teaching_packs/GROW_QA.json": "a8cdaa361414a3700c463ea40e0a159029db3fb803024e50b0eb39d082c6f364",
        "tools/science_teaching_packs/build_hub.py": "db1a706f68c8b33cdbcfc4c6f197781fb5cde2f3fe53dc979eea5c5b592ade10",
        "tools/science_teaching_packs/check_packs.py": "8895154bc87c7238f2e6d4a65991f5958cdbd29a27b58fdafb551e07f7a769c1",
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
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/LH_W7.html": "33ac63f9fbcf9c36d67658e87614f6e1e904de45aa3dc5128ab7fed94579f803",
        "Science_Teesside/Teaching_Packs/BUILD/SOURCE_MAPPING.json": "ff5ed25d7ed3bf20879dd2a63c1a8a68024c910556bedf764eb83be61d4ec8f1",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3-W7_DOCX_Collection.zip": "e0221279cd94ce002da21846a57e59cf000fb321dca3b16d45634124e71cdb2f",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3-W7_PDF_Collection.zip": "7455b42c68132edb14fcc021177d8b6f242eaaf54001ddf7f7e2488b76ae462f",
        "Science_Teesside/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3-W7_PPTX_Collection.zip": "315601d9afb5a05a21e82b7993b0973268f71637137d6578a7deadc5fd034fbc",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3-W7_DOCX_Collection.zip": "ec96c9fecd9f6252955a8c49ec1f446d7144602a36d55af80ef943b99b0b935a",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3-W7_PDF_Collection.zip": "ddcc8f97bb97f5fcf9c60f718618f06d62b25c32b4bde2d652c3d9fbdc78c050",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3-W7_PPTX_Collection.zip": "ccaeb527ab31c9193fdad87bf27f003336c800f549771c795b89608d9d51cec5",
        "Science_Teesside/Teaching_Packs/LAUNCH/DOWNLOAD_INDEX.json": "cb926c0aece9885dcb5c6c67221b7c7bfd5024bd714244242709a4ae9a3444b6",
        "Science_Teesside/Teaching_Packs/LAUNCH/Pupil_Worksheets.pdf": "e5f16f3cc9a3031a353d1899f7c02b980b291d46607e871976f7813db76f362c",
        "Science_Teesside/Teaching_Packs/LAUNCH/SOURCE_MANIFEST.json": "ba94dcfaa0bcfd72d895aefd0649e70faa13ec4d192a367f6ff32582efb0cadf",
        "Science_Teesside/Teaching_Packs/LAUNCH/START_HERE.txt": "2b7b55ab005abea12229d54ef4f8f5389cd6c0714078284537844e62b69ac3e0",
        "Science_Teesside/Teaching_Packs/LAUNCH/Teacher_Guide_And_Answers.docx": "cd428e8265728edbbe4c47ba7a2e4ceaa9351fe5221b28b1e9397b67b10e2d62",
        "Science_Teesside/Teaching_Packs/LAUNCH/Teacher_Guide_And_Answers.pdf": "393bdd8f2b5e620a9cc4926fd0a31ae09e989d844841841d0daf3e9140d5408a",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L1_Microscopy.pdf": "411edd8b048c842593c1121f8bc834e5317d37a7a14e63750eba2b9b37429f88",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L1_Microscopy.pptx": "a68b061201d1fe625fdc94bfee4fa2fdd0cc223557c24a959999cac21c195d50",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L1_Worksheet.docx": "578c8ea466beaef599c1d7f903a47356548b775352993f87ac73d714a97d8b86",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L1_Worksheet.pdf": "5a19b3f2ca31014d262fed5fa07132b1fb13b28faa10c64b896eaee3f12a6450",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L1_depth.pdf": "005e8b95cb519d392b039cfd83aad453f4658b6e8e8aa64033a8b3bf8d92f301",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L1_standard.pdf": "82063ab1b999b329d78a05d9cb26080946bbe2a7dcdb8e5173e6ccc79a9f8496",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L1_supported.pdf": "cc8711966739a08fcffd0a83101a6447b3df3b0f467e97a758716ea20c82b2c1",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L2_Magnification.pdf": "26f6f2663f3a38537d233a9c94861408c0a23ab01770ec64be8cb0c0b8c811ff",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L2_Magnification.pptx": "1fb4bd94df2a29ab0af72db475b8929bdb22aaa9cce4ee4a5bba89175f897286",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L2_Worksheet.docx": "910725485910dc58e2b030f28b0610e31a7c4b2891422ae67816799ca544e710",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L2_Worksheet.pdf": "1f619b4d341c9a2a339fbace64d0ff0ad7511bc3fd29ef07efc9f56f58eb6b3e",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L2_depth.pdf": "cb100881ed59102fccd6ffefb85fbfbb984d20658249cffde5f3f0ad1bb832aa",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L2_standard.pdf": "9ce05f7ee4e095294ea461fdd5f838ef4ef9f0783842898d36468e2f7aada8ac",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L2_supported.pdf": "7b56ab3c793ac029fd751fd279e542e74fa42f9a01bf99fac3708177b38559ed",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L3_Scale_Bars.pdf": "9acb60d205a4e7a4c83a146b7c2a4547d540e9eb5dc6cbccca7e70e0e55f830a",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L3_Scale_Bars.pptx": "ebf8d69debb79a17020e22a0b234ad5300319bd9d149e64f2996526db507a441",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L3_Worksheet.docx": "77497a489ddc7c0ff48ac4a208832e28b6022f20de6e1ae225d59b27c6d78d92",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L3_Worksheet.pdf": "ffec01cd95a2ef8d9e1aa87d8b5e07f99d938b5bc7a6858c357388374f3bac8e",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L3_depth.pdf": "53184ecb48997a1e102ad0903760a103522c6adaeb52b1c112759b9c2209e435",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L3_standard.pdf": "ac051b2f92d89fdf77253f8edf3c4429fa89d398d40d0ee2606cf0f02d22b260",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3L3_supported.pdf": "e0e52afc7e76fabaf33ef82f3704f1d0eec08bd0fb4097c72bce38468f4aaed0",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3_Weekly_Plan.docx": "0ff2731c3812884f5662f488a0eedd24f4e9689a9a58800125416d0666c66ecb",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_3/W3_Weekly_Plan.pdf": "b2827f23371b7874d89245a7dd75e410cb7e9f45beb43ee564988a7d9a000de5",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L1_Diffusion.pdf": "ee6a555d71f9088a24f2eb409483c5798359f93612b3107f9750d9547fb9f827",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L1_Diffusion.pptx": "80b965d1bf780a7eeecce82a92c91e90485d149cde5b85105fa6aa7380adefb7",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L1_Worksheet.docx": "414490320b228f4259874aeeb726813c8578ed535b25ebf8be2186400d4c06d3",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L1_Worksheet.pdf": "2bc670392d9a4c01ca91b0c18740652fa6a128034a7d02532c61f1b2425b1c80",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L1_depth.pdf": "e4414be692a08830b502d4565df44f3e92a3f01f0acfa014eb04d4da3638b7d7",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L1_standard.pdf": "1559958acc64bc63d89be2aad107ecbfcd9790ac2197999e8f7afa841ca18938",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L1_supported.pdf": "24b69c4457b50caa801d8f4ab70a2a7ab09a94e6332d9f933fb26b9a0b39452d",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L2_Gas_Exchange.pdf": "b3652f52606f1fc860735976363e37b5224327692d32a600e7acdc56ab62359a",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L2_Gas_Exchange.pptx": "6cb8a1c32ebbe00111b4ba7187f992a89d367864d5f80bd518525016056cb66a",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L2_Worksheet.docx": "ce22594dac00e13df8b079f3c16f0abfe44f2c821d85162206eddcb454291082",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L2_Worksheet.pdf": "52574a3978cdc979e213f4f6f895fe8b375514b306de19844486297190b972cd",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L2_depth.pdf": "e47ff950834a3e008590d3e3aacd023035099c9a690478937ee898f27230ceed",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L2_standard.pdf": "00a824d2d52417a7fc1add1376937a9a55a6cae32c160f00491997044e41649c",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L2_supported.pdf": "bb56237271dcaf6c0ea670f2f1d35b31299d4b07afbd02b18e21b2e3dc4513e7",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L3_Diffusion_Evidence.pdf": "61ae806cd59bfd578a9a231bf59bb85082718dc8b509b0e55eecc95a5679478c",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L3_Diffusion_Evidence.pptx": "4eee78c7dc875371151c4a2309b1539c894a04e63d8b635676c825ca401f8834",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L3_Worksheet.docx": "f98364c37342b2c7e1d8852b3e9480c56608087c553509d190c246264e3bd55c",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L3_Worksheet.pdf": "7c788728303715a6d3801eea275715dc127bbbda1060fdb5a3059ec0fa3f6ef1",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L3_depth.pdf": "8110273a50fa1e3ee30af9634015dd60910d01c274f2747dad22de7e1c43571f",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L3_standard.pdf": "1bbcbea02fd6a38295d7cbeb4e750cf90794a1376ef38a0d8f46e64419f7facd",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L3_supported.pdf": "a1eb3480ff04ec86f2e2bba418f200fd29c831f419efb28ce8caa1fa0e39b8ca",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4_Weekly_Plan.docx": "8908c707b8a70a5ec32231750fd2997c72803de0be7c140266753597cce870ee",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4_Weekly_Plan.pdf": "b51e3e4d7842e2eb79d1d68746bdae2815890a729c2392f746425eb7fbc8d4a1",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L1_Osmosis.pdf": "c480c3dded76690daf3a246be25c46638de5591b2c376e42fb19d9f4c7016558",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L1_Osmosis.pptx": "710ae7a5ab374e599d710279e21984619f6f2acd958ff06c4365080fa8467f32",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L1_Worksheet.docx": "9a46502209db857d1ef7cb407c65e5cb0fde6877ce225f55bb88b3dbe4bdb81b",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L1_Worksheet.pdf": "533ffbba83bc6a18cb44a9af3723e727af41c73b0dc7becfd8a4684ecec2f769",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L1_depth.pdf": "153c07f6d4174b9ced5537a34cc39e0129dc9fca4ce86f30710d5fe0e61abebc",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L1_standard.pdf": "c450cb8ca0c00a54c088790805d1629f6225fafa7f20f2ed85e231980e12b23a",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L1_supported.pdf": "ddbdaab0499efb7e0407d7085c8768c032d130b0e0945efc28f423113f955773",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L2_Osmosis_Investigation.pdf": "45f9117690a893731d768d95778a635d7c6b6d324b803c383e4020dcf14f879a",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L2_Osmosis_Investigation.pptx": "dfb1a60077b8bc34cc5737c1f4551a18f20b65d3b42acd3161abdac911dc4735",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L2_Worksheet.docx": "78f94b01728e94f2edc93bf884018c84a411e71f9db8b7035d02159287895a2e",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L2_Worksheet.pdf": "e96884229cdc695046cb0fe6960404e4407da72d0d489cd3fe43e3613e59af53",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L2_depth.pdf": "a9127c50279abc4874aefdbd6e78d02da91aa0faf5d861820173558a263505f9",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L2_standard.pdf": "6c80296e85da6fe98231d1ed4cdaa56191c6ec1962ccf247badc85186591df01",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L2_supported.pdf": "bd98b8c86d0dbd4bf75e2c19c20413250bbac9f976bdaa42698b69cab230134a",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L3_Osmosis_Data.pdf": "5ff00817f0e9629d974c4a260116044f986978960a46554bb6d32f3798dfd980",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L3_Osmosis_Data.pptx": "59bfe0fa66da6413fad107598fd5eab556324da67068d343d7024ed9fd96c4d6",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L3_Worksheet.docx": "a88ec8ac1d32332cca655187aa319c387a384da783f4f8a5328775bad6ab1b48",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L3_Worksheet.pdf": "2f45e3db7c25cb4be482c47a3ea674baab297ab8fac06530152dc710050eb6a8",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L3_depth.pdf": "11d54d8a1c7b08056ee672e0c393b4c423d9e487cc473ef5b83888fe54a0e1b7",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L3_standard.pdf": "29abc6f371bb8ea82846b3a8a8e8eb3f5b4d2cd641eacf4c91c3cfc298486857",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5L3_supported.pdf": "984c6ecf259beafe41c77e60af240495f6f32715dd1c2c7ece6121888bfa0e10",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5_Weekly_Plan.docx": "dc6175157f80ed060f6dc829204758b6ca079fc3a7d0156648a495a31bf77a11",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_5/W5_Weekly_Plan.pdf": "9d9f05619d7368418e717af6dda8158786f025fa217639090886a2f0ced4126b",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L1_Active_Transport.pdf": "a877671f4bce8b6ec20dbdffc31005d7a8913420a21e4a50521bf46095c56ab0",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L1_Active_Transport.pptx": "6fc2f87c44239ffb9b6e84a692c27f463bee58ef6e88eba54dfd19009b6646f3",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L1_Worksheet.docx": "a0db709628b013be34cb431640a4d6353c08899275e69c7048ee9eb5906556e1",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L1_Worksheet.pdf": "dbb36ee694301b2454c5d25784899e39f4c8645bb24a4323611c118da2ff3091",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L1_depth.pdf": "0d645d463c3440e8f162066073976948d17113c3c04b9a1389cc9936e352e434",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L1_standard.pdf": "3cec9853fcbe51f60e2fc49d51ef01196b9dbc7255813485666bedd8c64b3730",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L1_supported.pdf": "e31ae68717e48acb5d1a49c466a319aa4c4d9e896ea2ada6072f94123d68ba19",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L2_Root_Hairs_And_Gut.pdf": "8e48afe3ccca498f510b45c3a0cbecb63c4ba943a425294a00610b8f0bc82a49",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L2_Root_Hairs_And_Gut.pptx": "7127955eb2c1e2f38541286be5d238ad9c26ba8c35dbd1cc3c3ee27aecc71592",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L2_Worksheet.docx": "ca371afe8188dea2a79b4f8d01dc6d443382395bb0f753bc52ea0f34753a4f85",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L2_Worksheet.pdf": "e2ae0ea71b98613bfa02e4ebb00931c3cf00ebd0ab1533e9dd9c0be49a254a4a",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L2_depth.pdf": "46dc11aeeed02b38f81b2deee28c89adf809c261a0828d65d0772ff80f3ec0d9",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L2_standard.pdf": "4b18f94880cd466e663925c6b601697d3d47c68f63b21aeb98efe5581a9c822d",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L2_supported.pdf": "2e454bb29b5debe12fa5dfc89951bf473822ae664cf1f96e1f7706e78832fde6",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L3_Compare_Transport.pdf": "7ab6dcc9e5b8b8174eb9c9fc48a384e1d6d518b81562f0fde795976b998b02eb",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L3_Compare_Transport.pptx": "5c36b70c325b6102025f253d2664d1589ce5820758006dbb50e634bd8a1bcdae",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L3_Worksheet.docx": "ada63ec53ae3feada8f75a624f3a1e4c7b20dc22d02866c53fedaa6033cedbf1",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L3_Worksheet.pdf": "67908331e90ad45815a5dfab1391fd1f58e1b21636bf9ee50c85a4571b0f20d4",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L3_depth.pdf": "dea895c6bad53c4060b1bc15184a21631285451d8a820a0a7ee4903a13b386a3",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L3_standard.pdf": "28b4f3cab0a6dbfce5d2e72c7e63be6c983a4a65ec5b8b4b8e93221174e2ff57",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6L3_supported.pdf": "71e97b4a48ae5192af0075a4b0be4fad52d31f1432e78a5c559527179be25b29",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6_Weekly_Plan.docx": "b6b26aafedca7a02a28881ab8c00e9a07a333e5cec4c7aa21a648ab6545e098a",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_6/W6_Weekly_Plan.pdf": "0d00dc615fd0dd0de39caaf8b3075a720662d2ea565850fef0ad56fa2ae6f707",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/LAUNCH_Science_Assessment.docx": "504dbb695495660c2141b79f01e7cc71457a9d4659595ff55c8b610cbc7c110e",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/LAUNCH_Science_Assessment.pdf": "eea71d1a3b9a105542fa566a1c39adb0cdba3fd138d84b64ff25985275838af9",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L1_Review.pdf": "e2899621b752d69f1cf73da996cf698e7875b041da0bc1663686740578c0ba1c",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L1_Review.pptx": "a820db909139c864f44133b2f461acc0fc49b3f3eb77f3c59b5c3f579e73dcb8",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L1_Worksheet.docx": "25d14dff4c4f6e4ab56609b9af1e67597270a970e85151db273ffe98f2631aea",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L1_Worksheet.pdf": "7b307bef4e082bfdf7225530b121095810480ce52761068a21843cc7c412c096",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L1_depth.pdf": "7427ebdc876c5bf9ba137ee6b2b30f44c6e3cb791e9c70900bae83ceb980c0c1",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L1_standard.pdf": "f6cbc794175f8c62cfa3098b1afa6374fde6d94997dbc416df5a4dd5dceb7008",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L1_supported.pdf": "633dbf208b8c32c18e5985bd5e09c8e29234ce1533c584fe0a0b073d8fa7513c",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L2_Command_Words.pdf": "61617770ba69ea6d85fe37533191878c61d54aeb526f8e9053daebac0c415531",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L2_Command_Words.pptx": "305f7a0940b08a66a5963acc5efb07827c256552bdaa6158f0c0ce966b88e250",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L2_Worksheet.docx": "7c25d67a7c637c567f447aa655fd272ff6f1efe7dcdcd54c7dc40c77e1e1f887",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L2_Worksheet.pdf": "2742657e67b01f9fda32b27ff1704239f0e45fc5f4d445561dca3f041d37d2b0",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L2_depth.pdf": "59eca019f32fd0dc59f1cd9b153a4a4d337d419bf970194217edb58bd5ad754f",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L2_standard.pdf": "895a72d288f1041ea15c9ee7d91713cae7aa8dcdb7362c4ef6f7467964afccc7",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L2_supported.pdf": "be095c3778f0bde0f3f36a41cef54cdd7b3a720c44ba1eca17ace9007c297723",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L3_Assessment_And_Response.pdf": "d01342b1d3f5a7950c5459591199fce745083f4cdaf99e4f292379e9a1cf03b9",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L3_Assessment_And_Response.pptx": "6097b44ad6a0321335fac1bb72c3de07f0ada203431c36cf40156097fd7297cb",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L3_Worksheet.docx": "9d7b617f9ab63a6f7dbdf05ae27e7f089a907f88d41889fcf441140af86fb101",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L3_Worksheet.pdf": "0343a92d5d13872a021e14e334086f513e9f645ca14a9059e381d13e50b92acc",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L3_depth.pdf": "177602c03c56f61bbd03cd4b537d21c4c22dce607e85c322954b675490195c42",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L3_standard.pdf": "1499987c069be0d685c72ddfe9e3b5e021df258002a52244a470e4c3e7dc7dd9",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7L3_supported.pdf": "c5ee897b1129bb86eb0813c08af7df11bf4f42e4b70f5b79c7ccc1402ee0f770",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7_Weekly_Plan.docx": "499928095b9cd9aaba5f0b09a40d101ea40f98d41b574ca0f1fc410a50688605",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_7/W7_Weekly_Plan.pdf": "4ec297f090a8d5983b03a7ca23b866ef0e166c0f603f0963fa7c7dab075dbc35",
        "Science_Teesside/Teaching_Packs/LAUNCH/Weekly_Plans.pdf": "5bfbdf746dd1b83c93ca12c9c5f10f5f8051be30ed4efc1344caa49cac578dc9",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3-W7_Complete_Pack.zip": "2e5e209f9e1c367b51a94ac499a723ecad28cce29848876992c47fcf2fa5feeb",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3-W7_DOCX_Collection.zip": "df25831ba257f5dd177a25ec84c8ace3b47d356e146915c6ea2eab49bfb7e978",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3-W7_PDF_Collection.zip": "8abedd028ad762655f261e35b9221159574caaf0818730fb369baae88df1b6ac",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3-W7_PPTX_Collection.zip": "514f3ee23d1d37aa3840d7fd94df6b44230a3ec0634e0bb4f93023a8d83e7b5c",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3L1_Lesson_Pack.zip": "060327f6300211acb59eb660124649f7ea75ef0a77587d4a19ec5d3bbe0731b7",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3L2_Lesson_Pack.zip": "cafe99ba04eaf46c966ca20a06df81582c6a548b025c90085c4220e0d7f4c3cc",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3L3_Lesson_Pack.zip": "0d4a0a73e9b4c28da739f932e98597fa8ec72c5c446dd8d194cfc8184f2d5e8b",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3_Teaching_Pack.zip": "1cfe3bd4aa65ce320b4d1c7903093fc63b993961c0aec3206296166afea3d6ad",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W4L1_Lesson_Pack.zip": "9846dfc74adf1cda144ade7ec7c88b1b78228fdfd383a13eb380adf15b46c645",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W4L2_Lesson_Pack.zip": "b8cdd8fcccb792bf439bd411a271b0d40869ffcde9d20240c15b325f15916ff9",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W4L3_Lesson_Pack.zip": "3d1c3f04228fd15c43a46eea6384c8c2aa371781d21042b41df92eae22340c42",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W4_Teaching_Pack.zip": "42e4e6c30a17faa38bf7e94617403d27fc0916f969753cdd08db6cde73693d00",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W5L1_Lesson_Pack.zip": "49f1ce68e3ee5ee9f6bea7c2d2d0dd8aca43171f2de1b2cebab167f7ca290afd",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W5L2_Lesson_Pack.zip": "61e35a16b68ef299dd091d7c7652c513f3dbc42b792f424e18db2ac23d9bee55",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W5L3_Lesson_Pack.zip": "26ba452aed8ef680f390f073db2cb342bc07e89da4e88da205a18a218adf53a2",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W5_Teaching_Pack.zip": "83c8ee82197d2e857b893f53a64d180ea89e61d7a78fb1d4579c22d5224eafb6",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W6L1_Lesson_Pack.zip": "96de676da4d305e1d669640caac92cbc2ff2797441deb2a86794bbf9ae50bc1e",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W6L2_Lesson_Pack.zip": "8d83f3370645b56bdbf19c2d9ae4e852ea91d8edcca7a8d452e22867f6542d89",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W6L3_Lesson_Pack.zip": "bc7e35933bee81f4f98a4fff44bd82060726da08accf16621f3fa6262969bec1",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W6_Teaching_Pack.zip": "f9c2ec89883a42b3ac4b20a8af04f338f0062ffe937d7361776b4223ced3a1c2",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W7L1_Lesson_Pack.zip": "b2a2810152d8b849b7b4c114c4777660333969b79630adabd66b3aa5382a11a7",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W7L2_Lesson_Pack.zip": "8bbfe0aa46cc2c23643a94839f62294528bff209b39f055572057537fb1063af",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W7L3_Lesson_Pack.zip": "fb3c5db69672fc921fe1a81c01503a2a9e8419297625fef8e8fea98a3195d112",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W7_Teaching_Pack.zip": "8ac9185636f8e4c068e8df19cf0900392485df928296a1726e1809a9c130e3ab",
        "tools/science_teaching_packs/refresh_packs.py": "ce14bfa3c503bde2a5e0a8a07effbfe52d6c7262894cf062dcad358c473e7d47",
        "Science_Teesside/Teaching_Packs/GROW/Image_Credits.docx": "b7fe4b107695458bd8138170b0c98d14adddfe156871bd228db798790dbf3786",
        "Science_Teesside/Teaching_Packs/GROW/Image_Credits.pdf": "651dcd9f749c6cfb5ffccd73eb9ffb14a57f8ff8a8860f348969b34114396f86",
        "tools/science_teaching_packs/check_hub_browser.cjs": "27756f9dfc18bae97722b2f4514cb1bf3606a416c698fcd309a62437a6ff91ae",
        "tools/science_teaching_packs/VISUAL_REFRESH_QA.json": "3ce5b90abaf89fc5a2a4085791bb16e09667545cf489a985c1c525bd7698fc80",
        ".github/workflows/science-teaching-packs.yml": "bc177669ef54ecaf7f21247ecca0aa75993476679eab978e716c76385960e9ce"
    }
}
# END REVIEWED CATALOGUE PINS

# These semantic pins are deliberately outside the movable file/manifest block.
# Neither the catalogue pin tool nor the generic manifest pin tool can bless
# an edited, deleted or reordered original resource, or an extra lesson row.
CATALOGUE_ORIGINAL_ROWS = 734
CATALOGUE_ORIGINAL_ROWS_SHA256 = "b8ffcb16f5fd2a413e8a0b06ad2d4b112f450364fa294377869dc32c8235bb2c"
CATALOGUE_SHELF_ROWS = 49
CATALOGUE_SHELF_ROWS_SHA256 = "3ab3e66308af203301acf75d57fa78728c83e6a336ba8a17d0392d9a092859c5"

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
# Reviewed Education completion publication caller, Site PR #268, 2026-09-06;
# advanced to Site #299 47811e56, then Site #301 50877370 (Play revision registry: Glitch HUD and
# §3.3 touch-action revisions, transition pairs) by Order HC4.
PUBLICATION_CALLER_SHA256 = "30085564dd29c8c7c9c94a60ab9788716d21cb850d308258203f8f2755c304d3"
PUBLICATION_GATE_WORKFLOW_PATH = ".github/workflows/mbm-cross-estate-unification.yml"


# HC3, 2026-09-06: exact reviewed CI-only LundyLoop proof transaction.
# Full hashes remain checked on every Apps run, including files not in the diff.
# No standalone payload or arbitrary CI path is granted. Both gate copies match.
LUNDYLOOP_CI_PINS = {
    ".github/workflows/verify-lundyloop-professional-os.yml": "79f2df4bab2df52719160ccf9d1fe8d0ae543555778ab7d3a660094dfb0796d0",
    "tools/lundyloop/verify_live_bytes.py": "a27f791633260e7e2d8ba7ca2abe5a35db105b9ccbf96d26205628dcc1e636ad",
    "tools/lundyloop/test_live_bytes.py": "972ca2ae06da44722bfd011fda03a361c6011c699f95bb6ce78bca95b71f2e77"
}

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
            errors.append("reviewed catalogue requires the original 734 rows plus exactly the reviewed hub rows")
        else:
            def row_digest(value):
                encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                return hashlib.sha256(encoded).hexdigest()
            if row_digest(rows[:CATALOGUE_ORIGINAL_ROWS]) != CATALOGUE_ORIGINAL_ROWS_SHA256:
                errors.append("an original catalogue row was removed, reordered or edited")
            if row_digest(rows[CATALOGUE_ORIGINAL_ROWS:]) != CATALOGUE_SHELF_ROWS_SHA256:
                errors.append("the reviewed catalogue hub rows changed")
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


def lundyloop_ci_errors(root: Path, kind: str) -> list[str]:
    if kind != "apps":
        return []
    return ["reviewed LundyLoop CI bytes differ or are missing: " + rel
            for rel, expected in LUNDYLOOP_CI_PINS.items()
            if not (root / rel).is_file() or digest(root / rel) != expected]


def boundary_errors(changed: set[str], kind: str) -> list[str]:
    allowed = ALLOWED_DIFF
    if kind == "apps":
        allowed = allowed | set(LUNDYLOOP_CI_PINS)
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
    errors: list[str] = publication_errors(root) + lundyloop_ci_errors(root, kind)
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
            # HC5 D2 (Matt's ruling, 2026-09-07): support buttons live on adult
            # pages only, so the Creator Hub's "Buy me a coffee" line leaves the
            # pupil surface. The reviewed result is admitted by exact digest of
            # its normalised visible body; any other wording change still reds.
            current = hashlib.sha256(normalized_visible_body(text, kind).encode("utf-8")).hexdigest()
            if current != APPS_HUB_REVIEWED_WORDING_SHA256:
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
        for rel in set(["index.html", "resources.json" if kind == "lessons" else "apps.json", PUBLICATION_CALLER_PATH, PUBLICATION_GATE_WORKFLOW_PATH, *CANONICAL_HASHES] + (list(CATALOGUE_PINS.get("files", {})) if kind == "lessons" else list(LUNDYLOOP_CI_PINS))):
            src = root / rel
            dst = fixture / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        good = run_checks(fixture, kind=kind, canonical=canonical)
        if good:
            raise RuntimeError(f"positive-control fixture was not initially valid: {good}")
        if kind == "apps":
            for rel in LUNDYLOOP_CI_PINS:
                target = fixture / rel
                original = target.read_bytes()
                target.write_bytes(original + b"\n# planted unreviewed byte\n")
                if not lundyloop_ci_errors(fixture, kind):
                    raise RuntimeError("LundyLoop CI byte mutation was not detected: " + rel)
                target.write_bytes(original)
                if lundyloop_ci_errors(fixture, kind):
                    raise RuntimeError("Restored LundyLoop CI bytes did not pass")
            if not boundary_errors({"tools/unreviewed.py"}, kind):
                raise RuntimeError("An arbitrary CI path escaped the boundary")
            if not boundary_errors({"LundyLoop_Professional_OS.html"}, kind):
                raise RuntimeError("A standalone payload escaped the boundary")
            print("LundyLoop CI controls: real green / planted byte red / restored green; unrelated paths red")
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
