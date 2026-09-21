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
    # SW2-T5R1: reviewed inert vocabulary; no component styling changes.
    "assets/mbm-tokens.css": "2e78ad7348ee7beaafda1f33ff5b112e7fd121654d7a9d39fc1ec681dee00019",
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
    "resources.json": "733772e93ae497830627af2c3a21fcbf743bb42b550d40bfb24959c8e221f9f1",
}
PIN_COMMAND = "python3 tools/pin_manifests.py   (from either checkout — it writes both gate copies or neither)"

# Explicit education catalogue release, 2026-09-05. Matt authorised a new
# browsing design, so the old Lessons wording comparison must permit exactly
# the reviewed result. These pins do not exempt a directory or a lesson: every
# named byte set is checked, including additions, on every Lessons gate run.
# Apps retains its original authored-wording comparison. This block is updated
# in both gate copies by tools/catalogue/pin_catalogue_contract.py after review.
# SW2 A hub wording explicitly approved by Matt, 2026-09-14; manifest/tool bytes stay pinned.
APPS_HUB_REVIEWED_WORDING_SHA256 = "9e5a4ac6c1e9bfb04a1c0186a82fce96aa03565a02dc3f18ee1569fb4b5664bf"

# BEGIN REVIEWED CATALOGUE PINS
CATALOGUE_PINS = {
    "visible_body_sha256": "9961e6f6c4627d644a364dedef7b37b1731cf8508e0ec85909f070a328bec187",
    "files": {
        "_sownb/CALENDAR_SPINE.json": "cd1cc2a6ed95877caa8826c155b605782ea696a8a801b3cf6489b2b0a8fe35f8",
        "_sx3/SX3_PASSES_LEDGER.md": "6ddd4d692a5dfdb54e348896f6981f44a396688cf6816aa9d7986841f40fff43",
        "tools/sx3/pre_ci_catalogue_sweep.sh": "9848b9e4e9ccab0bd8225d26d7ffa4683c59c249bff688f33c5d665671d9f818",
        "assets/catalogue/display-titles.json": "e8072487ca9d163089b83160ac5c57a8e94729c09d9fb0bb76632938a018bcb9",
        "tools/catalogue/build_display_titles.py": "4256ab6b07420af4ef090e57d32b8f29fcae88d9075d64750e52f17947dbd8a1",
        "tools/catalogue/check_display_titles.cjs": "5d06689114a69124a2d7f59d644a85775756eadd2b470df01e066c2202df681b",
        "tools/catalogue/check_display_titles_browser.cjs": "5662cdb93c7796ead4fb9bb69ce94ac65fe1e29e103f00c65bd07a4d5129a7cd",
        "tools/verify_lessons_chips.mjs": "e417afd94ae4f3a450caab2edf4b6c41d14e4588f070d0ad822263e30a86cf39",
        "tools/sw2/check_tokens_inert.cjs": "0feabd4ad86fd578ca85a69b491dd92ea133697c77f4385cd3a15ebc1810abf9",
        "assets/catalogue/lesson-order.json": "f71e0c84b03943220143df9dedc0f28b3d13a89de46b0dac4c6cde6ad02e2e12",
        "tools/catalogue/build_lesson_order.py": "2caa4b97584b58330e3ca8e07754cc2877d687a1660688e321c50b730f89db54",
        "tools/ux2/hub_gates.mjs": "80ae8def49c49e549c8a2e6b65d521cfdaebb2b7d05f650fa6d5e436f2b6586d",
        "index.html": "389c3320b158e9bc472b4402d41d1d23e4bb2d78b54385884c0be6ca31f73309",
        "Science_Teesside/index.html": "065d524af2647cb18c861e8d9ef2d9d524cdaea777482f5b722d24e49a773977",
        "Humanities_Teesside/index.html": "6f69b888c3829c2fe44c2bc579b4b598acf35aa297e87621a68138c99b221388",
        "humanities_teesside.html": "1e2faab06cb4caf4a26f377200a55cbd380c7f3ceada74f666998b47611896b7",
        "pack.html": "c05cde1b83de3da3a292d150e7c400782719d30aec6a130fb4df158786993b65",
        "assets/catalogue/pack.js": "acfd0f1b00dce1421fabd8a1870b55d4c54ffc1157b2efe8a01b354f385ccf4b",
        "assets/catalogue/pack.css": "ba6c5c84bcff84c023f2f10ac345a159f48ea97b2e8eb542cb3e56435204d63a",
        "assets/catalogue/pack-notes.json": "c7c30351306a21f360190b202b98bf202fde02b8376a1a54886204e718850988",
        "tools/sw2/pack_notes.py": "a81a187002a69bcecca28c9c3130f546e1aae279d5af92cf750a6f9fb04c8fe6",
        "tools/sw2/stamp_pack_page.py": "ee37ba3739598535989353dd2ecd0225ad8f4ded0b9f3e6d83bbc0c2326bd4d8",
        "tools/sw2/check_pack_page.cjs": "fb093130e13b7e11e996f681f7845620b51e1a2802b6e7b80e8cf3eef92c5eff",
        "subject.html": "e5515e9169c05d51252d0ae1a7c68c49df3011fba4b481d587f5425cc060af96",
        "assets/catalogue/hub.js": "588f4c2dee4aa5030901f6d260f5dd160aaf306d4634732e99d38046d334e652",
        "assets/catalogue/hub.css": "603586d0668c39a2039891ab9f599cc234f65748a6794eee7fc65c334b5a23e5",
        "data/calendar-spine.json": "d199474b13c9d340add2c87165396d83712b0f1c9f8bd03b7b12e8fdf6af0d61",
        "Humanities_Teesside/David_Cover_Autumn1_W3-W7/index.html": "4e25eb9ca8f9f93c720d88d945f3d6d79580f3362a88698fe7af75d146f01e96",
        "assets/catalogue/catalogue.css": "59abee137c41a8a015e42cf0b32d20b7f4e5fc8e3d236a1cd735322386bf8569",
        "assets/catalogue/catalogue.js": "a0fd3efc8356377effad7249be7222984ce92947a8143259148851dc399de5c7",
        "assets/catalogue/lesson-navigation.js": "fa6bdae6826950422dfb13a905a2a50c5c959bef50fb438f00b6170befbfaf8f",
        "assets/catalogue/science-shelf.css": "b2b1eb328662d841add139ccfff107f985f17373f1ee82b8762475663097ab60",
        "assets/catalogue/science-shelf.js": "a59fe0c988a5de7d614afc6a36d7dacf14c6e3fa92c732740442e4914d00f356",
        "assets/catalogue/terms-and-styles.json": "f3a6b10216dd955eb1ef3e47c1955a5feee0e09d2ac2b600b212196d28056191",
        "assets/catalogue/science-shelf.json": "f4b6725b373070831b91d07b64a0dec216c422571c891c99328701a1f4dac89f",
        "assets/catalogue/humanities-shelf.json": "b2facaa50c6781f0fdf19fad5b3b170bfaef54546c030e951956ccf47223f8c0",
        "tools/catalogue/build_catalogue.py": "10a704418e67c6b9ec80bb911cfe267df7a12e8c4adbb6e878ca14c5cfb7c3b1",
        "tools/catalogue/build_science_shelf.py": "062e30e917c415fb241c4c98fd86d682ca5f1bebe842696e03ff8e44c3840210",
        "tools/catalogue/build_humanities_shelf.py": "3ed6e289a2656ed5de228082012dd9e957d2d13b2fa77f5857b9dee22ae138a9",
        "tools/catalogue/check_catalogue_static.py": "eaea1b94c5f36b5f998529a5822866b00502af3dae6e7304b7040d85369354a3",
        "tools/catalogue/check_catalogue_dom.cjs": "4481a0cb254ab61a151acb7df530d6fc9b4c8264de01b4c411cee920d28d84d2",
        "tools/catalogue/verify_education_navigation.cjs": "b0d9297a33fb9ea2494fecaa45e02ae6fcf6fa88e6a62ced35cf521fbb1851fd",
        "tools/catalogue/sync_shelf_card_titles.py": "f906e244fd8fd2e596e6e5e0a1fce9a53bee828eed0b74194eccf4860e45b7a0",
        "tools/catalogue/HUMANITIES_STRAND.json": "0a9f184b3253c757ae376898358cd269ca2f1b2b26df8a845b4d0ffa45cfa7af",
        "tools/catalogue/hub_sections.py": "696c3a956583d4872bb33ebf63bd499dd1db4fa8acec09948e677b3ed44253f3",
        "assets/catalogue/shelf-base.css": "951d6188059da3d2f20717ab7d82773b335d453d8c2d82f5b75f230229351e61",
        "assets/catalogue/humanities-hub-bindings.json": "edd1c2aca59ffb39409c1aaec8f861d2141c44e81978e9bd48dfa85be634e3dc",
        "tools/catalogue/restamp_evidence_sha256.py": "611d3db56e0289b172bba1bd2794ca22f597a9300ff4f0321c45ff2c7bfca54e",
        "Science_Teesside/Build/START_HERE.html": "acac26140f5aeef22292e6ce3831fa61aaf5e62432cc3998b340918c8bfaee7f",
        "Science_Teesside/Grow/START_HERE.html": "d2bec305dec3212215c6f599cad3925c571f9a34ca6e85268893c8ed142170dd",
        "Science_Teesside/Launch/START_HERE.html": "10b46e7cf26e3aa4b7f1fb4758a039bcbec7000bc2ec8d30dfe3ce0e0b966353",
        "tools/catalogue/SHELF_SELECTION.json": "7d4cb97190e6007ebaf5ed6fd91117fe3a0b4c3f66603dc8c619c73fc1a680ba",
        "tools/catalogue/HUMANITIES_SELECTION.json": "5df3e69d4d9d3825225bcc80376b3fbebf61656df6e333f6b9a8aaded1893bf4",
        "tools/easter/science_original_browser.cjs": "aae28a4166d41546cbe5b0acd0866eeaf5e6f47cd5b1949fc48ecb2d4c79a1ec",
        "tools/science_pack/browser_checks.cjs": "058c9bc1f06c876f2994a23d467d83fced683c6355eb92d0ef43986d3e28d72d",
        "tools/prepare_served_publications.py": "acae94bb9c142e20479bc9e5e103b09af87ba84ba3b1dde7baaa86cdb0792629",
        "tools/test_served_publications.py": "063e76bc6579402a41b0bd0b7a79ae99be301cb9db97deb5b7257b85687b851b",
        "tools/verify_served.mjs": "1de323833258e4c051543ee4daf9a9eedc61292510d5a6d621a2b4ab1dcbbf2a",
        "tools/test_verify_served.mjs": "1459d5d50db08514e64bc48def2c80e71ef160ad3023c554452de7c1a836132d",
        "_sx2/DECISIONS.md": "98959aafb9360877134158427865aabf69aeab094b499b58c31451fec9aca93e",
        "tools/ux2/resource_sizes.py": "2e8d36613fb39e3114c2006337771ddc9c724f9b6333a6e05cfed4e646e4224b",
        "tools/ux2/s1m_published_input_proof.py": "95b82480a9fdbb607fcaf3077d1e58dc1e9a5eafd96581fdbec281c979de1d10",
        ".github/workflows/s1m-published-input-proof.yml": "fcc9f4c6b6a550873bda92346bb73e47d9ec0cfe95664a8eec66d0e7947dfb76",
        ".github/workflows/watch-main.yml": "9a468937b9eefbcdb010f9eed9a2b48f4111761202932fadad680cc3b477f3b6",
        "tools/verify_v6fin_w7_r1_r7.py": "f864bce7fa7f8482520dc41851bcb1e428de8529a10d6d0977645a4c9aed3865",
        "_sx3/FENCE.json": "36e0fd81b283dc41957acff27b906858522ab27eed3c04c6350d5050f230e913",
        "Science_Teesside/Launch/Autumn2_W7_2026-27/SCI_L_A2_W7L1_Topics_2_3_Assessment_Introduce.html": "2b6fedfe3044b25254d4e17fe0eb7c235e0ed176cb50ab9c7bdca3c3a3c53d1d",
        "Science_Teesside/Launch/Autumn2_W7_2026-27/SCI_L_A2_W7L2_Topics_2_3_Assessment_Explore.html": "b8255a810f66250666744fd7793318d2bbabe0780a85f7ad8c97025337bc17c4",
        "Science_Teesside/Launch/Autumn2_W7_2026-27/SCI_L_A2_W7L3_Topics_2_3_Assessment_Do.html": "553454b2d545e0f6d0ed15cc4038ed2108ea7329ca8a81b945597d04c039c88a",
        "Science_Teesside/Launch/W14-W15_2026-27/SCI_L_W14L1_Genetic_Condition_Research_Introduce.html": "d9556b6fc52357fc4c354e6f354270ca9e8da55f283dbcdd7a57faef991cef96",
        "Science_Teesside/Launch/W14-W15_2026-27/SCI_L_W14L2_Genetic_Condition_Source_Evidence_Explore.html": "08a47f06000f3a14ac38f6afb94b304b8f6dbf2f36b803f146639d1a7dae52f7",
        "Science_Teesside/Launch/W14-W15_2026-27/SCI_L_W14L3_Genetic_Condition_Presentation_Do.html": "59fa8708f3fc2b1331a49a03b63465e2e2713af8c7d69091df356ec287970491",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W13L3_Inheritance_Probability_Do.html": "d0d4f47746946fd0cd332be94865e7282fdaf97fdd800f6646718cc35b6beb7a",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W9L1_Cell_Cycle_Introduce.html": "c0e2a3725ab889f9b0b51e5bad3c9056d1faf973f9f6353122947139e6084586",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W9L2_Mitosis_Sequence_Explore.html": "3439d5e6d06fba838ad695d732b08f86775bf6fbf0536812447ba0ed5ef8116d",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W9L3_Identical_Daughter_Cells_Do.html": "a40855bf2e4d520ad1ec45f8dd442635141cb459c802dc56f9c4198505d708fd",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W9_Copy_separate_divide_Classic.html": "649a152c0fd4a768496f55de23add747acb75dcad4e73a30bfe9453e0d6bcc8d",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W10L1_Growth_And_Differentiation_Introduce.html": "c5f7062f97517b87080578f7e9cc996320450a28414aafef722c5311abf74f02",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W10L2_Stem_Cells_And_Meristems_Explore.html": "386454dba2e88fee123ddbd39c3965c6af2f7c18248eb1f4c58665f0f2c56ea5",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W10L3_Growth_Stem_Cell_Data_Application_Do.html": "5f4fa6ce615bd0210601c6229f15e76b309e7d3e070aae67be703689114cfadd",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W11L1_Stem_Cell_Evidence_Introduce.html": "d080289046c68268eb64f388251adbb05109f0c7da2ffb1fa0d596d44f82f66d",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W11L2_Benefit_Risk_Uncertainty_Explore.html": "b4e898fa0e87db690fc1b95206df6fa5c95ff6827e267b8c96d10f377527ac9f",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W11L3_Stem_Cell_Discuss_Do.html": "ee3308dda387e77bcdec5a1d0bc150367858a906469885c9cdb21c466ec412b5",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W12L1_DNA_Hierarchy_Introduce.html": "84b9283cd2d65a80204ed899f89205572f290d6661fb7d62fe513f9c897a1873",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W12L2_DNA_Structure_Explore.html": "e84e681deafc43f233e582ae15adeccebe06feaa3b2bb2674d7e8e4089164517",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W12L3_Fruit_DNA_Evidence_Do.html": "0a3e7536dc9110d705e0cc58e70bc845c982b3a1f9431d0b01debac1247c03cc",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W12_Zoom_into_genetic_information_Classic.html": "90e297a0cd6989c101ecc966499c58ad6f830ede7a8c278e20319d35df6380b0",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W13L1_Alleles_Genotype_Phenotype_Introduce.html": "fac4a58dbc596176adf28e246565c8bd46636a9121fb84be50e15ac8bd9c5e04",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W13L2_Punnett_Square_Explore.html": "da80ec932131c969c456ec35ff3514132901bbb51c2c002868308a220e71e79b",
        "Science_Teesside/Grow/W8-W13_2026-27/SCI_G_W10A_Solar_System_Research_Explore.html": "e10e97c2d792de2fad0ce454962e3a31ec608b43750bd71315b3bb1b0655981a",
        "Science_Teesside/Grow/W8-W13_2026-27/SCI_G_W10B_Solar_System_Presentation_Do.html": "18c99f9225f39ec3e6e4d5aecfc94ab8cf208fd2e398e2dfe12f7b2dfb2c31c6",
        "Science_Teesside/Grow/W8-W13_2026-27/SCI_G_W11A_Global_Warming_Explore.html": "82b34329f1faf788152bc22c9e1f9eb8fd8236f3116d07337b9dca62b1325ced",
        "Science_Teesside/Grow/W8-W13_2026-27/SCI_G_W11B_Climate_Action_Do.html": "5ef530499159bcb9ce80a063e110ce4047545f7a70444080afda495b2c7fa7dc",
        "Science_Teesside/Grow/W8-W13_2026-27/SCI_G_W12A_Science_Connections_Explore.html": "062a12a7dee5f5199ae91726f9ac0009cdf17e2dc4446d9e75c0288ab1213024",
        "Science_Teesside/Grow/W8-W13_2026-27/SCI_G_W12B_Science_Answer_Lab_Do.html": "4ce4be0d9399e88b600e31c1eac960a93b2f1601f733e17aed2cfdbcb88a3b43",
        "Science_Teesside/Grow/W8-W13_2026-27/SCI_G_W12_Follow_the_warming_chain_Classic.html": "94addd62c6e0169778b206e5dd59f51b508fd2ad329594718472d5222f224335",
        "Science_Teesside/Grow/W8-W13_2026-27/SCI_G_W13A_Rover_Rescue_Plan_Explore.html": "bae4a588c9382eec0be5901a500a9e3cde6e4b3d7bbc43d8fb1aeabebace712b",
        "Science_Teesside/Grow/W8-W13_2026-27/SCI_G_W13B_Rover_Rescue_Investigation_Do.html": "94e0f4685d789407d127a2c5c031676aa62277d75365f681ad217172550d1a77",
        "Science_Teesside/Grow/W8-W13_2026-27/SCI_G_W9A_Spherical_Bodies_Explore.html": "2681b3f42b2bd6b8acedcd682c23d617c77eecfcce03b7cdac3db5a6751edb2d",
        "Science_Teesside/Grow/W8-W13_2026-27/SCI_G_W9B_Spherical_Bodies_Do.html": "4ad909faa2bc690cdb530cdd02555b2c216c27d5a4a8f2986e4e29814dbce984",
        "Science_Teesside/Grow/W8-W13_2026-27/SCI_G_W9_Turn_Earth_explain_the_sky_Classic.html": "3efded0179e818a3e7c0a5d0692610acfb4b91b1d85bc937c4b79bdd79668851",
        "Science_Teesside/Build/W8-W13_2026-27/SCI_B_W12_Give_a_rock_a_job_Classic.html": "509f38056bd09e903c70b0426ac55ab7ff73f7da10261a97eec11d49d7b27d1c",
        ".github/workflows/glv3-verify.yml": "4bf27ca7471a21359e35d1bc7277c5fa0adeb5f31a47c769f192165796037088",
        "_glv3/tools/verify_change_boundary.py": "b7b8f392e28f9cdf3aca237b08646af60301cc76318f93a0d178d67685574f54",
        "_glv3/tools/browser_verify.mjs": "737ad30f297e061407161743f017614179cc6c56f1c9a3904bbe7c98df38c888",
        "_glv3/tools/chip_gate.mjs": "16cdd5c0ad3745c57340ed0ec6a208d221e4793bfc9b1cd9bc703a6c2613dd9a",
        "_glv3/tools/catalogue_membership.mjs": "4d7ab03e23ee0d3c3fc934f4f0a901afc61169754db099f4f5c24dd9cce058ec",
        "tools/humanities_resources/SOURCE_MANIFEST.json": "f76b592cd5f6e755bf31906e68bfcb05fec7d80a8d5a104306e617fad23ef18e",
        "tools/humanities_resources/DOWNLOAD_MANIFEST.json": "1d872aa4e9d01d7f10d26a0e8d182ddcb4513598413314f7c38d055318d39a2f",
        "tools/humanities_resources/CONTENT.json": "335ea55d7964d8095064e2c67c95fbd8d65e28b4d1ddf25f6e4ee812abd29b98",
        "tools/humanities_resources/ORIGINAL_MEMBER_MANIFEST.json": "c4ce9e5a0a5d966ee31f401ae476a2dc10a43aa8dc749e09b2cef87b745db073",
        "tools/humanities_resources/build_resources.py": "d99981a314f152af98fe3a64c48f7ac1bc2afe184bb0e4a2c504b8d00399366f",
        "tools/humanities_resources/check_resources.py": "ec5383e3a34cbff999f190b0014a4a73e00a3a29e2714498f7620fd638dc2aa5",
        "tools/humanities_resources/resource.css": "1aed9aaca0d73a4b200c4e5d0977e73f4e906c747d7340c7a62f4197a8344bae",
        "tools/humanities_resources/resource.js": "ad40afed95490bfcce92dc062da46e1b27bcb96bdc80e37eabdfe02bf6ffc446",
        "tools/catalogue/TERM_AND_STYLE_EVIDENCE.json": "98d77c564d0c0f506a8a3bcc7e5366e1c4e457a61090ce150c9e064823250f84",
        "tools/catalogue/TERM_REVIEW.json": "b0ed0d82fe21a222c75f6a38390b01defc0d5d958fac8e85421b7901ce6d201d",
        "tools/catalogue/SCIENCE_WEEK_BINDINGS.json": "2f7ea74d51d4d1e132c65ec756780f8e29d5a2be1c4efd94e1c4ac85b9096200",
        "primary/year5/science/autumn/forces/Lesson8_ExploreGravity.html": "20047720bf1d309055abdf232d341b6fd99b833631efa0bcbfb3dabed9671196",
        "primary/year5/science/autumn/forces/Y5_Forces_SoW_and_Plans.docx": "ca36cfd92f1c768ea66f0eb748d47e6227f67569f77b5472d0da13d03f92f2e6",
        "Humanities_Teesside/BUILD_W1-W8_2026-27/BUILD_HUM_W1_People_Special_To_Me.html": "030be544f76147106e1a7f817ddca11142fcbaef168c28ef2397316a069f384a",
        "Humanities_Teesside/BUILD_W1-W8_2026-27/BUILD_HUM_W2_A_Special_Book_A_Special_Place.html": "197d3ebfab750e84d89ee5e3dedb177b9d86d768602d0ef62be0ac4582cd34cf",
        "Humanities_Teesside/BUILD_W1-W8_2026-27/BUILD_HUM_W2_People_Who_Help_Us.html": "7b90dbfb9e82e1a4d20dda3703e68086c5367643bd3b58c8533e97836dc80521",
        "Humanities_Teesside/BUILD_W1-W8_2026-27/BUILD_HUM_W8_A_Festival_Of_Light.html": "a91c419bde53ffefe77b17db0e8ebb9973b4df447690c6a41a94c76210a654f5",
        "Humanities_Teesside/BUILD_W14-W20_2026-27/BUILD_HUM_W14_Festivals_Display_and_Reflection.html": "bf14c15092537d25d1b067d5cc32bba8b5ded673e2d8247b352b0431c8abbe59",
        "Humanities_Teesside/BUILD_W14-W20_2026-27/BUILD_HUM_W15_My_Week_Timeline_and_Caring_Stories.html": "97e71086dcda835b431f9cf94d545f802429faabbb0bd76d26a30987c70ae8fc",
        "_sx3/CHASSIS_CONTRACT.md": "7bcbd67432df1edcedcccacffbeae56b16ab933cea6dd6ada761a263781930d8",
        "_hum/EVIDENCE_LIMB_CENSUS.md": "43870031ec3c0059fb03ed16180a40d630b2eec63a4fa29cbafd3ccee7415e4d",
        "tools/hum/evidence_limb_census.py": "5d360d643641dd27784f5ef06c850ef20b424d112e6de1a98d1d5768c2ef69e4",
        "Humanities_Teesside/GROW_W1-W8_2026-27/GROW_HUM_W1_Beliefs_And_Worldviews_Around_Us.html": "e026cb09ca0c26998be6172bd5622545878cef9cd509b4d2f6c0454ca7ab1389",
        "Humanities_Teesside/GROW_W1-W8_2026-27/GROW_HUM_W1_Migration_On_A_Timeline.html": "dbf44fe5be6e352cd6210d1b7426c15bfd4e00dd6f02a9f1643ab41d90ee75ce",
        "Humanities_Teesside/GROW_W1-W8_2026-27/GROW_HUM_W2_How_Beliefs_Shape_Who_We_Are.html": "adc0e844bb2b51bb9c0f646464ab03ae67736b28a1e249d27d56c15e28ac9734",
        "Humanities_Teesside/GROW_W1-W8_2026-27/GROW_HUM_W2_Reading_A_Migration_Source.html": "2c505b209aaf25af14425d63dfc648939257a8f3bade68fd3226296b7da80287",
        "Humanities_Teesside/GROW_W1-W8_2026-27/GROW_HUM_W3_Why_People_Moved_And_What_Changed.html": "5a389f52fac689814f978804cfa9e1213d9b16df21c74f3219bea27df2edffb2",
        "Humanities_Teesside/GROW_W1-W8_2026-27/GROW_HUM_W4_Diverse_British_History.html": "1f13e87e4f3f11233b417cf1e05c038e83de2bec3d8c49bfd092b9c5527c7b4f",
        "Humanities_Teesside/GROW_W1-W8_2026-27/GROW_HUM_W5_Was_It_Significant.html": "9ac862ecd06d8438d8f8a1b4a4a112f5fc95e7136a19226080c6e52c2583fcd8",
        "Humanities_Teesside/GROW_W1-W8_2026-27/GROW_HUM_W6_Planning_An_Account.html": "a09c410a1b04098e91327b523c04d4877b40343e3c2f01e41c66f65d01002708",
        "Humanities_Teesside/GROW_W1-W8_2026-27/GROW_HUM_W7_Writing_And_Marking_The_Account.html": "015a5514cc1145a35084834d470f3138a0b41359d43c6e7385a539a81fc36e0c",
        "Humanities_Teesside/GROW_W1-W8_2026-27/GROW_HUM_W8_Finding_Places_In_An_Atlas.html": "6739b5cb8d059f972012844f20d6a49249b5bec231cc018285675a44dcdca7be",
        "Humanities_Teesside/GROW_W1-W8_2026-27/GROW_Humanities_W4_Explore_Hanukkah_And_The_Theme_Of_Light.html": "cd82d9e3ba3bddc820e4e6980338f8055d42e4f7c4279532d4eb6a2d78605f10",
        "Humanities_Teesside/GROW_W1-W8_2026-27/GROW_Humanities_W5_Explore_Christmas_And_Christian_Belief.html": "e21ff0ff140cdff349c3e6f8dc5bc314be9e8d6be05d888cb8008382b5a85daf",
        "_hum/LOOP_CONTRACT.md": "c2574700e93b178c32138a27ba05c5496f3f8f83736154ab1c86b71f552bd08d",
        "tools/hum/loop_adapter.py": "04efdbd2c63baad2f6fac7b3b75d307c059a0327108f46130b49fad60c73163e",
        "tools/hum/render_proof.cjs": "35aee6aa2d3b11367c310258160c7e01dabc41913e767968f88c27f6f8ec899a",
        "tools/hum/verify_loop.py": "a0f02c3a52f71b2e957f374d356576105db0877f9a3759dbb21088ce0761caba",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W1_Belief_Identity_And_Belonging.html": "6dc9a434f33931eb5f38c65454feb5fb87588afaa0053f3a0c95c216a4c8fc4a",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W1_Migration_And_Identity_In_Modern_Britain.html": "b965d521d918cd24408059c8d940966c16c138f2a8c40fc51860e2f8d67ea9c3",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W2_Cause_And_Consequence_Of_Migration.html": "c49b62b36952fbe4da9cbd19dfc7401a628ecbc423451a188fa3fd9b55d8dd0a",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W2_Two_Worldviews_Side_By_Side.html": "439d8cacebdc7911314b6aad2bc92d0ecff5dce7364d7bea4b56ac70ba1e15d8",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W3_Can_this_record_prove_it_Classic.html": "1737abaa8804ae7da34ae45ef064c133149dbfe619a0e122e9dd2c0862d85660",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W3_Evaluating_A_Digital_Archive_Source.html": "a385de10b4db2e5a5370ed24db214bd0ec0ade59d2604eae12b51d3d74091204",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W4_A_Timeline_Of_Twentieth_Century_Britain.html": "24f7ea8a63f02f88a291a59b65db8c878e8ae85a32d831b79736b31113d10559",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W5_Who_Shaped_Britain.html": "0a1a646dda79dd7db040af551128294caef16fba6e3e90a4dae233d99b34fa7e",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W6_A_Structured_Account_From_Evidence.html": "55e46c6599d930327833d95493f1017fba4ba76c64ba4fddbc540f9ae49985eb",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W7_Source_Based_Assessment.html": "a42f61b9de0ed5b9d89ab18cdde017dff34dd789b43219011a5a563ad7cdab87",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W8_Maps_Symbols_And_Grid_References.html": "7dcb2d67927b3d74376f4e1c822aac82d036210af59e94cecd8647ef8d6fe7de",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_Humanities_W4_Festivals_Shared_Values_Day_Of_Peace.html": "2495d9a762c6d434c5d1cbac3b0ac63d8f7562b2f38a98d863d0e3d201f16239",
        "Humanities_Teesside/GROW_W1-W8_2026-27/GROW_Humanities_W6_Compare_Festivals_Of_Light_Respectfully.html": "d4da31012106415fca6641fcd1d5bcdd7e9213cef98897dcab972f0602d850e4",
        "Humanities_Teesside/GROW_W1-W8_2026-27/GROW_Humanities_W7_Reflect_On_Remembrance_And_Shared_Values.html": "3fe17c6e46638def69dfd72132605e4540f289f272cc87ca2d9408c7525a5cfa",
        "Humanities_Teesside/GROW_W15-W20_2026-27/GROW_HUM_W15_Rights_Timeline_and_Belief_Resilience.html": "dd22c4d6f96f00a9f6a1174672c2145dafa34171d1148f65b0c68b1c4b1dae03",
        "Humanities_Teesside/GROW_W15-W20_2026-27/GROW_HUM_W16_Sources_Campaigns_And_Hope.html": "8acbafb35b90a104d1aad179c188d5e29e4c99e5a35db033daa7087d8edeb07e",
        "Humanities_Teesside/GROW_W9-W14_2026-27/GROW_HUM_W10_Teesside_Connected_World_OUTSTANDING_V3_1.html": "6c0d8b003c060237fbbf308ff57b8c90db4d939d8299c1658c0e4bef4af1bc36",
        "Humanities_Teesside/GROW_W9-W14_2026-27/GROW_HUM_W11_Light_Across_the_Map_OUTSTANDING_V3_1.html": "3ddc21faaf0d98be4304ad63bd8c659b556676288fc0c4ac89b55c622b543a64",
        "Humanities_Teesside/GROW_W9-W14_2026-27/GROW_HUM_W12_Compare_With_Care_OUTSTANDING_V3_1.html": "3fcb995013519cafcc155e7ad11c3cde94913149dd8362233a3c67e418c0c583",
        "Humanities_Teesside/GROW_W9-W14_2026-27/GROW_HUM_W13_Belonging_Briefing_OUTSTANDING_V3_1.html": "a8fc4a21540e85c6ff00ecc04fcfcdcf27ffaa3b2017022ee99ed7d5299f5170",
        "Humanities_Teesside/GROW_W9-W14_2026-27/GROW_HUM_W14_Map_and_Belonging_Challenge_OUTSTANDING_V3_1.html": "6935c53274bf191f7cfd0c62c0c03bae85e60e44c00b85f0abfa19b4dd81aafa",
        "Humanities_Teesside/GROW_W9-W14_2026-27/GROW_HUM_W9_Pinpoint_the_Place_OUTSTANDING_V3_1.html": "69a9285e4e671645754b80c8fd1624d699977504cfa40aacf770acf51a465024",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_Humanities_W5_Structured_Explain_Response.html": "adaa425bab46005aef4cf6c6d6997760ff75818965a7461af2f145c974016762",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_Humanities_W6_Remembrance_Peace_Across_Beliefs.html": "b0e93d11cd494ec361058214da3193f2721cd6531fbbc99af4a0b3c888dad351",
        "Humanities_Teesside/LAUNCH_W1-W8_2026-27/LAUNCH_Humanities_W7_Belief_Identity_Assessment.html": "1b2c8e41fe9e740614b0685c6ab594614518acd15788905282d84cbe7d1e239b",
        "Humanities_Teesside/LAUNCH_W15-W20_2026-27/LAUNCH_HUM_W15_Conflict_Causes_and_Ethical_Decisions.html": "36aad344c9e91f5c1fc4aeb28c111fee64864868e28ee7dd36252d0c6caa1047",
        "Humanities_Teesside/LAUNCH_W15-W20_2026-27/LAUNCH_HUM_W16_Steps_In_Law_And_What_Comes_After.html": "1b2b12b93d4bf4583aca5356151b2c469d7ee3ba93d502d6a943686cb93a0b42",
        "Humanities_Teesside/LAUNCH_W9-W14_2026-27/LAUNCH_HUM_W10_Settlement_And_Urbanisation.html": "127026a754e180800e9202a552f938b2af446730bc5e533f2aeb822b12692e64",
        "Humanities_Teesside/LAUNCH_W9-W14_2026-27/LAUNCH_HUM_W11_Local_Fieldwork_Collect_Data.html": "3f83f53d6a8b7a02d397aa554f6a59977a04c9a1beb3bfa532949f23ed4eef92",
        "Humanities_Teesside/LAUNCH_W9-W14_2026-27/LAUNCH_HUM_W12_Fieldwork_Data_Graphs.html": "4018cf72fb54cad4c3d6e21d4dcbdec6117554331546fefbd4b756684cc83a8f",
        "Humanities_Teesside/LAUNCH_W9-W14_2026-27/LAUNCH_HUM_W13_Contrasting_Places.html": "66517aec3c3bf97dc4eb536535aaf009bfb8b91a0f0088b04c7d6d1418fcafbf",
        "Humanities_Teesside/LAUNCH_W9-W14_2026-27/LAUNCH_HUM_W14_Fieldwork_Enquiry_Write_Up.html": "1e200c6fa11000e66d7e529135876de9c2481ab107f4cf1a68cdc77691f21994",
        "Humanities_Teesside/LAUNCH_W9-W14_2026-27/LAUNCH_HUM_W9_GIS_Layers_Reading_Place.html": "8544e086b5e4a6c611982f289fb697626731041eb1cbbd77a4f3e454928aba61",
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
        "Science_Teesside/Teaching_Packs/GROW/DOWNLOAD_INDEX.json": "f4838737eba7f6db77bf5d8741cdaf046a21d15159da70cbc550030824cddd63",
        "Science_Teesside/Teaching_Packs/GROW/SOURCE_MANIFEST.json": "78b1d12b1b817c05a5743688a0946b855a8c211c954d7b29ba41575a2e2f7156",
        "Science_Teesside/Teaching_Packs/GROW/START_HERE.pdf": "93a7e61be570fa6934e93973b1a4f4eb200df3da24f83b8ba45ec64ccbf80375",
        "Science_Teesside/Teaching_Packs/GROW/START_HERE.txt": "856bddba97acc3d6389f09d99d3b0dc6224a4948b2be46c885bbaab7d9485c93",
        "Science_Teesside/Teaching_Packs/GROW/assets/made-by-matt-approved.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3A.zip": "2596818e45a67ea1b306f7c9287fa70795ab8142c6c93b9e63e1f99e1a4e5b22",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3B.zip": "4fedd9c4a162c3e712a327afd85554b19c55ad1f5b8cacea057b0fdecbb305ed",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W4A.zip": "789bc7f2048bba2eeed5dce137c93b1d03cb15841e88b7d7caff3202fb920aa5",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W4B.zip": "ae960df6ee5618ed8583c96399360734365285461cce3268cab20601ecf24750",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W5A.zip": "a45c2101629bee39c6637e7ea571be93e2947d0faad017f6a1878bf4cd19e3c7",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W5B.zip": "29d0aa2492db9d2dc9cfec2d73c1cb6fd8b00658202385f696c0703dc8d9fb03",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W6A.zip": "662b93aaafc83b0fc7766e620f934aaa01ad4f7bb9e7d9500264581e316dc588",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W6B.zip": "f394bfa9bd59fb66abf085b366bda1ba974835f74704aeba7db70cf249e20160",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W7A.zip": "d65c89a82992eec3bec05f855f29688f5d97258884b5affba043e1fb105c580a",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W7B.zip": "fa2e93d7e8832e5741390701bda0b9693a9868f68e3f442db15f8cc4c362691d",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week3.zip": "5a8606a41a4b9e5a7accdf3ee730d727b709d92734f669d07a1e84324fa8035b",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week4.zip": "df33780c2dea97c485158d026f8694051244d866663dde06ab8ac2ac14cd84e4",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week5.zip": "fa2c5bd9f4f509b52d1d2510afc8ae25e3f9bbce55fc3fe9eda438882f3663a9",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week6.zip": "6c0c4b0c76e3bf15c104748649c8d501e4ee3f669cf55fa280e3b73768aa6730",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week7.zip": "3fd530bcedb10162514f9d37b785f447c24e8a0ba8c82b4ea94a578b54e33784",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Weeks3-7_Teaching_Pack.zip": "d8b6f0ce61e7925089aadbc66b63756316268c9c2934575ccdf18e74cb41e6ce",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_Science_Autumn1_W3A_Friction.pdf": "0e57d93e45bf29236754a735e42f6d2ae923aa1a23c65ebe9ed19041347ced7d",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_Science_Autumn1_W3A_Friction.pptx": "13dceb4a32f65165df9353349a69c87465e7f33b9f941036f8f714fd10a9f9da",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Pupil.docx": "9f8afdf8df90eb845d3ea352d36b9bd19dd192a6c040883fe70957eb8be487de",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Pupil.pdf": "856691efece9acaae40a529f949f3d26567345c8f658de9e26eab1bbbdc585cb",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Teacher.docx": "9da8a692bd1ad6b4a040e4b4a970275c90577cbaf73342492d1908148c5d8717",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Teacher.pdf": "08c926202671c6b2c25778d5d2dcf2f99a473dd704201f0ef9a58e3a359b18f9",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3A/START_HERE.txt": "b5c46c92125be91cb86f64c5969ad8378ab3948b41a82e7be01e7378ccdfc81c",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test.pdf": "1ce1ba083eb62b521368b3c5863c098733ae7d677a1e7c0e641b8e0fd7681d3a",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test.pptx": "3049816d76009ebe3ad1b609e9ca22ec54c3abc82d3e8037b012386759ba278b",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Pupil.docx": "e4333309ef2e2dcf587385063c8e43eee56c3a285089b4f749580124d8c128ea",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Pupil.pdf": "7ddb70eb886f743fd0813b5d581435b36bdfb1a5813e23a6cb6f3b95ccdfee8b",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Teacher.docx": "c0e2ae5adaff89fa05b28e389f7d422e0f638ca9edd33313da61d57d258732cb",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Teacher.pdf": "c9c7bf0a6dc4b4a69c1df89bf7fc3a2fdd73c57828ecb0619688611b52a61d5d",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/GROW_W3B_Friction_Measurements.xlsx": "7ab6650a16051e655dde2f48928810cb2a825e07d4d0a028fea7cc25ee64b1d5",
        "Science_Teesside/Teaching_Packs/GROW/lessons/W3B/START_HERE.txt": "70a87773d7f0bc53b67cc1023263f2837ec473ceffc6ec1fc79b82823805c756",
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
        "Science_Teesside/Teaching_Packs/index.html": "4d9fc732a9b9d086b59881300a081a0f3fc2627bc8cd083b680fade75883caf8",
        "Science_Teesside/Teaching_Packs/packs.css": "70ca73b323e5cabf05b1f5f9f8107694cfcecf4ddf8043f342049ee4c797ce59",
        "tools/science_teaching_packs/BUILD_QA.json": "d5ee55a25c15ca86dbd6324b417c70d672e1d0c19a1fa6462f35cc620927a2ff",
        "tools/science_teaching_packs/BUILD_SOURCE_PROVENANCE.json": "bd3093b818cd94ab74260f28f2c8ae08e77fbac307e8dcd0cf2a77540e299197",
        "tools/science_teaching_packs/GROW_QA.json": "a8cdaa361414a3700c463ea40e0a159029db3fb803024e50b0eb39d082c6f364",
        "tools/science_teaching_packs/build_hub.py": "db1a706f68c8b33cdbcfc4c6f197781fb5cde2f3fe53dc979eea5c5b592ade10",
        "tools/science_teaching_packs/check_packs.py": "01609d0d19e3e4a5de810725d68ac97fcfa0f8843d626dc5a7aaddca009aa578",
        "Humanities_Teesside/Teaching_Packs/HUM_00_SoW_and_Order/Humanities_SOW_Alignment.xlsx": "537350c7f0ba110ea90edf5039826c1a2858c04c54ec006c550ff143c09dec69",
        "Humanities_Teesside/Teaching_Packs/HUM_00_SoW_and_Order/Humanities_Scheme_of_Work_2026-27.docx": "b078d01fb53a9f5d828b7f64d9ddb9d1a36daa681e8829d2a6d811abca664d11",
        "Humanities_Teesside/Teaching_Packs/HUM_00_SoW_and_Order/Humanities_Scheme_of_Work_2026-27.html": "ac8f8d0a4188d147097a491b0db59efef16feb0c0f6c4fa8e13144bb8a53f69f",
        "Humanities_Teesside/Teaching_Packs/HUM_00_SoW_and_Order/ORDER_HUM-D5.md": "688b3f5dcc60f6c0cd9c68e2cb2cb7c756ab834e9956c4b20b37982f749c88d4",
        "Humanities_Teesside/Teaching_Packs/HUM_00_SoW_and_Order/RE_SOW_Alignment.xlsx": "b1ce56c551520fb360ea06e68c59c1642556337474526c38fb539a36296c2aa8",
        "Humanities_Teesside/Teaching_Packs/HUM_00_SoW_and_Order/RE_Scheme_of_Work_Autumn_2026.docx": "3c2fe9ef4e4cd27361d76c4bb07234d4fe5eed8be40bcdbf1d1133b4632dd9a7",
        "Humanities_Teesside/Teaching_Packs/HUM_00_SoW_and_Order/RE_Scheme_of_Work_Autumn_2026.html": "5a1b523738c7a9e21c7ab2a713970423b5bc4343595432ee315bb5999932e992",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Captioned_Model.mp4": "8fa5f6ba3f6b7210d48a37277125eba44ff69843e7f6875177e6bc28eb6747bd",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Editable_Pack.docx": "ba4218c0c930bdad13c95b796c7279bc26f713d78a412349e5d47f6724cd5ecb",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Editable_Slides.pptx": "cfda24ab774a2a5c2a742afdef594663ce9a854aa8a12694fd0ff6db6326b987",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Knowledge_Organiser.html": "3e66b84d17cb11b3d7c7b315ef734d88c4edb94a94125e2707a16addbb2dc3db",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Knowledge_Organiser.pdf": "868102f22dd543cce610053626095a530320d26b88ea5e116e151cb3cef5dc28",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Lesson.html": "1192868212189362ad1850b7d3589c01457694f1c94e304a16245e09ae83ae83",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Pupil_Resources.pdf": "29a00cfb5f9bec7af9c6bc891cb7245207f3a35ab261e47005530c4094c4c2a8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Teacher_Notes.pdf": "37cf73d652b204e486350e7b65081175c8f463a04b4818640e7eb2e165442269",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Captioned_Model.mp4": "77173af6f427694cde81390ea21a8f1dba343a229c807a44009c87f93e5766b8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Editable_Pack.docx": "91b3470b41b0a61f596d8abcde9a16cb5c1ece605bbbc34da64992ccaef0965e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Editable_Slides.pptx": "c6bd63b7fdbc4ce2f83cc6ba78cf7848eeec0de3909f72bdbf9d94594bcf182d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Knowledge_Organiser.html": "3b38e793985423f62c24448edee7ac73d6f0a98f14b874e28c1725abd64445c2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Knowledge_Organiser.pdf": "a630484d37fc1d0c28e81f0c25868b52327db50c9c6de1e76debda7e5ca116a4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Lesson.html": "7412243f8449c42fa7027ca612b0af6c643d5fc0e9ca627b29495e597220c0e1",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Pupil_Resources.pdf": "3b4fe4f602a55759285a98f6f1e2d45d2d46f67215504ceb55a923d3bcbcfb32",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Teacher_Notes.pdf": "a82945dc967a871fc564d1672060dd0f281de51c41187b81117370894f662909",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Captioned_Model.mp4": "6799b383452024ffcf72332567d694ba979b6423141ce4b822aa3c3ea8ee63b2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Editable_Pack.docx": "c2417f48f62cc82e1a455133168f31b4d8534a9b4f6a5066248943775b0d2eb7",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Editable_Slides.pptx": "de5a8a7af83b5c3010f41aad4d8d6216c572541e21cab8ba335d410e34081210",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Knowledge_Organiser.html": "ecbdf5a09d9680fb4a038d1be68d65646113642c37df6a9159eff7ece3ba69d4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Knowledge_Organiser.pdf": "fb3a1002abc247a97de4ddebe31957e628da05dcacfc691a6c02b32e152c2ee3",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Lesson.html": "5e53738ef888c7600138cd1da2658aee40be5119076879e72c9c2017dca8ebe8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Pupil_Resources.pdf": "c4e0b931a96350ea576d7558660347300103edd8f9470e8cbb8147abeb95bddd",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Teacher_Notes.pdf": "357c0c42f9bb9b1d7d3174b991adefea2bf7251e9d6c047e65fcead5e52a2e17",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Captioned_Model.mp4": "44ec3f4cf67a570d39f8dd10e0c221b60043c64e5ff9f8c703f73c899fa26c7f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Editable_Pack.docx": "3cba20163d155b254250d5d04e561b7ab97ee1e0e62a7203ae03f74ec57fe07e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Editable_Slides.pptx": "134e89022083818a9b01dcd3b117146b7c8fa955a4da049944abb00f9ab2a7c9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Knowledge_Organiser.html": "66d4d4779b40c56879219034901ba86a72635c76beee76e4c207d3d57829cf2c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Knowledge_Organiser.pdf": "482acde5fbfe07c7320ba7c797146a9e2df43835206a3109e52f1dc9d6f38aaa",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Lesson.html": "90e2c3a51ed1d8217d1ad40951bea2250a81902590b048889f336e2ea7848696",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Pupil_Resources.pdf": "06e25f3305baa497f8e390a15c8a774c9924ed6008692989c00f8c9f96d9a0c4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Teacher_Notes.pdf": "e4679530a054a5c59f2ab9e4c69a8a7f4ec2150e0f859f61522278dc6dde0dbf",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Captioned_Model.mp4": "6e49af80f4a65eb96e7d44b3124a8623399746d06de9e553ba1d6ac1820964bd",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Editable_Pack.docx": "6e5062cfe442d1c1393305aeb97ca8cd9997b5b32a94cf53957cbb46b5f5d5de",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Editable_Slides.pptx": "2d7a311e7f7cc48154932ab3abc264be9c85a883784be06144c4815fad4e4eb4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Knowledge_Organiser.html": "9302b4e790b814bfdb39beba6365b21fdbcb301326407c5233f90d0dfe792687",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Knowledge_Organiser.pdf": "711154c45a697db045eba0bdb1128dca890c14294c6fdde6f93c6ca2455a5781",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Lesson.html": "e8ff62a224f4b583679841208493a6b3d04b1dad3bf4a588b2b8ae619f6040be",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Pupil_Resources.pdf": "e1714a396234df106f1d9a60863782eca89f778fbc9f5a3c2a3fadf82412525d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Teacher_Notes.pdf": "db8a527ee6733276cfa13be6707bdf7fd51683bbbb308316cc6a17bb85fc04f4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Captioned_Model.mp4": "729b94fed48c24c1d5782de86f959d2c36b8a242607a28f6527c3e422f6b633d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Editable_Pack.docx": "c3e667ea40e836ca2348167405f2cbe77573aa67c7ae278d1983284426451204",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Editable_Slides.pptx": "e3d9ced1eb206eaa6f4e4f3a140b94b892232398e6e36f8e8496a7a263da19c6",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Knowledge_Organiser.html": "5aa307e49336ebae2446d4090a28b87467f840aaa49bbe4c410dc280585cee1f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Knowledge_Organiser.pdf": "5603b0397bad083b453bf7394d6684e27e7706f0591cd9fd0f1179252507456e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Lesson.html": "39b08813df37c6012cac3c2b8818e9f5d5a08869f3a485617dfc5a77d936b5b8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Pupil_Resources.pdf": "35c2f9bedd818e4cf1c8b84d9e4f0c51951dacf2e7de3a9c4b4186d381cb2091",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Teacher_Notes.pdf": "2e331beb3ad1e67d69e308c2df71ddce6ff3894e34a3a4933b80bd9e6b4f6473",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Captioned_Model.mp4": "f061462dea7135392eb4391312f9714d66c9a3198cabb7e5c321d3363df45309",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Editable_Pack.docx": "55a0f12a9595c1cf0612533bda9290b9031121ee2b11742c6354612730f6320a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Editable_Slides.pptx": "5f24d03d2b3e0823255d066a643852e009ca98fc4f34f984844c97a4df3ffe41",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Knowledge_Organiser.html": "b3b5d61e5bacbb1669a0d2c2c6956a04874f162bb4d8ab94a236dcbcc15c099b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Knowledge_Organiser.pdf": "db0bec4a5997afe173847d60aa5daccfa4814b2b61a7a6cbb5709bd980fe11a6",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Lesson.html": "27d00134171b8a54f668a86dd437a11fee024695919a98cbf8cebcb3b534cd3a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Pupil_Resources.pdf": "7f429dd60fe3f4929451c3252ce4c4b93290269d3e65681297762c1e47b00fd6",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Teacher_Notes.pdf": "1528c4085a6a61470847fc7a9727ac41a322c6ce9638c39ac18326b0748dbf89",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/READ_ME.txt": "c6db9ea733f5a67a6f32d702dc54963f97d3c8e430f310cdbacb47c5440d4e07",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/arrival-change.svg": "c98d1fa61e8163d08305382a36516b63b3f3de65440e068ca491f92d8a169cc8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/arrival-community.svg": "1de816a4040c040a8ec5c392b32035528497217d1a9f98e312930ea02a765d68",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/arrival-diversity.svg": "8c3b9c5a0600994a9352b2181952d9ab92c75b9e398e6845a97e1944cf18043a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/arrival-fairness.svg": "529e890159203a9483e9c044181e331554e27a9a65106cb78c3e644bbb75a8c4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/arrival-festival.svg": "1e1bb8c407d767b99f02cfb4e3cba2577938252c83e649639590d95875c01fca",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/arrival-peace.svg": "792b8cd954eb3b23bae480d4db84519e5c5a2b506442c3772cb90416ad4a8ae7",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/grid.svg": "be3436cb4c1b0fa7993e214c47407186a74ed353c4fe727069afaeee572d9bb8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/local.svg": "e666bc5070d66bbb2b564685a768421508764e67b28dcce67b6be40cf0ba5e2e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/objects.svg": "88aca060c6685e20fd47a6740f32c3012a15c48b12dc6bad91867ae040267eae",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/phones.svg": "ff17e352efd169723a534fe0a4c6846d716604929b506bb8afd0ffda0724928a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/world-climate.svg": "c7eb4516343528f9851ab39a89c04abf8b26b260b85706314c567895ce2a7ad3",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/world.svg": "26fc4e5b254e2611c6de7db61635e5da69beb764ff861655a1b7a682774079dc",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Captioned_Model.mp4": "27e372fb76c393618ad50c7646297a5de2634cf380b46008aaee24e1e7329b5c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Editable_Pack.docx": "5ec25185c0ee34a51fed7578a22710382f729df4252044b243742d30b420f5a8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Editable_Slides.pptx": "d21c1563074ca9e572bc8cdf9ca2b6605a5bcfefbaf3365ecff395c37287ef41",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Knowledge_Organiser.html": "40439b73feafd73e9fdb302f8c387a37943e6309a9061ac91a0e2819e0602668",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Knowledge_Organiser.pdf": "1eed83e326a7e7ed83b9c1cbe4c4a937cef65184d5a23d95112f82e9ad1f0707",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Lesson.html": "36dcb892dcf165e2e1b19d9c89f237bac0b27edb11226d57a12102d40762261a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Pupil_Resources.pdf": "0b022e28a1ba0ca0300d3e49200efe20f795d3e0deea37e1719d46329df27b38",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Teacher_Notes.pdf": "b56e65d0d91b9f5a71e6ee4437ba9a55648e6de5207ab0cab245080c6b6fa1c8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Captioned_Model.mp4": "4e5fe08cdb62a84699773e85af089dbf0a82f20f09a695f3dba0dfc9e8f6d686",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Editable_Pack.docx": "3f7bd38532af9728ef28cbd469dbb654490e19cfcd797557665a8557f915da7c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Editable_Slides.pptx": "718df0564cc04f829be3cf940f7c594d8e7653fde687acf6f4ad6649840a35b4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Knowledge_Organiser.html": "9a480ac49e3b70537513f25994506bd53109ffa3a1af2ef436d33f0634ce46e4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Knowledge_Organiser.pdf": "d12ec8182576ba80e6e8babf1d8f9294fcfad890030a1180bd585d13f9f034a7",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Lesson.html": "f6fcd4c4a3f72ddc447d025e13b92c28a27bf038084783234268c67d7020dfe8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Pupil_Resources.pdf": "2b8d25a9b90bc688a30cee4a436fae9da5acadc6ea5be0e08208c17c61a34233",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Teacher_Notes.pdf": "bc604fa8fdf64afc8d5171b5f6399052448ee019854c9a9c3f31499c09f82190",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Captioned_Model.mp4": "a01cec3a4122abf6d5a1538c4a045c9edd705cc71fdc61792136d1a0cb7eb9cc",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Editable_Pack.docx": "9698bd7c5259b45f52b91b0da0201ec42f68cdeef088e95ecd36d3df024709b5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Editable_Slides.pptx": "1004155fc1fe26181287f11b2d7256e54cf8c9146a9194dfe167d374998f980a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Knowledge_Organiser.html": "f0562ccdc634da0a73a0103d80cef7980f68cd2e03443630f23f2717e1a200ec",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Knowledge_Organiser.pdf": "5bea657e4fc355189eab0117af54fa94667cf1fb285c902719ece4dfbb136c32",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Lesson.html": "8ac77bdd965bad5c3f96ed166234891a77a2efb57a38eca2dccd4c33912ed399",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Pupil_Resources.pdf": "74b89a85ae290c7a92aaa294b63cc11d95ad910104736514f0b5e1d0ed06e478",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Teacher_Notes.pdf": "ca45b2898bbdbf042eb133888c55024f773f45d6ab8eac0776e3b9fd7f811853",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Captioned_Model.mp4": "f8508413835f4f6b7da9560df5a34be4576fd28103321fa87dde8e02548f24b8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Editable_Pack.docx": "8e59d4a336e345822969c7d278507d0b87d82258f19a2f0e8d0cb69b245d2cc9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Editable_Slides.pptx": "f91ce4ef835e9d92a9568a4f461c4bf0488eb79c9eedd01530da603c731d3f9d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Knowledge_Organiser.html": "5e07a502976e39e47f86b48d32a83c578670c2da5f4096571d1931f97f03fd08",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Knowledge_Organiser.pdf": "756a7d988c9b4557214e294ebfe609350faa3574b608b8e1acf54406a89cce60",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Lesson.html": "77d20bda14edddbc47b9c6218ebfa7fa55a6c4917c934d8b45008a78100d2c13",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Pupil_Resources.pdf": "dc0063c6a349deb1e5fdf7334212d3fbbc7599947f5c6df7cc5b5820c1f3aaf1",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Teacher_Notes.pdf": "484edbedd4f36b652e9edbb678392653226c76dcf7ad33d8d6e2cb3fa782c617",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Captioned_Model.mp4": "d7901902a1df8f0427406ef698a7fc00080139c11f866935cba3b323d8e2f4e7",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Editable_Pack.docx": "43deca2b5d9cb14440ef2766e061f3e290ffc73771ba31e551afc5305a30f71f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Editable_Slides.pptx": "563437d8138ef940fd094ea27502eab86ec37223e5bfa418b79c806b1e6ac4b8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Knowledge_Organiser.html": "0048c8d0598c8eacdab502d66b52aea2d2e8ba8b9608ad020cb88e3c8047bea3",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Knowledge_Organiser.pdf": "54c070b18901980996718efa64cf0a26a638cf68bc9008d58bedf76d805b4fe3",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Lesson.html": "65358dad991b44d2b58a6b6578511e6f08ce4ea937fa1628023f210c58225e14",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Pupil_Resources.pdf": "1629c9c31a3fdc5fb126a6f5b2d6a0a6503a358ae73ac5a426e978eb048eb0aa",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Teacher_Notes.pdf": "ad9fc3e249146af8f50a2dd68680aa097b7e50be02f5aa62d036e01e467dd6dd",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Captioned_Model.mp4": "48d1104447ee11372b61673d71ba3057d4495c125c0f9b54411f0e729fcec5f2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Editable_Pack.docx": "21eee128ab8ecc639e32f0d068c1cd5ebf532d11c80ed0a10aa1414e0cf76bbe",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Editable_Slides.pptx": "eada084af4c4f1c5e337f1121487d10165a13802a2f4465f5d4c06978f722d92",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Knowledge_Organiser.html": "3ca5600ac5639520240bb60edc07715d7157b132056173dc971d829cc629d52b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Knowledge_Organiser.pdf": "bed02b4dc5cc31134965d6ae14f33463ce27f98820789306f266333b726cf5d8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Lesson.html": "8cb0d5d70f526707e41d5960ce635d692e5eb067519231d3a59e4ae2d278beba",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Pupil_Resources.pdf": "05a3df175825afcbee8c0d2b0b930f73202ed48cfa85e2cf446926879e890231",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Teacher_Notes.pdf": "6cd6af07cc07ec35202709612498fd108441519f91fac5459294e7468c3dbfec",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Captioned_Model.mp4": "1bca4e415328a017f3494bf4d4b7db779544b01173cc07e07562bd5d19b34464",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Editable_Pack.docx": "55518db545be873b113a766f5f2184b3d75e8f092e2533d7c6e4c980c3c26965",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Editable_Slides.pptx": "d852d22e6cc2788dca4d284b4bd31122cb60f1d6eccb382014746da0fb1add60",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Knowledge_Organiser.html": "decc5a8f6a0710d77bf59a9f545e207a29caa1f87442af93b6299656c2d6787d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Knowledge_Organiser.pdf": "a15d9bc8ef7b7b8e3c144df48337926e3d3965b4a15d70d0055ef15777d41a17",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Lesson.html": "7cff5a297697b90feb5c9596ed4ca7b96cae95a9001bf373c50df1fd16d5d523",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Pupil_Resources.pdf": "95731f0c7778302038af6829e4f4f843fa33d9093fbd78cc09b1a24b6e316e7d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Teacher_Notes.pdf": "c0c7129f507d9ae462fdde108823ade704edb5d435c4c1919d408843647d1380",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/MANIFEST.json": "b693855bc779e604c9a2851cd2fb564cad071d4dce45eb6438350fa1c141aef1",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/READ_ME_FALLBACK.txt": "be8efb425b2248d5b755d816383d8854e0fed26d99b108bbf898b5f68d96695b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/SHA256SUMS.txt": "9f9e515d8f2eb725c27af7e6064c0bf317ac86e0278944cbc19394acc5ae75f0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/SHA256SUMS.txt": "b7a6bc6e2a2a92e17cc0f6f1a48bcdd45b98f70ffbd572300f3aefe060eacff2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/SHA256SUMS.txt": "340c594f5b4340d257b5db6b0fc86d0822da04623ce275f564313bc72aa1ce3c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/SHA256SUMS.txt": "3c1f9b61b106d0d77d28999450e7fdc8375de0ecbfd51964fca25d20089bb5e3",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/SHA256SUMS.txt": "96587db7912c6d7a7248bafa8d21bb976b15a8eb0664711e8ed45b2062df7f91",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/SHA256SUMS.txt": "a4545d2ffa724f7c49a83d93ac62446b2b65cf150657ab6b3b45d4f846b51050",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/SHA256SUMS.txt": "01f5fa20dd3443c163bb5110e92a9ef65423296401b91d5dd5794382a1c86868",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/SHA256SUMS.txt": "1e780dcd5706ac2551fe8891ec14febac9d05c53febe8da9f8c142f41b7d1d08",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/SHA256SUMS.txt": "2e9a134f88dbddd5306114c2f8bec94c631afb870207461f9a1c06ece292fe00",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/SHA256SUMS.txt": "5ae18b9063c67265a8d67a8b9461cd5c9deeb48f89c318893eca92b0006112e8",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/SHA256SUMS.txt": "b2de4b668a22d789c015d63198685a286364e89970ca8e7ce295bc95e94f1d2d",
        ".github/workflows/cross-estate-on-content.yml": "1da236d50f2013b5d03e06d85d73018d56380936e2c490eacf17862c93b15364",
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
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3-W7_DOCX_Collection.zip": "2482706e4f9c7e192287acfd02e7c09381597a1a9fc772c9d39fe630eba5a3aa",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3-W7_PDF_Collection.zip": "b3116412bb38368b96c0236e2b41902deb76e96461f1ca1c3fb134d878f842f0",
        "Science_Teesside/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3-W7_PPTX_Collection.zip": "592f59c2ccae4f9531af5296eb30064c8fee92c44ba2b896db8038cf2a93dce8",
        "Science_Teesside/Teaching_Packs/LAUNCH/DOWNLOAD_INDEX.json": "431b8d5b10c4b037d09553a5f6818681c4a2f56fbf7beed4dbcd687bdefe90fc",
        "Science_Teesside/Teaching_Packs/LAUNCH/Pupil_Worksheets.pdf": "40b4561e417afebf2cae6a5eae1ade45859a9dd462bf69e8dd4135c836d3f7bc",
        "Science_Teesside/Teaching_Packs/LAUNCH/SOURCE_MANIFEST.json": "3ec0db25c3deb4839106d59bb03361e05d103e7347a6f2939ff3f4cbb9de7655",
        "Science_Teesside/Teaching_Packs/LAUNCH/START_HERE.txt": "2b7b55ab005abea12229d54ef4f8f5389cd6c0714078284537844e62b69ac3e0",
        "Science_Teesside/Teaching_Packs/LAUNCH/Teacher_Guide_And_Answers.docx": "407a1c8c72112dded2dc9c89d3a73c6b5834cabcb743d8bd6f436c412ef1656e",
        "Science_Teesside/Teaching_Packs/LAUNCH/Teacher_Guide_And_Answers.pdf": "f359887eabd99b868f1741b65ddc0a16b0eb2d5909d127f166926aa877657fb2",
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
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L1_Diffusion.pdf": "0641dbde7d35b8d98332c864eb419b7f0d18610b79e96c2439c5cd741803f6ec",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L1_Diffusion.pptx": "a61a92cb908959617c5e62440bdf18c8fce41a5a5c91eb348086d4fc687b32fe",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L1_Worksheet.docx": "587d0c554d8f496b13bfa4f35cd91e4fc6e5e9618059b73cf2a5a9131e2ada75",
        "Science_Teesside/Teaching_Packs/LAUNCH/Week_4/W4L1_Worksheet.pdf": "9ce702ccc29bfb3eecf02e6f73df2de5cb96a6e695962e79fb49c8ea90ce414e",
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
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3-W7_Complete_Pack.zip": "a1194521ca6943909d8cb73c61dbf6d6bd5e1a5bd704d640ef7dd9f8b3df0e7e",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3-W7_DOCX_Collection.zip": "638527b335f4062db3da9d6172da4ec9993ea007d3e4dc8a507d122f2e358baa",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3-W7_PDF_Collection.zip": "8a0d4e26223491be1998e21fe25995bf50bd807d5ba3fce6eb73aa657b8771d7",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3-W7_PPTX_Collection.zip": "6d410f6066f65c30550717b1180bd2b7410767ee62e13406927d1b8d41107bc9",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3L1_Lesson_Pack.zip": "a72792b9c2b10eb660850f17765b6b723f68ff8cc95e6be1f830ba64232803e3",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3L2_Lesson_Pack.zip": "0e6d454ab2437aa39b8d1c8409c6300822d87df038fba3e168d1d51fb122f446",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3L3_Lesson_Pack.zip": "2c10aca9832f12889edfd8923f80c8660596d67fe1e81b4ee40122f2c4ff66e4",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3_Teaching_Pack.zip": "8e6c80015fc3c45585ebb7add1cb99dfeed48c4daccd05dc0d96486719e97abb",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W4L1_Lesson_Pack.zip": "5f0985a04ccfdbcbaebc6d31773a04caa55ea9ba8b3b7caefd6c01f4929f5d76",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W4L2_Lesson_Pack.zip": "a426dc9b51d4345db06a6ec9681bee9a51591950416b4d4c823715eaf2515ec7",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W4L3_Lesson_Pack.zip": "74caa4b61be0c043de6312d0a9abbb688356c8826073f7793cab82a70cbde62a",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W4_Teaching_Pack.zip": "eb29b571f83605f35ca8f287acbd30498e595c86a99e69a0c7101dd804f8ca6d",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W5L1_Lesson_Pack.zip": "ae830ca4d6d07af91c80e406416665014dcecc86c9e27d5c8ffcade94d3522aa",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W5L2_Lesson_Pack.zip": "ac6a50b5f79420d90545cc07b43eddb1caa0085f7eea966f958de80b2523f0da",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W5L3_Lesson_Pack.zip": "4f632511bc0565ae70452d117ec6181b1bff401607464293af1ac17ba9cae014",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W5_Teaching_Pack.zip": "798f62805181e146d2e65bd19cb2a497154745d948b1fa1168b614def7b9d8ae",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W6L1_Lesson_Pack.zip": "5590e2f273994a9f3003d80dbe41f0e18e1b6a186767ce514a2806f3345ca26b",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W6L2_Lesson_Pack.zip": "a1d47be6ae8f026788ca6106b63aa03242561f7ca4e0b19f91e7cab2af510648",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W6L3_Lesson_Pack.zip": "87bc34837a81123d3b992d1b366ad00236ac0d4e23fe2da0f434e79aafa814fc",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W6_Teaching_Pack.zip": "e86f79ae921379d4e91418f520be95fa45daf94eb4f60b00502f786c82451128",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W7L1_Lesson_Pack.zip": "338c05412e504ac6a1c1ca9e7f31e93a00ca3b7bc163b4f9a2da497d12749908",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W7L2_Lesson_Pack.zip": "64f412f903d741cdee73025a8f0c852ee68efb8fad6de7a04ad54a9b69479f66",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W7L3_Lesson_Pack.zip": "b5c3cd9041ad61a754d0f8896d52e1c2bf580f1ca60c876aa845798e16bfdc3e",
        "Science_Teesside/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W7_Teaching_Pack.zip": "509df11b11bca9e59f8a74a53bc149edf64caa02110074b6d1f654ca3dae74fb",
        "tools/science_teaching_packs/refresh_packs.py": "ce14bfa3c503bde2a5e0a8a07effbfe52d6c7262894cf062dcad358c473e7d47",
        "Science_Teesside/Teaching_Packs/GROW/Image_Credits.docx": "b7fe4b107695458bd8138170b0c98d14adddfe156871bd228db798790dbf3786",
        "Science_Teesside/Teaching_Packs/GROW/Image_Credits.pdf": "651dcd9f749c6cfb5ffccd73eb9ffb14a57f8ff8a8860f348969b34114396f86",
        "tools/science_teaching_packs/check_hub_browser.cjs": "cf95cd468472495950f24a3dd0b1f4b9794f0a7df251ca7ab0c4e3098a276ad8",
        "tools/science_teaching_packs/VISUAL_REFRESH_QA.json": "3ce5b90abaf89fc5a2a4085791bb16e09667545cf489a985c1c525bd7698fc80",
        ".github/workflows/science-teaching-packs.yml": "385c2cff9f8ba709070380d0f6dbd11af89b72f9b5e847e68bf4264287927c88",
        "tools/stale_evidence_sweep.mjs": "17813c59e3752fb9843374a302895d0d4710fb2c749d29af81a77873ff9d3677",
        "Science_Teesside/Build/W8-W13_2026-27/SCI_B_W8A_Sugar_Labels_Explore.html": "74d17d4e0f6873f094691daa753539f8a351887160beea6a8a8d727bba864d2d",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W8A/BUILD_Science_Autumn1_W8A_Sugar_Evidence_Read_The_Label.pdf": "fc9ba726c94177000d872c28e3c7db3812c268d6552e936a316c38654a95a0dd",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W8A/BUILD_Science_Autumn1_W8A_Sugar_Evidence_Read_The_Label.pptx": "d93b814710bcf57ece951ba0aaf82ed41320247571ec48147e26a5423b3c07e3",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W8A/BUILD_Science_Autumn1_W8A_Sugar_Evidence_Read_The_Label_Pupil.docx": "be71bc9be6c6d9c23383ee35ec739df80830ad5e336e7095098deaf3003a6d64",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W8A/BUILD_Science_Autumn1_W8A_Sugar_Evidence_Read_The_Label_Pupil.pdf": "25544b193963f552a1511ac17bd5b5353cbeeca71d6788ac4deddbc61f905dc4",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W8A/BUILD_Science_Autumn1_W8A_Sugar_Evidence_Read_The_Label_Teacher.docx": "7932493b683f1ac4ab7fbaabef8f55ec13e0db311dc63334788dc88e9fc5d099",
        "Science_Teesside/Teaching_Packs/BUILD/lessons/W8A/BUILD_Science_Autumn1_W8A_Sugar_Evidence_Read_The_Label_Teacher.pdf": "8c9984c7683196b03a8acdf90764d7136f390f4fb0e28211077eb4184311f5a5",
        "tools/downloads/offline_pack_browser.cjs": "017782ecf949ee7c3030c4f872c2c532e0178ccb03cc39c8c636acf257623a95",
        "tools/downloads/prepare_pack_browser.py": "b5e8cee27b6bbce9d86764712b71785942efcfdd9f4c46139da541727340f46f",
        "tools/downloads/test_download_pack.py": "1fd8ed1c791ab7ac60227ea10929f5ff13966d151c807c15192427bdd9ba0f2e",
        "tools/science_teaching_packs/check_build_sugar_browser.cjs": "1c89ea763fdbeedba36bc497db6ef9bcdacf807ee74b01f008e6981b6c339c29",
        "tools/science_teaching_packs/check_build_sugar_pdfs.py": "62f8d1d1989be600374fdae1dbda9c7ebf407711cfb572123a3f9c31c4442a03",
        "Science_Teesside/Teaching_Packs/web-slides.html": "f31f09d03f5d8c417af1745b38309fa537afb8bb4c6a08f387db3349d9e1cba2",
        "Science_Teesside/Grow/SCI_G_W3_Friction.html": "508f1967b6481671dafb149d7177b620b194074312cee0dbdd30553c166b634a",
        "Science_Teesside/Grow/resources/GS_W3A.html": "e5bfaf2bc70912aeb59fe9a2eb1032d86c7a473a1059ba782fee1be7b3513dc1",
        "Science_Teesside/Grow/resources/GS_W3B.html": "fb6580bfd1e02d82627d60e1c2e08c3a34b227d0cbe760545502a8e51ab91208",
        "Science_Teesside/Teaching_Packs/GROW/SHA256SUMS.txt": "758dcbdd646219106ef7c416034c24e5e89da1423df5393621eef985e0c4a3a1",
        "tools/easter/SCIENCE_ORIGINAL_TARGETS.json": "9cf2665095691e047d7b7645ee171bbef8c48deaa19647aa401e1b408b9e45bc",
        "tools/grow_resources/CONTENT.json": "8b51f89b02b50ddb2ff409bd0959c730b1d28f25a1ffdd264a21d3fba17c7677",
        "tools/grow_resources/BROWSER_TARGETS.json": "a223e070f70b979809c2bbc8325d505af3217bf633ecb3cec3bc63b954e876c4",
        "Science_Teesside/Launch/SCI_L_W4_L1_Diffusion.html": "563e0bddc7049afb1dfc7245b1810da5094c19bca8027a08bbaf4c26d5a0dc54",
        "Science_Teesside/Teaching_Packs/LAUNCH/SHA256SUMS.txt": "cbb0aa2c07320596ce8118df19526c158e952a7c6b730fcd4492dc57b7052586",
        "Science_Teesside/Teaching_Packs/BUILD/SHA256SUMS.txt": "316444eaaa55fd786c393a40443f511b450c0f04a5ba1f752cef125fd254be01",
        "Science_Teesside/Build/W8-W13_2026-27/SCI_B_W8B_Autumn_Science_Checkpoint_Do.html": "7b27a0d82cd7df671c6a3b52b46d5d620ed678c332cdc58d1c649c3b29dacbac",
        "Science_Teesside/Grow/W8-W13_2026-27/SCI_G_W8A_Day_And_Night_Explore.html": "2560984b05d13f2e998c7ae00cabf414b313821b836d6d68299774da55db8928",
        "Science_Teesside/Grow/W8-W13_2026-27/SCI_G_W8B_Day_And_Night_Do.html": "97ef11162a1c36b1df421d0f85ab32be6139bfbd47ee36314426020a1162a32b",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W8L1_Enzyme_Action_Introduce.html": "1e46f94da927f5bbf190c067ea84b16cd60d0112c6381bd17de07c774fabd346",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W8L2_Amylase_pH_Core_Practical_Explore.html": "d69088d64598a8f230603a9af232f3055dab3796330e30c19566dd087f5f52f6",
        "Science_Teesside/Launch/W8-W13_2026-27/SCI_L_W8L3_Amylase_Rate_And_Topic_1_Do.html": "81e67475c5a727e1fae1806504b56a0f49b15f9573be563cb6c55cc4e381dfda",
        "LundyLoop/1_whole_school/Day_to_Day_Desk_Sheet.html": "170fdded4a26dd7fa92992fa99cf109038c71ffa7d89184f0a2dcb45e20395c8",
        "LundyLoop/1_whole_school/Whole_School_Reference_v2.html": "d2668c89e218192f87137a77d270e04d4cdce1d36c373fe6767bc50b86efe2af",
        "LundyLoop/2_leadership/Impact_Framework.html": "84bcad36767fd69b9b3afa5912b1b27faa20fc80c30d0bc7cf5596c64de5e773",
        "LundyLoop/2_leadership/Impact_Monitoring_Crib.html": "dd6d9bfe1453eddbeefa93aa95aeddcc3981b657223918a23183551b41f9550e",
        "LundyLoop/2_leadership/Ofsted_LAUNCH_Loop_Sheet.html": "c2a081cb5cba2f977099a43b11236c852601842d898bf8579aed9c7f62594cff",
        "LundyLoop/3_subject_guides/science.html": "2945a7783ecc44966bcd62fdfd76aac410f78620cc2795bc97f058efb3ea70b7",
        "Science_Teesside/Grow/v3_40min/LUNDY_DAILY_REFLECTION_EVIDENCE_WINDOW.html": "5145899e4c822dbecaf1a98fbc2211db63ac48ad42c9af469c6f8f77eac8dfe4",
        "Science_Teesside/Grow/v3_40min/SCI_G_W3B_Friction_Do.html": "97aed0e499bb85d11d2aefc822c9bd8c4c856281813ec7bbc04cd8d1f86a7c24",
        "Science_Teesside/Grow/v3_40min/SCI_G_W4A_Mechanisms_Explore.html": "fd28d3366804e5a50cf1c93f0d831841e31f005b783179b170cc67527c391d8f",
        "Science_Teesside/Grow/v3_40min/SCI_G_W4B_Mechanisms_Do.html": "7f186cec059e51af8d68c19bf8854f000cecdf63d4f12b187214905eafb5692a",
        "Science_Teesside/Grow/v3_40min/SCI_G_W5A_Fair_Test_Explore.html": "cf7c715478fad8e29cbe1a42c3d5e7819465589fda764989256fbf47d9132bfc",
        "Science_Teesside/Grow/v3_40min/SCI_G_W5B_Fair_Test_Do.html": "a404195e8d314ba7f40e6dd54d37a02946f5c08482054d416143fb1b11d1a7a4",
        "Science_Teesside/Grow/v3_40min/SCI_G_W6A_Earth_And_Planets_Explore.html": "ebfa441095f114e2fdb427ccd9ee24860e17ad12ba55d2de77525768997a4869",
        "Science_Teesside/Grow/v3_40min/SCI_G_W6B_Earth_And_Planets_Do.html": "91ae4a3586aff866541f5b1809b423cadcdf3321f664b29fce53defc4a6ce1ae",
        "Science_Teesside/Grow/v3_40min/SCI_G_W7A_The_Moon_Explore.html": "2b54a5399c6422873be70b5ab43ea271112f54ae1401d990705b19a2f75030b4",
        "Science_Teesside/Grow/v3_40min/SCI_G_W7B_The_Moon_Do.html": "85c9c9c7d4a12fa67fe6a098960aef0e880a3b7bf217667e39dad570bac11ebc",
        "Science_Teesside/Build/W8-W13_2026-27/SHA256SUMS.txt": "e00a7819a77039be3ab614ba92de09889748723aa9ad759f7a6bfe64c2e5fb28",
        "data/chassis-census.json": "c0ce60b67c570e42d1228e1071fdd123829ab7285e5667041589125b99b52e62",
        "tools/downloads/definitions/launch-science-aut1-main.json": "d63aad66e4c5522cb34076584c64c30e1708ede39f0c9267aff5193c2844cdd5",
        "tools/launch_resources/lesson_acceptance.py": "bbebaeb821f32c04eb1b2e01e819795ffa97cd851f33d7c22fec0b0505a9fe21"
    }
}
# END REVIEWED CATALOGUE PINS

# These semantic pins are deliberately outside the movable file/manifest block.
# Neither the catalogue pin tool nor the generic manifest pin tool can bless
# an edited, deleted or reordered original resource, or an extra lesson row.
CATALOGUE_ORIGINAL_ROWS = 734
CATALOGUE_ORIGINAL_ROWS_SHA256 = "b8ffcb16f5fd2a413e8a0b06ad2d4b112f450364fa294377869dc32c8235bb2c"
# The appended rows are the 49 reviewed hub rows followed, since UX2 D3
# (2026-09-08), by the companion-pack entries DERIVED from
# data/companion-packs.json by tools/ux2/companion_catalogue.py. The count and
# digest below are re-cut by tools/catalogue/pin_catalogue_contract.py from
# rows it has verified against that derivation; an edit to any appended row,
# a removed pack row or an extra lesson row still reds here.
CATALOGUE_SHELF_ROWS = 222
# UX2 A1: keys that may be appended to an original row without moving its
# digest (see catalogue_errors). Nothing else is additive. No original row
# carried either key before the ruling (measured 2026-09-08: 0 of 734), so the
# second set is empty and the allowance cannot launder a pre-existing value.
CATALOGUE_ADDITIVE_TAG_KEYS = frozenset({"halfTerm", "unit"})
CATALOGUE_ORIGINAL_KEYS_BEFORE_TAGS = frozenset()
CATALOGUE_SHELF_ROWS_SHA256 = "0e6805d0866fd029aed17b9410785ce013d21c51b6d7a0fddfc972efbc9e98a5"

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
    # UX2 A1 (2026-09-08): the record's schema travels with the record. It is
    # data, not a lesson payload; it is enforced by tools/ux2/check_catalogue_schema.py.
    "resources.schema.json",
}

# The education publisher is executable release configuration, not a hub asset.
# Permit only this named workflow, and require its complete reviewed bytes on
# every run. A broader permission, trigger, job, floating ref or mismatched
# builder is red.
PUBLICATION_CALLER_PATH = ".github/workflows/education-pages.yml"
# Reviewed Education completion publication caller, Site PR #268, 2026-09-06;
# advanced to Site #299 47811e56, then Site #301 50877370 (Play revision registry: Glitch HUD and
# §3.3 touch-action revisions, transition pairs) by Order HC4.
# Until Order UX2 both callers advanced together and this one digest served
# both repositories' callers. UX2 moved the Lessons caller alone (Lessons #436,
# #438, #442; the order writes nothing to the Apps repository), so this digest is the
# LESSONS caller's, and the Apps caller carries its own reviewed digest below.
# Advanced 2026-09-09 (SX1/SX2): the Lessons caller's publisher pin moves Site
# 92abc460 -> 94ae15f8 so the all-file admission registry admits the Spring/Summer
# Science batch. The Site commit is 92abc460 byte-identical except that registry and
# the retained usage-registry baseline; education-publication.yml is unchanged between
# them, so no builder, Play or usage-discovery code moves with the pin.
# Advanced 2026-09-10 (AMEND-3R-GC1 P6): the publisher pin moves Site 2a154e33 ->
# 2e49afdd. Unlike every advance above it, this one moves BUILDER code and not only
# the admission registry -- .sb3 is added to the publisher extension allowlist and
# to the admission census, without which the 23 Scratch projects in the GROW
# Computing unit never reach the served tree. education-publication.yml is
# unchanged between the two, so the gate itself still does not move.
# GC1 12 September: reviewed 810ae8f8 -> 3c2743fb registration-only carrier.
# SW2-T5R1: consumer-specific registry-only carriers, with unchanged publisher code.
# Advanced 2026-09-15 (CX2 R5) to Site carrier 297ed5dea71461d25365fa8a9ef1139b7d161996, which is
# c06526c5 byte-identical except the admission registry (two regenerated catalogue files admitted
# beside their published rollback digests). Only the caller's two commit references and its
# comment move; this digest is the caller file after that move.
# Advanced 2026-09-15 (CX2 S3) to Site carrier a89e2c601b491be7b0121754a17f56228eafa21a on the same
# carrier branch: 297ed5de plus two registry commits (Lane D BUILD W8B and its lesson-order; the
# relabelled teaching-pack hub). Every entry keeps its published rollback digest beside the
# candidate. Only the caller's references and comment move.
# Advanced 2026-09-15 (CX2 §2 Friction) to Site carrier 8cfd08b3abe08eeb79ff2139bedf07fbf536c520 on the same carrier branch:
# the GROW W3 Friction candidate (this branch, #538) admitted beside its published rollback digests — the lesson, resource pages, GROW pack records, seven Week 3 archives, W3A/W3B natives, the hub index, lesson-order.json and the usage registry (30 pairs, nothing added or removed). Digests from a full three-repository build at this builder, qualified by a control build of main that reproduces all 4044 admitted digests. Publisher code is unchanged.
# Advanced 2026-09-15 (CX2 §2 Friction rows) to Site carrier 17e82d701c25354719114b4fca2fc3207a9da3d8 on the same carrier branch:
# the reviewed Science download rows (science-download-usage-additions.json, pinned by check_education_separation.py) brought to the nine Friction files whose size changed; the first publication of main acae624f stopped there after admission had passed. Registry unchanged from 8cfd08b3; no other publisher code moves.
# Advanced 2026-09-15 (CX2 §3 Diffusion) to Site carrier 7f97cbbfba76a44e86514116eaea67bd46782274 on the same carrier branch:
# the LAUNCH W4L1 Diffusion candidate (this branch, #546) admitted beside the published Friction digests (38 pairs, nothing added or removed) with its thirteen download rows reviewed; one commit on from the Friction rows carrier main pins. Publisher code is unchanged.
# Advanced 2026-09-15 (CX2 §4.8 Sugar R10) to Site carrier d76182f4cbb0071b3652feba265dc66129d393f0 on the same carrier branch:
# the Sugar R10 hygiene candidate (this branch, #547) admitted beside the published Diffusion digests: the BUILD W8A lesson whose feedback card no longer names the evidence product, its re-rendered teacher DOCX and PDF, the BUILD checksum list and lesson-order.json (5 pairs, nothing added or removed). No reviewed download row moves — the two documents keep their KB-rounded sizes, measured at 0 of 320 rows changed. Digests from a full three-repository build qualified by a control build of main a8b3c968 that reproduces every admitted digest. Publisher code is unchanged.
# Advanced 2026-09-15 (CX2 §8.3 Lane D) to Site carrier 429dd4ecf0ef00f8e04d2296473cf99f46243cbd on the same carrier branch:
# the whole return week (this branch, #545, carrying #543 BUILD and #544 GROW) admitted beside the published Sugar digests: BUILD W8B, GROW W8A and W8B, LAUNCH W8L1-W8L3 and lesson-order.json (7 pairs, nothing added or removed). No reviewed download row moves — these six lessons carry no pack downloads, measured at 0 of 320 rows. This carrier also replaces the withdrawn sparse W8B digest with the one a full build actually produces. Digests from a full three-repository build qualified by a control build of main ec7d34ab that reproduces every admitted digest. Publisher code is unchanged.
# Advanced 2026-09-15 (CX2 §8.3 Lane D, corrected) to Site carrier dd9d228aeb183f6efc26f2f7f35982f70b3f91de on the same carrier branch:
# the whole return week (this branch, #545, carrying #543 and #544) admitted beside the published Sugar digests, re-cut after the authored lesson-config block was restored to all six lessons (W8B b67be20d -> 492a4c28). Seven pairs, nothing added or removed; no reviewed download row moves. Digests from a full three-repository build qualified by a control build of main ec7d34ab. Publisher code is unchanged.
# Advanced 2026-09-16 (CX2 §8.3 Lane D, corrected again) to Site carrier 3032ae716518c9e51b3ea00314e288bbb4145d9a on the same carrier branch:
# the whole return week (this branch, #545, carrying #543 and #544) admitted beside the published Sugar digests, re-cut after the guidance button was docked and the stage timer moved off the home link in all six lessons (the full offline-pack check now passes 12/12). Seven pairs, nothing added or removed; no reviewed download row moves. Digests from a full three-repository build qualified by a control build of main ec7d34ab. Publisher code is unchanged.
# Advanced 2026-09-16 (CX2 §5.3 EDU-Q1 companions) to Site carrier 40339776460347d0018569d598c45d0dd1a93497 on the same carrier branch:
# Carrier 40339776 admits the six catalogue/discovery outputs the companion rows move, as [served, candidate] from full builds (served oracle main e1a05dce).
# Advanced 2026-09-16 (CX2 §5.3 EDU-Q1 companions (second mint)) to Site carrier 7491329d8533b7edf6d32cfaa13a065c28af3f41 on the same carrier branch:
# Carrier admits hub.js (pathway directory read case-insensitively) beside the six catalogue/discovery outputs, as [served, candidate] from full builds.
# Advanced 2026-09-16 (CX2 section 7.1 PLAY-Q1 batch 2) to Site carrier 08d74766de02b90e90e6138b7c20e66bb30aada4 on the same carrier branch:
# Carrier admits the two re-stamped education lessons, the lesson-order projection and the resource
# size table, and carries the Play evidence rebound to the batch 2 bytes.
PUBLICATION_CALLER_SHA256 = "4e1678265e6a4a4d7478112778ff8ef552d08003b67ac4f2cc2aa7802111c17f"
# One reviewed caller digest per repository kind. detect_kind() reads the root
# it is standing in, so this entry is only ever compared against the Apps
# repository's own caller: the Lessons gate run and the Apps gate runs are the
# only callers of publication_errors(), and the Site repository invokes this
# verifier in no workflow at all.
# UX2 A5 pinned this to the Apps caller at 924ab986 -- the commit Site
# domain-split-verify.yml checks out, whose caller names Site 23a4f360 -- on the
# premise that a Site catalogue-contract control ran this gate against that
# checkout. No such control exists, and 924ab986 is behind Apps main. The
# reviewed Apps caller is the merged one: Apps #72 advanced it 23a4f360 ->
# 6430f23f (CX3 cycle C) on 2026-09-08, superseding c420519111f6 thirty-six
# minutes after it was written. The mismatch stayed invisible while the Apps
# gate copy predated UX2 A5 and so had no by-kind map to read; putting the two
# copies back in step is what made it fire.
PUBLICATION_CALLER_SHA256_BY_KIND = {
# Advanced 2026-09-16 (D-1): this repository's own publisher pin moved to the Site
# carrier f70f4973, which re-binds the homepage feature card to this repository's main
# and mints the publication admission for the paths whose bytes had moved. The caller
# file therefore changed, and this is its digest re-cut from those bytes. The "lessons"
# entry is now its own literal rather than an alias of PUBLICATION_CALLER_SHA256, which
# stays where UX2 A5 left it: the two kinds pin different files and had no business
# sharing one constant.
# ORDER SX3-PASSES: the publisher pin moves to Site main 0cd8f842, which carries the
# 21 transition pairs for this release's published bytes, the re-frozen retained
# registry baseline, and the builder-pin move that puts domain-split-verify on
# the same Lessons state as this carrier. A CARRIER PIN MOVE under release-red
# precedence. The caller file therefore changed and this is its digest re-cut
# from those bytes -- derived with sha256sum, never transcribed.
# ORDER HUM-T batch 1 (STANDING RULE L33, 2026-09-20): the publisher pin moves to Site main
# cac643be, which carries the eight transition pairs for the six transplanted BUILD decks,
# the lesson order and the size table, and both L31 pin pairs at 3887f7ac / 327da98e. The
# caller file therefore changed and this is its digest re-cut from those bytes -- derived
# with sha256sum, never transcribed.
# ORDER HUM-T batch 1, second window (STANDING RULE L33, 2026-09-20): the publisher pin moves to Site main a461a77a; the caller
# file therefore changed and this is its digest re-cut from those bytes -- derived with
# sha256sum, never transcribed.
# ORDER SCI-COMPLETE PASS A (STANDING RULE L33, 2026-09-20): the publisher pin moves to Site main 3cff4ba7; the caller
# file therefore changed and this is its digest re-cut from those bytes -- derived with
# sha256sum, never transcribed.
# ORDER HUM-T batch 2 (STANDING RULE L33, 2026-09-20): the publisher pin moves to Site main 297e09b4; the caller
# file therefore changed and this is its digest re-cut from those bytes -- derived with
# sha256sum, never transcribed.
# ORDER HUM-T batch 3 (STANDING RULE L33, 2026-09-20): the publisher pin moves to Site main 83ffbe8b; the caller
# file therefore changed and this is its digest re-cut from those bytes -- derived with
# sha256sum, never transcribed.
# ORDER HUM-T batch 4 (STANDING RULE L33, 2026-09-20): the publisher pin moves to Site main aad258a9; the caller
# file therefore changed and this is its digest re-cut from those bytes -- derived with
# sha256sum, never transcribed.
# ORDER HUM-T batch 5 (STANDING RULE L33, 2026-09-20): the publisher pin moves to Site main ec58a420; the caller
# file therefore changed and this is its digest re-cut from those bytes -- derived with
# sha256sum, never transcribed.
    "lessons": "11b429dc41065ee516dda1039d8bd46987db5a17c8ac9bc87fc01dbbe6122a7e",
# Advanced 2026-09-16 (served-defect amendment D-2): the Apps repository moved its own
# publisher pin to the Site carrier that carries EDU-D3, so its caller file changed. This is
# that file's digest on Apps main, re-cut from its bytes.
    "apps": "fa424547f5f7effdc284e87bdf72dd816efbeca59b2d79457f381c80d4c19fec",
}
PUBLICATION_GATE_WORKFLOW_PATH = ".github/workflows/mbm-cross-estate-unification.yml"


# HC3, 2026-09-06: exact reviewed CI-only LundyLoop proof transaction.
# Full hashes remain checked on every Apps run, including files not in the diff.
# No standalone payload or arbitrary CI path is granted. Both gate copies match.
LUNDYLOOP_CI_PINS = {
    # SW2-T5R1: the shared browser proof is also required at reviewed bytes.
    # Re-cut 2026-09-19 (SX3 PASS 6, STOP-P1 control): the PUBLISHED table on its line 24
    # is now DERIVED from the Site admission registry by tools/sw2/pin_published_digests.py
    # (lessons "" 5c4e3ced, subject.html 93a071a8, apps "" f15bc17d), so the reviewed bytes
    # moved; digest taken from the edited file, never typed.
    "tools/sw2/check_tokens_inert.cjs": "854df1c0c5549b4713aa18e286379fc21aad72939ded8b56d04b069a1a9c28da",
    ".github/workflows/verify-lundyloop-professional-os.yml": "7e6cf886ff1af45cc3bcf255ee6a688b75dbb4034fce20b609fe0188a63c11ce",
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
    # PIN1 Apps, 2026-09-12: exact internal trigger-derivation machinery.
    # Both workflows check its output; no payload or directory is exempted.
    "tools/pin1/derive_triggers.py",
    "tools/pin1/test_derive_triggers.py",
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
    # ORDER UX2, 2026-09-08 (Parts A and D). The same shape again: the order's
    # ledger (written on every part), the README (documents the size table), the
    # re-pointed chip gate, the UX2 gates workflow and its tools (run in CI, ship
    # nothing), and three DERIVED data files the hub reads at runtime. The data
    # files are regenerated by tools/ux2 and checked against their derivation by
    # .github/workflows/ux2-gates.yml on every change; a lesson edit regenerates
    # the size table, so a boundary that reds on it would red every ordinary
    # lesson pull request. None of these is a studio and none can alter one.
    "UX2_LEDGER.md",
    "README.md",
    # ORDER CX2, 2026-09-15. The same shape as the UX2 ledger: the order, its
    # working checkpoint (appended after every material result), the lesson
    # standard it cites and the recorded PLAY amendment. Documentation only;
    # none of these is a studio, none is served and none can alter one.
    "docs/orders/CX2_FINISH_2026-09-15.md",
    "docs/orders/CX2_CHECKPOINT.md",
    "docs/orders/LESSON_STANDARD_2026-27.md",
    "docs/orders/PLAY_BRAND_AMENDMENT_2026-09-15.md",
    # ORDER CX2, 2026-09-15. The source-admission tools. Each one stages one
    # reviewed replacement transaction: it declares the transaction in the GLV3
    # boundary, extends the reviewed-path list, refreshes the derived catalogue
    # records and re-cuts the pins. They run locally and in review, ship nothing
    # and are outside the publisher's public_file() admission, so none is served
    # and none can alter a studio.
    #
    # They are listed because of an asymmetry in this very check: the changed set
    # counts MODIFICATIONS, not additions, so each tool passed silently while it
    # was new and reds the first time it is touched after its branch merges. That
    # bit the CX2 checkpoint above and then tools/rw1/admit_w8.py, whose review
    # base must move to the current main on every re-admission. Listing the class
    # rather than the instance that happened to fail.
    "tools/grow_resources/admit_w3_friction.py",
    "tools/launch_resources/admit_w4l1.py",
    "tools/launch_resources/refresh_w4l1_pack_records.py",
    "tools/science_teaching_packs/cx2_sugar_r10.py",
    "tools/rw1/admit_w8.py",
    "tools/rw1/cx2_lane_d.py",
    "tools/verify_lessons_chips.mjs",
    ".github/workflows/ux2-gates.yml",
    "tools/ux2/hub_gates.mjs",
    "tools/ux2/unit_tags.py",
    # UX2 D3 added the companion-pack deriver and its placement manifest but did
    # not list them here, though every peer is listed (build_spine, unit_tags,
    # resource_sizes, calendar-spine.json, resource-sizes.json ...). The gap was
    # invisible because it only bites a PR that changes one of them AND this
    # file, which only a contract re-pin forces. pin_catalogue_contract.py --
    # already allowed -- imports the deriver and reads the manifest to rebuild
    # the pack tail, so both are catalogue-record machinery, not lesson payload.
    "tools/ux2/companion_catalogue.py",
    "data/companion-packs.json",
    "tools/ux2/check_catalogue_schema.py",
    "tools/ux2/prove_catalogue_gate.py",
    "tools/ux2/build_spine.py",
    "tools/ux2/resource_sizes.py",
    "tools/ux2/fixtures/hub-hrefs-before-ux2.txt",
    "tools/ux2/fixtures/appendix-a-lessons.json",
    "tools/ux2/fixtures/retired-hrefs.json",
    "data/calendar-spine.json",
    "data/resource-sizes.json",
    "data/planning-keys.json",
    # ORDER UX2 Part D2 (2026-09-08): each subject's checksum manifest is
    # regenerated in the content PR that places companion packs (the order
    # requires it). A checksum list is a record of bytes, not a studio; the
    # gate that proves the packs is tools/ux2/check_companion_packs.py.
    "Humanities_Teesside/Teaching_Packs/SHA256SUMS.txt",
    "Science_Teesside/Teaching_Packs/BUILD/SHA256SUMS.txt",
    "Science_Teesside/Teaching_Packs/GROW/SHA256SUMS.txt",
    "Science_Teesside/Teaching_Packs/LAUNCH/SHA256SUMS.txt",
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


# ORDER FINISH-2, manifest-pin ruling (2026-09-20). A pack-scale population cannot be
# carried as exact per-file pins. PIN1 materialises one trigger path per pinned file,
# and the HUM-D5 packs' 1750 pins took the derived workflow to 534,033 bytes -- which
# GitHub would not load at all: three push runs ended instantly with zero jobs, no
# pull_request run was ever created, and so this gate never ran on the pull request
# that landed them. A gate that cannot start is not a gate. The packs are therefore
# pinned by their own SHA256SUMS manifest.
#
# This function is what stops that being a loosening. Every member a pinned manifest
# lists is digest-checked here on every run, exactly as an individual pin would have
# been: the coverage is kept, only the indirection changes. The manifest's own bytes
# are pinned in CATALOGUE_PINS and checked by the loop above, so a manifest edited to
# admit a new file reds on the pin before the list it carries is ever honoured.
#
# Scope is exact and narrow: a pinned manifest is expanded only at
# <CATALOGUE_PACK_MANIFEST_ROOT>/<one path segment>/SHA256SUMS.txt, the shape the
# HUM-D5 packs land in. The Science pack manifests sit outside it and are untouched,
# so no file that was never part of this ruling is newly judged here.
CATALOGUE_PACK_MANIFEST_ROOT = "Humanities_Teesside/Teaching_Packs"
CATALOGUE_PACK_MANIFEST_NAME = "SHA256SUMS.txt"


def catalogue_pack_manifests(pins: dict) -> list[str]:
    """The pinned pack manifests whose listed members this gate expands."""
    root = CATALOGUE_PACK_MANIFEST_ROOT.split("/")
    return [rel for rel in sorted(pins)
            if rel.split("/")[:len(root)] == root
            and len(rel.split("/")) == len(root) + 2
            and rel.split("/")[-1] == CATALOGUE_PACK_MANIFEST_NAME]


def catalogue_manifest_entries(root: Path, rel: str) -> tuple[dict[str, str], list[str]]:
    """Parse one pinned pack manifest into {member path: reviewed digest}.

    An unreadable, malformed or empty manifest returns an ERROR, never an empty
    mapping. Treating it as "nothing to check" is precisely the silent gap this
    indirection would otherwise open, and it is the same refusal fence_errors
    makes for an unreadable fence.
    """
    try:
        text = (root / rel).read_text("utf-8")
    except (OSError, ValueError) as exc:
        return {}, [f"reviewed pack manifest could not be read, so its members cannot be honoured: {rel} ({exc})"]
    entries: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        checksum, separator, name = line.partition("  ")
        name = name.strip()
        if not separator or not re.fullmatch(r"[0-9a-f]{64}", checksum) or not name:
            return {}, [f"reviewed pack manifest line {number} is not a sha256sum record: {rel}"]
        if name.startswith("/") or ".." in name.split("/") or name in entries:
            return {}, [f"reviewed pack manifest line {number} names an unusable or repeated member: {rel}"]
        entries[name] = checksum
    if not entries:
        return {}, [f"reviewed pack manifest names no member; refusing to treat an empty manifest as no manifest: {rel}"]
    return entries, []


def catalogue_manifest_errors(root: Path, pins: dict) -> list[str]:
    errors = []
    for rel in catalogue_pack_manifests(pins):
        base = rel[: -len(CATALOGUE_PACK_MANIFEST_NAME)]
        entries, problems = catalogue_manifest_entries(root, rel)
        errors.extend(problems)
        for name, expected in entries.items():
            member = base + name
            path = root / member
            if not path.is_file():
                errors.append(f"reviewed pack manifest member is missing: {member}")
            elif digest(path) != expected:
                errors.append(f"reviewed pack manifest member bytes differ: {member}")
    return errors


def catalogue_manifest_member_paths(root: Path) -> list[str]:
    """Every member path a pinned manifest admits, for the self-test fixture."""
    pins = CATALOGUE_PINS.get("files", {})
    members = []
    for rel in catalogue_pack_manifests(pins):
        base = rel[: -len(CATALOGUE_PACK_MANIFEST_NAME)]
        entries, _ = catalogue_manifest_entries(root, rel)
        members.extend(base + name for name in entries)
    return members


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
            # UX2 A1 (2026-09-08): the two ADDITIVE tag keys, `halfTerm` and `unit`,
            # may be appended to an original row. Every other byte of every
            # original row stays under the digest: the keys are stripped before
            # hashing, so an edit to any existing value, a removal or a reorder
            # still reds here. The tag values themselves are gated by
            # tools/ux2/unit_tags.py --check (derivation) and
            # tools/ux2/check_catalogue_schema.py (enum/shape). Proved red on a
            # planted title edit and a planted unknown key by
            # tools/ux2/prove_catalogue_gate.py.
            def without_tags(value):
                return [{k: v for k, v in row.items() if k not in CATALOGUE_ADDITIVE_TAG_KEYS} for row in value]
            if row_digest(without_tags(rows[:CATALOGUE_ORIGINAL_ROWS])) != CATALOGUE_ORIGINAL_ROWS_SHA256:
                errors.append("an original catalogue row was removed, reordered or edited")
            for index, row in enumerate(rows[:CATALOGUE_ORIGINAL_ROWS]):
                for key in row:
                    if key in CATALOGUE_ADDITIVE_TAG_KEYS and key not in CATALOGUE_ORIGINAL_KEYS_BEFORE_TAGS:
                        continue
                    if key in CATALOGUE_ADDITIVE_TAG_KEYS:
                        errors.append(f"original row {index} carried {key} before the tag ruling; refusing to treat it as additive")
            if row_digest(without_tags(rows[CATALOGUE_ORIGINAL_ROWS:])) != CATALOGUE_SHELF_ROWS_SHA256:
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
    errors.extend(catalogue_manifest_errors(root, pins))
    return errors


# SX3 FENCE. ORDER SX3-M4 §1(b). _sx3/FENCE.json names the decks whose proof
# the #586 limb narrowing removed. The loss is latent: the limb only runs when a
# deck's bytes drift from its recorded evidence sha256, and a drift on one of
# these drops its week binding SILENTLY, because none of them is
# style:recommended and so none raises. The fence holds until the fallback limb
# lands. It is enforced here, against the pull request's own diff, because this
# gate already runs on every pull request in both estates and already computes
# that diff — no new workflow, no new trigger to forget.
#
# A missing FENCE.json is not an error: the Apps estate has none, and the fence
# is retired by deleting the file once the fallback limb has landed.
FENCE_PATH = "_sx3/FENCE.json"


def fence_errors(root: Path, changed: set[str], kind: str) -> list[str]:
    if kind != "lessons":
        return []
    source = root / FENCE_PATH
    if not source.is_file():
        return []
    try:
        fence = json.loads(source.read_text("utf-8"))
    except (ValueError, OSError) as exc:
        return [f"{FENCE_PATH} could not be read, so the fence cannot be honoured: {exc}"]
    entries = fence.get("fenced")
    if not isinstance(entries, list):
        return [f"{FENCE_PATH} has no 'fenced' list; refusing to treat an unreadable fence as an empty one"]
    fenced = {row.get("path") for row in entries if isinstance(row, dict) and row.get("path")}
    if not fenced:
        return [f"{FENCE_PATH} names no fenced path; refusing to treat an empty fence as no fence"]
    hit = sorted(fenced & changed)
    return [f"fenced deck modified before the fallback limb landed: {rel} "
            f"(see {FENCE_PATH} and _sx3/STOP_L_limb_population.md)" for rel in hit]


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


def publication_errors(root: Path, kind: str = "lessons") -> list[str]:
    errors = publication_trigger_errors(root)
    caller = root / PUBLICATION_CALLER_PATH
    if not caller.is_file():
        errors.append("reviewed education publication caller is missing")
    elif digest(caller) != PUBLICATION_CALLER_SHA256_BY_KIND.get(kind, PUBLICATION_CALLER_SHA256):
        errors.append("education publication caller differs from the reviewed immutable publisher pin")
    return errors


def lundyloop_ci_errors(root: Path, kind: str) -> list[str]:
    if kind != "apps":
        return []
    return ["reviewed LundyLoop CI bytes differ or are missing: " + rel
            for rel, expected in LUNDYLOOP_CI_PINS.items()
            if not (root / rel).is_file() or digest(root / rel) != expected]


def boundary_errors(changed: set[str], kind: str) -> list[str]:
    # SW2-T5R1 retires AR3: shared assets are admitted only through their
    # required exact-byte registry, checked on every run above.
    allowed = ALLOWED_DIFF | set(CANONICAL_HASHES)
    if kind == "apps":
        allowed = allowed | set(LUNDYLOOP_CI_PINS)
    if kind == "lessons":
        allowed = allowed | set(CATALOGUE_PINS.get("files", {})) | CATALOGUE_RECORD_PATHS
    unexpected = sorted(changed - allowed)
    if not unexpected:
        return []
    errors = [f"standalone/offline boundary violated by changed files: {unexpected}"]
    # ORDER SX3-M5 §2: name the CAUSE, not just the symptom. A lesson deck that
    # reaches this line has not been admitted, and "boundary violated" reads like
    # the change is forbidden when what is missing is the admission. The estate
    # admits a deck by naming it in CATALOGUE_PINS; tools/pin1/derive_triggers.py
    # --write then materialises the matching trigger path, and PIN1 asserts the
    # two sets are equal in both directions. This is the remedy, in one line,
    # where the refusal is read.
    decks = [rel for rel in unexpected
             if rel.startswith("Science_Teesside/") and rel.endswith(".html")]
    if decks:
        errors.append(
            "deck not admitted; add to the boundary set (CATALOGUE_PINS, via "
            "tools/catalogue/pin_catalogue_contract.py) and to the trigger list "
            "(tools/pin1/derive_triggers.py --write), which PIN1 then asserts as "
            f"a pair: {decks}")
    return errors


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
    errors: list[str] = publication_errors(root, kind) + lundyloop_ci_errors(root, kind)
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
            # UX2 A2 (2026-09-08): the hub derives both count lines from the catalogue it
            # fetches at runtime — the browse line "<M> resources · <S> subjects" and the
            # results line "<n> of <M> resources". The retired year tabs and subject
            # chips (fillTabCounts, buildQuicknav) no longer exist, so the contract names
            # the expressions that replace them and the fetch they derive from.
            for token in ("${rows.length} of ${H.state.rows.length} resources",
                          "${rows.length} resources · ${cards.length} subjects", "H.loadAll()"):
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
            errors.extend(fence_errors(root, changed, kind))
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
        for rel in set(["index.html", "resources.json" if kind == "lessons" else "apps.json", PUBLICATION_CALLER_PATH, PUBLICATION_GATE_WORKFLOW_PATH, *CANONICAL_HASHES] + (list(CATALOGUE_PINS.get("files", {})) + catalogue_manifest_member_paths(root) if kind == "lessons" else list(LUNDYLOOP_CI_PINS))):
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
        if kind == "lessons":
            # The fence must go red on a fenced path and stay quiet on anything
            # else, and it must REFUSE rather than pass when the file it depends
            # on is unreadable or empty. A fence that cannot go red is not a fence.
            fence_file = root / FENCE_PATH
            if fence_file.is_file():
                fenced = json.loads(fence_file.read_text("utf-8"))["fenced"]
                one = fenced[0]["path"]
                if not fence_errors(root, {one}, "lessons"):
                    raise RuntimeError("the fence let a fenced deck through: " + one)
                if fence_errors(root, {"Science_Teesside/Build/does-not-exist.html"}, "lessons"):
                    raise RuntimeError("the fence objected to an unfenced path")
                if fence_errors(root, {one}, "apps"):
                    raise RuntimeError("the fence fired on the apps estate, which has no fence")
                with tempfile.TemporaryDirectory(prefix="mbm-fence-control-") as broken:
                    empty = Path(broken)
                    (empty / FENCE_PATH).parent.mkdir(parents=True, exist_ok=True)
                    (empty / FENCE_PATH).write_text('{"fenced": []}', encoding="utf-8")
                    if not fence_errors(empty, {one}, "lessons"):
                        raise RuntimeError("an empty fence was treated as no fence")
                    (empty / FENCE_PATH).write_text("not json", encoding="utf-8")
                    if not fence_errors(empty, {one}, "lessons"):
                        raise RuntimeError("an unreadable fence was treated as no fence")
                print(f"SX3 fence controls: {len(fenced)} fenced path(s) red / unfenced path green / apps estate quiet / empty and unreadable fence red")
            # ORDER FINISH-2 manifest-pin ruling: 1605 pack members are admitted by
            # their manifest rather than by 1605 individual pins, so the expansion
            # must be PROVED able to go red on every way that can be abused. A
            # manifest check that cannot go red is a 1605-file hole, and this control
            # is the whole reason the indirection is not a loosening.
            pins = CATALOGUE_PINS.get("files", {})
            manifests = catalogue_pack_manifests(pins)
            if manifests:
                index_text = (fixture / "index.html").read_text("utf-8")
                one = manifests[0]
                base = one[: -len(CATALOGUE_PACK_MANIFEST_NAME)]
                entries, problems = catalogue_manifest_entries(fixture, one)
                if problems:
                    raise RuntimeError("a pinned pack manifest did not parse in the fixture: " + "; ".join(problems))
                member = base + sorted(entries)[0]
                target = fixture / member
                kept_member = target.read_bytes()
                target.write_bytes(kept_member + b"\n<!-- planted unreviewed byte -->\n")
                if not catalogue_manifest_errors(fixture, pins):
                    raise RuntimeError("a manifest-listed pack member's byte drift was not detected: " + member)
                target.unlink()
                if not catalogue_manifest_errors(fixture, pins):
                    raise RuntimeError("a missing manifest-listed pack member was not detected: " + member)
                target.write_bytes(kept_member)
                if catalogue_manifest_errors(fixture, pins):
                    raise RuntimeError("the restored pack member did not pass")
                manifest_file = fixture / one
                kept_manifest = manifest_file.read_bytes()
                manifest_file.write_bytes(kept_manifest + b"0" * 64 + b"  planted/unreviewed_addition.pptx\n")
                if not catalogue_manifest_errors(fixture, pins):
                    raise RuntimeError("a manifest enlarged to admit an unreviewed file was not caught by the expansion")
                if ("reviewed catalogue bytes differ: " + one) not in catalogue_errors(fixture, "lessons", index_text):
                    raise RuntimeError("a manifest enlarged to admit an unreviewed file was not caught by its own pin")
                manifest_file.write_bytes(b"not a sha256sum manifest\n")
                if not catalogue_manifest_errors(fixture, pins):
                    raise RuntimeError("an unreadable manifest was treated as no manifest")
                manifest_file.write_bytes(b"")
                if not catalogue_manifest_errors(fixture, pins):
                    raise RuntimeError("an empty manifest was treated as no manifest")
                manifest_file.write_bytes(kept_manifest)
                if catalogue_manifest_errors(fixture, pins):
                    raise RuntimeError("the restored manifest did not pass")
                listed = sum(len(catalogue_manifest_entries(fixture, rel)[0]) for rel in manifests)
                print(f"pack manifest controls: {len(manifests)} pinned manifest(s) admitting {listed} member(s); "
                      f"member drift red / member missing red / manifest enlargement red on BOTH the expansion and its pin / "
                      f"unreadable manifest red / empty manifest red / restored green")
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
