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
        "_sx3/SX3_PASSES_LEDGER.md": "4c47b97880f45050ba35cf301212592e9b39cc0cbb4423091a8553f695885e48",
        "tools/sx3/pre_ci_catalogue_sweep.sh": "742316438ef8421c1bd199341b1c364654c05e895fa51cc5d362e6e86133aaf3",
        "assets/catalogue/display-titles.json": "8e8aac1643221c5511b469cbf734838dd14fbd7bdd7e8cb2fc71e5227c0339bd",
        "tools/catalogue/build_display_titles.py": "4256ab6b07420af4ef090e57d32b8f29fcae88d9075d64750e52f17947dbd8a1",
        "tools/catalogue/check_display_titles.cjs": "5d06689114a69124a2d7f59d644a85775756eadd2b470df01e066c2202df681b",
        "tools/catalogue/check_display_titles_browser.cjs": "5662cdb93c7796ead4fb9bb69ce94ac65fe1e29e103f00c65bd07a4d5129a7cd",
        "tools/verify_lessons_chips.mjs": "e417afd94ae4f3a450caab2edf4b6c41d14e4588f070d0ad822263e30a86cf39",
        "tools/sw2/check_tokens_inert.cjs": "0feabd4ad86fd578ca85a69b491dd92ea133697c77f4385cd3a15ebc1810abf9",
        "assets/catalogue/lesson-order.json": "25c707845f1f4bd0c83ee8b6e15a21f4758af862efd0b59078ac1ad4cdedf748",
        "tools/catalogue/build_lesson_order.py": "8a09eec10f828d44c02397f3d7afe37548128143f6dbab22c90db8d74bc586a7",
        "tools/ux2/hub_gates.mjs": "80ae8def49c49e549c8a2e6b65d521cfdaebb2b7d05f650fa6d5e436f2b6586d",
        "index.html": "389c3320b158e9bc472b4402d41d1d23e4bb2d78b54385884c0be6ca31f73309",
        "Science_Teesside/index.html": "3e0c54aa15453164890db38bb6cd2096db5c061f901beb643cdb9ea1316d830f",
        "Humanities_Teesside/index.html": "7594ce3f6bd34025e32f556d736d39fd218b409a36511ab57e779c4080c4cd86",
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
        "assets/catalogue/science-shelf.css": "f664655e57c086abe35499f5dedf737eddaa0942e6629dd4a7fcf4e801536508",
        "assets/catalogue/science-shelf.js": "b47b998866401f136968a2e1e94cc5beb65be83fbd342f49ff5a811804792651",
        "assets/catalogue/terms-and-styles.json": "fbcc0ad022a7239a2fc0f0137716c1dc4d2156e13214944e7a0d55b01363ca24",
        "assets/catalogue/science-shelf.json": "4ee03d7827f1c2ef9d6af927b2451506d895e237ffa4f7b694b4bdb855a1170a",
        "assets/catalogue/humanities-shelf.json": "b2facaa50c6781f0fdf19fad5b3b170bfaef54546c030e951956ccf47223f8c0",
        "tools/catalogue/build_catalogue.py": "10a704418e67c6b9ec80bb911cfe267df7a12e8c4adbb6e878ca14c5cfb7c3b1",
        "tools/catalogue/build_science_shelf.py": "a06ce779e4331661dadcdeb896b5d533374ca82bba812f605860c6fe53d11335",
        "tools/catalogue/build_humanities_shelf.py": "ef74f9eced59fd6ec33f22c02cf0d39d518ac6f2eb8873aaf21517859fb78662",
        "tools/catalogue/check_catalogue_static.py": "1f55f22846763ded7bd27fdc389b57d1cba3b1eb58c066c944dde9b6b70617df",
        "tools/catalogue/check_catalogue_dom.cjs": "4d18cc2f1fb330ee9f629a55296436b1a207758d51b6281b3b85ec8bfcf0c376",
        "tools/catalogue/verify_education_navigation.cjs": "b0d9297a33fb9ea2494fecaa45e02ae6fcf6fa88e6a62ced35cf521fbb1851fd",
        "tools/catalogue/sync_shelf_card_titles.py": "f906e244fd8fd2e596e6e5e0a1fce9a53bee828eed0b74194eccf4860e45b7a0",
        "tools/catalogue/restamp_evidence_sha256.py": "bbd736cb4da363732d5493b3dcd0919f3f22561a8612fb34a6f143270bb62b9d",
        "Science_Teesside/Build/START_HERE.html": "acac26140f5aeef22292e6ce3831fa61aaf5e62432cc3998b340918c8bfaee7f",
        "Science_Teesside/Grow/START_HERE.html": "d2bec305dec3212215c6f599cad3925c571f9a34ca6e85268893c8ed142170dd",
        "Science_Teesside/Launch/START_HERE.html": "10b46e7cf26e3aa4b7f1fb4758a039bcbec7000bc2ec8d30dfe3ce0e0b966353",
        "tools/catalogue/SHELF_SELECTION.json": "95def027287e7cc1eb1190bafa21733c9c0999286c15a231dc17dfe7a56331f4",
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
        "_glv3/tools/verify_change_boundary.py": "3520583ddf3ea8ccbffab4207e0ae69bf97295fadc7ceca681cd8c6e084de273",
        "_glv3/tools/browser_verify.mjs": "737ad30f297e061407161743f017614179cc6c56f1c9a3904bbe7c98df38c888",
        "_glv3/tools/chip_gate.mjs": "16cdd5c0ad3745c57340ed0ec6a208d221e4793bfc9b1cd9bc703a6c2613dd9a",
        "_glv3/tools/catalogue_membership.mjs": "4d7ab03e23ee0d3c3fc934f4f0a901afc61169754db099f4f5c24dd9cce058ec",
        "tools/humanities_resources/SOURCE_MANIFEST.json": "8b9c0bec517a7357fb210979712e62d465dfd9d2f2dd5f349dd2d398d9bf5cef",
        "tools/humanities_resources/DOWNLOAD_MANIFEST.json": "1d872aa4e9d01d7f10d26a0e8d182ddcb4513598413314f7c38d055318d39a2f",
        "tools/humanities_resources/CONTENT.json": "335ea55d7964d8095064e2c67c95fbd8d65e28b4d1ddf25f6e4ee812abd29b98",
        "tools/humanities_resources/ORIGINAL_MEMBER_MANIFEST.json": "c4ce9e5a0a5d966ee31f401ae476a2dc10a43aa8dc749e09b2cef87b745db073",
        "tools/humanities_resources/build_resources.py": "d99981a314f152af98fe3a64c48f7ac1bc2afe184bb0e4a2c504b8d00399366f",
        "tools/humanities_resources/check_resources.py": "ec5383e3a34cbff999f190b0014a4a73e00a3a29e2714498f7620fd638dc2aa5",
        "tools/humanities_resources/resource.css": "1aed9aaca0d73a4b200c4e5d0977e73f4e906c747d7340c7a62f4197a8344bae",
        "tools/humanities_resources/resource.js": "ad40afed95490bfcce92dc062da46e1b27bcb96bdc80e37eabdfe02bf6ffc446",
        "tools/catalogue/TERM_AND_STYLE_EVIDENCE.json": "68142f2f2d9787dbd5c6824e235d25c7879e623416bfb683e6e8a04fb14d2aa9",
        "tools/catalogue/TERM_REVIEW.json": "b0ed0d82fe21a222c75f6a38390b01defc0d5d958fac8e85421b7901ce6d201d",
        "tools/catalogue/SCIENCE_WEEK_BINDINGS.json": "b13c25e76ffbb916cf997ee62a265a6ff0bf296c125b00458df42d87985aaba2",
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
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/CHANGELOG_Final_2026-09-19.md": "44d89702b11b55a224c0eb93fe65fb0c2a48cd5c864fb3bf61045471e9512421",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_A1_W01_Captioned_Model.mp4": "0365edba2eb1e8f9848fcb233b7030d7881abb3c1a179634f4c8cce9ba409ce8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_A1_W01_Editable_Pack.docx": "ba02825ec89ddf3369ced01504a51e0dfb6a7eed93b2dcb5cc583878d44b1358",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_A1_W01_Editable_Slides.pptx": "3c705620d79776352af83609440212f753fbb158aa1eb736672e61ecbdd5de49",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_A1_W01_Knowledge_Organiser.html": "3319ae8ac031726c1f6c179410c73d0f3fb51caa6653e91a69852297a50610d9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_A1_W01_Knowledge_Organiser.pdf": "56e1958c8ca18e7533f9eb037de7a354f93d970bdc3334c9f9166c69b7851b77",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_A1_W01_Lesson.html": "4062daef3e633654a06f9d37604fa71fe70f062f1e6decce0b0856cc973195c2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_A1_W01_Model_Transcript.txt": "13ce57b1f24e88f2f72fea1ecc1597a81441a33e1fc26f4bd9e7b806db563987",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_A1_W01_Pupil_Resources.html": "a1169abd8bc321a5d1e35a1f94747c38c0736b71144dd103d4370e178ced40e8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_A1_W01_Pupil_Resources.pdf": "d6f64e3dff654aff22fd3b4e7fc563b00c937c265e091c605fb3af853abb9ee7",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_A1_W01_Teacher_Notes.docx": "af17dd534846f8d859af0bf2bcb60f3bd25d29a89c6eab0fc9b074287d6f8783",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_A1_W01_Teacher_Notes.pdf": "cd6d92efefbbe2666a581d374e1255cfea0dca3f636b48b8758eb2124a3e5b5c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/Visual_Resource.png": "739f62dab27da2af3c405215657a73cd4fdc86bd0d78cc3f70d3c8415448afae",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_A1_W02_Captioned_Model.mp4": "ca84c0f2b23b0668c901920e72a887a61e5477d6fbb266d8804df1434021d664",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_A1_W02_Editable_Pack.docx": "7120ef08a694650f33ab480736b72651e0cc8c1b187afa78b2909cc857448835",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_A1_W02_Editable_Slides.pptx": "6e344a43a78a136ae1ae7400fbb3e79192f7470024c2a3a2795b10ea8786cbf5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_A1_W02_Knowledge_Organiser.html": "725376ca946e2951c6f455fe37ba171c9cbb67ec86d6096deef5b3615dc8cd60",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_A1_W02_Knowledge_Organiser.pdf": "46c5f16b31e8cdf7729a48388c28c80e240de95ea28722c69d3a8cc5b328f5be",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_A1_W02_Lesson.html": "e6df7729754388d2df36940d207d02aabde11db6dbc82d4e780b9348ad0b04ba",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_A1_W02_Model_Transcript.txt": "2a285d96c41a8b56c6845040ec4c2feb5952364bc250f7097b61073f8eabbbe0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_A1_W02_Pupil_Resources.html": "c720b9333e788d1cb7c13821d0aa8874f82bdc8dfe8ffd50d4e403598cb4caf0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_A1_W02_Pupil_Resources.pdf": "07f6189e8f38ac8e0f7434f8e40ea5dfaebdb276c8808d7eadbcfa4fea3464af",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_A1_W02_Teacher_Notes.docx": "6f59eed401729b6133d7d532cad4768c6e1d7983bd9d59dce509e21dfd93feaf",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_A1_W02_Teacher_Notes.pdf": "ad9e26f585f631848400992f744122807a461cb707a6482154e7a8b0c4d661a0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/Visual_Resource.png": "f6b119878e95c75031aa1a7be1183417b5cd87bbb145f1d59ce75782e8054e52",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_A1_W03_Captioned_Model.mp4": "16ff50e4a61232bece5c7fc0366a4a3d6c884f8b0a3903fb3d6fe61b3f66f4ab",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_A1_W03_Editable_Pack.docx": "c00efd36d7778bdbc2690c1924c3aca0d33ed04fc9a0ff0a4aedb2956bdbf4f5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_A1_W03_Editable_Slides.pptx": "eaa7fcebf6da5d8a7d6d75d386f769da5b459c252c100daa650ca16f85b197a5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_A1_W03_Knowledge_Organiser.html": "71f004dc48d86c927c29fe1f8aae5f3d954d12c5eb9b5c0bf26772de22792cb6",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_A1_W03_Knowledge_Organiser.pdf": "b16cd4ae91723575e28171631d0a91013038dc925db20682fc278fdac57b9b6b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_A1_W03_Lesson.html": "618f9675ba934c5aadb9a53d15ef6fb54d43ec6c1bfbefe8740321d3f781273c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_A1_W03_Model_Transcript.txt": "5dbf849bd536ccc49dab4473beed627f15c586017dc1a16d12197a5657f737ab",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_A1_W03_Pupil_Resources.html": "9c1b40851e3d63ffef46fe9e725f2ed824d896c61c75f4f2a35ff0019bf9942d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_A1_W03_Pupil_Resources.pdf": "128132e40f054993bc37be8d61f3cdb1c94c5d7191f7c9a0b38c7bf8ca8f1227",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_A1_W03_Teacher_Notes.docx": "afb6bfecbe7e56613980e8809be98b156bd345c6a79e6cfe639bc472f0632a28",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_A1_W03_Teacher_Notes.pdf": "8027c68e8889015d8b7bd99bd5f9fdd92e3ffc00ab63e08f2064b251cd15281a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/Visual_Resource.png": "98612fecc4beda6094e993c06b11eb788c86eb715f64ab9a370cb5bc371dd06a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_A1_W04_Captioned_Model.mp4": "ba6a789c701d49f0104a44659d72dc04435c6d694cb123130425e7456f3e55d6",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_A1_W04_Editable_Pack.docx": "52e445fb064d2d15364fb68f26fadb33c822a92dbe1ee651d9baf46c3665e28c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_A1_W04_Editable_Slides.pptx": "915cd09969e39da792e6e2d297bc9a6b8e59b81ae5a00c48771a9773ef0f5612",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_A1_W04_Knowledge_Organiser.html": "b1fb009353157ffe5fa21f9ca44a7470b1a3c081148e41bdd747f125c45a8313",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_A1_W04_Knowledge_Organiser.pdf": "3eba00186f9998a2beb585b8e0ad9fd8701601065a9b7665514ceb301795ca60",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_A1_W04_Lesson.html": "d47361943276407e78b4f92e8e681e09352a72cdb11abdd0664cdeb7fa676586",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_A1_W04_Model_Transcript.txt": "aedca4d11bb38bd6b2cafbc361c8c83ca47283307c0235764555ab60e6431ba4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_A1_W04_Pupil_Resources.html": "c2113156281b090b318b0ab41d967e20d6f43ac817972213859659b5169ea10d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_A1_W04_Pupil_Resources.pdf": "abe043f414afe2ffdc1906eaee1e35d3562064abea0d0562d7c6d8e553e05d22",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_A1_W04_Teacher_Notes.docx": "5a748659cd26590cad6cd045eeb97841659913f6c71273fa757e70b443214119",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_A1_W04_Teacher_Notes.pdf": "f1f3517bbe9444efad0130759ea6cbd6dcc3e4a75268a854410bcaf904dd4642",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/Visual_Resource.png": "70e92c494897f11460437449966aceb385df9d0924a6e9836764b7bacf9e184e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_A1_W05_Captioned_Model.mp4": "3df8b626f20fc1c26eec1b67a8da7d1242469c8ded96f0c4fa4e1d45ba82e442",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_A1_W05_Editable_Pack.docx": "9d51e1f5db1c84461029e8a6202ce89b9f701f2a0a5dac26805a007f359b6ac2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_A1_W05_Editable_Slides.pptx": "a17cce478f866529a174cd18f87cf783f7f29016f86640072cd053986770c1a7",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_A1_W05_Knowledge_Organiser.html": "788add1e4c5e268534c635bab0ae52d1c9f6f3814724f227eb0a06d408d4e69e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_A1_W05_Knowledge_Organiser.pdf": "02929b0d103e63330d7ca83f7ebe83aa95c36febf51020db6627bbe75905921a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_A1_W05_Lesson.html": "9ec3c6e9d4b1f74894c46f1f10e22e37bc3d3310480750ecac4b24ebc11b0c31",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_A1_W05_Model_Transcript.txt": "d46fe1a1099d847a79152844e132ca844c5ab2ddb951b8a7b93bf1b30fe74884",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_A1_W05_Pupil_Resources.html": "e2d86efa2c9f839d3af28e9cd5abed02ec04c9613360265e0dba1d387f8c073f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_A1_W05_Pupil_Resources.pdf": "6951fd4b31ad20aa8ab41ed8a9e3cfeb10e931696fa2eef8b0f4879425af520e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_A1_W05_Teacher_Notes.docx": "c85834bd9bdf5cf140dbc521dfcfbed8d3756b4bb20103774b9e430eb30aa7b0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_A1_W05_Teacher_Notes.pdf": "aaa562c38c560c72254de6c6e26bf4b7a3751ecb5081f0ee06bf477045590c69",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/Visual_Resource.png": "fa0add9a62953911f2d1bd816ffb951ffce8c61d16234b05150d6a9708507049",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_A1_W06_Captioned_Model.mp4": "ae718a2c6a652dfd702ac890e3cf8aa97e248b66865663fb9ee05a30adb737dd",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_A1_W06_Editable_Pack.docx": "06951bde207b11c998097d3084556e926902b929ac521f0518a86652a0729c45",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_A1_W06_Editable_Slides.pptx": "7acc7acce0e6c49efebd7e80275667ffd46f24921a991a5e65ded35e693fa748",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_A1_W06_Knowledge_Organiser.html": "8908ace7fed1cdedbcf266082b895d38fd7e3b067a032f9c8c1277b76d8a76c8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_A1_W06_Knowledge_Organiser.pdf": "91a3e59306458f2a46a770c6c171988360fba07b031e1311368f368f72a674ff",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_A1_W06_Lesson.html": "312c87a42748d1bb8d6c873a285d95b19bbc2b2f14a880b39d722496a998b70a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_A1_W06_Model_Transcript.txt": "79d167fb6a3cb1ada4ca3cf808dbefb7520f1b0e76d20ee1a98b47c37f14d144",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_A1_W06_Pupil_Resources.html": "889c1c32ae968aaea6a52491b299f953c865ecf84ef6dcd0650ed94decd110b0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_A1_W06_Pupil_Resources.pdf": "0ab270c799b2784c3e0bcd35005accb1f7ea0335c36574987d42a5e77c0b050c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_A1_W06_Teacher_Notes.docx": "635e837bba40f40198026646c0587e7dbf9fde07ba26b4eb10b70dfcbd499992",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_A1_W06_Teacher_Notes.pdf": "72203e365731c5207973d5b65b0874157ced9bd96d0c6ab67fdbfceb4db210fd",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/Visual_Resource.png": "bb13fdc29e82f65160f9c935aa0a6d9520f9039e59733e5868eb9589154b9dd8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_A1_W07_Captioned_Model.mp4": "ba9ceb10d9437c51de41fa5e9a58a732eec258e094bdead0f3a62dfaa5d8c26e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_A1_W07_Editable_Pack.docx": "835f94cbfd91bc900fcfed304ad6bd4efeaf22dc67bbca1a50b83433d7ec823d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_A1_W07_Editable_Slides.pptx": "71a8ac2cca3d397d6f4fd63996ee31e087f06e858e4b6a22d381ebe8f6c5c7e1",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_A1_W07_Knowledge_Organiser.html": "0fa47ef5cff6764b2464f9069016e3ff81f313b1da079dfafe4c97da52af3168",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_A1_W07_Knowledge_Organiser.pdf": "65ce6f27d78188555d279fa3930b69f14db357894af6090217fdfd4b72943b23",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_A1_W07_Lesson.html": "2733e6f4942820ccfd5695fdfcdd099f3cec9b50030d72ba4892ff83cdcc5224",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_A1_W07_Model_Transcript.txt": "d5e59f50fddb03d19a81468d4cc014075b86477f0e6f7d5a27ed564dc3301f08",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_A1_W07_Pupil_Resources.html": "1947dc49f9faa663830b19f1de5bfbd816300abfe85082d6b08a5ee2907a3dea",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_A1_W07_Pupil_Resources.pdf": "940b3fb538ec6d0425f55eb44d47f7ec1aad66ec4feec732f17cd5240caf3e7d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_A1_W07_Teacher_Notes.docx": "e1cbeee45586c1de54031336c875daee8888b65d34dcee0f2febd723df43cc2a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_A1_W07_Teacher_Notes.pdf": "115c2710d62548dc871718fd615b41d76fe2ebd8b9399b104fc6bbf5a03c6805",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/Visual_Resource.png": "d89ab32c281d4a8296878ce5614ecbd7f942d1606cd1905fd08d43d653b6e609",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/README.txt": "b18e6a10681a2287090de194cb29747da642f300b3a25d7c11b3b45bcd814714",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/Review_record.html": "373ae723cf21fb6685146267c57286a8621b3d006e077c80339204f4d62dd3b9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/SHA256SUMS.txt": "9f9e515d8f2eb725c27af7e6064c0bf317ac86e0278944cbc19394acc5ae75f0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/START_HERE.html": "d1bfe78e81e93ec7b59841a85fdb50e7776944c687b940aeb750c1d47427ce3d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_A2_W01_Captioned_Model.mp4": "9084edd4a1209bf97b34a508c7c052340a2fb1e131dcb67ccaa177140e03512f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_A2_W01_Editable_Pack.docx": "2415e0b42fd215b81992718024bcac9d90ca99b221e59060d975f0415a1fe2ba",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_A2_W01_Editable_Slides.pptx": "1d379e28ac7779877a834a0cfe57000537e310aec798d664cf3232652603ecf7",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_A2_W01_Knowledge_Organiser.html": "81bda5a2570a51a25cea5180ad3922f156d3bc295958582f998b02b397409464",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_A2_W01_Knowledge_Organiser.pdf": "6736a598955f454a57f13994bb7dbfeaadfeecb8b1deb1368f0cd3155942a96a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_A2_W01_Lesson.html": "2d164f40a3312aa5e698137fa930cd83096392a49ed7890cf8e8672d0af5eb25",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_A2_W01_Model_Transcript.txt": "2bda6800ee5b242396d3783c589bb40a5fe98454689a840ab428a5b8409d5e16",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_A2_W01_Pupil_Resources.html": "2f94340e15b9d25d09413ede10fd505a5f44dc8e6a00575482bf309b58cae647",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_A2_W01_Pupil_Resources.pdf": "944d331ee8d0d0eb1ed1c0d7c7818c1600446f818391cd6cd9545955fce8cc4e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_A2_W01_Teacher_Notes.docx": "980f745e463e945b6a43a42e3c63c519038051606c2357da8f5c8398a6bd3b55",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_A2_W01_Teacher_Notes.pdf": "7a256d35a3207953ce09fb99f84b9aedb375976d380d9036549e29158c9b2e7d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/Object_Picture_Choices.png": "d812ba11ba11632878dceead3e2fcc015f9c12f52937f69015578a0fd19bd2d5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/Object_Picture_Choices.svg": "00d6020a1cddaa6208daef94b77af7d471c8dabb11a0c1906a1b243ff11100ae",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/Teaching_Visual_1.png": "be2ff7a3e6618d3ef87c0b5372aa3189f3e2fdc82624a7da30b62db7fc4461ea",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/Teaching_Visual_1.svg": "221096217f280d56c29c28d3dcdd467f9bf39c3507bc8920ea3a3c005cb13495",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/Visual_Resource.png": "7ebbf1b881fceadeb6fad27b5cde908cb866634b82156a2076c8c774669c1c93",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_A2_W02_Captioned_Model.mp4": "3744efff27f3a5bc1350c42376c7e209504a4f3461b4dd762ac740f184c227bf",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_A2_W02_Editable_Pack.docx": "7fba91bdad83d32354b39a6a462c82e968cfebfb2ae05563ea0da679afca06b4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_A2_W02_Editable_Slides.pptx": "613b85507c959662402f78677ecd74715e872fcd5603517fe7fe1208636d3c65",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_A2_W02_Knowledge_Organiser.html": "6b5b85826974fe95f2bbf556bb3661a434ec1ec19dc2c8726bb6e0e1b9f9e2e2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_A2_W02_Knowledge_Organiser.pdf": "1e88f8dfbd20240341f2a76ed54de71492b0988dd39260940d45bc3fa34580bc",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_A2_W02_Lesson.html": "731e0d63b0228c796b4331eec73c9c16e4b6a0dd2618c1ed856668f28f66f365",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_A2_W02_Model_Transcript.txt": "e505d6426c3fc130f19e68bdb56fe433d9831bf5805db912198f3f8c39da449f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_A2_W02_Pupil_Resources.html": "d80a6df84dc99137d15e6ceeb068a4ee3875889dbfa14b120498a8abb8446a4a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_A2_W02_Pupil_Resources.pdf": "0beff65583f23dc028c553f6d1306c0e25a734b0c9624a92dd2316d66451e12e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_A2_W02_Teacher_Notes.docx": "29de803b6fbd92500f7cef78936adea0daf1d77b7717364aac46d2c6cac40c3a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_A2_W02_Teacher_Notes.pdf": "5e5a7f5362fb028be126d96660b2da835535a2176ff5078c047b2eff19881259",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/Object_Picture_Choices.png": "d812ba11ba11632878dceead3e2fcc015f9c12f52937f69015578a0fd19bd2d5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/Object_Picture_Choices.svg": "00d6020a1cddaa6208daef94b77af7d471c8dabb11a0c1906a1b243ff11100ae",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/Teaching_Visual_1.png": "be2ff7a3e6618d3ef87c0b5372aa3189f3e2fdc82624a7da30b62db7fc4461ea",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/Teaching_Visual_1.svg": "221096217f280d56c29c28d3dcdd467f9bf39c3507bc8920ea3a3c005cb13495",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/Visual_Resource.png": "223871c71f76467c6fa3c367a4a96c45292a6bbf8a4907e5ac9c08365a071504",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_A2_W03_Captioned_Model.mp4": "b67ed5104d9471577601a4de3da51698235dfd450adf90a8ac46c9708353be5f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_A2_W03_Editable_Pack.docx": "389667f500756316a253a2a964fd0b3bd286a63b4dfd0b4b1662558c09e2f7cd",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_A2_W03_Editable_Slides.pptx": "fe5b001f1edaec31e89636b2173d3338df1ce817f85f3a8865ae2777d9474306",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_A2_W03_Knowledge_Organiser.html": "ed68c9b29ff4d2d778433eecd36ed869b6bbf7b38094974e6ab0d34b89d6617d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_A2_W03_Knowledge_Organiser.pdf": "bc4f1fd48cf63be0b5740ca4d6ce5949fe2936f3641181ea5afd140a83180919",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_A2_W03_Lesson.html": "a0cc2a8b87df7cdcccb9beb773adb052e14724c3a50ed9bf1afe5e49c3404e34",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_A2_W03_Model_Transcript.txt": "f736b0498644fe978ef03abb5395e018846f122f7396c7c5155af5427d844631",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_A2_W03_Pupil_Resources.html": "e15a91a5a195ff42143f342582f28fdb648b2cc26134be1b2894a12ee1b6ea1e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_A2_W03_Pupil_Resources.pdf": "4181ed183575a8ccea4dc2da1cfde25312d0c3e35eb19d379192f14c195ac01d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_A2_W03_Teacher_Notes.docx": "93aca1ac409b58a6f2d0f69df49c2ed74ac388271e346bede16fc93acf33f61d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_A2_W03_Teacher_Notes.pdf": "8536ee7f59b8b23df3a1280c2190ce60febfa8d0d1f1b6632ee6ffab467498ea",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/Object_Picture_Choices.png": "d812ba11ba11632878dceead3e2fcc015f9c12f52937f69015578a0fd19bd2d5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/Object_Picture_Choices.svg": "00d6020a1cddaa6208daef94b77af7d471c8dabb11a0c1906a1b243ff11100ae",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/Teaching_Visual_1.png": "be2ff7a3e6618d3ef87c0b5372aa3189f3e2fdc82624a7da30b62db7fc4461ea",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/Teaching_Visual_1.svg": "221096217f280d56c29c28d3dcdd467f9bf39c3507bc8920ea3a3c005cb13495",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/Visual_Resource.png": "b4ea4a4bb63070e345a1485ab6d9a1817f892b4af58d55d7a4115eeb049b5c9a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_A2_W04_Captioned_Model.mp4": "7cda9e42cb3b340db7883f979b35aeb8813e2c1dd4f2b3ca2d0b1fb9f46e179f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_A2_W04_Editable_Pack.docx": "7e3e97e02c0bfed8325e92a2abb359ad06390b2d75c20964d6756c07d0285813",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_A2_W04_Editable_Slides.pptx": "a0b56cf363bd6a8c1b0e87c7310d1314eb387255927c8f293ca4d3e1a9b85659",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_A2_W04_Knowledge_Organiser.html": "06b5795f4d8678ba1d834691eea2152ef972e3c5a685febbdb578b231f6daf36",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_A2_W04_Knowledge_Organiser.pdf": "88479263a41ce25e85eeea88e8655f2b359bf0ecd90ec9db562b3f9c121e206a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_A2_W04_Lesson.html": "900624dc192d56503a4e7a5af6d4e8a890e6acf901f480f0e595d5f68bf19c89",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_A2_W04_Model_Transcript.txt": "fc690f016a1bf0e3f2509eda5c1d5b83470a8bce5a2a3e9b2774bfc0c2fd9c60",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_A2_W04_Pupil_Resources.html": "67868f02b02a8ee4922864cedf9b02bc0c646e2518df12a097fc8dd450b6b680",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_A2_W04_Pupil_Resources.pdf": "e1a2c46f02b775eed165749207f8c505995923db3c33cc52f971815dff5c76ca",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_A2_W04_Teacher_Notes.docx": "b9ca52ba57e312b330d4c45d3a6a70fb94269f0c207970ef72575dd47fe63457",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_A2_W04_Teacher_Notes.pdf": "ad5145d7d94a7fc8bdfbe360ccd90c9bd1e166ba2c5bd33b9f2279ad0cea35e2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/Object_Picture_Choices.png": "d812ba11ba11632878dceead3e2fcc015f9c12f52937f69015578a0fd19bd2d5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/Object_Picture_Choices.svg": "00d6020a1cddaa6208daef94b77af7d471c8dabb11a0c1906a1b243ff11100ae",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/Teaching_Visual_1.png": "be2ff7a3e6618d3ef87c0b5372aa3189f3e2fdc82624a7da30b62db7fc4461ea",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/Teaching_Visual_1.svg": "221096217f280d56c29c28d3dcdd467f9bf39c3507bc8920ea3a3c005cb13495",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/Visual_Resource.png": "2849be040cc2fe6c05182426edfa6f57baeedf19de2a37051a94a8dfe28e862b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_A2_W05_Captioned_Model.mp4": "8831e6900e3665bd0d1df12e7b1fee37ad22c9d78665f1e1bddb8eb22a0ef618",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_A2_W05_Editable_Pack.docx": "e27b56e63e243c6ffd03fc00db2227d68f8a22555c1aaa4e2a94358864bd346b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_A2_W05_Editable_Slides.pptx": "c903c25908b0a7aad9ecfc7efd5ffd35ee1862f6ad21ae9bd1e53604154d92cc",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_A2_W05_Knowledge_Organiser.html": "837741e06bac2a6209e46f9eb8af8d9fcad4594b969ea3a80369a236074e88cf",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_A2_W05_Knowledge_Organiser.pdf": "633cd8b749d51b3a22cf006ac28034219a9d2b3bda4cc200b81fb09406fe066c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_A2_W05_Lesson.html": "2d0ea7d27f98ddc23856dc09b51860bd5bede4ffa35696e189097d239941adb0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_A2_W05_Model_Transcript.txt": "03ac6efb1b7ca60ab55bdd7e38b3a0eaa9fa7178d38d7267d987e1281c93bea8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_A2_W05_Pupil_Resources.html": "4836d20ff08d25aedb565d5714744bbf890bb3a7442a615953dfd41a056d7996",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_A2_W05_Pupil_Resources.pdf": "d7ba5bb6ef562260e14e35f61e52491fcf80c16adf2b4e55a1834e23003de59d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_A2_W05_Teacher_Notes.docx": "b208368a7254b4c345eef6c6b18f4a183b85c71b911d2611729407890364b063",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_A2_W05_Teacher_Notes.pdf": "a3c5fc3d42ee3ecf069adb155f82b874b8cac458a1fa62bf22f39e33592d073a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/Object_Picture_Choices.png": "7c415d2b15a988b6b0d8651f4e0f18589a54dee80cfc15d1134f2443ceb6086d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/Object_Picture_Choices.svg": "9b87480c64333262f50001b921d3bb94138843d8998598caa704b71268604042",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/Visual_Resource.png": "1b888eb911e2885e2433eabc6c147731c04c47a0bc522b6e2e8c33485b350df2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_A2_W06_Captioned_Model.mp4": "cd0034c6b1e1924831910107680a57b0ae308e8d5c0814f78a35fa437b59921b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_A2_W06_Editable_Pack.docx": "475298a1edc9dbfe34ed87caa3c5493aca554da39e17199cfc8c9925a1e84695",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_A2_W06_Editable_Slides.pptx": "a1cd8de6fe0657b99d4820581ee966a8a7e152f6eaa458174d8c6a53587fa4d1",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_A2_W06_Knowledge_Organiser.html": "5e25c241294afe5ec6d1234442426420b7c9a56a321530e220c6755e11dd6e39",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_A2_W06_Knowledge_Organiser.pdf": "4fe37e7005dea126c40f981476ff631d65669b9c74fd549313478962ffa7da9a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_A2_W06_Lesson.html": "3df91513d90613ccd96d69c58159365ec561cd98e0d29343b900ea3c718bae40",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_A2_W06_Model_Transcript.txt": "326c8b151ded3034f72f04cf7ff7e8b3f9ae4fdde943b90f2ba93acedf664c0b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_A2_W06_Pupil_Resources.html": "f955c8410f3426806df8b14f401dbe566c984af04873f5f624b6aa8cfbcd5be0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_A2_W06_Pupil_Resources.pdf": "0970bbd19a61054e0d98391683eaa1b53e895a464e557a6199efe11f01299e22",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_A2_W06_Teacher_Notes.docx": "0c2d5d5e92e8248fedab6d2a70964a1d5482b6a49c16e943efec9d7ddaf10174",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_A2_W06_Teacher_Notes.pdf": "c1cc700d29532cbfefeff5ee4cd79cfda62d5251b3da3fc8a0e813b3d6a62ed2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/Object_Picture_Choices.png": "783137c05ebd3688de815c04e9aeaebbe7dd21d6272661e9c6edcc91c0ebaf65",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/Object_Picture_Choices.svg": "c640df990e9362dc8a2a5beda99647d54041eb05e11467472d9c5c6c8000f725",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/Visual_Resource.png": "cae206dc8a100d78681eddd3ff95311eab69e0951e9b9430b3910050b4096aa8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_A2_W07_Captioned_Model.mp4": "a9ed90b2f7d317c0fc19871bd99d60cefa2c620604f12927f378fdecdd64186f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_A2_W07_Editable_Pack.docx": "db6f67bb1a1a9d23563a4a4040e18b1eaed792b97b371e4d5be738df96a83cbb",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_A2_W07_Editable_Slides.pptx": "923a88c1dd73e3aaea2a9a9afc3cea4c8de4100a802db56e5b72539ab9da3da2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_A2_W07_Knowledge_Organiser.html": "96476628024010693b2a2a19d2a660abbea03237637de686b553ef3d1cc026ef",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_A2_W07_Knowledge_Organiser.pdf": "c1ac4059df9462c28197874630594138f885b164b9acd9cc2cefa6b5642b038d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_A2_W07_Lesson.html": "68bb9c042061f46e8e5affe17575e39c60527be9e48afe189390fe14259817f0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_A2_W07_Model_Transcript.txt": "5707d54f1af436f322fe20e9937369837e5027a64528874ccbd95c939909286a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_A2_W07_Pupil_Resources.html": "d601405c364e2959e6d3585f21b5666554d65d89e1a89c133e05506b7316a384",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_A2_W07_Pupil_Resources.pdf": "3653a287f442b3b1715e447ad2e13c7db5c437aa6ed51962e09c01603861074a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_A2_W07_Teacher_Notes.docx": "cb4afe797544012f912710316cbd8f3aee424a730e99d790113e175c6344d752",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_A2_W07_Teacher_Notes.pdf": "00409bae938202f3389b1b40372963410ff0440d13aa66872549873857a79de2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/Object_Picture_Choices.png": "d812ba11ba11632878dceead3e2fcc015f9c12f52937f69015578a0fd19bd2d5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/Object_Picture_Choices.svg": "00d6020a1cddaa6208daef94b77af7d471c8dabb11a0c1906a1b243ff11100ae",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/Teaching_Visual_1.png": "be2ff7a3e6618d3ef87c0b5372aa3189f3e2fdc82624a7da30b62db7fc4461ea",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/Teaching_Visual_1.svg": "221096217f280d56c29c28d3dcdd467f9bf39c3507bc8920ea3a3c005cb13495",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/Visual_Resource.png": "d84b0bdbd26c960196117cec7152c0cb4ebb55c9b18a7ec81d95bf3aded1d528",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/CHANGELOG_Final_2026-09-19.md": "36182a18bbcfc41e67104cf7998bb17ad9d7b0011bb2a48b888ea7654cbd4113",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/README.txt": "b18e6a10681a2287090de194cb29747da642f300b3a25d7c11b3b45bcd814714",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/Review_record.html": "a1fe27cc3a4ae116bcb071ac4c7ed2aa075f718f34f0fc65c1ed9dad24ba8809",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/SHA256SUMS.txt": "b7a6bc6e2a2a92e17cc0f6f1a48bcdd45b98f70ffbd572300f3aefe060eacff2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/START_HERE.html": "42df5b8b8d74c5f5215eba84777a1935ccf8fb6ff771ea60a8a6a92cd3bfda7d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/CHANGELOG_Final_2026-09-19.md": "3d7b38deb4886748e126ac3b0b2dc957e67e678d94c89944a486d6aba1a4f6db",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/GROW_A2_W01_Captioned_Model.mp4": "8482ac836e210404376bd9f25ac92e43a76beaf7f167731c0513a86169065c68",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/GROW_A2_W01_Editable_Pack.docx": "e0fa0dc9e6cd867138479f4874ee517357164d0178bf689fb2d4d0288df37252",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/GROW_A2_W01_Editable_Slides.pptx": "6cdaf14c54171338488b0e4ecbfd8764be9f50634d8655ff83abfab3e08537b3",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/GROW_A2_W01_Knowledge_Organiser.html": "44168495b44f4953dc4c93e03e0e0d35a0a26eed22f6e420477561d6c2ee4183",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/GROW_A2_W01_Knowledge_Organiser.pdf": "dc5695ca056ac215bb773514352d91460f90a7c2f7fcf2d2479155210b4a68c5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/GROW_A2_W01_Lesson.html": "ade14f88b6d6d891bc3b64220ef20254066d586ef2f76ba619d4b185c241d492",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/GROW_A2_W01_Model_Transcript.txt": "4bc35f2d54d6ea57838867d8de18aae344d17a3405d9d00c4eaf6c262b913d01",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/GROW_A2_W01_Pupil_Resources.html": "7d1f432718ac746ced50078e48ebeddac6d0d15c9bf15c4315c3e24b866bfbe9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/GROW_A2_W01_Pupil_Resources.pdf": "67013b930e9e3d96d3af92c7210c72895771dd83f6c93417b9f3ce56727ec60c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/GROW_A2_W01_Teacher_Notes.docx": "756cd60cec343e954d0fc131b4d833491b1c2da1fa6898e52f6795d0dcf4681c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/GROW_A2_W01_Teacher_Notes.pdf": "c3956858c5fa637609d3f748bb0b47ec087ae89601ba82f30b8679d20f38f129",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/Teaching_Visual_1.svg": "761079525b882bce3f95c6072d39ee6f8670fdca8396720b0347f72bbabb96df",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/Visual_Resource.png": "ff9a7e2bf27c4e289a514f3216165e92d4e1bd6a2dcb89859fe3a531c7c0d8ab",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Captioned_Model.mp4": "894b883af47030d2bfaf4c0554bb47f7f914c2af54bf13c24e31522511404223",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Editable_Pack.docx": "ca54c35a67ccc637c793f04f6a7320f875b65bd1db0a8dcc325a48847c2388c1",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Editable_Slides.pptx": "d77fa052b983c47448d0e3766310f0984ec145add636a14007d6503469c7db5c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Knowledge_Organiser.html": "80b14b1b2689fd7e17caa1cdeb89dee260a971fa648003e69461c008fe104318",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Knowledge_Organiser.pdf": "438e88024c6b2da1dd5432251ebb5bfb82f721ee70a3a1409457c51ae8144e87",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Lesson.html": "6f604503052a58d610e1967be727c129d8654270bf284ac3cdfe16485b8c315f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Model_Transcript.txt": "b8d589421def718c299ff1f1c31c8c5d500084e56c03028f300b86e0d3f7a600",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Pupil_Resources.html": "a4cf0388d34187eb36a3251082056c9565930e41954d416939fee07e5e9582dc",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Pupil_Resources.pdf": "1bfb5814b74d150e50e3a6c26265d23203d8461151971ef1ed44e25486541576",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Teacher_Notes.docx": "02aa59aabeebc74ba9bf756bbb1ca072bab47fb595316c6e8f2405fadba912c8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Teacher_Notes.pdf": "7d6deedfe478048da954d9cac6b3c85f0b4df08f5b6478c84b93d15be4593c74",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/Teaching_Visual_1.png": "d265cc3f826a81fffa5dd5c83b4f7aba856ebccc01b2959dc1d76d06c7f965de",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/Teaching_Visual_1.svg": "dc53a18458642bc88affb55a98a602cadb30bbda471d654f477a6182d15f8206",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/Visual_Resource.png": "12a5ee602523eb8688a4adf0b439b4450d78c317c08100133718a80332579fff",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/GROW_A2_W03_Captioned_Model.mp4": "4078dd970df824c5bc28c0c6a16c7da69dff894aeb80021533b94f1d36b62259",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/GROW_A2_W03_Editable_Pack.docx": "67549f1d4669dbbed5a8bbafb8c1ae1c82063c681fefa33e497cf2b5437d1d0b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/GROW_A2_W03_Editable_Slides.pptx": "d95d93f48b6edd24f69546d3fdc7c7182bf74c7bcae006b8351b1dfc1326dbbd",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/GROW_A2_W03_Knowledge_Organiser.html": "fe312a6de96b5d85973bfd7f75ae3a592ab3c284d69ab7b2cd1e1b4595071a08",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/GROW_A2_W03_Knowledge_Organiser.pdf": "990fdc498f655665a82ae6e36638f01eb9c6a1697a24801154cf603232d4a5c6",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/GROW_A2_W03_Lesson.html": "a70bf1797ccf5ab3b454ea6759cb1b1510a30481a9a8acbf821112a1a32481e4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/GROW_A2_W03_Model_Transcript.txt": "07617241c7225e0c856117ed4e2d69329fc184951607025d3e8d190d6183c194",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/GROW_A2_W03_Pupil_Resources.html": "4965b6f2aec6570127e188d208cc03db05ad28e6e9e2b705f37257709a4d2729",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/GROW_A2_W03_Pupil_Resources.pdf": "2172bdaabe3b04ba2add99288c8941cce71c81bfdc5d8f36a97508354c2cf5c5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/GROW_A2_W03_Teacher_Notes.docx": "8fc34b227067406edef1c0d6ada1528bc647cf0aa461d6f2da91b69667b90e95",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/GROW_A2_W03_Teacher_Notes.pdf": "b3729875002b1a72846dc0f734e846bfd46147b5612e8d0852b6fcc8889bc07c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/Teaching_Visual_1.svg": "761079525b882bce3f95c6072d39ee6f8670fdca8396720b0347f72bbabb96df",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/Visual_Resource.png": "5e89fabb72439f213186e42fbc34519f4f9587963b486e063e3dd23e84691d23",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/GROW_A2_W04_Captioned_Model.mp4": "3da1b0bd9aa27da180d501e4a497eca8262a77f8e69e8db664e9c8d58363fb57",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/GROW_A2_W04_Editable_Pack.docx": "10215c4251dd01e49ca1a30383020a88e1de483f0dd351e70301936e05d5482b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/GROW_A2_W04_Editable_Slides.pptx": "eec147b699a2cf281cdb9dc2716c3e5c4ab05814dee36c62f64b765075383aa3",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/GROW_A2_W04_Knowledge_Organiser.html": "5b29231039dbb8cef5ab4c79fb0da8c3eba8cbde7bd8c09857a570db90cd0cd1",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/GROW_A2_W04_Knowledge_Organiser.pdf": "ebb28a5f5669b61e47c49e1fd6d0dccb06de8fa63d9b64eb7974120e2aedd43c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/GROW_A2_W04_Lesson.html": "e8c3880a7f82e06d19c16f2c4c3dddacd70b076ad133d02a483db85cdc55b214",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/GROW_A2_W04_Model_Transcript.txt": "cdd63a63ddd9fe9981d5b5c3f2c9ac96a6833a01ee2df4dba41ecd9419021858",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/GROW_A2_W04_Pupil_Resources.html": "c0a678923c6ba0fdc9bc469ac3fb048652cc7803054b18f2539c8e8a9a91211d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/GROW_A2_W04_Pupil_Resources.pdf": "b3990cbcd16608aea563858a0b24770bd88c3e9e92ee32eb63274262dfb04901",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/GROW_A2_W04_Teacher_Notes.docx": "5d11b2be0498402141ebcb97e3a759913fb01375a38901fb72a0381298227065",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/GROW_A2_W04_Teacher_Notes.pdf": "2ab4d48d445cd438266140b0e30d8d508e213b5e8c0161ee28c8347fb7f00d4a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/Teaching_Visual_1.svg": "761079525b882bce3f95c6072d39ee6f8670fdca8396720b0347f72bbabb96df",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/Visual_Resource.png": "23083a32f38e98b2cce00ded51b82be102adb7980ea60dca30a2e4bca57aed45",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/GROW_A2_W05_Captioned_Model.mp4": "42cbae34575ead3d08a4c2de95f81da104945c0af466264ffa3f87fc2150679d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/GROW_A2_W05_Editable_Pack.docx": "bf89579a8ca73d4b64ff9c0f3d66c7a6f356966e41dfea5c02c395f5978f924b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/GROW_A2_W05_Editable_Slides.pptx": "397d08945612ce5c58a1b649b77315a11d88863ff5b3c7252b5dc0dd80dc786e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/GROW_A2_W05_Knowledge_Organiser.html": "5dafda54502e5029de63d54d9cdf3323b2b6f728faf798fc5a0ae9e28b86198b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/GROW_A2_W05_Knowledge_Organiser.pdf": "57fb2a982a04c78620521e23adbd8481396cc1e8cf4e667b4764f4c09a11f5f7",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/GROW_A2_W05_Lesson.html": "608cfc88af462c35be0154957438285b348e239d9b49760d656323103149eac3",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/GROW_A2_W05_Model_Transcript.txt": "8f4624f46a61db02601148463b84f8bb3744ca54614835bde1fabfcdd1490216",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/GROW_A2_W05_Pupil_Resources.html": "88d9f6ea93b0ee35dbe2ceb5f0056159e37537a29826cce60481a29cfbf9a47d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/GROW_A2_W05_Pupil_Resources.pdf": "5147af97a1987e670fd79e626690b0011b1cd664fcb253f0c66f7066ec527a32",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/GROW_A2_W05_Teacher_Notes.docx": "bffb61d4d232012df5847c99250605978c8eaf23ab2d8a752dbf1b8bb9189f7f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/GROW_A2_W05_Teacher_Notes.pdf": "650cb110d4e9749b0d6826652d2f88f8104a54a66305ccc50f0372a3e55871c3",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/Teaching_Visual_1.png": "be2ff7a3e6618d3ef87c0b5372aa3189f3e2fdc82624a7da30b62db7fc4461ea",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/Teaching_Visual_1.svg": "221096217f280d56c29c28d3dcdd467f9bf39c3507bc8920ea3a3c005cb13495",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/Visual_Resource.png": "90699117452f27123b864837ffd6d2e8e1d16d8f62dc2486f4fea52e7e9180b6",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/GROW_A2_W06_Captioned_Model.mp4": "b1dcad707e455b2d596354e6eb1acb8d6291d4fe6ad7c2664cab77e41c1779c1",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/GROW_A2_W06_Editable_Pack.docx": "2c728c3d6e85e849fe7f072d9de2c63a9c31b456af4534c11d5a153db8aa84c4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/GROW_A2_W06_Editable_Slides.pptx": "657726477bbb2d21467d28089dc7c4f061bd38a7dc47fbda8733d6ea32b74aa5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/GROW_A2_W06_Knowledge_Organiser.html": "585e6f74f9eb7d767ca70c73f325105cd0abea58d2fb29609c063d7693564982",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/GROW_A2_W06_Knowledge_Organiser.pdf": "1317cdcd99fa4da17d09961077ace1e2b1021c863b7b3b6e3a5502fe2f417ed0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/GROW_A2_W06_Lesson.html": "3942a4dd5aba3ae8cc6fef3509deee9b410beeff2785e63a930488eb1483641c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/GROW_A2_W06_Model_Transcript.txt": "2c27214d6b1620e54a52ffd583bb2f79e32f7c4f963a6aa337d322bcf9b7291c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/GROW_A2_W06_Pupil_Resources.html": "22a049fece5257e31e339fab5f45a465e889102050be126ca3b6c064b3c9e155",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/GROW_A2_W06_Pupil_Resources.pdf": "00eb1f05e129b52757644c097a94a6aec150c26784231bc220a39ea8e174443a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/GROW_A2_W06_Teacher_Notes.docx": "f6878ebd9820bcb8a6113440fe555d763bd02ae9068d684daf0598aea6c868a4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/GROW_A2_W06_Teacher_Notes.pdf": "aea4c3294d04861376a8d4fa4ea3f70d0aea9df2c4ae72c893bea3307980ae94",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/Teaching_Visual_1.png": "be2ff7a3e6618d3ef87c0b5372aa3189f3e2fdc82624a7da30b62db7fc4461ea",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/Teaching_Visual_1.svg": "221096217f280d56c29c28d3dcdd467f9bf39c3507bc8920ea3a3c005cb13495",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/Visual_Resource.png": "692e4fb04d4b4b3dabc9271d9a607cc558dbd40f6efea43ae167cfd924b18498",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/GROW_A2_W07_Captioned_Model.mp4": "32559930f02ae94dfd2ddd61f2e3d0751deee78b44cbd6302698e379dae13794",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/GROW_A2_W07_Editable_Pack.docx": "7401d0f22936c1a843b23682fa7e7dc6d69c2ae67a3dcdba53fd73c041568c8e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/GROW_A2_W07_Editable_Slides.pptx": "a434466d7b602a4877a32f4d75a5a9cd9faef22508f4d5e0dde5621c8821ae53",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/GROW_A2_W07_Knowledge_Organiser.html": "ac56bb65401bd2cccad486347b30794bd230f1ea6562e586b5e2cb342a1edb7c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/GROW_A2_W07_Knowledge_Organiser.pdf": "11b451c02bd40372943743d03f308d0e418acaf02647259469e8827b4307441d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/GROW_A2_W07_Lesson.html": "5666e3d34aff3f83b2214add2e7b3e6bf7f1b2b810ebcac3c789f9883a9f91a7",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/GROW_A2_W07_Model_Transcript.txt": "7125a1587fc235f733b42e6c29c522559c7dae792eb0940bb58af8fc7ef1f42b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/GROW_A2_W07_Pupil_Resources.html": "c2a4ae7e01eab702ac6c10879093760b76cfc0290a280a4540a3b1d0382b1853",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/GROW_A2_W07_Pupil_Resources.pdf": "0a5d5a1131dd3d6389a8e65f74f86fc3a27b43d47b383fd7d483ff3a524719c5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/GROW_A2_W07_Teacher_Notes.docx": "92c37d91be134bb358ca8ab682f6dd92adfc37a6950d97ed009569506fd64f18",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/GROW_A2_W07_Teacher_Notes.pdf": "ec213623bba3931f15f37e623c7c1e8e68b814203f0f1d84cf6a444e8b781cbc",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/Teaching_Visual_1.svg": "761079525b882bce3f95c6072d39ee6f8670fdca8396720b0347f72bbabb96df",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/Visual_Resource.png": "7e267e588365c04c648d485a79bd3e5c2e15c8fb9e148e36c16c3f10c41b4565",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/README.txt": "b18e6a10681a2287090de194cb29747da642f300b3a25d7c11b3b45bcd814714",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/Review_record.html": "38970dfa04ceaca640b809ef547793b87c45b2d97de4b79bec4434f9a9c9622f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/SHA256SUMS.txt": "340c594f5b4340d257b5db6b0fc86d0822da04623ce275f564313bc72aa1ce3c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/START_HERE.html": "ec788e244beb87d38f1e0f1a0dc38c78a1570f31e275215dc2e6708f48bd3b64",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/CHANGELOG_Final_2026-09-19.md": "58bb65645a3f7b5748861e27c85c77cf5c65d8ba883596289e4fec281dc969d9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_A2_W01_Captioned_Model.mp4": "3047c83ac90043c3d6c928eb17445b0ad87876a116294bb3dcb6fb4fe04c28e0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_A2_W01_Editable_Pack.docx": "fa7fafaa53a95909279ec69496a9b93d89426103071246e73a4dfaa22993de0f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_A2_W01_Editable_Slides.pptx": "19b395b6e1be91769848fc27880e6c829b9c303cbbace8984edfecfd8257243f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_A2_W01_Knowledge_Organiser.html": "3c2fcb5ae7888fed49dcfbfbe3369595e769c0074b2cfcd4db19d16c82c82abf",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_A2_W01_Knowledge_Organiser.pdf": "6c4663e3edb37106b72906351efc35e7a4ef2a3a0ce8ce0dd12a9ede3c2971cf",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_A2_W01_Lesson.html": "5429fe36bc079b89ac1cb21f68683900bac71b701d2554af85c5193c1d520b7c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_A2_W01_Model_Transcript.txt": "83d014d82e62d13af3284d2f7dd6da2ca8f12dd9018ecaaa5621223f68f91968",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_A2_W01_Pupil_Resources.html": "d8f8e7d6c7262de5a094058ce278fa1fbc357f2381d383b07cafb0b09e3bb130",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_A2_W01_Pupil_Resources.pdf": "f5b2182b598b252ad133e1259f1521a160190ed0bd2a0b876e56faf408f19ad1",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_A2_W01_Teacher_Notes.docx": "8c99849df8f8e670de459845af317abb28a25318d3ae24d90f94b09188112b58",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_A2_W01_Teacher_Notes.pdf": "a0740d0a48c56115a74868adf14087ae9eb6fa1677a4eb14219064bd7024938c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/Teaching_Visual_1.png": "d265cc3f826a81fffa5dd5c83b4f7aba856ebccc01b2959dc1d76d06c7f965de",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/Teaching_Visual_1.svg": "dc53a18458642bc88affb55a98a602cadb30bbda471d654f477a6182d15f8206",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/Visual_Resource.png": "f4f5bdd91d9870f91588fbf52c6c8e2983bee165b281fb14ea6a8261c361bff5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Captioned_Model.mp4": "14cebdbe370850b75a340af80467f5d4d3028638cb04fbc4d9c21fedcfbc9d78",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Editable_Pack.docx": "a0df52e0ec5632882f3219e2366c35fa30be441be75be58acd1edc3f76212b43",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Editable_Slides.pptx": "de50a4e19d107ab451abd385e1c16bb0fe0bfa74f2c236e7cfa5fddb079ecaf4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Knowledge_Organiser.html": "e010399870eb6da4a875bf919d847bd3891424412b626aba3b4aff94b525aa6b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Knowledge_Organiser.pdf": "cfdbad95978255b42fd27271b424029a6c66a352b79a43b1b3023582ca1e4238",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Lesson.html": "149fcbbd07776f5ec8a7ba59bdda3ef026d79a9cba8fee0184302bf4e9555a23",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Model_Transcript.txt": "7e0db2fddc2b127e58b02bf7f8ab5ace4a1720c41b8475ee1492e70ad08f9234",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Pupil_Resources.html": "d5d43a3c4c90b63a6be812f64ed74608161e67489bd90bd233d831314e6ad334",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Pupil_Resources.pdf": "56efd36269cfcf2407daf24867d5b3c57b182df3eefa67f56e75931d870f466f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Teacher_Notes.docx": "d7bce7046c8b2b3f91d1c716c4ba54d9fccf14638e8e0440ad0795695b1ea133",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Teacher_Notes.pdf": "0806a2cc6bd838be5b51887e7efbd9886d7817ff9ae9131e9eaf90276093ef3f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/Teaching_Visual_1.png": "278eb4644692cdb2fc8efdd36f8f929dc61830a0cbf29be4f62a02af8d40a19d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/Teaching_Visual_1.svg": "d4d545027bff75a1700537078ceccc15505df787964e4f8a09646b590b29e468",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/Visual_Resource.png": "35c89a64a4b1a7d199d04431cb20f43ff85283c523e9a5382ffd882fb051160e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_A2_W03_Captioned_Model.mp4": "e4711c3a644460831c71d63cc02eb28ddecf7face0e7bf84e34fddf06ef47ce4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_A2_W03_Editable_Pack.docx": "9e962a79f982ae0f11d8d2d87712252f8568900d14d81764d4e491795a93c0d5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_A2_W03_Editable_Slides.pptx": "d55b6304a69805d9ca1ebb7e2c5c5eb41cd91c06eee186cb46eb7aaf09b5b8e0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_A2_W03_Knowledge_Organiser.html": "a19f8f2ddfc053b0362ea2a2fe1fb2dc95641d013f9be05eddad7ce0d511970a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_A2_W03_Knowledge_Organiser.pdf": "4d43a66d50a559642680e0df9704e1c3aca048302b3edf8c83f6c06175c4061b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_A2_W03_Lesson.html": "0cfeae160d2205ec8a81c3e1122faaf440950cf2ff83a21084b11cf07cf9ffb6",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_A2_W03_Model_Transcript.txt": "d71ff39573142d344a71c7c752cec31c3b3fc4bd4b10be7bb77393906079ed1b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_A2_W03_Pupil_Resources.html": "022d9280f85e9147b88807e6e513afd5a84bb161a856241fcfb77343a69c423a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_A2_W03_Pupil_Resources.pdf": "ebd133a9a9a172984a5bb2841669d71243e037f7b552d2ef03b7cb8f89fd7956",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_A2_W03_Teacher_Notes.docx": "d4597ca0029b22db997772eb9ad28c5fac7d3fe34f5d8271ffcae016cda3be62",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_A2_W03_Teacher_Notes.pdf": "d462a6d5234ab7cad25221745c12e695336b2a448b2b08e043b57be2ba32180e",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/Teaching_Visual_1.svg": "8f7cae4fa423ab28d05244d1b48c17505d5e72e2952b76f8aad7069786f3c520",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/Visual_Resource.png": "98686e31fdfb46c1038281c1519c314006a798929a37d5d545e0db290f6503c4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_A2_W04_Captioned_Model.mp4": "1e59996e99bdb2cfee55f0f8f2269756b9f1c64d13e4d7599176760b15136ec4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_A2_W04_Data.xlsx": "909f2e0828553c786f6b4724b380f0b07b9b43c35ebff9fc11e71cc27b4e3609",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_A2_W04_Editable_Pack.docx": "ef4a6df930cf4e35b7c61dcf61d58512add92e93bdee711485b38250780b57e0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_A2_W04_Editable_Slides.pptx": "48ffa5d7d6fc1e7e2c728d7eaaa83a2c0a805a9382ff11439c14499b2c9bf8f6",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_A2_W04_Knowledge_Organiser.html": "30dceaec6500fc09db1315773a7e0007753a1ba81dfc244673969aa13d36b80d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_A2_W04_Knowledge_Organiser.pdf": "4a6e20580891d056e485653a8a719b59972854daea5f5332990e1b03e419ab24",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_A2_W04_Lesson.html": "1739ff443285b2c69104bbd404fbc68301e718316068ad94d20d6219e8b67dc7",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_A2_W04_Model_Transcript.txt": "fc03d79576379dc7923f89543ea61a5c171c54e6022a3150359abc3717f7227b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_A2_W04_Pupil_Resources.html": "787ca387231e9ed6d63730dd2494b8e178d3459ffbb95755c77aa601b681cf2c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_A2_W04_Pupil_Resources.pdf": "0886e164277c851f6836039123f0b5027e789c0b46862118c1f8401e25b35927",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_A2_W04_Teacher_Notes.docx": "76e247bb9d64e2a4b75359c828deb2f3512e87346240a61c0789cfafe7d68a7b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_A2_W04_Teacher_Notes.pdf": "778e5b1fe5dbe128f22284c044daa3c72bf46e62fd8dfd1d7e02298ae71ff9bf",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/Teaching_Visual_1.png": "278eb4644692cdb2fc8efdd36f8f929dc61830a0cbf29be4f62a02af8d40a19d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/Teaching_Visual_1.svg": "7220d6a5b075a5d496df91fb2516c2c5a7adf738994172b16f1710bdae2842fa",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/Visual_Resource.png": "93a0dea0431170526c0ee234acb52762b0734b90e756c99195446d3becb8638a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_A2_W05_Captioned_Model.mp4": "93c279aed0e41e01948aff24fbae612f7f4ddabb2c7049c69cb8ec60a1cc2c1c",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_A2_W05_Data.csv": "2af25a03ee9fdd61057777f7e435166fc6e70aa933580c324ca9decd1a3bca45",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_A2_W05_Data.xlsx": "dc5b539925e5f095518753798c18dba44bddf2ba8312b98fae7ff04e59c8c8fe",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_A2_W05_Editable_Pack.docx": "92252fa8c43ce014f8eaaaf7027ca92c9b7c8b476782126c4a0b455ef4d39cdb",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_A2_W05_Editable_Slides.pptx": "ead4838cb17344f398b1cfa275902bc958ebd01cfbb76020dc863c47dd9be6a2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_A2_W05_Knowledge_Organiser.html": "07937614eddff16a97f183b0f61231031dcf568d50017eec74d8ae1c0b185dae",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_A2_W05_Knowledge_Organiser.pdf": "92b37dbe2acdcb0a6fd3542964281aa8e3bca839fcd76b0e69d28942539140c8",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_A2_W05_Lesson.html": "9e69e97f105f5b0b4fa8af7e4c3515a65ec8980277f1a5d160ea30957b8598f2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_A2_W05_Model_Transcript.txt": "bf578dd334fa060983087b58d96aba2004c434edd9e52ef75c1455f3250b7a42",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_A2_W05_Pupil_Resources.html": "72626bbfedee7f99b69c8fef7d81ce39f080abd194c87a31a5c42f3d528992d2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_A2_W05_Pupil_Resources.pdf": "f0c39c1f862a6b9c627a6bc72db3445902322ffe9a20205cd8b9d7e11e868ab2",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_A2_W05_Teacher_Notes.docx": "4126ae9c2c2801e594ea026b03ed23e465d12f060fb7ab4adc0f833194ac35ac",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_A2_W05_Teacher_Notes.pdf": "38a0f2f9a28eabe6078776d0b0b9483b2223d141b40dd86535da490d8b20bfe6",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/Teaching_Visual_1.png": "278eb4644692cdb2fc8efdd36f8f929dc61830a0cbf29be4f62a02af8d40a19d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/Teaching_Visual_1.svg": "7220d6a5b075a5d496df91fb2516c2c5a7adf738994172b16f1710bdae2842fa",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/Visual_Resource.png": "d46967d404d4e7cb9640ff1519f86f5fd8ecae43f510fe83bc41e23fcbdc6972",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_A2_W06_Captioned_Model.mp4": "c4e702f3f24428b9251ae4e5ab5146a416f4d844252561dbce30b0d41e0f201a",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_A2_W06_Editable_Pack.docx": "f92572737d7b65d8c3b2572ddecfc3cf2b3cff2bc3a462ac4aaa1ae384e7565b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_A2_W06_Editable_Slides.pptx": "4043dc97c8f61287c250260921498d404ab8dc01be1ff8c9fde3ee31ab7ae407",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_A2_W06_Knowledge_Organiser.html": "54e093d4342f089949016664c40c801b19cf2c8b8a89b53adfee92b4419fe845",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_A2_W06_Knowledge_Organiser.pdf": "2f49115f72640056e9cf6790ef87a5c9fa1055dc36f3fe212068b0a0277ec2c1",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_A2_W06_Lesson.html": "f76303ee29eef6d783274eb05e9269dd58e88b3840fdbd3e4207a551ba02f76f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_A2_W06_Model_Transcript.txt": "5431592ee988c404d878878a6a9f6894cdc53ae5a605d4658556e3c2a59afa25",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_A2_W06_Pupil_Resources.html": "cd6a7561836e5b66b427f7594219574ab1fbc0ec839435fe55ea9979ca84e6d6",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_A2_W06_Pupil_Resources.pdf": "ad4659284f352055cdcb7a34bd533f86b97ba45d0bcdd12d12bab022a65ad28d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_A2_W06_Teacher_Notes.docx": "aad8e498f75a24a94779aaf3fac1370344ba047ef00548509cef9e68d934b519",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_A2_W06_Teacher_Notes.pdf": "451549afe881b55f192dc89a68bba40689153537783d3d9c65e3caf568965188",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/Teaching_Visual_1.png": "278eb4644692cdb2fc8efdd36f8f929dc61830a0cbf29be4f62a02af8d40a19d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/Teaching_Visual_1.svg": "7220d6a5b075a5d496df91fb2516c2c5a7adf738994172b16f1710bdae2842fa",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/Visual_Resource.png": "070708d765f0a6727e7bbd30854aa96a5597b4e3127aaafbca000e721bc49dee",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_A2_W07_Captioned_Model.mp4": "12deceec41066f7cd7523135d31ecb77d00624848a29413b0bf856ba3e7f306b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_A2_W07_Data.xlsx": "beb5d001b03256bbba68331105f20bc03fdd25f7581a2880717c6de13a467ff0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_A2_W07_Editable_Pack.docx": "82ac811ebbf0b1caa8756b4f3c91f1d8340726072b6c8255c35796d9da503850",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_A2_W07_Editable_Slides.pptx": "5ac588acebc664b71e396156f340b1cd83d32fbf252a305f5a46ca2706b5f68b",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_A2_W07_Knowledge_Organiser.html": "f1d12f28872f9238e0b5529d664d07075332cbbbc4c533ebd3289fa3bdc8676f",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_A2_W07_Knowledge_Organiser.pdf": "24bb218fff6fae1a34bfe43a0d690dbd7b8b111e24fa3dde14f500aec66173c0",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_A2_W07_Lesson.html": "91c123854baa473656cb99329fa0a96f40f90f9aa6fbeeb57d6026c9eb68cfc1",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_A2_W07_Model_Transcript.txt": "03071f524f0462dbf3dc7e38e51c3db0f1306a3902468aa3e8c52daad1aa60b6",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_A2_W07_Pupil_Resources.html": "bed751aed5b75879aa0014a5c9bcd429f8f384d54b460e77da3023a2c7d72b64",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_A2_W07_Pupil_Resources.pdf": "dd6529129dedcd02bcf501484732cdd160ccff669b3f1702320d97bd908f97ed",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_A2_W07_Teacher_Notes.docx": "c3995c3cc8751d853e7fe48993ceeda0de24e84787cb3b7a8b99962dcdc77953",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_A2_W07_Teacher_Notes.pdf": "8cb0827dfd18dc55b6a38acd377c9cf12326fef8e56e47f1b94c59b7668ed4d4",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/Teaching_Visual_1.png": "278eb4644692cdb2fc8efdd36f8f929dc61830a0cbf29be4f62a02af8d40a19d",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/Teaching_Visual_1.svg": "7220d6a5b075a5d496df91fb2516c2c5a7adf738994172b16f1710bdae2842fa",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/Visual_Resource.png": "479a71a44960c5a03387618b29711aa4da72ceb9924a8a9ad2754c777e12f6d6",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/README.txt": "b18e6a10681a2287090de194cb29747da642f300b3a25d7c11b3b45bcd814714",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/Review_record.html": "4b51e22ce35487d04546050e814675d25c70c62e0fbafbcc44a64f53f7033ee5",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/SHA256SUMS.txt": "3c1f9b61b106d0d77d28999450e7fdc8375de0ecbfd51964fca25d20089bb5e3",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/START_HERE.html": "3c7a7d260e3d9f51efaa8917f42462b8dc110559522a17d8e1247f17bde41d26",
        "Humanities_Teesside/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/BUILD_S1_W01_Captioned_Model.mp4": "850854ca4463d88facc95cb077b1aee8a35765baa8e359665dcbbaf2d256452c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/BUILD_S1_W01_Editable_Pack.docx": "2512ebe692c9aad0f58c8b513a57fde34d571dfd298e588993e733c920663c37",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/BUILD_S1_W01_Editable_Slides.pptx": "fe2c80e43b7da41a2502b8503363fa83ccd29c39baecedcb2b2b7e61bbb36b38",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/BUILD_S1_W01_Knowledge_Organiser.html": "b397551699d448f2383816ee43d68ef32ec7714222818d765cb5b43fbbc3589a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/BUILD_S1_W01_Knowledge_Organiser.pdf": "712a6c41931a4d511354863ae5ba0a0149eb28aa1b5d7dc64caea7c6d969b404",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/BUILD_S1_W01_Lesson.html": "cda96d3a7135d63d060f65993829e995874b90bcc62fb15b5f80526acc876e71",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/BUILD_S1_W01_Model_Transcript.txt": "778960b2782113d2fed4e70674d08081f66d6827c0f65495b124577d7f804336",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/BUILD_S1_W01_Pupil_Resources.html": "050952603fd9ce28aeeb0b8068e3fd511230847374f0f5b035022e183a69a63b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/BUILD_S1_W01_Pupil_Resources.pdf": "74f7b3aa99c7cee49a9a0f2fe4b1e4e9451b1f8419c35abba4792ace09dfeadd",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/BUILD_S1_W01_Teacher_Notes.docx": "1f314ab20eaf5a33c59f33523f94e66e7e0bc95963b963a46130051fad29f1ca",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/BUILD_S1_W01_Teacher_Notes.pdf": "4caf243e08f8dffe4e240dab81185e6e193823a81423b185047515dc3017d579",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/Object_Picture_Choices.png": "ed68f67a67f92a3f4ec3a7ef95d3143976b7cc52c77bdd294dc9139837d3d71d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/Object_Picture_Choices.svg": "6e6f68be419a58038f55bfea014c7735658d988a4d2e0c8d19898f59a15b9192",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/Visual_Resource.png": "9d2a6bb27e2ab3b9e032a0df89c3b316a57348505d1b959e619abd6d2bae9df1",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/BUILD_S1_W02_Captioned_Model.mp4": "2d00cbd8518100b9f2cabbf8da0cc8e37238ebf69fa853d926b54fb014a59a12",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/BUILD_S1_W02_Editable_Pack.docx": "8716da6109ad8a969314556e0fe41a08bd89957088e731a7abf677ff217a9d87",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/BUILD_S1_W02_Editable_Slides.pptx": "50ecee41332dfa91e58b182cca59681f45af4f18ce08dd6b95965bbfbda31803",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/BUILD_S1_W02_Knowledge_Organiser.html": "fce29e59925845e23fc476d42e71998355165a9a6740497d0da1da2b4bd176fd",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/BUILD_S1_W02_Knowledge_Organiser.pdf": "edec25cd2f93b200ceeceb95dded43ea7c7b5ed4128becaea3240c2eda24bea7",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/BUILD_S1_W02_Lesson.html": "80ea4022f47d83032d8b4017c0ec794e6f24c7cc17620d2d9161d90cc06db86b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/BUILD_S1_W02_Model_Transcript.txt": "ec9e838b1de57560159dde170a9f5638c19c57a443cee559f04012aa4bd42f80",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/BUILD_S1_W02_Pupil_Resources.html": "e9f014aa23ece72c0072d6997c80c09be4c2971b0067fe634fb6eed6928a04e6",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/BUILD_S1_W02_Pupil_Resources.pdf": "39e6b017f8c8e1837f83f365a526e77b08915f9d8014533ea455469fb750a3ac",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/BUILD_S1_W02_Teacher_Notes.docx": "07ddde55f21d7a8a82651e54152c118b52d1b169b1594fbdc0039827acc98ba7",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/BUILD_S1_W02_Teacher_Notes.pdf": "f46be1c799ee459a2c4493835109b2822bbcc339630feadba21b34d9892fcc21",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/Object_Picture_Choices.png": "ed68f67a67f92a3f4ec3a7ef95d3143976b7cc52c77bdd294dc9139837d3d71d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/Object_Picture_Choices.svg": "6e6f68be419a58038f55bfea014c7735658d988a4d2e0c8d19898f59a15b9192",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/Teaching_Visual_1.png": "4325e8a9f30ddee1d60c48a84ffd855b3e7e3c14baf1550b78470bf2bb7486c4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/Teaching_Visual_1.svg": "be77de2677840464af652e8aad29cbce9b83ec8916b06e8b56eae750f762e7b4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/Visual_Resource.png": "aafd376fd8cdc05b84c0f48827ffb5dee3d8a030363ce3e9b6c67f670a7df4c0",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/BUILD_S1_W03_Captioned_Model.mp4": "9a56bf827adfbfeede0fc92e6fcdad23e7ba5bed14361506cc3c5f64c6ad1dbc",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/BUILD_S1_W03_Editable_Pack.docx": "4c2249d6f9c938e4d0c6cc588844e5a0eb2818d484cec6fb7cf85f5f5e2ab685",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/BUILD_S1_W03_Editable_Slides.pptx": "1307143dd9759de07a0a783ddb0b0d27184df34aabe2b207fb62389b9a227776",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/BUILD_S1_W03_Knowledge_Organiser.html": "8f62877754fb429b19d647a72962f12139c8d4813a0cafdde557e71e862fa823",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/BUILD_S1_W03_Knowledge_Organiser.pdf": "40fc25d00ec54c1f5c54c278d9994a72129d03786363307a034e819bf39709d4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/BUILD_S1_W03_Lesson.html": "19b4cfa5da196a971a478deaf528991ccd71220783061bee78b38f555a6d57a5",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/BUILD_S1_W03_Model_Transcript.txt": "af058261baaf0776afb441960ac78c05334a1ca4bc4dde523540f73b56abe76c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/BUILD_S1_W03_Pupil_Resources.html": "c21b324b1e26367470e9fd2530bd816a51012604140d4a77293b8d8311e6e57d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/BUILD_S1_W03_Pupil_Resources.pdf": "34b3d1ddf3412b168016d053a015defe311fc35bc303aae9fb78e920042365d6",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/BUILD_S1_W03_Teacher_Notes.docx": "011886cbc6fff424acf20b9b859ad08d9e1e0da3102f77848f9f77c8034d98af",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/BUILD_S1_W03_Teacher_Notes.pdf": "b5207b7dc2d9f98746ac0662a9cff471fdbd829a564f7ae837398314c5cb0205",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/Object_Picture_Choices.png": "ed68f67a67f92a3f4ec3a7ef95d3143976b7cc52c77bdd294dc9139837d3d71d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/Object_Picture_Choices.svg": "6e6f68be419a58038f55bfea014c7735658d988a4d2e0c8d19898f59a15b9192",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/Teaching_Photo_1.jpg": "cde4dc690052c1b0a658fd1e1f09c5a657086cf56c7fbc0bd1ed468ae3514083",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/Teaching_Photo_2.jpg": "6e1d3a6530790025b0e970213d76128faa258ffff9eac1cd8de510c734f60bed",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/Visual_Resource.png": "f5b1fd2925a731978098ba73062d6e62cac746d5c322f0405282690d5a57fbd7",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/BUILD_S1_W04_Captioned_Model.mp4": "755df89cf23b2e4b50f3789d067e7f6d7c339e557e18b0081d390251c6ef4bf5",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/BUILD_S1_W04_Editable_Pack.docx": "e3d4c8ce95e61baaabec5602bfdff8646bfecc8c7669182128653eda81f7f3cf",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/BUILD_S1_W04_Editable_Slides.pptx": "d98af69ca31f906bd681a356d123acee15f55821c1c8dfd119ec91546e906d7e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/BUILD_S1_W04_Knowledge_Organiser.html": "9e09cc02116165eb4db68edf63127cdb517bf66c4477d9247a49f50bcd0453ca",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/BUILD_S1_W04_Knowledge_Organiser.pdf": "f8e5c8f23a0424ccc0fffec524e59af4e8fdaba76aa51fb61640082217c2ce22",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/BUILD_S1_W04_Lesson.html": "3488ee267ea5a45c339c7a98b05a84db375142ab77fabbce6a7a73721c685fb7",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/BUILD_S1_W04_Model_Transcript.txt": "0ab3f74339335cb3a783497cf705c784faae249b2371c2b0d9d4666013808e28",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/BUILD_S1_W04_Pupil_Resources.html": "e9e937502845d9daf6c259d3f9ff5f36eaa6eb27c48143cfd58f2f4b0a6fd2a1",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/BUILD_S1_W04_Pupil_Resources.pdf": "6a47b9e49a4aafa1844afd9b3534d8616f72a7e37c92bcb8a92d783f2ca1bdce",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/BUILD_S1_W04_Teacher_Notes.docx": "dd23ec2151a240c8dcd716fce4f8265799b902a1d3c8f3c4960703425caa0963",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/BUILD_S1_W04_Teacher_Notes.pdf": "cc2aaa53e9ab99477c0dadb34428a5ce7a31c006c5ef3e2d9becc846465add03",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/Object_Picture_Choices.png": "ed68f67a67f92a3f4ec3a7ef95d3143976b7cc52c77bdd294dc9139837d3d71d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/Object_Picture_Choices.svg": "6e6f68be419a58038f55bfea014c7735658d988a4d2e0c8d19898f59a15b9192",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/Teaching_Photo_1.jpg": "cde4dc690052c1b0a658fd1e1f09c5a657086cf56c7fbc0bd1ed468ae3514083",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/Teaching_Photo_2.jpg": "6e1d3a6530790025b0e970213d76128faa258ffff9eac1cd8de510c734f60bed",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/Visual_Resource.png": "1df43088af22a4fb672eb37b7f0083e0068add30f1abb0007e8610169b754e69",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/BUILD_S1_W05_Captioned_Model.mp4": "cefb63f8706cbdb4feeb5b3293eb66c8566e622f9caadd455116b40933f3eb4b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/BUILD_S1_W05_Editable_Pack.docx": "5f4492ad015a60096320c7a03b61ab689533bf99c8f96303640b2b4a8c17ddab",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/BUILD_S1_W05_Editable_Slides.pptx": "2dc31ae9cd7c7c156c734487a37f27e0a914182025723ce71db4d94a7e57bdae",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/BUILD_S1_W05_Knowledge_Organiser.html": "7a78c22c52e5b874b844dea40d96bcdb0c8f94d917fd8653137c8dcaad549681",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/BUILD_S1_W05_Knowledge_Organiser.pdf": "6af65ed1a19b08678f703bb91fa9e9d46a943411c48f3e926d80d3eb8e1c6b78",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/BUILD_S1_W05_Lesson.html": "ba1fcdd0e38253b7048035df76b5fff93569b5989d03a87a17cf14edfff0b4d2",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/BUILD_S1_W05_Model_Transcript.txt": "d171e5571dd529316af1f4e8e4b8fff93d7adbaf5b8cec2ef1d9eea0c441016a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/BUILD_S1_W05_Pupil_Resources.html": "72c477fb828891541cb90179493e609a6fdf0ec4eb1aa60be1c99d94ed0a7c52",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/BUILD_S1_W05_Pupil_Resources.pdf": "3b592f101ce06103532a622371191ea03e9fd14f37c4b0777c5646e07892b936",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/BUILD_S1_W05_Teacher_Notes.docx": "c91b017d19dfbb6d59a65164b6088080615feda71dfbaad6301baa50051935f7",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/BUILD_S1_W05_Teacher_Notes.pdf": "2ec26d4ea50c51e0d7def4535958fd22c2734d76bfb6e51aa4a67b37ef28aeef",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/Object_Picture_Choices.png": "ed68f67a67f92a3f4ec3a7ef95d3143976b7cc52c77bdd294dc9139837d3d71d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/Object_Picture_Choices.svg": "6e6f68be419a58038f55bfea014c7735658d988a4d2e0c8d19898f59a15b9192",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/Teaching_Visual_1.png": "4325e8a9f30ddee1d60c48a84ffd855b3e7e3c14baf1550b78470bf2bb7486c4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/Teaching_Visual_1.svg": "be77de2677840464af652e8aad29cbce9b83ec8916b06e8b56eae750f762e7b4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/Visual_Resource.png": "42a4c22b9b907efdc03e8376e891fde915b21445fc0d72392a0b259392e97908",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/BUILD_S1_W06_Captioned_Model.mp4": "1fe5b5ed4c8248854ce0e2d61254f3ef5a0f1985bde8c7008fa3e9c51b4f5d6f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/BUILD_S1_W06_Editable_Pack.docx": "76c8b500af02fa84d338756ea34f8b2242e3a3ad72ee12a79e113f8cb9fd6743",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/BUILD_S1_W06_Editable_Slides.pptx": "707faf5a4bf579b0b62ccc4a7d1ea371c92036ac9052ff3d410c28cf535d8b0f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/BUILD_S1_W06_Knowledge_Organiser.html": "4fbc37629cf89cd07cbcd662e30311fe508f136c8a95ef5b64e901d8e725051d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/BUILD_S1_W06_Knowledge_Organiser.pdf": "6e4e926799eaab75fd7092bea8ea22b2c18ecc427acc51978b7919cca3a35326",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/BUILD_S1_W06_Lesson.html": "1b89913457b3e019000f6fa5151ecb9b4064fe368f33b3c15b3fe44a9b5c05d8",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/BUILD_S1_W06_Model_Transcript.txt": "9c1bafe8e8003992b48629cea25b829df64b495a82ee50fe6a6a93c53e628b8e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/BUILD_S1_W06_Pupil_Resources.html": "7e764c636d895b84718d340e72c6a89e40253fc55c7b50ecd6701e0634e5033d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/BUILD_S1_W06_Pupil_Resources.pdf": "d86d9d786015f4b7ca7c84d569191644b45e8bd6022e0b03d46be3b2f26196d3",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/BUILD_S1_W06_Teacher_Notes.docx": "11e6246cf082669104c06a034a569e0a772b68f34a9a3d3870ba3d7c152d7c1e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/BUILD_S1_W06_Teacher_Notes.pdf": "3a3a9accd2bd73e0d05c6717afcdb36912d81e664bd636e7ebecd2dde94ef937",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/Object_Picture_Choices.png": "ed68f67a67f92a3f4ec3a7ef95d3143976b7cc52c77bdd294dc9139837d3d71d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/Object_Picture_Choices.svg": "6e6f68be419a58038f55bfea014c7735658d988a4d2e0c8d19898f59a15b9192",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/Teaching_Photo_1.jpg": "cde4dc690052c1b0a658fd1e1f09c5a657086cf56c7fbc0bd1ed468ae3514083",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/Teaching_Photo_2.jpg": "6e1d3a6530790025b0e970213d76128faa258ffff9eac1cd8de510c734f60bed",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/Visual_Resource.png": "66399902cec42f3b066b94d3917ba339aa56ca983b4d0c5377797c69735e29cf",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/CHANGELOG_Final_2026-09-19.md": "6242d67f793c57f1bbfb5399cb3ff9510e7e1d48d2add539620e4bbbd881f86f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W01/GROW_S1_W01_Captioned_Model.mp4": "4128b3a43daaf9ac1e738096df37c57fce76f9c6b705971a43b513c7d98ae79b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W01/GROW_S1_W01_Editable_Pack.docx": "01c4773413270f20e62709dfada06589dda7262cc478d57605d03131d4d51434",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W01/GROW_S1_W01_Editable_Slides.pptx": "3c727a89af9ea218898212adb2ee21bd42d6085f30cd778eab888221e2747d0a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W01/GROW_S1_W01_Knowledge_Organiser.html": "0239b805a5074c469c513ee3683cc6f844dcb67651bb7a1deeeded0d2e887ff7",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W01/GROW_S1_W01_Knowledge_Organiser.pdf": "02ff467636d93ac1ae81355f1bc35e1897c27213f336776cea2cc32a3fb638b7",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W01/GROW_S1_W01_Lesson.html": "8767a5d70ac26218bccc9c28d17dd8dca489aece0d41e42024d5f725ccf85f7c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W01/GROW_S1_W01_Model_Transcript.txt": "98ecea80a1c10894ab29d0a3c6d427efd58cdeb8300dd9c23ef7501023367f7c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W01/GROW_S1_W01_Pupil_Resources.html": "59947af2a344912757606824920194d34bcc0bb44dc8cc5f0b7a4a65c2ad81d0",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W01/GROW_S1_W01_Pupil_Resources.pdf": "bf464d2f34cdcff713423482a2ab31000f2ff4ff770411622d9e8732b36c8e0a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W01/GROW_S1_W01_Teacher_Notes.docx": "f2590f8b32e73a18a41e9d9376aa08498a9c9f9667b243a9cbb8b0b0f1e42665",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W01/GROW_S1_W01_Teacher_Notes.pdf": "9efe6503813a08b0b615c40b40e4c3ae9958f1ac21f602d8cc877016cb99b89c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W01/Visual_Resource.png": "d7e5fa540f818171e52781f5e3e12f0fcb34ea48c0b5f13f6cc8c465e5a31537",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W02/GROW_S1_W02_Captioned_Model.mp4": "7a594f90620d081a46d9e486a186ceaab82c56156f0f72717a562960c8c90b0a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W02/GROW_S1_W02_Editable_Pack.docx": "751940ed91189af4f08685e4322bdba54d00483755a1dfa18ccb362bfd113326",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W02/GROW_S1_W02_Editable_Slides.pptx": "482a1bd46822f5d032a8c86e950afdf8a7d2f621f9fa5ee918d231b28b30cf23",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W02/GROW_S1_W02_Knowledge_Organiser.html": "2445d7f84aa532a69d0fe37287f5cf696b65502517d2d4f25329d47aa2687594",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W02/GROW_S1_W02_Knowledge_Organiser.pdf": "22040368aac085b2120e0c614fdbf8c33cc4f5d72ee6000a3a951e4ec41a1491",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W02/GROW_S1_W02_Lesson.html": "395557e4278ea9c6ef5404571552aae03bd6353e5091d5fdbb47a437a33786b3",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W02/GROW_S1_W02_Model_Transcript.txt": "a10cb357c679f5d04b230416f20fa774ff2e373e502c7f6e40629eeab2f23623",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W02/GROW_S1_W02_Pupil_Resources.html": "bf7b50396cf6d16507cc4e691f7672feec675746c7c7187be45310278340e758",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W02/GROW_S1_W02_Pupil_Resources.pdf": "3eda814a787b1f7183ac0507ca30aba37e5276161d95918caccdd6b53e0a1d8a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W02/GROW_S1_W02_Teacher_Notes.docx": "dcc0b640e9d8bac5b75984d9c90ef22f45945b47d405651d7ef52283f095f53a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W02/GROW_S1_W02_Teacher_Notes.pdf": "c25013972516bf2497e18721f604721a3add3a1b127d9a96dacc6a5423b55981",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W02/Visual_Resource.png": "b2b60e79d3222f4b951609846d7821a93cd234d1bbb5511fdd91f861eeb1feff",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W03/GROW_S1_W03_Captioned_Model.mp4": "52ff18420fadfc32f2d9fe1abf2a9bc44923406acd838736c7c12fb1ff900e06",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W03/GROW_S1_W03_Editable_Pack.docx": "301920c3a45d5b80949753ffbb5e85958e38d469244a97ba51a1b74b11d78893",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W03/GROW_S1_W03_Editable_Slides.pptx": "c34edb1eff19687bca014406c6d4b4198817ba7e08a89daee3bb968bcb2d449b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W03/GROW_S1_W03_Knowledge_Organiser.html": "cf1d139d91a0369f86b30ca75c6b0fba9202596fee353b77f40ad0a6cb8850c9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W03/GROW_S1_W03_Knowledge_Organiser.pdf": "191e896449aa7e336f04ce2e2d3e28139076f68268a2dd7ea713f7a8e604a36d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W03/GROW_S1_W03_Lesson.html": "25a4ee078319954f540afee1c9e975fb35cc079b71d68437a055fffb46866e21",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W03/GROW_S1_W03_Model_Transcript.txt": "3baea937768b5994f808ddc71c4c64303e5c264f4238cacdff009065563ba900",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W03/GROW_S1_W03_Pupil_Resources.html": "f7829edad04c005785dfc88c624c167b53c4660ca7339be59673e8de8d9a4399",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W03/GROW_S1_W03_Pupil_Resources.pdf": "844525c3b14843cbd18ee5982d1f7f378903340fcbdadaaee621f6586b53fc97",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W03/GROW_S1_W03_Teacher_Notes.docx": "190956c4f67c878891fec8be71c274c256adf1760fa3296e17edc57a40d43248",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W03/GROW_S1_W03_Teacher_Notes.pdf": "18ed89dba5c6d9ad4df16d561396c70857bc1fa9f4f93908ffd201b0e43a9201",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W03/Visual_Resource.png": "82ce807024a96c001cb7b0b77793426c593cab36d5789106bccba0654b2e4e1e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W04/GROW_S1_W04_Captioned_Model.mp4": "bb98e57114a548d36dc474ec92d10a19a62732fa696b29a28faa6e12c1eedcdb",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W04/GROW_S1_W04_Editable_Pack.docx": "4eb57269ddeedd853cb01d50b12c842b9045505b1b5300bce956e1788fa41376",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W04/GROW_S1_W04_Editable_Slides.pptx": "15ad2a227bf84319a5ea55caa7aa968ed6f4263b69d262a9e4c5b19bdedad02f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W04/GROW_S1_W04_Knowledge_Organiser.html": "c9175bf653730eeef1a75affb9e571ac70b3ab6b0725d7938af708ff6768c6aa",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W04/GROW_S1_W04_Knowledge_Organiser.pdf": "1f45f5acc7ec53cd8ae687a01946a4d77896f3d9a3feca53ed8088a2b4d4f4c7",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W04/GROW_S1_W04_Lesson.html": "7205ce1ac6500739954c9d4961a357a31f5528589cc71ffb6d957842f65d0fbe",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W04/GROW_S1_W04_Model_Transcript.txt": "382dd05edabea1f4379f7b83b36f6d9971a2ed5156130dc7a3736156a60104ff",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W04/GROW_S1_W04_Pupil_Resources.html": "0bfece0a3289af7e44b60a3e2d260a622dbb67d30e78d679087ed5dca897d8dd",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W04/GROW_S1_W04_Pupil_Resources.pdf": "4166fbdf653be13c7744becdd8565fab4ca523cdcb159d74d55770034f11eec1",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W04/GROW_S1_W04_Teacher_Notes.docx": "9c1cd38a2c73a49ce727142b7c9ef93610cf2f48faa045a247deb038d529b95a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W04/GROW_S1_W04_Teacher_Notes.pdf": "19296780f0355a0b237d75def6b0afb488780634763ba3420367815fb951cd29",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W04/Visual_Resource.png": "5941e316ef1dd15f2b3b773d082e392ea98526ec4a6206fe003e2970f8cd2d04",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W05/GROW_S1_W05_Captioned_Model.mp4": "9a1b9e73d8733d960a6d52ae74a83b97bd829454776783200b2d5168e06768f0",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W05/GROW_S1_W05_Editable_Pack.docx": "04f8241745c1895520edc5e4763107a0a63122ea10f1a50aff197864ec698ba4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W05/GROW_S1_W05_Editable_Slides.pptx": "40a1f020dd3ebe52331942284bf9dc1e9f34adedd44aa448cbc223af2dbc4a95",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W05/GROW_S1_W05_Knowledge_Organiser.html": "3aefe41182bbc93a6e6ff0c1f15a3fd3768585584d2c61911d21bcf959b6ee1c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W05/GROW_S1_W05_Knowledge_Organiser.pdf": "779d92e30b09af0950b96e4bbac5bfb20db53f5c2861907a7be447052ad44b4f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W05/GROW_S1_W05_Lesson.html": "fec1954b9a8c5e30a24b9df6b6d77509eb8f4811e87251671c1860970e781d2f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W05/GROW_S1_W05_Model_Transcript.txt": "23bafb09626838bc7bec49f76b700ea8e58e3161e292b6f291206815f09f75dc",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W05/GROW_S1_W05_Pupil_Resources.html": "3dbf0ce983407adfec72498db1d574e407b9379dbff34a3d7cfbb65ebeefba8d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W05/GROW_S1_W05_Pupil_Resources.pdf": "7da96cbf39f815dcd9559bac6c2a30e9983c548e9878c6f5da0511f051ecfcdb",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W05/GROW_S1_W05_Teacher_Notes.docx": "d97f486c78991ad4fbc2c7ba5a88517debf8d9962cc3c545d9cb491be4378095",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W05/GROW_S1_W05_Teacher_Notes.pdf": "c8f795e92ad8c765a00fcfab09f9dd032fbc9dfd49e4273ebf4b4f27ea01899a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W05/Visual_Resource.png": "dbfbd029b9dc2f404cd5b9ba0531b5b9dbe409a3ceb5826679a15147fc286c40",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W06/GROW_S1_W06_Captioned_Model.mp4": "39fad391bb0b4f0a32dfd465a2b2a32c844386c7b2b12fc0fd5573132fa9ceb6",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W06/GROW_S1_W06_Editable_Pack.docx": "30faa00237cccd432f423537df7e56b8eb28ac8503eba66bfbe6ec94f1f19213",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W06/GROW_S1_W06_Editable_Slides.pptx": "b7f356e2fd5b60629899f5aea839f7d2a3da3547e825e6d053c3927ed21523d7",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W06/GROW_S1_W06_Knowledge_Organiser.html": "018c7b1fe11206f21edce677725bb0edd6787fa192198ec05e1726212ab2583e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W06/GROW_S1_W06_Knowledge_Organiser.pdf": "52a7ec50e662a133d3711d49425ff40bd54048e6459182e61692a5aea3cbc633",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W06/GROW_S1_W06_Lesson.html": "1f4c650cba4bec9a3a42eceaa08b9f72413130de68db5fb73c4912845090c8a6",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W06/GROW_S1_W06_Model_Transcript.txt": "38de5d00a5e5276327138cf88d759105b1a98d70a9babd74c73379c00ca317e7",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W06/GROW_S1_W06_Pupil_Resources.html": "d158ef2ee33838b0b58c3d4aacf5dbab8cb5f8071ed3ed306514a3ddb002f59e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W06/GROW_S1_W06_Pupil_Resources.pdf": "34a32c3a0eca9b706aa428b0683244f0bfcfaeff76d7ee41ac6576e39115bf40",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W06/GROW_S1_W06_Teacher_Notes.docx": "0d767c42b245171cee382fbe9ccf7bdbf88289b0e90d75681327f3ade8575f88",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W06/GROW_S1_W06_Teacher_Notes.pdf": "a295300f9e208716f6039a6f16c6a5b5ac3253c45a3c349294a31ec1e6195213",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W06/Visual_Resource.png": "488c1020ed3d28ffea28e98dcae4db9e2f4c0e54591d2acb92d21d9773963df1",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/README.txt": "b18e6a10681a2287090de194cb29747da642f300b3a25d7c11b3b45bcd814714",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/Review_record.html": "449c2ebe1fcf649e013f0bd25844975ac9454c9fde39797b4d8043bc58dc1812",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/SHA256SUMS.txt": "96587db7912c6d7a7248bafa8d21bb976b15a8eb0664711e8ed45b2062df7f91",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/START_HERE.html": "92b4d9dcc4468b22fdf7c50a70f89aba20851c8ade674ec6206a8f4fc49599d1",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/CHANGELOG_Final_2026-09-19.md": "1304180c2bfc22c9b9ad1420ab87037402b64376c1dd9387150740921f50675b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W01/LAUNCH_S1_W01_Captioned_Model.mp4": "c49e25e9c6802c947285cda3bed1f792248715c04c925f767757bd4e33aa8347",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W01/LAUNCH_S1_W01_Editable_Pack.docx": "7f349d34e13b0976ac5dc2191f4c845812240a812be8ad8b597e46c7042995ef",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W01/LAUNCH_S1_W01_Editable_Slides.pptx": "fa7c067fabf13f0fc4e4bb086295785e991539a1cf83ff38fc090b661802acfe",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W01/LAUNCH_S1_W01_Knowledge_Organiser.html": "7c1bb9d784428be39c07a0e5987750601387a1f3d6056d64e1c9751b327bb60d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W01/LAUNCH_S1_W01_Knowledge_Organiser.pdf": "d6e450fd818b4a61b388cf211275d4d4c278d99dcb911ef15e352fe900900b92",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W01/LAUNCH_S1_W01_Lesson.html": "780c746b091cb9fc46c895bd56a06e4ffcbe2dd9dc60bc152a4457b4f8c8c3aa",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W01/LAUNCH_S1_W01_Model_Transcript.txt": "5df9677cad4b84ade6de06c9c998254ecd93ee2a69baa73ac3382400a679658d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W01/LAUNCH_S1_W01_Pupil_Resources.html": "69ea9af8c09bdc618507c344f3ec5c918fcf3d021d8400b06c6359427033641a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W01/LAUNCH_S1_W01_Pupil_Resources.pdf": "8a9787a48281ffbdc1e8f35f8772ee0e40ca5670d086886193a7bb200050bc2b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W01/LAUNCH_S1_W01_Teacher_Notes.docx": "865de895d7cb6340ee8197775abbd9afb2e93d11888bd3253f4046ff3d59d4c4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W01/LAUNCH_S1_W01_Teacher_Notes.pdf": "f96913ddbd31615a301a8272d3b4af6277724adf61b07d7c454e5495053f6bd3",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W01/Visual_Resource.png": "226ee510f04d3267f110325f3fe3a5710ace60fc5435d99ded37f8844336f888",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W02/LAUNCH_S1_W02_Captioned_Model.mp4": "c74f353004f540c7200123e0a9ebf39d3f8de2fa9b6be22942be1ea10919b8be",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W02/LAUNCH_S1_W02_Editable_Pack.docx": "a618b5e89817d02ca44e9c339c04ea773962f59b1f0d0e986d6ad8c59b2605de",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W02/LAUNCH_S1_W02_Editable_Slides.pptx": "f8ab209d6f94d7f0a85662ccd27c1b6b850ff7603aae82b44cfaaad876ae4894",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W02/LAUNCH_S1_W02_Knowledge_Organiser.html": "530419e5d3d12700ff558bb4246adfd374b2198f9e1f0f1d919dced730a61a7a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W02/LAUNCH_S1_W02_Knowledge_Organiser.pdf": "86bdfc25bb13caf59b28705a715c4bdeaf79cf89dbda366eb0ccf84816472f4d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W02/LAUNCH_S1_W02_Lesson.html": "eef2f4e53ae19ea1a5aa802620c48df5dcdc3c6e89ad19dd929e658dcd933201",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W02/LAUNCH_S1_W02_Model_Transcript.txt": "0a2890e82cdd0476d8c0eeb462167c6127de46a2232a20e822f1301d3e08fdca",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W02/LAUNCH_S1_W02_Pupil_Resources.html": "49b70e31cf512f0551a13df84f058b9546ca467a5d4d90407890a0c222afafc4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W02/LAUNCH_S1_W02_Pupil_Resources.pdf": "16dbb3a3a957dae0d841beb4c9fc88653d46176806e98a1970aed52893d6f322",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W02/LAUNCH_S1_W02_Teacher_Notes.docx": "8a48af169e0fbb4b42648b123e57a480a01033686a99e04832fb93d65aa9d0e1",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W02/LAUNCH_S1_W02_Teacher_Notes.pdf": "6522423c457627cab9a21ab7e8eb87bb44e954175482b10b631618fed9fc1f77",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W02/Visual_Resource.png": "79b8f3c25c5a09a91a88218b1fb00e5b23a503541f570df78f597292cd487462",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W03/LAUNCH_S1_W03_Captioned_Model.mp4": "f8fd662e378d7500bc4d3abbe39abbeb3ba319a58a5ecfb9cf0bd85defd206c9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W03/LAUNCH_S1_W03_Editable_Pack.docx": "c868dd86cfcda828fd5161d98745dca70d5332328b272cea6c32f9cf1d713473",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W03/LAUNCH_S1_W03_Editable_Slides.pptx": "eba5e5d1251168133926b881f509506df21bfc7e64c8d19b733c5ebb33bfb182",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W03/LAUNCH_S1_W03_Knowledge_Organiser.html": "48709727ab260655f0175184c2c0f02d04d77edfd41b68a184b47b6abfaaffce",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W03/LAUNCH_S1_W03_Knowledge_Organiser.pdf": "e8e1b9ccd2312c5e2221392af67f08d186b876b3bcd8f2361fcbaf37f5223d6c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W03/LAUNCH_S1_W03_Lesson.html": "f19d0dd8ed88b18dc1d33faf61b7729abd16b3651604b5a920ba21d149a5d1fe",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W03/LAUNCH_S1_W03_Model_Transcript.txt": "57e5349a08ce65aca18682ef0ddfe56aa6e55b0517572fbb4b5f25e1df8378d2",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W03/LAUNCH_S1_W03_Pupil_Resources.html": "c36c7bd3581af3a0bd9de7a43d156ff8d593583f85d09c22e1292b192f4b136c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W03/LAUNCH_S1_W03_Pupil_Resources.pdf": "3c05cb17c601236a37f94d3b9dee09fc4d3748417bb7722de7b824f6fd318c00",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W03/LAUNCH_S1_W03_Teacher_Notes.docx": "3a50e31562ad8d6c911cf7b8e64a918562725441991646865159411530fc87a8",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W03/LAUNCH_S1_W03_Teacher_Notes.pdf": "a46054dd86dae0c91a4b5f5f196475a6169cfa2cb2fba326599bc3a93ab2fff0",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W03/Visual_Resource.png": "74cf3b8ef331a4d62d856a9eba7f140ca82b26ab60ee879877c721b75ee73cc3",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W04/LAUNCH_S1_W04_Captioned_Model.mp4": "676ef304048359586c678d8cd16f26741ea511c93ff127791ef7bdd30e630688",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W04/LAUNCH_S1_W04_Editable_Pack.docx": "9572e108baa3af13cdf3311db17823b64fb945011431df9ba52864b25914e608",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W04/LAUNCH_S1_W04_Editable_Slides.pptx": "c0fb60beeac266560dddbeee8aa9b1ce88e8bb4d1a743139a37571eeae9e2e42",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W04/LAUNCH_S1_W04_Knowledge_Organiser.html": "31389063177298da3da532f9289f9fecd5cdd09c3a9d2c014a40eaff009c5a67",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W04/LAUNCH_S1_W04_Knowledge_Organiser.pdf": "4f67e83f227ff08b1c43a3eaf43870183c2c582280a6a6bd0cd295af6d1d9674",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W04/LAUNCH_S1_W04_Lesson.html": "9fe7b03b9d9a8da25e8bf666e5d112fd20d2045486e1de4ecb9d8909409b9992",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W04/LAUNCH_S1_W04_Model_Transcript.txt": "e76faba8727bf7b87272d6a803b4e1dface594595c656a13fa9ecff7b2fe4e08",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W04/LAUNCH_S1_W04_Pupil_Resources.html": "e58a478cdcd89119d9eb88093786db1daa8c484781a54cfc7ad4c10553d24a8b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W04/LAUNCH_S1_W04_Pupil_Resources.pdf": "d248927266154840cb14362cfc99d9be8da99421423c80cd0d8001ca05af73a1",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W04/LAUNCH_S1_W04_Teacher_Notes.docx": "ca92a5ec63d970678d06f5f613ff880b1971294b4cb5c34715e7e71f68607307",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W04/LAUNCH_S1_W04_Teacher_Notes.pdf": "9b880de6c55d6e90505dfe695eeda794b0c2a0914bc6bf5641bda090e8a2447b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W04/Visual_Resource.png": "085b35dea347c41a4e477b0eda76cf2486ae49262c6a27fa137eb83f1b3416ea",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W05/LAUNCH_S1_W05_Captioned_Model.mp4": "65455bcfd14b099d48837b12a3f762b4f587cf1d7c4b39d3cafe1e70374a209f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W05/LAUNCH_S1_W05_Editable_Pack.docx": "d959878684ec6cc1d6f2db0f6cc65611faacba237ed1fab8be38a4f60ae13f70",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W05/LAUNCH_S1_W05_Editable_Slides.pptx": "af6de7909b33e2b8175165d51a85090d49ae6765020cf712dd07c85e0d4e0e99",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W05/LAUNCH_S1_W05_Knowledge_Organiser.html": "7e504990937b7ec964014e5714cc03481e9342577c01fbb732037475b7cc5429",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W05/LAUNCH_S1_W05_Knowledge_Organiser.pdf": "1b64757eabb6790a3b8868e915e067139e5a86f3afc9fd843f889fbc65929b1a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W05/LAUNCH_S1_W05_Lesson.html": "66dde25fd64394b1daf04d700fe9932e054f7883fe664c13084bd04018380570",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W05/LAUNCH_S1_W05_Model_Transcript.txt": "aebfed299857d363fa440a1db6000c0c6aeef1da62b0505e793521ef6fe8b708",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W05/LAUNCH_S1_W05_Pupil_Resources.html": "990a78a1a8e944d7b9657b9a08efeae2f625dd33e3189a85bf411d2a662b5848",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W05/LAUNCH_S1_W05_Pupil_Resources.pdf": "a5208bd1b83072b74c7dfa85425e5908953d80d9a7ff26241211e3b65a2bfb71",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W05/LAUNCH_S1_W05_Teacher_Notes.docx": "690dc61531db87c56ca2d9ad7f2cd2c3b9d7d568699d8f5043420c497af4d7ad",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W05/LAUNCH_S1_W05_Teacher_Notes.pdf": "f28317f2cd4608e73d6859f68dfc5b53acb28003c4ad591c58afb55272e0dc0d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W05/Visual_Resource.png": "9d70a5eeaef4b481d40d9ead120944f52d7d856932c41cd259bf007d437ee040",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W06/LAUNCH_S1_W06_Captioned_Model.mp4": "d1219ee3be021728bf8880c1fdde859a1cae1691dea32f651bc66d0c9687885d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W06/LAUNCH_S1_W06_Editable_Pack.docx": "b7ed92cdc2c4d5f0800e021292ee5d820587eae7b8be57609eb3810bf2592160",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W06/LAUNCH_S1_W06_Editable_Slides.pptx": "1b265df925b66b12158f954c2846cb57cefb15c0d08ad2f21093c29e8afd443c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W06/LAUNCH_S1_W06_Knowledge_Organiser.html": "6134d2a07353a4d638bba5d326d197b41b992377c67ce0c624491952b8df5fca",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W06/LAUNCH_S1_W06_Knowledge_Organiser.pdf": "8fb497622fc6206f0fb3c9315c4c025453e0bfdcb7c93e4a9b33e2f56f17dac5",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W06/LAUNCH_S1_W06_Lesson.html": "cf789d5a357aa2dcae03213a8b99d79f610dad27c66d608b3c4ee40efd48f282",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W06/LAUNCH_S1_W06_Model_Transcript.txt": "59634a56d1e86037b354e6fed4d4aa8a5e1112808e5ec7116957465f98d6e2e5",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W06/LAUNCH_S1_W06_Pupil_Resources.html": "b0c32de31abe28f99f5d8421d4b75d9bbd70e31f5544576b4407d951dabc819e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W06/LAUNCH_S1_W06_Pupil_Resources.pdf": "09806fb8e4b633e4dc4862758ecf23bedb6e1a4f7f895ba32bc5b280f8db8ee0",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W06/LAUNCH_S1_W06_Teacher_Notes.docx": "a46dec7379b9d5b8d33fb64cdf1530c8845ff126bbe43506ee7c675b94ef0689",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W06/LAUNCH_S1_W06_Teacher_Notes.pdf": "cd3148f5d0417ab1dc4eac96466a18dfd8745f54fee511926bb479b6a8f5c831",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W06/Visual_Resource.png": "e96ad612bd29fd4b732c5072433a207e310477bb5e65187e0d6d3a1141b32422",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/README.txt": "b18e6a10681a2287090de194cb29747da642f300b3a25d7c11b3b45bcd814714",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/Review_record.html": "45b170df36aeb573ddf75ac4741b2d907c09f35ffc6b7449bf3a31bfd797ce1c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/SHA256SUMS.txt": "a4545d2ffa724f7c49a83d93ac62446b2b65cf150657ab6b3b45d4f846b51050",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/START_HERE.html": "64bcbfc9be136aaa78416b86835136427d48723c80064e5f9fda38d5aa261e57",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/BUILD_S2_W01_Captioned_Model.mp4": "3c5ff6a9323ddbc4ffb47eb3d424ac7d302d2926236dc46b4d8e5d1a9baff032",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/BUILD_S2_W01_Editable_Pack.docx": "3ca77c37d44b8225d86dd4243d826c2557f5f1fcec07f6b30546d4fd194cd431",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/BUILD_S2_W01_Editable_Slides.pptx": "835b35a90123978ed351bef24ecad612c07c83133f5915e411b2ebe09dd4a863",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/BUILD_S2_W01_Knowledge_Organiser.html": "34d514ceee3dc103a5b34f52f9b31564a52bd3fc7869aded5ef31f003026886a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/BUILD_S2_W01_Knowledge_Organiser.pdf": "38aa46283cdf5bfa27f5dc3bf27601f0a91f5165fc4c756818f0f13e5cf0c2f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/BUILD_S2_W01_Lesson.html": "b7e2de7b27a16a9a50a58e0e5c37f00b75a69431e34f82e3856636e3c88ce4a4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/BUILD_S2_W01_Model_Transcript.txt": "84275b4b6ecc1291d0cead4b66ebfab6018c15e990cc935857f72723f19b1eb1",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/BUILD_S2_W01_Pupil_Resources.html": "7e0366957dc8044595fe30c51f746d84e35d5d4ed516cc4b3554ad29fd9ffe6b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/BUILD_S2_W01_Pupil_Resources.pdf": "c67b27ecf56d2b7ce59e395a77b109985bf7d2ec6a07d8c0c191c9f11600a0ea",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/BUILD_S2_W01_Teacher_Notes.docx": "00e10b9230d270496e6211d971e1356a4a90d56d7ac5c8904584f30530500467",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/BUILD_S2_W01_Teacher_Notes.pdf": "933e5459f0ecedddd939e870446c61f52a8feda9c20a2392b97372e8822ba48e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/Object_Picture_Choices.png": "783137c05ebd3688de815c04e9aeaebbe7dd21d6272661e9c6edcc91c0ebaf65",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/Object_Picture_Choices.svg": "c640df990e9362dc8a2a5beda99647d54041eb05e11467472d9c5c6c8000f725",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/Visual_Resource.png": "253f9251bd7982204ac37b7884cfbd660e0aacae1f49bbd222ac0b3b936951e3",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/BUILD_S2_W02_Captioned_Model.mp4": "2271e3049e3261df974d4d0e3b876233574d7dcd81090c2637093901bcc7cfd8",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/BUILD_S2_W02_Editable_Pack.docx": "5534e4225d54cb3e66772056738587770f569ca02256c18eb399f9e1c7735f9b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/BUILD_S2_W02_Editable_Slides.pptx": "50240e17db942d4216c1ffeb3fe0f019c60e8466e45e4ac4d3fa4ef35bc2284b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/BUILD_S2_W02_Knowledge_Organiser.html": "67457fee3a03a59f7c37642abd0f303f52414f9c1c772c11e26adfd94ddcf67a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/BUILD_S2_W02_Knowledge_Organiser.pdf": "7bae08e8782aad0efda15f34639842b20208a7c8c2effd5500828f5bcc1357be",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/BUILD_S2_W02_Lesson.html": "241da5fcc77f4420a74d48d0dfaa2212b1cd687e55f61241227f7d40fed9561b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/BUILD_S2_W02_Model_Transcript.txt": "ad65fcc06727f6081795d86b679a48e547525bf209860ecc8d44e41d4e39dcdc",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/BUILD_S2_W02_Pupil_Resources.html": "6950e198aeeeefa5f87262cc343fb3d135d49629e3ac8fa2fd840baf71a2c906",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/BUILD_S2_W02_Pupil_Resources.pdf": "2394a27cf083937226165fc053ad02719dbf849dd954c4fdca08d54823161844",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/BUILD_S2_W02_Teacher_Notes.docx": "3c58db5abb4bdab706f08ae959d5ddfca9e45a69d1a7df1c78e8dde4474c2e69",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/BUILD_S2_W02_Teacher_Notes.pdf": "291638345cf89a7651f357a2a7dd18856b2f9f9a84484bab4c0f1521855fe2e0",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/Object_Picture_Choices.png": "783137c05ebd3688de815c04e9aeaebbe7dd21d6272661e9c6edcc91c0ebaf65",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/Object_Picture_Choices.svg": "c640df990e9362dc8a2a5beda99647d54041eb05e11467472d9c5c6c8000f725",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/Visual_Resource.png": "607ec77185fb644d2d03c91b56439c0345607fd4c6f636b840fbeeca87715a4b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/BUILD_S2_W03_Captioned_Model.mp4": "da40122d17a98aa7a3cc6ac5ca77e47a6036e423d525936b0bb45593d8b56f4e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/BUILD_S2_W03_Editable_Pack.docx": "c76f5565c2bbd4ad00ac907934a056b518caa8bc51d64480ef63fa5a4b8f9700",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/BUILD_S2_W03_Editable_Slides.pptx": "320226c22e1d681f5b09c5ff1b4396da47e4b1441e34c2be791d9d2453a50501",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/BUILD_S2_W03_Knowledge_Organiser.html": "3a9eeba3330175dc6bd1d4b2af5c24af042e6719cdd80185bcd92b748514a842",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/BUILD_S2_W03_Knowledge_Organiser.pdf": "26e62c61428a28174f0a64feff1af4653f706e270ddf1003373f7e18120f0089",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/BUILD_S2_W03_Lesson.html": "111128f24ae3dd5516d19af7a2a2eb4ee10916011136640de53231c86e5e0eda",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/BUILD_S2_W03_Model_Transcript.txt": "8da55273a2e69e5000a86f133ba31f2a765c46e6610468b7c787d64a282d8ab5",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/BUILD_S2_W03_Pupil_Resources.html": "67f7b07a546fc201a259ee046ef6b60aed9c24c38a6af100fbef581082dce7ff",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/BUILD_S2_W03_Pupil_Resources.pdf": "b383df035c8d2fa498708cbaa2eeca778611207ee3a4544252bf7897f28f5ae5",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/BUILD_S2_W03_Teacher_Notes.docx": "7e7dd866845cd9f3cad9943fc689f67a45d68cbb350174785fef80ae93f47883",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/BUILD_S2_W03_Teacher_Notes.pdf": "1fe3e6fff6fbbd9f5a92286d8df45b4da2dd7d6dbcc8c0cb83013d1bcba4f1db",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/Object_Picture_Choices.png": "783137c05ebd3688de815c04e9aeaebbe7dd21d6272661e9c6edcc91c0ebaf65",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/Object_Picture_Choices.svg": "c640df990e9362dc8a2a5beda99647d54041eb05e11467472d9c5c6c8000f725",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/Visual_Resource.png": "277deaa6325bea84f785f6876005bbcb47ca964c287fd78833a3e917bc0b7f08",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/BUILD_S2_W04_Captioned_Model.mp4": "7179f4a8e2b6aaf250896442cd3a17e790462cc59fba14980e1e882610001236",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/BUILD_S2_W04_Editable_Pack.docx": "eebe46299a8e52c826b7e47d8734204b5fc8692264b86a86f59b5b82af301779",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/BUILD_S2_W04_Editable_Slides.pptx": "700730eb7b9846fc45e6521de846c79bc4061a93079ed9fed221e34df6a34489",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/BUILD_S2_W04_Knowledge_Organiser.html": "e7c2f877cb45c830e6238d7df77efc79df0302056531b13f675af927f44ae430",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/BUILD_S2_W04_Knowledge_Organiser.pdf": "d1bae6c83dd42ab60df70d26414148e94154eecbb61a1bce7b88b96340add6e9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/BUILD_S2_W04_Lesson.html": "c0f408a5de26fde384ef7cd58328922832c3218520942cfeaa2103b936f5e2e1",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/BUILD_S2_W04_Model_Transcript.txt": "8d6e9a6e7e34a9f2fdc8bc9028851e3fb5f40894547c7166e87e28b8e527527f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/BUILD_S2_W04_Pupil_Resources.html": "b86e4172713bf55108fc7a06cd20803391a6a3414c3c566cf12ccac9dede2f41",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/BUILD_S2_W04_Pupil_Resources.pdf": "79f9a6c24b38af3d3f79e360a6d69f4b1ae9f8ee833729a6f31d5417674638c2",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/BUILD_S2_W04_Teacher_Notes.docx": "5c90af076bf2152c02b30ebc4aec140c41f42253e778dbc2ac8a697f9548fc51",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/BUILD_S2_W04_Teacher_Notes.pdf": "f17fc09d1e7fd9fbaf6c275ff766f2279c9863f74fd44fef11987b339d8f4ec3",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/Object_Picture_Choices.png": "783137c05ebd3688de815c04e9aeaebbe7dd21d6272661e9c6edcc91c0ebaf65",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/Object_Picture_Choices.svg": "c640df990e9362dc8a2a5beda99647d54041eb05e11467472d9c5c6c8000f725",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/Visual_Resource.png": "04b6f2b4159281105e3d69a19fd300a4ec04f32ac1649afc3d9bb55f77090839",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/BUILD_S2_W05_Captioned_Model.mp4": "84d919cd6fcdcba0fb00348658178cdafbc41909616ff41c6288aa0a4b45a725",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/BUILD_S2_W05_Editable_Pack.docx": "87173c2b948ed209b983ebcb213953a8f9ae11fc1aa9f8fa6838367598f5e7bd",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/BUILD_S2_W05_Editable_Slides.pptx": "ea12f673b17da5bb1ac01aaefe0501dc1e05232e1a45f1bcf95f8e72929d382d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/BUILD_S2_W05_Knowledge_Organiser.html": "ac2b1a9d1d3b8fbbf9bdd93039a927f07c28c321366e5618454036cab035120d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/BUILD_S2_W05_Knowledge_Organiser.pdf": "f9839a9c6292fb81c683a11c5c58d8d3307352871781e70299105c241cd4f13a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/BUILD_S2_W05_Lesson.html": "a823c711e5720d198fed6ae37152116f6cc42d4bcfc4a30bca2378fb783e6e9c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/BUILD_S2_W05_Model_Transcript.txt": "22fab5e7c70a699668a4b97abe48bc893db70053f4d4ddb0ceffdddba40471e4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/BUILD_S2_W05_Pupil_Resources.html": "f80a252d76926472acb0bb1b34389f4ec282caef06ef736d8b0cdc423ca7fd55",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/BUILD_S2_W05_Pupil_Resources.pdf": "92e018019c808d7f4dd2d44dd443a32129287c134f2d65e98d6047d0e7f3a5b8",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/BUILD_S2_W05_Teacher_Notes.docx": "aca15ed6117f76daaed27a6929adcacb33e9acaa7373b0197e33f05918a24709",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/BUILD_S2_W05_Teacher_Notes.pdf": "84cf480f475d68e1130c92efe434dbefc7aa35c75003b6967cc7a61f030c94ba",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/Object_Picture_Choices.png": "783137c05ebd3688de815c04e9aeaebbe7dd21d6272661e9c6edcc91c0ebaf65",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/Object_Picture_Choices.svg": "c640df990e9362dc8a2a5beda99647d54041eb05e11467472d9c5c6c8000f725",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/Visual_Resource.png": "fbb4e32cad10feca63784935a1177ef0a46e580487d811373b77a2ed5625c67f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/BUILD_S2_W06_Captioned_Model.mp4": "bbe3c4ee2f2d3ffdca03cea36043080abeb3547bd80fdcef15fbe0b6aa9edfce",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/BUILD_S2_W06_Editable_Pack.docx": "c141c7a667813cfbb9efd86e3b809838daf15e73f7a7e4d275e0bfc0d6a5daa8",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/BUILD_S2_W06_Editable_Slides.pptx": "d226fa525c8e7e04034d8af8f3f38ab2a4e1763693e7bdfa93878dc1ade9aac5",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/BUILD_S2_W06_Knowledge_Organiser.html": "f5d8543fb0854a2bd1e08f3d993aee44e98f2a4cf586884cf2687c323d03ca93",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/BUILD_S2_W06_Knowledge_Organiser.pdf": "6cb52544d84258fab53e6c04fe9f0b5291ef3debcee448845e457aee8aa19e13",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/BUILD_S2_W06_Lesson.html": "845b6b086d9e1cc90bf1d9514f82f9901ab8de315c800263f7509d171709b2e2",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/BUILD_S2_W06_Model_Transcript.txt": "1129637d7d72085e195d2fb85700b2ef1fea3aefe9e43ce63d0ec14e1913dc88",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/BUILD_S2_W06_Pupil_Resources.html": "da4299e2d478c6768f7185e44a13b1ace38993ddd776e32bdc21fb20305a99a1",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/BUILD_S2_W06_Pupil_Resources.pdf": "942eeeaf2a4e1dbbe1892532004e2dccd2abef89d805ab560abbe54e484b023a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/BUILD_S2_W06_Teacher_Notes.docx": "da2aaac1970867f1271558e899029963347bab2f80ebec0b11c050869c6aee73",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/BUILD_S2_W06_Teacher_Notes.pdf": "5b266f47739ae8a8d2e5ca4b835494b9b7a2fd2555ad81d88e971c508989d635",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/Object_Picture_Choices.png": "783137c05ebd3688de815c04e9aeaebbe7dd21d6272661e9c6edcc91c0ebaf65",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/Object_Picture_Choices.svg": "c640df990e9362dc8a2a5beda99647d54041eb05e11467472d9c5c6c8000f725",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/Visual_Resource.png": "d7bb57a9ada8929c6d3c04b8e8f26c37decc80f8cee68f5eb302368dc2c79342",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/CHANGELOG_Final_2026-09-19.md": "9aaba986b339f2597bc6ab3352271f26b7e9e5d31d768fb6f4f06d90c52df3f0",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/GROW_S2_W01_Captioned_Model.mp4": "bdf7be5cb2c97f9c3022f02b342d926431ecc91e01e760fc8fa0cba4a9755d56",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/GROW_S2_W01_Editable_Pack.docx": "10cb85d1cdd7e036d86604565e8413673f1c5a742409bde6dd29f64b71ce0a4c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/GROW_S2_W01_Editable_Slides.pptx": "7a99761f49defaa64c65718f454b53b0785cd9c5ac386936151b887246be46da",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/GROW_S2_W01_Knowledge_Organiser.html": "5062ddac8e5c9fd194124a74d0ccf44586fd02bde7e3fa65e9e0bf7b42502b51",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/GROW_S2_W01_Knowledge_Organiser.pdf": "e0a8e12373f0212b022be598aeb8780d4697b007787577871bdd06894d6ff65b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/GROW_S2_W01_Lesson.html": "52d68c297247488475f9bfdb11baca84b9602c65f36c27118c9b4fb3586a71ec",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/GROW_S2_W01_Model_Transcript.txt": "9316bc563631870ad76b3e3dc47f035ebd4daf09194fb5395db232cd9b23d28a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/GROW_S2_W01_Pupil_Resources.html": "1dd98e014a06891aa01b103ae1f6e3334318a293a6f3411b9616025084b09613",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/GROW_S2_W01_Pupil_Resources.pdf": "51b70c2d2ccbf1cb1dbf53dd477cac876db96983fb1be20ceb1181f6e56d520e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/GROW_S2_W01_Teacher_Notes.docx": "eab7af86e43119cec6f1571c6b832ec601b8ecf145f3ea4867d24ab0c2005fcd",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/GROW_S2_W01_Teacher_Notes.pdf": "7733c3e6ab6367961c09e3367a89bba12915cb78b664170640022253ac68b10e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/Teaching_Visual_1.png": "1a793b704e80391e197af1908acd410632bfda23bb8feb865f3a95bcccfffda7",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/Teaching_Visual_1.svg": "5f2676d8b038b2a94a9c064ee8b6e277701348d552d1af8e4007ea01a82b64b5",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/Visual_Resource.png": "ac9577e712cf0be5ad873f838b0ac935c6581a283c0d9d0374022312a12cba14",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/GROW_S2_W02_Captioned_Model.mp4": "ee69191e75cb9ce8fc1a854ea814b5abaec020181e92b7a5f17ad59773e6f81b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/GROW_S2_W02_Data.csv": "7598c1810f687464023f256602d663c44cb8e7c8f8c5cb70264633c74a754bd5",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/GROW_S2_W02_Data.xlsx": "c8d8fc889c2a18837a200413b2f9c5221e495aeacd367fa692454ccc98f3f637",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/GROW_S2_W02_Editable_Pack.docx": "b033cfa211d14085cea0f2834cc2231e861524fa91683cd8d61ed12bb584b593",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/GROW_S2_W02_Editable_Slides.pptx": "7893b277058775abcb1d6d2ee1a94e667e9f39ce795ec3e23a766a9d8152599b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/GROW_S2_W02_Knowledge_Organiser.html": "8c9d57644d1062563f93026c4d56405b774765cb6258485bfda0d96f9fee4259",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/GROW_S2_W02_Knowledge_Organiser.pdf": "5d7ee3ca595c89b99f65ea46367226f4089b74d669872d3c039b0b8752e09297",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/GROW_S2_W02_Lesson.html": "2e524c7bb62db6286d6358c942b7b27d7912cc0351f65d76626df6ffe8289529",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/GROW_S2_W02_Model_Transcript.txt": "0d9b7c0275ca720fea53f9f0ddb6a0f3d76a173f47acbe594a60d4e4f0275499",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/GROW_S2_W02_Pupil_Resources.html": "baaf6c33a42814de71fb9344328bb59f50b724709508a7791176060ec78b4ba4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/GROW_S2_W02_Pupil_Resources.pdf": "0f28bd4c0692c29565057cb7ee62bab052bf3d627640d288fd5638c908f3b0bc",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/GROW_S2_W02_Teacher_Notes.docx": "99781339e4d1129fd96d15d5812091c7128b62d5bc5f72c05f195339980a9b4d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/GROW_S2_W02_Teacher_Notes.pdf": "28b9ba1e3d1640c8cf383de90f9936d45423a954132bc791a97c632bfafb78e1",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/Teaching_Visual_1.svg": "8f7cae4fa423ab28d05244d1b48c17505d5e72e2952b76f8aad7069786f3c520",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/Visual_Resource.png": "0f96a55d6405a398804886a9feadb0eba2f930f703f8e5f511fe68fa18f17acd",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/GROW_S2_W03_Captioned_Model.mp4": "805b49b4986d5dfe5f30d851ddae6a11312c427610640f453cab987286a65b03",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/GROW_S2_W03_Data.csv": "ffcbd21d28f67f773a0a1db286616663120706acc2c97f3276529b8681f35f65",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/GROW_S2_W03_Data.xlsx": "78760a01bc2455d43f217f304aa6c731c6914e9e5a7e9d186a97610807d58dda",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/GROW_S2_W03_Editable_Pack.docx": "2c1ce167ecb7cc3b487badc9dcc594b8485d36cbd6f90c87ae8d19bacd6e9544",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/GROW_S2_W03_Editable_Slides.pptx": "c5cf1cf073e298058bab2032cbf80a587066426e7cb467159e570b24c68333d2",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/GROW_S2_W03_Knowledge_Organiser.html": "7cb35e3120d7a014246c8f4e15420cadf98b67a4b7e08b29ccc087fce6724679",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/GROW_S2_W03_Knowledge_Organiser.pdf": "ebd1a9d945314cef728ee5bdca06afaacb58f24c3edec3a03b9e319421fdbe60",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/GROW_S2_W03_Lesson.html": "4e8322859058262f288aa95e4c9a9428217672d9a8817205e47abd0b495cac3f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/GROW_S2_W03_Model_Transcript.txt": "cddc8694a0ae67723604cdcab489fa3c57a2bc48b3599542f6993b1b7328ef76",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/GROW_S2_W03_Pupil_Resources.html": "6774d43d76ab948384d74123c9c190096aaa2627d1ba8eded9f25533278f84a1",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/GROW_S2_W03_Pupil_Resources.pdf": "a3b7c4b1b121f7c38ba81879904c33afb18bf15365ab4aa709142c34e3db299d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/GROW_S2_W03_Teacher_Notes.docx": "de1cb792c8a609c4fb84b852ab2bb33ea9f1b1945b96cba22c7f7d5606fe3f22",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/GROW_S2_W03_Teacher_Notes.pdf": "3c2b52467daf5e82cadf629a2f2b1fdb421bc2014a68ea0f86d3fb360f03e405",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/Teaching_Visual_1.svg": "8f7cae4fa423ab28d05244d1b48c17505d5e72e2952b76f8aad7069786f3c520",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/Visual_Resource.png": "b9fa6ca7283096404cac3ff43fa39ef9403d0f2b2cd0fc7a6d35d9ad3a6be65b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/GROW_S2_W04_Captioned_Model.mp4": "622458666ffccea30fbd6062855a6f16e7b625509151a6f6e533f1262d4c755e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/GROW_S2_W04_Editable_Pack.docx": "5692d5ca9486388ab4b782cb4de7f28e173e54f4397bf046e868622cbfa73892",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/GROW_S2_W04_Editable_Slides.pptx": "adaefba84022c1a1429f21486432861036dfa761e84245d6639439c8a1f18baf",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/GROW_S2_W04_Knowledge_Organiser.html": "ecf2fc05f7f1c7234d1b59bbbb6d4fc22dacf017c1c221de3187ea266f15410c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/GROW_S2_W04_Knowledge_Organiser.pdf": "a043976e08be076b69404ee93a35b9496d0d95d71cb350bfbecc1533e6229416",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/GROW_S2_W04_Lesson.html": "23bd45f0afb1b4463c549812b01d4bd49959dfd464f15d7030810ceb1f1f1374",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/GROW_S2_W04_Model_Transcript.txt": "2877fe896b44d98607f6662366a66c658a4b481a15118f063c1f7e07aeb8892c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/GROW_S2_W04_Pupil_Resources.html": "ad43ac5cf48547284489f47429ea005884fd57a2aac47d11066f0e370e68ad17",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/GROW_S2_W04_Pupil_Resources.pdf": "b4b9b8e069ab0012dbebe537dbfd090360e0dccd9d92d5f88a608c5274090b16",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/GROW_S2_W04_Teacher_Notes.docx": "9e443e8b9ab93897c25bf671657b0d2529a804e703974a466c1a2262180cca15",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/GROW_S2_W04_Teacher_Notes.pdf": "d6b96ecfbfec01fe2465c79da2e8394e04ad75f09dc5b25f81ef95ae042b195b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/Teaching_Visual_1.svg": "8f7cae4fa423ab28d05244d1b48c17505d5e72e2952b76f8aad7069786f3c520",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/Visual_Resource.png": "90ce3f59d06b5b3435cedcea8ad674e57925f4c4c744c4bb960f4fcb3b9e491c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/GROW_S2_W05_Captioned_Model.mp4": "41257b671a428398dedb9026345d7508eda65784df8955aebec21fbec39faf6e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/GROW_S2_W05_Data.csv": "ffcbd21d28f67f773a0a1db286616663120706acc2c97f3276529b8681f35f65",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/GROW_S2_W05_Data.xlsx": "294610ded0a138a37cbe703af0886e1c7ee8d76d37bf4d4bd43af7833258aa08",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/GROW_S2_W05_Editable_Pack.docx": "96c038632c23b6356790c42be1c66d01da404a2a9b5f300832114dfbf24664ce",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/GROW_S2_W05_Editable_Slides.pptx": "0787d7dd4750ab6207ff7d18ad7a76e2e0a641b12f4491a00a704d9af5a0f668",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/GROW_S2_W05_Knowledge_Organiser.html": "a131cad9a27c6dfd7e0c481004a6d92319bb5301471fb5bf41e394c8ed566e91",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/GROW_S2_W05_Knowledge_Organiser.pdf": "0e9ee70e89f3acd290468df257e2302dbecfa4f4c484936df724ab0dc17991ba",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/GROW_S2_W05_Lesson.html": "6d1048a3bb47d05668af0794ea64c5b22bd311c0a0392b5c6ab434c650628e51",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/GROW_S2_W05_Model_Transcript.txt": "32cba47957cb55e253e4917c024445b703ff6568b75eb101480158ea66053397",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/GROW_S2_W05_Pupil_Resources.html": "86e020ac2b14dd216da5f08439246a3db6d01948376b5433af7404dfc7f5ae2f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/GROW_S2_W05_Pupil_Resources.pdf": "031135f64b61158c5c63f0947882785eb8db0983de165941009c797a6670ffc1",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/GROW_S2_W05_Teacher_Notes.docx": "440724f6d2b31ebe7b9752d245e97fb85491eafb2e1734e6962afa33e7e1850b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/GROW_S2_W05_Teacher_Notes.pdf": "d05a2580b16ffcfcff4bcc71d5afcb11ba7f537a8750de7a5772d5decd3426af",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/Teaching_Visual_1.svg": "8f7cae4fa423ab28d05244d1b48c17505d5e72e2952b76f8aad7069786f3c520",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/Visual_Resource.png": "ebbd77e335efc545ca3950bcdb12c8e3885cdcd22409a7dfdca140b1b8dc0466",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/GROW_S2_W06_Captioned_Model.mp4": "cc96d3b6227729cd6df44aec1e4c759c527d3b6b343f6d87d2f3144eb9260e89",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/GROW_S2_W06_Data.csv": "ffcbd21d28f67f773a0a1db286616663120706acc2c97f3276529b8681f35f65",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/GROW_S2_W06_Data.xlsx": "eff96477eeff570c20d43ff876527fc92981c44b9d14ca0c79b2b7ee94802bd0",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/GROW_S2_W06_Editable_Pack.docx": "3944f6d3e864725d96615ab3b1291378c6c91c96055f43471006ce843e240718",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/GROW_S2_W06_Editable_Slides.pptx": "9b945379310aa897c3a7b376c76cddee0a773ba0f5f3ae9454e0b049d4b672bf",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/GROW_S2_W06_Knowledge_Organiser.html": "a9536f965ca249713a25edcf85638697011ad603e238bb2de78f61a15c128642",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/GROW_S2_W06_Knowledge_Organiser.pdf": "15740204ed7f2b9767dc1cf4590953f031dc641dc45192d622631a395f75d2d7",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/GROW_S2_W06_Lesson.html": "a873fcf4c430f874f9c2e661cf88ec3996bf30691a695f1a6e75f85ae1eeedd4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/GROW_S2_W06_Model_Transcript.txt": "09f5bb6244791695b3ca404103f12e14f8a328d8286f08964b06829fab71f8e2",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/GROW_S2_W06_Pupil_Resources.html": "732e1c15ff619a8a929049374d80407aad5b08b087a770f2a041d6bfaf575721",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/GROW_S2_W06_Pupil_Resources.pdf": "62211656b8746bcf61f6cacd15cb8643871b924dc4e5d362b488288f264d43e8",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/GROW_S2_W06_Teacher_Notes.docx": "c92981b1a2a2963558ee86e915a8a1779a70a64d28dbbeb4d1f0b802b4e5ca96",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/GROW_S2_W06_Teacher_Notes.pdf": "785207f8f056d542da4f0820980ff838ba194c6a900877f53303b14847ba094a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/Teaching_Visual_1.svg": "8f7cae4fa423ab28d05244d1b48c17505d5e72e2952b76f8aad7069786f3c520",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/Visual_Resource.png": "b6e539a6d2e27d17238e73c0ccc63edccbca2402f5600a112b47299563e943eb",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/README.txt": "b18e6a10681a2287090de194cb29747da642f300b3a25d7c11b3b45bcd814714",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/Review_record.html": "6b8e5f91c2d3dc34865b656de4cc258870d97566df3ae5fc5022cd78e06d36f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/SHA256SUMS.txt": "01f5fa20dd3443c163bb5110e92a9ef65423296401b91d5dd5794382a1c86868",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/START_HERE.html": "53c772cfb5d7526f9c9c82140f3aa9555fb38e7f00f09cde1e4ede845aa87ae1",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/CHANGELOG_Final_2026-09-19.md": "857699afc8f0520c38f594936bc023d99b0d4424bf4a26b7029ceccd2cd0dcc6",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/LAUNCH_S2_W01_Captioned_Model.mp4": "9a0e87be9419c56f2a1bdfe3eecd564aba26e6fa1d5d60a3dce085f28d63b40a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/LAUNCH_S2_W01_Editable_Pack.docx": "a4192b700de5991c81ff54291d4181c8ddf616587472672a322d3e30b6c78ea5",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/LAUNCH_S2_W01_Editable_Slides.pptx": "71971304398df72e895264d228887825e19cdc4ce83d8a807ce20b676dadfb2c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/LAUNCH_S2_W01_Knowledge_Organiser.html": "83a49ed848410f78709c8c45851010a7ed2266c83ed9cd4fdc24ac64cc6995bc",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/LAUNCH_S2_W01_Knowledge_Organiser.pdf": "5087fff8b22917824318c90a66f864cb681e9ce2fcfe1ef0d624353d4d111990",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/LAUNCH_S2_W01_Lesson.html": "e0e69e4563850ec5a9f64161f60ee1d4fcce54f0b7b433347ebe635dd9080511",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/LAUNCH_S2_W01_Model_Transcript.txt": "362620f6b3d2f500e54e4ffb41f4cb9a46718f26da7ef5a503d517535ff7e2a4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/LAUNCH_S2_W01_Pupil_Resources.html": "cdee9ffd4a206e5c69a19c917c6ff23ec8689cdeab87dbf290fd962aa043e5f5",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/LAUNCH_S2_W01_Pupil_Resources.pdf": "903b9eba7c9f93ef598f6c90113b65f5546da26c05aab8462df8bbc3842fb1e0",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/LAUNCH_S2_W01_Teacher_Notes.docx": "9d9df1e80fb0a9657ed5eb0c9758ffd7cae1434257679d9c46c84b9c8ce370b0",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/LAUNCH_S2_W01_Teacher_Notes.pdf": "8956bad7a5e6ef88330ab7b117a203dabed4afc84e55ba8933e69f9fcf7e1cdf",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/Teaching_Visual_1.svg": "8f7cae4fa423ab28d05244d1b48c17505d5e72e2952b76f8aad7069786f3c520",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/Visual_Resource.png": "3e5345c5b4918f9eb50521b622f3f5fae2487529bbce501ea1bc4cf72c4f8fca",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/LAUNCH_S2_W02_Captioned_Model.mp4": "6661f95d330592522246e30a43dd5381808f9b6b2eceb2f234e56fa7d01f948f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/LAUNCH_S2_W02_Data.csv": "160d63fe810ae3fb1575545a41cc720703a167cb0abfe4f5376f16c944b6fb91",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/LAUNCH_S2_W02_Data.xlsx": "f17bef8ef23f197494bb9b29774b7a00482af03f2e6a500d02e319b2233bf786",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/LAUNCH_S2_W02_Editable_Pack.docx": "dfee11f3bb8a218501f3fc0e2d86c6ac733e34a61d96efb1ce55a2a464de8800",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/LAUNCH_S2_W02_Editable_Slides.pptx": "e825a948628dd813b33a414746f4d7d4d273597c614367b2d48b5db065b86364",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/LAUNCH_S2_W02_Knowledge_Organiser.html": "260cca5b25a988e148c277bbc3e2b001ac9df081440c0defd8d6ad973d81b3d8",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/LAUNCH_S2_W02_Knowledge_Organiser.pdf": "3d32f7dd9e77aaacca413e0e8b2e5a4742b0aafe1bff46d3ee9920402a0f9f23",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/LAUNCH_S2_W02_Lesson.html": "103b56f769f430b8c7c5b9fd956c8df92d19d2c73bcd14f04155c50b6f496765",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/LAUNCH_S2_W02_Model_Transcript.txt": "026618123307caaf9b9aa36109d835259d98529264b6c466e8ed6be415ba3f20",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/LAUNCH_S2_W02_Pupil_Resources.html": "841bf9b7e80ef8bed45711bf0f9c80a31a6c545b6411d501aa0134399481b509",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/LAUNCH_S2_W02_Pupil_Resources.pdf": "aca646721d654a295a37d0990b653cdcbb0e6222046aabc5acae39e41a76eea3",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/LAUNCH_S2_W02_Teacher_Notes.docx": "bd0a9154625f6763e4e32ea62fa4348b52102f5596080c2eb8359fbe6f198e71",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/LAUNCH_S2_W02_Teacher_Notes.pdf": "90722f5af7f760e54590198a1999e26266a945ca5346840155f128a6fcec788a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/Teaching_Visual_1.svg": "8f7cae4fa423ab28d05244d1b48c17505d5e72e2952b76f8aad7069786f3c520",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/Visual_Resource.png": "98b88afea2cde3d82fe7380a61a7d1207e6cba97d79aff350e94e3ed59059500",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/LAUNCH_S2_W03_Captioned_Model.mp4": "5ba6ffdd5c2937a9a95013afef91c7a14145a033a889b4e9ffcd693ccca72a19",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/LAUNCH_S2_W03_Editable_Pack.docx": "2a7dcdd24fce359d62ff632bb0ebd34d314578531be7a68afc3b8e0826d1ca4b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/LAUNCH_S2_W03_Editable_Slides.pptx": "7b2ce742b31f58b62b2f7c8c96300b95f8c98ff5d5f1b99dd038729091d83553",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/LAUNCH_S2_W03_Knowledge_Organiser.html": "69b98e7b47589f57d4f3be4d1c0596b59c597ab887f8d92ab9527151512d1b3b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/LAUNCH_S2_W03_Knowledge_Organiser.pdf": "493ab9136e8ff2b841aed20263592bc2b46ab6a61dfad1aac1846b0dc1f1e694",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/LAUNCH_S2_W03_Lesson.html": "1b9780286d7bfa9c12b817b8d3e8baa0d0f3e26d09e3c2f2c545352942421392",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/LAUNCH_S2_W03_Model_Transcript.txt": "a443e63904492f969dc4ad94c745c60633ec71ddc4de99d47fc53919e11464e0",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/LAUNCH_S2_W03_Pupil_Resources.html": "d6d24ecfe6d6264cf548b2d8d17271d8708cf0862e7cd3db8328833008aecfcc",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/LAUNCH_S2_W03_Pupil_Resources.pdf": "eb47f792bed1f03e2d8dbebb5a9f85ad76a664fc28615dc0d207af6a0b5265e3",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/LAUNCH_S2_W03_Teacher_Notes.docx": "df2c6dcdda80882f46079ad9907be4c9e7e0a9c1b20555a83b4f3ff06f384586",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/LAUNCH_S2_W03_Teacher_Notes.pdf": "36bdc6cb1e654ba6b61f4fc83ad00ecf22beb503748d1047438c025c207b8eff",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/Teaching_Visual_1.svg": "8f7cae4fa423ab28d05244d1b48c17505d5e72e2952b76f8aad7069786f3c520",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/Visual_Resource.png": "7cabea1f2e13f001ef36fcf814a7a46be9f69695c82857a36c5b0d7d32983d57",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/LAUNCH_S2_W04_Captioned_Model.mp4": "a5c9ae1530e660e95ef831892029534fa1ca11a6309c8cbfbc58e0829afb231c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/LAUNCH_S2_W04_Data.csv": "fd2c0aefe55d58b03f767f02618b0b00c45cf2148d7c189f73ac2c81db4df6a4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/LAUNCH_S2_W04_Data.xlsx": "fc3d0bce7a41c66699e5ab11457c91d89a85d823e61c88cc928228fa747f44e5",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/LAUNCH_S2_W04_Editable_Pack.docx": "5fa32238cd2e97eb01d98b815cbd2ea9cf82b0d268bab89022b9d83ba9a11f2f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/LAUNCH_S2_W04_Editable_Slides.pptx": "141a5040b78b9f594fb89a4750c519a31518533fb8b837e9acfee9e049337a5e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/LAUNCH_S2_W04_Knowledge_Organiser.html": "16ffb72bf901130d6191dd52cde8d0518abbbc47a07f8f8fe45369f0064d6075",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/LAUNCH_S2_W04_Knowledge_Organiser.pdf": "503fbf2f1dc601f8dcf448039ab19b88999a5ce605696161a4ea6a80a0a972ae",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/LAUNCH_S2_W04_Lesson.html": "42e5db483bc0b30bee15b0bf85ebb86184026e83b0eea524e5cee342e79a988c",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/LAUNCH_S2_W04_Model_Transcript.txt": "bd61ee242dff77e51d7d859459ad6966fd0b72de726895ab09aacfc78956310e",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/LAUNCH_S2_W04_Pupil_Resources.html": "cde08376ad87c3da7337519600f69e537239baf854b9147b30b8c12178d9bba3",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/LAUNCH_S2_W04_Pupil_Resources.pdf": "a09ceca830f4a973530412ad5c470432bec2dca87301f3629339e8dfe3083b9a",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/LAUNCH_S2_W04_Teacher_Notes.docx": "1c69f2e3a75a4604fb511b961511333753a7fbf184e1b3a424af0dbeab5b27b4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/LAUNCH_S2_W04_Teacher_Notes.pdf": "44e33c2fe39b41cddd6cfb77c1c05ea2cac0ba53b0adce6d46ddd43173c584c7",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/Teaching_Visual_1.svg": "8f7cae4fa423ab28d05244d1b48c17505d5e72e2952b76f8aad7069786f3c520",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/Visual_Resource.png": "391570f4cb1008b8078865708f8051e3b2a9a75d48e66a68ace843c4caa10f17",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/LAUNCH_S2_W05_Captioned_Model.mp4": "27f35472c63180625e5ba4ab269887c730c07af0fa98becfde0040099877f803",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/LAUNCH_S2_W05_Data.csv": "fd2c0aefe55d58b03f767f02618b0b00c45cf2148d7c189f73ac2c81db4df6a4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/LAUNCH_S2_W05_Data.xlsx": "19fafabd49c876e6a311ac322e69cbe2fe73dde0ef0e43b64f1ddeb221893ba6",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/LAUNCH_S2_W05_Editable_Pack.docx": "55b44a6073dc895915120d752512162dd9abaada0937b8a9685e7e36f41a2c80",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/LAUNCH_S2_W05_Editable_Slides.pptx": "2540afce7c6e1143ff6a8ec61c5708440af49c276d7f49a112d18a7496e4779d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/LAUNCH_S2_W05_Knowledge_Organiser.html": "67cbc77696cb725186a8f97c0bb003c7840da9c0b651234b5a1674b1e3d73838",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/LAUNCH_S2_W05_Knowledge_Organiser.pdf": "0cb9147ee20df8e8b35e1d367a8119439bb680e88437001e2d38f072417d0cae",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/LAUNCH_S2_W05_Lesson.html": "7f8e66670e322a175a9a2314b41a6e2a5bb59da8ab712fa9b5831198aded0ced",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/LAUNCH_S2_W05_Model_Transcript.txt": "2b4e069aa35333bcb5e7cf59878d9d2c500b9798143b97c92fa4906f6a04699b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/LAUNCH_S2_W05_Pupil_Resources.html": "dcbb7caeb0435f4af5bfe10d169775349a0478a388ec6978f604ef5b84dfffb4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/LAUNCH_S2_W05_Pupil_Resources.pdf": "6720377929aae48972366ccf097b7fa714ee3017f4914e0f9b69608271a2d834",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/LAUNCH_S2_W05_Teacher_Notes.docx": "ecaecb42e60093f9987e42c8c3420a955cc029d28fefa6379f1e776a803609e4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/LAUNCH_S2_W05_Teacher_Notes.pdf": "13017cc387c96b3c4fdb1bcd5b353e040a0bd571d377332a6e033e22c2c4543f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/Teaching_Visual_1.svg": "8f7cae4fa423ab28d05244d1b48c17505d5e72e2952b76f8aad7069786f3c520",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/Visual_Resource.png": "4da7c6c332c847067f96ab1929c784a923d0e8704291a18ff5c25bf4ea000cad",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/LAUNCH_S2_W06_Captioned_Model.mp4": "014e4ea2f67d1221a1a3affc7081b392907ebbaeafa60d73023fab7f770b42ba",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/LAUNCH_S2_W06_Data.csv": "fd2c0aefe55d58b03f767f02618b0b00c45cf2148d7c189f73ac2c81db4df6a4",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/LAUNCH_S2_W06_Data.xlsx": "2461052f6d02c589c79628d95eb0525a473dad3670a70db66a55e25b45a072cb",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/LAUNCH_S2_W06_Editable_Pack.docx": "56af850faac29228475c8e9a86cef804f67b77c81dd2fa442d4e972f9b7f9d13",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/LAUNCH_S2_W06_Editable_Slides.pptx": "4f22bd67289d67944fe7c2810d5f8c34816b2bacee8c3702f2a007d29323cf9f",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/LAUNCH_S2_W06_Knowledge_Organiser.html": "89956089d1f82b00599c2ae0d86dab1be4dc32b6b11968fbf7b001ab1d2714a2",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/LAUNCH_S2_W06_Knowledge_Organiser.pdf": "87e5fc052f1a4526bde43fdf77480198d3a6ff6aa2c0b6a875fefeadb03fcb10",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/LAUNCH_S2_W06_Lesson.html": "464bec59cced0ac71ade394267959992970bb6c16bf81cad6f21f0321b6936fc",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/LAUNCH_S2_W06_Model_Transcript.txt": "846c8d60560500bfbb9de532fa19c698b2f608e62f588c7e1c80b0337361e728",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/LAUNCH_S2_W06_Pupil_Resources.html": "2b0c45194a305706c55de8801ee185c859739695418b30eaa8c0df26f7164e3d",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/LAUNCH_S2_W06_Pupil_Resources.pdf": "f2eb513ef8d00eeb11255e504f5fe4393ec7d2959cfa1b2e9368a94aef96e540",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/LAUNCH_S2_W06_Teacher_Notes.docx": "0d459423d7d6f63b5af82b54af958dbe38c32bf1a7ee512f0ae244feaa619a96",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/LAUNCH_S2_W06_Teacher_Notes.pdf": "ea2d55c1fc67dba0980292c9e8070348981b343a0fad8b6f09caa700645b134b",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/Teaching_Visual_1.png": "d91d12b6ebd6fba9555f0ca5711a27bba3ace8ff0e136344855d4f4af24cad61",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/Teaching_Visual_1.svg": "8f7cae4fa423ab28d05244d1b48c17505d5e72e2952b76f8aad7069786f3c520",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/Visual_Resource.png": "0f22f641e33d30564c6b3c791b2b2405dd8c5e4c5d10b782e4a229c0273ac641",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/README.txt": "b18e6a10681a2287090de194cb29747da642f300b3a25d7c11b3b45bcd814714",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/Review_record.html": "de002df984bf0dd59a4a4c73201329b3b5ab378ac812b40e867e43cc943098bf",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/SHA256SUMS.txt": "1e780dcd5706ac2551fe8891ec14febac9d05c53febe8da9f8c142f41b7d1d08",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/START_HERE.html": "4f43aae1069ea1ed914642d2839d35cc1d2343343c32f7cf49ef546e58ad6c12",
        "Humanities_Teesside/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/BUILD_RE_A1_W01_Captioned_Model.mp4": "0a82e0b3378244bfa38caf1540adbc0aa0a88b872ee0ad75c0c485c65ad04e78",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/BUILD_RE_A1_W01_Editable_Pack.docx": "b4454e912218650792361c9c382bfecc8f40c50bc6602abdb5089652151441a1",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/BUILD_RE_A1_W01_Editable_Slides.pptx": "77336ac4b08e76c2640b3433624cd01f1d70bffb45d99d858692b401de5dad84",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/BUILD_RE_A1_W01_Knowledge_Organiser.html": "1f7eb77a4004b39e19da59097f54b60a5a9a35e4283a7241a2d74731c22064d0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/BUILD_RE_A1_W01_Knowledge_Organiser.pdf": "f6948e92a23b7813380f85d51b14f0fc2d9fba72e4fc45393997be5d569955fe",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/BUILD_RE_A1_W01_Lesson.html": "390078134c9090fe2f7d9159500baffdb3b54544771d94b274262325564700ad",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/BUILD_RE_A1_W01_Model_Transcript.txt": "ab3514ed2ef7cc770c055960bd2657be8853795a97b0a43c7c18c922e1328bd8",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/BUILD_RE_A1_W01_Pupil_Resources.html": "e180a56835244ddb0e189704375684c70b76bbcdf1b891d953d18349957c37a3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/BUILD_RE_A1_W01_Pupil_Resources.pdf": "1af6c1195c5cb7e459e182bdece214c9c1dc87be9518c23c4200ebc206df2218",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/BUILD_RE_A1_W01_Teacher_Notes.docx": "d2a591fd3d1430bb0688ff1d65df856ee7a588897baecacfad6f83072a5f36d8",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/BUILD_RE_A1_W01_Teacher_Notes.pdf": "c918882f8f1f51b3c9618f5e10956ec86e6562f4d6a110de33feef559dc9ede9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/Object_Picture_Choices.png": "f9453352ce89a7872cb91b7b57eaea1f571e359415be3cf89eedc55bead3c87f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/Object_Picture_Choices.svg": "976a037dec431ce2e2c90b0bf5f51d72adc57a267a34fc71a3d005d32e92a064",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/BUILD_RE_A1_W02_Captioned_Model.mp4": "62b23fbdc31bc2c979376bef8b1f1c5e19bf175d2d450ba2dd44bc2e08a96d29",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/BUILD_RE_A1_W02_Editable_Pack.docx": "1c38cd86799c0c7cceb3304b081359b04a27fab020804b827801c2fdff9c6844",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/BUILD_RE_A1_W02_Editable_Slides.pptx": "688319365e3be18c8542b2e2a0672d623a01ae0075fc2cb7a4df3326393c853e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/BUILD_RE_A1_W02_Knowledge_Organiser.html": "bb2c9af1ec53692c0cb36f36d43cd1e018cb429cb9b220676d1d48f9bdbd57ba",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/BUILD_RE_A1_W02_Knowledge_Organiser.pdf": "c32cb2958350c07ccc682b51299a98524f7e6c5933de37939cb2769cb75319c4",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/BUILD_RE_A1_W02_Lesson.html": "94b0caec44a162ef9befde813a9fb4139c893b0f72c2953448256cd5cb9d0a08",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/BUILD_RE_A1_W02_Model_Transcript.txt": "793c49570f5297a3e9c1b5e5eb8d0bd2aa3e62ce5a3d60b831315336bd3dee47",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/BUILD_RE_A1_W02_Pupil_Resources.html": "5bbc3693153ae48f812dc427adf93046c28e32590ab7e3876dde1ed19318c6cb",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/BUILD_RE_A1_W02_Pupil_Resources.pdf": "6c12e54550c83b57e9d2b9ad86670342ed3bb3fc0bfc0b984fe931e4a41fe488",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/BUILD_RE_A1_W02_Teacher_Notes.docx": "613b85e4b1a617228b7b0f3a2859052ac988348006445c1d9898bc716457608f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/BUILD_RE_A1_W02_Teacher_Notes.pdf": "c15e57d6123c2039e39179b7136f0af856c68838490035f74209cc6b0b9b6cb4",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/Object_Picture_Choices.png": "7f2a95af1a056585d041d66f0a34831d9bcbec0f229eaaf4702220331c2f3442",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/Object_Picture_Choices.svg": "c0d22cd7dbb3d5256a8237360f0f0115c44a3a930b9a9c28ac953c20878c3378",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/BUILD_RE_A1_W03_Captioned_Model.mp4": "b6150b49401c46f986afc13c3435688bef7ff12545d9a3aa1435829b2f8e1dde",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/BUILD_RE_A1_W03_Editable_Pack.docx": "b0b3d3515ebd265a5fa606b7aa5f3cf362b81a68e00f7b1038d7fc1df63738f2",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/BUILD_RE_A1_W03_Editable_Slides.pptx": "a26201a5739abd9127539648ff2dafc3af06de05c20c84b1095d210a79676a50",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/BUILD_RE_A1_W03_Knowledge_Organiser.html": "529411dcf03bd87af5cdba92512cbd6655599b27898d097ab849b61e56115783",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/BUILD_RE_A1_W03_Knowledge_Organiser.pdf": "71d27e2317126350ba1c9309fcd11b7e64f90b58e262509ddfc6658dc566a769",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/BUILD_RE_A1_W03_Lesson.html": "87c4379cdfcbef45d43f4d60d78ef0b2624542cda98c808d0b5a88773dd2e235",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/BUILD_RE_A1_W03_Model_Transcript.txt": "b974c3a25af6523927cc9c3c7dbed9fdbd5bbcabcda86d5e58d6f0131a97d360",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/BUILD_RE_A1_W03_Pupil_Resources.html": "f394e65ba287898142b105785c6125833f037b19743a251d239d5f8d8940880d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/BUILD_RE_A1_W03_Pupil_Resources.pdf": "f1197d6be21f3ef7550f5dd0bf5b2e08e533b743b40b10117f49c83fc2a6c61d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/BUILD_RE_A1_W03_Teacher_Notes.docx": "cdd682f0e2af3f476e34ce021b511e6563b75e54643343a7c9bd188a8096bf62",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/BUILD_RE_A1_W03_Teacher_Notes.pdf": "10276273cf658bf22560bf6af304f04ddae569a2a799b448b6bdd3e722064744",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/Object_Picture_Choices.png": "571b2eccc136ec164fd43d01025e43160511e158891c40f446472addf1238c98",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/Object_Picture_Choices.svg": "fdc3395493d0f7af6f7a5b58d73b2ca74c2886eff9b7ff954d9d011075acf625",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/BUILD_RE_A1_W04_Captioned_Model.mp4": "e08a748c281a1e922dc8bd7101ce27410909087d20f71b1a01b4c9a44485eafe",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/BUILD_RE_A1_W04_Editable_Pack.docx": "3c0acbac2ecc5c4e7703427d15e7beb9c3efdbb8bc4b4fb13cc0dbf64be860b1",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/BUILD_RE_A1_W04_Editable_Slides.pptx": "e3df3d9fb85b3cf65e7a3cc6f65cf93f42cd39d164d74de3b1a6bbbce14bfb68",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/BUILD_RE_A1_W04_Knowledge_Organiser.html": "98706606e566de83223d9cf2dc88b2f4b1102e8000230da66b546e13e9e1b9bd",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/BUILD_RE_A1_W04_Knowledge_Organiser.pdf": "a68dd624e9822a41febd06b1220718838c14d686383ba0fe38bf87a396973dca",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/BUILD_RE_A1_W04_Lesson.html": "24251d8d2063421143c7c5e562f4c74d6f0ba97b972ecb96913be0b1a00815d5",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/BUILD_RE_A1_W04_Model_Transcript.txt": "b8c5b5c4230cb6bdc0f3559fdc882a1e4a9dff36f804a719fa522acdb6ec7a24",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/BUILD_RE_A1_W04_Pupil_Resources.html": "b9190ee884e5ecbf14cc0f59104a4fb2bfb0a8e77f9a963d4deffd65b9742e39",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/BUILD_RE_A1_W04_Pupil_Resources.pdf": "84b7dac1e6f049fe56b4563cadad511245aa1bb1f0ff7bfdb9f803eed54f5991",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/BUILD_RE_A1_W04_Teacher_Notes.docx": "8e4b6e45ce5de38575f07b59848be5430e73a65dca64a50efdfed60aab2d93d0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/BUILD_RE_A1_W04_Teacher_Notes.pdf": "db2d77ef2d2e9864149acff40655a4b6f3a2ded7705ad8a0cc47f2a20971ec00",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/Object_Picture_Choices.png": "7aaa780c175352a09edd65fc3ddd6952886ff3f3ddf2469e2813726f4aaf8b43",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/Object_Picture_Choices.svg": "4ed7f6c6c652b563005b84adb67f933ae8b4dc33e5b4eee4886992bc683c1340",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/BUILD_RE_A1_W05_Captioned_Model.mp4": "55c8843fa061cfa0b20ac10be050d27b027c52a1dccaf80c6373bd4adcbda625",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/BUILD_RE_A1_W05_Editable_Pack.docx": "4e16645b41c56bf8642a53c52fa38fc57006ae323e54858aa28d5d138ae54071",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/BUILD_RE_A1_W05_Editable_Slides.pptx": "7b2d056ca84d075ab7caa29af69239dbaad07b2d50224992f9013d7f68b06f55",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/BUILD_RE_A1_W05_Knowledge_Organiser.html": "94dbed62024a6bb63d5797e76f5f963c03f7fc93e0457238e9464eb25563e47c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/BUILD_RE_A1_W05_Knowledge_Organiser.pdf": "196e1d9e7f8e349088e18d4e83ffb779590cc3151457dd520d7a81d7f0888a1c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/BUILD_RE_A1_W05_Lesson.html": "e4ea7f65de4eb38684d2442717755e5ec5c4d715227479df430ea3e7c404bfb5",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/BUILD_RE_A1_W05_Model_Transcript.txt": "79cbc0ddadb07449b6365244f0a09f0811217d558cbeeaa0e43ef889c4dcc005",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/BUILD_RE_A1_W05_Pupil_Resources.html": "88386c20676f6b5c6332e2b0a41c64da82cf6dde1a08b8d710cc7e04a832c0aa",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/BUILD_RE_A1_W05_Pupil_Resources.pdf": "7f91fb4c46c0a464adf15e8444a67ac7c9363d9ee495f757631b49f7a487ff51",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/BUILD_RE_A1_W05_Teacher_Notes.docx": "f435585a6d3c07b0b18322fb0841468fbb083ddf3a855298eec975502b730b99",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/BUILD_RE_A1_W05_Teacher_Notes.pdf": "fa22e7abf5a709ad17e86b11c781e84c2707d0397c86876cc792acad3e576014",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/Object_Picture_Choices.png": "aeee84c34c480438eebeb9f67ee90285831e649f509ea782352787bbe239551a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/Object_Picture_Choices.svg": "f0ebdc0a943f0a3b435fa4797da247f920449549d07e062da9bfdc51eecbb22c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/BUILD_RE_A1_W06_Captioned_Model.mp4": "b731e2158080e4fde8607731be0f5059e2fbfe69dd12119ec9f3574b5c76c47b",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/BUILD_RE_A1_W06_Editable_Pack.docx": "ced23ff5ea05eff2333cb4a99ce5cd73fca41a94644f8fe6b5d7877b5fe3adc1",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/BUILD_RE_A1_W06_Editable_Slides.pptx": "b814f14f2531a7eb5d0250f6625b9df9444c7d078fbfb7a2aacd0318b8b41897",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/BUILD_RE_A1_W06_Knowledge_Organiser.html": "cadce94b53cbdbf9ad2d89a7d4f5422d5918e3270131b4bc6205a3baf65a96c4",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/BUILD_RE_A1_W06_Knowledge_Organiser.pdf": "c9c974efd1d3da603e16898d5e39f2c72ceb23c59ba75353717b6eced9cf8d73",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/BUILD_RE_A1_W06_Lesson.html": "e31fa9fe9ea11eb6de8aa79c428c56c77efe0617e06c26c6c5630221983cea1a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/BUILD_RE_A1_W06_Model_Transcript.txt": "3db4bbb71bf036f010284a8428475b7c1447a3a4bd552a868d403fe24a1e81ed",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/BUILD_RE_A1_W06_Pupil_Resources.html": "b8d86114ee5d3f520269d2866e8348bc6cba6cb66dc2576279a689de7d2ed0bf",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/BUILD_RE_A1_W06_Pupil_Resources.pdf": "be43b8e4e76b8d6bcb82462c3632599ec0692f4472d17eec60aaaf891a11e652",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/BUILD_RE_A1_W06_Teacher_Notes.docx": "e6cf22e34e6d5b56cc9f5fdff4bab30717196b09b1f15637afbbffdf31274dda",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/BUILD_RE_A1_W06_Teacher_Notes.pdf": "0e0a9d814303a71d42f5edeec43e5bb2bf560b958a252af4cd5210ed906dd1e3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/Object_Picture_Choices.png": "00815cd505861c7cc62279db569ed101a634d99efda10b79abcb0b4142260713",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/Object_Picture_Choices.svg": "171685356d7d8632ae9aa3ab8e059275cd7d7a3261a01d6bdf6ee896715625cb",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/BUILD_RE_A1_W07_Captioned_Model.mp4": "08b7cb6d6d2704ed545c551a164f629b7aae9e19e45c1386f6f1f139d428c4b9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/BUILD_RE_A1_W07_Editable_Pack.docx": "4819c0f71ec69fa82e1adb36ab08f609285e0f5f2f33a7691edd3c6c821e115f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/BUILD_RE_A1_W07_Editable_Slides.pptx": "a8c9f35e96649a5c182b36378f432e61a7cce898a530bdaa6c73cc9fd6cf0078",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/BUILD_RE_A1_W07_Knowledge_Organiser.html": "1ceea27df6c9046878e32449d766513589ef13ea44be6338ae15b4d3c5a35b41",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/BUILD_RE_A1_W07_Knowledge_Organiser.pdf": "f5fa57ea9468ca890be46d8c2c08c9feab2953d17d2fb2c190ee88fb28bef10a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/BUILD_RE_A1_W07_Lesson.html": "475925b87c0d1d1f82e3de9148b55ef5d66b2c9a4adb2a070bba8f51832a3091",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/BUILD_RE_A1_W07_Model_Transcript.txt": "c6b02a51d1cd25f55f189e95e3d14cce37f60ac11245437f0f15c190fea6a9d0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/BUILD_RE_A1_W07_Pupil_Resources.html": "8176b510096c1d6c1ce206111e853c99f7eead7a407b09608173e6835fc14831",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/BUILD_RE_A1_W07_Pupil_Resources.pdf": "e1628f1dfba1f2c711b853d2bfb8ff0821521ed7bef7214d0917c3502243f73e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/BUILD_RE_A1_W07_Teacher_Notes.docx": "e58197650b0e57dbad6d08f425cdbb12c20f6c017c582d396d1edc2dc397a3eb",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/BUILD_RE_A1_W07_Teacher_Notes.pdf": "1e83d05f51e53580303c8baf375a664fd28db81177807428f19fa44d303c2409",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/Object_Picture_Choices.png": "798ebe66df7c5d23e8453827db5a728e9be0e0201baee18ddf09efe655e19b7e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/Object_Picture_Choices.svg": "854b2d8ab3a62c4ad23e8d3afcf7d331acfa90ae7a82357f522f39df8fca078f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_RE_A2_W01_Captioned_Model.mp4": "5804d50a2453b37e77e3cc7b2675100da9fb32e52553d8f49bdebc5c3dabd1a0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_RE_A2_W01_Editable_Pack.docx": "fd9959b3679d9db69b11b57671e648962828df6c09a9555ac31fe128e7ef62a7",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_RE_A2_W01_Editable_Slides.pptx": "98f08ce53e46263e2898fe66175cc55a7058f56de6ba9ff4f4e13a99b7267c78",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_RE_A2_W01_Knowledge_Organiser.html": "e8ce34178d3db2e524373349aadbdc33403f2916c870de0f0f1010168cb862ad",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_RE_A2_W01_Knowledge_Organiser.pdf": "50e640aee96eca6a1c73bb515e3094f17fc78ab4acedc7e2c539b13794b230db",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_RE_A2_W01_Lesson.html": "34c6a4ea572ae4c06fe7112eae75501d8eb5ca507512b21b45cba5ae7fea08c2",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_RE_A2_W01_Model_Transcript.txt": "db876e1f0193cec4c9bdd4fa36529c92432c9c5d67462d3b81f46c15b30341a3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_RE_A2_W01_Pupil_Resources.html": "321d7de1467e55fd1f561bb0e0376306d24b3e1bc597a5875f65cff293fd7cfb",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_RE_A2_W01_Pupil_Resources.pdf": "2ede5ee49400743e7516c0a99035ea4d37efc650bc4289e42ce05d6c124d546f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_RE_A2_W01_Teacher_Notes.docx": "657d657281c6cd4642e4b8388190ad647df2e270dd41510b18dd3a28c5f814e9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_RE_A2_W01_Teacher_Notes.pdf": "0e76d1b29bcb29c09a09eba0dca5acc50c1ad8ba53987e8c382a59234e7eb4b5",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/Object_Picture_Choices.png": "9c38530a13a73f4a4a1776b787dd86dc16ceceed8de1bf6896f700e8169f9296",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/Object_Picture_Choices.svg": "326d6254887ff8282ca5cd3a8460ec0fd2ec22c5d7352b18a204da09f1fb7403",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Captioned_Model.mp4": "e5b0b3b5b664483ae51fb2cec92d4ac0a80930ffb89a77f1f8a083685a7ed25b",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Editable_Pack.docx": "eff633d76ec719a42fcbcfce43a3a66cd844c86a846ffe6b232ed2b50e5e1fd9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Editable_Slides.pptx": "2b97a69c8c5eaa2cdacbc2891dfb5c5747a262de6155614bb5a27f2233fa71a0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Knowledge_Organiser.html": "e2ffb46de59c595f3b4e92f80e247e72505b9eec70e2ab734d1672d950fe9ddc",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Knowledge_Organiser.pdf": "87dc82d0d4c4e0a0e154881405534e8db2bd4b451e4679bcc71dc2258c150535",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Lesson.html": "42ee70d7f1081bfa2aa22683df830a1bcf3ca165b8739d1be9cbc40e46e29c14",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Model_Transcript.txt": "0222746855728d89a64554a1381281be51016e623a4afccdd460431b7b269604",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Pupil_Resources.html": "d0fb84513573f9ce537059313b7eafe17e3058c5443d8082558915b257126ec1",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Pupil_Resources.pdf": "82319303563756c150e9e3c0ac364bd377d289ffb7e458effa167becb6b83e3a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Teacher_Notes.docx": "d7f4f4e980b74577db96f0662db7501762efe74603720f426a536e9e80f6e1da",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Teacher_Notes.pdf": "8b1e6e62f05d19d77310193e15c586c0bb8dab5c26e03964da06051e620aafb4",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/Object_Picture_Choices.png": "4643d3c0e3c9975ac9b1a58eb4f31a047bf8990417e62797787e13f7cd749a2f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/Object_Picture_Choices.svg": "e4d16f15fb6209c734af324ef14712dafce8516b9aa471df522856d495dc06bd",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Captioned_Model.mp4": "8b9729f6e62f44bba73431017f010a194b65863d68993c8561412bef27c27263",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Editable_Pack.docx": "bb6cc9dd163c70c1fe3f4865e1c90a12b26d9fe1610480caf36b0055ac83b093",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Editable_Slides.pptx": "0a6781519e8c49b2349a62e208bb1668d6c8bc3efa8faccd5e00cc2d1ea789dd",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Knowledge_Organiser.html": "dfcc85194e3024c50757f7efbeb05670c6d8f2bfb068e508194629bdd4f8443c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Knowledge_Organiser.pdf": "40515e3330df3100981c716b15b77cc32757aa8b83ed269145cc13499efe8734",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Lesson.html": "a6317b637546a4f34f04b5ec0aa7d6a2aed10fd092e72b515bc7b51b74f2649b",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Model_Transcript.txt": "00751cb0b14117b490087f5a581eeb46c04c70c0ce6de8bbd3adb0d949d9eaf2",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Pupil_Resources.html": "63e2b7bba1ecade161ef60f7017a5bdb3e556a8756ed6af0fe794e100953630e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Pupil_Resources.pdf": "6417acf541d918c8f9088cd3c6e64989ec52153330936d3a0aa9f10c2a4357f6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Teacher_Notes.docx": "12cf82de050d39c7aa92ddd5e1734aa79921eef2917ba1f4b78b51c799e70d89",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Teacher_Notes.pdf": "456ff270ec9430029139eeaea54579072d867a7524c9e9e0574e13604e0e54f5",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/Object_Picture_Choices.png": "65d4646a57b6981bb645245130877291d0cc34ac7e815ec541bfb013505555d7",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/Object_Picture_Choices.svg": "e2dc627ae1718bf90f35e2d84396b6d1f54653b27c31e1a877b9a35ac0e8de09",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Captioned_Model.mp4": "957c2e4db4a6934a5af5346db124d555079426dd3f3f3a348fafffffe3e5ddd6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Editable_Pack.docx": "b6c14f97cd716be8e7c6060644ad3df3788ddd5d3825320fad31072768aff085",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Editable_Slides.pptx": "e063311f8c5c0292fee923bbc8a88bb34761687800fa7a859cfe9d18bd03ed41",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Knowledge_Organiser.html": "2b31fddbf0337c8ccb5e55a4b808d77ddb65078db3f172fbb8edc36d55770a72",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Knowledge_Organiser.pdf": "0edb7e83199b358c62fc7b1a7c9b190804d5103adbdc367dec797630653219c4",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Lesson.html": "ebb31cc0bb277568f6aa726de93bf0ba9bc22e6287ca32cde8b4f8401332d761",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Model_Transcript.txt": "66ce8dd502fb58288f01d7d0e3d5d0f0723e9a6c3a834bcff00272c086761277",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Pupil_Resources.html": "fb4d4235fb698d5718522c067c447384dcaea637c90d868a83780af6c7888cbd",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Pupil_Resources.pdf": "82a4e5d8379267f0f3af502fa6b249284005adace697c870a31558a4799e057d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Teacher_Notes.docx": "156e49089d7208b0e127e8f302fa7ee5ae51b141c98253b1283fff24072bdfc3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Teacher_Notes.pdf": "79422b20f9dc4d2db8809b131b48468a1d95fffe1eb76708a245d1cbac05221c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/Object_Picture_Choices.png": "4f439f2a421fd69d25bb9f19499a332a542c413b8f28ee8384b186812d2ee6f0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/Object_Picture_Choices.svg": "5855776a59026c04685f1f8323d5887c043c7e55e2198cba2ee4400807ccf4e7",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Captioned_Model.mp4": "5bef155d218c4453ff590815287913af8237c011e379978b95166776e88ee62a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Editable_Pack.docx": "6148b8ca9341edc565744ee585702e9bfbe033c2fc39a3c3433c3db38c1fbe76",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Editable_Slides.pptx": "139b1037a1b9546def40d6637d9628c943e01e447eb2675dd022e14325583f37",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Knowledge_Organiser.html": "b2a5325836afb154c5787c70609e35bc53324437d44931847bea1444ec092d15",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Knowledge_Organiser.pdf": "b348b4f59d38efe1fce2100833242a7f1de9c6675697fc434327375af9ab9377",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Lesson.html": "01e6450a6b86f27e91ba2716a4c575d8611243381d9c95ba99ae34a07a84994a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Model_Transcript.txt": "3ba2f1f0fdc572b137d54afce81f5f91465374b99a0b63b5e1edb141d8dacb08",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Pupil_Resources.html": "cb16898d232a75988c8df85c246aa43a359b958f8d71ea93797c132359f89a80",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Pupil_Resources.pdf": "033ad57eba583bcef4e0f760cc5285f67f3d8e2b2b14754349fcded1ad6d5f1f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Teacher_Notes.docx": "efc768234b7d6d8ed9434ff009562ec0bddeca8f18850d1fc014b17f0146e485",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Teacher_Notes.pdf": "c8213b28195f1732a6bdd1c93cf46a586e6ba591cdcd05f3c9f9e30027d3a90a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/Object_Picture_Choices.png": "6aade8f8f4348d7c1641b447142a1339cfcdfbfc4990e8300e0e2d625068a233",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/Object_Picture_Choices.svg": "53e21c24afcfaef31e60348ab838f3b5d55f86dc0b97ee64231079ad880db49f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Captioned_Model.mp4": "abc75c9cd47a9014bd93a29ef0cd5a1df9fd0cb096d51e4b26846dc95850f55f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Editable_Pack.docx": "491ec1811127abd3d661a34ccd266eb7e44ce72f51bf1fba98a8298c5e831afd",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Editable_Slides.pptx": "602e63729b86c034ae230684300e34705bcace19726df1893300cafce0ae940f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Knowledge_Organiser.html": "03be7b7cafb9071ac24632d0d1a656edd61b2b354388c5843eb8bd2680070d1c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Knowledge_Organiser.pdf": "f2ade95cc8f790b8d8a4ccaae6f6bb6e10afda647784494d4aaec5c86d6ff241",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Lesson.html": "2bd5bc7c821de84735fc6153a2fc60085e361728fb6d4d6f8b5c3f23a74d27cf",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Model_Transcript.txt": "672b4393dbcb43dd5ba41a43a8f9a120fefcd9778ddc1c4b59f6d408e4cb7b61",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Pupil_Resources.html": "f8ec6ddce207420dffb13d2f5cbca3ecaf1b5136725e9e1cbb7932b9ea00554c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Pupil_Resources.pdf": "be4bd82d48dceb103876921775e99b651e9ca6b3d84e74820215f43e63f89cf4",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Teacher_Notes.docx": "6425c7384d3ccce70932634ab6dc34daeafb5d8697b1ff51766181c4330f05c0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Teacher_Notes.pdf": "31320425df9e411c16f067ac24170f76a3a3d6b661fe76dd240bc0649950ff3a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/Object_Picture_Choices.png": "d9e8f3f505830afe6e4f35005d5c38dfb32f008843cfacd67e24613ed092a219",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/Object_Picture_Choices.svg": "60da88f70ef92f4e86f963c6c134a1a679b67bba1771fcdbe6084df48a9d5171",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Captioned_Model.mp4": "c54b0a62c85cdfd91def806f579563f66482e800ef5e26ff0dc6eca3579f5a02",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Editable_Pack.docx": "6d5e1fad9f5de968a82b4633556fc760d256f6b45a5d0a77319917bb6c9c0779",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Editable_Slides.pptx": "3624d0e906a2239a99be7ea29b2d2f57d38e9383d355d9785bfb7b632d20140b",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Knowledge_Organiser.html": "9c6a01b565c4e6040217cbe597f09a9bc688994d8cf616634a8fd05b4775b350",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Knowledge_Organiser.pdf": "a6a743a56ca924256026d3d28c1f22422638c883fee5a45b3eed3aa42d72b4cf",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Lesson.html": "ba7593d57f55a412177eef97d23322b4a195f24b2ae17c5fc99ab3bd6041e6ae",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Model_Transcript.txt": "d3b44c55db6ccadbe308377cfff21ab8d26777f790ae7386d547873c785eac6f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Pupil_Resources.html": "c6efc3e85f86ed34ca986683877fd4ad7dd5db232172e4f1d175482b07eae714",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Pupil_Resources.pdf": "1e9e948bf5eae7f0c9aeb4f5ee3ac0b7a74d4c87f30a4192ec544d5ef3279c55",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Teacher_Notes.docx": "1379fa67ad28863d58bcceded43450b1b1c8162991bdd635d55a0f781627de3a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Teacher_Notes.pdf": "c7f6b1be839701c52958c8a5169df5c52b616a6f747ad161070f2548e1445826",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/Object_Picture_Choices.png": "4f19d89d34b3a0db84469e65489ccc875f62f32fa30ce5de51fbd1a99b020e72",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/Object_Picture_Choices.svg": "12ccd75adacd6a4a3d916ac6880bb3126ea156d8a7c72d92d914d2f2cecae816",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/CHANGELOG_Final_2026-09-19.md": "8c0ee1e267189d0572b09de7fdd1d25ce9959a3d13e9ee5079e5db4d4963c387",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/README.txt": "b18e6a10681a2287090de194cb29747da642f300b3a25d7c11b3b45bcd814714",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/Review_record.html": "5fa2f45aead80bf9b82e062d2bcc8db2b1b1f4e10213dc608b24b05688adb9b5",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/SHA256SUMS.txt": "2e9a134f88dbddd5306114c2f8bec94c631afb870207461f9a1c06ece292fe00",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/START_HERE.html": "2aa7709d2fd182634bfc39eb8699ef789f164aec9159150bfe7bf0671b46f91d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_BUILD_Reviewed/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/CHANGELOG_Final_2026-09-19.md": "d2b7f48100f9a98e12cdf9621e9190e111512eb54acb9acf464a11618160aa6e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/GROW_RE_A1_W01_Captioned_Model.mp4": "fc33dd6e4eca656345a1c629690690c07b0eafffbf4e4b5984b249378c072798",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/GROW_RE_A1_W01_Editable_Pack.docx": "0423ca9fd645581078e620b458d70b191f4147cdcad9960291f0891d3d40f5d6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/GROW_RE_A1_W01_Editable_Slides.pptx": "c2121a98fa18e363da03ab44fe14e8798a9b8d6cd73592621acb6295584e85c8",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/GROW_RE_A1_W01_Knowledge_Organiser.html": "642915c3bc23c24604e4f7996a45aada54ee0c6f119ef1a2eda5dd0f52a4ec92",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/GROW_RE_A1_W01_Knowledge_Organiser.pdf": "5ff7932a8210460d5b9075374737520f9338ef4673c7fce498fb4452412111e8",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/GROW_RE_A1_W01_Lesson.html": "7aded26d3a640015d968c79e03e23f8a3d4d8abbf015ae3719c1e25b4a6a167e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/GROW_RE_A1_W01_Model_Transcript.txt": "071403cf790237ae2a36218bea7e28276a120fcc3ddca2fe089c94bb2edf7605",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/GROW_RE_A1_W01_Pupil_Resources.html": "32aacf4c4a7377b01548639c5b840f9886f4f8b0a1c3d8a263bdcb3f7a8c969e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/GROW_RE_A1_W01_Pupil_Resources.pdf": "cfd88896ed47b217a1d5e11258e943fdccd861e8b933044751ad3105780c717e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/GROW_RE_A1_W01_Teacher_Notes.docx": "6382b4c4e10f251c20483bd8132bb35d7f209a1aa83456b95effd62446b38e99",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/GROW_RE_A1_W01_Teacher_Notes.pdf": "398a585a56386aa37ff6938e1bb5011c262515b5c2394f504d97b73d822cf69f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/Object_Picture_Choices.png": "bf1ec52fe91f902f02eaa5ba224ad5fa1b9abb4d6bf21e8f0b093b5b673fd786",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/Object_Picture_Choices.svg": "d3ab6e0df501b8bced7b411ac2f42754e342ae7da319df5880e38dd70eff3e81",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/GROW_RE_A1_W02_Captioned_Model.mp4": "e058986919013cd5f9818a1c223f253612f96e64a6606bc177ef8f2405f1e9ae",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/GROW_RE_A1_W02_Editable_Pack.docx": "864eb707877481677d076b1dd4eee710db2136af933436880d2a841216b80855",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/GROW_RE_A1_W02_Editable_Slides.pptx": "53b6f92e167eba83bebfdda1dde34776b978c9d269ed19153236859bedd41efb",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/GROW_RE_A1_W02_Knowledge_Organiser.html": "fe42ef09f14231152f3f75d9f0d162b44a26eec609c74d86865931d1efb3c934",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/GROW_RE_A1_W02_Knowledge_Organiser.pdf": "91ff89d3df51f0fe0020ebc10c785c328f3a3cea6c1559f0e50d2deedea6d299",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/GROW_RE_A1_W02_Lesson.html": "a797d65c916e854481bb2a82f18787f2fb2bbe3d4b3c05188ca5c8b6a1acc011",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/GROW_RE_A1_W02_Model_Transcript.txt": "4f7a18de5fe3b4d8df807f16ccec4fdd8f68f043ab3a22a9bf139757746ded9c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/GROW_RE_A1_W02_Pupil_Resources.html": "da102dac6b2a2bf0efbd01c8ebc1946d94b5ab0fdbe3edcc6e0c7ca286f80883",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/GROW_RE_A1_W02_Pupil_Resources.pdf": "919de3ed233619558d5508244f9a2f0b2aa1c502628421e2cb2f88c6423f6479",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/GROW_RE_A1_W02_Teacher_Notes.docx": "590b1ba8125a1f1dbaca4c4760c158aaa02f13fdc427db6e1178ed5c7039e149",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/GROW_RE_A1_W02_Teacher_Notes.pdf": "e6145b001363dd05b71b0b752acc673ca421bea5f74974f0676dab47c2c59e2f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/Object_Picture_Choices.png": "4ae1e32a68545ab86de410a1dbf6fa46696bbf543f74411d13281ab49b610cbc",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/Object_Picture_Choices.svg": "d2a3ed24e7d76bb32f72abe0de13474cf2f4066abbead5cc5015a4c9733deba7",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/GROW_RE_A1_W03_Captioned_Model.mp4": "ea515d8370526eaa103de8289ccdf0d3389ea23fbb24f486405077acfc36ea7a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/GROW_RE_A1_W03_Editable_Pack.docx": "3cbf7f9c088c25ea474c9414b9436a0f7e8f458b32db534c995e2643e90db2ee",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/GROW_RE_A1_W03_Editable_Slides.pptx": "d3e0b65c6d2a539bcd55e2efd7d116b6f8e4c7310cbb26b2f84bdce202b8072a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/GROW_RE_A1_W03_Knowledge_Organiser.html": "b7650e20b943acdd134525c117f2ad0a847830be216569ef555354c4f74e34d6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/GROW_RE_A1_W03_Knowledge_Organiser.pdf": "0e87ba70b05dcbe9fe2cd8d4406a8e103bee49fc7699489ef61f025ab6c2853a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/GROW_RE_A1_W03_Lesson.html": "36dfb860e052a36ecc0f3acc7467132cfd428d7d50379e138394683ef09673c9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/GROW_RE_A1_W03_Model_Transcript.txt": "88956e320457fbbd2770a4d2ff8ab150ce0fdcbc8bc1cc97986841d66b147fce",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/GROW_RE_A1_W03_Pupil_Resources.html": "addee48d7a2ffcfa97ba5db16d03d77ee41add6da2e6a0fd34c19df19c839ada",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/GROW_RE_A1_W03_Pupil_Resources.pdf": "b47eead1f3fc8da5371cf793f0392178bef44a70dca5fb3f2a13272677c16e31",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/GROW_RE_A1_W03_Teacher_Notes.docx": "fd6c12c02d68b0d33d27ca4f139a56da768b6304d7f8eba0b4bea91087c7d4bf",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/GROW_RE_A1_W03_Teacher_Notes.pdf": "7e4eab990099d493dbd16d8fe8dccc3a80f83ca2600c13d609ad0e7ec0c20b95",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/Object_Picture_Choices.png": "615036a65f8aa9fac577a2a8d7aaca9f4dd2c14deeea3167a4dd522fb057ac81",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/Object_Picture_Choices.svg": "ad16f9703991caaa156c11462895abf6e5cd5fa534b726c8e6962e0e11a4f076",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/GROW_RE_A1_W04_Captioned_Model.mp4": "cfa2e6813325bb538dcfb0c390eaa44766948bc440e35e829ca718d61045b361",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/GROW_RE_A1_W04_Editable_Pack.docx": "ba0a4a97c382d4d52f373ad179d8fda40b3683b36c4128fda25c0c02ae80ff37",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/GROW_RE_A1_W04_Editable_Slides.pptx": "8d386320e5e6a96ddbabc2ee42628f23b4f096af81088db867e5eb7e17fe9aa3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/GROW_RE_A1_W04_Knowledge_Organiser.html": "3319af7bc7f01adc8184b28ae4e7b012c0fca9daadaa7e398d2c7ec86073e906",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/GROW_RE_A1_W04_Knowledge_Organiser.pdf": "9ab96426643dd9019bd9c0e1d3fe0ff227678f7aee4054bf30c10e74bd6d7bfa",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/GROW_RE_A1_W04_Lesson.html": "9c697cbe917850987462e68d0b2dc4703e7ada48d2da6cabed9df278d06d303d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/GROW_RE_A1_W04_Model_Transcript.txt": "3f2ba49cd75bff34ef160a70a1de919ab4869e12cbf75ba859d0189ef419b4f5",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/GROW_RE_A1_W04_Pupil_Resources.html": "5d1973d5d9d6c58381ddea0ba65633d5e1924636390b388e90e69c5d3f9a52ff",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/GROW_RE_A1_W04_Pupil_Resources.pdf": "e0cf21d345bd17d7a67fdcd7f36789e67f9d6e8a20a5bc3486f4906cd8dd0d90",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/GROW_RE_A1_W04_Teacher_Notes.docx": "07d66516bef5a254511a2a56e5ee90c68a9bfd123dac6f5f1672fd988b12e544",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/GROW_RE_A1_W04_Teacher_Notes.pdf": "9c17e81c3d2cb76ae606b49144278f5d9e38ffaec35f5fe7ed64135f84d37c29",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/Object_Picture_Choices.png": "158b4cc6ff2210f0727bb19700cd25358926241469158ec3cb02423556e90427",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/Object_Picture_Choices.svg": "42b829b84bc7b558a3045105009d823b8efee7d73b68c61ecf877ab9ce7454fb",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/GROW_RE_A1_W05_Captioned_Model.mp4": "058da2fec40f5be62a55ba2aa63e6b313bcd2b37230e71739e66b7f17fae7777",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/GROW_RE_A1_W05_Editable_Pack.docx": "4c55abc0c28e83bd401815006fe17618310a8a6634adbf7a4b50174e9208dd8a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/GROW_RE_A1_W05_Editable_Slides.pptx": "f598de8b05368b3a673de5795e7fddf7c4ee8401b477e034bfc4fbd69bdcd6a8",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/GROW_RE_A1_W05_Knowledge_Organiser.html": "66262990340c6afd469e42f8448a99ff5793b6771469a458031ad6edd93840fc",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/GROW_RE_A1_W05_Knowledge_Organiser.pdf": "dbfb067f6e0b0d1961be0873aa285298a9f524262eb13c8903e43c77de035f0f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/GROW_RE_A1_W05_Lesson.html": "232d9f1f66dbbc4ae745eea1c437d45c95654e953e2fbb2ad6a8d8b52f62a3a0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/GROW_RE_A1_W05_Model_Transcript.txt": "c4ccad7ed654678efba528b370c673882d120895ffcdcb5fe5cb275c79ad80c6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/GROW_RE_A1_W05_Pupil_Resources.html": "04b4b5084a0e378365523fe8e319977209364839c4d76e0fa388db61d12f36d1",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/GROW_RE_A1_W05_Pupil_Resources.pdf": "739efb0df503accd39d6e7a5d71e057b732a0c342cefb90a7787f8c8abe26fc3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/GROW_RE_A1_W05_Teacher_Notes.docx": "e345a6a6bbfbdac8703cd386cf85073479add26926e39a4c78ad7200c49d7589",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/GROW_RE_A1_W05_Teacher_Notes.pdf": "78729a230a2a809616292ecd706664839ea3c576f8ac28e339a4b9069f04c676",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/Object_Picture_Choices.png": "2ec930f485a43d60335fd5247fdd59157bc10a6162191739f18d29c159ef615b",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/Object_Picture_Choices.svg": "93b2903541d534c7e05819ed272b958c9467a97807b717b3626877c9e083f754",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/GROW_RE_A1_W06_Captioned_Model.mp4": "bbf1de7dcf586399b6009054b7c94697acf69942971f30d5493d7f1786b7fdc3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/GROW_RE_A1_W06_Editable_Pack.docx": "aa746ca606dfe30625982a3c6090491db9be2d88b1444e3476ff35d10db2d28f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/GROW_RE_A1_W06_Editable_Slides.pptx": "8cdf8c521f2c6c3330494844561ffb9ccbdfb95044a5e792ed121d1ef145fe1d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/GROW_RE_A1_W06_Knowledge_Organiser.html": "3b4136e37c00add8a8ca91f0e8f42a2768757ec527d979a857f396c56f65ed3e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/GROW_RE_A1_W06_Knowledge_Organiser.pdf": "85315c64205011e5fe54eb914d27d1f432f333696abbb3526ddfdcb1dff5600f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/GROW_RE_A1_W06_Lesson.html": "510ab24101ef27dce41546c27e6f8f22e6064c4552a76a6f07483405cf549bf3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/GROW_RE_A1_W06_Model_Transcript.txt": "8740c4be1ec14f28aa4bd44dbbed213e22a5d653fdc8c00d18fae1bccda0aecf",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/GROW_RE_A1_W06_Pupil_Resources.html": "5b0c55ab5d502e934cc15f9640a24d2763e3f4f2bdb118c6529beb4fe5d9fa5a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/GROW_RE_A1_W06_Pupil_Resources.pdf": "1509c41e7eb9ac8e2bae92c1ed5608b503ca0677d5ef2a16613584540ad434e7",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/GROW_RE_A1_W06_Teacher_Notes.docx": "5d7d2fe76597ef6570ef38cae49cda42afc8493dc3eb48f6d36f1977e2fa0746",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/GROW_RE_A1_W06_Teacher_Notes.pdf": "63e67b26e6c9c3a532855faec82ca4a697c69867c314669d164ab5d03281b221",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/Object_Picture_Choices.png": "d47a9d783e0d3d046852b77a5ff1b3715d91a0c4dacd4b256d377e6275095989",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/Object_Picture_Choices.svg": "6e6041d19be6f79968c6192256bef3ad0e880f8924a5f7331382180e465a97b4",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/GROW_RE_A1_W07_Captioned_Model.mp4": "1382d03ddc0d589a23db7b35b700cc290fa8830ccc475cbabbd7abb560f266c0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/GROW_RE_A1_W07_Editable_Pack.docx": "7091feb0a49dd2f82ec9787634bb2b233170c7a3d19d05cef91818eb3d05e43f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/GROW_RE_A1_W07_Editable_Slides.pptx": "f9e1d34c54ad559d3138e523a3a7a83590411e161e3a0112c57f3e165cc7baf3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/GROW_RE_A1_W07_Knowledge_Organiser.html": "88952df41b2d1f582ec304b346b6a675488f9e5b6596de7e1c3c399e1f240c33",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/GROW_RE_A1_W07_Knowledge_Organiser.pdf": "be7220b882cf12c5170383bb54a20a08edeefc967a57dfdd821e326b960fff6c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/GROW_RE_A1_W07_Lesson.html": "f41835574d4cb4f27324513956b5b5e6b2147b604ea6d9c2b05e283328e1fabd",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/GROW_RE_A1_W07_Model_Transcript.txt": "18762ec024ff6a0158892bf83ad9b2e2bcb7d06f006295bc6f689dd9abdf333f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/GROW_RE_A1_W07_Pupil_Resources.html": "1c27605586181720beea1c61d78485e8c94e13f5d3a1c1bcab81a3bc087c2403",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/GROW_RE_A1_W07_Pupil_Resources.pdf": "087d5dccde2037be47451ca984ca3f53d59c1e734ef3387ae9eb2c63bb547e6b",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/GROW_RE_A1_W07_Teacher_Notes.docx": "c953c7020a12fbb21f2cf4a1b9dde2f2d95ba4b95decc9c04c151076fa82ec5d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/GROW_RE_A1_W07_Teacher_Notes.pdf": "605c3193b01bac79ad286e4ded0b99e9a951273bbddda5ad31f5774156ed8da2",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/Object_Picture_Choices.png": "6aade8f8f4348d7c1641b447142a1339cfcdfbfc4990e8300e0e2d625068a233",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/Object_Picture_Choices.svg": "53e21c24afcfaef31e60348ab838f3b5d55f86dc0b97ee64231079ad880db49f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Captioned_Model.mp4": "39d0aa46930bb2e08fb6b3a8ff60b173f37ed820bd1786ac8d637c6fb73c7dcc",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Editable_Pack.docx": "7ac79da541135023ebc4718063ad2ac2ae988d374273bca37f3462d92c4e33f1",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Editable_Slides.pptx": "00d928c62b44492138a7cafabc237e56e72e5e89778c2dd82d4276579215d108",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Knowledge_Organiser.html": "658a8600a7a167c08c2f99b3eb1edbfd990def7d15902aeb261602cd6e3c5c52",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Knowledge_Organiser.pdf": "a8c64f5504682cca1c964f4cda131eea27eef7e6afb80a5a76e155067f3fd7c1",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Lesson.html": "46151cd43d6d3102b3d0e40d3e59512ffbca4381fa8e84504afaf2c2dcd43a51",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Model_Transcript.txt": "ca346aef3776bf97ae277fc35b3caddcf387b5cc71391dc9d2a67fbb0f23c674",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Pupil_Resources.html": "f03708897997d7a294bbc8f47e84526d2d76cfc507a715d7c1a1eab40dc4a81c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Pupil_Resources.pdf": "310282ecb77aa52d346c0833ed249716312428f01b8364307f74ee2d63c36e28",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Teacher_Notes.docx": "5a78af0e718fb24fe281918e650b3f14528bba3ae3e0864ce4e73fb96b9f57ae",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Teacher_Notes.pdf": "8e506e383c0fc41684d26c5dbf66805702b8a0af7b6a643b025068c20ca218ab",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/Object_Picture_Choices.png": "90828be115f583214b2cc89b5144f8e58ab063e3af4b898c9dfb3e4a44a5f24d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/Object_Picture_Choices.svg": "455aa5bee76a02a55524466417d3e0f21442a1f75d52405662a6d3489c2fe22a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Captioned_Model.mp4": "d44299ec942a4501c48a66164369762abd66d86f010c836c8e654bc4236b11f3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Editable_Pack.docx": "1a7063605160aed24cc6b33920a69404685a1f39e2ba0709f6afb6083feb9ef2",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Editable_Slides.pptx": "456b4706bf7fcaff974e96a5694bf2f7434e9f7f0d918f7d05dbb52c4ae92bdc",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Knowledge_Organiser.html": "f25d87d99c36255dffd7393dbfbd04c03ebdee92b5c174ddd4ab792620b6423b",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Knowledge_Organiser.pdf": "db322f55d74fc1924fa751c3b460fefc9f53b264cac08624da056bfde8c07b56",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Lesson.html": "12810e1612a6d4d7095f6f03f3017ed17727f0460c3644b25af350fbc50884ce",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Model_Transcript.txt": "38e12b8aed970f56a89bd124a40ad22f0f69080c30362f6a4823673b0b00e798",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Pupil_Resources.html": "7ab8ec166bcd4536a272db0afce65e7f4728ce31ea50d3882e7e2d9a8d69d77d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Pupil_Resources.pdf": "9afe77f92eae48efb5da5c90385800eb30fb07e8a51401b199cba24dc4942ab7",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Teacher_Notes.docx": "91eb0be77c0ec14e791eaf02ffbfb9e45227a8cccbe8fa47ddecabad673ada79",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Teacher_Notes.pdf": "801a64f0c74d4b9e3ee9de9487056f68e99751249db43e3a90cf02f601f1e456",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/Object_Picture_Choices.png": "360243ea9db05ba84cf56dd5ced4ad48a0c0a7b80c1ee21c9375473dd0279465",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/Object_Picture_Choices.svg": "76f294cd5bf0c04e2c446d892d909d0b0428eecec89510796f250c536aa7ecb3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Captioned_Model.mp4": "7a919603d12e004505230c537cc47e662aa57935194bb97b1121d89dde7b0a74",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Editable_Pack.docx": "73377a3b6d613cfbddd19995b646e465fb7c32bbdb9b1be5b36ae63f9477a311",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Editable_Slides.pptx": "51a110ffa376d6fc1a63b123600bb624a539c98130881a5f8d06bf17ce5e49c7",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Knowledge_Organiser.html": "55e204eed91d5729b039badd6aaef7fb3a0c60879eb933cac81807942c60a856",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Knowledge_Organiser.pdf": "f5f64c7867f0c91b875be45200d14ded11ad819ea865458791f2ad0de5d144ba",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Lesson.html": "50c069a77d85e5ad31c6260130b215dede0902f3b431c13fa9ceafd7b872e901",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Model_Transcript.txt": "94de8c04d27dc2367095be83afb81748ba70b1e931290e113e005a3b4fd4cbe2",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Pupil_Resources.html": "96db4ceb118c96a640797f08287c7ff08e5c75ebc93ac6fabcbc2030e1186347",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Pupil_Resources.pdf": "285dd5dab9d226db28571f2a1d25480415e108dfc6e6e4c321a1894235b38814",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Teacher_Notes.docx": "29de66b8c1d959c71f4f7ea15c1d7ecd848622dbd1dd53753431494be24e1544",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Teacher_Notes.pdf": "c24abe68d89b2c31001ec60e19abc41e274c4d8d172d16409a79cd67286b9835",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/Object_Picture_Choices.png": "945f2b45523f8a29ef1fc30d902dc67670f097348bcb8ba47a26914b74946339",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/Object_Picture_Choices.svg": "f3aebac60c32e83d5b96ffe551cc85af6ad789a98163331b5a593f7bf42d6840",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Captioned_Model.mp4": "7a2511b5b29217c39de5da31834c05300d5238e7f2f17c59f0acf3d31b805772",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Editable_Pack.docx": "8c522ba9d9c3e7889b1c2074d3de9379f80c824dd7618eeae9162bf67f382175",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Editable_Slides.pptx": "416b76b4f2560b6c6f3b769bcd40fd528a10db3bc350a5cf1c9d478bebafea43",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Knowledge_Organiser.html": "40fb405330aaccc91fca5ce069b1d1477894326a41c048ac8d88a40d82ab08d3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Knowledge_Organiser.pdf": "42fe07a5b3afa6bc352d13da4245ef964644258e12fbae6e66e7df621f17c9ba",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Lesson.html": "e96380c15ad49014f2299d7c3eaaf95733ba61b4c44da56069d32f172d5bc43c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Model_Transcript.txt": "459176dfece6f942547ffafa5a9cacdf664b2a6155422a367b294b3cb8a1902f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Pupil_Resources.html": "86259c2d3e198e9a939a3be88484ff4e2d807c0a49928543331f802b27c288ad",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Pupil_Resources.pdf": "9ec070ac5f1bab7f6ddece03e8c3114e9767db032a7905ba0b61a820913277c1",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Teacher_Notes.docx": "0eb4c45dd736f3756486ed5a937babab25a247b2785617be1100f4d9ca79fb29",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Teacher_Notes.pdf": "3e4c013e848a22c58bd8bd316a043d8ea7e63ac0b08ee051ca0184d5cee3cfe9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/Object_Picture_Choices.png": "3bf72d2cc6cfcd30ab6171eaeb2eab18e5848dc74a5fb39ac5b67c35fbd0e432",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/Object_Picture_Choices.svg": "db5ad39b271ddc61b36526f8d94336fedde54c0fbf8369f3a7849937145c9fb3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Captioned_Model.mp4": "9bc5ce30f8052b21b0860165b8946fad058ab12f07e08f6e9ed390f980b634b6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Editable_Pack.docx": "f8d17e1482149bbd167741953259b28debdb248aeac013ea83803cfb51e3987a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Editable_Slides.pptx": "517eeb56a7e94b5d4b994fb5d82593d4075399b3c7227b5744f08505d0aeff88",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Knowledge_Organiser.html": "6b5a3f9b8ab5450ec1e7e20306bc33b77969ed26436c2dd784e1e2a4a833a148",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Knowledge_Organiser.pdf": "db694069db54d241c3f297bf8de80356aca96d64d7ac4dfffbeaf4123c8660b1",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Lesson.html": "abcee307ddf2dfe43ff34be209b4b9afcc8010c9f005e271c88666e14d5b1b44",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Model_Transcript.txt": "7eec047350ee148367a0aa146e9d9a07e70698e4046ac5fc7be318c72405fb00",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Pupil_Resources.html": "602f3691431123c6adf288575a8188871ba81c4ee6df04de43e7c2b42a42958e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Pupil_Resources.pdf": "60bb6212a5696924124baa02db5d27148b17f5cf1f6547a90deaeb797ef9cbd5",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Teacher_Notes.docx": "9475745c0fc23fb06583ccae3a0ba5d996b403ee5fe6b602edb3c15223e1406f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Teacher_Notes.pdf": "5a61ab8c574bc99f6cc73a5cda1375b31bfb55b694d55df1a76274c42323eac3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/Object_Picture_Choices.png": "6d880c50adef451513e071840dfa9041f07da7901deb19411c79a55b13dcfcb0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/Object_Picture_Choices.svg": "0e2c27c6f7727371ffcbc395971ca992ee4d684b991195d89bc8c9f6df1b7acf",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Captioned_Model.mp4": "1d4fcc9dc7f865f706a7f84201549ac02e5acb619df463ee0eac41f8d19d4993",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Editable_Pack.docx": "cddee6d0320e5e43e33dc597f21bbc230cbd83fcda9ee1246155afb734c8c1ab",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Editable_Slides.pptx": "38267f40867cbe370f4443a88af0cd0f24d8c60ab60460eb0c4679356b3daaea",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Knowledge_Organiser.html": "f6899d40387c98205c86170c8eace1047622d0f8a68caf7f33fe48281e9f75d0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Knowledge_Organiser.pdf": "d294c393f063b97601c99e9d09c36c1664e4e6920c4887c4c446772e16e85492",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Lesson.html": "8f556dbdd7927979df24c7658654600b1c3374e83d6819ca88205a7929d3dc77",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Model_Transcript.txt": "1b596f72e9c6e952300305171b1b31482c0f580cd00fdc71a794a71d20371989",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Pupil_Resources.html": "cb9b561a54d186fc35ff1b53e51fc2a0512c19d254cd16a297574418e2694922",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Pupil_Resources.pdf": "159ffbecb1fe72ff914d8fa8a5ae0c08df6ea4541c42b50922109c31821c7ba8",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Teacher_Notes.docx": "61a962d558bd76f16a39637dc5f5012b5c305d24711959f57e83efcfb1d01e0a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Teacher_Notes.pdf": "fe0c43893380ddf9d0329d5e8a5c983d06d743d03d7d28a78cfbfb1a809b4726",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/Object_Picture_Choices.png": "aeee84c34c480438eebeb9f67ee90285831e649f509ea782352787bbe239551a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/Object_Picture_Choices.svg": "f0ebdc0a943f0a3b435fa4797da247f920449549d07e062da9bfdc51eecbb22c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Captioned_Model.mp4": "3e09dc3c2394146abfa773d2b1d341752e43aa7f784c94b97826758cff9fc7e6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Editable_Pack.docx": "41e6338748b3a81d4e42cc7f5f3fc7923906f860606dbe9382915f4655892d3a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Editable_Slides.pptx": "3a90aa95713ce0408ffa6d88106e4f718db55cd94d66c261b5e973ae2c2e07a9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Knowledge_Organiser.html": "6af1ce908cab3014a643bdb8a51aecaca28600faf40772f49f6e4083c95df82e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Knowledge_Organiser.pdf": "a1057a12673806e0f55201b3ff728d67cdb7ce483e7e2a37e0155f991492c0d9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Lesson.html": "8fbfd80069c4b26fc7d0dec9459c305c9cffe219c251fd1f600bcb424b9d3b82",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Model_Transcript.txt": "dc1f8051b2679c64a89619819f0832ebcba00a5fd5cddd4bdf30d4a1adac80f6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Pupil_Resources.html": "43e81e7499a2c908a160b166576f92c8eef57fbf0b8638d233486e651db701d1",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Pupil_Resources.pdf": "d1a0f4c9d88f4d6332766c51cf7a2e521a4511f1a2ca4892237b703bee5c0c73",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Teacher_Notes.docx": "6562269a5024228c603d53a9d5f3679931e1d9655479b631a150e0c58a5c2ef6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Teacher_Notes.pdf": "b31e564e25dbf4fd41f56d20da92afd1480068e445acc01ad4fb41818e15e923",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/Object_Picture_Choices.png": "4273e41f07b60d513752d09fc4ddd5e314873cc362a1df02fb3e7c863213dddf",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/Object_Picture_Choices.svg": "68067872cbd4c4470451620a9be4b3f809bfd1f7e45049e4ab58f16cd7392619",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/README.txt": "b18e6a10681a2287090de194cb29747da642f300b3a25d7c11b3b45bcd814714",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/Review_record.html": "c4d217fece8fd4aa2285a7d8de35ec1e1b965a292fcec23c795f44413e4c952c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/SHA256SUMS.txt": "5ae18b9063c67265a8d67a8b9461cd5c9deeb48f89c318893eca92b0006112e8",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/START_HERE.html": "a0d380d8704f9b90650c24c9d66856b98b5152b63bd5fac0d2f62870cdb093c0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_GROW_Reviewed/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/CHANGELOG_Final_2026-09-19.md": "a8a367310913a3f2071e29838fbe1d31c096c65e2c965f08870a5e5699030ee5",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_RE_A1_W01_Captioned_Model.mp4": "1e326b26e107010b2d9cae2e30335e6492d66d9c37997e513cac560c54b1ec8d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_RE_A1_W01_Editable_Pack.docx": "0dbde8cedf663e840bd1aa79350802cad29aaa2e173e0d2745d94b6905165dcc",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_RE_A1_W01_Editable_Slides.pptx": "1251590334ce708bf420a7b8192505bf4017ec65ce274c819459cb1dd7b3e5b8",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_RE_A1_W01_Knowledge_Organiser.html": "24f72ae5cc93774e0122823aecbcf3515a2ada64e6dd72791c52e2ec1f571f51",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_RE_A1_W01_Knowledge_Organiser.pdf": "62037cbfa8dbfeaa783baa8ae76e7c4ac920d38982672d6924d1ddf913ff9117",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_RE_A1_W01_Lesson.html": "78571ff17d4b661506b88c48a90279cc7a1aef05a2abcea364309ad30f93781b",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_RE_A1_W01_Model_Transcript.txt": "68a3962e47d3e424c817dc0834984917b0b2b284ac62dfc1424b788e198cabf5",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_RE_A1_W01_Pupil_Resources.html": "5220a408e5bac658875ebc35ad1508b18f7ade1c5349068fdc4c2d1ca4c78305",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_RE_A1_W01_Pupil_Resources.pdf": "e53ba426159b22da4525ccc072b647b64ed972da30bac9ef933a2bfebbdac46a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_RE_A1_W01_Teacher_Notes.docx": "b48acca94c5291d521c15be2a464389091cc3cc84159a5b65d9c5591110a1f2b",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_RE_A1_W01_Teacher_Notes.pdf": "85e9db3a9de5fabc604923b9c1e0b210f65b42aafc5073275ea08f6c4bf3247f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/Object_Picture_Choices.png": "8f54ecdbfb89ec5e9c04e834a74443ba825f6d1d016b6ef04f13a9d6a7c9bedc",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/Object_Picture_Choices.svg": "cf055c4dc63917ca1e1c70a52477c08b98bb991d395420267d4cfda3b36fce00",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_RE_A1_W02_Captioned_Model.mp4": "cadd1522683268ea5e58f359f11cc392cccd650913d7afff25531381b9fd53cc",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_RE_A1_W02_Editable_Pack.docx": "4c883a2544ae757923a660becd92d2554cfb7ffe371c2ebb438a3805241abdf1",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_RE_A1_W02_Editable_Slides.pptx": "e1ff56a9cbd15c3d07c9527af119f36d4b8badf194357ac7b2d1fd52d496bb6c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_RE_A1_W02_Knowledge_Organiser.html": "06aebe1eb12963c46746736cc5fbbfd83a4d1e4b60a92b68586573c3755bd500",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_RE_A1_W02_Knowledge_Organiser.pdf": "a926ffc316b0391abef1ef81bf6e9f3327b18a121d6735309781993be10bb5eb",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_RE_A1_W02_Lesson.html": "ac2fa8981763a275cf7fa8179b5316f5aff47f5c0705df958a14abe2bcbc4f6e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_RE_A1_W02_Model_Transcript.txt": "1a9c447c13f2d36d3b33189ddce7732ced15249a48cd62d31e2d2aee8358e9bb",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_RE_A1_W02_Pupil_Resources.html": "568896a56d76eab5b5c61d5192b97bcf246f75f39ad6fc437451d91859ffc7b0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_RE_A1_W02_Pupil_Resources.pdf": "d556292b3fa43e557ac476fdcfe6f4fb6aee47adb018caf822771e455359a465",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_RE_A1_W02_Teacher_Notes.docx": "c084291bf836b1e2ef5ddb6c1685379d369c42897393e0e49a8792de8eb21367",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_RE_A1_W02_Teacher_Notes.pdf": "80e31eff0e45e2f3fdb871f0767aafa50f3c471b49e8a1d05939e6b1df2cc9b7",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/Object_Picture_Choices.png": "2306e69a21ec8bdce423c8e2aa25d6fde495b05ee7a7196eabe240c6eb66c209",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/Object_Picture_Choices.svg": "40687f9bc675bc47c7aae92ea30d03ac5d31963f87a9213a10446053664c03b2",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_RE_A1_W03_Captioned_Model.mp4": "b935b055e239be84cb515786af0937a0b17d8dc48d6d2ffe7293eb543bad275b",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_RE_A1_W03_Editable_Pack.docx": "d9623197d180789a60759075458d7ce2de6fd60591e300d22e2cf0b3006c2787",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_RE_A1_W03_Editable_Slides.pptx": "9f0c0addacbe261d1b649b97ec2b9c325f067f3ce646f7eb2aac8f66f71f91d6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_RE_A1_W03_Knowledge_Organiser.html": "c76491721d3b1e8352779b8de7c6e632ccb7e20e394c24acb593cc4d541adfaa",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_RE_A1_W03_Knowledge_Organiser.pdf": "d95ac8a21e9004b06e149e21243ae50e83209b8d296d94035475222bba3d12e0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_RE_A1_W03_Lesson.html": "6f79adc5c1450514306df83ead5c00a33dc3924c3a380223204e332325673c36",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_RE_A1_W03_Model_Transcript.txt": "4b20053d1d0938b8d1cba85c2ef4700f709d6f27f0437853c64f007530e84ab3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_RE_A1_W03_Pupil_Resources.html": "b302d9e759a3ab5ef6e4a3bb0405a09327e3b4f453de8158ce3d3cbd229123ea",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_RE_A1_W03_Pupil_Resources.pdf": "ec136f052dd043a5f0e53e003a1978ea3f8fbb94dc3e026e4abcdafc4c488f67",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_RE_A1_W03_Teacher_Notes.docx": "2627b440364476b66ece194e34bd2d263c2fad55fd4acf03ab5d8a2e2fcf70bc",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_RE_A1_W03_Teacher_Notes.pdf": "1a41e4b13e4f3461e52084d85c22f0328f8845a3d5f92c96b15c0c4d0b6a0236",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/Object_Picture_Choices.png": "dbacf2dc270329e30c464a2c0efe5a5d42c4bf8b23f8a65f71930cd61022983e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/Object_Picture_Choices.svg": "134aa06ef59037e27759f8fd47fc924fdc723363ee73428385cd45063c3a8b04",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_RE_A1_W04_Captioned_Model.mp4": "dda57025e228f9f5e6dd4ef2cb679916b1e5a4e2ddb340cc96626ed422db6820",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_RE_A1_W04_Editable_Pack.docx": "66109379d3cde837cbbb6c17b61c1d391c0dd42b1adffdf61e60a0b1be748c81",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_RE_A1_W04_Editable_Slides.pptx": "d27a48e1bd163c1e70fb5067b5717e498ba9ead6058b528ee73aac63d302d281",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_RE_A1_W04_Knowledge_Organiser.html": "27484364c5900f0ca17e1ad7b55ee1ee428aa7e11e9ec211a82c3871ef6c583c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_RE_A1_W04_Knowledge_Organiser.pdf": "2aaf904016e2e854195265e4400f860251638762595daffb40283d25f186f703",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_RE_A1_W04_Lesson.html": "229769bcaa6d5358c10f1d08215773ba7ee2619e27fb749cf1b48ef98e83afc2",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_RE_A1_W04_Model_Transcript.txt": "293a1428b2e0be02956e5443af0e43f84a8a4a721d1d83aa67bd9b27f872d43d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_RE_A1_W04_Pupil_Resources.html": "0d2e0d6af96348209e1bf2779bdb7abd681fb0c0276c2c79c0ebc41193a08974",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_RE_A1_W04_Pupil_Resources.pdf": "5c3a281605413e64ec8a6431464ac1435872888ec19b8fb31b65b8ffd29463a1",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_RE_A1_W04_Teacher_Notes.docx": "1c72b019eee8806e13bc330d85887d281d0961ec5e0453cc227470744348324b",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_RE_A1_W04_Teacher_Notes.pdf": "1ad00532eb3d383caf75565a6ffb4735ce91ed52e377c0c7761d20886fd4f4cc",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/Object_Picture_Choices.png": "da03b24da57fbf60572da220331d8300e1113c2594d7b641226f20236ee8a963",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/Object_Picture_Choices.svg": "18cf8b564174af67ed12c33e095ec361b8e6492c11ba9db4b1c4dbadf4d11199",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_RE_A1_W05_Captioned_Model.mp4": "e7cb1341aa9ca62ece29e9341494ef9d02204152f1c314448c75c6b1a5625087",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_RE_A1_W05_Editable_Pack.docx": "74176363e640c914c74640f171a28c859f0c3cd4f95642b9b2d735881bcaa64c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_RE_A1_W05_Editable_Slides.pptx": "5dfd0f1b1ba40c882ae61c6ce1497d048dcc6080941791c6521bd6abd0609b36",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_RE_A1_W05_Knowledge_Organiser.html": "b5355d757867d802922f8a1f86017f69637a9c39b27e219f80f6d7dd13223e07",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_RE_A1_W05_Knowledge_Organiser.pdf": "8b2e4861b4835b36a71a45512ac32adc4036319b5a7c382dafffcf076905802e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_RE_A1_W05_Lesson.html": "f40e5871617c62b7bfcf46d3f163fd956b63703844df36c3b90cec4fd39103ce",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_RE_A1_W05_Model_Transcript.txt": "a87ac82b8e65c31d3710815600d53e649a2844c9c5b3e4314afeba71e94800d5",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_RE_A1_W05_Pupil_Resources.html": "68b2eeca136464a319358a92a17110b928fcfbb83807989bf68c20657dea69cd",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_RE_A1_W05_Pupil_Resources.pdf": "4211f9a53c608dc346bed69d8ef67458e73cb582aa1bd12b595a2d59e085aa9e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_RE_A1_W05_Teacher_Notes.docx": "20d6d834cd33659c1027220016cef08b8ed14f2566081d110b4176d0458c2a1a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_RE_A1_W05_Teacher_Notes.pdf": "b2c0f22803ca2d33eb86e44a2d42c6c953df55894c0b0fa8f389cfd1ab81fbec",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/Object_Picture_Choices.png": "1377e7ef445459fa33d613b50e763c5c6f1ce07a1777db28e1e2b036b39aaba2",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/Object_Picture_Choices.svg": "7c286fa8340fc3b84ba5e8c3cfc4a39c1b367798919b1f9051920a2a891629c7",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_RE_A1_W06_Captioned_Model.mp4": "b4dc7621a1d62dbe4c90b284eb92f6a7625dba48d1a5228fc1ad51412ae051c6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_RE_A1_W06_Editable_Pack.docx": "79fabc09095003ff4d328a8507c60769df6adcff8a61acfb85d81b8246d5547b",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_RE_A1_W06_Editable_Slides.pptx": "cc5eb291212e44bde3987912d6a16965ba7302b301227b5d0de8ebde5bf1de27",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_RE_A1_W06_Knowledge_Organiser.html": "a11d8dac8f2781b1a5d9bf1427b7d14b89dde73a1a8f39aa90e63fc04636bd66",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_RE_A1_W06_Knowledge_Organiser.pdf": "a246d4d0d65f0f2103a870936d89ca202e13b690f5a7432fe17f9d6404ef0316",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_RE_A1_W06_Lesson.html": "e0febc1d6c1bbff3a86ffbe9de42ef6ac4911132439e0e8863720bb2488d5fe6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_RE_A1_W06_Model_Transcript.txt": "76c063de3dbb61b84f4c395414fb49d7e22c8de3f91a18ad116deea0ad313cbf",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_RE_A1_W06_Pupil_Resources.html": "3dc409a6b7a334c8f3480d7e69de8e9e319056ba98c6adb76062a6bbfd88b6c1",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_RE_A1_W06_Pupil_Resources.pdf": "427b41d32956d2f113fb75dc25a5f896b3776e3f08fad5651872af32ae0d4245",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_RE_A1_W06_Teacher_Notes.docx": "251b74186f6446e3e76ddc8e1874f8b9f35afbc123847292e9cab32da13d7460",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_RE_A1_W06_Teacher_Notes.pdf": "7f4e6dc21eabf038c48d673bdb7e12804d6fdfa768c9b43047093f1b3dae8136",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/Object_Picture_Choices.png": "13cf86607534270a14265d61683f235de85069bea1881fecbda166b98f518275",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/Object_Picture_Choices.svg": "27c7ad14f8f8c2aee3013433c8abb45fdf88c8afa9fdce461b99083fe1e11646",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_RE_A1_W07_Captioned_Model.mp4": "3fdfe9b3e1b076d16e5dcdcb3f03666a1c239eaae368cd575eb8562b2094d666",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_RE_A1_W07_Editable_Pack.docx": "cc451a35925b3c99636a91668610d56be7fa14f14f37bd39ed8b1c596cc73798",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_RE_A1_W07_Editable_Slides.pptx": "57539b3f52cbde6510772b1af5a385ce76430b9c1b90abec4f229e203984b5b7",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_RE_A1_W07_Knowledge_Organiser.html": "468a35fed82d2c6aef1cdb4f8d4f00cc0de496f12cdc9bfdd000b2b862e86671",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_RE_A1_W07_Knowledge_Organiser.pdf": "e87f1587aee18362199f5c1eb864c6c7a4f854b3ee1d221001af498f5d291b32",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_RE_A1_W07_Lesson.html": "1cd75a8a33e9202db2f2d1bb511ef573b87a55355bab988c845e0c28d5f93da0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_RE_A1_W07_Model_Transcript.txt": "a2f0172b11b34b1c6179ff360be2ace2280928e453bd8c3b737169adf3c9cdaa",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_RE_A1_W07_Pupil_Resources.html": "60d4d650667a0e20ee8ee946aa23a6d25e3099c56774ce13b612dede5b3f0d57",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_RE_A1_W07_Pupil_Resources.pdf": "e78a41a37f17fe97e481b3ea1032681bcafa3ce4a152bb8e68160f30fb035584",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_RE_A1_W07_Teacher_Notes.docx": "81b844ea4560767faaac233e7649ffc6fcb1d36b847ec2c4a8736e668418c2f2",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_RE_A1_W07_Teacher_Notes.pdf": "9a2d8782a1b7df143c9b32ef780cad3e21b352fd69baaf21e01d65e278c788eb",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/Object_Picture_Choices.png": "7b8265232d9d4a7483174e18ff587529e9206b0d325749aec547c9a9f1c336f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/Object_Picture_Choices.svg": "20eda92e86b70ff59350ea9834d16623602ddad06c90377ee36778c1020a1bd5",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_RE_A2_W01_Captioned_Model.mp4": "9e668addbb1f117e02ee94486acf873ec9e796fbfe7c0760654e57ac2553f7a3",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_RE_A2_W01_Editable_Pack.docx": "50a7bdc7ebb54dff8139a4fd71813cfaddb3c37ed7cf4e26d52d5f8ea3ad8239",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_RE_A2_W01_Editable_Slides.pptx": "d5c126cb2b47e8b425dde186eea997fb98593fc9cb5dee72c5826bcf17bf3f99",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_RE_A2_W01_Knowledge_Organiser.html": "f74753a8d7dce7f36a288809057cda37b03fddb09eae0a4c51064f51c1bff587",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_RE_A2_W01_Knowledge_Organiser.pdf": "6ce41f72ea84d2eeb6b6ceb0a6b48d8f821260eb99acba226b5acd067a3752ef",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_RE_A2_W01_Lesson.html": "2f3f536c4f825410cc3d64f5256fba3fb58432090e2c7e59e5915dffaaf0c5a6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_RE_A2_W01_Model_Transcript.txt": "febfaa4ee19bcaf36faa5f7600daff7c1f04136f2f2b528b1b53e8241d6bb625",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_RE_A2_W01_Pupil_Resources.html": "08cbbc9db144ad40a165e4eef86117508e2bc8d821fa7ba0b46f1f426283d2ae",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_RE_A2_W01_Pupil_Resources.pdf": "6c37d48ac185895dbc1492f792f3c3f4ae578f0d676ec94269d89690c5de2fbd",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_RE_A2_W01_Teacher_Notes.docx": "251cf507f14fc931c69c19e59a5aea34f9641b64e93dc9a20d9cfb851f3b6b31",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_RE_A2_W01_Teacher_Notes.pdf": "e2fd0456ec12f4e330ef024fd22d7a54c326eebc22a597c0efa3843013808c23",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/Object_Picture_Choices.png": "c50860a9d5782f9876ea3040d0e8c578156bf489cb345173234e2c6dbf047b4a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/Object_Picture_Choices.svg": "ba2978c10c21ec2b7dd14e45dc4988599acb0f95262744f5b8c9ce875857cb65",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_RE_A2_W02_Captioned_Model.mp4": "55d2424de0453c37a967ecfecf9ee7367623437c636f09395f1a59f5500307c8",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_RE_A2_W02_Editable_Pack.docx": "b435a79c6949e4c5026d1fef5e4c78671f0896c511c72e59f08a17f9d2417bc5",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_RE_A2_W02_Editable_Slides.pptx": "af2b72bf67b3612df2d58502f37732a18275bfe8942e5d0b81bc75063068f427",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_RE_A2_W02_Knowledge_Organiser.html": "e5745f06d9263664c217c498ee7d387f7134e4e3c9dae85783e9a267fe3b95c0",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_RE_A2_W02_Knowledge_Organiser.pdf": "c3e24e475e79672df52701e1504346c29e61943767e9c57845c832cb53cd840a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_RE_A2_W02_Lesson.html": "e2604a92fb02e2b6884d6a0ae42895f8d461306cbc982ad052e75c2bd81fe8f5",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_RE_A2_W02_Model_Transcript.txt": "eea985a2257806497aece0255bc547cd7bdaca01ab4d343b79ab41d859c62644",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_RE_A2_W02_Pupil_Resources.html": "a3cda90bac7c02e0caa080c9da13a4b2954f617814425f8834ba2387a7c52b62",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_RE_A2_W02_Pupil_Resources.pdf": "65c9eee78d33bfea24f9eec3e38c044045900ba9196cbf731fe1819701a6e146",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_RE_A2_W02_Teacher_Notes.docx": "25cc5d6f2003d0b5d325069b170424ff219ce44d1a0703e57f1819a42647d819",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_RE_A2_W02_Teacher_Notes.pdf": "1714d29cc44850c494dc36268efbc71ede57dfb7e0f462b0e0fd8a39313cc4ab",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/Object_Picture_Choices.png": "311905a04f7fa331ac3278b0a84a6157df17ef1387b31487b46367529e2241ee",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/Object_Picture_Choices.svg": "27e0d78cc0fbdb3b77232ad5c8520db7d7a4d22871733486197c0264d7e492e6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_RE_A2_W03_Captioned_Model.mp4": "08fb6d83740d4279d53402cc0e7d27b8231325879d82ade44116f0b131248c11",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_RE_A2_W03_Editable_Pack.docx": "56b513a56437e050dac241ee2c110e07de9d4feb4e46f20e4a2f85ac3a4c557c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_RE_A2_W03_Editable_Slides.pptx": "48bf2107570b63f902509a6c9c98a5d7f5e9cc712c36f7455feb6e0cd128e366",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_RE_A2_W03_Knowledge_Organiser.html": "53840766c2ff36e78b373022493820f1f7dc615d2757e3020660afa39db39dee",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_RE_A2_W03_Knowledge_Organiser.pdf": "5305523162c995af4da75c63014b476f2574fa821caf169b47ba07a08b2b4116",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_RE_A2_W03_Lesson.html": "105fd58d10dec7b307d6c3cf45c059a30afcd5e3d5f863dea534290936e50ed9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_RE_A2_W03_Model_Transcript.txt": "f65223a93d92abbe2261ad55f0bd439796c19aaac8ead4474998296bdf76e59a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_RE_A2_W03_Pupil_Resources.html": "d104fbce6011c10fa26e11252f657d2dc526bfe160728267fb79d1ea3400a61c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_RE_A2_W03_Pupil_Resources.pdf": "6597d5cdf77ad6ab0598f09035d0b792c542454845a3af5901a18ff677e9bb78",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_RE_A2_W03_Teacher_Notes.docx": "f049300c9240d45b122bc02158f2cf428f93a122e715708f5bf65baafa29e551",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_RE_A2_W03_Teacher_Notes.pdf": "da57f2f189028246f1163a269402ed33e2ab26b01a80e928bd64fa89bbad188b",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/Object_Picture_Choices.png": "d0970fd813e04a5fc8c2cca897faa08259b8a0de8c80217650a2c7909cccd84f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/Object_Picture_Choices.svg": "fdb0ca3b53ad881c6fc00cf00f63206837922c781c29855064dcf7eef283f6cf",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_RE_A2_W04_Captioned_Model.mp4": "dc1b0426f0ea41fb8d869b4bb4628f5c2a820fa8ed36091d245b7ddbaf901f49",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_RE_A2_W04_Editable_Pack.docx": "3b78fda12f9241f9b7f3bd0762ec9c64e4f734b6556dc40851f3aaca6c964823",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_RE_A2_W04_Editable_Slides.pptx": "73734bb72734a7bb9be03c10253a77d7c016c8fd2d0d6ad90b2c0f28880c6a51",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_RE_A2_W04_Knowledge_Organiser.html": "fe79c894f3d312474a7cef7811907fb93cedcb13b3c4c990837ff76dce586285",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_RE_A2_W04_Knowledge_Organiser.pdf": "3b958f6f588b3a9550ec6ca30c00a2181761ed3b9f9ab4bd0d9f46ec1a13e32e",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_RE_A2_W04_Lesson.html": "f3eb0edbb6a440ea4ab98a0bacc5d48d3677f83549f3e44a49cc177f690f2203",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_RE_A2_W04_Model_Transcript.txt": "75942af396f2c2381a58c33a8105a16de5dc770ef39c179cbe1999b01d832947",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_RE_A2_W04_Pupil_Resources.html": "47e06bec3847bb69686ed16d8517970172b380696151f6e92f181c098842f409",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_RE_A2_W04_Pupil_Resources.pdf": "0e5bf0788f80cde7514c33e4177b4ba5049172e98f634764ac3407ff9422b3b6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_RE_A2_W04_Teacher_Notes.docx": "32ee83f0d9baf930b6ed560b47c7b7423bff9b35e730fdf0f348f6f0b2f1707a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_RE_A2_W04_Teacher_Notes.pdf": "c0a118a1fb7b0c80f22b3cca61f5a8c1f9f04a4b58e52bf8f6553f94f1934510",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/Object_Picture_Choices.png": "70c1d83727e669ed08cf375acd2c8e6e106024ceaa0bc8ec6d0a146845b48224",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/Object_Picture_Choices.svg": "5252d7640c4bb99ca473b2df9649f921a100dfdeebed70d81ac954a07dd25df7",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_RE_A2_W05_Captioned_Model.mp4": "190778ea6de4b39b26adf61bea927409b51210500061d05cf8098fe5da9dd45d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_RE_A2_W05_Editable_Pack.docx": "92fc5417af9f4c6219925c8c626674d286398ff0a4fbd7eeadc40c5ab8c95181",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_RE_A2_W05_Editable_Slides.pptx": "602f215b02ee4bf497d1ea4e74a2b4e180a54bacba88bd53dfe0ef8c63c7a8e6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_RE_A2_W05_Knowledge_Organiser.html": "af60b6e1b22f3f19867e1a0e9471cb49cb8fab962c95fde18806a163782b332c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_RE_A2_W05_Knowledge_Organiser.pdf": "d54e8253a6622427a70d8f90f2980e4a7a5baed8aa4c03b35c8619812d57a192",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_RE_A2_W05_Lesson.html": "c87d0c8b522c0da1348c367bea88d6a5ca70163880aa9aa22a40d5fd355bd567",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_RE_A2_W05_Model_Transcript.txt": "dae3e070f7a899e8e52d589fb86b9aafc7251a10da1eb22e103abf2eb458354d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_RE_A2_W05_Pupil_Resources.html": "490daa1ea4cf391ce84fa0cff093bffa05e25dc06317b2198964f794dc972d51",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_RE_A2_W05_Pupil_Resources.pdf": "b57bbe1d7b1714b90fed686aa2790e2433e6de121d77f82f18ff8d230e342ba9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_RE_A2_W05_Teacher_Notes.docx": "16ad6615f9355ccb8082d9a85cb01543c394b361d6340f2d78cc02b6394f7af5",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_RE_A2_W05_Teacher_Notes.pdf": "7518d29054828c2e48ec351e711bc872b1355c77dd4c06834938d2b1bd629216",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/Object_Picture_Choices.png": "3b30135f12467a453d911f6966f5ddd9723257a539b411602d133a6ed5659f20",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/Object_Picture_Choices.svg": "69d3cd5534996f667b732276ca8885cc5a8d4c32b628aa49540a118dbb5f3b2d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_RE_A2_W06_Captioned_Model.mp4": "fb4a49a8c6fe24f5fc6a9176c00d75e29f639fdb8b615b160f3dabec8043c10f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_RE_A2_W06_Editable_Pack.docx": "cbf2ae9b69663df4ca3ba094d4c84e09ded3a33d071f3ea8aec0a5237fe3e409",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_RE_A2_W06_Editable_Slides.pptx": "a1a6c512c3dd709a4fe6a58b4e7ef83728780722e1a765688468ce2a4641235a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_RE_A2_W06_Knowledge_Organiser.html": "c91d60048149faf7dbc71f8e58b403986354fa095157650db23247226661712c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_RE_A2_W06_Knowledge_Organiser.pdf": "2c8c3c9da4e7819e5cdf42b0f67843ec7187427add8180f1ec999fb13f620aba",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_RE_A2_W06_Lesson.html": "9c7ee1f261c35182044a415ad394314feedb10dc7b60d10e941fea3ec8d142c9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_RE_A2_W06_Model_Transcript.txt": "a6ca7b3c488b43ffcc1fcc8c5c6ef094e5979a41443bc77c66ab0c2e525f0216",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_RE_A2_W06_Pupil_Resources.html": "c30530430fafa181452ddb8a7f428134bd22c56e1293bdb0a9e2a50c1dde1aa6",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_RE_A2_W06_Pupil_Resources.pdf": "4d9ac9cac2fbfada31c9208c3951ab54453afba4f4b37645aeb77ef8c5b4caab",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_RE_A2_W06_Teacher_Notes.docx": "23aef17bf2aad0c16b59918d53238ab785d517dcbbc8d398b2e5dae47fd2b472",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_RE_A2_W06_Teacher_Notes.pdf": "0706bc7e3003b73f547db57b5d4addc8a9b12e256c9827dcbfe154416df01563",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/Object_Picture_Choices.png": "61823fbfac9cc8378bf9dccf87002bbec5a0172f8a1b156c7b5e7a77ad4be685",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/Object_Picture_Choices.svg": "f7d4d669cad78123ae1677643159ac0a580c5b40be987d0ce718cbec3be561d7",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_RE_A2_W07_Captioned_Model.mp4": "273e591f8f4d9aede79ef762e4c709e58e5be58f1a95821780b33e80b621ab31",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_RE_A2_W07_Editable_Pack.docx": "41c5056b823304bc1c93a84bc059f5c4cac5d2dac18574445cbe1664587ba4bd",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_RE_A2_W07_Editable_Slides.pptx": "1a223626bf3dc0fb803a90b1611a7215e7733240077cb9db0acd7ad37137c65f",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_RE_A2_W07_Knowledge_Organiser.html": "f045845c3986b7341ad177f5ef0563bcbd5423b2867f147766139c3b2ff5cc83",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_RE_A2_W07_Knowledge_Organiser.pdf": "8b4d72e01d82d45ce1991b6a9f16ce8e74c77314b79d5868262ea2a364302b26",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_RE_A2_W07_Lesson.html": "4032c299b21c665de3dd6a52806b62a7859bbf66e6a5520a76b822e80b710b1a",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_RE_A2_W07_Model_Transcript.txt": "727132cc5127b5de5761f11e9839633762a5bc535aa9d66f2ffbaac2876791d1",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_RE_A2_W07_Pupil_Resources.html": "0cfd7c8bfa01e12d0ae1d6304282c25b89466c9a8fa70aa9424213201ed6e753",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_RE_A2_W07_Pupil_Resources.pdf": "67170203f37efb20590330b55d401d6300100f786984a094d03441b092c0677c",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_RE_A2_W07_Teacher_Notes.docx": "308678cdb78aca4f426c5c8a6a764bd8f4947daabfd107839e2d14cd9983b042",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_RE_A2_W07_Teacher_Notes.pdf": "5f654faefcf0f120218b23a5334f49774b0ba7f41a15eca5b6e6f94d8ea487af",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/Object_Picture_Choices.png": "5856a89d799c11575f8a32a0e2741301485abf224af7414ec785fee252d20eab",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/Object_Picture_Choices.svg": "b38c41caf0da521a85c82245aec46d9785445391915c1ce868e6e455c4c06407",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/README.txt": "b18e6a10681a2287090de194cb29747da642f300b3a25d7c11b3b45bcd814714",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/Review_record.html": "1bc3e0b332600d5254395a4c0df7b4ae304a7e79d8ac8bef0024b4fd8943b6fc",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/SHA256SUMS.txt": "b2de4b668a22d789c015d63198685a286364e89970ca8e7ce295bc95e94f1d2d",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/START_HERE.html": "7f766a100fb4698aed7a8fa7d7cf200d143aa0d1420dff10f81b2beecd1bd3b2",
        "Humanities_Teesside/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/Sources_and_checks.html": "99bc81bcc969a4c17d1f2f4b5acd41eb71ddb4743999dcbc8203c5b6a43238f9",
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
    "lessons": "16448b9115440a55374db5e1a37cdad92322ea3d2dfd6873658c89f2223d0e28",
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
