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
    "assets/mbm-hub.css": "1643f51bcfe7f89923e908cf4f79b36a80d8bfa767779ab1c9cebe2e1a8b513c"
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
    "resources.json": "c6389b6c2fbed8c37016bb121d13cd9c13e7f55e0d868157bb7592366af91090"
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
    "visible_body_sha256": "204ce8e89ab6d0299e38e0d291417a1f8b539d7c2dc982edac7d41edfb14b2cd",
    "files": {
        "_sownb/CALENDAR_SPINE.json": "607ebb2e358b4c872de473444bdee1cd112677759af392e68137ecfb7023e489",
        "_sx3/SX3_PASSES_LEDGER.md": "5ea492a8cbc2d6f1108ceedeec6d0b80bc662467183f30e69850e7cfd2c0cc25",
        "tools/sx3/pre_ci_catalogue_sweep.sh": "9848b9e4e9ccab0bd8225d26d7ffa4683c59c249bff688f33c5d665671d9f818",
        "assets/catalogue/display-titles.json": "1aeb2476f0dad53484551775f71a64bddbb39ce4a082e09499f2685f7d3ade71",
        "tools/catalogue/build_display_titles.py": "02c273ff45b553708e6cd770d6ecb0647d925548be911c6b7fe1370061f458e8",
        "tools/catalogue/check_display_titles.cjs": "ef27c6fabcafd05015ba988ee99b0906cabe1a519c1049635ee92b7e7c361ce1",
        "tools/catalogue/check_display_titles_browser.cjs": "0c193780f901cf4d3b7013819a7488567bf7ce40a75d05dbe43c7a6971877344",
        "tools/verify_lessons_chips.mjs": "e417afd94ae4f3a450caab2edf4b6c41d14e4588f070d0ad822263e30a86cf39",
        "tools/sw2/check_tokens_inert.cjs": "a8258b89b5dd00147a0c8b18488a2dcf8102bc20d2ddf2fa1aa0863d25454674",
        "assets/catalogue/lesson-order.json": "5957271b0d58795ddce640baaf59ccbb4a6c2c008092c491a816af52a33db0f5",
        "tools/catalogue/build_lesson_order.py": "35a4c54779b800ae8bd949154d0d19fddb190f49ec18e62efdd86d03313f6180",
        "tools/ux2/hub_gates.mjs": "3d3120df94b1789041370c4045fbcc983635af0b30a0705447f18371bed98944",
        "index.html": "798d5572afecb8db10a516f9a0ed57d54b7d1dc5e220077a6be85d5f046b555e",
        "Science/index.html": "34fbe6ad5d02f887a430c3f822ff0c41b5442797d945e924b5d3259bd40adfcd",
        "Humanities/index.html": "497e5b88cf8c85f449a3fe81d2553c42e320e07e12cdaa0e6e4c393b3a18c1d3",
        "humanities.html": "bfb8f9383680b9c6d849931652db29289b92d5ed18c5f9616cfc0ede0614fa5c",
        "pack.html": "42935782c353525d28b9263a90a8c48e4b5ca764226444edfa68d6f664862be1",
        "assets/catalogue/pack.js": "48396bdf604a2eeb3e63f5ab18988fb2c87d0260586a18dd2f53824af3cd03de",
        "assets/catalogue/pack.css": "ba6c5c84bcff84c023f2f10ac345a159f48ea97b2e8eb542cb3e56435204d63a",
        "assets/catalogue/pack-notes.json": "f0a440b51785ecedb045666f1a5e44c082ff6f91786940636495837639609ec2",
        "tools/sw2/pack_notes.py": "a81a187002a69bcecca28c9c3130f546e1aae279d5af92cf750a6f9fb04c8fe6",
        "tools/sw2/stamp_pack_page.py": "7d751c25a0a00a1602388537df236c0f79dee6facd31be15fc6e7bce38512149",
        "tools/sw2/check_pack_page.cjs": "89f6a087381c5a34342dc5738f67ad0a3d9f4bc8cfb684da451125617a606235",
        "subject.html": "c70ef79bd0090c069167e1a2308baae69f89dc206783befede5baac84561b1d8",
        "assets/catalogue/hub.js": "cf8a420b8940af1e226d93eefd14e49a37899a99ccf5724137654de3774862da",
        "assets/catalogue/hub.css": "4bbfa8cb449ee9e022fe70df48b4d15cf1faab7e81bb09e8f6985a65a91fded6",
        "data/calendar-spine.json": "d199474b13c9d340add2c87165396d83712b0f1c9f8bd03b7b12e8fdf6af0d61",
        "Humanities/David_Cover_Autumn1_W3-W7/index.html": "4e25eb9ca8f9f93c720d88d945f3d6d79580f3362a88698fe7af75d146f01e96",
        "assets/catalogue/catalogue.css": "59abee137c41a8a015e42cf0b32d20b7f4e5fc8e3d236a1cd735322386bf8569",
        "assets/catalogue/catalogue.js": "a0fd3efc8356377effad7249be7222984ce92947a8143259148851dc399de5c7",
        "assets/catalogue/lesson-navigation.js": "42e579bbef3940c24ca4360319290820305a777330b8bff79152b2cb6aa077e3",
        "assets/catalogue/science-shelf.css": "b2b1eb328662d841add139ccfff107f985f17373f1ee82b8762475663097ab60",
        "assets/catalogue/science-shelf.js": "a59fe0c988a5de7d614afc6a36d7dacf14c6e3fa92c732740442e4914d00f356",
        "assets/catalogue/terms-and-styles.json": "cf73f9181fe1927caa63c5ad7e4bf9672556a9cd71856824c087664b37b0780f",
        "assets/catalogue/science-shelf.json": "6bfcac8579a72f8413e158b49460a8b853f284b8dc64bd4da4442c37e92edadf",
        "assets/catalogue/humanities-shelf.json": "3f6a3583f3658b79a544aeef27a778a283069e4842d763cb95728a703669d9a7",
        "tools/catalogue/build_catalogue.py": "249e82b795e0fa5f1eaeb7afd00883a963d63742b50b783fa88f808737ab230d",
        "tools/catalogue/build_science_shelf.py": "396b6aeb7cb3cabe037b7af27877ae7a090e5aa1bce284409e400549d5204c24",
        "tools/catalogue/build_humanities_shelf.py": "0d58e1dd47c9c806b7fefc42437b47947853760e785eb3ed34b35148eea874cc",
        "tools/catalogue/build_science_hub.py": "b00b55dead2cc5566515259b2dbd0b082365823fc29bf10ba40c887256b8d5db",
        "assets/catalogue/science-hub-bindings.json": "510e1a73fbb2f914d6373442300a3671b4a008c664582e3abd22517fdebf27e2",
        "tools/catalogue/check_catalogue_static.py": "5eb7b3ebd11fbfceb9f8c812ec8b7dc5a02b3b162c0f78982f4e7afb6f4eb589",
        "tools/catalogue/check_catalogue_dom.cjs": "877ab8515ba5cbcbd8be32c52cfed067707b675d239250bdf2a68134382798c8",
        "tools/catalogue/verify_education_navigation.cjs": "48d00d8c490157059b6f21664c1b06e8c5af215575ee207040ee0c83c37d168f",
        "tools/catalogue/sync_shelf_card_titles.py": "d5e8fd850e5ac6340f0d1550ea2992fc03ef1fff8deeec144c73685042feaf7f",
        "tools/catalogue/HUMANITIES_STRAND.json": "d2d239ce547e15f39d7776e5de99c0436eebc274a4077f5f627b9f893ee435a3",
        "tools/catalogue/hub_sections.py": "3b201e96e05a124d47c6b5b1063c0df25d2b5c5cf4505aad7494663c7e92a90e",
        "assets/catalogue/shelf-base.css": "15d7b64ad06b9b27c5f03e91da30ba35c4ca01c1b12b1208b06bfefe5e6ff4e0",
        "assets/catalogue/humanities-hub-bindings.json": "cd199564a8c38fdae7425bc99d4d32ae523966ed9e491a590757b3951cd6d5b3",
        "tools/catalogue/restamp_evidence_sha256.py": "bfa35a1f979746d471d5af08152e20017bb20a1655490340c74ff6209652827a",
        "Science/Build/START_HERE.html": "acac26140f5aeef22292e6ce3831fa61aaf5e62432cc3998b340918c8bfaee7f",
        "Science/Grow/START_HERE.html": "d2bec305dec3212215c6f599cad3925c571f9a34ca6e85268893c8ed142170dd",
        "Science/Launch/START_HERE.html": "10b46e7cf26e3aa4b7f1fb4758a039bcbec7000bc2ec8d30dfe3ce0e0b966353",
        "tools/catalogue/SHELF_SELECTION.json": "bfc221a2ddea3dcd9ef5718bacc03deef3fb9968bdcfddc2242b16ec6e31fd07",
        "tools/catalogue/HUMANITIES_SELECTION.json": "8bc58e21f2a3483d97eaf64dbfdc1bbbfeb3599b6bc0693377800a0054fcdf0f",
        "tools/easter/science_original_browser.cjs": "aae28a4166d41546cbe5b0acd0866eeaf5e6f47cd5b1949fc48ecb2d4c79a1ec",
        "tools/science_pack/browser_checks.cjs": "058c9bc1f06c876f2994a23d467d83fced683c6355eb92d0ef43986d3e28d72d",
        "tools/prepare_served_publications.py": "c52ffe6cbbc7bb6e056eb3eb27f0bb9a36bb34d2aa86e5d3e02a63aa3653d3a1",
        "tools/test_served_publications.py": "02f9cd6defc7949c3198470ca28c8476c904adc54344884180b843ba48b8a88b",
        "tools/verify_served.mjs": "96eddcc5a76979e552f6c8c46da240113ccf414361eabdc704146831ad633cc8",
        "tools/test_verify_served.mjs": "2786e345a401f27a4ec29e4af95b3363ea01b9fa99e470bf4413281db0fbb257",
        "_sx2/DECISIONS.md": "98959aafb9360877134158427865aabf69aeab094b499b58c31451fec9aca93e",
        "tools/ux2/resource_sizes.py": "2e8d36613fb39e3114c2006337771ddc9c724f9b6333a6e05cfed4e646e4224b",
        "tools/ux2/s1m_published_input_proof.py": "95b82480a9fdbb607fcaf3077d1e58dc1e9a5eafd96581fdbec281c979de1d10",
        ".github/workflows/s1m-published-input-proof.yml": "fcc9f4c6b6a550873bda92346bb73e47d9ec0cfe95664a8eec66d0e7947dfb76",
        ".github/workflows/watch-main.yml": "9a468937b9eefbcdb010f9eed9a2b48f4111761202932fadad680cc3b477f3b6",
        "tools/verify_v6fin_w7_r1_r7.py": "73fc89a3f9c034ce8ad45b22b443b7bfe0da448ee1fff02c46c62e07790822ff",
        "_sx3/FENCE.json": "03541f944d0ea861a32c476034553b4ce3d43acf89edc5264f3808b4079e9c5a",
        "_sci/HELD.md": "2443f349c9cf1784e1e91ed1e93851e04cd50795403a5c1310c07946aeedd07e",
        "_sx3/RELEASE_LEDGER.md": "85605383b75547480a21388ed9003ac2ccde89b34373a45454595c2d9e0102a1",
        "_sci/WEEK_TOKEN_DISAGREEMENTS.md": "2ece32469fe9212d22dad5cfe7741b7f6cd06bba5429cbe74cb52185161c2858",
        "_passhumd5/CHECKS.md": "53128441515e578baf2e756bf9e49186d0ad95ddc44675f8f02104d393a79d83",
        "_passhumd5/build_text_index.py": "6239cbfed4f5a6b239655de67bd20aa4bd377205806ab479a23578a85b5eacd0",
        "_passhumd5/scan_gvocab.py": "01baaadc2d96cc06e7b458dc19b9734d96d84291e2d1b5c8ab43b08ec43edb58",
        "_passhumd5/p0_cell_map.py": "82d5786ba53cceedf35565ddebee3462c5e33a82536e4376ec73f635539a9158",
        "_passhumd5/CELL_MAP.md": "7c99de6f4ebae890cf2bf989bfae0298fbd3202dd41365a674e079d7e41c57e8",
        "_passhumd5/RETIRE_LIST.md": "70712b696a228d8656eda29fe495ac3084b38b008cbcdf84b0c6ea94c696cdd5",
        "_passhumd5/P0_SOURCES.md": "32b199b75456b911a71eec8469a4731883b831d1689cd3068f42c8012a48ff0c",
        "Science/Launch/Autumn2_W7_2026-27/SCI_L_A2_W7L1_Topics_2_3_Assessment_Introduce.html": "9130c85767d735e19fbc7b9e0dd1b314bd5db58f7e828f39bf35976f26741d7a",
        "Science/Launch/Autumn2_W7_2026-27/SCI_L_A2_W7L2_Topics_2_3_Assessment_Explore.html": "cae2d988234b575f7b9c97d0b6907dda83fcb513ed00e6a4e40ca23ee7ff59f5",
        "Science/Launch/Autumn2_W7_2026-27/SCI_L_A2_W7L3_Topics_2_3_Assessment_Do.html": "45b168db37157559bd29fb8c0b89582d3db97e0772f7a64f6cca40ebd0466928",
        "Science/Launch/W14-W15_2026-27/SCI_L_W14L1_Genetic_Condition_Research_Introduce.html": "3026dec2f838802ce76cfecb2919dfc665f097b4e03e47f12bbfeb7c664258a2",
        "Science/Launch/W14-W15_2026-27/SCI_L_W14L2_Genetic_Condition_Source_Evidence_Explore.html": "e7d58d365b6f9e694f41d656602013715214ec66d097b2039e1fc5978b3afb30",
        "Science/Launch/W14-W15_2026-27/SCI_L_W14L3_Genetic_Condition_Presentation_Do.html": "a87e9f650c2ab23de5361c97fdb6612817b793c7609392656255a7f3fd15cba0",
        "Science/Launch/W8-W13_2026-27/SCI_L_W13L3_Inheritance_Probability_Do.html": "2e53abf3402d40c00e9931e97a498376689e092143def2b5ef9ac032b3434582",
        "Science/Launch/W8-W13_2026-27/SCI_L_W9L1_Cell_Cycle_Introduce.html": "c0b48159102b3cebf72fcd91deccaf49bd9a2083d49b3fc2e9df43892971a436",
        "Science/Launch/W8-W13_2026-27/SCI_L_W9L2_Mitosis_Sequence_Explore.html": "73b82303adacbbfd2f8945514a62fe09805b3cf7ab905a88b11900bd1abd6f78",
        "Science/Launch/W8-W13_2026-27/SCI_L_W9L3_Identical_Daughter_Cells_Do.html": "df5087e190937e8df9213f037023fc77d4c20f5b351ecbfb5884f1fcc90e9ea6",
        "Science/Launch/W8-W13_2026-27/SCI_L_W9_Copy_separate_divide_Classic.html": "280856e8f64319de2e19b0f7766ab954c7138adb27bd5678fa08a52899a42e33",
        "Science/Launch/W8-W13_2026-27/SCI_L_W10L1_Growth_And_Differentiation_Introduce.html": "340c86768c9f6fe8a0bfecb5082aae28710842b27ce302a655b8e6d34ea3e860",
        "Science/Launch/W8-W13_2026-27/SCI_L_W10L2_Stem_Cells_And_Meristems_Explore.html": "3f4955539b7f6861d6ac7388aaf06491e182e9c906d58d448cab5ce94b5a92c9",
        "Science/Launch/W8-W13_2026-27/SCI_L_W10L3_Growth_Stem_Cell_Data_Application_Do.html": "567e92ad6b30eef8c38d9ba34e125334b6c4b0580502341e940c74be2b74c6ef",
        "Science/Launch/W8-W13_2026-27/SCI_L_W11L1_Stem_Cell_Evidence_Introduce.html": "39494550b4d70cb3b21c8c48439bc72f0d2d8b89190e4be6d2be3be6a19fcf38",
        "Science/Launch/W8-W13_2026-27/SCI_L_W11L2_Benefit_Risk_Uncertainty_Explore.html": "3a8d4a33ae5aabe7d5acf1c4aca3d20de8927f6cccd8753818527f1d0f55dfd6",
        "Science/Launch/W8-W13_2026-27/SCI_L_W11L3_Stem_Cell_Discuss_Do.html": "f349213fee22df9d180cf18a31b9b920d28cd4c6dba6e07ce906e85e15288e3d",
        "Science/Launch/W8-W13_2026-27/SCI_L_W12L1_DNA_Hierarchy_Introduce.html": "f01bd523431528632da86bbd9c02c38c6edfe47bffd764f2c4c2c69411fb3752",
        "Science/Launch/W8-W13_2026-27/SCI_L_W12L2_DNA_Structure_Explore.html": "e7aca0789b0a111e0efc5631a6c1d9409ed2dcb2686693e3528a56d2154f99d1",
        "Science/Launch/W8-W13_2026-27/SCI_L_W12L3_Fruit_DNA_Evidence_Do.html": "6e2fff14cfb09c791f80bda13d6386df6d447b3a754db3e2211556f2ba6dec8c",
        "Science/Launch/W8-W13_2026-27/SCI_L_W12_Zoom_into_genetic_information_Classic.html": "058defef68f87f80bed2f6d41ec15fca48b9808021fde468606155cbf8c526a7",
        "Science/Launch/W8-W13_2026-27/SCI_L_W13L1_Alleles_Genotype_Phenotype_Introduce.html": "4d0c893510792f08f75472fce3c2ed234299cab1db4129d93861ec2b5322d61d",
        "Science/Launch/W8-W13_2026-27/SCI_L_W13L2_Punnett_Square_Explore.html": "aba9608d6f10df7f63ae5a6bd0ce63af012dc6389f3708cf747ea19ea844ad12",
        "Science/Grow/W8-W13_2026-27/SCI_G_W10A_Solar_System_Research_Explore.html": "eae7aa0751ba8ffd84a27a316b9e9af1e6e56d94704097b8e5ec7cd0fcaf73a1",
        "Science/Grow/W8-W13_2026-27/SCI_G_W10B_Solar_System_Presentation_Do.html": "18c99f9225f39ec3e6e4d5aecfc94ab8cf208fd2e398e2dfe12f7b2dfb2c31c6",
        "Science/Grow/W8-W13_2026-27/SCI_G_W11A_Global_Warming_Explore.html": "5f9f9c657e4e28808275fc8dd0869224455cf21d2903ea377c3406b3cca7a8e7",
        "Science/Grow/W8-W13_2026-27/SCI_G_W11B_Climate_Action_Do.html": "5ef530499159bcb9ce80a063e110ce4047545f7a70444080afda495b2c7fa7dc",
        "Science/Grow/W8-W13_2026-27/SCI_G_W12A_Science_Connections_Explore.html": "ca2448cb5fc5c946694e844298b53291dbc7872377c443afe90318b7d42ce944",
        "Science/Grow/W8-W13_2026-27/SCI_G_W12B_Science_Answer_Lab_Do.html": "4ce4be0d9399e88b600e31c1eac960a93b2f1601f733e17aed2cfdbcb88a3b43",
        "Science/Grow/W8-W13_2026-27/SCI_G_W12_Follow_the_warming_chain_Classic.html": "0453527f763eeed83f1c45f9a53b02834b2700c12b373a6dad0db1b9269cb43e",
        "Science/Grow/W8-W13_2026-27/SCI_G_W13A_Rover_Rescue_Plan_Explore.html": "40d80695974510bc6d90a2daa6e25741780076cf43637d11f42b581b600c0ceb",
        "Science/Grow/W8-W13_2026-27/SCI_G_W13B_Rover_Rescue_Investigation_Do.html": "94e0f4685d789407d127a2c5c031676aa62277d75365f681ad217172550d1a77",
        "Science/Grow/W8-W13_2026-27/SCI_G_W9A_Spherical_Bodies_Explore.html": "861655ebad796f048961dd3fbb7d7b37c4fa19b124b3b22dadb7b19b0d2facc0",
        "Science/Grow/W8-W13_2026-27/SCI_G_W9B_Spherical_Bodies_Do.html": "4ad909faa2bc690cdb530cdd02555b2c216c27d5a4a8f2986e4e29814dbce984",
        "Science/Grow/W8-W13_2026-27/SCI_G_W9_Turn_Earth_explain_the_sky_Classic.html": "178c695fe2dc166a80abfd26e41174e28ecfa39d4700db0870d7ee27bbffd6e8",
        "Science/Build/W8-W13_2026-27/SCI_B_W12_Give_a_rock_a_job_Classic.html": "509f38056bd09e903c70b0426ac55ab7ff73f7da10261a97eec11d49d7b27d1c",
        ".github/workflows/glv3-verify.yml": "4bf27ca7471a21359e35d1bc7277c5fa0adeb5f31a47c769f192165796037088",
        "_glv3/tools/verify_change_boundary.py": "720fc90defb12858d832296e3425c87d61bdd430cf58a22142ed1402061c67d6",
        "_glv3/tools/browser_verify.mjs": "737ad30f297e061407161743f017614179cc6c56f1c9a3904bbe7c98df38c888",
        "_glv3/tools/chip_gate.mjs": "16cdd5c0ad3745c57340ed0ec6a208d221e4793bfc9b1cd9bc703a6c2613dd9a",
        "_glv3/tools/catalogue_membership.mjs": "4d7ab03e23ee0d3c3fc934f4f0a901afc61169754db099f4f5c24dd9cce058ec",
        "tools/humanities_resources/SOURCE_MANIFEST.json": "9d2972aa39fe12220de92aea2230fd8bdf7bef765d5b7cf2227c440026f546a1",
        "tools/humanities_resources/DOWNLOAD_MANIFEST.json": "fd0a9349db9824e2d03fa816d96a8eae2c974c22e33c03223dd72e85e17f2190",
        "tools/humanities_resources/CONTENT.json": "335ea55d7964d8095064e2c67c95fbd8d65e28b4d1ddf25f6e4ee812abd29b98",
        "tools/humanities_resources/ORIGINAL_MEMBER_MANIFEST.json": "c4ce9e5a0a5d966ee31f401ae476a2dc10a43aa8dc749e09b2cef87b745db073",
        "tools/humanities_resources/build_resources.py": "328d5d92bf37df27cadabbf52b832a4dc102b31c6ccaddb27737a2930fbcb4ed",
        "tools/humanities_resources/check_resources.py": "ec5383e3a34cbff999f190b0014a4a73e00a3a29e2714498f7620fd638dc2aa5",
        "tools/humanities_resources/resource.css": "1aed9aaca0d73a4b200c4e5d0977e73f4e906c747d7340c7a62f4197a8344bae",
        "tools/humanities_resources/resource.js": "ad40afed95490bfcce92dc062da46e1b27bcb96bdc80e37eabdfe02bf6ffc446",
        "tools/catalogue/TERM_AND_STYLE_EVIDENCE.json": "dfea9b56c4a9abe4470c8bc8b8f9db6acd38c5cec0c004544f34950d32af8918",
        "tools/catalogue/TERM_REVIEW.json": "9395de4c2803a7bc2a679cf0659c9df3c41c01e5ac60c0a2d39249414bc12de8",
        "tools/catalogue/SCIENCE_WEEK_BINDINGS.json": "9fa98ad78b0bd3c3f3ee15f88a7b2fd40eea810e6c9fb65ee93b3c5192888071",
        "primary/year5/science/autumn/forces/Lesson8_ExploreGravity.html": "20047720bf1d309055abdf232d341b6fd99b833631efa0bcbfb3dabed9671196",
        "primary/year5/science/autumn/forces/Y5_Forces_SoW_and_Plans.docx": "ca36cfd92f1c768ea66f0eb748d47e6227f67569f77b5472d0da13d03f92f2e6",
        "Humanities/BUILD_W1-W8_2026-27/BUILD_HUM_W1_People_Special_To_Me.html": "030be544f76147106e1a7f817ddca11142fcbaef168c28ef2397316a069f384a",
        "Humanities/BUILD_W1-W8_2026-27/BUILD_HUM_W2_A_Special_Book_A_Special_Place.html": "197d3ebfab750e84d89ee5e3dedb177b9d86d768602d0ef62be0ac4582cd34cf",
        "Humanities/BUILD_W1-W8_2026-27/BUILD_HUM_W2_People_Who_Help_Us.html": "7b90dbfb9e82e1a4d20dda3703e68086c5367643bd3b58c8533e97836dc80521",
        "Humanities/BUILD_W1-W8_2026-27/BUILD_HUM_W8_A_Festival_Of_Light.html": "a91c419bde53ffefe77b17db0e8ebb9973b4df447690c6a41a94c76210a654f5",
        "Humanities/BUILD_W14-W20_2026-27/BUILD_HUM_W14_Festivals_Display_and_Reflection.html": "bf14c15092537d25d1b067d5cc32bba8b5ded673e2d8247b352b0431c8abbe59",
        "Humanities/BUILD_W14-W20_2026-27/BUILD_HUM_W15_My_Week_Timeline_and_Caring_Stories.html": "97e71086dcda835b431f9cf94d545f802429faabbb0bd76d26a30987c70ae8fc",
        "_sx3/CHASSIS_CONTRACT.md": "7bcbd67432df1edcedcccacffbeae56b16ab933cea6dd6ada761a263781930d8",
        "_hum/EVIDENCE_LIMB_CENSUS.md": "43870031ec3c0059fb03ed16180a40d630b2eec63a4fa29cbafd3ccee7415e4d",
        "tools/hum/evidence_limb_census.py": "5d360d643641dd27784f5ef06c850ef20b424d112e6de1a98d1d5768c2ef69e4",
        "Humanities/GROW_W1-W8_2026-27/GROW_HUM_W1_Beliefs_And_Worldviews_Around_Us.html": "e026cb09ca0c26998be6172bd5622545878cef9cd509b4d2f6c0454ca7ab1389",
        "Humanities/GROW_W1-W8_2026-27/GROW_HUM_W1_Migration_On_A_Timeline.html": "dbf44fe5be6e352cd6210d1b7426c15bfd4e00dd6f02a9f1643ab41d90ee75ce",
        "Humanities/GROW_W1-W8_2026-27/GROW_HUM_W2_How_Beliefs_Shape_Who_We_Are.html": "adc0e844bb2b51bb9c0f646464ab03ae67736b28a1e249d27d56c15e28ac9734",
        "Humanities/GROW_W1-W8_2026-27/GROW_HUM_W2_Reading_A_Migration_Source.html": "2c505b209aaf25af14425d63dfc648939257a8f3bade68fd3226296b7da80287",
        "Humanities/GROW_W1-W8_2026-27/GROW_HUM_W3_Why_People_Moved_And_What_Changed.html": "5a389f52fac689814f978804cfa9e1213d9b16df21c74f3219bea27df2edffb2",
        "Humanities/GROW_W1-W8_2026-27/GROW_HUM_W4_Diverse_British_History.html": "1f13e87e4f3f11233b417cf1e05c038e83de2bec3d8c49bfd092b9c5527c7b4f",
        "Humanities/GROW_W1-W8_2026-27/GROW_HUM_W5_Was_It_Significant.html": "9ac862ecd06d8438d8f8a1b4a4a112f5fc95e7136a19226080c6e52c2583fcd8",
        "Humanities/GROW_W1-W8_2026-27/GROW_HUM_W6_Planning_An_Account.html": "a09c410a1b04098e91327b523c04d4877b40343e3c2f01e41c66f65d01002708",
        "Humanities/GROW_W1-W8_2026-27/GROW_HUM_W7_Writing_And_Marking_The_Account.html": "015a5514cc1145a35084834d470f3138a0b41359d43c6e7385a539a81fc36e0c",
        "Humanities/GROW_W1-W8_2026-27/GROW_HUM_W8_Finding_Places_In_An_Atlas.html": "6739b5cb8d059f972012844f20d6a49249b5bec231cc018285675a44dcdca7be",
        "Humanities/GROW_W1-W8_2026-27/GROW_Humanities_W4_Explore_Hanukkah_And_The_Theme_Of_Light.html": "cd82d9e3ba3bddc820e4e6980338f8055d42e4f7c4279532d4eb6a2d78605f10",
        "Humanities/GROW_W1-W8_2026-27/GROW_Humanities_W5_Explore_Christmas_And_Christian_Belief.html": "e21ff0ff140cdff349c3e6f8dc5bc314be9e8d6be05d888cb8008382b5a85daf",
        "_hum/LOOP_CONTRACT.md": "c2574700e93b178c32138a27ba05c5496f3f8f83736154ab1c86b71f552bd08d",
        "tools/hum/loop_adapter.py": "8f4d7cf3435af81286a0fa8ac40e527fd08dab35aba4cf9ca4b69c99e2f17d58",
        "tools/hum/deck_dom.py": "98cf5f472ef46d2b015779d61bc98b49190066018b2fca79b5e893b88bada4ab",
        "tools/hum/STAGE_IDENTITY_RULE.md": "19a8e7883ee47e9d5a4c39effbf912e906d6c91454e3ec67ef182801b8382a51",
        "tools/hum/render_proof.cjs": "35aee6aa2d3b11367c310258160c7e01dabc41913e767968f88c27f6f8ec899a",
        "tools/hum/verify_loop.py": "83b87724d4d9ca22ea55513f99e0df8d7f5dfded247b242a4c3be56693e77dac",
        "tools/hum/fixtures/aut1_twelve_stage_v1_base.html": "ab9f6abd62ef33df3bad621267aec70a5ccad6f765de71d623e55f13f0a5e2c5",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W1_Belief_Identity_And_Belonging.html": "6dc9a434f33931eb5f38c65454feb5fb87588afaa0053f3a0c95c216a4c8fc4a",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W1_Migration_And_Identity_In_Modern_Britain.html": "b965d521d918cd24408059c8d940966c16c138f2a8c40fc51860e2f8d67ea9c3",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W2_Cause_And_Consequence_Of_Migration.html": "c49b62b36952fbe4da9cbd19dfc7401a628ecbc423451a188fa3fd9b55d8dd0a",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W2_Two_Worldviews_Side_By_Side.html": "439d8cacebdc7911314b6aad2bc92d0ecff5dce7364d7bea4b56ac70ba1e15d8",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W3_Can_this_record_prove_it_Classic.html": "dd7d5bac3cb4a31c254c8c2bc0aa8acb46563775202c9bc56b37271f8f1869dd",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W3_Evaluating_A_Digital_Archive_Source.html": "a385de10b4db2e5a5370ed24db214bd0ec0ade59d2604eae12b51d3d74091204",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W4_A_Timeline_Of_Twentieth_Century_Britain.html": "24f7ea8a63f02f88a291a59b65db8c878e8ae85a32d831b79736b31113d10559",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W5_Who_Shaped_Britain.html": "0a1a646dda79dd7db040af551128294caef16fba6e3e90a4dae233d99b34fa7e",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W6_A_Structured_Account_From_Evidence.html": "55e46c6599d930327833d95493f1017fba4ba76c64ba4fddbc540f9ae49985eb",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W7_Source_Based_Assessment.html": "a42f61b9de0ed5b9d89ab18cdde017dff34dd789b43219011a5a563ad7cdab87",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_HUM_W8_Maps_Symbols_And_Grid_References.html": "7dcb2d67927b3d74376f4e1c822aac82d036210af59e94cecd8647ef8d6fe7de",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_Humanities_W4_Festivals_Shared_Values_Day_Of_Peace.html": "2495d9a762c6d434c5d1cbac3b0ac63d8f7562b2f38a98d863d0e3d201f16239",
        "Humanities/GROW_W1-W8_2026-27/GROW_Humanities_W6_Compare_Festivals_Of_Light_Respectfully.html": "d4da31012106415fca6641fcd1d5bcdd7e9213cef98897dcab972f0602d850e4",
        "Humanities/GROW_W1-W8_2026-27/GROW_Humanities_W7_Reflect_On_Remembrance_And_Shared_Values.html": "3fe17c6e46638def69dfd72132605e4540f289f272cc87ca2d9408c7525a5cfa",
        "Humanities/GROW_W15-W20_2026-27/GROW_HUM_W15_Rights_Timeline_and_Belief_Resilience.html": "dd22c4d6f96f00a9f6a1174672c2145dafa34171d1148f65b0c68b1c4b1dae03",
        "Humanities/GROW_W15-W20_2026-27/GROW_HUM_W16_Sources_Campaigns_And_Hope.html": "8acbafb35b90a104d1aad179c188d5e29e4c99e5a35db033daa7087d8edeb07e",
        "Humanities/GROW_W9-W14_2026-27/GROW_HUM_W10_Connected_World_OUTSTANDING_V3_1.html": "a4b6d63afdc7d3a7ec81d4f3ba8b095b75f55b1d6d6e4e534d0f93b1566bb596",
        "Humanities/GROW_W9-W14_2026-27/GROW_HUM_W11_Light_Across_the_Map_OUTSTANDING_V3_1.html": "3ddc21faaf0d98be4304ad63bd8c659b556676288fc0c4ac89b55c622b543a64",
        "Humanities/GROW_W9-W14_2026-27/GROW_HUM_W12_Compare_With_Care_OUTSTANDING_V3_1.html": "3fcb995013519cafcc155e7ad11c3cde94913149dd8362233a3c67e418c0c583",
        "Humanities/GROW_W9-W14_2026-27/GROW_HUM_W13_Belonging_Briefing_OUTSTANDING_V3_1.html": "a8fc4a21540e85c6ff00ecc04fcfcdcf27ffaa3b2017022ee99ed7d5299f5170",
        "Humanities/GROW_W9-W14_2026-27/GROW_HUM_W14_Map_and_Belonging_Challenge_OUTSTANDING_V3_1.html": "6935c53274bf191f7cfd0c62c0c03bae85e60e44c00b85f0abfa19b4dd81aafa",
        "Humanities/GROW_W9-W14_2026-27/GROW_HUM_W9_Pinpoint_the_Place_OUTSTANDING_V3_1.html": "69a9285e4e671645754b80c8fd1624d699977504cfa40aacf770acf51a465024",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_Humanities_W5_Structured_Explain_Response.html": "adaa425bab46005aef4cf6c6d6997760ff75818965a7461af2f145c974016762",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_Humanities_W6_Remembrance_Peace_Across_Beliefs.html": "b0e93d11cd494ec361058214da3193f2721cd6531fbbc99af4a0b3c888dad351",
        "Humanities/LAUNCH_W1-W8_2026-27/LAUNCH_Humanities_W7_Belief_Identity_Assessment.html": "1b2c8e41fe9e740614b0685c6ab594614518acd15788905282d84cbe7d1e239b",
        "Humanities/LAUNCH_W15-W20_2026-27/LAUNCH_HUM_W15_Conflict_Causes_and_Ethical_Decisions.html": "36aad344c9e91f5c1fc4aeb28c111fee64864868e28ee7dd36252d0c6caa1047",
        "Humanities/LAUNCH_W15-W20_2026-27/LAUNCH_HUM_W16_Steps_In_Law_And_What_Comes_After.html": "1b2b12b93d4bf4583aca5356151b2c469d7ee3ba93d502d6a943686cb93a0b42",
        "Humanities/LAUNCH_W9-W14_2026-27/LAUNCH_HUM_W10_Settlement_And_Urbanisation.html": "127026a754e180800e9202a552f938b2af446730bc5e533f2aeb822b12692e64",
        "Humanities/LAUNCH_W9-W14_2026-27/LAUNCH_HUM_W11_Local_Fieldwork_Collect_Data.html": "3f83f53d6a8b7a02d397aa554f6a59977a04c9a1beb3bfa532949f23ed4eef92",
        "Humanities/LAUNCH_W9-W14_2026-27/LAUNCH_HUM_W12_Fieldwork_Data_Graphs.html": "4018cf72fb54cad4c3d6e21d4dcbdec6117554331546fefbd4b756684cc83a8f",
        "Humanities/LAUNCH_W9-W14_2026-27/LAUNCH_HUM_W13_Contrasting_Places.html": "66517aec3c3bf97dc4eb536535aaf009bfb8b91a0f0088b04c7d6d1418fcafbf",
        "Humanities/LAUNCH_W9-W14_2026-27/LAUNCH_HUM_W14_Fieldwork_Enquiry_Write_Up.html": "1e200c6fa11000e66d7e529135876de9c2481ab107f4cf1a68cdc77691f21994",
        "Humanities/LAUNCH_W9-W14_2026-27/LAUNCH_HUM_W9_GIS_Layers_Reading_Place.html": "8544e086b5e4a6c611982f289fb697626731041eb1cbbd77a4f3e454928aba61",
        "Humanities/BUILD_W1-W8_2026-27/BUILD_HUM_W3_Places_In_My_Community.html": "1ed894d2443de648e0deb5aaf4615c6b92b0735abc27c109947a3c31c137d5e6",
        "Humanities/BUILD_W1-W8_2026-27/BUILD_HUM_W4_Then_And_Now.html": "a794d0c8095c8b8a29619335db783ced6742da4bde938161312908eb78c34a04",
        "Humanities/BUILD_W1-W8_2026-27/BUILD_HUM_W5_Same_And_Different.html": "7e8bbd4524445a76e3f22ea8eab447ba4ab7b7d5f44704e74b7633bef2e5f8a3",
        "Humanities/BUILD_W1-W8_2026-27/BUILD_HUM_W6_Our_Class_Map.html": "3ed142de2819ad74040c4ec8a55038225e41f98671a82c018f0a1c4f3a36b5be",
        "Humanities/BUILD_W1-W8_2026-27/BUILD_HUM_W7_A_place_in_the_group_Classic.html": "f2bec0a4a1238ee6be2f02e2c5ae6fb87fa06cf04d4739439d2f2eaca55eaebd",
        "Humanities/BUILD_W1-W8_2026-27/BUILD_HUM_W7_Groups_We_Belong_To.html": "3dc05abc16c9baa2cb2978226d0f047d84fc8f2583fe2ba3da9d9a5a20ccf063",
        "Humanities/BUILD_W1-W8_2026-27/BUILD_Humanities_W4_Show_Respect_When_Handling_Special_Objects.html": "3b884a498d58b04130fe97ecfae52b60ad8c13687d4b82c8581c5a9c7f89670a",
        "Humanities/BUILD_W1-W8_2026-27/BUILD_Humanities_W5_Notice_Similarities_Between_People_S_Beliefs.html": "701831c9205b4756b9397a583370b68f774110bcc11863380622eb816a1bd91a",
        "Humanities/BUILD_W1-W8_2026-27/BUILD_Humanities_W6_Reflect_Quietly_On_Belonging_Day_Of_Peace.html": "788f671f8221b03e2358371e620cba251f03879c7ac223aaec265118b6cd2665",
        "Humanities/BUILD_W1-W8_2026-27/BUILD_Humanities_W7_Share_A_Special_To_Me_Object_With.html": "be33baa63d4523febdbd0c4f6826efe272b68958c3be44b560a349b0ebd05266",
        "_sownb/vb/evidence/a2r/classic_v2_fixture_minutes.json": "110b377332e73395c6f2f2505674e25d71f329c77f2d00cefda6d0c4c9166c63",
        "_sownb/vb/evidence/a2r/fixtures/classic_v2_v1_base.html": "c9ec2ea5fcd7a7b1c370b4e7680a0580a4f69b33b6e6a7023b648988924dfece",
        "_sownb/vb/tools/classic_v2_contract_selftest.py": "1a571a20066abf020bbbba9ec7a6b99a28c627f04cc3165687ac87eae91c979c",
        "_sownb/vb/tools/reshell_classic_v2_contract.py": "ebf77751927f961453f73607e700378729865e44342642cf80817c2a703856c1",
        "Humanities/BUILD_W14-W20_2026-27/BUILD_HUM_W16_Then_And_Now_And_What_Is_Fair.html": "8513df51ec2501cbfe57d63892347c235cf101cfb6fe63eebf868079470b7dd5",
        "tools/hum/admit_transaction.py": "af6d1bece8f0219c316d2f13ca79573a1c9d2a7be299511ba95396bd1fc769e2",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W01/BUILD_SU1_W01_Knowledge_Organiser.html": "556d3d5d29e29c0f25f27d0892bb17c67ba9647e77551486586a0473a40d01d0",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W01/BUILD_SU1_W01_Lesson.html": "f9bdec1a3d49c8fb542f7b02cfa104141e2be8fb1f20bc33c8f6d55a155c4b61",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W01/BUILD_SU1_W01_Pupil_Resources.html": "a17b507c6283060aebd135e10bf7ccc5e2b22cb2a3b152ba4b127dcb9a9cf94c",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W02/BUILD_SU1_W02_Knowledge_Organiser.html": "2ea53fb30d70a48967f945ba2d4d1136c378561cd18ab8d848b4282e2da91367",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W02/BUILD_SU1_W02_Lesson.html": "f5eea0753a495ae58ccff58e0735267213311a758ce88eef4c1e7658edd019df",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W02/BUILD_SU1_W02_Pupil_Resources.html": "89990eb982ab3deb714ceb90bc58d4095aa52149d22b2e8a8092e85d1408dca2",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W03/BUILD_SU1_W03_Knowledge_Organiser.html": "824bd892a835fdc21cd5a005eb9900f8b4871fc892ebd88c87515cf0186cb561",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W03/BUILD_SU1_W03_Lesson.html": "27d31db816e1182bacceb64617aa12c34a51fd5bd36352e8af20cff6625a37f8",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W03/BUILD_SU1_W03_Pupil_Resources.html": "100ab6a30ce901bbc8fb3fada5584070512cbcbcc942b9346dd08c4ac1e277f2",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W04/BUILD_SU1_W04_Knowledge_Organiser.html": "42803ade88d4545eae2d737d3a5dbe6b434e8606289e92a914b153cb0824c994",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W04/BUILD_SU1_W04_Lesson.html": "bb4774e6f3884bb28e60e04b53e389352d99676fa32be5f7c772920b445f15a3",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W04/BUILD_SU1_W04_Pupil_Resources.html": "0f857523e0fc30079aa29ce4692ef0c9d3fc8acbea81c7a100517940fcd4858b",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/BUILD_SU1_W05_Knowledge_Organiser.html": "06b68734e46fd57805bf935d4b29215e6722cf8279ee646ae6cb20bbc9acb16a",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/BUILD_SU1_W05_Lesson.html": "7b8a8b230e7f14179dba20d940c77e62d21c3e5394cf1151bb519ce01d08fae9",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/BUILD_SU1_W05_Pupil_Resources.html": "01ca55af085df21e5098f50624e4f46d6261cad627f0e7400714e0723e4be1f8",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W06/BUILD_SU1_W06_Knowledge_Organiser.html": "bd6d34df7c9686981de13f28d708790df9e436462784fbe3e66d0ff446a58d50",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W06/BUILD_SU1_W06_Lesson.html": "75cea8d6a9ce58156a66638e390393c9fb652709daf9de4a6563e3c422936f55",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W06/BUILD_SU1_W06_Pupil_Resources.html": "5d5ec53e4dd803b6553815487ba543d540b975676d3ec9cccbec3959908c4dae",
        "Humanities/BUILD_W27-W39_2026-27/START_HERE.html": "96e3afcf562a827dd2b235d022748b5b53b59adff43d64d5dae3c39e3ea830cc",
        "Humanities/BUILD_W27-W39_2026-27/Sources_and_checks.html": "dac061e62f58aae8c7c803ae3bc55155a85544a20873c61a6953bff154f7318b",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W01/GROW_SU1_W01_Knowledge_Organiser.html": "304f7b59f07602dcea6463a35491591047cdb7bca7d14a2ec8c56e2c24e3803d",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W01/GROW_SU1_W01_Lesson.html": "a786070e48b2c3fb8fd0fc976a9d690e13f68f431291e1bbed6fc387c85b2e67",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W01/GROW_SU1_W01_Pupil_Resources.html": "7c13f8cabbc820a97de601ff128bb6153f99821051053edd9893b07f183b4306",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W02/GROW_SU1_W02_Knowledge_Organiser.html": "a42bbd596ed226d5899f138011467a9cf3839fb86b2f9eea5b19eba8e13c6ae7",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W02/GROW_SU1_W02_Lesson.html": "cbdc67e1e498f464f65cb66a7343133a98822441f7068b355d81c9d7ae50ef14",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W02/GROW_SU1_W02_Pupil_Resources.html": "e87732ae765b20646256cddfb5716cecb70fc04d708c7d63f5ff695021bd5701",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/GROW_SU1_W03_Knowledge_Organiser.html": "065bdd2a52f0fc5ab531e884fffad40c0367acd1b003932a160b903aba0356b3",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/GROW_SU1_W03_Lesson.html": "cf482ade46f87249adbab42b9e0a2998fea140179de1cff5f779466fdce3e5e6",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/GROW_SU1_W03_Pupil_Resources.html": "c0ec815f418dfaef8e1f99e2e4adabf0bac2b3db1edede34bd2cdd473da16fb8",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/Sources_and_checks.html": "5ac92240747e170ba0614f7b3d75b75821807a35cd80070469d14d39f7c58cd8",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/GROW_SU1_W04_Knowledge_Organiser.html": "1f30e9fbc0857fb5034bf2a0865f3117dc533812992c13c44ac3de38720a0069",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/GROW_SU1_W04_Lesson.html": "63ac556c4567a2188c253c8986448d0f2c762bf528880cbd2102d1acd4257c00",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/GROW_SU1_W04_Pupil_Resources.html": "9f1dc7c4b3541e25828b5bc2d989ab6e473e2e2fcc1e6e56bacc34677b458f18",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/Sources_and_checks.html": "0dfd4a4c0735cd9a5ab1a3afccf041acbfc3a03f73665312a41fa43390eb9136",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/GROW_SU1_W05_Knowledge_Organiser.html": "b3b9079ae07d5fd47c126db1a2ac8d83fee82b921afef61d17fab7262bf6a7bf",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/GROW_SU1_W05_Lesson.html": "0268feebdb8b404c16d392626ba2bb99d636f4f67f09ef68687079c085cee9af",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/GROW_SU1_W05_Pupil_Resources.html": "5f7e4d6dbcfab0e85dc5651a98e7fd63a542bc1c34f453c21397b4e95b8d3991",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/Sources_and_checks.html": "138d10b4b93fc3fdf1ebba492a2792fd7965f9b1ee609e65baa87628a486c30d",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/GROW_SU1_W06_Knowledge_Organiser.html": "b2e73fd5f74e5f36c546aa6bcdc464a2ba8e8d47a0351fcd6e3d77c17c8c1531",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/GROW_SU1_W06_Lesson.html": "84cc8979fde68076a8254971942a8c43d60c61adde9cc0830466a976273cff0f",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/GROW_SU1_W06_Pupil_Resources.html": "09f8fb65218fc8cf4ceea14efcbd7d33addba1dc1d629913db16612ae75a52ea",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/Sources_and_checks.html": "6402d0a62614985befaabdcdd2296e651f5a81658084d6211242400db7116964",
        "Humanities/GROW_W27-W39_2026-27/START_HERE.html": "7d653c761494c58a997c9984850da495c8040348d1c09c1473e2a840cba2be27",
        "Humanities/GROW_W27-W39_2026-27/Sources_and_checks.html": "587e8e655bf20804a54d3fda8139564bfb7c73b1b3eeba5fe15ac975765baa79",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W01/BUILD_SU1_W01_Captioned_Model.mp4": "a49c4ba757e05244a3514a3fa95944d0686fb787d8a5a6a1f8d34caeef2c822d",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W01/BUILD_SU1_W01_Editable_Pack.docx": "6ed8f2a9403b24efa1068b9d2f34d48352ceece1ccd554287ae3be2ba5ea8ad1",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W01/BUILD_SU1_W01_Editable_Slides.pptx": "55696d71a8f85a7c51eed236fb648ab322ad31772a0b97308208bd7dc7554274",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W01/BUILD_SU1_W01_Knowledge_Organiser.pdf": "3daa27fc23d55e11c050cc80665b3ae8d7afe07b843bbbae13a66fe4d04b1be8",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W01/BUILD_SU1_W01_Model_Transcript.txt": "0a5582edc851ba73edd8010282a5b966322d7209b5f4eb68cc4dd28f4f20aa26",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W01/BUILD_SU1_W01_Pupil_Resources.pdf": "ef9c078c786c8f828ee92a0d26d55bb81a9206fb87e71f1eb4d33f1dbaf04334",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W01/BUILD_SU1_W01_Teacher_Notes.docx": "569f30e0367ea2b0d56d6bc35fabd3fc7f8f5d517618afbc41fba434bd98ef9c",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W01/BUILD_SU1_W01_Teacher_Notes.pdf": "660424e70b03bdfb4a99dfdacd6d0d368e481956c29cf5ff03a8fd452e952dd7",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W02/BUILD_SU1_W02_Captioned_Model.mp4": "aefe389da403522dcbdf8f3fdb5067c7bdf90a0ff8ff1fb7707f7804eac9de18",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W02/BUILD_SU1_W02_Editable_Pack.docx": "3ca9c85ed15c49f849a38c066ea9d9dad6993f7197b961f3a3a07b40728c3449",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W02/BUILD_SU1_W02_Editable_Slides.pptx": "bdbc13726a469708737943d55ac42b1b8a6d9c5afc75f7d58474c226db5849a1",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W02/BUILD_SU1_W02_Knowledge_Organiser.docx": "c280a9c60d299c49427d067329a6c6c7b4b67e66122fcf498d414cf35da37a95",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W02/BUILD_SU1_W02_Knowledge_Organiser.pdf": "13fb289b374621031981d67670ff54d58cad2ee40ce62ccaef8093f5ffc6c6dc",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W02/BUILD_SU1_W02_Model_Transcript.txt": "203f07e34a2b8e06806cedd2df91f9e7d3889d5e0f7348d0e5deb33a1c957245",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W02/BUILD_SU1_W02_Pupil_Resources.pdf": "73a25ee9cbcd769fdcad9c23d2bca097a8e2144b920d17507963dcde75c65baf",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W02/BUILD_SU1_W02_Teacher_Notes.docx": "9fd8098e68579ac79cb48a67042b4e9df58be7ac71a2e42a0a679ef62f7796df",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W02/BUILD_SU1_W02_Teacher_Notes.pdf": "60ce50216826925f6e9f37c6335669a8a85b4e4e8277364ea6a19290f8f70bc8",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W03/BUILD_SU1_W03_Captioned_Model.mp4": "c2f09c83692227219577ce6da71884fa427d2f1567d9a722e30512023ef6735f",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W03/BUILD_SU1_W03_Editable_Pack.docx": "522d69b4d5693c405fec238f2e3e2309a181314c4ad7b3be3e427f56af8855f3",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W03/BUILD_SU1_W03_Editable_Slides.pptx": "74281d8a8811acbee06099eed71dbf2f1619f51979017c0241730a69db5e4150",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W03/BUILD_SU1_W03_Knowledge_Organiser.docx": "f010a05f5973d8ee45ce8b348eb1e07047b63918619bad0a6df36edda4ef4075",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W03/BUILD_SU1_W03_Knowledge_Organiser.pdf": "25adc43c8f95c59ae8139469fcc79df20b6a014b9495b5284abbce46197a4e48",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W03/BUILD_SU1_W03_Model_Transcript.txt": "bf30e462ac86ee97e36404754708d83b3688762731b2b33335c5dade468c64d9",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W03/BUILD_SU1_W03_Pupil_Resources.pdf": "82a4622a2b5f0eb855e5d99cdba40bfe11ac394ce055053d9c0f19babd94aaee",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W03/BUILD_SU1_W03_Teacher_Notes.docx": "16af5aee924e359d46d78b30c7e842026535136ea7cfada7f8d929d1e97d25ea",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W03/BUILD_SU1_W03_Teacher_Notes.pdf": "8dafd0b5027e75ceea48cc8a9a90fdeb9376298460ee326d2a393dfa864e481a",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W04/BUILD_SU1_W04_Captioned_Model.mp4": "c259e240dc8ab049852558ae887a621644bcc2692de039426eeec1f2b6a50f5e",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W04/BUILD_SU1_W04_Editable_Pack.docx": "8fb76522ba846e2b602633575d72edbc2203fee376b65ea6e5ec3234c07d543f",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W04/BUILD_SU1_W04_Editable_Slides.pptx": "e0dfa0a10fcffd565acb1bd9324ea33acc530452b5a9bfb8845473db00a9d610",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W04/BUILD_SU1_W04_Knowledge_Organiser.docx": "122d646d18541619a90c7f61cedbf96445f058e7c3e8ad55a2bb5cbed561be11",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W04/BUILD_SU1_W04_Knowledge_Organiser.pdf": "6213cb311cafc889bb1b9e5956b6673b9e3f3b12f44c12245be2c2a7a4d1f4d6",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W04/BUILD_SU1_W04_Model_Transcript.txt": "7ac7aae40c72f99169b41d5fb45fdd554d8977bd6d0c7772df81ac22809adf36",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W04/BUILD_SU1_W04_Practice_Tally.svg": "94034da923f5d9146a4a2341541253b0714d0d27844ec98f9d3180a57e48b967",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W04/BUILD_SU1_W04_Pupil_Resources.pdf": "3995c584a62c7a6bc38158f4758f57271e99e24aa6fcdfa461c7a36d6f06236d",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W04/BUILD_SU1_W04_Teacher_Notes.docx": "72c5991f0390d01cdeff7498231204d654bd6616645aacdb689646ef9df3ae41",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W04/BUILD_SU1_W04_Teacher_Notes.pdf": "17c13e10b988bafea45dc4b2aa6981fde1ab1a0d75024ef574ac0ebbe68b882e",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/BUILD_SU1_W05_Captioned_Model.mp4": "e696a534b55d4b9a58a037932b73d0c968d8c76c476e186f157da27da504189f",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/BUILD_SU1_W05_Editable_Pack.docx": "6a79174faf73053d2efa818f034eb6a15d80835e608ade7ab343f06348029328",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/BUILD_SU1_W05_Editable_Slides.pptx": "72a819fe5fbd0ecf792cb8c3997b8e35f2556b7ac5c3f0d9aaf48b9bbcaaa361",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/BUILD_SU1_W05_Knowledge_Organiser.docx": "ef4723cbfcb9aac416468f7e7f43a20f30dc2fe5c31f665895bfdbb4d8883432",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/BUILD_SU1_W05_Knowledge_Organiser.pdf": "491165f98896cf3f2bf2d4f07c0b6ed9e808b8604c61ce950c7382c32382139a",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/BUILD_SU1_W05_Model_Transcript.txt": "e5b3c5579cbe1e410c9cb11c5b41c7088b2b163d1d101115f50d54d0592daf45",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/BUILD_SU1_W05_Pupil_Resources.pdf": "5f29131193e4bfa0f5ff97fa47b8518e2f584e66a53108b99eea384ad23bba2b",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/BUILD_SU1_W05_Pupil_World_Map.svg": "22c4a9d78cbf38e3d9dc3291d0032a4890df689ad7fcb5593266ad428574c1f9",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/BUILD_SU1_W05_Teacher_Notes.docx": "c8eb207cd3098236ef3a8b56b1f93ff9388beea6d6ebccc532b2308131b72840",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/BUILD_SU1_W05_Teacher_Notes.pdf": "e655c98552d4e5f705d38b0228ed2724cd6cc3fa4e1f765915bcc2f0b02f9398",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/BUILD_SU1_W05_World_Map.svg": "f86615266f079ae5c60ab50f7762f24e1de1bfae2ffdb566c8420217dc98e561",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W06/BUILD_SU1_W06_Captioned_Model.mp4": "a7aa4c9b569f5fdd09cef8389d4195852a7e9574e0babbdf59bad7a6a70b2b2a",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W06/BUILD_SU1_W06_Demonstration_Plan.svg": "cbac5d90dd0305a0a838a6173a386abda7721a26704152ed98498ade8a5935ad",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W06/BUILD_SU1_W06_Editable_Pack.docx": "34dc7859d2f68a8fe1e7c7c4f3c73207b28051acc7d105f8781f70241476508e",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W06/BUILD_SU1_W06_Editable_Slides.pptx": "afaa9f7f9d3fd7a9f1ebf5c004761a7a954652acce122d2b7381f49e46247a68",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W06/BUILD_SU1_W06_Knowledge_Organiser.docx": "228a659f355e9100c93a2f5b70c339fa19723ead4ebcb53d4e87433a71d4538b",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W06/BUILD_SU1_W06_Knowledge_Organiser.pdf": "825f40a0d538f66d5c6c6af77c8dc226f142af54e44a618d052a4c6c264f2b0d",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W06/BUILD_SU1_W06_Model_Transcript.txt": "e1c1f74d81fe103898e7d7439236c576f533813cdfabb7666a06d0ff6898a764",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W06/BUILD_SU1_W06_Pupil_Resources.pdf": "92df33a81f1105227c33e9c9140bf275e082897b41a82d4dc5e3f20d5da853bc",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W06/BUILD_SU1_W06_Teacher_Notes.docx": "25bd0713adc765ea1b2ba23b0d261d15b30311c0341ea52ef07256b18a54cb32",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W06/BUILD_SU1_W06_Teacher_Notes.pdf": "ecad0575cfff37006a5a48fcc4e0ec342fdc4148fd7ea98560fde01df6e6f3ec",
        "Humanities/BUILD_W27-W39_2026-27/README.md": "2fd481ec81e118a654e5eaf55aac4049664cb52550fa92495873163d6f5d952d",
        "Humanities/BUILD_W27-W39_2026-27/SHA256SUMS.txt": "d20040b4ef79cf5d9630c6387c05240d1b66ec2d4a26526845697f08f872e643",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W01/GROW_SU1_W01_Captioned_Model.mp4": "e310d66789da2ce297adaec86d1860648226ddbad161e4d9d8bdffa0256556b7",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W01/GROW_SU1_W01_Editable_Pack.docx": "5466c946c712d50eb6398d44c30e2a8e05c08aa3a3f8571ac7aeeb03aae5f05d",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W01/GROW_SU1_W01_Editable_Slides.pptx": "c73f7dc6ac3365023441453d2b1a11fb00a91cdfcd5158aaa2b28bddd2b745d2",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W01/GROW_SU1_W01_Knowledge_Organiser.pdf": "e9fb62db511970e67ef733db42f3400c1109791459c63b35aa09fd01fdcd2edb",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W01/GROW_SU1_W01_Model_Transcript.txt": "7daba73404e158c3a27ce63040e2e16350c9e321878b234216bc3b34c3720af2",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W01/GROW_SU1_W01_Pupil_Resources.pdf": "ed937f8fd08d4c8487898f121dc2c6ccf2aaf163da9652f4b444dff8612e51b4",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W01/GROW_SU1_W01_Teacher_Notes.docx": "de7fc5f5d3761000bfdccb6ae8bed28e6f15b7ac62c6b7919c74b499b2687450",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W01/GROW_SU1_W01_Teacher_Notes.pdf": "c9d13c951e445f844e3fbbef61d7091c5db6f29b6ed9ad0f1389e10e60c29a91",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W02/GROW_SU1_W02_Captioned_Model.mp4": "cf538f4d0cdabdc128615e3711c4ae0984995388fd7a122aa648ad706fca2482",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W02/GROW_SU1_W02_Editable_Pack.docx": "fb486dcd75590e9f9c23359ce356610ee365801609fd848835cfae7f3f17bf88",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W02/GROW_SU1_W02_Editable_Slides.pptx": "d742146b1f2df4450a25410a1e74d459eac974993d99a1605eac5a1e79dee397",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W02/GROW_SU1_W02_Knowledge_Organiser.pdf": "5911144fabbda2ea7d80f9884bfdc19c8c75fa107534b437b77991715c43d19a",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W02/GROW_SU1_W02_Model_Transcript.txt": "8435ef18ce6ae1b4e7e9697f74d9d462048d8175a518005324588aec2120033f",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W02/GROW_SU1_W02_Pupil_Resources.pdf": "6eaf5093236d52339271db4458316b86811621ebcdae37413ec41fa1bf59c315",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W02/GROW_SU1_W02_Teacher_Notes.docx": "15a6cdfe01c337ef18ce429c7734f0164f848c27382d56935112de49a43cd314",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W02/GROW_SU1_W02_Teacher_Notes.pdf": "0a357c099a7a5dde6a3a642644c73646d2489ddf1c29ec73e52100d2c37e454a",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/GROW_SU1_W03_Captioned_Model.mp4": "32ddd8a8b2827e1ff94dec0ef249ad5a992db4184d0d81ca07d95eeb7346c2ea",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/GROW_SU1_W03_Data.csv": "5f559be976495304aa10bcbecac68016f37d689898b8c5b18ce63dc8a6da170e",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/GROW_SU1_W03_Data.xlsx": "62e4eeb037894b92700b7aa2de1b21218c4885c2082bdcc3f7ad562e89a8df43",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/GROW_SU1_W03_Editable_Pack.docx": "337647fb9eef9a262a572136a4419e7f0fc6080fe550070396c05bfdc06e7786",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/GROW_SU1_W03_Editable_Slides.pptx": "c0e33bb052e622b74a215b763cc715f7b6c2ddae47ecd1c4e5f1d4cedf163433",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/GROW_SU1_W03_Knowledge_Organiser.pdf": "d64d6a1a877cd8ede4f8ba01b836f1c29f90206d8f7a6435362bcc610fcdf0ca",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/GROW_SU1_W03_Model_Transcript.txt": "306323f65b1bf79cda9e25108eab5667f575d0d0171eccf21e80bfaf734e46a0",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/GROW_SU1_W03_Pupil_Resources.pdf": "a93fe8291336793dd2e58e3428de866995f79866bce1591135ff9f6421e27d3a",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/GROW_SU1_W03_Teacher_Notes.docx": "ced287a00733310763fd4928bf25b3a6c301133673fcaf0472c22cfc5a8992a1",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/GROW_SU1_W03_Teacher_Notes.pdf": "7694fc2e0996163b75642b3c994a119a1b7b8b55076ac0a1b8eac05379577e39",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/Teaching_Visual_1.png": "fcf5b9b21a64d2a33ed2791b79548a8569fe5f2773e162a7829f3919598a39d1",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/Teaching_Visual_1.svg": "aa9cc0f1dd96a80b43d633f2183660f6a06550bc7bd274bf62ae06dc2a011f14",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/Visual_Resource.png": "fcf5b9b21a64d2a33ed2791b79548a8569fe5f2773e162a7829f3919598a39d1",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/GROW_SU1_W04_Captioned_Model.mp4": "8e412b8c6776fbd63d4873e6d7bff4c134257a67460cbbc607f746f258db9051",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/GROW_SU1_W04_Editable_Pack.docx": "64a36272ea6537a6e07d45b42adcf98ed1fe4f2f11df2019c6beccbabb359afa",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/GROW_SU1_W04_Editable_Slides.pptx": "0b98905870b9d3b05bfee9bc8c98799ca4d261bbb53fef342189351f8ee9e96e",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/GROW_SU1_W04_Knowledge_Organiser.pdf": "a082099cc88a581929d3bfae894b7805d2281f3577e639ae7675825ed828c7da",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/GROW_SU1_W04_Model_Transcript.txt": "74bae108b11069e663ce8e46712bb953ae2807c692adb6fc8f1237fd12cf4d67",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/GROW_SU1_W04_Pupil_Resources.pdf": "9e4517ccf154b1878db73176364272bc8fc694f4dc96a47a06ec839437f68ba0",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/GROW_SU1_W04_Teacher_Notes.docx": "4a42b3f7b45eba3504ce60a4949e4e2c011a4f3d4b3ed24d8f188f3fe0dd2400",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/GROW_SU1_W04_Teacher_Notes.pdf": "74c5dbb52a7e6b4a296ec8962533e9b12db7bbeed7c3f0f2fbff071c1e38e0cc",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/Teaching_Visual_1.png": "adcc6cdd025c8fc4fd983d6494d492def017b4452cbd2ca4b742eb0088a715e2",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/Teaching_Visual_1.svg": "be31bc16d7b27d9567b896da60856a96f5897d0901d9caccee17812fd601aaa5",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/Visual_Resource.png": "adcc6cdd025c8fc4fd983d6494d492def017b4452cbd2ca4b742eb0088a715e2",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/GROW_SU1_W05_Captioned_Model.mp4": "3275427de80711dec50885848a78e1a4708ac3cbbe5d6b3cc7f6c2087868ffd3",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/GROW_SU1_W05_Editable_Pack.docx": "0df2e9d8be026b3266c3a6bc6f1f1735b73eb1356b174bf213f8d2f21b463f6f",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/GROW_SU1_W05_Editable_Slides.pptx": "b4937b4671933ec45d5ea6f66befdc215239393d3fdce96faaa622db913219d6",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/GROW_SU1_W05_Knowledge_Organiser.pdf": "2b6da725212837d58574d9f2bb24ec7c7a74087fe1e653b7d5eabf4f6136f2f0",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/GROW_SU1_W05_Model_Transcript.txt": "c1deac7c6f1ae8a591a5eff027682e4875043d6978d12a16be0026085f95a80b",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/GROW_SU1_W05_Pupil_Resources.pdf": "01ead805b20c1a318638d7fe4903bf70721e8b207344045b6be3d95ca297d7e8",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/GROW_SU1_W05_Teacher_Notes.docx": "de2ffa1f5b728a15a638dc9429a7ae67f8c8c528b23c50b38d7806912410a4db",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/GROW_SU1_W05_Teacher_Notes.pdf": "9475a6cc5a4850a9075b660bd61c3db5d2d3fe58ce11ab3a35926110574d6036",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/Teaching_Visual_1.png": "e3e41a4918f05e792c2214855d18a6c6f89f2b7a7a424c3a4d701b7a3f2342a6",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/Teaching_Visual_1.svg": "9013971a1fb9b36164e851fa1f1ce9e47f95a62d3d79e8bfd632602a18681bb3",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/Visual_Resource.png": "e3e41a4918f05e792c2214855d18a6c6f89f2b7a7a424c3a4d701b7a3f2342a6",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/GROW_SU1_W06_Captioned_Model.mp4": "4e599e746cd0a6716a04213ae3475ec99f7e7528fc6695f24f196c349639f699",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/GROW_SU1_W06_Editable_Pack.docx": "c281ed3c373a714ae2809edcf67ee6442da55a9ca0679941e42feeb7a014f6b5",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/GROW_SU1_W06_Editable_Slides.pptx": "dd22a0b91a6a3783411f1680f48b1a61870e34a35fce3fe74f8d1fb478a4ce1b",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/GROW_SU1_W06_Knowledge_Organiser.pdf": "fdefe7ca13cf4cdfc4099e47180b52819c62a1de2fc2702eb09590d5222237f8",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/GROW_SU1_W06_Model_Transcript.txt": "91bcb7bb53a628057b05f910f375a8c92ce736ba7665ac2566b10caa9f706c7d",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/GROW_SU1_W06_Pupil_Resources.pdf": "23f5aa2f1b86a115ac8f6248e031841303818f886734b8c13ef94bbb441074c9",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/GROW_SU1_W06_Teacher_Notes.docx": "91410acf142e6f84af8054d95fa8dfcd68c377ed601cd7b2b50a2e829c0bd817",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/GROW_SU1_W06_Teacher_Notes.pdf": "91f34763b34b940c0c8874405755c8a53d0ba6c01512981e328fdf82e43b8a8a",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/Teaching_Visual_1.png": "a4697b29bafed2a52207dbe3c95c0c4bf15002da406b41148a926369f0a2dc30",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/Teaching_Visual_1.svg": "79e075b98bbde373e9ad8a02616874c2acfee940b34c4794f6d2f9940fbf949f",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/Visual_Resource.png": "a4697b29bafed2a52207dbe3c95c0c4bf15002da406b41148a926369f0a2dc30",
        "Humanities/GROW_W27-W39_2026-27/README.md": "d636efe503812cdf675d140b93568cf5f22136521eb2039ee8189e6dff47e3b5",
        "Humanities/GROW_W27-W39_2026-27/SHA256SUMS.txt": "7b59594b27b8d5369b90b726784f70275f2238130d8e10c3461c7f6abd5472f2",
        "Humanities/BUILD_W27-W39_2026-27/CHANGELOG.txt": "2733da52983532a309738468a0b7e9902025cb9e18018059f5c33a39fd538a62",
        "Humanities/GROW_W27-W39_2026-27/CHANGELOG.txt": "68feec6a79029a747bba6a78aab55c196e13a21631c2cfa068f3be1e20f0f2bc",
        "Humanities/LAUNCH_W27-W39_2026-27/CHANGELOG.txt": "9b409ef65c4e2fde23a6174ff711f3dee859db7f2d24424839dd2944c7796935",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/LAUNCH_SU1_W01_Captioned_Model.mp4": "223fee075c5b8295242c95a66edd11b701b73edc160ca9fc73d7a7da48c8c2ee",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/LAUNCH_SU1_W01_Data.csv": "5e4aac3913e5d2aeb549870cd8855766ef31af63213e65cbf1c3fd6dba4209d1",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/LAUNCH_SU1_W01_Data.xlsx": "15eb1241e17839a5754e406e6087f7ab171b0bce55f26f7a3545bc82df0b5772",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/LAUNCH_SU1_W01_Editable_Pack.docx": "ad8151480497d68c85e7072243a229769ce931b8526992bc6675c7175f57a47c",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/LAUNCH_SU1_W01_Editable_Slides.pptx": "c4d844c0e02c62ddaf7112a9e7f87be69df6ea85ba175face8af12e39b2969f7",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/LAUNCH_SU1_W01_Knowledge_Organiser.html": "7be6562956e16fd2d72bc8b0659e7e91fa2edd79f42ffb485b119b1da7ddfd46",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/LAUNCH_SU1_W01_Knowledge_Organiser.pdf": "4272e713b1440d08b964fa134082c6f4a7b83d156cb667eaa18aaa36f52b6a5d",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/LAUNCH_SU1_W01_Lesson.html": "d688631fd70176aa795c40376add227c8c111ec64971b9031b6badaa8714e45d",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/LAUNCH_SU1_W01_Model_Transcript.txt": "1ebe141e3ecf64c80ed84f03969ccbac792685bf42f8c27c85d65f1c9c5a6006",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/LAUNCH_SU1_W01_Pupil_Resources.html": "3dd0da529309e3f63495194be6906c54aacf05b207e8075a1845902d383e316f",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/LAUNCH_SU1_W01_Pupil_Resources.pdf": "bb2eda97f3173bb2c650f2c37dfdab59b19f359da8b4f97b8a1ee0a36f82c830",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/LAUNCH_SU1_W01_Teacher_Notes.docx": "3d26ce25a7eaa60eb64cd857c3d7bb7249eb313ac67a8f2abaed4472a73e151e",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/LAUNCH_SU1_W01_Teacher_Notes.pdf": "d13c473f5004bdd2d68c7920e8db1a55f8808c408183b89c92132e179c9b08bc",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/Sources_and_checks.html": "29877c91d17404473b4012869c22b7a3ea84ad5be63120e5049cee3d479a0a32",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/Teaching_Visual_1.png": "1f125a3fad70fc5b1303f1e90596bec66a17d0f3ffaf965b77fe4d9d23bfac53",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/Teaching_Visual_1.svg": "9b0309453187d70ee18be143aeb638b8009049bda219c2ac5fd16a5f9601a74c",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/Visual_Resource.png": "1f125a3fad70fc5b1303f1e90596bec66a17d0f3ffaf965b77fe4d9d23bfac53",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/LAUNCH_SU1_W02_Captioned_Model.mp4": "66ae4faa850eac033ece7508948b58c931204044049a977823763a15d8b95380",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/LAUNCH_SU1_W02_Editable_Pack.docx": "f351577d6e32e7c7bfb880b324d663ee66e00f0271e0975b6b7e54ae6a1aba68",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/LAUNCH_SU1_W02_Editable_Slides.pptx": "d18837edbc8a2f2a5403d4e83f36ad1c9a240aabae762d23b994861ff8f2cf00",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/LAUNCH_SU1_W02_Knowledge_Organiser.html": "2940b779de567a8aac8deaa4b0ee410694a0f9ae652daaa4805cc0cdcf817c6e",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/LAUNCH_SU1_W02_Knowledge_Organiser.pdf": "a8abba765492b6eec4b6df3be34f7dc5cafab6823336ad36e501daf9bb638184",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/LAUNCH_SU1_W02_Lesson.html": "466debb38ce5e6acdbcdc3a1d08f4189eb2f0b7b49d1555ab6c92cae41108289",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/LAUNCH_SU1_W02_Model_Transcript.txt": "fa24d4d6d533fb4d393e7a8061c1ec14c6540544c898d283d2ba6da1ba28637f",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/LAUNCH_SU1_W02_Pupil_Resources.html": "6607f47e85e8c21914661812faaa7b3092327884cda7612666a347dde61b3743",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/LAUNCH_SU1_W02_Pupil_Resources.pdf": "19eb93934978239d0927dc1ac9768dc50c06fe66f4ab74f70078f3889be3e79c",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/LAUNCH_SU1_W02_Teacher_Notes.docx": "3ea2071c070e1f13cf5618926848d6983d5ce73cf522f6cd03aef03dd7faa2ba",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/LAUNCH_SU1_W02_Teacher_Notes.pdf": "3e425c737a8298b9607cf5005c3dad835910aa858dcf761a0697456a4539baa3",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/Sources_and_checks.html": "3bfdb8be74a4931b03c73c3d6f623e1af7933f948181e612be70858ef7cdcbe0",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/Teaching_Visual_1.png": "b1ba8d8834e6668a033a1f05ef85cf53e3c7c9f341476366f668041e57c465a7",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/Teaching_Visual_1.svg": "9ebb881a715d28f33e1a825d4e36ee585a213396b911c07bed0ee28a1454fc5c",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/Visual_Resource.png": "b1ba8d8834e6668a033a1f05ef85cf53e3c7c9f341476366f668041e57c465a7",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/LAUNCH_SU1_W03_Captioned_Model.mp4": "28029edfcb191f301c417937cf059eefafc5e37ef4166b79b787663789c8397c",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/LAUNCH_SU1_W03_Editable_Pack.docx": "156a197301265b180b8a8ac81e23042dad26104eb78e756925f1611fe459b90f",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/LAUNCH_SU1_W03_Editable_Slides.pptx": "3f8b693b0ecd2cd64b50a6ca531df68be9b9e0c6d7b1b71c0bc1d8cf02bade32",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/LAUNCH_SU1_W03_Knowledge_Organiser.html": "4e6f5a54ad4a590444c1d21b055054a82094f9fa5a55aa4a1af96c61acc1793b",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/LAUNCH_SU1_W03_Knowledge_Organiser.pdf": "9bb9741a001e3b02d5ae9e33d9a08ce3f646f023e2cb9f2db63c31a73782621f",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/LAUNCH_SU1_W03_Lesson.html": "14e6c922028e16b3aa377ca54ab1a83a308e7dca68a712891c285e7287bd2dff",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/LAUNCH_SU1_W03_Model_Transcript.txt": "c63e32b9009b68a1ce4248430b0068b701325b19963db321cbeb80eab69d2fba",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/LAUNCH_SU1_W03_Pupil_Resources.html": "9ae1089bfd801b77430d72897651eaba4410d7363d5eede82db6bfbd7e659f98",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/LAUNCH_SU1_W03_Pupil_Resources.pdf": "80cdef02da770dbd7d8f3d9da97682329cf84c202419b864fed3d95857c24de2",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/LAUNCH_SU1_W03_Teacher_Notes.docx": "84551fd800990f995721c64c6a149b88c04aee97d7a77312cc9f8c731507598c",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/LAUNCH_SU1_W03_Teacher_Notes.pdf": "d2eb8bfaaccf013cc10af3f91ab2ec30a87dc9b748c1342d40dcfa9e8225c9d5",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/Sources_and_checks.html": "81c9c9ff9dcc195f52f92246cc10cd716fb1b4aee6bde3ffea051d5462985c06",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/Teaching_Visual_1.png": "cb1c35d671b004e50a1584a6f7f59c80b492ae3b5c27aba9a71f8ee3d24e7ae4",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/Teaching_Visual_1.svg": "1cc263433f04e80f3ca72ab056dc32663d6c195784fd796069146c515ed8cc5c",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/Visual_Resource.png": "cb1c35d671b004e50a1584a6f7f59c80b492ae3b5c27aba9a71f8ee3d24e7ae4",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W04/LAUNCH_SU1_W04_Captioned_Model.mp4": "afaef4efbf6fb5a1f1f6245419f74b7fec59c1ba254a58c9999f08b8dabb8c6e",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W04/LAUNCH_SU1_W04_Editable_Pack.docx": "09822d774365f82bd915b577b5cf6ce4a8252d2214cf418ed0a16f8031e27b0c",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W04/LAUNCH_SU1_W04_Editable_Slides.pptx": "dfd131773aaa3af159c6bbc191aa0153461406437c39088e8402d1aaf557eb63",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W04/LAUNCH_SU1_W04_Knowledge_Organiser.html": "a6e0134a5bdec15e6b940fb140540255f7d15bbacb4fb6516d7889a6545b8725",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W04/LAUNCH_SU1_W04_Knowledge_Organiser.pdf": "7832f67c845d0c3efda0492b28192aff90f2ee61a0d5b08c292b6c0c9939725d",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W04/LAUNCH_SU1_W04_Lesson.html": "d5d9f406d55acd52662b011552ecba5ad560e75f7897111776c6b033dd525756",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W04/LAUNCH_SU1_W04_Model_Transcript.txt": "8db6b85dee23dfd7bc7a9f31ee2ba87504005269079bcc59bc3c7b4df7f19c0b",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W04/LAUNCH_SU1_W04_Pupil_Resources.html": "685ac2587f5e0abfd2c9f09207542b120b20b9b3c09074ef0f569a2692e0e741",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W04/LAUNCH_SU1_W04_Pupil_Resources.pdf": "8da1079f3dc75bdf50a02c8ddc2aed0560f339299b55841220262ee631004f08",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W04/LAUNCH_SU1_W04_Teacher_Notes.docx": "a3f6c4f9cb5f6da64a9aa060fce6809adf3f4d013812e3da16ee6393a80fd706",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W04/LAUNCH_SU1_W04_Teacher_Notes.pdf": "b55628296155e388d5fda30820ebe62ffb76c1112585131fc7fdafe6dc7fcff2",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W04/Sources_and_checks.html": "b05876ddf7f80f7319fa1b0b3f49e20187b87ca749fc1f85166b0ea85cec8cd0",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W04/Visual_Resource.png": "47203f71812d19cf3602da19a3a82a73f9c617510cdf9d2b6c9940ed5e687d4f",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W05/LAUNCH_SU1_W05_Captioned_Model.mp4": "459ec0c44b3d41fd95daedbae44d99398fad1a1840582ebb6e116c8bb64485fd",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W05/LAUNCH_SU1_W05_Editable_Pack.docx": "ee6fb8342a3aec3959a8d667f0c3bd394c25223366f5f83153eee230e0a00dc4",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W05/LAUNCH_SU1_W05_Editable_Slides.pptx": "0c79ff61687df027cc40c3f62232c91c514e06d2dd0c11363e5a47799ed67e5a",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W05/LAUNCH_SU1_W05_Knowledge_Organiser.html": "ab7f110871e6ee7c63a8d21c20b12b49b66f5c38693367ff0084a04c64926d02",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W05/LAUNCH_SU1_W05_Knowledge_Organiser.pdf": "fbb2708b0525dadb741cc8f042c4080e0787e6e47930826bcb5c4b8a9065a9f1",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W05/LAUNCH_SU1_W05_Lesson.html": "531974067ae1f24da64d629e96f1695c4d80e52e188a911c5d650d1523d367d9",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W05/LAUNCH_SU1_W05_Model_Transcript.txt": "4eae8b55adaaa42db40945b5e2ec9b210ed3ca966e2d7e68a03d0e1159c632c2",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W05/LAUNCH_SU1_W05_Pupil_Resources.html": "7bc5cb3771c7066972a8cac7d9a62a29721035b7a513026d8a17db3b531a0ee2",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W05/LAUNCH_SU1_W05_Pupil_Resources.pdf": "e7e046348403ba8b169d9eea453c015e572e09168d714921f045f1ea3728f9c8",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W05/LAUNCH_SU1_W05_Teacher_Notes.docx": "d8fd2edf297a6b52239a3cc837fc13e68ac6d14e4ecff2db39edc591cce7a665",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W05/LAUNCH_SU1_W05_Teacher_Notes.pdf": "a1721cf860ce746bd38d1f51a3b618b64959e9fcb8777843d911a8a130cf0929",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W05/Sources_and_checks.html": "dc2bb0e06c96e3c684b1b14be21beb06d7c670c4a7b52a492e55c04d1a6469b2",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W05/Visual_Resource.png": "4facb2f3f70e7ec118b09d93a84cd761698a7ac365ac8334c43633cc9928e59d",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W06/LAUNCH_SU1_W06_Captioned_Model.mp4": "b5dc6922f7561411dcbb1066e6be8a1aea9c848176dfc50aaaf85632c67443f5",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W06/LAUNCH_SU1_W06_Editable_Pack.docx": "0454b707bd56da1055099f1cdda889ee0c3d96ad40185897b867a48a0f8cb24b",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W06/LAUNCH_SU1_W06_Editable_Slides.pptx": "3f6bcc0f7e4e1e3871f21d155287d13f564994f63c6619f1e4ed1fc0e2061206",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W06/LAUNCH_SU1_W06_Knowledge_Organiser.html": "45f2e1ea5821bdd0c38b2bb8c90892ac756f615ab513d3fc1825f5bc4eb6fd01",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W06/LAUNCH_SU1_W06_Knowledge_Organiser.pdf": "e085acb1ca51a66ec61e2785db2878e84d651403833da03ddadb565cd22245fb",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W06/LAUNCH_SU1_W06_Lesson.html": "05b17089118b1e8d8d9491398f4477f224df4bbfd0b6c706aeac8be674140c97",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W06/LAUNCH_SU1_W06_Model_Transcript.txt": "8557f0b96b37c12b4c4d2b068670f24c47e666238b8586d262f320ad8fefa599",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W06/LAUNCH_SU1_W06_Pupil_Resources.html": "5702eda2b9a723956e37be0abff9b71d36880bb2bffac705cc19c9d80d2b7b3a",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W06/LAUNCH_SU1_W06_Pupil_Resources.pdf": "411f8c14aafbedc6225cf71f767afe0107a01a1b0fa444a1ba052d0b6deea300",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W06/LAUNCH_SU1_W06_Teacher_Notes.docx": "f8a0251b8ef2860854a70f3410f6448fd03a663832305dab644e21e2eb8c3dd1",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W06/LAUNCH_SU1_W06_Teacher_Notes.pdf": "4b1f89a0441d54247a79918c3c94753250f88a3d23a75b3f7c98ae492e8d9b6d",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W06/Sources_and_checks.html": "fd389ef2d42c23947542fdcef14250c7f080ef637a5c46fb7a077ed2fba94ede",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W06/Visual_Resource.png": "52a7163cc5ef2299463e95f2512f6414e326d22493a92903052a096f6f0b1a23",
        "Humanities/LAUNCH_W27-W39_2026-27/README.md": "cf39c6f67165f1b6f5c3a0f368385bc1b7babcf17fcfdbfd6d51bca24df98dc9",
        "Humanities/LAUNCH_W27-W39_2026-27/SHA256SUMS.txt": "fbb067847fa74fcf9160deec871d88fcaeefc91ed2368e44b70516cf141cae44",
        "Humanities/LAUNCH_W27-W39_2026-27/START_HERE.html": "dd07b91e212e71e863c96d9a31d489a68f5ea3ec529f50e96f6125251e48eb8c",
        "Humanities/LAUNCH_W27-W39_2026-27/Sources_and_checks.html": "fff2824ac1fa482b7f6640b667be548c56648aa80c9745d1a5ea81871514a2da",
        "tools/hum/dom_oracle.mjs": "258b146a9e85ed3773db915776356bd31fb54defcb1f601b140489f61c4676c6",
        "tools/hum/explicit_document_tags.py": "9fa0d799133e59753848490b9cb052a1872f2204ce520aab6c2e57399812862b",
        "Science/Launch/Autumn2_W7_2026-27/SHA256SUMS.txt": "c03b36ddb50b9d4e626a13c67c33f7d399f6f8d9e94a94133b1efcb42af9bdd2",
        "Science/Launch/W14-W15_2026-27/SHA256SUMS.txt": "0bb93ca935491473b9df0d0f5605f3ea67057c6a00eb78c4925e154b71c8d5eb",
        "Science/Launch/W8-W13_2026-27/SHA256SUMS.txt": "e8c3db8150760d44c9dbac0472200ac8b4043771db89c92dd5665a0232a5c1e1",
        "tools/catalogue/SCIENCE_CHASSIS_CENSUS.json": "fc8cb66f8d3b7ec56976947012d7ae26e7794d95efd3baaad2f182ca4311e81d",
        "tools/rx3_recommended.py": "b4a079a865d6ea956f1a7cb7a4837071db6e96c886565670d1d4a55c661fc150",
        "tools/catalogue/check_title_slide.py": "49815bce6b54d97aed864e403d10bd49d19d886bf5a39cbe7583375ee47ab77e",
        "tools/catalogue/title_slide.py": "3e4e7e8dfa590f3e0a8e24f49939edd9be2d59e4f955aea0935caa003f104788",
        "tools/public_surface_census.py": "310af4565b6b6998e33911352bfbaf37d65497b94d0f03a752d38277f7cdbf0d",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W01/_staff/TA_BRIEF.md": "d28e9ed7ad20dd7da627290a5678ede678471bbc7359d016ee74970321cca8e4",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W02/_staff/TA_BRIEF.md": "e55b49716400e42d4453811db490961d2624954e6f1c09f94bbf8bbf986a78bb",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W03/_staff/TA_BRIEF.md": "9244173372c00c45eb9dd1970f674763b240b6f1e007ae08e8093d8265deea3f",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W04/_staff/TA_BRIEF.md": "bd6a9bcc0f03479fd2b6f7091ff12f1573112b445e791a1da2e3099e808efb99",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W05/_staff/TA_BRIEF.md": "492c7592bca90a896afe9e58dd491d770c3b61f3dbda7b73242ef0a8216e1efc",
        "Humanities/BUILD_W27-W39_2026-27/BUILD/Summer_1/W06/_staff/TA_BRIEF.md": "3550dbc1a874d30b20a3f3da7ac0e8aca636ae4e62e5440db6d839f67917a7ec",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W01/_staff/TA_BRIEF.md": "e4677335086a339d74bfc5d4b275944696e8836fe84b09a117e2ee5984f68149",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W02/_staff/TA_BRIEF.md": "613953445ba2e9ea8ec02e43728ba0300d31cb62de3c2049470ebcbfb228ba79",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W03/_staff/TA_BRIEF.md": "f3490c954df66e312a88faf31dfe19094d364605a3e63fd6a869312b26de4c0b",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W04/_staff/TA_BRIEF.md": "f1d5c286f93baa83a0ca198384ece5d7bd80103f406be659405e77bc34ece4de",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W05/_staff/TA_BRIEF.md": "b6081f08a99f1e0d8acd251694b0e5d349556538ac4498901cfa715e2252386a",
        "Humanities/GROW_W27-W39_2026-27/GROW/Summer_1/W06/_staff/TA_BRIEF.md": "e0b8e34e888371d2b5ead9f052b1cfccde69cf3ed59ef92f2d6914b143e0f271",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W01/_staff/TA_BRIEF.md": "f5a569244b7d84b8a7ed997e60d09e1a4a9679515413a20a1cfa7977bfe9b0f0",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W02/_staff/TA_BRIEF.md": "e380fed313ec542920d02391e7b099aea4b4b202c3916ebd311ab786420d5563",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W03/_staff/TA_BRIEF.md": "f9b7ebe4181d3c7a498852f67be08554f6a127487b68617145a7b43cb246b074",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W04/_staff/TA_BRIEF.md": "cb817fafa40bfb3934bcf892f88e5ec3a072af8dec6b526eb5fea0d4069ac506",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W05/_staff/TA_BRIEF.md": "8f7087fd172849f7462ea5cfc1818f05b97a2bab24d507b6662ef2b3ef28e5d5",
        "Humanities/LAUNCH_W27-W39_2026-27/LAUNCH/Summer_1/W06/_staff/TA_BRIEF.md": "4715d058a4c65e3b7b15c60196b9481159ca445d7bb82fa7697d99d17f47923d",
        "Science/Build/W27-W34_2026-27/_staff/SCI_BUILD_SU1_W01/TA_BRIEF.md": "4d736ec23552cdd162ebfdbd62704e8720731f9005b9d74811a4a41768a9fd13",
        "Science/Build/W27-W34_2026-27/_staff/SCI_BUILD_SU1_W02/TA_BRIEF.md": "9f2180e95614a4d1bff62304ef89fbdb9734f0b8cc11ae30cd4325a0cd76b7d5",
        "Science/Build/W27-W34_2026-27/_staff/SCI_BUILD_SU1_W03/TA_BRIEF.md": "f0ebe46c6820c0c5433fb1030e08a0784760b303288ea649517a8a1c759e3115",
        "Science/Build/W27-W34_2026-27/_staff/SCI_BUILD_SU1_W04/TA_BRIEF.md": "8add803611c31bebd59c5f2891e6634b339bae29d60e3c095052bef2837cdecf",
        "Science/Build/W27-W34_2026-27/_staff/SCI_BUILD_SU1_W05/TA_BRIEF.md": "97f262d1e068199ad7cf6e23712a0ac51d63c95ad9cde71ae6cc932a7068dc3f",
        "Science/Build/W27-W34_2026-27/_staff/SCI_BUILD_SU1_W06/TA_BRIEF.md": "9b031cf913ec3a373a98a5d4e741c0f079b8330fe086d94ad386a0e68c3216fc",
        "Science/Grow/W27-W32_2026-27/_staff/SCI_GROW_SU1_W01/TA_BRIEF.md": "63546c8c2bc40552ac0250f1644fd0c96259a7954afe11d18dcbe35ad263d469",
        "Science/Grow/W27-W32_2026-27/_staff/SCI_GROW_SU1_W02/TA_BRIEF.md": "abc8100fe5feb68c92d56a4c11bfe20eb428395b5772a5ab3a41ef4b947dc2dd",
        "Science/Grow/W27-W32_2026-27/_staff/SCI_GROW_SU1_W03/TA_BRIEF.md": "76f9d9a3607f7a11ea6d8b7a3fd592526d6cd66e2442be3e6236a16906261775",
        "Science/Grow/W27-W32_2026-27/_staff/SCI_GROW_SU1_W04/TA_BRIEF.md": "e9e1e319978e7bd889641aa15718f7229e9ca61e6a8c80290d700de8d0e7c86e",
        "Science/Grow/W27-W32_2026-27/_staff/SCI_GROW_SU1_W05/TA_BRIEF.md": "9be3667d9606e8447442f3d1493ba3312cc29b6e125bdb2ff18c26d9b85ea729",
        "Science/Grow/W27-W32_2026-27/_staff/SCI_GROW_SU1_W06/TA_BRIEF.md": "5dd50bfc74359e194f61a91a12d3553fbe7efbd05519ce07a8267dcad2ab1512",
        "Science/Launch/W27-W34_2026-27/_staff/SCI_LAUNCH_SU1_W01/TA_BRIEF.md": "d2628e2dbc7221fe6963df0b5124d450062331a24b6e3e4d792664a61def054a",
        "Science/Launch/W27-W34_2026-27/_staff/SCI_LAUNCH_SU1_W02/TA_BRIEF.md": "5ba509eca808b5b5b7cd7f8d9927faa0edd7bf1061427996550387c214d7b3a2",
        "Science/Launch/W27-W34_2026-27/_staff/SCI_LAUNCH_SU1_W03/TA_BRIEF.md": "846727993e3adb2eb0ca707c95987c9491e52e40c8675cc9a321503ab7b269f5",
        "Science/Launch/W27-W34_2026-27/_staff/SCI_LAUNCH_SU1_W04/TA_BRIEF.md": "5ead0d772a3544c366d0c93b9e50a50f368f7823c9c08270198cb54b1008396c",
        "Science/Launch/W27-W34_2026-27/_staff/SCI_LAUNCH_SU1_W05/TA_BRIEF.md": "d0fa0a5a9593dd145cbe56c618da6a288cf9c2897b971778e20ff42c1cea8647",
        "Science/Launch/W27-W34_2026-27/_staff/SCI_LAUNCH_SU1_W06/TA_BRIEF.md": "8b6313307fdafebe8a2d6d9efd47b2ae3dee3f088a6bcb90497fdb2b835b3cbd",
        "Science/_staff/PROVENANCE.md": "4bc74f9bf2aac0a9a1fef7f6c1410ba835173ee622b90ad4370385b71b50f79d",
        "Humanities/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_A1_W01_Lesson.html": "5f1ab114ecaec7c7a8a56c576af7a8f14f70ff70866465926e55a4aa98ef87ae",
        "Humanities/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_A1_W02_Lesson.html": "9055d34c0069bfc0a19179370164133e4c35f5e50a5f5cf77e9ba18fe84666ac",
        "Humanities/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_A1_W03_Lesson.html": "b093859c48180274b680f1e35d4afb78a309d1099d48fe6fccd51b461d3e232c",
        "Humanities/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_A1_W04_Lesson.html": "bdfd44034f439ae5181c17bfe78e6747af340bb3d15fb0739e99c9de75aab49b",
        "Humanities/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_A1_W05_Lesson.html": "f95a2eb84b151fe03a0a5fad3a98bcc5aafce8f83c7677b8c8681de3b5a0d7af",
        "Humanities/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_A1_W06_Lesson.html": "35e73d60a56b324de4908b19b16522f39defcc8dfba5cb0d90abb2156bffe006",
        "Humanities/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_A1_W07_Lesson.html": "dbc6f3109dd6265e517cb0566e1f6de0bf5b784bbfea423df5384981059382de",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_A2_W01_Lesson.html": "a1c16ce481a960e243e89371550357640648760cf1d6e5dd0d45b89be8d85bdf",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_A2_W02_Lesson.html": "8e6b2f73511aaa359a5605929757ae19a078c6e01584ffdef7d4f77b68a88c9f",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_A2_W03_Lesson.html": "d40fe5863e5cdaaf70ab0ffdf9f4829377e2d35b74a9d5e455385e7a232bc9c8",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_A2_W04_Lesson.html": "2b304ba13036e4d205e6cdaba6c7778e84b8ccbc42d0367ea75fe13db225e7a0",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_A2_W05_Lesson.html": "79900fa6d3f0d3821436e68baf359d47f039e7038e8ec8abe5b1ade0695a0ac4",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_A2_W06_Lesson.html": "bbbf137d46c3aac3fb11ac1b82f3bd425e949953d95e2184590b54a854db159f",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_A2_W07_Lesson.html": "495189e883e2a78a6e24fb3a8005aa4866f5e382fd0afa793d9b48e0b856fd4c",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/GROW_A2_W01_Lesson.html": "15e63b281875f6d62636a9b619abd954526d6c31318687510dbab09271e91e39",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Lesson.html": "d4027f9992d0c3f7413e8741916d43159c074f712a79dd04bdd1613f800ca556",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/GROW_A2_W03_Lesson.html": "663ff01c19bde7cce9cd46596b2b329e167501cdff570f9dbae6ca1fc9ee12b3",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/GROW_A2_W04_Lesson.html": "0395590993c36cefd35e3f8ad9b1cb9220f60f09b9eebf3cabfeffcc64e5f735",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/GROW_A2_W05_Lesson.html": "a2b7242f2c720312b8d75fd3bd3fbf61d5d79df41ef9aca03060e8e656cc621b",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/GROW_A2_W06_Lesson.html": "a85daba32d269cfae3347c0a731a1778560bdcae0e0388538f88863ca2601a6e",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/GROW_A2_W07_Lesson.html": "5124e543efd5f8452ef18f7cba460aa230dd2d52681107de1e59f0ef8f6f7d65",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_A2_W01_Lesson.html": "5dc5be4aee51879803a1da926b42b222d24c9993472128cd0c3d812ff32d5e9e",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Lesson.html": "3ab7cd756a478bafcae91b0144e2b5478e48c8f4af14a292c204defe140970f2",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_A2_W03_Lesson.html": "ed798926fc9029b1e89633cf6aef8ad0b539fd0f85e1bd46b14eaef6ab70816d",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_A2_W04_Lesson.html": "018a35512e73b58a24506983e7f33e502dc03740001f9c6fe07176fc2d62f1d4",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_A2_W05_Lesson.html": "f292ac63fba414206333dffd3869de2657c37036bbfa757de2c9a0eee368760f",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_A2_W06_Lesson.html": "14727c333c6cefd5f7131733cefca33d66c78affec110830e2c42791f1c759f7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_A2_W07_Lesson.html": "facb9ac110bb65f343fda3d2f13bdf384272a40b3f8be62d96d135817b2b7e47",
        "Humanities/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W01/BUILD_S1_W01_Lesson.html": "2482e33c71758259071faccb8a86bf92a16b7479d52dd455e5be825bc8e30832",
        "Humanities/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W02/BUILD_S1_W02_Lesson.html": "5e854d667a77bb6edce02396d0f541315dee5ca17e092e4b5f75657f2961d274",
        "Humanities/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W03/BUILD_S1_W03_Lesson.html": "072dcebd5ed8117b4af623e280afdbebfebdbb8223ab4b8c4caf823e02200431",
        "Humanities/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W04/BUILD_S1_W04_Lesson.html": "2e3d23014e4de69e482bae679a62d1697075d9eea49d13166dcc3251c195dca1",
        "Humanities/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W05/BUILD_S1_W05_Lesson.html": "d98b79c3b7e05c179c61fa5d58a0a48dbbb73d3ecc3118de2867a2bde935910c",
        "Humanities/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/BUILD/Spring_1/W06/BUILD_S1_W06_Lesson.html": "987557d14a2633201d21a15aac34f69adea668db851595ed32e2be24edd04201",
        "Humanities/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W01/GROW_S1_W01_Lesson.html": "f2e5f4ad118f8b8ce7a17cdbaffd012de098b4f5f7b429513e48bc715fa17fb8",
        "Humanities/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W02/GROW_S1_W02_Lesson.html": "519c40e2567bee09bed0fb19edc0dd206570ca9d65e87ef4f2f32525dae5d1ab",
        "Humanities/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W03/GROW_S1_W03_Lesson.html": "1a0c31b74fa1ceeaeebff8ea10141c202bd34ebf9aefc68a281290ac4d742df9",
        "Humanities/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W04/GROW_S1_W04_Lesson.html": "8b609a82bdcaeec34ed7e837af2466367450ff7ba4ce57e4b194b482cbe78458",
        "Humanities/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W05/GROW_S1_W05_Lesson.html": "dda4d977e4499d9d6bc98b7ba1c3eb8a9463a1744ff3a0a81d9782c337a30169",
        "Humanities/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/GROW/Spring_1/W06/GROW_S1_W06_Lesson.html": "b604a07d48ab000ac36a1cd8ef0eb4b1f5da36ae85312ec86c1a06ec762565df",
        "Humanities/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W01/LAUNCH_S1_W01_Lesson.html": "55b570e7070c1f9af8b570cd5fd5d4613c7135d1d6c1bdf8066416799da003b2",
        "Humanities/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W02/LAUNCH_S1_W02_Lesson.html": "2578e4873ac34d541c8269174c1dd84b7e11e928240115a778d5b01719f39bdc",
        "Humanities/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W03/LAUNCH_S1_W03_Lesson.html": "3300ac68f11af9cda9f161e02031f18c5737e0a06f453f29e2565ccca5c39c01",
        "Humanities/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W04/LAUNCH_S1_W04_Lesson.html": "fb4904a633b51bd7e1b118415a373f241b2fd96e048c1c2dd0f4e51d6647f42e",
        "Humanities/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W05/LAUNCH_S1_W05_Lesson.html": "ba6e045a160aa8df7ef4cf2233d30451e725eba82b6eba3c5aa550d47372b863",
        "Humanities/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/LAUNCH/Spring_1/W06/LAUNCH_S1_W06_Lesson.html": "226bcb9a46eefcc248521ae4b8ca8148bb1017dc335776b0656c054237129668",
        "Humanities/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W01/BUILD_S2_W01_Lesson.html": "5ca95456c016e586a970108fd53bbcfb0cf1724db1a7e11907b2c2451ad0a55e",
        "Humanities/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W02/BUILD_S2_W02_Lesson.html": "72590065a98eccc42d4123b2392c973472f095d87a584c6df0f76503fcadbc31",
        "Humanities/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W03/BUILD_S2_W03_Lesson.html": "06d731dbc610e50e6b46dfe9f71385beb8e92a268be3bdf8d5399bffa64ae60d",
        "Humanities/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W04/BUILD_S2_W04_Lesson.html": "4de5f2ef8ff474334ec7ec48307704cc4468655f100a65bffc8b244ac7285219",
        "Humanities/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W05/BUILD_S2_W05_Lesson.html": "db63df0d9e111332d9a6859ba5a8b5a1714ce724f1d847b1314efbd52e826085",
        "Humanities/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/BUILD/Spring_2/W06/BUILD_S2_W06_Lesson.html": "9b54d696d4de412fc6ad4ceabf8bc91b283a405acebf978a566652208d075ca5",
        "Humanities/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W01/GROW_S2_W01_Lesson.html": "9d93b0de8ade11d33abea62f2766664ac7589418694403a2829d375411498d8f",
        "Humanities/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W02/GROW_S2_W02_Lesson.html": "023ecca14955dfcbd1b13cd8d845ce54e98961add7f9bc104d8283107f5b1105",
        "Humanities/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W03/GROW_S2_W03_Lesson.html": "7d95b4c0d60beede6d07eb3bc69570f6a0c020cf102f3f89d721bc24f216e8e7",
        "Humanities/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W04/GROW_S2_W04_Lesson.html": "dfa7b5383aaff4c49293fc503ab5a6ee370ce80065c6690ed72c349f8648343c",
        "Humanities/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W05/GROW_S2_W05_Lesson.html": "698a6096c4c6bcd51bcd3c1066c2b8ad2ce6d6b93b8e45b0e55e8ed6319e3a33",
        "Humanities/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/GROW/Spring_2/W06/GROW_S2_W06_Lesson.html": "0de35a96243bbad825f4291d4a28561dd14d863ceb5c92206537a58b23c26d15",
        "Humanities/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W01/LAUNCH_S2_W01_Lesson.html": "dcf1838d414e806b84bcae5df533f9471d7a8b0be0cd2c0852349b64ab866622",
        "Humanities/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W02/LAUNCH_S2_W02_Lesson.html": "6d85a5671d4c7ae280b59cf02cc2b8c593339350807e225d4b7714997b2e4039",
        "Humanities/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W03/LAUNCH_S2_W03_Lesson.html": "8d266858aae0337432f84c456fb0c8a675de36fad06c25d03ee732941da48991",
        "Humanities/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W04/LAUNCH_S2_W04_Lesson.html": "91baee0bb8cad5c48fac86615263c48173496d570df349252dea042463e9d93f",
        "Humanities/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W05/LAUNCH_S2_W05_Lesson.html": "e93fe22e4ee0db3d7fd05321521d804e3192d7f4f1299c14f42d523a00d284ea",
        "Humanities/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/LAUNCH/Spring_2/W06/LAUNCH_S2_W06_Lesson.html": "d10a5832ac7b86be298e4b08d83f3f426e6731a118287512aa94c2a187bb6475",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W01/BUILD_RE_A1_W01_Lesson.html": "6120f11ef73139427c72d16455a1578bcd9d41fc758073c43a647322139e5e84",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W02/BUILD_RE_A1_W02_Lesson.html": "32b655ec62d74cada8a009ddca5b0f4285abdb48e1c94eac598cb66d51267952",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W03/BUILD_RE_A1_W03_Lesson.html": "6ca005d877400b6893caf1b7e793c73f9c206e2fa29b25abadfae9fb9baf9b67",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W04/BUILD_RE_A1_W04_Lesson.html": "90b96500f6edbb3b918b7bfaded3f9f363d63dd7b2e615ec40b7fbb47cae5592",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W05/BUILD_RE_A1_W05_Lesson.html": "8bfead9a8ccd03a143697e997fdb2e571b96573657b3dbc32890c01848c8d7a9",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W06/BUILD_RE_A1_W06_Lesson.html": "47503b698f9f8e3177adcf855442bd50636ed5c363f19456c22e0800236e5152",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W07/BUILD_RE_A1_W07_Lesson.html": "c6e1debc5ebe82bc0d5e008cbbdac217cd5ffb7b045a6d4fa45d4bed74b0d62b",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_RE_A2_W01_Lesson.html": "51d8023fe37567838c7ef5b0e377b227a52b0cebef8b3f07afbfb1fb1a69394d",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Lesson.html": "52e8974f682baec2f8fb34ebf5d8087b95c03daffe82a1a2c2e7458b9e93bf28",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Lesson.html": "5e4d672e77b78ddaa0204dd6bf0e89078728a71de1afacc18fc278a59d65ad01",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Lesson.html": "c21d501faa52598a8fe87ae0c8ade2d6fdd273182cef2ae20df29ad2ba302d2f",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Lesson.html": "515595c44b56e584627f847a587e83243d8049fac9dd651ffd7795c320bba0d6",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Lesson.html": "789de9f9b1e1987b7b69eb7ad8751307b44108c6266a2954c198798d0fe41c7a",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Lesson.html": "8f9bad8798406811142c11c57e3b4e7d8c19e13e8a1017274cfe2a735fe67a85",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W01/GROW_RE_A1_W01_Lesson.html": "107d230da08bde88fec3b03d6e29b40784c67e4f787adc9bf9c93e8f42a4eba2",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W02/GROW_RE_A1_W02_Lesson.html": "40f2f7f7f235ac0d302e1ebe41e99470e6a1b27ae460c099a388994cfe78669c",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W03/GROW_RE_A1_W03_Lesson.html": "96cdab5f4ee79e2a12ddd84f0178ed88cad0647d73fe361d584db43811f7f23a",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W04/GROW_RE_A1_W04_Lesson.html": "fdfae07fe2feacf017787ccdf2feac14cc8fa621a1aa62604420d615f630f5f2",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W05/GROW_RE_A1_W05_Lesson.html": "d7761c238790e21249796574887cc4fecc01e4d52b5af4154266f972dc6fb37e",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W06/GROW_RE_A1_W06_Lesson.html": "fcbcef20ba801a22fe52ba8dc7eee9fafafc47182db8a40047908436d678f579",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W07/GROW_RE_A1_W07_Lesson.html": "b2d87e32fff13bcef7aa5e4048df815dd19865a6b54313ddc81eb5c85b947fb0",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Lesson.html": "fb65f1586b54091998c873384d2220e350d6dd35996ab2e1c0ed2277b24e9cb0",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Lesson.html": "f003b991143ed389fb6906ba86d6786e299110ae9392729f9f6b0c98fa7c5663",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Lesson.html": "236222756ee58317ec9682321380a991ef2023ec70d0b7c19b5923ff64f4b9af",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Lesson.html": "35ebb0a72043e0e634770c57d62119786557985959dbb42f46363effa6df4fdf",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Lesson.html": "f82948b1a1596dc0873fdb1304acf5b05e20a83d1724e94775d2fd79d23bb666",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Lesson.html": "2fb6439e5f500c59d62478aa533531ca17ac821fb18b67a0a1d78c24625d7269",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Lesson.html": "bdea643384ee2df8e375fd793621bf391f0f428c0d4ff6b5dfb0cd3d7b304783",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W01/LAUNCH_RE_A1_W01_Lesson.html": "45ed365695f99c6965d56a00d1f007bfe90395ad03288cea0f7661cb84392472",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W02/LAUNCH_RE_A1_W02_Lesson.html": "d0e5863c27f12c9b252bce4b869c57fca10e85a23b0791949a6f9f29bed67a6e",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W03/LAUNCH_RE_A1_W03_Lesson.html": "b1bad16ec2c426bb2a88b77df29cba5e2b94afb80d2d0e140975019487d1df86",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W04/LAUNCH_RE_A1_W04_Lesson.html": "240e61b9ceaca4ae77cd199a27297fdc810aaa736b3ad216b2250747440e5480",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W05/LAUNCH_RE_A1_W05_Lesson.html": "681f3d41f7b37cae7bc4049d965c9f46c5e38cc619881abce403fb6fc1755cf8",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W06/LAUNCH_RE_A1_W06_Lesson.html": "0d5a0a71d58a4715ed30b644c08ef7feaeb43aec99ae7ca593f096b6d347ba15",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W07/LAUNCH_RE_A1_W07_Lesson.html": "335041a08d4094428b755c4f70e37f2fa46e55254978d189bdcca2ffc99aef2d",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_RE_A2_W01_Lesson.html": "61d368e16d5848253677a554f1071084ea88407c40d4c8d3cd6c40501396ca8c",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_RE_A2_W02_Lesson.html": "c70a5941a35f28d163a49286a1c93f72626c2afc9d74655833336b1fd9a40ae4",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_RE_A2_W03_Lesson.html": "962dc70295083424236b16615432c7572ab34ed03e02eb477b6cf172d04af0b0",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_RE_A2_W04_Lesson.html": "fbdeafb79997d142e7cd004d9b21af62ea162df778b64c73ba0e290aa906512e",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_RE_A2_W05_Lesson.html": "2ba488d168cdbb7efc50ad018590fd8bae1bd6af7ce83826ab039f82ef5e6651",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_RE_A2_W06_Lesson.html": "ae521ec05c1d2422b1fc850d34d291c528632c67b10f705eb2af97a7a48ce84f",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_RE_A2_W07_Lesson.html": "79a92af856b83dd7961316d1f6a953b320c4689ed25d467e40128a89938c47a4",
        "Science/Grow/W8-W13_2026-27/SHA256SUMS.txt": "3bd2c6ea90c2ee8071c6ae92ab8136be3541d05a16f4f94768431f819c5b152a",
        "ASDAN/Consent_Aimee_La.html": "fba7cf591575cee56f8c8d0ce77d2f03062a4331452c3ff59049310da2780243",
        "ASDAN/Consent_Aimee_P2.html": "9f2c79180c0e6fafda27db94028c53576e3095f80b8b950bf20aa2c6336f1f92",
        "5_6 Local Choice/Rivers/L1e_Final_Briefing.html": "36c042c860537077496228e60939250cff49f9026a69c225b1a4d74d6424156a",
        "tools/liveteach/lt-pick.test.js": "2dc2ed2e3cd21c315f4dd3d7b9000cf6a4b05b299cba8941a5f64db138e76c98",
        "LIVETEACH_LT1_CONTACT_SHEET.md": "364c10fc887179c0ae28bec0919146c64f4ba5960026b213d732263c047cf98c",
        "LIVETEACH_RESIDUE.md": "5a18069638e4bbfb6a4da111f68e4ac3a17f5de4c8aead731d718f794d89e400",
        "404.html": "e899e06d5908fd29dbf3a1011f8e7e7c5c46b216a73a19835c4197b6431c58cc",
        "Build/README.txt": "84aa743004ececee3d3e9aedc295f0afc0f686124dd1b2f2f422b38c7b282a61",
        "Games/Cup_Final.html": "ba96143c03cde6a4b6c0e54b7e0b478877fde1070ef03051c7965c5dc6d1aa68",
        "Grow/README.txt": "9c2c46c4ebfb56c1ae99c7c20ee2bb73a623a3525c8f3daedf718599b7e7cfc6",
        "HANDOVER.md": "b2e4979f17db2ac9dcf2ed8eeb3461ffbdba19ad8713a40b33388132c18381ce",
        "Humanities/BUILD_Scheme_of_Work.html": "2c66d10240492b848d6242d261f1e7a9cdc1f8b756c718f27ad4fbdabce64a31",
        "Humanities/GROW_Scheme_of_Work.html": "f8de9c18ce88bc07a3eaec7bf73a2fd5917253053e4997e7e20a6fe7ce5a2dd7",
        "Humanities/LAUNCH_Scheme_of_Work.html": "4ce63bb630955552535e937ff08df51bd8f9acad9375d88eabff2a13ebc0b8b1",
        "Humanities/Pathway_Tracker.html": "28b134324fd748c745bd59199334dd20331dcb9cebae8982d7cd1262e745d8f1",
        "Launch/Art_L1_Colours_Lines_Like_Me_v5.html": "7218c677193750c4b7e4d7c542736dbf6d3f413dce931921f16210e594f5f69f",
        "Launch/Art_L2_My_Identity_Picture_v5.html": "058540b4dfc57ebda2d9c41cbf8a40f9701a66964729ded273a56ae8500e4641",
        "Launch/README.txt": "d298bccc19f2dc4318a5c5e0a9cdd79b81a7bdc7d20c9d07237b069335ac3f50",
        "Launch/index.html": "997eab91b19a7476cf67c81338b6e23932391bcfe2fefaa1d93b917b36335749",
        "LundyLoop/2_leadership/Head_Office_Summary.html": "9395e47831d7f2fe2b1ebd3ce88cd40de5c811568323b3108e1c05ffa5136a36",
        "LundyLoop/2_leadership/Loop_Walk_Logger.html": "40075564d6166a2b9e6a91dd63ef52390a0405762b677796c60f3a2f36f88cb8",
        "LundyLoop/2_leadership/implementation_plan.html": "1641bf743e49a10414170a0cf190ae9758a5273c7b7cbc9120041aab6c42c5f7",
        "LundyLoop/2_leadership/policy_alignment_matrix.html": "0c3028e51fdad33b163abd906536fef43c29111d42816feffc2fa21ab600c71c",
        "LundyLoop/2_leadership/qa_coaching_sheet.html": "a86b54bacac3c4d5984d5c6750d2e488d5e2b713caa9a86729bcf2c53482901f",
        "LundyLoop/3_subject_guides/art.html": "9de2ed9bc34e0886636f17a9c3df0c4c4b97dbcf3c4f945d688818b7fab2a9a5",
        "LundyLoop/3_subject_guides/asdan_pfa_assessment_companion.html": "44a75d4b71343c5752ed51991e95480287c5a7ef7a559d95d419c8a870fd190d",
        "LundyLoop/3_subject_guides/d_t_and_food.html": "22731c5fdb9e564b766a299541591fbdc774696d1ba9879ad3b21866325238e2",
        "LundyLoop/3_subject_guides/english.html": "6caaa7e80b9c842aa07e17b81b55ab359c855de3eef1588676a8f1644a376cfd",
        "LundyLoop/3_subject_guides/humanities.html": "e5ce252ac77bccff682c3fab672fcb2ab2f022586b2c02e1b189c295b8f64849",
        "LundyLoop/3_subject_guides/mathematics.html": "1ed1f7886102da5e9b4baf1c9dc50b2ec442ea1ce56022e21dd4163e785f45f5",
        "LundyLoop/3_subject_guides/music_and_drama.html": "490525c590790b528422e75e1e3ee4fa08f126d736af67332b798bb056d12524",
        "LundyLoop/3_subject_guides/pe_and_outdoor_education.html": "b0b34da62e1c51d753578b0c0f4dcd2ea81a9ee1e0ecfdab64ba765da172c2d6",
        "LundyLoop/3_subject_guides/pshe_and_rshe.html": "4fe7958c91c6da54e970601ef00ca00034142da8c9115a5bf788c0a331ff2aa7",
        "LundyLoop/3_subject_guides/re_and_citizenship.html": "10852e9190c8cbb0778999aadbfb5ffc2d707f3bfe13d507ac25964aaf1e9ab2",
        "LundyLoop/4_send_and_pupils/Loop_Passports.html": "8593137a25b76d12daf4e9a979937581d0044b4db6c40c69d18d1b0291800d23",
        "LundyLoop/4_send_and_pupils/Pupil_Feedback_OnePagers.html": "0637643812d9b63bf4c25939d8c4516255d33ef6dae78a821328752a5a523b67",
        "LundyLoop/4_send_and_pupils/SEND_Overlay.html": "2916475db946e788fa65bba3a5f2f5b291dd749309ad26787f84e14c37149f71",
        "LundyLoop/5_staff_training/INSET_Twilight_25min.html": "3a31ce1783b035f1fee14105561291d7322dcca06899425db31b73c09c233f86",
        "LundyLoop/5_staff_training/R_Gate_Calibration_Game.html": "e4a730dc50ee1cb55881b51fc9ffc894a65fb4e77d94b7b233c5a0f81e879e26",
        "LundyLoop/5_staff_training/TA_Card_Lundy_Loop_Progress.html": "562923adf14c2bee395d735e87097487038cbede4b37552ed11f92402caa3f61",
        "LundyLoop/5_staff_training/calibration_examples.html": "b7e32613bc33befac9128e11fafd1377c58fc5ca7c81ec77fe76f3d5bb649251",
        "LundyLoop/5_staff_training/five_minute_briefing.html": "a645118122686cc1e1a1aac3ce259abdd87bdb7aa6f7dda5efbbaa53607169be",
        "LundyLoop/6_posters/source/powerpoint-source.js": "061fb14a62b693a6fb60102d0aa91a2005fd2727ea27ab292d35a43461ca6533",
        "LundyLoop/README.txt": "111af76af1200850ae03a779636cd6696fc6b4584958d20512d5be7e59d52d53",
        "LundyLoop/index.html": "f0fabe0c3bb7db290717e69fcb4cc2872fbce309a8f86771f31936a4041f6b57",
        "MASTER_PROMPT_Live_Teach_Projector_Kit.md": "d561dc7bbd5a7e94c5e1fadca7ee9fe4785ad77b2c9a13be28d288c31a7b32db",
        "Planning/BUILD/README.txt": "84aa743004ececee3d3e9aedc295f0afc0f686124dd1b2f2f422b38c7b282a61",
        "Planning/GROW/README.txt": "9c2c46c4ebfb56c1ae99c7c20ee2bb73a623a3525c8f3daedf718599b7e7cfc6",
        "Planning/LAUNCH/README.txt": "55f962061c660a001b8c1eba0a282b26c805498cb9a2106fb7d1e6bc3ffb391d",
        "REBRAND.md": "89826a88bcf37e85e1a4dc8b6a92101192407ae84f6d3cec6ab534b346b4d609",
        "Science/Build/v3_40min/BUILD_SCIENCE_PRACTICALS_MATRIX_PROGRESS_SCHOOLS.html": "bf7e040bd47cb2921b92545c6b4b76a81e3dd643734353bdae49490499d2d83a",
        "Science/Grow/v3_40min/GROW_SCIENCE_PRACTICALS_MATRIX_PROGRESS_SCHOOLS.html": "613e2d77e367617fc252b43007603f4cf8d96f903f196d56831e0308c8454aa1",
        "Science/Launch/v3_40min/LAUNCH_SCIENCE_PRACTICALS_MATRIX_PROGRESS_SCHOOLS.html": "90f5873faa1ed5f1c6c1d83af3a5c06ae41bb028588e066a4d86409c92f346f3",
        "assets/catalogue/science-download-bindings.json": "1e44e0fa5f772b4e65722520619ecd20f0771faad79c4db7aecc5d955bd3305d",
        "Science/Teaching_Packs/BUILD/BUILD_Science_Autumn1_W3-W7_Teaching_Guide.docx": "c4fd055acdb11a2310fe820b6f473733835dc4789b9151cd3377ec4d251f2196",
        "Science/Teaching_Packs/BUILD/BUILD_Science_Autumn1_W3-W7_Teaching_Guide.pdf": "a479821f2de450e28bd414625f8066768d2c72423bd5ff76046536bf8f7a5d7a",
        "Science/Teaching_Packs/BUILD/DOWNLOAD_INDEX.json": "d5656956c366d611eceec99574a3643936e1b82a0b6ee6256fa130bb0621523e",
        "Science/Teaching_Packs/BUILD/SOURCE_MANIFEST.json": "d737b988e0d3aadfe577aea62cf53933eb8d7690dafd326a595162b7e33bd540",
        "Science/Teaching_Packs/BUILD/START_HERE.txt": "7dc574750bc326685d64d0abbd25b632e9f8a724c7aa84f1123055c7f148ec7c",
        "Science/Teaching_Packs/BUILD/assets/made-by-matt-approved.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3-W7_Complete_Pack.zip": "1e66202c29445378b10feb01a5cfb00ce93c43e1fcc3bea9de601d85f6333cef",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3A_Backbones_Lesson_Pack.zip": "f196c85140c531a494a79795e374e15d4bc15121d1e3f3983a1f256ca56a73ce",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Lesson_Pack.zip": "c4280ab8b6408a2c8ff2d13bdde1955841058fc987410d6c532a6db9583582d2",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3_Teaching_Pack.zip": "07e47f445e89ec22b2d8c6050b6b74b7f987732b2655f0d8db071e7e9124ffad",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Lesson_Pack.zip": "d919d3383c97e43e00c542383b62bc9560a1d2f68e1cf5bc763df23361f71c6f",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W4B_Muscle_Model_Lesson_Pack.zip": "ad0d2d1e18cca96811a3acdc708092c6b909d938d6596b4860eedb7d3074f7d3",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W4_Teaching_Pack.zip": "02c91af4af1139ce14542c12fb13ee76bcb82fb7b1faad0db88c36a375d9ad7c",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W5A_Body_Needs_Lesson_Pack.zip": "c4a130816b5d17546fe43566f4c2e91b979cbd01878a23adf6f005fe9dd32389",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Lesson_Pack.zip": "9e3eabe0aa4866eb2213d0aa7d2165983e8afda85e379f6e2783cdc367a784ca",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W5_Teaching_Pack.zip": "9e55e314b5c03e9f80c64a80b23aae7c200b964d838962783d02bc975e464a1e",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W6A_Balanced_Plate_Lesson_Pack.zip": "ca62ad075c5614016e2cd3c352e63b0d04662474832c0c28c629f2a52b73942b",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Lesson_Pack.zip": "fb9965490c8a5d44fd9e2a5423405740e1b9df25857f571a4eb4519194291643",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W6_Teaching_Pack.zip": "60346b224bd796e8f9a6113605ee3a98494e789a6d28585bbdcb0513429fd8fa",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W7A_Food_Sources_Lesson_Pack.zip": "53c8c7e375361c2c1e3ccb900017d6f5586a3d90fc5b3a14be517eb81aad419d",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Lesson_Pack.zip": "04b0bbf1564ee434baa39236a5154b7db6f1867a837a2f806c20519064db4d6a",
        "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W7_Teaching_Pack.zip": "5b9c1475cacc375538872ae480d5e071ed06faa2d0d34f58d38eda32dc3d1014",
        "Science/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones.pdf": "570c42fdaeef7d4c714e5b78bb49d970cfecee79414a1610b8d6db337d74d635",
        "Science/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones.pptx": "07e840c37da904610ea52fdd1ae0b6826aa0426d2778b82548fb4f006e63f320",
        "Science/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones_Pupil.docx": "58837cc18cfc2d44a1bc7b24be6fab2342d2dde54e6d6647ba082bcc553391da",
        "Science/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones_Pupil.pdf": "4324477322dd593ae260e14c8c3e355ac33a43d9b432aca25af5332f470430ef",
        "Science/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones_Teacher.docx": "a30fbee2586c2b803f07ecfdd7ffa5c2779ef519b0614951258bbee6605a6d15",
        "Science/Teaching_Packs/BUILD/lessons/W3A/BUILD_Science_Autumn1_W3A_Backbones_Teacher.pdf": "6852b465cc9e424cb792f108fa31ccba452f90a71f9252c7302be66247dcd059",
        "Science/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence.pdf": "8d6684d616b4dcdab42f08bd1935eb88f11572756368bf53a912f81b51d5c745",
        "Science/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence.pptx": "19d4cc8166e3a9d995d47dce93352a533e896183f3314a003047d2de8c3930c2",
        "Science/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Pupil.docx": "82f1d04cd6358fdc3f6840ba00cb339b59259b02bc2a4e42bb97410b9e1c0afa",
        "Science/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Pupil.pdf": "9a79a4609822378d5b2fcd4980172de3f24f485789e46dd5ec88efda31003508",
        "Science/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Teacher.docx": "7f849b0158faa1fe8bba0987354f487e6c78022df3e4bd1b5b1d4f1b61c051da",
        "Science/Teaching_Packs/BUILD/lessons/W3B/BUILD_Science_Autumn1_W3B_Backbone_Evidence_Teacher.pdf": "8b7f52e865574def5fec30400ab20bb5a9fcb0caa9e9c69ed3df33d508905fc1",
        "Science/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs.pdf": "e33f83b4f6636b4cccbff17c5f05627cb15970fc4ded60269fde2414a86e8a7b",
        "Science/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs.pptx": "36e216298251f9764baa23bd8d894b37c2d415fe38eafdf17b33729cba7f07ab",
        "Science/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Pupil.docx": "0dee5d479908ccc14ac17afe664d8c430996d3ea5aa02ba63db5062285445255",
        "Science/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Pupil.pdf": "7f1c1f45d405743c4c5ab3b4ee1728a2d5e4bc49e0dbe80174ca92527d7713f7",
        "Science/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Teacher.docx": "417d3907c7395c5dd188a2001a0e7578212bb87fcf061490cb9bb2b78d41d681",
        "Science/Teaching_Packs/BUILD/lessons/W4A/BUILD_Science_Autumn1_W4A_Muscle_Pairs_Teacher.pdf": "e834c2e011e8236339745cb4bee8499eb652b8f50b349db576f2026b182bb940",
        "Science/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model.pdf": "e905f9f66c1085e5f4dd1dca6a01a9cb12398f7cf58ae72c9f5c0680db86c4fd",
        "Science/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model.pptx": "835302e10c4c9d42b607f8004991e211b37969088a75a8321167686c580c2ea5",
        "Science/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model_Pupil.docx": "2386806265db047de86ee81877131e6eca2d49eb6896cf5e932d05d6fffcfdaa",
        "Science/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model_Pupil.pdf": "62241873d87742418b8e9889f3f21d510b8ca7eec8c066d9cd9a2ed48c61c31a",
        "Science/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model_Teacher.docx": "7929264661f58bd50b6b3d37445efee1aea81c2986f2757e958782febc6eac22",
        "Science/Teaching_Packs/BUILD/lessons/W4B/BUILD_Science_Autumn1_W4B_Muscle_Model_Teacher.pdf": "b58f2f31273f4b5e0fffa7c42c31bb82e741b9a726bc415ec8deaaf353e95beb",
        "Science/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs.pdf": "fd6c8d2f57ebbf3ed3159dc6dce0a87badd45fff85aa9807872cccb0e48b214c",
        "Science/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs.pptx": "61aedc65b748140e93f0a8d33846f22417c9c8dd45f6d7f397c74d199bbb0018",
        "Science/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs_Pupil.docx": "bb1c470bcd7ce4b8d67a5c9b40c2927a6c5e4c45c3a1929f692411244055b835",
        "Science/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs_Pupil.pdf": "400c06df0345091f8106763ef3c87d6827c8c08460ed63e6c3cc6978196ce4e9",
        "Science/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs_Teacher.docx": "3aea73afd099d214959dabad16ccdc5c4fccf9852def555d90b93a4fcb6742e4",
        "Science/Teaching_Packs/BUILD/lessons/W5A/BUILD_Science_Autumn1_W5A_Body_Needs_Teacher.pdf": "59b102ac7c36b715834e1d4143f71ff19ddca35223370487cd99500ac4f2a23f",
        "Science/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission.pdf": "a44ec33f0c1bf6aa8169b18182a746623ec195d4eb73cd3381875173c7d9f5f6",
        "Science/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission.pptx": "97560a78fbc990ea1446a64a509f01b0a2de0541cc9d82cb56ee557d0b28b223",
        "Science/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Pupil.docx": "5470a602ef06198ac0936289a59633c6ccddd5f57a9e3f69a88467ecf499632a",
        "Science/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Pupil.pdf": "bdd15828211eda839093c742513381f6401c1137f9509755244b832f78d467f0",
        "Science/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Teacher.docx": "cc7f542d1ca6304b1b19d821ad981c4bfbb844da2aaee781d769b0d91d5394a1",
        "Science/Teaching_Packs/BUILD/lessons/W5B/BUILD_Science_Autumn1_W5B_Food_Jobs_Mission_Teacher.pdf": "d101e634948e248cbb81c74d1554e9c525ed1c060672576ecb118839ac75c85a",
        "Science/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate.pdf": "a256991e850c6067ff8ef438d044acb16978bc2ec5eb22f0b4e75e427be145b1",
        "Science/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate.pptx": "f2e49ddde23ee01511021c0c531e67cac435334ac2387ee8cd964fa4f1c09352",
        "Science/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate_Pupil.docx": "5ddd738899464e13f47797484c7b67bb8d180f8dfa54190ce6a5ee6989c481a3",
        "Science/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate_Pupil.pdf": "2c0bd6f86ef08e5566c0d4b0dddb7eb317fd8231fb6d839a1c7ab0e247282811",
        "Science/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate_Teacher.docx": "dd41e08c1dacf4665b8d0738e0ebdd0afd9adcdc9014fc4007a81bcc774509fb",
        "Science/Teaching_Packs/BUILD/lessons/W6A/BUILD_Science_Autumn1_W6A_Balanced_Plate_Teacher.pdf": "e38a3490fe006d6b1f5ff54e4b93f02b33f58aa912822d5d31d6c3dfaf5389dc",
        "Science/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison.pdf": "78ba407d2c75bb56c39770ef002350a522868ab35dd49bb91047ea1728e4739a",
        "Science/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison.pptx": "c0c0424d3877f7aebb676b425044ac93880dabd761988368317580ca5adfcab6",
        "Science/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Pupil.docx": "5f6021b68a0d49d75caeee2d2d188913bdbff24bebb5c50e90e7479e0918111e",
        "Science/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Pupil.pdf": "5e35dac7e16dc7548d64aaf8af3b00ffe8e5e554bb8076d89ab47b57975429e9",
        "Science/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Teacher.docx": "32a3c2580e7cb8b6e2e4696419f191255e3e01090f49f7ef0cf066ebed149d70",
        "Science/Teaching_Packs/BUILD/lessons/W6B/BUILD_Science_Autumn1_W6B_Model_Plate_Comparison_Teacher.pdf": "cc6e4a4a9d9510c84ea3dbe1a50c01e5f67721933dc543c14c3236f58f7b345b",
        "Science/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources.pdf": "e2e5d516894e369e93861d63df96a6fbd163b096583c7d26fc0d541f38ff2fba",
        "Science/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources.pptx": "e1b43759dab1b36e2e8da895ee8542713a9763e9f615f859f64b5e227ae11470",
        "Science/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources_Pupil.docx": "9685dc0158aa3b7db919980e4f9347805b494f74d0a3835327577962fabd279f",
        "Science/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources_Pupil.pdf": "c566123241ad7acd6e6a3753abfe459934d320065151ffe83a36d6058ccd0d57",
        "Science/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources_Teacher.docx": "382f902b5c4e99a7043645097e676ec37928f0ed1e1bd9598ec84f7107696ec5",
        "Science/Teaching_Packs/BUILD/lessons/W7A/BUILD_Science_Autumn1_W7A_Food_Sources_Teacher.pdf": "65c5f93f10a5bc68bb46e904a57cdc0eadf9bdb947c99181b04c31db41bb641c",
        "Science/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation.pdf": "6cb785fb6c253f362d4caf168f6e06bbd77fa33ea41edfc44c29757189c9bfeb",
        "Science/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation.pptx": "4c91daa2018cc0f0df7256ea1933622dfb7505d55ec38002a6b548f3355d0433",
        "Science/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Pupil.docx": "f10192242483ec30446302afa3ce6334f5c54c9782bac2f352e55ef48b9ae4e1",
        "Science/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Pupil.pdf": "bff6a31bba74a70e7875cf823cee12354abc0cf6c0e28672345e758f9f89896e",
        "Science/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Teacher.docx": "b9d84baca89f4f2498fa14e228d9a522b1ed4009c4bee4f90fcb213f1c992ccb",
        "Science/Teaching_Packs/BUILD/lessons/W7B/BUILD_Science_Autumn1_W7B_Food_Chain_Investigation_Teacher.pdf": "3f2816a6722bfe7b18131206002491899b989a530d8509c59ff2b0871fdc7d61",
        "Science/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W3_Cards_and_Labels.docx": "1ecfd3c50271dd3895f9cbdeb5cc29fb92b08090ba040f3736b5936cab1767a4",
        "Science/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W3_Cards_and_Labels.pdf": "cc6c60baa5ba53dad174ec6749ca054c06ae12730b212b255a635acff35eec2e",
        "Science/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W4_Cards_and_Labels.docx": "c21fd7caf1ae81bd24e2d6d8de073d79361df2767ba204e38de3cb3680bb4aaa",
        "Science/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W4_Cards_and_Labels.pdf": "431654dc2a70d637463ac0c3c0627a33efbcd21ba9f55760da5c18151ffcfef9",
        "Science/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W5_Cards_and_Labels.docx": "ceeb395e64389eecf1af8b3e72e46a96f1102093ed95ae872ba8894d9aecbe21",
        "Science/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W5_Cards_and_Labels.pdf": "d198a60d9b24a3a4ab9e05d2cf7f6eff33e05bc411ba4ce32aab3f0410ad727d",
        "Science/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W6_Cards_and_Labels.docx": "be0cbc702aef03707812a2f84e3e02737bdc2299b3e7baecb1cc9cc98c5dc2b9",
        "Science/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W6_Cards_and_Labels.pdf": "da0bbeac4c479fc4f20173691e236a67e7c936856f6b460332847810c6b4fb60",
        "Science/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W7_Cards_and_Labels.docx": "9bfdec7cd96599afba6e9421ad9d80fc7df9e07be01d5334c5b8a61319919aee",
        "Science/Teaching_Packs/BUILD/resources/BUILD_Science_Autumn1_W7_Cards_and_Labels.pdf": "68746df0bf740914b914ecf6d6c2a1b4b39252171e50621fa7a0c4aa4d1f141f",
        "Science/Teaching_Packs/GROW/DOWNLOAD_INDEX.json": "df85278ac30254d8fa806baaa5a6b19f2bb634a3b0a7023fe766c68d839aff9b",
        "Science/Teaching_Packs/GROW/SOURCE_MANIFEST.json": "e2d194b4151a345daca8b9fec8f67db961d88cde133e5b655eccc9644e6f906f",
        "Science/Teaching_Packs/GROW/START_HERE.pdf": "93a7e61be570fa6934e93973b1a4f4eb200df3da24f83b8ba45ec64ccbf80375",
        "Science/Teaching_Packs/GROW/START_HERE.txt": "856bddba97acc3d6389f09d99d3b0dc6224a4948b2be46c885bbaab7d9485c93",
        "Science/Teaching_Packs/GROW/assets/made-by-matt-approved.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3A.zip": "16bf28c4e0ed8d754db564cc147dec1ec84956e5b2a3453d78c8463d4bccf687",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3B.zip": "77174c720e049cb79b37caee6ba3c2bb0f26ff07c638f3d0184f5d026b09fe1b",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W4A.zip": "3f5917a779d2119a9356b454b8cb3b4180e0e2a8a66d290fac91f7de3fc1ce4d",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W4B.zip": "3a3d79d0d479dbca9c4380071625873e4553221afe21a0a4372d308c60300434",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W5A.zip": "9434d3446815da5461d64c16d6d0b35c0d1066c3b971492a2aa29b9221333141",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W5B.zip": "2e2e8d8c554dc47b1405ebb34b3c8d8b7da3b2a8e3118e9a67b7fcef7207ae5e",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W6A.zip": "ac2856d0c00ddfee1d31fc1a3f3f31ff80e2161a7e0b7f706b19e53be42b7941",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W6B.zip": "3c30ea234c4decde141a25979ce457f3b031addd887cb010daab12dca2b0ab30",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W7A.zip": "6331ade7e38a9fa806ad1965b90e2c7d026a01b56cfd078e299f4b1e194629a9",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W7B.zip": "fb9f571a0f5397ba61c5e9c661a61791647b95868b3d792a515eabbb23febe94",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week3.zip": "6729dd874e434096bdbe5b7ab7b33db1ca5d9a95369f5b5c8dbcb4d4da94ecaf",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week4.zip": "98300c761585df193224fed460aa91ac929b91c3edef7a64eeb61f11e3e968af",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week5.zip": "3ff2075063455fe190397bb383c1d7dff3f17c6fc3a3b41f8d734bf206ffed39",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week6.zip": "22d6c481304de88bed8a65e533cfe7a30f00d93b59edbdf107665eaa88dd68c1",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Week7.zip": "78ebc1a11f9967fad4fd2f1f468121e2ce7c43067069f01e361dd1d1bb85e712",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_Weeks3-7_Teaching_Pack.zip": "3be54e29329689533088a06d8b23c2bd52c0e745d01a7bfaeabc034fac96abb9",
        "Science/Teaching_Packs/GROW/lessons/W3A/GROW_Science_Autumn1_W3A_Friction.pdf": "0e57d93e45bf29236754a735e42f6d2ae923aa1a23c65ebe9ed19041347ced7d",
        "Science/Teaching_Packs/GROW/lessons/W3A/GROW_Science_Autumn1_W3A_Friction.pptx": "13dceb4a32f65165df9353349a69c87465e7f33b9f941036f8f714fd10a9f9da",
        "Science/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Pupil.docx": "9f8afdf8df90eb845d3ea352d36b9bd19dd192a6c040883fe70957eb8be487de",
        "Science/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Pupil.pdf": "856691efece9acaae40a529f949f3d26567345c8f658de9e26eab1bbbdc585cb",
        "Science/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Teacher.docx": "9da8a692bd1ad6b4a040e4b4a970275c90577cbaf73342492d1908148c5d8717",
        "Science/Teaching_Packs/GROW/lessons/W3A/GROW_W3A_Friction_Teacher.pdf": "08c926202671c6b2c25778d5d2dcf2f99a473dd704201f0ef9a58e3a359b18f9",
        "Science/Teaching_Packs/GROW/lessons/W3A/START_HERE.txt": "b5c46c92125be91cb86f64c5969ad8378ab3948b41a82e7be01e7378ccdfc81c",
        "Science/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test.pdf": "1ce1ba083eb62b521368b3c5863c098733ae7d677a1e7c0e641b8e0fd7681d3a",
        "Science/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test.pptx": "3049816d76009ebe3ad1b609e9ca22ec54c3abc82d3e8037b012386759ba278b",
        "Science/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Pupil.docx": "e4333309ef2e2dcf587385063c8e43eee56c3a285089b4f749580124d8c128ea",
        "Science/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Pupil.pdf": "7ddb70eb886f743fd0813b5d581435b36bdfb1a5813e23a6cb6f3b95ccdfee8b",
        "Science/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Teacher.docx": "c0e2ae5adaff89fa05b28e389f7d422e0f638ca9edd33313da61d57d258732cb",
        "Science/Teaching_Packs/GROW/lessons/W3B/GROW_Science_Autumn1_W3B_Friction_Test_Teacher.pdf": "c9c7bf0a6dc4b4a69c1df89bf7fc3a2fdd73c57828ecb0619688611b52a61d5d",
        "Science/Teaching_Packs/GROW/lessons/W3B/GROW_W3B_Friction_Measurements.xlsx": "7ab6650a16051e655dde2f48928810cb2a825e07d4d0a028fea7cc25ee64b1d5",
        "Science/Teaching_Packs/GROW/lessons/W3B/START_HERE.txt": "70a87773d7f0bc53b67cc1023263f2837ec473ceffc6ec1fc79b82823805c756",
        "Science/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms.pdf": "4af5fdcdc9e4d5c651545fbbde812762f924249d42a103d3e41ddfe49c120051",
        "Science/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms.pptx": "394e9a36b4e15708e43346e328c82f89ab3323d4de1df0cb0e2d9743a22d1044",
        "Science/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms_Pupil.docx": "4621245842054aa069124ff174f09c0eff8f8c56769d37c1acea9afe75f3045c",
        "Science/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms_Pupil.pdf": "1b2156236206deff8ec4f909faad3fd552c4caaa0a67cdc703cb900c6eedae08",
        "Science/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms_Teacher.docx": "d6324f71091db4971ca431f635995a5237638871b7a3a4a3455b75a9946425aa",
        "Science/Teaching_Packs/GROW/lessons/W4A/GROW_Science_Autumn1_W4A_Mechanisms_Teacher.pdf": "e7cfbdfcd17ce2734650cd91a04768a3da95156d6acd92bf6956040961d53366",
        "Science/Teaching_Packs/GROW/lessons/W4A/START_HERE.txt": "eb41429cf022ed25c1dfc3cf05d21787608cddc59982cc9d5aa2357135fc842a",
        "Science/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test.pdf": "a7ce2404efddea8e8e4adef88e7e5a54659cebcafc42805dc299370a06569e6c",
        "Science/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test.pptx": "435e8601d04da39509358516118a7240f1060425c0f4ed78a166566110ac9b35",
        "Science/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test_Pupil.docx": "11f958262f40611264f00fa24bbff2292cd214ed84b03204b398bd017a7802e8",
        "Science/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test_Pupil.pdf": "317ae814fd7d1968d2c23a865df8457e2e00838b68bbf32972de1f59ea650c71",
        "Science/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test_Teacher.docx": "ed27ebae53477ad516ec1580b8b0a67e6c81c2eed031ad5094a291b7a24c5835",
        "Science/Teaching_Packs/GROW/lessons/W4B/GROW_Science_Autumn1_W4B_Lever_Test_Teacher.pdf": "21bbcae5a4fb0667afcb6069ac59ed7c80e12ce15b174aa4de67000a8a8080fa",
        "Science/Teaching_Packs/GROW/lessons/W4B/START_HERE.txt": "ec3da721d7bce358ce3458b77bbc5bc0c8ab01a305486e2c711d7919cb5daaa7",
        "Science/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test.pdf": "5057527cb48084fadd02863d9cab017e71818955efe11da514300c5d86743123",
        "Science/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test.pptx": "b9a829b1e5cd38fb891f687b2521de4da4e5e10d433610f614720b21ce14098e",
        "Science/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test_Pupil.docx": "b3a5a3a18ffeb6c72a53b1f23379efa730f8981795509239d072408fa44c99e1",
        "Science/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test_Pupil.pdf": "1e6e19a583143063af3d001a7039c89feaf8aa0bcd9553f8b0dd9e58218aa5e8",
        "Science/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test_Teacher.docx": "5ec3f179b213cba5730070d69c5a46b3d7a20c7bbe665c3049d1f3012e5fc1ec",
        "Science/Teaching_Packs/GROW/lessons/W5A/GROW_Science_Autumn1_W5A_Fair_Test_Teacher.pdf": "adbf06615291d03f65665098eb1aa6a21d7aef15a32dbd2742bd41640d6c3608",
        "Science/Teaching_Packs/GROW/lessons/W5A/START_HERE.txt": "a290efa290a30a831a30ef59dd7fd7826ff7d8906de67c3698caf19619681ccf",
        "Science/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical.pdf": "3782fa567cc5c389de3801cc57a6c46a425e158fed71cb554507537229b833cd",
        "Science/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical.pptx": "946c83f16a9f5357f5d13241039c48a0869c1406a198daac348f8a1e07392ed9",
        "Science/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical_Pupil.docx": "6569a9920bd4597d4fc41fe10709451062fca39f5419c0eb030ebd0be5d85b00",
        "Science/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical_Pupil.pdf": "06d2ba4a1bd1a1ee3175877c9fdb108f3b60d510fa3c843444f61b7bec591fc6",
        "Science/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical_Teacher.docx": "88bdee24e177ae31505cbfe467083f11dc114c0e3b55c3b200a26fe944839e00",
        "Science/Teaching_Packs/GROW/lessons/W5B/GROW_Science_Autumn1_W5B_Fair_Test_Practical_Teacher.pdf": "891c8c64d24767bf85c66c956d9bb85842688424c3ea71eb967e1e6e3207afe2",
        "Science/Teaching_Packs/GROW/lessons/W5B/GROW_W5B_Fair_Test_Measurements.xlsx": "746d64a30be2304c439fb5af7ef79b25dbe8f69d51c8de3c12cd22b8f2ac2104",
        "Science/Teaching_Packs/GROW/lessons/W5B/START_HERE.txt": "d667aaa4d4c65214655f7f9744b7b8b240d5a5d39539300c35aa5f4abcf65ed1",
        "Science/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets.pdf": "31be861dc9629f03f58665c7e2455c4bb3e1bcf4c0eb954dced62cd6d89608ed",
        "Science/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets.pptx": "1fabda3827fa43febb7fc3836619f5dbb7847deee60736c0c72dbc9047d30982",
        "Science/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets_Pupil.docx": "91bcbcbfbfdfa3039f205b9c08f7583fb126c5bd0953a5968921e1ed5eec681a",
        "Science/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets_Pupil.pdf": "08f14322ca35b6da824b798ef777f1e82a17b8c44ab032ce6da19c87fb12a60b",
        "Science/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets_Teacher.docx": "8568d4650f1adeeb8524c86799e49e2172e39dc282f80304471ba81a2f731c05",
        "Science/Teaching_Packs/GROW/lessons/W6A/GROW_Science_Autumn1_W6A_Earth_And_Planets_Teacher.pdf": "1e1a3882a6716e9933f81a5ec94dea92fe8e0f06384080b3c8fe324287cba086",
        "Science/Teaching_Packs/GROW/lessons/W6A/START_HERE.txt": "922b972648e167684acd8d528e0842294ef89a61478b74b65d74ce22c25e15bd",
        "Science/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets.pdf": "82649adfce0d1fbf07b3d5ab00719ae0936812fc8b485e66ea58ff47108c46f9",
        "Science/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets.pptx": "90435b48ab9baa82bd2a3b266e963c2710bedfe79f88671deb2989a859be6602",
        "Science/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets_Pupil.docx": "35785f5169326bc4115abea9934d254ff990e7ccaf3b104bb2469bcf8945a16e",
        "Science/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets_Pupil.pdf": "a2bad2d15b930cce103dc59e5e65b15f63b34afecf3c8d54a8358c28126c6940",
        "Science/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets_Teacher.docx": "d29f02f60a8ac61014113416c8c1042520f3b1a6815476f12b830bb72eff6f56",
        "Science/Teaching_Packs/GROW/lessons/W6B/GROW_Science_Autumn1_W6B_Earth_And_Planets_Teacher.pdf": "318cf84513b3ef6daa97918782dc2ec845cc0f4a5905c315e65a4a92bf9eaf08",
        "Science/Teaching_Packs/GROW/lessons/W6B/START_HERE.txt": "488a26039677af53ef3d8435dd412e98406a807d10534a7725d2261d06869d23",
        "Science/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon.pdf": "c7cbef511bb242f2155b64c64ed8557724d128a469b21671bcdf2b2ca014a176",
        "Science/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon.pptx": "430e539a95c7c53ee57159ef43f3fd3c88fa175ebd58a5a7b32693314ee5c2a0",
        "Science/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon_Pupil.docx": "d4565fa4adf2bd77cc2288652e0d43e15c066a3501bc7a454edd02eafbe137b2",
        "Science/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon_Pupil.pdf": "bff2ab37b1c04a2afdb9d86f5a17822d3fa63727e76aa3d563e77d2bdcd8ebad",
        "Science/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon_Teacher.docx": "bc036875e5bd9e9ecb6e2f1f52d9dc0adc42f486d6bf04d246d02aa78dfbd763",
        "Science/Teaching_Packs/GROW/lessons/W7A/GROW_Science_Autumn1_W7A_The_Moon_Teacher.pdf": "64f052a34a5849381178f8a22dce9d865afb2b2602a0f805004e75149b450cc5",
        "Science/Teaching_Packs/GROW/lessons/W7A/START_HERE.txt": "447de6ad4347b097a16c09d40df429a4908e381b6ed9c36084c2e1cbdf6916a6",
        "Science/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon.pdf": "8a8946342e27252e71994094866df85a98eb52b18c2cc315c48737f7b0c6844f",
        "Science/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon.pptx": "cda721e5dd3c1799c89b8e00b79fe548759b144998b8f9ad2a8c244956ff0acf",
        "Science/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon_Pupil.docx": "8920525bc2020b7a8d6a2e3f935eb77415f8903f55f1a2f7636c49bd8fead9ee",
        "Science/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon_Pupil.pdf": "f11ce921052aa19e98af6741988dae84482cb5cc87caa15cb6d06740db7ba6a4",
        "Science/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon_Teacher.docx": "1d026a3de59ada343c814e3ed895368d5aa9292244ca569a66ba7a53f3cf126c",
        "Science/Teaching_Packs/GROW/lessons/W7B/GROW_Science_Autumn1_W7B_The_Moon_Teacher.pdf": "ff0c970316fa22f34c67fe22f8b0365b3bba423fef0aefb0e63cbc5a01070f19",
        "Science/Teaching_Packs/GROW/lessons/W7B/START_HERE.txt": "10d6ba34be76c3a7d82a346e83a65c86612ecd95505e63fc797a091bed945ee6",
        "Science/Teaching_Packs/index.html": "7cd0206831e3cb49209eb97471344a04220efb527914f27532deb20be93e8ce8",
        "Science/Teaching_Packs/packs.css": "70ca73b323e5cabf05b1f5f9f8107694cfcecf4ddf8043f342049ee4c797ce59",
        "tools/science_teaching_packs/BUILD_QA.json": "d5ee55a25c15ca86dbd6324b417c70d672e1d0c19a1fa6462f35cc620927a2ff",
        "tools/science_teaching_packs/BUILD_SOURCE_PROVENANCE.json": "a61bafa6e47477ba5f3d6428908aab7cdaca979a947ef71880160dfc0b8f09c6",
        "tools/science_teaching_packs/GROW_QA.json": "a8cdaa361414a3700c463ea40e0a159029db3fb803024e50b0eb39d082c6f364",
        "tools/science_teaching_packs/build_hub.py": "43459a1bff564fef2f66671ebcf0272a28301cb97de60f21a1c59385753be63e",
        "tools/science_teaching_packs/check_packs.py": "214e7fc9d67171e83d8f8605e44412e7f4b0ba071d568d3ce91804805959e56c",
        "Humanities/Teaching_Packs/HUM_00_SoW_and_Order/Humanities_SOW_Alignment.xlsx": "537350c7f0ba110ea90edf5039826c1a2858c04c54ec006c550ff143c09dec69",
        "Humanities/Teaching_Packs/HUM_00_SoW_and_Order/Humanities_Scheme_of_Work_2026-27.docx": "b078d01fb53a9f5d828b7f64d9ddb9d1a36daa681e8829d2a6d811abca664d11",
        "Humanities/Teaching_Packs/HUM_00_SoW_and_Order/Humanities_Scheme_of_Work_2026-27.html": "ac8f8d0a4188d147097a491b0db59efef16feb0c0f6c4fa8e13144bb8a53f69f",
        "Humanities/Teaching_Packs/HUM_00_SoW_and_Order/ORDER_HUM-D5.md": "688b3f5dcc60f6c0cd9c68e2cb2cb7c756ab834e9956c4b20b37982f749c88d4",
        "Humanities/Teaching_Packs/HUM_00_SoW_and_Order/RE_SOW_Alignment.xlsx": "b1ce56c551520fb360ea06e68c59c1642556337474526c38fb539a36296c2aa8",
        "Humanities/Teaching_Packs/HUM_00_SoW_and_Order/RE_Scheme_of_Work_Autumn_2026.docx": "3c2fe9ef4e4cd27361d76c4bb07234d4fe5eed8be40bcdbf1d1133b4632dd9a7",
        "Humanities/Teaching_Packs/HUM_00_SoW_and_Order/RE_Scheme_of_Work_Autumn_2026.html": "774b57b7f0bd57b7382a9f30da10d4d77b93953ff91d79d64548dd6a0fb906d9",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Captioned_Model.mp4": "8fa5f6ba3f6b7210d48a37277125eba44ff69843e7f6875177e6bc28eb6747bd",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Editable_Pack.docx": "ba4218c0c930bdad13c95b796c7279bc26f713d78a412349e5d47f6724cd5ecb",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Editable_Slides.pptx": "cfda24ab774a2a5c2a742afdef594663ce9a854aa8a12694fd0ff6db6326b987",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Knowledge_Organiser.html": "3e66b84d17cb11b3d7c7b315ef734d88c4edb94a94125e2707a16addbb2dc3db",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Knowledge_Organiser.pdf": "868102f22dd543cce610053626095a530320d26b88ea5e116e151cb3cef5dc28",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Lesson.html": "a5aa6d120a0063d9c6b29ab56277873c72a362e69f1b7d4e754179fed9fb1007",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Pupil_Resources.pdf": "29a00cfb5f9bec7af9c6bc891cb7245207f3a35ab261e47005530c4094c4c2a8",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W01/BUILD_A1_W01_Teacher_Notes.pdf": "37cf73d652b204e486350e7b65081175c8f463a04b4818640e7eb2e165442269",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Captioned_Model.mp4": "77173af6f427694cde81390ea21a8f1dba343a229c807a44009c87f93e5766b8",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Editable_Pack.docx": "91b3470b41b0a61f596d8abcde9a16cb5c1ece605bbbc34da64992ccaef0965e",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Editable_Slides.pptx": "c6bd63b7fdbc4ce2f83cc6ba78cf7848eeec0de3909f72bdbf9d94594bcf182d",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Knowledge_Organiser.html": "3b38e793985423f62c24448edee7ac73d6f0a98f14b874e28c1725abd64445c2",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Knowledge_Organiser.pdf": "a630484d37fc1d0c28e81f0c25868b52327db50c9c6de1e76debda7e5ca116a4",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Lesson.html": "b470ee45affe0d1294b24a80e24c1e65487ea1dc0c6ad24e241668eebf42c915",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Pupil_Resources.pdf": "3b4fe4f602a55759285a98f6f1e2d45d2d46f67215504ceb55a923d3bcbcfb32",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W02/BUILD_A1_W02_Teacher_Notes.pdf": "a82945dc967a871fc564d1672060dd0f281de51c41187b81117370894f662909",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Captioned_Model.mp4": "6799b383452024ffcf72332567d694ba979b6423141ce4b822aa3c3ea8ee63b2",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Editable_Pack.docx": "c2417f48f62cc82e1a455133168f31b4d8534a9b4f6a5066248943775b0d2eb7",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Editable_Slides.pptx": "de5a8a7af83b5c3010f41aad4d8d6216c572541e21cab8ba335d410e34081210",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Knowledge_Organiser.html": "ecbdf5a09d9680fb4a038d1be68d65646113642c37df6a9159eff7ece3ba69d4",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Knowledge_Organiser.pdf": "fb3a1002abc247a97de4ddebe31957e628da05dcacfc691a6c02b32e152c2ee3",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Lesson.html": "3d8abc157a0d8482270c6495750b3e92192008941afbd95cbee37b095f01c4ac",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Pupil_Resources.pdf": "c4e0b931a96350ea576d7558660347300103edd8f9470e8cbb8147abeb95bddd",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W03/BUILD_A1_W03_Teacher_Notes.pdf": "357c0c42f9bb9b1d7d3174b991adefea2bf7251e9d6c047e65fcead5e52a2e17",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Captioned_Model.mp4": "44ec3f4cf67a570d39f8dd10e0c221b60043c64e5ff9f8c703f73c899fa26c7f",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Editable_Pack.docx": "3cba20163d155b254250d5d04e561b7ab97ee1e0e62a7203ae03f74ec57fe07e",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Editable_Slides.pptx": "134e89022083818a9b01dcd3b117146b7c8fa955a4da049944abb00f9ab2a7c9",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Knowledge_Organiser.html": "66d4d4779b40c56879219034901ba86a72635c76beee76e4c207d3d57829cf2c",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Knowledge_Organiser.pdf": "482acde5fbfe07c7320ba7c797146a9e2df43835206a3109e52f1dc9d6f38aaa",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Lesson.html": "e4cab4290fafe1cf8ed76c62a5aa197aabbd307905f3ee09388774eb6d0c75b6",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Pupil_Resources.pdf": "06e25f3305baa497f8e390a15c8a774c9924ed6008692989c00f8c9f96d9a0c4",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W04/BUILD_A1_W04_Teacher_Notes.pdf": "e4679530a054a5c59f2ab9e4c69a8a7f4ec2150e0f859f61522278dc6dde0dbf",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Captioned_Model.mp4": "6e49af80f4a65eb96e7d44b3124a8623399746d06de9e553ba1d6ac1820964bd",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Editable_Pack.docx": "6e5062cfe442d1c1393305aeb97ca8cd9997b5b32a94cf53957cbb46b5f5d5de",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Editable_Slides.pptx": "2d7a311e7f7cc48154932ab3abc264be9c85a883784be06144c4815fad4e4eb4",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Knowledge_Organiser.html": "9302b4e790b814bfdb39beba6365b21fdbcb301326407c5233f90d0dfe792687",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Knowledge_Organiser.pdf": "711154c45a697db045eba0bdb1128dca890c14294c6fdde6f93c6ca2455a5781",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Lesson.html": "b383c1efb428fd153588e9851ea20640c44f22107691e74e37cffa2358e0c9e3",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Pupil_Resources.pdf": "e1714a396234df106f1d9a60863782eca89f778fbc9f5a3c2a3fadf82412525d",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W05/BUILD_A1_W05_Teacher_Notes.pdf": "db8a527ee6733276cfa13be6707bdf7fd51683bbbb308316cc6a17bb85fc04f4",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Captioned_Model.mp4": "729b94fed48c24c1d5782de86f959d2c36b8a242607a28f6527c3e422f6b633d",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Editable_Pack.docx": "c3e667ea40e836ca2348167405f2cbe77573aa67c7ae278d1983284426451204",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Editable_Slides.pptx": "e3d9ced1eb206eaa6f4e4f3a140b94b892232398e6e36f8e8496a7a263da19c6",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Knowledge_Organiser.html": "5aa307e49336ebae2446d4090a28b87467f840aaa49bbe4c410dc280585cee1f",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Knowledge_Organiser.pdf": "5603b0397bad083b453bf7394d6684e27e7706f0591cd9fd0f1179252507456e",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Lesson.html": "def46c2eab70d8e875be6031d5f8078aef9a2492f338dd4ecaa5d3f11a6418a7",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Pupil_Resources.pdf": "35c2f9bedd818e4cf1c8b84d9e4f0c51951dacf2e7de3a9c4b4186d381cb2091",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W06/BUILD_A1_W06_Teacher_Notes.pdf": "2e331beb3ad1e67d69e308c2df71ddce6ff3894e34a3a4933b80bd9e6b4f6473",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Captioned_Model.mp4": "f061462dea7135392eb4391312f9714d66c9a3198cabb7e5c321d3363df45309",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Editable_Pack.docx": "55a0f12a9595c1cf0612533bda9290b9031121ee2b11742c6354612730f6320a",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Editable_Slides.pptx": "5f24d03d2b3e0823255d066a643852e009ca98fc4f34f984844c97a4df3ffe41",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Knowledge_Organiser.html": "b3b5d61e5bacbb1669a0d2c2c6956a04874f162bb4d8ab94a236dcbcc15c099b",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Knowledge_Organiser.pdf": "db0bec4a5997afe173847d60aa5daccfa4814b2b61a7a6cbb5709bd980fe11a6",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Lesson.html": "e9766b69562f291c2e7881e9f67201ec00a613be9895643468143a411437b18f",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Pupil_Resources.pdf": "7f429dd60fe3f4929451c3252ce4c4b93290269d3e65681297762c1e47b00fd6",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/BUILD/Autumn_1/W07/BUILD_A1_W07_Teacher_Notes.pdf": "1528c4085a6a61470847fc7a9727ac41a322c6ce9638c39ac18326b0748dbf89",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/READ_ME.txt": "c6db9ea733f5a67a6f32d702dc54963f97d3c8e430f310cdbacb47c5440d4e07",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/arrival-change.svg": "c98d1fa61e8163d08305382a36516b63b3f3de65440e068ca491f92d8a169cc8",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/arrival-community.svg": "1de816a4040c040a8ec5c392b32035528497217d1a9f98e312930ea02a765d68",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/arrival-diversity.svg": "8c3b9c5a0600994a9352b2181952d9ab92c75b9e398e6845a97e1944cf18043a",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/arrival-fairness.svg": "529e890159203a9483e9c044181e331554e27a9a65106cb78c3e644bbb75a8c4",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/arrival-festival.svg": "1e1bb8c407d767b99f02cfb4e3cba2577938252c83e649639590d95875c01fca",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/arrival-peace.svg": "792b8cd954eb3b23bae480d4db84519e5c5a2b506442c3772cb90416ad4a8ae7",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/grid.svg": "be3436cb4c1b0fa7993e214c47407186a74ed353c4fe727069afaeee572d9bb8",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/local.svg": "e666bc5070d66bbb2b564685a768421508764e67b28dcce67b6be40cf0ba5e2e",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/objects.svg": "88aca060c6685e20fd47a6740f32c3012a15c48b12dc6bad91867ae040267eae",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/phones.svg": "ff17e352efd169723a534fe0a4c6846d716604929b506bb8afd0ffda0724928a",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/world-climate.svg": "c7eb4516343528f9851ab39a89c04abf8b26b260b85706314c567895ce2a7ad3",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/Editable_Visuals/world.svg": "26fc4e5b254e2611c6de7db61635e5da69beb764ff861655a1b7a682774079dc",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Captioned_Model.mp4": "27e372fb76c393618ad50c7646297a5de2634cf380b46008aaee24e1e7329b5c",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Editable_Pack.docx": "5ec25185c0ee34a51fed7578a22710382f729df4252044b243742d30b420f5a8",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Editable_Slides.pptx": "d21c1563074ca9e572bc8cdf9ca2b6605a5bcfefbaf3365ecff395c37287ef41",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Knowledge_Organiser.html": "40439b73feafd73e9fdb302f8c387a37943e6309a9061ac91a0e2819e0602668",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Knowledge_Organiser.pdf": "1eed83e326a7e7ed83b9c1cbe4c4a937cef65184d5a23d95112f82e9ad1f0707",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Lesson.html": "0592123d64d2f32b456ac79b59c33cece51a3a246cd3396f6f28cf43e796f966",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Pupil_Resources.pdf": "0b022e28a1ba0ca0300d3e49200efe20f795d3e0deea37e1719d46329df27b38",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W01/GROW_A1_W01_Teacher_Notes.pdf": "b56e65d0d91b9f5a71e6ee4437ba9a55648e6de5207ab0cab245080c6b6fa1c8",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Captioned_Model.mp4": "4e5fe08cdb62a84699773e85af089dbf0a82f20f09a695f3dba0dfc9e8f6d686",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Editable_Pack.docx": "3f7bd38532af9728ef28cbd469dbb654490e19cfcd797557665a8557f915da7c",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Editable_Slides.pptx": "718df0564cc04f829be3cf940f7c594d8e7653fde687acf6f4ad6649840a35b4",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Knowledge_Organiser.html": "9a480ac49e3b70537513f25994506bd53109ffa3a1af2ef436d33f0634ce46e4",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Knowledge_Organiser.pdf": "d12ec8182576ba80e6e8babf1d8f9294fcfad890030a1180bd585d13f9f034a7",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Lesson.html": "0e9115cfd1c97eabdd6719a2d6ca212eb9f523ca735078302d2e25673d99c0bf",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Pupil_Resources.pdf": "2b8d25a9b90bc688a30cee4a436fae9da5acadc6ea5be0e08208c17c61a34233",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W02/GROW_A1_W02_Teacher_Notes.pdf": "bc604fa8fdf64afc8d5171b5f6399052448ee019854c9a9c3f31499c09f82190",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Captioned_Model.mp4": "a01cec3a4122abf6d5a1538c4a045c9edd705cc71fdc61792136d1a0cb7eb9cc",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Editable_Pack.docx": "9698bd7c5259b45f52b91b0da0201ec42f68cdeef088e95ecd36d3df024709b5",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Editable_Slides.pptx": "1004155fc1fe26181287f11b2d7256e54cf8c9146a9194dfe167d374998f980a",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Knowledge_Organiser.html": "f0562ccdc634da0a73a0103d80cef7980f68cd2e03443630f23f2717e1a200ec",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Knowledge_Organiser.pdf": "5bea657e4fc355189eab0117af54fa94667cf1fb285c902719ece4dfbb136c32",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Lesson.html": "0e0e2826667768d97a0e341f5fcf67be25ebd930a1afc9b013940ad09740d35a",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Pupil_Resources.pdf": "74b89a85ae290c7a92aaa294b63cc11d95ad910104736514f0b5e1d0ed06e478",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W03/GROW_A1_W03_Teacher_Notes.pdf": "ca45b2898bbdbf042eb133888c55024f773f45d6ab8eac0776e3b9fd7f811853",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Captioned_Model.mp4": "f8508413835f4f6b7da9560df5a34be4576fd28103321fa87dde8e02548f24b8",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Editable_Pack.docx": "8e59d4a336e345822969c7d278507d0b87d82258f19a2f0e8d0cb69b245d2cc9",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Editable_Slides.pptx": "f91ce4ef835e9d92a9568a4f461c4bf0488eb79c9eedd01530da603c731d3f9d",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Knowledge_Organiser.html": "5e07a502976e39e47f86b48d32a83c578670c2da5f4096571d1931f97f03fd08",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Knowledge_Organiser.pdf": "756a7d988c9b4557214e294ebfe609350faa3574b608b8e1acf54406a89cce60",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Lesson.html": "827586049083e26f9cf0766a714503f9811328364755c71ff6095a2b56160889",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Pupil_Resources.pdf": "dc0063c6a349deb1e5fdf7334212d3fbbc7599947f5c6df7cc5b5820c1f3aaf1",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W04/GROW_A1_W04_Teacher_Notes.pdf": "484edbedd4f36b652e9edbb678392653226c76dcf7ad33d8d6e2cb3fa782c617",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Captioned_Model.mp4": "d7901902a1df8f0427406ef698a7fc00080139c11f866935cba3b323d8e2f4e7",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Editable_Pack.docx": "43deca2b5d9cb14440ef2766e061f3e290ffc73771ba31e551afc5305a30f71f",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Editable_Slides.pptx": "563437d8138ef940fd094ea27502eab86ec37223e5bfa418b79c806b1e6ac4b8",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Knowledge_Organiser.html": "0048c8d0598c8eacdab502d66b52aea2d2e8ba8b9608ad020cb88e3c8047bea3",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Knowledge_Organiser.pdf": "54c070b18901980996718efa64cf0a26a638cf68bc9008d58bedf76d805b4fe3",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Lesson.html": "5afbf764a5ed15a8d4676cfc5c6b44738ccf1faf04f2d070f46e327f59eb1df9",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Pupil_Resources.pdf": "1629c9c31a3fdc5fb126a6f5b2d6a0a6503a358ae73ac5a426e978eb048eb0aa",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W05/GROW_A1_W05_Teacher_Notes.pdf": "ad9fc3e249146af8f50a2dd68680aa097b7e50be02f5aa62d036e01e467dd6dd",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Captioned_Model.mp4": "48d1104447ee11372b61673d71ba3057d4495c125c0f9b54411f0e729fcec5f2",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Editable_Pack.docx": "21eee128ab8ecc639e32f0d068c1cd5ebf532d11c80ed0a10aa1414e0cf76bbe",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Editable_Slides.pptx": "eada084af4c4f1c5e337f1121487d10165a13802a2f4465f5d4c06978f722d92",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Knowledge_Organiser.html": "3ca5600ac5639520240bb60edc07715d7157b132056173dc971d829cc629d52b",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Knowledge_Organiser.pdf": "bed02b4dc5cc31134965d6ae14f33463ce27f98820789306f266333b726cf5d8",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Lesson.html": "5a14e462a87c9a741f14f709efdf6d0bb4974358e5b86812883a91e0387c8e39",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Pupil_Resources.pdf": "05a3df175825afcbee8c0d2b0b930f73202ed48cfa85e2cf446926879e890231",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W06/GROW_A1_W06_Teacher_Notes.pdf": "6cd6af07cc07ec35202709612498fd108441519f91fac5459294e7468c3dbfec",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Captioned_Model.mp4": "1bca4e415328a017f3494bf4d4b7db779544b01173cc07e07562bd5d19b34464",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Editable_Pack.docx": "55518db545be873b113a766f5f2184b3d75e8f092e2533d7c6e4c980c3c26965",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Editable_Slides.pptx": "d852d22e6cc2788dca4d284b4bd31122cb60f1d6eccb382014746da0fb1add60",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Knowledge_Organiser.html": "decc5a8f6a0710d77bf59a9f545e207a29caa1f87442af93b6299656c2d6787d",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Knowledge_Organiser.pdf": "a15d9bc8ef7b7b8e3c144df48337926e3d3965b4a15d70d0055ef15777d41a17",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Lesson.html": "f168ce4cd63b189ff6ba819cbaf744975670ae1a54230bb6b147f87b8325a7bc",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Pupil_Resources.pdf": "95731f0c7778302038af6829e4f4f843fa33d9093fbd78cc09b1a24b6e316e7d",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/GROW/Autumn_1/W07/GROW_A1_W07_Teacher_Notes.pdf": "c0c7129f507d9ae462fdde108823ade704edb5d435c4c1919d408843647d1380",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/MANIFEST.json": "6cd175cc1cc25fcc69dc579e7b1750545d7fcb1cac849196ca72134b8708b766",
        "Humanities/Teaching_Packs/HUM_Autumn_1_BUILD_GROW_Fallback/READ_ME_FALLBACK.txt": "be8efb425b2248d5b755d816383d8854e0fed26d99b108bbf898b5f68d96695b",
        "Humanities/Teaching_Packs/HUM_Autumn_1_LAUNCH_Reviewed/SHA256SUMS.txt": "480587877c978b6792d8107131157de7264cfc8b38743ae3eba36abf36cc66c7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/SHA256SUMS.txt": "e02a5e9c69a4f89c89db97f9cfc021f142ca391d7ea3ed063c597d9090c934db",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/SHA256SUMS.txt": "2b4b67ace56960017c5f7128de2489a9eb78187c3d62b773cf343c0bdf6aac0d",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/SHA256SUMS.txt": "f274ad67757070e6417a75b44785903f6577398bb59fa455012c586ed5f206b5",
        "Humanities/Teaching_Packs/HUM_Spring_1_BUILD_GROW_Reviewed/SHA256SUMS.txt": "2f6c77dc0572c988281792b3c0f5285fc03d802bfe28033ee6a9c4ae7e61912d",
        "Humanities/Teaching_Packs/HUM_Spring_1_LAUNCH_Reviewed/SHA256SUMS.txt": "bc16f31e639bf89b0c4bc14ae07439f5aacf0a646d7f4639a6d66e51bce86f9e",
        "Humanities/Teaching_Packs/HUM_Spring_2_BUILD_GROW_Reviewed/SHA256SUMS.txt": "423cf78757820f83ea54bdb970d528649179a719d9fd75a3b059075dbaaeade0",
        "Humanities/Teaching_Packs/HUM_Spring_2_LAUNCH_Reviewed/SHA256SUMS.txt": "50cb5d58839fc4942693a01850a137497a4361bb467a4ee3b658d86793ac74ca",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/SHA256SUMS.txt": "ccc10683c49aaaf9fc3e57b34f6e1a90d77ef3eeb72c9bd716fcc40a8cf00cd9",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/SHA256SUMS.txt": "871fa30a1d1355372c39218f3794a082a8823a5003fcde28c2683ccf5ce3c343",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/SHA256SUMS.txt": "1aef26713d7bb00458ed20e3b76c5ccecdf3ba703786cfef073b7893c3a1d913",
        ".github/workflows/cross-estate-on-content.yml": "e323c85b033b82455fa950e2be395868c279a929ccb6b94981fcb8f3258ae72c",
        "tools/humanities_resources/PUBLIC_LABEL_CHANGES.json": "1054940b3c20ab2c084965a4ae11c8827867267e119df6d8e65f717d7e22adf5",
        "Humanities/David_Cover_Autumn1_W3-W7/BH_W3.html": "3cb06cdadc3af0b852e54192a10203295be12c6139601e98e86c9496478a79f0",
        "Humanities/David_Cover_Autumn1_W3-W7/BH_W4.html": "ad5f0adbe53b57189e3c9958ec5e79d3f9b91018e6fc85001140141284e5c387",
        "Humanities/David_Cover_Autumn1_W3-W7/BH_W5.html": "c67cf1fbb4e37c3f6bd9f7e6f69e56eeff26150f2afa8447d461a5684dda2665",
        "Humanities/David_Cover_Autumn1_W3-W7/BH_W6.html": "6e13cc25bcf3918309406ec1269b0765117181e90007306d76e115d585319717",
        "Humanities/David_Cover_Autumn1_W3-W7/BH_W7.html": "b8d346263c2a4e3fad004273c2eb37ae02996ae6566eb1d02605aad203aa07d5",
        "Humanities/David_Cover_Autumn1_W3-W7/BR_W3.html": "68433d21e8b4c04a9c38b34b89afd6162fefcbae3b90ced8779b01341f5b7948",
        "Humanities/David_Cover_Autumn1_W3-W7/BR_W4.html": "48856c5185b28621ca9c7a3c4d668fd0402d69039351516753dae80c3b393e65",
        "Humanities/David_Cover_Autumn1_W3-W7/BR_W5.html": "7311ca67b4a83a5356149ed7b7e96c19ef0742c9b6e1fd736a4eefbe97f33796",
        "Humanities/David_Cover_Autumn1_W3-W7/BR_W6.html": "4547ff74bdc25dd5f3de163a57fabf0cdb062ab922b5be13e6a76e4e31f6ac7f",
        "Humanities/David_Cover_Autumn1_W3-W7/BR_W7.html": "7575fb9d4d8e28ca487c89a91dd70b556dff94e67a8723b37b63d06d363c6537",
        "Humanities/David_Cover_Autumn1_W3-W7/GH_W3.html": "8a28b949bd4a6c4e2a7965e5edc07bc20454df22ac0ad4fa6d94950119286bc7",
        "Humanities/David_Cover_Autumn1_W3-W7/GH_W4.html": "f84c91ca65ca730620172ca70b551061bbe568017d6815b2b12df9be0e4dad55",
        "Humanities/David_Cover_Autumn1_W3-W7/GH_W5.html": "d9a0680fa3928b1d7d23333c001bc7a3d70d46bea9612ade3b9588b97ba4bed5",
        "Humanities/David_Cover_Autumn1_W3-W7/GH_W6.html": "5119f8b0b33aeb3d225be4af3c883a88476d62448d2ee5ad5cfa161b231f96d7",
        "Humanities/David_Cover_Autumn1_W3-W7/GH_W7.html": "2839c19f411983273d84b098a6d1db10f30bdd7ac975b83ded2061512157d347",
        "Humanities/David_Cover_Autumn1_W3-W7/GR_W3.html": "df6893b26d5dad94d001e20bd4cd2bddd0dc8861b879fa16fcdf9546f094d1d7",
        "Humanities/David_Cover_Autumn1_W3-W7/GR_W4.html": "9c1bd091b3d792bb8f765c8ef8ab781c46952423d85d2dc7f428d7d66afc7476",
        "Humanities/David_Cover_Autumn1_W3-W7/GR_W5.html": "b750830cc0cb162ab721d4357a882351b7c82c36ba5a5bbdb09da87004cbb19d",
        "Humanities/David_Cover_Autumn1_W3-W7/GR_W6.html": "609c398050b997a8e8f84dcd38e2ae3a4e8e46f444b927f78a7d55de314d5686",
        "Humanities/David_Cover_Autumn1_W3-W7/GR_W7.html": "6c196a0bd2db17728722d456a1af310f17e8220dcd6578bd9b35643aea6fb3f3",
        "Humanities/David_Cover_Autumn1_W3-W7/LH_W3.html": "95856d0bd41abe02aca8a405718ca4b413e7c797673ff5beffeca13b87abe691",
        "Humanities/David_Cover_Autumn1_W3-W7/LH_W4.html": "51ac458f002341ba2610fd5dbdfb3beaec961606c57f953c48b7469baf8f6d73",
        "Humanities/David_Cover_Autumn1_W3-W7/LH_W5.html": "63ed872c7b5534d8d1c4ffde723fdb7742789ae7bef705b2b9cfd3eb2a34993d",
        "Humanities/David_Cover_Autumn1_W3-W7/LH_W6.html": "6ea47b86c65a116d95ce2376b16dfd9fe773c6290fcded2efa072db19be0dd22",
        "Humanities/David_Cover_Autumn1_W3-W7/LH_W7.html": "33ac63f9fbcf9c36d67658e87614f6e1e904de45aa3dc5128ab7fed94579f803",
        "Science/Teaching_Packs/BUILD/SOURCE_MAPPING.json": "7e30e48fc01940656077ed1932c3132c425ddca908c73db6f0b409b5e8664988",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3-W7_DOCX_Collection.zip": "2482706e4f9c7e192287acfd02e7c09381597a1a9fc772c9d39fe630eba5a3aa",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3-W7_PDF_Collection.zip": "b3116412bb38368b96c0236e2b41902deb76e96461f1ca1c3fb134d878f842f0",
        "Science/Teaching_Packs/GROW/downloads/GROW_Science_Autumn1_W3-W7_PPTX_Collection.zip": "592f59c2ccae4f9531af5296eb30064c8fee92c44ba2b896db8038cf2a93dce8",
        "Science/Teaching_Packs/LAUNCH/DOWNLOAD_INDEX.json": "e2907a8f829cde9c8ab4b8f012cd49ce89daac86ee09b2b3554da07bb0aa4d89",
        "Science/Teaching_Packs/LAUNCH/Pupil_Worksheets.pdf": "40b4561e417afebf2cae6a5eae1ade45859a9dd462bf69e8dd4135c836d3f7bc",
        "Science/Teaching_Packs/LAUNCH/SOURCE_MANIFEST.json": "3bbd898b418638248906d177138ec8bf0232753814f07a837ee50b6b08f3b9a5",
        "Science/Teaching_Packs/LAUNCH/START_HERE.txt": "2b7b55ab005abea12229d54ef4f8f5389cd6c0714078284537844e62b69ac3e0",
        "Science/Teaching_Packs/LAUNCH/Teacher_Guide_And_Answers.docx": "407a1c8c72112dded2dc9c89d3a73c6b5834cabcb743d8bd6f436c412ef1656e",
        "Science/Teaching_Packs/LAUNCH/Teacher_Guide_And_Answers.pdf": "f359887eabd99b868f1741b65ddc0a16b0eb2d5909d127f166926aa877657fb2",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L1_Microscopy.pdf": "411edd8b048c842593c1121f8bc834e5317d37a7a14e63750eba2b9b37429f88",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L1_Microscopy.pptx": "a68b061201d1fe625fdc94bfee4fa2fdd0cc223557c24a959999cac21c195d50",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L1_Worksheet.docx": "578c8ea466beaef599c1d7f903a47356548b775352993f87ac73d714a97d8b86",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L1_Worksheet.pdf": "5a19b3f2ca31014d262fed5fa07132b1fb13b28faa10c64b896eaee3f12a6450",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L1_depth.pdf": "005e8b95cb519d392b039cfd83aad453f4658b6e8e8aa64033a8b3bf8d92f301",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L1_standard.pdf": "82063ab1b999b329d78a05d9cb26080946bbe2a7dcdb8e5173e6ccc79a9f8496",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L1_supported.pdf": "cc8711966739a08fcffd0a83101a6447b3df3b0f467e97a758716ea20c82b2c1",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L2_Magnification.pdf": "26f6f2663f3a38537d233a9c94861408c0a23ab01770ec64be8cb0c0b8c811ff",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L2_Magnification.pptx": "1fb4bd94df2a29ab0af72db475b8929bdb22aaa9cce4ee4a5bba89175f897286",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L2_Worksheet.docx": "910725485910dc58e2b030f28b0610e31a7c4b2891422ae67816799ca544e710",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L2_Worksheet.pdf": "1f619b4d341c9a2a339fbace64d0ff0ad7511bc3fd29ef07efc9f56f58eb6b3e",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L2_depth.pdf": "cb100881ed59102fccd6ffefb85fbfbb984d20658249cffde5f3f0ad1bb832aa",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L2_standard.pdf": "9ce05f7ee4e095294ea461fdd5f838ef4ef9f0783842898d36468e2f7aada8ac",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L2_supported.pdf": "7b56ab3c793ac029fd751fd279e542e74fa42f9a01bf99fac3708177b38559ed",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L3_Scale_Bars.pdf": "9acb60d205a4e7a4c83a146b7c2a4547d540e9eb5dc6cbccca7e70e0e55f830a",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L3_Scale_Bars.pptx": "ebf8d69debb79a17020e22a0b234ad5300319bd9d149e64f2996526db507a441",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L3_Worksheet.docx": "77497a489ddc7c0ff48ac4a208832e28b6022f20de6e1ae225d59b27c6d78d92",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L3_Worksheet.pdf": "ffec01cd95a2ef8d9e1aa87d8b5e07f99d938b5bc7a6858c357388374f3bac8e",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L3_depth.pdf": "53184ecb48997a1e102ad0903760a103522c6adaeb52b1c112759b9c2209e435",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L3_standard.pdf": "ac051b2f92d89fdf77253f8edf3c4429fa89d398d40d0ee2606cf0f02d22b260",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3L3_supported.pdf": "e0e52afc7e76fabaf33ef82f3704f1d0eec08bd0fb4097c72bce38468f4aaed0",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3_Weekly_Plan.docx": "0ff2731c3812884f5662f488a0eedd24f4e9689a9a58800125416d0666c66ecb",
        "Science/Teaching_Packs/LAUNCH/Week_3/W3_Weekly_Plan.pdf": "b2827f23371b7874d89245a7dd75e410cb7e9f45beb43ee564988a7d9a000de5",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L1_Diffusion.pdf": "0641dbde7d35b8d98332c864eb419b7f0d18610b79e96c2439c5cd741803f6ec",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L1_Diffusion.pptx": "a61a92cb908959617c5e62440bdf18c8fce41a5a5c91eb348086d4fc687b32fe",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L1_Worksheet.docx": "587d0c554d8f496b13bfa4f35cd91e4fc6e5e9618059b73cf2a5a9131e2ada75",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L1_Worksheet.pdf": "9ce702ccc29bfb3eecf02e6f73df2de5cb96a6e695962e79fb49c8ea90ce414e",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L1_depth.pdf": "e4414be692a08830b502d4565df44f3e92a3f01f0acfa014eb04d4da3638b7d7",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L1_standard.pdf": "1559958acc64bc63d89be2aad107ecbfcd9790ac2197999e8f7afa841ca18938",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L1_supported.pdf": "24b69c4457b50caa801d8f4ab70a2a7ab09a94e6332d9f933fb26b9a0b39452d",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L2_Gas_Exchange.pdf": "b3652f52606f1fc860735976363e37b5224327692d32a600e7acdc56ab62359a",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L2_Gas_Exchange.pptx": "6cb8a1c32ebbe00111b4ba7187f992a89d367864d5f80bd518525016056cb66a",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L2_Worksheet.docx": "ce22594dac00e13df8b079f3c16f0abfe44f2c821d85162206eddcb454291082",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L2_Worksheet.pdf": "52574a3978cdc979e213f4f6f895fe8b375514b306de19844486297190b972cd",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L2_depth.pdf": "e47ff950834a3e008590d3e3aacd023035099c9a690478937ee898f27230ceed",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L2_standard.pdf": "00a824d2d52417a7fc1add1376937a9a55a6cae32c160f00491997044e41649c",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L2_supported.pdf": "bb56237271dcaf6c0ea670f2f1d35b31299d4b07afbd02b18e21b2e3dc4513e7",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L3_Diffusion_Evidence.pdf": "61ae806cd59bfd578a9a231bf59bb85082718dc8b509b0e55eecc95a5679478c",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L3_Diffusion_Evidence.pptx": "4eee78c7dc875371151c4a2309b1539c894a04e63d8b635676c825ca401f8834",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L3_Worksheet.docx": "f98364c37342b2c7e1d8852b3e9480c56608087c553509d190c246264e3bd55c",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L3_Worksheet.pdf": "7c788728303715a6d3801eea275715dc127bbbda1060fdb5a3059ec0fa3f6ef1",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L3_depth.pdf": "8110273a50fa1e3ee30af9634015dd60910d01c274f2747dad22de7e1c43571f",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L3_standard.pdf": "1bbcbea02fd6a38295d7cbeb4e750cf90794a1376ef38a0d8f46e64419f7facd",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4L3_supported.pdf": "a1eb3480ff04ec86f2e2bba418f200fd29c831f419efb28ce8caa1fa0e39b8ca",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4_Weekly_Plan.docx": "8908c707b8a70a5ec32231750fd2997c72803de0be7c140266753597cce870ee",
        "Science/Teaching_Packs/LAUNCH/Week_4/W4_Weekly_Plan.pdf": "b51e3e4d7842e2eb79d1d68746bdae2815890a729c2392f746425eb7fbc8d4a1",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L1_Osmosis.pdf": "c480c3dded76690daf3a246be25c46638de5591b2c376e42fb19d9f4c7016558",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L1_Osmosis.pptx": "710ae7a5ab374e599d710279e21984619f6f2acd958ff06c4365080fa8467f32",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L1_Worksheet.docx": "9a46502209db857d1ef7cb407c65e5cb0fde6877ce225f55bb88b3dbe4bdb81b",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L1_Worksheet.pdf": "533ffbba83bc6a18cb44a9af3723e727af41c73b0dc7becfd8a4684ecec2f769",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L1_depth.pdf": "153c07f6d4174b9ced5537a34cc39e0129dc9fca4ce86f30710d5fe0e61abebc",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L1_standard.pdf": "c450cb8ca0c00a54c088790805d1629f6225fafa7f20f2ed85e231980e12b23a",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L1_supported.pdf": "ddbdaab0499efb7e0407d7085c8768c032d130b0e0945efc28f423113f955773",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L2_Osmosis_Investigation.pdf": "45f9117690a893731d768d95778a635d7c6b6d324b803c383e4020dcf14f879a",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L2_Osmosis_Investigation.pptx": "dfb1a60077b8bc34cc5737c1f4551a18f20b65d3b42acd3161abdac911dc4735",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L2_Worksheet.docx": "78f94b01728e94f2edc93bf884018c84a411e71f9db8b7035d02159287895a2e",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L2_Worksheet.pdf": "e96884229cdc695046cb0fe6960404e4407da72d0d489cd3fe43e3613e59af53",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L2_depth.pdf": "a9127c50279abc4874aefdbd6e78d02da91aa0faf5d861820173558a263505f9",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L2_standard.pdf": "6c80296e85da6fe98231d1ed4cdaa56191c6ec1962ccf247badc85186591df01",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L2_supported.pdf": "bd98b8c86d0dbd4bf75e2c19c20413250bbac9f976bdaa42698b69cab230134a",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L3_Osmosis_Data.pdf": "5ff00817f0e9629d974c4a260116044f986978960a46554bb6d32f3798dfd980",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L3_Osmosis_Data.pptx": "59bfe0fa66da6413fad107598fd5eab556324da67068d343d7024ed9fd96c4d6",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L3_Worksheet.docx": "a88ec8ac1d32332cca655187aa319c387a384da783f4f8a5328775bad6ab1b48",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L3_Worksheet.pdf": "2f45e3db7c25cb4be482c47a3ea674baab297ab8fac06530152dc710050eb6a8",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L3_depth.pdf": "11d54d8a1c7b08056ee672e0c393b4c423d9e487cc473ef5b83888fe54a0e1b7",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L3_standard.pdf": "29abc6f371bb8ea82846b3a8a8e8eb3f5b4d2cd641eacf4c91c3cfc298486857",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5L3_supported.pdf": "984c6ecf259beafe41c77e60af240495f6f32715dd1c2c7ece6121888bfa0e10",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5_Weekly_Plan.docx": "dc6175157f80ed060f6dc829204758b6ca079fc3a7d0156648a495a31bf77a11",
        "Science/Teaching_Packs/LAUNCH/Week_5/W5_Weekly_Plan.pdf": "9d9f05619d7368418e717af6dda8158786f025fa217639090886a2f0ced4126b",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L1_Active_Transport.pdf": "a877671f4bce8b6ec20dbdffc31005d7a8913420a21e4a50521bf46095c56ab0",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L1_Active_Transport.pptx": "6fc2f87c44239ffb9b6e84a692c27f463bee58ef6e88eba54dfd19009b6646f3",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L1_Worksheet.docx": "a0db709628b013be34cb431640a4d6353c08899275e69c7048ee9eb5906556e1",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L1_Worksheet.pdf": "dbb36ee694301b2454c5d25784899e39f4c8645bb24a4323611c118da2ff3091",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L1_depth.pdf": "0d645d463c3440e8f162066073976948d17113c3c04b9a1389cc9936e352e434",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L1_standard.pdf": "3cec9853fcbe51f60e2fc49d51ef01196b9dbc7255813485666bedd8c64b3730",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L1_supported.pdf": "e31ae68717e48acb5d1a49c466a319aa4c4d9e896ea2ada6072f94123d68ba19",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L2_Root_Hairs_And_Gut.pdf": "8e48afe3ccca498f510b45c3a0cbecb63c4ba943a425294a00610b8f0bc82a49",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L2_Root_Hairs_And_Gut.pptx": "7127955eb2c1e2f38541286be5d238ad9c26ba8c35dbd1cc3c3ee27aecc71592",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L2_Worksheet.docx": "ca371afe8188dea2a79b4f8d01dc6d443382395bb0f753bc52ea0f34753a4f85",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L2_Worksheet.pdf": "e2ae0ea71b98613bfa02e4ebb00931c3cf00ebd0ab1533e9dd9c0be49a254a4a",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L2_depth.pdf": "46dc11aeeed02b38f81b2deee28c89adf809c261a0828d65d0772ff80f3ec0d9",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L2_standard.pdf": "4b18f94880cd466e663925c6b601697d3d47c68f63b21aeb98efe5581a9c822d",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L2_supported.pdf": "2e454bb29b5debe12fa5dfc89951bf473822ae664cf1f96e1f7706e78832fde6",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L3_Compare_Transport.pdf": "7ab6dcc9e5b8b8174eb9c9fc48a384e1d6d518b81562f0fde795976b998b02eb",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L3_Compare_Transport.pptx": "5c36b70c325b6102025f253d2664d1589ce5820758006dbb50e634bd8a1bcdae",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L3_Worksheet.docx": "ada63ec53ae3feada8f75a624f3a1e4c7b20dc22d02866c53fedaa6033cedbf1",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L3_Worksheet.pdf": "67908331e90ad45815a5dfab1391fd1f58e1b21636bf9ee50c85a4571b0f20d4",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L3_depth.pdf": "dea895c6bad53c4060b1bc15184a21631285451d8a820a0a7ee4903a13b386a3",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L3_standard.pdf": "28b4f3cab0a6dbfce5d2e72c7e63be6c983a4a65ec5b8b4b8e93221174e2ff57",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6L3_supported.pdf": "71e97b4a48ae5192af0075a4b0be4fad52d31f1432e78a5c559527179be25b29",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6_Weekly_Plan.docx": "b6b26aafedca7a02a28881ab8c00e9a07a333e5cec4c7aa21a648ab6545e098a",
        "Science/Teaching_Packs/LAUNCH/Week_6/W6_Weekly_Plan.pdf": "0d00dc615fd0dd0de39caaf8b3075a720662d2ea565850fef0ad56fa2ae6f707",
        "Science/Teaching_Packs/LAUNCH/Week_7/LAUNCH_Science_Assessment.docx": "504dbb695495660c2141b79f01e7cc71457a9d4659595ff55c8b610cbc7c110e",
        "Science/Teaching_Packs/LAUNCH/Week_7/LAUNCH_Science_Assessment.pdf": "eea71d1a3b9a105542fa566a1c39adb0cdba3fd138d84b64ff25985275838af9",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L1_Review.pdf": "e2899621b752d69f1cf73da996cf698e7875b041da0bc1663686740578c0ba1c",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L1_Review.pptx": "a820db909139c864f44133b2f461acc0fc49b3f3eb77f3c59b5c3f579e73dcb8",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L1_Worksheet.docx": "25d14dff4c4f6e4ab56609b9af1e67597270a970e85151db273ffe98f2631aea",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L1_Worksheet.pdf": "7b307bef4e082bfdf7225530b121095810480ce52761068a21843cc7c412c096",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L1_depth.pdf": "7427ebdc876c5bf9ba137ee6b2b30f44c6e3cb791e9c70900bae83ceb980c0c1",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L1_standard.pdf": "f6cbc794175f8c62cfa3098b1afa6374fde6d94997dbc416df5a4dd5dceb7008",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L1_supported.pdf": "633dbf208b8c32c18e5985bd5e09c8e29234ce1533c584fe0a0b073d8fa7513c",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L2_Command_Words.pdf": "61617770ba69ea6d85fe37533191878c61d54aeb526f8e9053daebac0c415531",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L2_Command_Words.pptx": "305f7a0940b08a66a5963acc5efb07827c256552bdaa6158f0c0ce966b88e250",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L2_Worksheet.docx": "7c25d67a7c637c567f447aa655fd272ff6f1efe7dcdcd54c7dc40c77e1e1f887",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L2_Worksheet.pdf": "2742657e67b01f9fda32b27ff1704239f0e45fc5f4d445561dca3f041d37d2b0",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L2_depth.pdf": "59eca019f32fd0dc59f1cd9b153a4a4d337d419bf970194217edb58bd5ad754f",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L2_standard.pdf": "895a72d288f1041ea15c9ee7d91713cae7aa8dcdb7362c4ef6f7467964afccc7",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L2_supported.pdf": "be095c3778f0bde0f3f36a41cef54cdd7b3a720c44ba1eca17ace9007c297723",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L3_Assessment_And_Response.pdf": "d01342b1d3f5a7950c5459591199fce745083f4cdaf99e4f292379e9a1cf03b9",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L3_Assessment_And_Response.pptx": "6097b44ad6a0321335fac1bb72c3de07f0ada203431c36cf40156097fd7297cb",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L3_Worksheet.docx": "9d7b617f9ab63a6f7dbdf05ae27e7f089a907f88d41889fcf441140af86fb101",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L3_Worksheet.pdf": "0343a92d5d13872a021e14e334086f513e9f645ca14a9059e381d13e50b92acc",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L3_depth.pdf": "177602c03c56f61bbd03cd4b537d21c4c22dce607e85c322954b675490195c42",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L3_standard.pdf": "1499987c069be0d685c72ddfe9e3b5e021df258002a52244a470e4c3e7dc7dd9",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7L3_supported.pdf": "c5ee897b1129bb86eb0813c08af7df11bf4f42e4b70f5b79c7ccc1402ee0f770",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7_Weekly_Plan.docx": "499928095b9cd9aaba5f0b09a40d101ea40f98d41b574ca0f1fc410a50688605",
        "Science/Teaching_Packs/LAUNCH/Week_7/W7_Weekly_Plan.pdf": "4ec297f090a8d5983b03a7ca23b866ef0e166c0f603f0963fa7c7dab075dbc35",
        "Science/Teaching_Packs/LAUNCH/Weekly_Plans.pdf": "5bfbdf746dd1b83c93ca12c9c5f10f5f8051be30ed4efc1344caa49cac578dc9",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3-W7_Complete_Pack.zip": "2c4e45a5cb2dfeddab2eab0894250a9bb23e11f8558a7a1b41181ab861de6829",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3L1_Lesson_Pack.zip": "2635ad9fcb128c7e100f3f0270c72394809dc2a4e6d5a1a484ef09b7fd50be4f",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3L2_Lesson_Pack.zip": "51b8d2a4e8e79ffc71eea2aa0073ee7c7d8ed738a88963f6da8730e8b01b2efa",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3L3_Lesson_Pack.zip": "ff7a9c6d7175db2be41b96bb5df27ec9dfce144ea7fda1f9e2eb998bec89b997",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3_Teaching_Pack.zip": "33d73973583e1a66e28610c7081801a697f562889d91e330290105de06d97df7",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W4L1_Lesson_Pack.zip": "681efca90ccd4fe7143578e9771c905f0f90cf2e7688c6ac5ff0ad94014e24bf",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W4L2_Lesson_Pack.zip": "66f6e1a5c82175bcbeb6c103dda4b166067ddedefe75a48c1c9e729ee04244f2",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W4L3_Lesson_Pack.zip": "af858882f4eb585529e7a96934c5d874c52d6564e3cf6c6ca3023d6c484abf53",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W4_Teaching_Pack.zip": "f83dfca777feae79489aeb521135864304f62d1ff38bc4978659af316e7d00c5",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W5L1_Lesson_Pack.zip": "f9d699fed947c921f5fe17cf5a858b7b7de3436ef6f7ec3a88fcd0b0b8b3569f",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W5L2_Lesson_Pack.zip": "88f02bb5be1377604ac31ca5249925790f74fa255ac4c3ccc9cdfd76f945fd12",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W5L3_Lesson_Pack.zip": "1a9dcea48a1aac5e576148f0d908e2f2a5823f1e1747860019a0c8f20750f3a5",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W5_Teaching_Pack.zip": "339d9b737ef1b0023fe12803e83bd4d41c196afccc0c52344f6b83fca8f4a1b7",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W6L1_Lesson_Pack.zip": "0f62f3d193e36443328ccf553b15bba3f0e75ddc8f76b2a72f8333035d317fcc",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W6L2_Lesson_Pack.zip": "58a424aacd37371cfe42911a82d08e36c674aa36b700811961648a43d2c13de9",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W6L3_Lesson_Pack.zip": "71dc842201fd627ae1766ede91dba65acf183514291fbafcc49cf3717f06aa93",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W6_Teaching_Pack.zip": "dd36acf680333cc56b54bf6dafba51c6eb00a85801a6333cb9c6613c5702ba12",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W7L1_Lesson_Pack.zip": "db6a470dc5e60cf36f75bff48167943f4e5421a681927ce424928db27ad822ed",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W7L2_Lesson_Pack.zip": "164e9da79876bc77853614b679b45597894b8c25802b67fe8dfda02ff781e98f",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W7L3_Lesson_Pack.zip": "28327f9ecf4367a3153a16d04e496433645c16a59bc55f46d2646f7ba9f9d985",
        "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W7_Teaching_Pack.zip": "0f97ddebf0447024b936ed8c5b2053afcd8578911f64e1a2e1c560d2c3db1ad6",
        "tools/science_teaching_packs/refresh_packs.py": "09e86848edaf07d4064a2c0232e9078b6e33223b9c7d1b7b5c226e8dc4fbf29f",
        "Science/Teaching_Packs/GROW/Image_Credits.docx": "b7fe4b107695458bd8138170b0c98d14adddfe156871bd228db798790dbf3786",
        "Science/Teaching_Packs/GROW/Image_Credits.pdf": "651dcd9f749c6cfb5ffccd73eb9ffb14a57f8ff8a8860f348969b34114396f86",
        "tools/science_teaching_packs/check_hub_browser.cjs": "9323d0a64514970426bf30c8b281f99d100a8849d087d8f4354c78f3fe5022f4",
        "tools/science_teaching_packs/VISUAL_REFRESH_QA.json": "3ce5b90abaf89fc5a2a4085791bb16e09667545cf489a985c1c525bd7698fc80",
        ".github/workflows/science-teaching-packs.yml": "f3bd379cc5f1ebcb296f4819a8e2f6f7a488a4b5bd2955d409f8a7ee626715ff",
        "tools/stale_evidence_sweep.mjs": "17813c59e3752fb9843374a302895d0d4710fb2c749d29af81a77873ff9d3677",
        "Science/Build/W8-W13_2026-27/SCI_B_W8A_Sugar_Labels_Explore.html": "74d17d4e0f6873f094691daa753539f8a351887160beea6a8a8d727bba864d2d",
        "Science/Teaching_Packs/BUILD/lessons/W8A/BUILD_Science_Autumn1_W8A_Sugar_Evidence_Read_The_Label.pdf": "fc9ba726c94177000d872c28e3c7db3812c268d6552e936a316c38654a95a0dd",
        "Science/Teaching_Packs/BUILD/lessons/W8A/BUILD_Science_Autumn1_W8A_Sugar_Evidence_Read_The_Label.pptx": "d93b814710bcf57ece951ba0aaf82ed41320247571ec48147e26a5423b3c07e3",
        "Science/Teaching_Packs/BUILD/lessons/W8A/BUILD_Science_Autumn1_W8A_Sugar_Evidence_Read_The_Label_Pupil.docx": "be71bc9be6c6d9c23383ee35ec739df80830ad5e336e7095098deaf3003a6d64",
        "Science/Teaching_Packs/BUILD/lessons/W8A/BUILD_Science_Autumn1_W8A_Sugar_Evidence_Read_The_Label_Pupil.pdf": "25544b193963f552a1511ac17bd5b5353cbeeca71d6788ac4deddbc61f905dc4",
        "Science/Teaching_Packs/BUILD/lessons/W8A/BUILD_Science_Autumn1_W8A_Sugar_Evidence_Read_The_Label_Teacher.docx": "7932493b683f1ac4ab7fbaabef8f55ec13e0db311dc63334788dc88e9fc5d099",
        "Science/Teaching_Packs/BUILD/lessons/W8A/BUILD_Science_Autumn1_W8A_Sugar_Evidence_Read_The_Label_Teacher.pdf": "8c9984c7683196b03a8acdf90764d7136f390f4fb0e28211077eb4184311f5a5",
        "tools/downloads/offline_pack_browser.cjs": "017782ecf949ee7c3030c4f872c2c532e0178ccb03cc39c8c636acf257623a95",
        "tools/downloads/prepare_pack_browser.py": "24446fbd47fa0a8b4de2ae1f79185206ecc042ccc72dfcdec8076c3bc38e9ada",
        "tools/downloads/test_download_pack.py": "cd5ec2a980f5cd305f4e33d18d4297bd1e75f8b9674f55e10c6f4d37a466ce6e",
        "tools/science_teaching_packs/check_build_sugar_browser.cjs": "f0b3b44a025131f16d2085f26ca7a2d9d19e2dbb58a6d692d309a49f3d3a1f2c",
        "tools/science_teaching_packs/check_build_sugar_pdfs.py": "62f8d1d1989be600374fdae1dbda9c7ebf407711cfb572123a3f9c31c4442a03",
        "Science/Teaching_Packs/web-slides.html": "f31f09d03f5d8c417af1745b38309fa537afb8bb4c6a08f387db3349d9e1cba2",
        "Science/Grow/SCI_G_W3_Friction.html": "508f1967b6481671dafb149d7177b620b194074312cee0dbdd30553c166b634a",
        "Science/Grow/resources/GS_W3A.html": "e5bfaf2bc70912aeb59fe9a2eb1032d86c7a473a1059ba782fee1be7b3513dc1",
        "Science/Grow/resources/GS_W3B.html": "fb6580bfd1e02d82627d60e1c2e08c3a34b227d0cbe760545502a8e51ab91208",
        "Science/Teaching_Packs/GROW/SHA256SUMS.txt": "de59e3ca70b403b69b625ae07603d69e1d557bfaa6f50a798d59f9ebb77f754a",
        "tools/easter/SCIENCE_ORIGINAL_TARGETS.json": "b5ca128e0ca53030256299a6877dffa781b63e5c1f2034722b75ae2ab806e204",
        "tools/grow_resources/CONTENT.json": "d8e39cef0051046bee5f1044e0cf2e412b3b4ebf8480361d6ddf298b667a6903",
        "tools/grow_resources/BROWSER_TARGETS.json": "288490cad98b1ce7d3f4b8f357c086220f1ef070c846189716c18b8a7122bd0c",
        "Science/Launch/SCI_L_W4_L1_Diffusion.html": "563e0bddc7049afb1dfc7245b1810da5094c19bca8027a08bbaf4c26d5a0dc54",
        "Science/Teaching_Packs/LAUNCH/SHA256SUMS.txt": "7ac03b10baef29ab9e82ab18fab775e22c7fcaf079c201ad818493902b40abc3",
        "Science/Teaching_Packs/BUILD/SHA256SUMS.txt": "4f26737e16194546a95f093cf1f566cc723bdce80822caf03cc7503abfe289b7",
        "Science/Build/W8-W13_2026-27/SCI_B_W8B_Autumn_Science_Checkpoint_Do.html": "7b27a0d82cd7df671c6a3b52b46d5d620ed678c332cdc58d1c649c3b29dacbac",
        "Science/Grow/W8-W13_2026-27/SCI_G_W8A_Day_And_Night_Explore.html": "a5c6fb99587b2d9d715b116cfe7b0c706abe186bd386cc23b72f4fb2b5984493",
        "Science/Grow/W8-W13_2026-27/SCI_G_W8B_Day_And_Night_Do.html": "32c49a121b8d9ed7f2af13c038117bdf4fbb0e9f23232f91a0015040843d6a00",
        "Science/Launch/W8-W13_2026-27/SCI_L_W8L1_Enzyme_Action_Introduce.html": "125bd365d7c46d62b3867ef226c3197e715d6d6834895ca1e228e5219d1dfa0c",
        "Science/Launch/W8-W13_2026-27/SCI_L_W8L2_Amylase_pH_Core_Practical_Explore.html": "cd724ac40006a40abee3b6bc958f6fcdb3c44af017ad2564f4a601154c4a65c6",
        "Science/Launch/W8-W13_2026-27/SCI_L_W8L3_Amylase_Rate_And_Topic_1_Do.html": "d415a934d0ab0e0de37b8f75bcfc5a3c3410fb8cdaf8ff1b187400cd3d1f75c8",
        "LundyLoop/1_whole_school/Day_to_Day_Desk_Sheet.html": "3d5fc8fe3563ed7e7d00df8a022b1888ef6f427579a607944c81594454311062",
        "LundyLoop/1_whole_school/Whole_School_Reference_v2.html": "715aca553c1a54ae504460d00f7b600ee17eefd27567f4a3aba1cd4b8de1fb90",
        "LundyLoop/2_leadership/Impact_Framework.html": "d2ede4fa93500dc48af37b8464ea85fa597cf2896042ccfbd43f3e78ae765bdc",
        "LundyLoop/2_leadership/Impact_Monitoring_Crib.html": "d116cde23efe70ccd3c004ff2379af42e9e7fda4ce8df7d7ee5f9cd548e1ca79",
        "LundyLoop/2_leadership/Ofsted_LAUNCH_Loop_Sheet.html": "1f7c600ffccaf931f5c8001e1c151e8165bbaa6094a4e25a3fccf73b424befdb",
        "LundyLoop/3_subject_guides/science.html": "734d2e53f6a7c28fe7e52c66d3ee4661b2557682acb30cc2e77d7e0b9eb19c03",
        "Science/Grow/v3_40min/LUNDY_DAILY_REFLECTION_EVIDENCE_WINDOW.html": "8a110cc1db2527e2e1a7d95e506fdb99d085a543453ca305aaf46fdd3f792a2a",
        "Science/Grow/v3_40min/SCI_G_W3B_Friction_Do.html": "97aed0e499bb85d11d2aefc822c9bd8c4c856281813ec7bbc04cd8d1f86a7c24",
        "Science/Grow/v3_40min/SCI_G_W4A_Mechanisms_Explore.html": "fd28d3366804e5a50cf1c93f0d831841e31f005b783179b170cc67527c391d8f",
        "Science/Grow/v3_40min/SCI_G_W4B_Mechanisms_Do.html": "7f186cec059e51af8d68c19bf8854f000cecdf63d4f12b187214905eafb5692a",
        "Science/Grow/v3_40min/SCI_G_W5A_Fair_Test_Explore.html": "cf7c715478fad8e29cbe1a42c3d5e7819465589fda764989256fbf47d9132bfc",
        "Science/Grow/v3_40min/SCI_G_W5B_Fair_Test_Do.html": "a404195e8d314ba7f40e6dd54d37a02946f5c08482054d416143fb1b11d1a7a4",
        "Science/Grow/v3_40min/SCI_G_W6A_Earth_And_Planets_Explore.html": "ebfa441095f114e2fdb427ccd9ee24860e17ad12ba55d2de77525768997a4869",
        "Science/Grow/v3_40min/SCI_G_W6B_Earth_And_Planets_Do.html": "91ae4a3586aff866541f5b1809b423cadcdf3321f664b29fce53defc4a6ce1ae",
        "Science/Grow/v3_40min/SCI_G_W7A_The_Moon_Explore.html": "2b54a5399c6422873be70b5ab43ea271112f54ae1401d990705b19a2f75030b4",
        "Science/Grow/v3_40min/SCI_G_W7B_The_Moon_Do.html": "85c9c9c7d4a12fa67fe6a098960aef0e880a3b7bf217667e39dad570bac11ebc",
        "Science/Build/W8-W13_2026-27/SHA256SUMS.txt": "28c48fd2644c70cee9e36b95981c25b08f9bd5693c9f43a7f73138f113aecf04",
        "data/chassis-census.json": "11e7b4b8f3bb43de2d338c59808418a2286b4fdb93bcf16e067868bc48a577e7",
        "tools/downloads/definitions/launch-science-aut1-main.json": "b42288f072512eaa9e0e954a6927d1247640dfbf6daac31fcfec4b80b59cb0c6",
        "tools/launch_resources/lesson_acceptance.py": "bbebaeb821f32c04eb1b2e01e819795ffa97cd851f33d7c22fec0b0505a9fe21",
        "tools/easter/refresh_pack_checksums.py": "7248b8424c6435f3637a7e3414e38fbab9f67e6b2a0f6f34fc8a586dc4e9c126",
        "tools/sx3/split_arrival_stage.py": "995e325aa9e5a157232cc63fd242207ecd1c9906ec43774611b47bb53f2d4ab7",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W01/SCI_BUILD_A2_W01.html": "8aa212b808412a58145e4cd66f8340feb51da865eb5f8600a15ed5813ec8e6b2",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W02/SCI_BUILD_A2_W02.html": "c50ed117c8637f20a99df353017a100ce9cc423d697e4a284c82c717ed191729",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W03/SCI_BUILD_A2_W03.html": "e498181851be764a17e0f56537f427c3b6434ae2620f6de6791c3767385a8830",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W04/SCI_BUILD_A2_W04.html": "e236155bca8b61a6792788d303555d550c8cca644678337468182e304b396a5d",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W05/SCI_BUILD_A2_W05.html": "17edd793f04daed139f9bcd52086e987b0684d223329f6ddd67f515e763eb6be",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W06/SCI_BUILD_A2_W06.html": "2051cf800a2413f6d87bd4fdcb24181ccd610eb3edde9652c0fff79c50e91b84",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W07/SCI_BUILD_A2_W07.html": "d48b70b0d933b12c8edc0630d4005ef8c0b4e5bd3902321aaf4c684749175349",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W01/GROW_SCI_A2_W01.html": "7ac238c37f22bd73e1a3030533ef95acc842f5ef1c5b63ec1fccfcfe6170ddc1",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W02/GROW_SCI_A2_W02.html": "c45c77b2c19abb443570e768ff9a5e3f0274ec0d2001ae8ec2f417905fed6080",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W03/GROW_SCI_A2_W03.html": "66350093c8ce6d76abae1413654f4f38fb154b48f88059458ee519a4b5005203",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W04/GROW_SCI_A2_W04.html": "c55a36af14216f2272a09df6773cf23178e29c4eb8c169d7dd74065d59bc9554",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W05/GROW_SCI_A2_W05.html": "e78439e2ce5893bf5a9b99d671d7d0ce440bfd4913210a9fb2c8945634c9fdd9",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W06/GROW_SCI_A2_W06.html": "5eae1a3b226fba8f323233bf5ab8e0b6793201aa3435a8ac431346636804ad86",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W07/GROW_SCI_A2_W07.html": "12b724f89f9573177cac1ac12c5a6d511ad5fe8c15e49ee9da1134296b24a009",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W01/SCI_LAUNCH_A2_W01.html": "68f551d7fad64a4044ff94a5ec5e51ef50fdbf610cde86e52a167b29c1e57e87",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W02/SCI_LAUNCH_A2_W02.html": "557f591ff51ba7386db0749302a5a375d7032095d2b442de847a9c25d3bf109c",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W03/SCI_LAUNCH_A2_W03.html": "31539459d094abc4df7f72a81e70a28521dc3522d82d8aa74602c2bc97e17d1d",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W04/SCI_LAUNCH_A2_W04.html": "8f0ff0382d8b081d619462db3d99df733ee294e95092c157a26f6a9ebfa58f18",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W05/SCI_LAUNCH_A2_W05.html": "87f56b1679f1898ab2fd2f131c231aa9623ca32c5ea0c970c3b7e240b4b09c04",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W06/SCI_LAUNCH_A2_W06.html": "3b77933ff22b9d4f2d42dfacfdf63616e6afc5ecfc4b7071721b2bb25965f3df",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W07/SCI_LAUNCH_A2_W07.html": "7b0222fcc21e8f5915c169d4a9555598bf31eda46f72c0c085e7c78f16f4a727",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P1.html": "f9fe7fb938aace82bd84c206503b056603a92cc12ea5b1479aa4653b693a2b7a",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P1_Editable_Pack.docx": "bd312c7f1b0ed68783b007471db4358c05b2c5152a5cb47db009a032a8357a58",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P1_Knowledge_Organiser.pdf": "21267a597ce2579b2850547acf74baba4bfaf554a48c4818d3f2107018232973",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P1_Pupil_Resources.pdf": "9d71b77d7521ea2025f43f9ea8213a1a4313015ef4eaa6ecc080308f4f456c13",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P1_Word_Page.pdf": "853bb9327e38312513f7e79bc0ed10b6bdecd0ae0cb201d1793bc87a184320a6",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P2.html": "50981c4549441f4f076b9296fe27c4ac08a03e727f4d1b572d0b14b9aa48c003",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P2_Editable_Pack.docx": "5aaf766e14a746497f3c98307e33613d3a75328a63fdf28ce6e58938b1db5612",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P2_Knowledge_Organiser.pdf": "d4df2abc39a9d292d21478ee0c3aeb0455d247810b3117bc1b3cac28c0f22765",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P2_Pupil_Resources.pdf": "5092013b135085f18d15969eb71973c4ea13743f30d8cb5cf3311078d10707ab",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P2_Word_Page.pdf": "55cc746f0041fbd95d3b8456fb05d80a402bc99d9890bbd2cf4cb10f9ed46d65",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P1.html": "04b581ddaad85093e61685fc37cba53ab0509a22a12330d58a7772ffa1a4573a",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P1_Editable_Pack.docx": "bcfa61d6d54b055ea9a9a8da8873820821a96d8d0a287c0afb882e32c44158df",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P1_Knowledge_Organiser.pdf": "330c1068ad8c854eba3579c87323bbd44c6b34085add29f0116a4a74272b77bb",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P1_LESSON_SOURCE.json": "da18c08addd8cf72645eaf8f7d40b8bb9bc3237b014c6307ec9f709add0ce0e9",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P1_Pupil_Resources.pdf": "0ac30bcf2a4ceff8384da01b1a1dffb9601c464cbb67c38e6a113ab8a903434e",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P1_TA_Brief.pdf": "6649b3ed6ab140b911f30c2f8037dc48d94d12dfbad19797d6370c2e1dce13c0",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P1_Word_Page.pdf": "a0b07e735ea95722b7e04b9684360e951e3ca2f5e5d0e6245e3978353f083ce7",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P2.html": "e5eaaee053f6cf202538562ef593a35e4569dc53ebbe7bd6a217bb6f85d7fa5e",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P2_Editable_Pack.docx": "25613d500cf28ec9f16869ab15a69ab087b2b6978c381635ee0aa8ebf5ac45a0",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P2_Knowledge_Organiser.pdf": "6388d5e0ada1c030862c0616fa2d6cccff57aa96ff114e4fd5c4f07931827e90",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P2_LESSON_SOURCE.json": "b1a39d01a1ddaf5b1ebbbb4cdc5404fe581a0109a371ead52ad5c99fcf1325ae",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P2_Pupil_Resources.pdf": "2bf6a56efd5e8a9a1b303e6c08652d30d5312f85265f84cb562352bd20b8ae14",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P2_TA_Brief.pdf": "a38d1ff54044ade0b490632902235be875a8054ea7b9389f6f2f5cc0d7f5e99c",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P2_Word_Page.pdf": "f607ba492ec7241b4b960c46df721bd016f9db5a41a656769de272c0767f9072",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L1.html": "37e4f33796b834366ed837c9087e943d4a5f86a73bf7096a5b43d677c20d6b51",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L1_Editable_Pack.docx": "3819492eb5e69f6272c9bdf8d6b67ad505c403ff6d12126c6aa89bcb94353061",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L1_Knowledge_Organiser.pdf": "0be94a336b15aa90ff2d8ad6bd083c50a594b0772b2c34f40e0733210f9c8359",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L1_Pupil_Resources.pdf": "90d96ae7c9db767121ad2bd02b32e9e9a6d0bc27c881a6dd6c251f0f9717ffa5",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L1_TA_Brief.pdf": "2529ab39a331969e9ce36ef52a7cdfc647c542df3733060a57af63ae8753bad7",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L1_Teacher_Notes.pdf": "72259decc5cb72726fd63678ce1e9fb74f0c4bb2da4102a395e7a3c67ee79757",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L1_Word_Page.pdf": "07394707d6fe82e4e615c89edb7ec1ee00291bf673a13a3be9705b5101adead7",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L2.html": "12412e20a49b1927d5448c0cd8f1f68785d9005d9b648fd53064e4eae49d6012",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L2_Editable_Pack.docx": "1c12f4ad7e2152933c37835dea88b7bb667ec94517711d9ab48298b845c74639",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L2_Knowledge_Organiser.pdf": "6828774324b31e15096930f9404a0a52332b12ae0145f51d55d60ac0ec252a2d",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L2_Pupil_Resources.pdf": "0c7803325256e2e7c21537a375b6d01247c61b1948a9b272562a36cf2b020207",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L2_TA_Brief.pdf": "3f00e2f8c8d16c407ef4f919037cf1819a12fcdf1161b3b17fc0dcf278eb835f",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L2_Word_Page.pdf": "5ff5abc72687a32b07926ebde0301cabb4cd9822a12cb2c962ef22cfb149ad5c",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L3.html": "6e03c5465fb5af66d46dbc7107b1d0a7ba48f6ade90c178796d01384443f26a6",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L3_Editable_Pack.docx": "e55f161c21cd21afae8a4144c96a826c11b6ead745e28670113eed616241af3e",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L3_Knowledge_Organiser.pdf": "187ba3e37c2eba48733072546e10d6efdcd9eac0f72be30c82f905c65b4dddbd",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L3_Pupil_Resources.pdf": "5bac2399679393f5675372c714ca52fb0575963d886231477b998c25699eba5c",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L3_TA_Brief.pdf": "10b256f949dcb82d1ac06674f6cc2fa36f77787914f4c55d4d3870bad3a0767f",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L3_Teacher_Notes.pdf": "f719fc0973fb6c527e741b70e1804ab7bc662ed1ca64ef55c7aea8b57bdca7eb",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L3_Word_Page.pdf": "7efe49136d285b4cb400056f788c671f944cc6da25c38723b0d89fd9cc1fd1ea",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P1_Slides.pptx": "8692338d658540dbe378b8a3c7c51afea10727e6deb3352a9c594761b7e7cd7b",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P1_Staff_Answers.pdf": "f306d34810421da4baea544cf6f828f3d08b34174c92f8214c37d453fa4fdd43",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P1_TA_Brief.pdf": "9b9b89be125a6dc3e0ae2687d2a51fb4312707a2963dedc59f9a59f966cb1400",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P1_Teacher_and_Cover_Plan.docx": "20e222766e99053b25c57f67a7f26fddc6ed8450fc110cb09ba07de30f59a969",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P1_Teacher_and_Cover_Plan.pdf": "167a8bbebe34110542850ac7ad7fcf122d21782bb284982c362229acfe69d8f2",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P1_Tier_Pack_Standard.pdf": "63aabedecb5a1f128858bc1b3fa8bda81ef313ded6b3bee9ee8fe809327cd80a",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P1_Tier_Pack_Stretch.pdf": "9eb29dc33de527778d6e8b22f89b5174192e4aca3860c3f2879c0076f48555da",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P1_Tier_Pack_Supported.pdf": "fa7b1271152b731b7e5f1ccaf5ce970f5e1a2ed978b34b686b5965ff72e0f9e4",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P2_Slides.pptx": "80bf3559458bbb5a398ef8970bd2abed3bb58e088ca4310bb5a9e5a05ded1edb",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P2_Staff_Answers.pdf": "ed66906bfee2eb41acb7e3ba4a05b5ed90a287854f855bdb1bc35f0762120568",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P2_TA_Brief.pdf": "d5bd612069fede8d7946f75196eef7784b89a7153bee3ac611313b994852ad41",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P2_Teacher_and_Cover_Plan.docx": "7c083cbed6e11d6d221ec0f71088a26502c07ba3df4c396d8ed9a5b767ae85cc",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P2_Teacher_and_Cover_Plan.pdf": "0fac05a0194a8e5154b4d18b34b068ca39cd23db5a6545d82cc287ea5e2fe458",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P2_Tier_Pack_Standard.pdf": "e8b4ceb66eb38178459b31069fed21651fd42065888ee1622d50acc3dd5b8cb6",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P2_Tier_Pack_Stretch.pdf": "ced4c6b1082edb09233b8d5df9601deedec104ea657a29ea6cd415908e65c00c",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W08/SCI_BUILD_A1_W08_P2_Tier_Pack_Supported.pdf": "7dc3046a6740d792644996744d0adfff410fe627564a09c7cd1e630a0ea245d3",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P1_Slides.pptx": "b3a595b98ac472d04264fd693a59786e2f22d0463d6931182de0363fbc50c6d9",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P1_Staff_Answers.pdf": "d37a45c44b76c1c7950bc1190591bb4d98fbb7a1586518356175a1bfb4306e49",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P1_Teacher_and_Cover_Plan.docx": "f9b64f301cb61b0a2c4d4b0c611e717d24b2842e07d24724bb9add6231f57401",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P1_Teacher_and_Cover_Plan.pdf": "e1c95f87e9818a43bbd8c6e2425ab684a5c326c4f487aecf0a3454bc84972211",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P1_Tier_Pack_Standard.pdf": "2fa6c16d8958d3795940379fd6e1abba4fbe0d417bfb8586a69b2c2d36806430",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P1_Tier_Pack_Stretch.pdf": "7fd0f0c2367bebb9df4f252e750d39ab21fa6b61029593b5c554fc927be109fe",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P1_Tier_Pack_Supported.pdf": "307c7e59582b457950ff9285cf73ed949646c244ff040b2e0c91da7179a6d197",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P2_Slides.pptx": "e52d66fa9fc148923a25cd0a9f6bac9fb5f218c3f3c4d446565f2009e810fbdf",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P2_Staff_Answers.pdf": "da089015ddb857afb7716294d82bf9082ce616fa6d2d38bd9e86815d0b399f3d",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P2_Teacher_and_Cover_Plan.docx": "9d77750476293f20d2273a7351c6efd16c3f12a883365847710aac6bb57f3f7b",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P2_Teacher_and_Cover_Plan.pdf": "109253b5aa73f8cf7adc6cc629e728ed7deb237566530fc5fbec7ce4c58ef004",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P2_Tier_Pack_Standard.pdf": "aa9f7c21b2608bd803de1bcce3907ea8a5717440d206ad940d4ca19ab387de15",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P2_Tier_Pack_Stretch.pdf": "17370edcc7d2f5299b2fe6544192edb87de6f67f2ea71b27da7559d70c2e2d91",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W08/GROW_SCI_A1_W08_P2_Tier_Pack_Supported.pdf": "afd8498e3615c0083a33369f27e0619843c4ae9ad8da7e2e79deabfc1fce9cc0",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L1_Slides.pptx": "e7b5a6d12b6b9b1ac3bdac81a0b9cfd2e13d0feaab89e7305eefe38979acff67",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L1_Staff_Answers.pdf": "a2d3cf2a33a2243dd90554e06824fbe9237d25b635cd8f160f0432e8de3d387f",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L1_Teacher_and_Cover_Plan.docx": "1e5f9e6be792dcbd135b7af50643eab585dd01536778f52a07f623b73a22f52d",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L1_Teacher_and_Cover_Plan.pdf": "5afc540ddb1af6d1a5ffd4091dca982c8ffa6a3163b0b3acfdee5f2208d0d1da",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L1_Tier_Pack_Standard.pdf": "6f8cacc3531014beb13283b62f232e4e0f13f8966ee5456d91dac51e6be7916e",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L1_Tier_Pack_Stretch.pdf": "cc8c2610c8d2426718ff68d0c827186051ed10290b84ce6abf88e55ed550a31b",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L1_Tier_Pack_Supported.pdf": "9c3b8c182397006de0aadaf302f576d08d86991f7ebef5b7ff96bea4a90110a2",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L2_Slides.pptx": "22b050e29515b7870e3a4ffd946ee2572144021a98222ba445e48cfd55cadea3",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L2_Staff_Answers.pdf": "d74bcec22272fd357a8e9a70fbdceaa20cf1070674510e5a3a1c94abae780cef",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L2_Teacher_and_Cover_Plan.docx": "402637e43bfc0798c83e70ade6198cb7cf9d040b7d71553a08a9cfeb2318d821",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L2_Teacher_and_Cover_Plan.pdf": "1167fa90296852a34867e15693c240e8f32f4e2ca9710984388b27063417d3e6",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L2_Tier_Pack_Standard.pdf": "a35d8376b32714dc9efe844fae9f0de7c3eb2c425f4f978c458267594febd72a",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L2_Tier_Pack_Stretch.pdf": "8f75a9c3eb811e0975b90b55ccee8419da2e46bb81d611f0915fc8bdbbbe4ac8",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L2_Tier_Pack_Supported.pdf": "ca7e159c3ebaeef3599aa51b51c4293c70926910e6fb7dc2b3858014b166bc7a",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L3_Slides.pptx": "9e5e616843da77c847f997071d64bf66c99b69410cee9114eda9e3e28c3d121d",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L3_Staff_Answers.pdf": "c49fdde938fe1c2bddbbfc72690bf7813afed79aa78876961175e68e3dae1ddc",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L3_Teacher_and_Cover_Plan.docx": "c8fcb602b71bf492e6a6b61abe5ec76518ea4220da3a83dc6699d55c98b74846",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L3_Teacher_and_Cover_Plan.pdf": "a1a89d754ea4628c791046505158b08a063fb280ec35b79a3e48c70819ea7fe4",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L3_Tier_Pack_Standard.pdf": "9b53f78108cd24692e11187272294f9bcd0d748e60c5c374c01eda88e6602b53",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L3_Tier_Pack_Stretch.pdf": "64277a00f927f640d733ea4bfb013185bc50e39767c90e8169050b5d73cadc8a",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W08/SCI_LAUNCH_A1_W08_L3_Tier_Pack_Supported.pdf": "d632f205b8366fd1642e79483b4e38861af09782ca38a32854cd5b82f55975a8",
        "Science/Build/W18-W26_2026-27/SCI_B_S2_W6_The_Evidence_Museum.html": "a035abce0d3a000388fd870d6464ccc5beea732d05f343e57286a2c5e32142a9",
        "Science/Build/W18-W26_2026-27/SCI_B_W18_Soil_What_Is_In_The_Mix.html": "c2dfd7467525b4e16b84c5c3f6169104b3e56eb93f19bcf176cc54df13ad2d5a",
        "Science/Build/W18-W26_2026-27/SCI_B_W19_Soil_Let_The_Water_Through.html": "6d00913c4a1e6d7416940d1c563f8bfb70a5af26cc96863e8c8d2199b684b531",
        "Science/Build/W18-W26_2026-27/SCI_B_W20_Soil_Account_For_The_Water.html": "dfe734ceb9cf62110ae70596485376633309f797b685ec69ff221c4a157f6dab",
        "Science/Build/W18-W26_2026-27/SCI_B_W21_The_Blackout_Box_Mystery.html": "69facd351125b4bf42b58a61be3f206e78c8637d754b72941b64b06b35a216b3",
        "Science/Build/W18-W26_2026-27/SCI_B_W22_Light_Source_Detectives.html": "cc8fde748fa625c294dbc14712aec983e3ce0c42a55c3190d84d4b95fc29993e",
        "Science/Build/W18-W26_2026-27/SCI_B_W23_Sunlight_Make_A_Safer_Plan.html": "39803d5a36353744618709105daaec6f0ee7f3af97e5c45461cf59e2d8ce0d0d",
        "Science/Build/W18-W26_2026-27/SCI_B_W24_The_Shadow_Screen_Lab.html": "ee0270fafe98bb09f9933389779ec8bb3830072903131d2c0a537e935e33820f",
        "Science/Build/W18-W26_2026-27/SCI_B_W25_The_Shadow_Size_Studio.html": "6fec65e159e4adb5dbf6d28cd9f31aeefdefe4ac11baa55303fc91daa30cf462",
        "Science/Build/W18-W26_2026-27/SCI_B_W26_The_Fair_Test_Repair_Lab.html": "b25603f579ed857f48bfa0e23a5b407a193710684a5a97f0cf6bac2ea062e3bc",
        "Science/Grow/W18-W26_2026-27/SCI_G_S2_W6_The_Spring_Science_Evidence_Exchange.html": "e96f76c22c0995f601d54ea49280a5c7b2b46feff98bb619de51610e7c0b755b",
        "Science/Grow/W18-W26_2026-27/SCI_G_W18A_The_Cold_Case.html": "b3b1b5dd758fd95f5e1add5d6a8826c78b8c21f7aed5b5653c1804336deeeaab",
        "Science/Grow/W18-W26_2026-27/SCI_G_W18B_Circuit_Fault_Clinic.html": "62aee8012e48c26374b653df3a3327cdbe8a7aaf81936a097cd7bb0b968029aa",
        "Science/Grow/W18-W26_2026-27/SCI_G_W19_The_Spill_Mat_Design_Lab.html": "257607862aa78a37eb09a405cd4d77bdaa3d8962cb825bf3bd6a38eacb22a378",
        "Science/Grow/W18-W26_2026-27/SCI_G_W20_Body_Systems_The_Dispatch_Challenge.html": "3ba8036580d99c11e469bcc5b5f01e00168127d39a06b1d6d9c77cd75eb171fb",
        "Science/Grow/W18-W26_2026-27/SCI_G_W21_Heart_Route_Rescue.html": "b324bd644646f5d191ab1e007bf051254a8eae21115679fb8267b33d9e6a0f2e",
        "Science/Grow/W18-W26_2026-27/SCI_G_W22_The_Health_Evidence_Advisers.html": "6ff2ae0930cb863bd81589e50fd5b0e87f0123ef1ada1e4d349bfddf1b5360f0",
        "Science/Grow/W18-W26_2026-27/SCI_G_W23_The_Nutrient_Delivery_Investigation.html": "be13cab84c879e8a8c359280b12e5aa5b9803d8e7355e08fc6dc6cbed51b94b7",
        "Science/Grow/W18-W26_2026-27/SCI_G_W24_The_Recovery_Research_Room.html": "468afdb0ab08d6f974a56f289babfc8122bf7bbdd0815fc203b138f9cd2c3d26",
        "Science/Grow/W18-W26_2026-27/SCI_G_W25_Life_Cycle_Archive.html": "8e7a1f6e54fe72e80151f7e066ab961053b70e25016d3d86a4bfe355288b00e7",
        "Science/Grow/W18-W26_2026-27/SCI_G_W26_The_Life_Cycle_Comparison_Bureau.html": "16fd7c4f61714e08cff8dcb3f0ea527a53855143a43254159594789b48edecba",
        "Science/Launch/W17-W26_2026-27/SCI_L_S2_W6_Health_And_Plants_Evidence_Checkpoint.html": "b80aad62cbf5e32026c09747dd594563ab74f904cafb9dd5b52a82db48fd8c19",
        "Science/Launch/W17-W26_2026-27/SCI_L_W17_Evolution_Build_The_Evidence_Case.html": "4dfa2e8128805e934b30b1cb47670fb6165325a14b839d313915badd2c7b13ad",
        "Science/Launch/W17-W26_2026-27/SCI_L_W18L1_Selective_Breeding_Design_A_Resilient_Crop.html": "0e3802e555131ec4e746626f804006f5cfde37e71c81d6e12f822204b7c42704",
        "Science/Launch/W17-W26_2026-27/SCI_L_W18L2_Genetic_Engineering_Change_Test_Decide.html": "8543572840ccc204caca5c595f727b58335616ce931a5db83fb2cf623ebce9b3",
        "Science/Launch/W17-W26_2026-27/SCI_L_W21_Disease_Detectives_Follow_The_Cause.html": "6f6271807fb72936fec447f13484cafb07abacbbfabae8058082b6653381e4eb",
        "Science/Launch/W17-W26_2026-27/SCI_L_W22_Immune_Memory_Recognise_Respond_Remember.html": "60867b0fd1c5177b9d326677b53ff2a296d1742fcbf2c10f61a49162e9154456",
        "Science/Launch/W17-W26_2026-27/SCI_L_W23_Disease_Data_Newsroom_Make_The_Numbers_Fair.html": "f0ff4f9822a7698ddb1b502f4be5fddd39e09b34b3076b1e9c96fd3c5235fdd5",
        "Science/Launch/W17-W26_2026-27/SCI_L_W24_Photosynthesis_The_Light_Lab.html": "804b18765c1b10fcbfd4f6136891b863852e40c4651c297e5d25ab311066089b",
        "Science/Launch/W17-W26_2026-27/SCI_L_W25_Plant_Transport_Follow_The_Water_And_Sugar.html": "6b12ed852e131a63bd7b13fb1aa07535dbd942b4d849b4bb2b54cf97a5289e55",
        "Science/Launch/W17-W26_2026-27/SCI_L_W26_Greenhouse_Challenge_Grow_More_With_A_Water_Budget.html": "f65c036a80029e775b40e1de07e3d86fde36571658abc499a8809a95d2d91a2b",
        "art.html": "066d4bdd3107ae7105d2930352b48e8b848f53a402874e3ed432ac7eb0db41bf",
        "tools/downloads/SOURCE_PLACEMENT.json": "a4ad22abede7e69dcbd434781ea385c613662121f38417c71e658378fe229b9e",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W08/BUILD_RE_A1_W08_Captioned_Model.mp4": "3ab4e04878f4f32431990301f4efcd6d13622f00b4c8d8614a55ccd7d5da6f5f",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W08/BUILD_RE_A1_W08_Knowledge_Organiser.html": "a66d638003a6a58250154c3744099d04780e20051c7e5455e3c3a98144bb1391",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W08/BUILD_RE_A1_W08_Lesson.html": "8b29ccf42a1a5137da2337594cd86f9116ed166113edaaa5a8b87efbc8248ff0",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W08/BUILD_RE_A1_W08_Model_Transcript.txt": "1f2ea6dea9ca7f89a89551ab1390dda2c46facde3fe53b2627c27810d46ab767",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W08/BUILD_RE_A1_W08_Pupil_Resources.html": "1bd5150035da1b98e09cb128cee4f6d95c1c1e50c5f6f16ce47d273612766678",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W08/BUILD_RE_A1_W08_Word_Page.html": "d2310504eb3f386b2a6a725b258aa3c138f8fd433c9113ccf99f40813f18a738",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W08/Object_Picture_Choices.png": "798ebe66df7c5d23e8453827db5a728e9be0e0201baee18ddf09efe655e19b7e",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W08/Object_Picture_Choices.svg": "854b2d8ab3a62c4ad23e8d3afcf7d331acfa90ae7a82357f522f39df8fca078f",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W08/Sources_and_checks.html": "dbd5258f906ee7ad3cd5acef6683c89af3691fa855459330e66cb1492e9043bf",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_1/W08/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W08/GROW_RE_A1_W08_Captioned_Model.mp4": "92b4151af44941422b3bbcaaf01bdaaad2b2a034e01f020982c2c0b25066382e",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W08/GROW_RE_A1_W08_Knowledge_Organiser.html": "0c6624b1a8b739e6fb37efa1dcd8c2cbe73749452db4a5e95efaf3934a18a88e",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W08/GROW_RE_A1_W08_Lesson.html": "fb8acf612896c8891db31b498dab8240b6e6d67e819985b5224e48b2fd512ac9",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W08/GROW_RE_A1_W08_Model_Transcript.txt": "c517db4159a9ebbf7b72cb3fa2fdc8494138576bb53b07e0038c899612d58d36",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W08/GROW_RE_A1_W08_Pupil_Resources.html": "09e6b90218f1361b1e63632c53c5b23af8708d036ab0ecfcb2074f6778800d72",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W08/GROW_RE_A1_W08_Word_Page.html": "cbe1d4e91036c44ea42606ef18a92f4075b94de83ec923d8a16775649227b5e5",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W08/Object_Picture_Choices.png": "6aade8f8f4348d7c1641b447142a1339cfcdfbfc4990e8300e0e2d625068a233",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W08/Object_Picture_Choices.svg": "53e21c24afcfaef31e60348ab838f3b5d55f86dc0b97ee64231079ad880db49f",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W08/Sources_and_checks.html": "3c777c0fb0c598a6722c8cb6c8c2e71b5e20da7b5c518667c20c15f389b076df",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_1/W08/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W08/LAUNCH_RE_A1_W08_Captioned_Model.mp4": "8b4eb9d2ab9ec93df8a5d387ecdcdaebeaed03f7b9a8e8809933e223ca698582",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W08/LAUNCH_RE_A1_W08_Knowledge_Organiser.html": "efcb492c4fdf3f63c96eb1897df0ffe1c05e03a6746d8ae3547aded71e9f8015",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W08/LAUNCH_RE_A1_W08_Lesson.html": "6795ab3a325bb78731dc39b5f8e49819de3fa7524ff8c3068b3dfc6e4e856270",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W08/LAUNCH_RE_A1_W08_Model_Transcript.txt": "fd1f526487991505fd3c9b1c2c63d7cd96c4efa168c9c652f329dfbe683ffb5e",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W08/LAUNCH_RE_A1_W08_Pupil_Resources.html": "2decd87c30190b1cf687e6f601acc9ef1a34d8a2b80e7fc0636d4c41f1481d99",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W08/LAUNCH_RE_A1_W08_Word_Page.html": "0803152ce3a25213521c94e2d54a644a734e7ed419430599454538b207ad75c3",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W08/Object_Picture_Choices.png": "7b8265232d9d4a7483174e18ff587529e9206b0d325749aec547c9a9f1c336f9",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W08/Object_Picture_Choices.svg": "20eda92e86b70ff59350ea9834d16623602ddad06c90377ee36778c1020a1bd5",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W08/Sources_and_checks.html": "30f756f5939970a48368d743a52f5ddfd7b010433c740a1651e2670e5d8c6374",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_1/W08/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/START_HERE.html": "4ea63a0c2de74e7d37f235b905229fd4e76702b6a058245b2fd8690b9f54b336",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/START_HERE.html": "9ec66e89f1b09782117ba72578ba205e37b196ee6dbcb0b0de2741f0cafd30bd",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/START_HERE.html": "d8688b954279d1d83d9b915a7b59610e6c0b32003681d7bf3ba8d6d36f7065f2",
        "Humanities/Teaching_Packs/RE_Spring_1_BUILD_Reviewed/SHA256SUMS.txt": "dfb40505261e40c0e5038d6722351ddd0450055c47b17a85a6b88d42714f584e",
        "Humanities/Teaching_Packs/RE_Spring_1_GROW_Reviewed/SHA256SUMS.txt": "80bb4cc4d430e3b110781c1870a6454f48cf2e56fe4c1759f038594d3ede2d8a",
        "Humanities/Teaching_Packs/RE_Spring_1_LAUNCH_Reviewed/SHA256SUMS.txt": "c4feb606541eff53b17a5e6d793f87d78c61d73caf6858944ffdb0db8d710d22",
        "Humanities/Teaching_Packs/HUM_00_SoW_and_Order/RE_Scheme_of_Work_Spring_1_2026.docx": "7bb5fe5fc1c72b12b472e9a3019f1b7bad7109f701698acf5a413587e99ff70c",
        "Humanities/Teaching_Packs/HUM_00_SoW_and_Order/RE_Scheme_of_Work_Spring_1_2026.html": "ee4e98a047de8ae7eadd7de1e254ef83ea811e0fb4c95dd313b683c5e9906e7d",
        "GROW_ASDAN/Community_Project/START_HERE.html": "1ca02932fbeafb09930d3dd68ea03248d39e58b4aa0b00cd18632c452c6c5801",
        "BUILD_ASDAN/FoodWise/Teaching_Packs/BUILD/SHA256SUMS.txt": "801425aa43631264b8e5288d7eabb3bff6f972c5e88263c57572ea97545633db",
        "BUILD_ASDAN/FoodWise/Teaching_Packs/DOWNLOADS_MANIFEST.json": "a913269f3d35d03f3c67eed19500da122937655e4956ce5c3b90af87076f4b30",
        "BUILD_ASDAN/FoodWise/Teaching_Packs/index.html": "e35e895bc38db84474de094ceb402e273f9f93419d7b4fcbfb08e69ae09f6cc9",
        "Careers/Teaching_Packs/BUILD/SHA256SUMS.txt": "97efdc2b08737bd672a93549964d641a5973130eab53c5cc872d1daf110bd138",
        "Careers/Teaching_Packs/DOWNLOADS_MANIFEST.json": "5590c0d9996a17bba2bba981f68d45612dd5845b070417da4e3ea07610aac3a9",
        "Careers/Teaching_Packs/GROW/SHA256SUMS.txt": "a0f67cdc5dd04ea632369655185a71d50f370c11a035a19044c3850806502650",
        "Careers/Teaching_Packs/index.html": "38a590db2d2a8eb62941dced4603ff8dfe2064b244503f26a6f0817ba9d7ffa4",
        "DT_Textiles/Teaching_Packs/BUILD/SHA256SUMS.txt": "7be9ae481f7dbb9693afa7a600f7d7922d9bdc82e1d34db780272612e8c346fb",
        "DT_Textiles/Teaching_Packs/DOWNLOADS_MANIFEST.json": "fc17200e5551a215a79b906e9cf55b31310b03836039b777fbb3b0aad55ca3b9",
        "DT_Textiles/Teaching_Packs/GROW/SHA256SUMS.txt": "e4c41c8799701b85f1e605fe3730ab9dba8f0e44836e66bc7f322958193010e9",
        "DT_Textiles/Teaching_Packs/index.html": "0ca9d944edf8cc9ca90bc076b3e368a0e0847eaeb805e3259842ccd24cff2cc7",
        "GROW_FoodWise/Teaching_Packs/DOWNLOADS_MANIFEST.json": "b4de1de95a6079bc61169c795177028d6f4a5c104a9fdc91db42ab4861488476",
        "GROW_FoodWise/Teaching_Packs/GROW/SHA256SUMS.txt": "061d2fa95fbe65bbe567b00d21d45baa563a31ffd1ac66eccb414c2bdc80ffe9",
        "GROW_FoodWise/Teaching_Packs/index.html": "264b07915612bccd2cb4e1ebbe8519cb7b560b7216ba09e37c5b42a5589d904c",
        "Humanities/Teaching_Packs/DOWNLOADS_MANIFEST.json": "52288be18459aaed5a108ea6bc4e3db6225826b92bebdf38e9c71122597ad156",
        "Humanities/Teaching_Packs/index.html": "7a440ca2a9ae29b1394b8bd20136729044db7347399b9d1f724129d155a520ad",
        "Humanities/Teaching_Packs/SHA256SUMS.txt": "799757748e78233580842920a195d3253042e78e4dee478d64d749f5da00da68",
        "ICT/Teaching_Packs/DOWNLOADS_MANIFEST.json": "6722f2ef668c5f16acd4b55f9bf67fee03aad6eab711224a3d239526f4bba7c2",
        "ICT/Teaching_Packs/GROW/SHA256SUMS.txt": "02524211bea8d374f7d5cc54bc73498165ead4090909147759881f2a468e50ad",
        "ICT/Teaching_Packs/index.html": "4a154278ea7ebf18985fd3d7e9d92bbdf81eb064a87d74189b37bc9e31fb0778",
        "PSHE/Teaching_Packs/DOWNLOADS_MANIFEST.json": "617f2636e9ddee6d1a498e60f7ec21fb0cfe57c58585df12edcc070487a82bca",
        "PSHE/Teaching_Packs/GROW/SHA256SUMS.txt": "98623695f0133b6c0b8ef089d5bcd982e30d7029f1477b1adac54e25bd840973",
        "PSHE/Teaching_Packs/index.html": "7b3c9eeaad68d2c3c4afccc579d6cb8df9bbf6a2e335ea21827315c1dce5548e",
        "tools/verify_fixture_names.mjs": "75417d083048ca425535807d2352163936fc22d18831997b5c2ce05c8e3dbe49",
        "GROW_ASDAN/Autumn2_W1-W6_2026-27/CHECKSUMS.sha256": "711cf723430c8520914327bb9cd8d9276fbb4285185e68792803987cdbca20bd",
        "GROW_ASDAN/Autumn2_W1-W6_2026-27/START_HERE.html": "27bdd6886e7ac0a3cf4c21baa86f3c27fe3e800866693fd8bab38f9857cb0db5",
        "GROW_ASDAN/Autumn2_W1-W6_2026-27/index.html": "27bdd6886e7ac0a3cf4c21baa86f3c27fe3e800866693fd8bab38f9857cb0db5",
        "Art/Build/START_HERE.html": "2e4338516acb7a3d4daa0bf2ae9a8b85f697320535639cef55e391554b007cb3",
        "LAUNCH_ASDAN/W7-W12_2026-27/SHA256SUMS.txt": "2d22a8b2b0c8a39fd5e9a034469826c58593f8064f191b150c441618d53c3582",
        "LAUNCH_ASDAN/W7-W12_2026-27/START_HERE.html": "0339b378fcb15e98689e74415ec4c55e5f3f5fce3372f4306778e4c9921efb98",
        "Art/BUILD_W1-W8_2026-27/BUILD_Art_W11_Light_on_a_dark_page_Classic.html": "e7e3c79ed96158752a9075dcca87263cb6a669afeebcbca99ebf8b7da3c13b47",
        "Art/BUILD_W1-W8_2026-27/BUILD_Art_W1_Explore_Drawing_Colour_And_Technique_To_Show.html": "4766f87e2c5ea4d876dbda34240f952e22003881fe3d7a28e0a55edd8cda9dc1",
        "Art/GROW_W1-W8_2026-27/GROW_Art_W11_Design_a_light_festival_panel_Classic.html": "8258aebbaf88ec8be6a0eba07972b437421a8e7760e4b93aca9260ec57aef5f8",
        "Art/tools/assert_estate.py": "dde499e2e8e9ce8d4e3fa9df7cc7bd4184fb746f4e823e1e568c5dd96e0ab175",
        "Art/tools/assert_print.js": "f383ae89df4c894a374efe56c0358d08f4fe037eab520c0f753e9cd50337e1b6",
        "Art/visual-learning/art-visual-learning.css": "d6d0b23cae7b46467fef98fe04a191ac47f787446cf8097913ae5e637cad8a5b",
        "Art/visual-learning/art-visual-payloads.js": "451b58aba7e17c09372195cf70f484b708c9faa8893cd4c252e882f0a53e894d",
        "BUILD_Estate_v3/Art/index.html": "4a415b437a73b2918034c66318ed4d4fbd7955d6a5342663278c3f12d0d9ae3c",
        "BUILD_Estate_v3/Art/manifest-v3.json": "5be2b169246563d3186e832df20edc076c2cbfccf0ccd99f824f9543b7c1db27",
        "BUILD_Estate_v3/Humanities/index.html": "c44ecaa8f371de403454c2b4145ddb5317186743ca202577f4d535990b57684d",
        "BUILD_Estate_v3/index.html": "302893d70d13f5ed91521614e9bc5f156f3a1fa32a93c32fce0d3cb465de3d1f",
        "Humanities/BUILD_W14-W20_2026-27/BUILD_HUM_W12_A_celebration_in_order_Classic.html": "fb1d424e90bda897a0d774b0341f1145c5a82b62a0a205bc9a7bce9a1f8b4b82",
        "Humanities/BUILD_W14-W20_2026-27/BUILD_HUM_W14_A_fair_chance_to_join_in_Classic.html": "9d9a17320bf574af802f8a96efa4c8e76ced26a3d1bc70c77c369bf1b6847fe1",
        "Humanities/GROW_W9-W14_2026-27/GROW_HUM_W12_Festival_lights_across_places_Classic.html": "4804785bddf3540d80f4df666a2241b010fe0619c8640976a8222c0ddf9e63fc",
        "Humanities/GROW_W9-W14_2026-27/GROW_HUM_W13_Compare_celebrations_with_care_Classic.html": "d846a22e2f5d9f3196907d5b172728e31a53795bb71997811bbe22330a93e82e",
        "Humanities/GROW_W9-W14_2026-27/SHA256SUMS.txt": "7f75f0e7f0884660f2d65ba3b767aa30e80b02730fefb3f9d16b1acd8a95de12",
        "Humanities/GROW_W9-W14_2026-27/START_HERE_GROW_HUMANITIES_W9-W14.html": "c68486b618a6df5156204232bbddcd49284e3e9c5cb053b1dd719b5c4a5c09ef",
        "Humanities/GROW_W9-W14_2026-27/manifest-v3.1.json": "c018845904d7dd76fb7a0946f70f086b6a6f75fe47d9a1464cc3510182fed2fa",
        "Humanities/LAUNCH_W9-W14_2026-27/LAUNCH_HUM_W11_A_growing_town_an_urbanising_region_Classic.html": "fdedaed03f95cf543abdd9d4c025569ce7b3bac52a16f1a17ae85ce733554faa",
        "Humanities/Teaching_Packs/BUILD/SHA256SUMS.txt": "e107c1706170a7738de0739d470903df52d934b8c9d2c14ec1f53429b1956d32",
        "Humanities/Teaching_Packs/BUILD/Teacher_Notes.html": "5db3a99e71dd2a39143292323ec6d165adda320ade20bdb38b0cfe763aa13677",
        "Humanities/Teaching_Packs/GROW/SHA256SUMS.txt": "1ac37fbc8fadb9b05291818c678702cfb8eeead2998469c3b5baba8210af254e",
        "Humanities/Teaching_Packs/GROW/Teacher_Notes.html": "0b37060f6c8637f4a35d79dd46159a22d5f52b9114688825be6c3d3fbceab85f",
        "Humanities/Teaching_Packs/LAUNCH/SHA256SUMS.txt": "4071aac6fd69fb4326d35aaf70a0acbaccdb95ca308a04269a100669de4e76be",
        "Humanities/Teaching_Packs/LAUNCH/Teacher_Notes.html": "05784e354a243b76859c4ebfa7f6a9b0d0b81d89a62f477e0609a6ca665b8063",
        "Humanities/Teaching_Packs/web-slides.html": "b58ebc98e92d6b9f32afee63db8b3a1d0f3006cbabcfe2df115ee2c299238d6c",
        "Launch/Slideshows/LAUNCH_ART_W8_Complete_The_Review.html": "cac083b1fa61722545dd14c4597aa3dcf236b5ed05eb8416d4276b71501406e8",
        "Science/Build/W8-W13_2026-27/SCI_B_W11A_Rock_Permeability_Explore.html": "b308d3ed71d4cca2c7828fd406e50d43d3b5244e56ca58478976f336baecf114",
        "Science/Build/W8-W13_2026-27/SCI_B_W13_Where_did_this_material_come_from_Classic.html": "aade409713fad37b7e3e03297654f6702f45ace803b605c8720b368bc09d063f",
        "Science/Build/v3_40min/manifest-v3.json": "574f45f03d752bb7559494a9033947efce666cf37287c4ffb3db178b9e95a6d4",
        "Science/Grow/v3_40min/SCI_G_W3A_Friction_Explore.html": "f4fc7562eee11ae418568007232622da88eaf56721d93b4563ae53fed791d0a2",
        "Science/Launch/v3_40min/manifest-v3.json": "0db2f244f5160808d7e63365aa2ce82f30b9b9ff425aab357d6089c2b12287ce",
        "Science/Teaching_Packs/BUILD/Teacher_Notes.html": "e56665beb68e8ac8dca6d39f817d785b97c63620d6e24f7c68eea0abaabcd215",
        "Science/Teaching_Packs/GROW/Teacher_Notes.html": "06da774069ab702c62cf35aaf954dc6e5707ff95803c1fc871fc275d4fb8c84d",
        "Science/launch-engine/inject.js": "5bd8266463b277052ca7e9b8a2844c064b1213b04e424bca767e8ac336b52395",
        "Science/launch-engine/test/gate-shape.js": "b9e17c97c0f0a19efb0068595e46de4b62f6f1e2ac2bf0ba06d4ec505732b970",
        "Science/launch-engine/test/health.js": "cc599709a0e2c3c6c517331f99b9f43a4dc3a29d4dc0e3c67cd1c017159dc9d4",
        "Science/launch-engine/test/print-pack.js": "b3bc74a66cb7057dad9d5f3face9ec24028978e5b85ca0bd5d883709e529fc99",
        "Science/visual-learning/science-visual-learning.css": "94cff82726164d7b1ef7315868ff8cb51eae0bf83bcf5590c838f509ee4e1a93",
        "Science/visual-learning/science-visual-payloads.js": "3f607c6cab15c006a5ac5d74821e01f0edd60c2e081fa1bcaad531ff765a16a0",
        "BUILD_ASDAN/Autumn2_W1-W6_2026-27/SHA256SUMS.txt": "211b71462d1e9d0907f7ee6adf1d00c49622ed814fb03eb1c15713e1a3c11a06",
        "BUILD_ASDAN/Autumn2_W1-W6_2026-27/START_HERE_BUILD_ASDAN_AUT2.html": "a319d8f005c7185e5aace0adfa34ceebb9212623bb73719850cbad46deffe7a8",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W03/SCI_BUILD_A2_W03_L1.html": "47198b5c64e835bb50326c6e61f4cd6ff10c6204fef3fb4cdb0f33de207afa22",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W04/SCI_BUILD_A2_W04_L1.html": "30ff99f4ceec2ed2bad2aaadb541ffc052539aff0eb66e56986d99256d9eb556",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W05/SCI_BUILD_A2_W05_L1.html": "a8a6757de71b554698291cca8b10dba50276f4a79fc665c4e06e43f797f9e192",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W06/SCI_BUILD_A2_W06_L1.html": "60e143b2bcee5d104c72dacf06007329d2c13350a6bd9f385ffc843e3bce8904",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W07/SCI_BUILD_A2_W07_L1.html": "189a7a5c6fd2b477c67c874411288dad3ae115b8c3c55f60d6d9dfdcd2ab7648",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W03/GROW_SCI_A2_W03_P1.html": "82c23e53688a6e02714e60d1f144ff7fda4b2653dd698d51960ad21913f2aedb",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W03/GROW_SCI_A2_W03_P2.html": "a5efa1d1e31cb94e4394c34eb97bbb6cbc9a1bdda453365d0c5f0df3abe2c6e9",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W04/GROW_SCI_A2_W04_P1.html": "6040a5f9a27792868b6353888f41d3ffc6f206cb6593601d9e3295cb61fb2b18",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W04/GROW_SCI_A2_W04_P2.html": "54452ff7ea28a3a0cc06a08fec7ede484d0fc9c071afa9826c981c4dc597d19a",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W05/GROW_SCI_A2_W05_P1.html": "648df031ee7d63f1cb2f61d33c74c8be824815fe74655b674e76d374e5d943c3",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W05/GROW_SCI_A2_W05_P2.html": "fe3b2be2d3996b8f9777c38c10883b227e827b094533d595a467abb07b1be346",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W06/GROW_SCI_A2_W06_P1.html": "f0177e264d4353005789cf1c5a98f0a3594581362f6a01825ff98492dd4c7964",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W06/GROW_SCI_A2_W06_P2.html": "f7542f233ebb09fe6dd0fe166a9816f40370a65c07c73a4fec03df6a5adf21b4",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W07/GROW_SCI_A2_W07_P1.html": "99de5b853dac71f056d0b7d46eb7f633cf95b34d602ae5631d424a9eaa76f9bb",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W07/GROW_SCI_A2_W07_P2.html": "25a5bf6e52065452b2ee82977fdcf49fe64d99da48188bc29202f92ffc79a0f3",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W02/SCI_LAUNCH_A2_W02_L1.html": "ce26617e0cb72760aa3a46cf2acbff7602062c3bff47f724c249fbd0f4de11a7",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W03/SCI_LAUNCH_A2_W03_L1.html": "f69417267d93fa078e6da47eec404cd25b4f0f8641d14cd75b56478f57188176",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W04/SCI_LAUNCH_A2_W04_L1.html": "af57b1ae86fea4f5582673482d002cf6c3805d4f9a56d51835e98453980c2b14",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W04/SCI_LAUNCH_A2_W04_L3.html": "87ea2c04c4211f29bd60cd7613380e6482345af997b0e3b8130271b0670e6967",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W05/SCI_LAUNCH_A2_W05_L1.html": "3bdb8a449e786ddf84ad0b72cfedccda408c84564bf207fd69e0026bcc0e85e2",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W05/SCI_LAUNCH_A2_W05_L2.html": "c797fa56ad692102162ac27185c4dd10a168b79f709faa7ea25ac57d995f1deb",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W05/SCI_LAUNCH_A2_W05_L3.html": "f2e98a18729eadda38e47c38c8ab22377b9c203091b78b8006eaa31415182f39",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W06/SCI_LAUNCH_A2_W06_L1.html": "5cc24a50efeb72870cd2b423038d4207373e06e0340c440e0ac201d637b7e17a",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W06/SCI_LAUNCH_A2_W06_L2.html": "7e3a55bdfb2f8f07a333fc0c49a29b9bc9eb5bb8f4f516865d1ebeb24e7ef16b",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W06/SCI_LAUNCH_A2_W06_L3.html": "0387309b3595ca299627d626c99584c0844c924408e336026db6aa74f2f95e10",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W07/SCI_LAUNCH_A2_W07_L1.html": "80e1539df3806aeb4ccc532642966e95519af50f8bb1ab3c47ed8ab8681be404",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W07/SCI_LAUNCH_A2_W07_L2.html": "6a9c14d38f571ce82f9036fd19537f1bb572195ce8821f55e992620c1b0e6545",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W07/SCI_LAUNCH_A2_W07_L3.html": "f3dea73d8d5a42eb869e71dec13b4704ed5ed59533e509b12b782d1cf5f6ba83",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W07/SCI_LAUNCH_A2_W07_L3_Pupil_Checkpoint.html": "1b808f8225ddd5b872227223fe044964dbc5ce05dbc21a41576bf5c33d09a87e",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W01/SCI_BUILD_A2_W01_L1.html": "821baf58d7f4f9bcb9429a85363953a640f3259b49e81dbba95923f5701ebfa5",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W02/SCI_BUILD_A2_W02_L1.html": "97f4d4d821849a562fd2aacb46d7f6036cd59409ecf7fb0014591825a3e7c0ce",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W02/SCI_BUILD_A2_W02_L2.html": "5fb3ecf2562e20513cce0cb09ae32e33deb52d72ff3738b30d365145cd662286",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W03/SCI_BUILD_A2_W03_L2.html": "c1fbb419a7f922ba96b4eacde22ccb004f431e49d888e1fb201b12c973e5bce5",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W04/SCI_BUILD_A2_W04_L2.html": "e072faaaa805e50895b7f618599c4aa40742480a1087d1a34f3940ce3a56df30",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W05/SCI_BUILD_A2_W05_L2.html": "bf45dcc5fdd98eb4b99701562d4b6b43b6b09187e03111813e534b946ff0c75b",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W06/SCI_BUILD_A2_W06_L2.html": "f3b5c9494d4fe986db5c3f07006a3b4d17c29b842d28d612e3fcef4143bcc644",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W07/SCI_BUILD_A2_W07_L2.html": "e2a950462459fd242cf0ef25ca647664f05cc74b9fc20d8395a3cc69a245efd5",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W01/GROW_SCI_A2_W01_P1.html": "ca038585e48cc0ec3a33d632ad6ed641ffe5576adcb81ea1f3568eb34460e4cf",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W01/GROW_SCI_A2_W01_P2.html": "06a38561bde50df3e84a242eb7b56e9a77d5d647a33b1c3e122f45a1aa24656b",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W02/GROW_SCI_A2_W02_P1.html": "fd943ad2a2a321ac42700c197b2e8cf0c548bc6dd532e5089fca7cb3cc628b4f",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W02/GROW_SCI_A2_W02_P2.html": "f3bd7d869345d75080080ccfd2c214ae7b374945f7f0b2ecad97817779be6efd",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W01/SCI_LAUNCH_A2_W01_L1.html": "0b262ec1eaf4b8c6c488a4340608b8ef5f8c091101514f5d0fe81b18dc705f8f",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W01/SCI_LAUNCH_A2_W01_L2.html": "a9820f81c66481480167e39d21c8cf30454f78452365f91cea3f15fcef9744c2",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W01/SCI_LAUNCH_A2_W01_L3.html": "61fc58cabecd3732212ab08247686208919c147f671fbebe58be52cc4d36c824",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W02/SCI_LAUNCH_A2_W02_L2.html": "dc5bf336077c0525e1b241eb20ee5fb02e19801bafb7e309eb7962df1d82a2b2",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W02/SCI_LAUNCH_A2_W02_L3.html": "3ab45d11e5588314900a3e10d182825328d6126a6d796626ddee1bc58aa37d7e",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W03/SCI_LAUNCH_A2_W03_L2.html": "786f750baaf5aec13b50034d5cc5788d3a1381f2df013a986807e8611393958d",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W03/SCI_LAUNCH_A2_W03_L3.html": "0e06110a085cef2042c04c5c22683e79a7f8b1aeaad44dc023f0896a57682141",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W04/SCI_LAUNCH_A2_W04_L2.html": "d4ff25699a01a8f3ab38def7a1bd8a520984262e6678b05041377570f3ea5cf4",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/HUM_BUILD_A2_W01.html": "738a087a9555357d9eb0f7d897a8d1ea3e19c3213b1fe0400f0891c65ac494cd",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/HUM_GROW_A2_W01.html": "859ab32641e4b05e8a0be1caced59f4ca0d73d804855ebbe4cbeac6f0b38cf7f",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/HUM_LAUNCH_A2_W01.html": "d11f5f045d336ad5dedff90e4a2782712130df057b51af52601163ffb7338633",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/HUM_BUILD_A2_W02.html": "00805ad0f8edcd333324d03ae4ecbd6b15c3fc6b5fb6e52189855040066cb451",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/HUM_BUILD_A2_W02_Editable_Pack.docx": "25275fbabaee49be06c5ce561df476afd5da33ebdea6a58deb2f0d4b1e081f26",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/HUM_BUILD_A2_W02_Knowledge_Organiser.pdf": "1a588d1687c83c2b90bf3540602c15d5ec815056c6f845275e122956e60e37c1",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/HUM_BUILD_A2_W02_Pupil_Resources.pdf": "ac1d0913ee0a0420c119579c1e52127dbead1e00f69b6d5a1841fd59a13c5fc7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/HUM_BUILD_A2_W02_Slides.pptx": "c44367790ec4f45e599ba4018b993b42fd075ef1b94fdfbff6ea4d467fbdc684",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/HUM_BUILD_A2_W02_Staff_Answers.pdf": "994f4ca889b023b93443f91b6489534af97a1df42af2b6ec68fe4b8ff603bfa5",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/HUM_BUILD_A2_W02_Teacher_and_Cover_Plan.pdf": "c1e21da7379f652d1540444a504a7c21ddea57b9a1fe987caff710e0fa5ca254",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/HUM_BUILD_A2_W02_Tier_Pack_Standard.pdf": "f4ab6f1f9332b7b23a6c0a51fd9bf18aaed1ae71efe98185322154c7352e6105",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/HUM_BUILD_A2_W02_Tier_Pack_Stretch.pdf": "be2f29ce6bc471461f7ded62e43ab49a9f6e53f059ddfa0a1d6afe8f0b782eb0",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W02/HUM_BUILD_A2_W02_Tier_Pack_Supported.pdf": "5442f7549e0bc347c0b554d5d69f5ad3513f68816153061d1c3217a47faf0371",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/HUM_BUILD_A2_W03.html": "57b79af4cdab37558dd51da008b290ca19e464ef60d2cbd63674f0ba8d81928d",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/HUM_BUILD_A2_W03_Editable_Pack.docx": "417e5bb5c93a98cba9b43656707a721515b1157593ab5cf728164d17c682fb49",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/HUM_BUILD_A2_W03_Knowledge_Organiser.pdf": "2757623c185e0cbb467542238acd8424bb7b96a65f5e7e1694fc140a36785bac",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/HUM_BUILD_A2_W03_Pupil_Resources.pdf": "007ba940ed1d2690b2b47ec1fc73b8240cf5493336d41a46b2dc56574ba0644a",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/HUM_BUILD_A2_W03_Slides.pptx": "b88d0f0a6dfadfb4143ebdaf1e2aca6fe05d1edce78ab8e8bd3cfaed5cf3b767",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/HUM_BUILD_A2_W03_Staff_Answers.pdf": "d02089563d2a13778378c0b03110d3af47b3fe3918c84bfb9ec3f1c6d0b03fbc",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/HUM_BUILD_A2_W03_Teacher_and_Cover_Plan.pdf": "a2f86cab5262d7f60f1604e2834271a81c44e3573fb93c4c0aca06393dcb05e7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/HUM_BUILD_A2_W03_Tier_Pack_Standard.pdf": "ab1bab710e6d1f31d99ca4e794c86a31c1aff7ad38de3410f76481ecd97595b5",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/HUM_BUILD_A2_W03_Tier_Pack_Stretch.pdf": "a2272c9d7f59235f09eaf6340e5874f2c9035c0821ba7ed1dc68fce10156eb46",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W03/HUM_BUILD_A2_W03_Tier_Pack_Supported.pdf": "574943d5ca7f92bc86c66a7d2f39b28d0323b6b7c213ef68b3bfc3efac95104d",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/HUM_BUILD_A2_W04.html": "5b7cc210b6dfec7c50567b54e2e337b18f64e2f559e3059387bea1cec30d6009",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/HUM_BUILD_A2_W04_Editable_Pack.docx": "fbeedf1282226bb4cc7ede7a23ab45fe3a4e769f9dfce23a314adeb1834c8194",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/HUM_BUILD_A2_W04_Knowledge_Organiser.pdf": "af6ae45290ff01bd3e2fb9817759c67a9d66866eb3de5adf5f6a5b42c6d060d7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/HUM_BUILD_A2_W04_Pupil_Resources.pdf": "91ea967ee7e1fd20a486c32ab7cacc93f29d3b273bec5dd98fa2fc0d5f00df5b",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/HUM_BUILD_A2_W04_Slides.pptx": "128d6ce4b3032f5adc46992746e99be79d0b3895c98a88b3b65ebf60ec5899e6",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/HUM_BUILD_A2_W04_Staff_Answers.pdf": "81bd7f636811d3a26ad4059c543b76a738d23b781b9607ea7e54769f35a232c5",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/HUM_BUILD_A2_W04_Teacher_and_Cover_Plan.pdf": "3803ef562160904595e8347e51607b8b39ea01103b4b4d132a117203db8ef189",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/HUM_BUILD_A2_W04_Tier_Pack_Standard.pdf": "cba3873a1319e80adeb59c0994cf6e5380976ca8dae94d796429a9b01f388137",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/HUM_BUILD_A2_W04_Tier_Pack_Stretch.pdf": "60da169e79b56f869f1d1ed8f9d52f563995ab65610a6adc408eba40621321c8",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W04/HUM_BUILD_A2_W04_Tier_Pack_Supported.pdf": "dba7a7742007230772305b2875c0518f0cdb8912b157cfdf7de025788cd2b706",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/HUM_BUILD_A2_W05.html": "a0fccc9221c92f82b1b5ae0aae8381afcb77ed6c4a6c4ae349c01fcfce1386e9",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/HUM_BUILD_A2_W05_Editable_Pack.docx": "6e22489c0ddaac69cc6d55b1b44d78d7f92beee35b15721834c5c587053fbb0b",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/HUM_BUILD_A2_W05_Knowledge_Organiser.pdf": "e28d87b0980a214bfb1dbceae79a1eb8a20a9e85033ffb9ffd1e6f932400c035",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/HUM_BUILD_A2_W05_Pupil_Resources.pdf": "b54f6c964be74ad6c9120369b79be6e5c1da7d9429e8fb6764d6527c20f0b17b",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/HUM_BUILD_A2_W05_Slides.pptx": "b1afb7c993d93e5175af0fb7177c5e105e17412b1641881404fca377caefce46",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/HUM_BUILD_A2_W05_Staff_Answers.pdf": "307f7576797f7c96707792844e633f8601b57f7af50a36d593bcbf07d096c4f4",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/HUM_BUILD_A2_W05_Teacher_and_Cover_Plan.pdf": "af5d4495bca5bc9ee18dc2e92b78ee1a53443673e75fb5a446a5b9c4377c7bd3",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/HUM_BUILD_A2_W05_Tier_Pack_Standard.pdf": "ffebabe65cfd7e5ad23f3e5dc25f5181793411734675bc754ae61a6a55a41b32",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/HUM_BUILD_A2_W05_Tier_Pack_Stretch.pdf": "b2b4abe5a9a8e84df0aab1b25ae05029891a04b429164c8212ff934f45d9a5ad",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W05/HUM_BUILD_A2_W05_Tier_Pack_Supported.pdf": "e50d6f1d0ca116293df770c5e33691d188c7303fbd301c18aa435a4bba4c4241",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/HUM_BUILD_A2_W06.html": "0d372959667754e71064d1f555e6f70dd59a3fbece5cec758678f9bcf2e7e9bc",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/HUM_BUILD_A2_W06_Editable_Pack.docx": "7fedf1c408ae36bb55b1c384f1c72486465a39a060857ca01ad6ec2d4f6aa100",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/HUM_BUILD_A2_W06_Knowledge_Organiser.pdf": "c534072e46e0797550ebe8577cc4033cd195ce2e767754e870025edb38a01399",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/HUM_BUILD_A2_W06_Pupil_Resources.pdf": "7d6f6340a982ec4561eda7b96c6c8e3a16e661b27d941d2f5cc51ca0fca5cda5",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/HUM_BUILD_A2_W06_Slides.pptx": "54d33d2ed1c55d93a0611be9fa8f4a901825309de42645e22ad7ca0f43eadf5e",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/HUM_BUILD_A2_W06_Staff_Answers.pdf": "988bc157512dcfba38f9b0982ea8114658cc46409d57fd98a91048970ce3686a",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/HUM_BUILD_A2_W06_Teacher_and_Cover_Plan.pdf": "b0b5460da5ad1a5ad131ff71ad302448e33ed0be2efb8643d0645be225b7f3d1",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/HUM_BUILD_A2_W06_Tier_Pack_Standard.pdf": "c22571df7bac2acfb94b0ca49b35f02b86fa1a140774d465f2373ca190a659cf",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/HUM_BUILD_A2_W06_Tier_Pack_Stretch.pdf": "2a7502d6e786a3d7c7701abc5431316e17aa823374aa076145f02895255cfdfa",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W06/HUM_BUILD_A2_W06_Tier_Pack_Supported.pdf": "73f2844535c40d96c010c4e3538acd573f727364184c90861d06180ccd27e7ba",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/HUM_BUILD_A2_W07.html": "a0e63204ffedfc570739927a60201e434083be154c8ab981ab97ab25df9f9ca0",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/HUM_BUILD_A2_W07_Editable_Pack.docx": "c1259bd8285aa61af8be63ff341c0dba699d86d66e2500d4fad0dd9e0732dffe",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/HUM_BUILD_A2_W07_Knowledge_Organiser.pdf": "e474bfa2a8d4aa2d5943ebaed1f68d622af4eed6fab6f5adc20b72bed20d0e5a",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/HUM_BUILD_A2_W07_Pupil_Resources.pdf": "cf142284275cc0405673533fe81acf7674d64af91b9dd647e3f945503f716508",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/HUM_BUILD_A2_W07_Slides.pptx": "adbface8e4e6b08cf4e756ae0cfbc03e90e7ba90cab1c8a335ef0f32fad9f89e",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/HUM_BUILD_A2_W07_Staff_Answers.pdf": "7bbea8cae583eb34b386dd84b8e7ab3efdd71453f650f386403c828156a96b10",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/HUM_BUILD_A2_W07_Teacher_and_Cover_Plan.pdf": "990d04e24b32389d4850fb161b05389f2cd528a1d4fc83907d5531b80ebe9385",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/HUM_BUILD_A2_W07_Tier_Pack_Standard.pdf": "b0c206fc688aff6406a4505130901c256bd13ebaea390a12af585ddb2d8dd5da",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/HUM_BUILD_A2_W07_Tier_Pack_Stretch.pdf": "fb8cb7caa6201e5f724b1747255904260d33a425225a41737ccc3faa8de5389b",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W07/HUM_BUILD_A2_W07_Tier_Pack_Supported.pdf": "22e1e02ac6132927a4de30fd45096c356e4e626ccc6cf5f709f2981a7d7fcff1",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/HUM_GROW_A2_W02.html": "dbd1f43fff62dffb311206ff0c28e065ea6a96e0e7e159b94b8e1cfa72143daa",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/HUM_GROW_A2_W02_Editable_Pack.docx": "9c8616028d396dd381dd40cb5f2ed5caa31d5cdff60cb5ac571ca54d840ac2a8",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/HUM_GROW_A2_W02_Knowledge_Organiser.pdf": "e11d894fb0710de8200f397c1e3bba139438e0b4142380d89010390efad8ef78",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/HUM_GROW_A2_W02_Pupil_Resources.pdf": "04e65335ee2aff5b053a2e5a5c53baa392e8e214b6e23ef5448103d6ad60854b",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/HUM_GROW_A2_W02_Slides.pptx": "10b1dee0ad7765961bc9bd9659343dbbcd4f739472ae9e5dd36368bd54a8a821",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/HUM_GROW_A2_W02_Staff_Answers.pdf": "5d17f62d1bb6287fd0045bfd342ffa89f209fb640af476f2b5d8ec028599b2c0",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/HUM_GROW_A2_W02_Teacher_and_Cover_Plan.pdf": "a49a255260cc3a1d13a5d6ad395486e3e63d03a77fdc1a80a5a5787217b0df0f",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/HUM_GROW_A2_W02_Tier_Pack_Standard.pdf": "0854a64b2a71d9053b1d1276d0fdbb2d135f3502326731a3c1ffe5ca0dc5e53a",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/HUM_GROW_A2_W02_Tier_Pack_Stretch.pdf": "8f971905d3fe51819b18001107b5768f5a31d459986c7484a8a80de9fa60e2d8",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/HUM_GROW_A2_W02_Tier_Pack_Supported.pdf": "1a25730fce8c40d4644d600b2fc1f6b644ba86d04b60905649fc66b2266c9f0e",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/HUM_GROW_A2_W03.html": "0e777d5241365c393fce84bb8bed0b65509d648cb0eef5e38bff5c0ead1b8f89",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/HUM_GROW_A2_W03_Editable_Pack.docx": "a38abc17f142199a06150600624acc47c692d12be5a53399bcb82e23037f7cd3",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/HUM_GROW_A2_W03_Knowledge_Organiser.pdf": "4290aedee7861c580abd7cd7c8341360b4eda4cf721356f29f911d88735f4fb2",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/HUM_GROW_A2_W03_Pupil_Resources.pdf": "de040b572b0312015ff4e958eb55ee9b895c922536450cc749e7fe7c18e324dd",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/HUM_GROW_A2_W03_Slides.pptx": "aed0952e1dc2817c500e622b20c88be74a63dc198273ea0d4303f586004a6416",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/HUM_GROW_A2_W03_Staff_Answers.pdf": "805a8260643d2ce71733ad2379fc3c534021d1d1bb8d581d3385fe6858e20f6b",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/HUM_GROW_A2_W03_Teacher_and_Cover_Plan.pdf": "7134461a840ad3f204c5b17909a8435d62af0181f7f505f44438514b611e8792",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/HUM_GROW_A2_W03_Tier_Pack_Standard.pdf": "07f7d96fd1e626e82448302ad2c25d3f664c07534dec0180d336bfb02366ca51",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/HUM_GROW_A2_W03_Tier_Pack_Stretch.pdf": "4f67abe0bb98b7ce08104bb2583d6035be95dc6c6d34d2dbb61d7670f3f7b241",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/HUM_GROW_A2_W03_Tier_Pack_Supported.pdf": "dd941855a94279a977295fc076edef5e6c0c3d3e44745cff9da192bf8623b4bd",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/HUM_GROW_A2_W04.html": "9b375af4036fcc317c66733cd4d29d1ae72b962268c788c942a3928da3d8ebad",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/HUM_GROW_A2_W04_Editable_Pack.docx": "1ad762e1b0fe73152a74fa4fb9097872fe934ce4619954b9f6c9df52fe96b490",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/HUM_GROW_A2_W04_Knowledge_Organiser.pdf": "9d4fac3e4f5c1dd1099168aa5f96c1742facbb20a68c3a257b979f69a3b1c5fa",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/HUM_GROW_A2_W04_Pupil_Resources.pdf": "0c066d3134ea93bbf40edb020d8b7cda76e7f5b3f546eebd5062865b15ebf510",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/HUM_GROW_A2_W04_Slides.pptx": "0648d91009b519a1afcbe4a2d774ce1274f7e071fb2333438949c8fbd37374d4",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/HUM_GROW_A2_W04_Staff_Answers.pdf": "51efeaa1bf7bc07b1b383bddf850f0b84a44231376dc3585a56a1b3812aed788",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/HUM_GROW_A2_W04_Teacher_and_Cover_Plan.pdf": "98dcbc099a3cf76b797157220bf3b604170c138094c0d746807dac3efffce78b",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/HUM_GROW_A2_W04_Tier_Pack_Standard.pdf": "bf1065fa9faaaeeede647f18aa5e78d60336f33c5419ba96f4e53ea656ff9686",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/HUM_GROW_A2_W04_Tier_Pack_Stretch.pdf": "79395dbf5f04aa4b8899c32df39497a7e14f0895c24c107d6531fe6be69931a5",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/HUM_GROW_A2_W04_Tier_Pack_Supported.pdf": "84467ec1a5db90ece90164bad3a40bc9f43c1ad2d2ff1680725e1b15895c219e",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/HUM_GROW_A2_W05.html": "c29c928de6f959359a903be09f8b4620a825b73abc6db2b4f7e1d3c14fbdc2da",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/HUM_GROW_A2_W05_Editable_Pack.docx": "615b3bc588278fe048633b824fc6e2ecce796df4878becc21badd85d20be3132",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/HUM_GROW_A2_W05_Knowledge_Organiser.pdf": "5a504a94098248e635f38420ec580ea9f50d3c5c96aa8f54deff73972a006c08",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/HUM_GROW_A2_W05_Pupil_Resources.pdf": "adc33a9f1c0b52694fbf14773658de95e50389596a8ea5da2e5a628e7d582fff",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/HUM_GROW_A2_W05_Slides.pptx": "a1dbc75045d9a7ceee47b02ba6f1d9d2de84e20dfe95a4f705a30ab76a9d7085",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/HUM_GROW_A2_W05_Staff_Answers.pdf": "ebb63fe75522ba1cf9ab87ceeee5b5dc6be638b6083f8b4e2299b12b6d8c810c",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/HUM_GROW_A2_W05_Teacher_and_Cover_Plan.pdf": "e908162a4bcbabda3b5fe0311f286ae8f67e485b67d1372f5c103e90ff73d79a",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/HUM_GROW_A2_W05_Tier_Pack_Standard.pdf": "059d5fe27bf0e5b50a880a5e58988eef7df3b7b604db1c9b8cbab8096b93426d",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/HUM_GROW_A2_W05_Tier_Pack_Stretch.pdf": "45f8bf19bc42495ce9b5900e9a4424c28463bc1cd5692631c00fd0c1fe37d10d",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/HUM_GROW_A2_W05_Tier_Pack_Supported.pdf": "a968ed41d120ca7b8880ad1cba1eb3be040dd27d9458b7f3aacf597d2a7aaeef",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/HUM_GROW_A2_W06.html": "c71b0ef8617bcd3b0292b7aa6ff88b25a47bdaecf4779e3151b9c9e0aa61a950",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/HUM_GROW_A2_W06_Editable_Pack.docx": "7d92c8545391b9515421a9ed387bed22f24b04f66ba220159099bbc185a5d945",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/HUM_GROW_A2_W06_Knowledge_Organiser.pdf": "1580dad06aa84b3d83fc10e3b9acac3c1d2a20a4f1aff42a2aca61468bdef426",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/HUM_GROW_A2_W06_Pupil_Resources.pdf": "7c791a345e990d53007aae6934a3adf2ae1ff1b721b7bba16ca8f4fbfc8ea5c0",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/HUM_GROW_A2_W06_Slides.pptx": "d8683f0c3fcce1bd0a6a9396a0871ed84cdb8fd4d078bd82c68c4b980b61a7b2",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/HUM_GROW_A2_W06_Staff_Answers.pdf": "0b6f22e5a6ab60b5513623f62c16ccc21fc8ea399f72a9ae6049e3210a8081aa",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/HUM_GROW_A2_W06_Teacher_and_Cover_Plan.pdf": "9b682036718789d26eefab3c502dd2488924bbbe044dc92cdfd79dd0c2164acd",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/HUM_GROW_A2_W06_Tier_Pack_Standard.pdf": "854b10b92ddddd6f43033244d014f5e114e59326693bd17488ed52feffccf6a3",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/HUM_GROW_A2_W06_Tier_Pack_Stretch.pdf": "160b3c5a0b60e4876bb8ddeb2fa0c13df4790de860c67f9e2e2930d528952adb",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/HUM_GROW_A2_W06_Tier_Pack_Supported.pdf": "2399e8ae9cd9573ec9273acd876d6d086cb59e13a90e1a04de8ee6f87b662823",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/HUM_GROW_A2_W07.html": "bf4c9273ea7cf04dfb5491461413917b8120d9e4f099f9539030f65c925cda4d",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/HUM_GROW_A2_W07_Editable_Pack.docx": "413b2ef7d1f76ce64911ea49156d069adeff913136a137b5abba7850cc80fd2b",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/HUM_GROW_A2_W07_Knowledge_Organiser.pdf": "5fe435fed4b5c8b6070647f661589157b353192477b2aed18799bf17e0995bf9",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/HUM_GROW_A2_W07_Pupil_Resources.pdf": "27bed92589c1ae013cef16ddba3832a504b3bb4eed23c1afe0385bc99ffe332f",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/HUM_GROW_A2_W07_Slides.pptx": "47d5a53077eececb99994c478cdf28835daa4fd589744d5960639edb60538bab",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/HUM_GROW_A2_W07_Staff_Answers.pdf": "7b6620d6566d60c89aa9da3d37c79bbd4504b25083bf945c5e04d1fe236f2fdf",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/HUM_GROW_A2_W07_Teacher_and_Cover_Plan.pdf": "4ed7450d59a8d3577b63effffa1fef7330edce775d6f7cc0e00b097465655619",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/HUM_GROW_A2_W07_Tier_Pack_Standard.pdf": "f79955dfe35d660a6e23ea91744d59057f27f8cd6c1e3cc79d8436a5bf79f34f",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/HUM_GROW_A2_W07_Tier_Pack_Stretch.pdf": "253b98da642d3ce644ba2331922f1ae79d531afe602ca53666ea5dca79915ec9",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/HUM_GROW_A2_W07_Tier_Pack_Supported.pdf": "5860bdccee1045b0bd97b2607f6eb4e8eb8a14d250fff1302db3578ae303d8ee",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/HUM_LAUNCH_A2_W02.html": "a45e8cee2cba1a8e95cdcc600832d350726b71cccd96ee35e391b875bbf3e4c8",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/HUM_LAUNCH_A2_W02_Editable_Pack.docx": "fc85f9d4bc6f2c88904eecfe699175086fb4beeca53b65e2f9bb26b1855d9386",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/HUM_LAUNCH_A2_W02_Knowledge_Organiser.pdf": "a5b5812ccc5c5f8cc8eb7da3f676d60dd67180126be06e2bf8d07f09a472afb0",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/HUM_LAUNCH_A2_W02_Pupil_Resources.pdf": "7e64b26407a6c27e8fc85639b50e636d8ad4ff5b830341256f4fa23e65bb8ad2",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/HUM_LAUNCH_A2_W02_Slides.pptx": "63fe9f28c57104aa8ea64b1597ab133a23e12f081ec694fe0947ccfd54d2b90c",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/HUM_LAUNCH_A2_W02_Staff_Answers.pdf": "396ad321d3b5dcea3a4dd4e595536a3b9629afc423fd033f5029b467bb626b65",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/HUM_LAUNCH_A2_W02_Teacher_and_Cover_Plan.pdf": "c1133979a723100b1be59f41b9748bb539393090dd524d71ec8616dcb6967369",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/HUM_LAUNCH_A2_W02_Tier_Pack_Standard.pdf": "a3b1b3493d3b0e7c9ab8db91026ce80476c042c4cef1bdce10043f8c12b059c0",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/HUM_LAUNCH_A2_W02_Tier_Pack_Stretch.pdf": "ead459515eec27b7f739886db5db232899638c8649783ee55e3ebd28d7f4bcee",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/HUM_LAUNCH_A2_W02_Tier_Pack_Supported.pdf": "59380e958dccf13a601b4c5e454b36b3a7be4a0454d4c9ca0db742e20a314cc2",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/HUM_LAUNCH_A2_W03.html": "5d708c33219c850d4fa71dc733fa9d3d0495dbcdb4ece3d1d85cc4ce104e9e9d",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/HUM_LAUNCH_A2_W03_Editable_Pack.docx": "fe5b41d283a1efcc1a1847275522271dd95479d3a3e2bce7ea44b756bd607879",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/HUM_LAUNCH_A2_W03_Knowledge_Organiser.pdf": "c602f08e228d8eff8eb313d3bb84858e0d524aae6788564f9f7343c1130a7670",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/HUM_LAUNCH_A2_W03_Pupil_Resources.pdf": "545ef471dcf04a8cede458c6188d809f8eb713965e2642ddccf1b4c6da329c91",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/HUM_LAUNCH_A2_W03_Slides.pptx": "3e27a98dcc95de12d74fc8073b77e0b3e02ac696fe2709b25d500340f9f534fe",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/HUM_LAUNCH_A2_W03_Staff_Answers.pdf": "7da978d532e67ad36b8c255a293fe62b12a13f2adb4cd1ae575dfd78c74a1eff",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/HUM_LAUNCH_A2_W03_Teacher_and_Cover_Plan.pdf": "a890515cc21b3fcf58b88b6579a0735e5c8a85cbc4c5263dc42b9ad31dbeeedc",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/HUM_LAUNCH_A2_W03_Tier_Pack_Standard.pdf": "7e1e70b49493183c877c53d5e72c27af9f451d02b795a5619718670ea4eb9ca5",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/HUM_LAUNCH_A2_W03_Tier_Pack_Stretch.pdf": "347d427004dec75ac8cc3ede0b5ed3c2183e88436b9057d288f9a99e3ced26f8",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/HUM_LAUNCH_A2_W03_Tier_Pack_Supported.pdf": "1c15fb3c294a9c65fa6761218e49f2d55cd39294631deee3e73a43e3418be0a5",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/HUM_LAUNCH_A2_W04.html": "79a0c6c7508c3695aa518d4c3a1bba4ac56817ca3b9162214a00f557389b512c",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/HUM_LAUNCH_A2_W04_Editable_Pack.docx": "f2b65d3605f8b0663073f6765dfa495667e4d663b96f83bf5b6979f0ddeb1a42",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/HUM_LAUNCH_A2_W04_Knowledge_Organiser.pdf": "82540f13491de2d1b4110bb4ac2ccab00aa689d71bfd7d9dccad600584ee69ac",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/HUM_LAUNCH_A2_W04_Pupil_Resources.pdf": "4b331a9afb0e2f7919629a82f5aa09e6bada40a0b538dd9f7c7debac72351113",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/HUM_LAUNCH_A2_W04_Slides.pptx": "7b05eb35250627f6e510ff8c54d1adbcc2b5a53b0c4825e6074eccab7b8e19b5",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/HUM_LAUNCH_A2_W04_Staff_Answers.pdf": "ff00a672eaf9a29dd3edea152d17affd7f406c82b54701d8107b26cf279c92a8",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/HUM_LAUNCH_A2_W04_Teacher_and_Cover_Plan.pdf": "d6923b203be0d3d665dd470e4995d3e09dc5578bc7b7102fc319d2833c17d0b7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/HUM_LAUNCH_A2_W04_Tier_Pack_Standard.pdf": "efbdabc4517d8d3a6f86cdcd9c04d9d77ac18b40c0db6ff13c6491a16c879793",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/HUM_LAUNCH_A2_W04_Tier_Pack_Stretch.pdf": "da13c399711ca7087ed55fe3a75309f46b43b4a7c01ddafa2a51c96625ddb0ab",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/HUM_LAUNCH_A2_W04_Tier_Pack_Supported.pdf": "eaa71eb43d0eab1e49210365782bfd99f76628f9d551e67a8581b6200207e485",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/HUM_LAUNCH_A2_W05.html": "022f6c24ce7704ae0966f22c669c9503f1a6fbc0d552096f6ba807fbee1e325a",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/HUM_LAUNCH_A2_W05_Editable_Pack.docx": "4f684a856eea8433054e132f908ad9ea92ff0654f0820378087106d54b43ede3",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/HUM_LAUNCH_A2_W05_Knowledge_Organiser.pdf": "6c3cb861d54caedf96f43ef7703aec2776d427e48eb28b9a316a2547fe748dad",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/HUM_LAUNCH_A2_W05_Pupil_Resources.pdf": "bf37b4023df8060306c5b5516d2ae26aa36357f3fe3b8635f4df56b3331cf51f",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/HUM_LAUNCH_A2_W05_Slides.pptx": "a6acc289661d2e67edc827669bdbed3f452e45843a9b497944e4c558f27f053f",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/HUM_LAUNCH_A2_W05_Staff_Answers.pdf": "c85b94a967f64a52f7802d6100ee42b749dbd935da6b2a34f009684b2b945751",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/HUM_LAUNCH_A2_W05_Teacher_and_Cover_Plan.pdf": "8de8c472ea091db8f54136650a218fb5c4af72d0aab272e08b3a8689a1a265ef",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/HUM_LAUNCH_A2_W05_Tier_Pack_Standard.pdf": "212c01dcf75b893493dcb3638592217f2a1a142e00c9e40489f6b72dc2cd8479",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/HUM_LAUNCH_A2_W05_Tier_Pack_Stretch.pdf": "a9941eed1d6c3f22de8ea5a35e850ef50819b21792fe00a1af490d77cb9d007c",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/HUM_LAUNCH_A2_W05_Tier_Pack_Supported.pdf": "ab4d98ce72910afdb09a6ed035e5f962c96fb725661ac62a44094182fcf43071",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/HUM_LAUNCH_A2_W06.html": "1cf3f4cea393cc749de8bba039ab43a032b48a5474e209a7c2718e3279b49f37",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/HUM_LAUNCH_A2_W06_Editable_Pack.docx": "29e24eb8d0ed5962fb5c1ba9bca04de501d83dafa47f48ee773534ced2242700",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/HUM_LAUNCH_A2_W06_Knowledge_Organiser.pdf": "bb21d222f5c853ee950ee3d1d0a0e9aba651ebcdc3dd01eb8a36018268f1a4cd",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/HUM_LAUNCH_A2_W06_Pupil_Resources.pdf": "c2db57709f5f9b478650aea00b50e394f2e93de5831098c9fe7f550a796d763a",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/HUM_LAUNCH_A2_W06_Slides.pptx": "f90534532f30797d47f9b6f4764b8f9676962850c959807b89a8aacc13ba7a9c",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/HUM_LAUNCH_A2_W06_Staff_Answers.pdf": "307e2ca388f129461607332e69a2db00d5e66651b2eacec2567d8907a7009d06",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/HUM_LAUNCH_A2_W06_Teacher_and_Cover_Plan.pdf": "e2c2405c94ae01f893f2a42517f8ef964d32b96ce785f1012063d85bb2e10cf7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/HUM_LAUNCH_A2_W06_Tier_Pack_Standard.pdf": "9eed60f28e9434cfa7c2152771277ebffba79ed203c34843a41957e686b087cd",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/HUM_LAUNCH_A2_W06_Tier_Pack_Stretch.pdf": "7ab2c4cbbf2f1958f5a07288e0657a230b225a9ddebacf0dea9a475a4a0c8ee5",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/HUM_LAUNCH_A2_W06_Tier_Pack_Supported.pdf": "53b4c0dc600a2c4ddb15830d44b2b47a049dc891f3b67b72c3a15e14569f0b29",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/HUM_LAUNCH_A2_W07.html": "8fff75d2cb32d6e8555686c46906e6dad71befff19b5b49023517a07f26b83cb",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/HUM_LAUNCH_A2_W07_Editable_Pack.docx": "ef57e0f91cfac31474f0ed7433e8c1161da466efe1a53ecece37c490eeac7edb",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/HUM_LAUNCH_A2_W07_Knowledge_Organiser.pdf": "abebeed33b5a9fb963f1e90512801963aef892ced75d2e87b317e894b747ce14",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/HUM_LAUNCH_A2_W07_Pupil_Resources.pdf": "9a0934bc29b0ba2838b4fda3f0d8fbc73563dcf5ac3622bff5eecfc22a31c350",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/HUM_LAUNCH_A2_W07_Slides.pptx": "220ebfc6dc5507fb8da51899202a55cbad257455b7eed5cc17e6968e7e57694c",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/HUM_LAUNCH_A2_W07_Staff_Answers.pdf": "8e924b83c1a69f733d04c30b8f37aa74c1b62b1542c771ba44c98a5787972310",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/HUM_LAUNCH_A2_W07_Teacher_and_Cover_Plan.pdf": "21eb8fd2023851896b613933dd97fbe1fbca8a10a9826944ba605b5454cf9d2a",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/HUM_LAUNCH_A2_W07_Tier_Pack_Standard.pdf": "af898e408e963ae9c740c75bd280c676c7a304615eca43b8886cbeff21332ad5",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/HUM_LAUNCH_A2_W07_Tier_Pack_Stretch.pdf": "c0fa18971ddd5ca36c21365579f2ab6d44852be54deda0c3184a28fc80b12e6c",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/HUM_LAUNCH_A2_W07_Tier_Pack_Supported.pdf": "8afa4ed13f94c6588c5f681284274c3ef1fc28f279a1d2583728d461b0d826e7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_RE_A2_W01.html": "79d14b0511374a947624bef22652397fe77a6a6e260521f05819a486f843ed7a",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02.html": "be812c3ebe46241f97ca0e31c481c434027577503aa3fd83a64d06334f32f54c",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Slides.pptx": "f43ece1d91dd5380aaa9d33b22462ee39a13998267720bfdd5fa343e4676415b",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Staff_Answers.pdf": "ef0b5a4feb3d5f81019dba330340575b949c42cf89cf7e600905a41ad041d31d",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Teacher_and_Cover_Plan.pdf": "95e0ffc185a94fe9b4cf8e681af4bd3c32548e6d77d8f2493bfda0411814fe72",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Tier_Pack_Standard.pdf": "206328fac1148d2098e4d92ee8d4e4b26987e915abb8ba03bc2b4851c9078e34",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Tier_Pack_Stretch.pdf": "b00389368988e33fa5c88fa1884e1b1761a4d57079395ecbadffcec4b96b6d68",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W02/BUILD_RE_A2_W02_Tier_Pack_Supported.pdf": "0fdf35ea66b1a0bd9ef4ec495dac97ee270faab82f08adb3e988980895c2d60f",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03.html": "fcbddf443ece4efd770a767fd4010d7c32f1557535fee5037991f14e96ae8a9b",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Slides.pptx": "7e4bd489a21a6ee5b9249f30df0dc3866543cbc899014d9bb8687725d0af1863",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Staff_Answers.pdf": "bcbd92a5b3287a54685218da9eeaced69ba7536925f5d405b7d3a8aabf5382cf",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Teacher_and_Cover_Plan.pdf": "18955038156c8357734c2d8ab98a54ce0f9c8b08bd1ab706d3531bd539e0aba9",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Tier_Pack_Standard.pdf": "b852ad9009ebb7dad92261ca5a97e8e63583ba82377e64ce17fa31013869af77",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Tier_Pack_Stretch.pdf": "dd903f29ce3af4b31cd4331ff01697704a65d97a209d141283823411d03c3e1f",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W03/BUILD_RE_A2_W03_Tier_Pack_Supported.pdf": "c07b407bccf9272182e9de68ec255b191bcca974c118ada47e5da67529c917d2",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04.html": "ba2c8e07f4a8fbc8234552a7c1bd086e544a65582fe9b2b9f53602c2c7d8ca77",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Slides.pptx": "a26eeb76ef3a2c56462b525b4191e64dc719772e8ce34e8e4b7ce8b668cd0466",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Staff_Answers.pdf": "e0f062c148c43ec8bf94dab23dcfdfaad44dfb0a213532577840d18be310d374",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Teacher_and_Cover_Plan.pdf": "4d859ff6c077816e59b13ceb44ee81b88e831b689dd4c98ba010ba6b461b350c",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Tier_Pack_Standard.pdf": "7a4eb92fa639c6f923e00b59ed57f9012d7fa91c3c05fbc81ec4811ac7a39eee",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Tier_Pack_Stretch.pdf": "6a45a2d81f8263855c450dfc60448925d2f3a70204d14b29064c7ab141d46e7b",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W04/BUILD_RE_A2_W04_Tier_Pack_Supported.pdf": "138606d658ff10507868aa31438023ba2aff0f474b2d10c15935d4c80a9169b8",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05.html": "07df20218ebe95b4197b7a09a133585c14a0ebd04b976b4f668b296bd9bac61f",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Slides.pptx": "3aa5983ff9fc80054c43cb582cc115a3adc694aafc79b5aeceba89b20e38003b",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Staff_Answers.pdf": "f43aae9c350b295ca4334d447f9a01613e8eee57bff88433cf64e16487eb906d",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Teacher_and_Cover_Plan.pdf": "0a5d541945a0c2fddf7fb1cb142cdd824dca1fa92a050ae9b6f4126f95ac10f7",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Tier_Pack_Standard.pdf": "a8dbbe58a92039031ba4a940646e01da953a7194107b19a1928bc328bb7205ab",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Tier_Pack_Stretch.pdf": "1ab1436d012ae559f74e581e1da01f75f82bdbedd3cbb8a50d896ed210a255f0",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W05/BUILD_RE_A2_W05_Tier_Pack_Supported.pdf": "ee26bcfa8fce5e8727c3fa1ebb674b1fb736e08b5849a81514074496fa3fe597",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06.html": "6b255744b796fc95fa057fe80270e4816964b980f789367ac90aceef367c3d79",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Slides.pptx": "b2c88d217a75c399ab3b126694705348045cb1f9a7b856324e5b01a6e8366485",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Staff_Answers.pdf": "1daf5ffbc56b1641e7cd08f86bcc74f4358bb0b61170a4c3a364f7a0d4feb1be",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Teacher_and_Cover_Plan.pdf": "07984b4f744ae8e778e01007625cddfe0141d076e80056f351428ddcfe5579c4",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Tier_Pack_Standard.pdf": "9c998ed3f70e330b45efd53bd1b31d624ae995996c3af9fa2042af7f15f44cc2",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Tier_Pack_Stretch.pdf": "b71e1d436ce96137a50ce0c8167eb0d823dc1d3f12c0cbbfde0949c7b26ea863",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W06/BUILD_RE_A2_W06_Tier_Pack_Supported.pdf": "4d1106d2ebedec624fb0a25b966c310dfe3350febe0a8b25cc330c5c44e1454b",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07.html": "21eb61f7039671a951185dc61f78c8f2bd24ef1ee14c7f97361ac25ad165087c",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Slides.pptx": "c2af1114362f4d4bcf4877a97fa6c42d67c3f024a468a0631c56aa6e5774f738",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Staff_Answers.pdf": "cc20e02272dbf71761785a3fc89c4e7f3a937304b488f05e808a85b5514c3693",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Teacher_and_Cover_Plan.pdf": "478b9f2e71573510c71ab2d7529172bf6dbb30ea79f5829148853425d74d47ae",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Tier_Pack_Standard.pdf": "9d59071a93168645e4ef9e65acd88b6f215146095136a61778050b1aa6f887cc",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Tier_Pack_Stretch.pdf": "d69920b9d85c9c4fdfd2f546b34b7a96d8e528f29173778dc3d800e053b5236d",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W07/BUILD_RE_A2_W07_Tier_Pack_Supported.pdf": "2484293692ea840e2052768a77fdf64e52b9a7c6444fbe82d7f7c7d84b26a1de",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01.html": "3955715b1a005a9387bc91892d07f6ff4bab0edb3693d0121e18fed7b9edf650",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Slides.pptx": "fd1dbe13c669f9ca832154c66ec8d677825a8cb3b8e7699b122c2e18cf09617b",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Staff_Answers.pdf": "ee391231d12c907215ddbaec7b5861ade2ce3eeb90ebfa70b4fe6a14207fa6dc",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Teacher_and_Cover_Plan.pdf": "75fe6d73a6c6ec22ef3cd7e828dff28521e2c6180ba83826570f474b1c966ba1",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Tier_Pack_Standard.pdf": "93b9273b5c72db1da81a40660a8ec8b7ea3b8cdb05d92c52b1a311a512834d33",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Tier_Pack_Stretch.pdf": "64a55051d9c177c70e45193c0bf68581966dbd87504d341b07179522c5b14727",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/GROW_RE_A2_W01_Tier_Pack_Supported.pdf": "ce29335af0bd80dc2b4e382ae11c191694d9f4a2d023fc6ef1acaa6da6a0b365",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02.html": "f1cae651dd2d81576593eba50d27b5182ab38383842a787f55dec1fe5824b7e1",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Slides.pptx": "7ba446bc23d0b663e1cbd64aa7f4d341c17d5955b601279183c1b176ef41230e",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Staff_Answers.pdf": "e58315da7dd88d2c67deb5244538c27e9cb3923a6508ee8ca0dfbc0a9075d13e",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Teacher_and_Cover_Plan.pdf": "88a98bb7a1c20a293ca30d5eda747a15ca7453cf736fe747cb564b6b4b3e485e",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Tier_Pack_Standard.pdf": "8f5736a1e0b38e1537d744b9ce64b3267476c53b2b20e64690c70962ba557ea3",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Tier_Pack_Stretch.pdf": "434447f22f137acd1d23db12c3dfa3604821c93a88974e451a125e881fea942b",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/GROW_RE_A2_W02_Tier_Pack_Supported.pdf": "4f93aa529401f46fc0ea447b226c45ce51cd236f3281996faa696f7467628411",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03.html": "1bed5e9910917819fee63cca545e4e85907999c71a3e17aedcaef6967bcf5b4a",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Slides.pptx": "cf7b644eaaf7400f7eaae46b7010d6aeaac1b03569c8af40ee7965ef603fb4ec",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Staff_Answers.pdf": "a1b6aea987050b40469c66d3fe52501bbb2b864158d44237e0b32673b753c5cb",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Teacher_and_Cover_Plan.pdf": "9a6f3cd3082da88b9ffcfc5134f551ee6e497afa0d042106987c4ba525187ea6",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Tier_Pack_Standard.pdf": "d6dc0908fe3d20a8574681aa0320d90b6d85b1ee8922d22f4eadeb9003926f82",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Tier_Pack_Stretch.pdf": "4eb6b438d8850c42ec6e06f85df1429cdabc401862cab8ce4172687d30e67c6b",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/GROW_RE_A2_W03_Tier_Pack_Supported.pdf": "c3815089a4074d0228ad6d151e7bacab666134a8cd46ae9d889f726448c19d73",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04.html": "065b2a169f248b6c552ea66188acb49f045f70435b36b7596f0579ba277b89c3",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Slides.pptx": "a08aef8c204bee796576c2c8e3bb711234e315ee69e1a1428a86c21f932f631f",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Staff_Answers.pdf": "eca49f6ef48f7e228fcbd44f50534a5a756ef784e82a1f6f7595d4246bc06f67",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Teacher_and_Cover_Plan.pdf": "9a2278d5db4cbf4543d0ac9c8763ed3c499d66c6e1567c729c8eeafa7ee14f67",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Tier_Pack_Standard.pdf": "eda8fd4971aec58584cb5ca3e984dfc47e23dade328e49f0312f50fe15e84992",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Tier_Pack_Stretch.pdf": "b1c63be8914ac0da98bbb11c9e6bc661e0eaca3667793c872f8f8e0e1d7d971b",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/GROW_RE_A2_W04_Tier_Pack_Supported.pdf": "38a078cd037ecda723c511032212fe881a852b248cce377f93dcd3089b48ca76",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05.html": "302f138c021c248c09af192d01fda12fdc8cde9ce29163a51aea5e406bc74fc3",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Slides.pptx": "8f4925a8e4619d4f085daa4f017143424d722f87d5d4607720d752608f8cafbd",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Staff_Answers.pdf": "99a253f94923c58934f036e673a3fc31924f9cc2a24e81c830885e8aa1eb7f53",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Teacher_and_Cover_Plan.pdf": "2729a39dad31827417162d0b9cf5e2f3f872f4a4893021e32ced196a4da70a64",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Tier_Pack_Standard.pdf": "9684f7f6e527618efcca16ed0d845c1959c20caca83af9e94e96701ed7a4a0e6",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Tier_Pack_Stretch.pdf": "4d53983c72c4c0632b82524f125104faa5391f187ac689c019ea108222ab18e5",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/GROW_RE_A2_W05_Tier_Pack_Supported.pdf": "8c7ce30cab0a1206d14e57cf850760ed799a131185ba482ca9ba5c35bd710629",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06.html": "44e5c4c4cdd9a313dbd1bf13bd6d328d53b5378bda41f430e4e9745cedf56790",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Slides.pptx": "6da9d01275c37c91cb18eb347d1a097c43b34947cd0fc382e584d16022a62342",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Staff_Answers.pdf": "c4a0588bec1a9555f19b963a2b70213f901318812ca03a5cd8142ac856870b33",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Teacher_and_Cover_Plan.pdf": "56558f540dac43aeb87b7a9f5181d6b98e5afbce2fb74143697235e8708f507e",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Tier_Pack_Standard.pdf": "97044e944c76b0069b23c7b1c2b5e9dc6ad8d157b242cad0416b36edd98b3961",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Tier_Pack_Stretch.pdf": "945048b8abc25804637c39e2a529816d988796a8f9bf19d5aec3bf39c60ee12b",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/GROW_RE_A2_W06_Tier_Pack_Supported.pdf": "6fa0f54319eb8cdd066a1322a5ad9708fb1b344fb38afdc16e12f959fcada26f",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07.html": "f5bde860c0f89932f71eb0f4d16af5a50bec741110cf5a30c25ea305f5daab5b",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Slides.pptx": "267976ade5cd07f321ada0ce291f5db45f19f1a0ec1662081155d2d1a16d4a1c",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Staff_Answers.pdf": "e1989b45b571347ee594e5c31f7b31d4f5558911f99ecd30bd424cbaf33656f0",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Teacher_and_Cover_Plan.pdf": "fd0284b14676f0b95ed901aa03381e350077ae296bd989ccfa96668d74be50e3",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Tier_Pack_Standard.pdf": "4cbf0b3e339d076edb9357e6be9893b80bf76ccc3b8f594f28be1407715a2359",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Tier_Pack_Stretch.pdf": "ce400eb66b0dafa9ac9c4dd651b1018f4d3057b920ac40c31e2eb7791a4198f3",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/GROW_RE_A2_W07_Tier_Pack_Supported.pdf": "0514570715c3aea733108a2f5bf3c2d96325c6946e1569c70277a7be61b2729b",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_RE_A2_W01.html": "06ab20c7ab30e619b6f64d2fb80cdf7bf4a56e8d046acd96b6b93e12b9f05652",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_RE_A2_W02.html": "e18cb57e683b1331909328950982be36dd6953f83b138f0924efbb1a6080c5d8",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_RE_A2_W03.html": "82f3de960e29c544b6d79e1dc95292fcf8564bee96fb468091e966534acf85ca",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_RE_A2_W04.html": "2516069e4d87b26a6904bae1f0cf15b7d6f33909f120f47374232b74a423149c",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_RE_A2_W05.html": "2f361609427e650d6a698b66097da93565434b13297c6affa952f599d9c72ef8",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_RE_A2_W06.html": "d70ea6e4887ba2cb63c4267df5ab9e12f4ce4ec343729cdc28c2ed456c150ba4",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_RE_A2_W07.html": "cac0ae6bc25c1b4c3278d13e6f811be05f446fddd670f3435cdfac0b5e872dcc",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Careers/Build/Autumn_2_2026-27/CAREERS_BUILD_A2_W03/CAREERS_BUILD_A2_W03.html": "f7de9fbfb88a5504fd9d8252a042a406b7a1233d223d36b4007a92ba06a16d17",
        "Careers/Build/Autumn_2_2026-27/CAREERS_BUILD_A2_W04/CAREERS_BUILD_A2_W04.html": "1c984bf5887760e9b4140d879934a2319a97633968f7769899de61528360b68a",
        "Careers/Build/Autumn_2_2026-27/CAREERS_BUILD_A2_W05/CAREERS_BUILD_A2_W05.html": "2bb17c942fafeebd158467d1cebcca0e8ac128aa8067dc1548f23f5badc4f65b",
        "Careers/Build/Autumn_2_2026-27/CAREERS_BUILD_A2_W06/CAREERS_BUILD_A2_W06.html": "5c9f2d406f327f85c0afd380cf5fa32587dd272627ad21e10cf0120b2728a279",
        "Careers/Build/Autumn_2_2026-27/CAREERS_BUILD_A2_W07/CAREERS_BUILD_A2_W07.html": "e423bb48ae421720dd6ffb48cb45f248422cddbd930e32f4661e01b8523aa571",
        "Careers/Launch/Autumn_2_2026-27/CAREERS_LAUNCH_A2_W01/CAREERS_LAUNCH_A2_W01.html": "ee089f19c0954ee6edf78b6318db67ac47354415c52b6eab1e505b4b25a953be",
        "Careers/Launch/Autumn_2_2026-27/CAREERS_LAUNCH_A2_W03/CAREERS_LAUNCH_A2_W03.html": "4a27c9bb59220475f5fa011e9ef09f0365c3754dfa4b2204a1566fc0f04381ad",
        "Careers/Launch/Autumn_2_2026-27/CAREERS_LAUNCH_A2_W04/CAREERS_LAUNCH_A2_W04.html": "ebcf0b6c11b797925d1c51623088ce72b17e662772388ca54f1ef08a83c2137f",
        "Careers/Launch/Autumn_2_2026-27/CAREERS_LAUNCH_A2_W05/CAREERS_LAUNCH_A2_W05.html": "7e1728abd5744ae5bcc6b8bfa90fc9a5d8f14fa4e20f3a0089330c43f45167cb",
        "Careers/Launch/Autumn_2_2026-27/CAREERS_LAUNCH_A2_W06/CAREERS_LAUNCH_A2_W06.html": "5b7da39613a8ead1e1c8032a9603bf82bde357f8745a2849984c511fac4b50f1",
        "Careers/Launch/Autumn_2_2026-27/CAREERS_LAUNCH_A2_W07/CAREERS_LAUNCH_A2_W07.html": "205883424e315a345271d9c01fb3c70d91d7721f28261e2b79633f5937f4d4e9",
        "DT/Launch/Autumn_2_2026-27/DT_LAUNCH_A2_W03/DT_LAUNCH_A2_W03.html": "4793c96dbb4a018ba0e51bd923aa64c10eb51ae52c12a7b0b6aa0b1e6013f1ed",
        "DT/Launch/Autumn_2_2026-27/DT_LAUNCH_A2_W04/DT_LAUNCH_A2_W04.html": "0816b026e65de7915740f3ea6c90c4229b8821a2d0c2eca4a2067972e738cbe1",
        "DT/Launch/Autumn_2_2026-27/DT_LAUNCH_A2_W05/DT_LAUNCH_A2_W05.html": "bf3557a7468de30ab2a3bde6d5dda40a5f21496716b7f15727499187369e0152",
        "DT/Launch/Autumn_2_2026-27/DT_LAUNCH_A2_W06/DT_LAUNCH_A2_W06.html": "f5e34d3167f22b7298c6015ca6436ce6b9fab5340d2be70a37f8816cb7aa3d8e",
        "DT/Launch/Autumn_2_2026-27/DT_LAUNCH_A2_W07/DT_LAUNCH_A2_W07.html": "fb41960eedef48af9ec539e4c93475056907b0beb7a95cb188d22eef050961ff",
        "PSHE/Grow/Autumn_2_2026-27/PSHE_GROW_A2_W03/PSHE_GROW_A2_W03.html": "3b16e8e3e85153bafd71a07d772b12453e751064b4ad721a55b5143f41de6a19",
        "PSHE/Grow/Autumn_2_2026-27/PSHE_GROW_A2_W04/PSHE_GROW_A2_W04.html": "8302c24deca89be123784bf77dd6fef3e0925c7a8cc35bd3e732da18271d8819",
        "PSHE/Grow/Autumn_2_2026-27/PSHE_GROW_A2_W05/PSHE_GROW_A2_W05.html": "fd843d64015f2c7bc3e5eb30476b4698a4d09ed2892718b01727698cb8d64ec6",
        "PSHE/Grow/Autumn_2_2026-27/PSHE_GROW_A2_W06/PSHE_GROW_A2_W06.html": "64728a0972c8efdda002cba9da3cff8e2927b4cdf23834e4794d7db7db025a21",
        "PSHE/Grow/Autumn_2_2026-27/PSHE_GROW_A2_W07/PSHE_GROW_A2_W07.html": "f6e0d3fa29f8cecc8d9845384a000265671a23c7bb4a2a5d78957859881a75dc",
        "RSE/Launch/Autumn_2_2026-27/RSE_LAUNCH_A2_W03/RSE_LAUNCH_A2_W03.html": "3afa99d1e5c6cbf7dbf227bd4c246ab0cda1959b09e9b7659eb1b37d6fd82307",
        "RSE/Launch/Autumn_2_2026-27/RSE_LAUNCH_A2_W04/RSE_LAUNCH_A2_W04.html": "3b2ec2e88fd6d19517ca383d6e80d708796fb54fb42d83dee4397abce3ca5cbb",
        "RSE/Launch/Autumn_2_2026-27/RSE_LAUNCH_A2_W05/RSE_LAUNCH_A2_W05.html": "e7a7c450e32cadd2730bd9df513fc8579b26e757d0517d319d0ca4185fdb0335",
        "RSE/Launch/Autumn_2_2026-27/RSE_LAUNCH_A2_W06/RSE_LAUNCH_A2_W06.html": "09c9fe70bd08ad3bcfdeacc8cf8d80456b88b90f3c10e2b5e83724cf1012ce9c",
        "RSE/Launch/Autumn_2_2026-27/RSE_LAUNCH_A2_W07/RSE_LAUNCH_A2_W07.html": "59a68369f4873fb912bb0fe296e1e49bf5e68b3f49ac7f75ef1156ebfd7995df",
        "RSHE/Build/Autumn_2_2026-27/RSHE_BUILD_A2_W03/RSHE_BUILD_A2_W03.html": "8e13fead137446ca35539e855802b6811011da6c66694c705c8d858739cf4710",
        "RSHE/Build/Autumn_2_2026-27/RSHE_BUILD_A2_W04/RSHE_BUILD_A2_W04.html": "f06e69163c02ab9cae8ed261b4c155d3be878053585726da8c087eec81c89ea2",
        "RSHE/Build/Autumn_2_2026-27/RSHE_BUILD_A2_W05/RSHE_BUILD_A2_W05.html": "45d68c1fc1c63e6c77cc07482e743c0ebb941fdaa0e2c7160e848eaa72aee8c2",
        "RSHE/Build/Autumn_2_2026-27/RSHE_BUILD_A2_W06/RSHE_BUILD_A2_W06.html": "616680e74e01ba504eb175a9837084e2b939c038b64fd892c889b1932f895b03",
        "RSHE/Build/Autumn_2_2026-27/RSHE_BUILD_A2_W07/RSHE_BUILD_A2_W07.html": "6abd49fbe94bb7ee9409928c2203812fbbbe1c1b1f378af290509037c8bf6e16",
        "Vocational/Launch/Autumn_2_2026-27/VOC_LAUNCH_A2_W01/VOC_LAUNCH_A2_W01.html": "0b47a71cd5a18183b1a6c83e259fa51a833c7685a1bef0d0569a838b94c4418d",
        "Vocational/Launch/Autumn_2_2026-27/VOC_LAUNCH_A2_W03/VOC_LAUNCH_A2_W03.html": "8643dc6ebf40ca913c9dbd269acc8bc0331118de7908fb856417be989968602d",
        "Vocational/Launch/Autumn_2_2026-27/VOC_LAUNCH_A2_W04/VOC_LAUNCH_A2_W04.html": "cbd947dd1f5f3c24b1661a51f6f830aa3d896933b4788f161d3ea9a32203ac59",
        "Vocational/Launch/Autumn_2_2026-27/VOC_LAUNCH_A2_W05/VOC_LAUNCH_A2_W05.html": "cb8252915b4861cf3d434988526a4451e4e39de35d2d0781f70bf058fd0e051a",
        "Vocational/Launch/Autumn_2_2026-27/VOC_LAUNCH_A2_W06/VOC_LAUNCH_A2_W06.html": "ec2e15b316b3c67ffd9057e15644b95caa62a3c869821cbf7aa1a60748a0b815",
        "Art/Build/CREATIVE_ARTS_A2_W07/Public/ART_BUILD_A2_W07_P1.html": "591f07facff93cda103358bda773ddbc672c17135d77d69097b88f04d2902225",
        "Art/Build/CREATIVE_ARTS_A2_W07/Public/ART_BUILD_A2_W07_P1_Slides.pptx": "3a083d13099905e570b0ba7ea72199b6c30c0753d2f560890ef212fded961f7b",
        "Art/Build/CREATIVE_ARTS_A2_W07/Public/ART_BUILD_A2_W07_P2.html": "7d09ad1531ff6a8763ca33af8fdd3a35e6955941ffc675d07fbe1d15f16bfe9e",
        "Art/Build/CREATIVE_ARTS_A2_W07/Public/ART_BUILD_A2_W07_P2_Slides.pptx": "c00cf9ee4a416035445cca799852a5090cf82def74e83864043ac7eebe489ada",
        "Humanities/Teaching_Packs/RE_Autumn_BUILD_Reviewed/BUILD/Autumn_2/W01/BUILD_RE_A2_W01_Slides.pptx": "e73ca74c88bd617904048bb31d71a5a6ffeaa3d354722a4ab0a98af7dc1d0795",
        "Careers/Build/Autumn_2_2026-27/CAREERS_BUILD_A2_W02/CAREERS_BUILD_A2_W02.html": "6eb3ad87a299e0146cd5ab30b59acd019713d0ea0bac3f94b24545cb94527201",
        "Careers/Launch/Autumn_2_2026-27/CAREERS_LAUNCH_A2_W02/CAREERS_LAUNCH_A2_W02.html": "f53a7346eca73388b59dcb254bd6b3fd304b421c7f9256a17019b32e62200088",
        "DT/Launch/Autumn_2_2026-27/DT_LAUNCH_A2_W02/DT_LAUNCH_A2_W02.html": "cb0a80043ed9a9434171fc0c9a1d39da15d3dbebc8984943901aed540c7b603c",
        "Humanities/Teaching_Packs/HUM_Autumn_2_BUILD_Reviewed/BUILD/Autumn_2/W01/HUM_BUILD_A2_W01_Slides.pptx": "32cfac21858bda55f8510a4910c4b63a41c2587df395849fe46ced47f79da1ec",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W01/HUM_GROW_A2_W01_Slides.pptx": "5529590dbef12dc21b9a366f833ebe470154c8392b327746a459a93089f77f5e",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/HUM_LAUNCH_A2_W01_Slides.pptx": "7b0a83fd26bee1583892861a9ec011fdc13ef797543d2b6e881f8c669f6bbe34",
        "ICT/Teaching_Packs/GROW_Computing_Autumn2/GROW_ICT_A2_W01/Public/ICT_GROW_A2_W01.html": "959a5960cfe7e14d59d6a38703ac8ce482a1acd83b521175f350991d29ae018b",
        "ICT/Teaching_Packs/GROW_Computing_Autumn2/GROW_ICT_A2_W02/Public/ICT_GROW_A2_W02.html": "9fad2eba8ae04caf5c796be75e3f40e487267b96aa07b1bee3a462d378518702",
        "LAUNCH_ASDAN/W7-W12_2026-27/lessons/ICT/LAUNCH_ICT_A2_W02/Public/ICT_LAUNCH_A2_W02.html": "6204bbb1dbc3aa44500f188e44272b78dcd01cc6b1d555cfaeb656b71afb1997",
        "LAUNCH_ASDAN/W7-W12_2026-27/lessons/ICT/LAUNCH_ICT_A2_W02/Public/ICT_LAUNCH_A2_W02_Slides.pptx": "d8a67c0c47d3048fbf7940d402a1abb2855f2c3149bbb95d20810f1deceee705",
        "LAUNCH_ASDAN/W7-W12_2026-27/lessons/ICT/LAUNCH_ICT_A2_W03/Public/ICT_LAUNCH_A2_W03.html": "6eabd3e33790ad50fa5989bf4696f21990ebc0592bd772b93792edb62fa062d3",
        "LAUNCH_ASDAN/W7-W12_2026-27/lessons/ICT/LAUNCH_ICT_A2_W03/Public/ICT_LAUNCH_A2_W03_Slides.pptx": "3997dcd5d34b2c40a95860d86bd13765c9809a2e5fc7aec1fb4cb991f5ff1ac7",
        "LAUNCH_ASDAN/W7-W12_2026-27/lessons/ICT/LAUNCH_ICT_A2_W04/Public/ICT_LAUNCH_A2_W04.html": "3c16ecdf53711da8fdb7e5a14f30a87c9248c7b96ad9c3532fd55a055890a02c",
        "LAUNCH_ASDAN/W7-W12_2026-27/lessons/ICT/LAUNCH_ICT_A2_W04/Public/ICT_LAUNCH_A2_W04_Slides.pptx": "267644a0c019c8a45b651b42731ae0cc92e5e5e4739f11eeacdd2ee2273d4301",
        "LAUNCH_ASDAN/W7-W12_2026-27/lessons/ICT/LAUNCH_ICT_A2_W05/Public/ICT_LAUNCH_A2_W05.html": "7ef4d34679509bf350e0e859177deebcbae8ece5697fb7c700813bdf79f55eb9",
        "LAUNCH_ASDAN/W7-W12_2026-27/lessons/ICT/LAUNCH_ICT_A2_W05/Public/ICT_LAUNCH_A2_W05_Slides.pptx": "7cee4843f44725d5f295bbfd6c1015e739f51ce03d37c9d141080de088dcd690",
        "LAUNCH_ASDAN/W7-W12_2026-27/lessons/ICT/LAUNCH_ICT_A2_W06/Public/ICT_LAUNCH_A2_W06.html": "4096fb881f9cd0e6a9d2025fdbc5f9c180a750af1e1ae0651bceb69f3258e67f",
        "LAUNCH_ASDAN/W7-W12_2026-27/lessons/ICT/LAUNCH_ICT_A2_W06/Public/ICT_LAUNCH_A2_W06_Slides.pptx": "4da2dc19b567adde99b767eaaa29f6d3ae3ef361cc119c0c305e3c68276f802a",
        "LAUNCH_ASDAN/W7-W12_2026-27/lessons/ICT/LAUNCH_ICT_A2_W07/Public/ICT_LAUNCH_A2_W07.html": "88340c00c505ceca94c29e7510a34d23cd746e3b2f975cd4498083535f1e8b1f",
        "LAUNCH_ASDAN/W7-W12_2026-27/lessons/ICT/LAUNCH_ICT_A2_W07/Public/ICT_LAUNCH_A2_W07_Slides.pptx": "0cbe4f2ad9ad221bd66821f886202b3adb9cbfae213ee64a74c6c88150e45355",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/LAUNCH_RE_A2_W01_Slides.pptx": "883d873acfaff940a4a471e89823793e872966eb6dbe3c0de76771c9d0db0681",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_RE_A2_W02_Slides.pptx": "fb6428630709141ec9d59293c2b9ac810f762cefd776bcb7d0f7fc76fa5bdbce",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/LAUNCH_RE_A2_W03_Slides.pptx": "1f9c0f12321547029af91e3cd046a2a9a63f8f8da791b5d8a173702c4e8f1624",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/LAUNCH_RE_A2_W04_Slides.pptx": "bece4342df6955915da38f305272a02c71bffdb75cbb20f1c9e0e14cb8f0b54b",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/LAUNCH_RE_A2_W05_Slides.pptx": "7068503eba0d29c83b433e5e6cc5ac9a45b8f0d6cee15d7a2ca8520b77d4bdd2",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/LAUNCH_RE_A2_W06_Slides.pptx": "3888c271392353afad7818f32947a583ebac5729856cec36a649287105aba6b5",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/LAUNCH_RE_A2_W07_Slides.pptx": "8654afc9d680703587ab22f2f24674479a8bd8d599dc5f8c738bfd0954f9fffe",
        "PSHE/Grow/Autumn_2_2026-27/PSHE_GROW_A2_W02/PSHE_GROW_A2_W02.html": "f7ce7a8279f1af37a6d04805e5e91181b13499f8bb48004b123fe2785492e56b",
        "RSE/Launch/Autumn_2_2026-27/RSE_LAUNCH_A2_W02/RSE_LAUNCH_A2_W02.html": "fc5d94134859bbf835d755f62254efa1d84d5ecb6e3a64818431e8fde8c18eeb",
        "RSHE/Build/Autumn_2_2026-27/RSHE_BUILD_A2_W02/RSHE_BUILD_A2_W02.html": "4977cdcc41915f124a986ea1e08e60dba5bba7a39a2150584acd0307a915412f",
        "Vocational/Build/Autumn_2_2026-27/VOC_BUILD_A2_W02/VOC_BUILD_A2_W02.html": "1881503959fe10b5268ec24337e7c63263dce1c115f8de900eced8b363b78b20",
        "Vocational/Launch/Autumn_2_2026-27/VOC_LAUNCH_A2_W02/VOC_LAUNCH_A2_W02.html": "df953c570957716973faecb1596f5d9209030f247b8f9114fd022ee363cbea6a",
        "Art/Build/ART_BUILD_A2_W05_P1/Public/ART_BUILD_A2_W05_P1.html": "7197445af32da2c554d76525a5bccdf5c1d7908dcf943709d2e98aadd80ba6cf",
        "Art/Build/ART_BUILD_A2_W05_P2/Public/ART_BUILD_A2_W05_P2.html": "22968efc0739249b4878c999fada37c67cdbcd7384f98d1c46cd1ca98ae187d8",
        "Art/Build/ART_BUILD_A2_W06_P1/Public/ART_BUILD_A2_W06_P1.html": "400e078c44f38c87c1ff489cf668d0e6ba6d1a410bb16a8038d8062127678c80",
        "Art/Build/ART_BUILD_A2_W06_P2/Public/ART_BUILD_A2_W06_P2.html": "5eb9a85a8789adb1240a210cbb60c074ff014a0806dca05ce29ddd18c1fb283a",
        "Art/Grow/ART_GROW_A2_W05_P1/Public/ART_GROW_A2_W05_P1.html": "447bbfd6bfe35d6ba4ba18a6ea1fd30f624beabfea496d11c61fcbb002a52a2b",
        "Art/Grow/ART_GROW_A2_W05_P2/Public/ART_GROW_A2_W05_P2.html": "5495f61689c95dd0c775b6795a6d482e20075c45ace28e14a1a1e8ecd9d5f897",
        "Art/Grow/ART_GROW_A2_W06_P1/Public/ART_GROW_A2_W06_P1.html": "a536fd13469754e946cf3589bb1e6b05502f381aa8c7e6b4349e4461049dbefe",
        "Art/Grow/ART_GROW_A2_W06_P2/Public/ART_GROW_A2_W06_P2.html": "ed19ee82063bbc14f96784f6119c021fc220c4a302e5d36f79b2808304afad2d",
        "Art/Grow/ART_GROW_A2_W07_P1/Public/ART_GROW_A2_W07_P1.html": "b1b6215bbc73066ae9ed75fd37fa45a02bd02f199072d9e4523b4b630f85c7a4",
        "Art/Grow/ART_GROW_A2_W07_P2/Public/ART_GROW_A2_W07_P2.html": "a8ec8d3e8c1ebea6ad9e0a1b206365d76507171418008bca2001fb77ac89da7a",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W03/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W04/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W05/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W06/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W07/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W01/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W02/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W03/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W04/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W05/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W06/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_GROW_Reviewed/GROW/Autumn_2/W07/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W01/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W03/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W04/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W05/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W06/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Humanities/Teaching_Packs/RE_Autumn_LAUNCH_Reviewed/LAUNCH/Autumn_2/W07/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Build/ART_BUILD_A2_W05_P1/Public/SHA256SUMS.txt": "8c949902c0506e5e7c11f9c04cffa3aa231e40959a827faa0c8b25840f4f78c5",
        "Art/Build/ART_BUILD_A2_W05_P2/Public/SHA256SUMS.txt": "84f51a822d9f7c59fe7af387b2f17a3e05df79a3724112922cb8188f76a7af26",
        "Art/Build/ART_BUILD_A2_W06_P1/Public/SHA256SUMS.txt": "c82cb8a79e1a691229a6467ae56c8649b63746c8ab29f3ba2b9e08631879eb58",
        "Art/Build/ART_BUILD_A2_W06_P2/Public/SHA256SUMS.txt": "3f5969a885a06f21bf0df1ba21afc7a2e83c188262877ad077382536896f6d84",
        "Art/Grow/ART_GROW_A2_W05_P1/Public/SHA256SUMS.txt": "d7ffc18f5d606754ebb6d35d331342398b6b124db6f17a146c426ed1d9a34e76",
        "Art/Grow/ART_GROW_A2_W05_P2/Public/SHA256SUMS.txt": "016b0b28c80ce775f1dbd9c71c7e3e2a59fd25cbab7500b870ae054bddafb3ef",
        "Art/Grow/ART_GROW_A2_W06_P1/Public/SHA256SUMS.txt": "7559b5062cc8ff589acf787290894579f46e939d81ebaa7333286dadb0fe9c32",
        "Art/Grow/ART_GROW_A2_W06_P2/Public/SHA256SUMS.txt": "d4f05d30efb745ed4bef459249a1939b434fe582a9a31b741ee71e0f02e20af7",
        "Art/Grow/ART_GROW_A2_W07_P1/Public/SHA256SUMS.txt": "f3190791d6f5a73e8ef8b73c753066edff6aa53aad2e7e2e0ab48482698b5a4b",
        "Art/Grow/ART_GROW_A2_W07_P2/Public/SHA256SUMS.txt": "373757250fde2ef9a6f420ab074753fac342ef9086805ec991a296780656a588",
        "Careers/Build/Autumn_2_2026-27/SHA256SUMS.txt": "618e979dacd4560c082a165c2384077cf95aa9e63f6505cebe0349df1cf43cda",
        "Careers/Launch/Autumn_2_2026-27/SHA256SUMS.txt": "469d9c5f14af0cd239fba3715136413ebdeb33b04bf43157805f9a3b9e9ac2ff",
        "DT/Launch/Autumn_2_2026-27/SHA256SUMS.txt": "00672ec0d95f49fc67f72ccc7f7f1a81c510d1cf15d8b68a06e069979dc5fcd3",
        "ICT/Teaching_Packs/GROW_Computing_Autumn2/GROW_ICT_A2_W01/SHA256SUMS.txt": "d89469302bb204a0418b3293a93aff87d3b1b792f7bf95b90ff6436fdaa5df67",
        "ICT/Teaching_Packs/GROW_Computing_Autumn2/GROW_ICT_A2_W02/SHA256SUMS.txt": "9cbed4ee3757f43cce689ff77073204868819e72a494de3c21521445203044d1",
        "PSHE/Grow/Autumn_2_2026-27/SHA256SUMS.txt": "c6399ebd777032625b1da67f30d4cc022db4bfe1d525eb54ebb083727c1319ea",
        "RSE/Launch/Autumn_2_2026-27/SHA256SUMS.txt": "1184ee9703e741a6afedbd009bc3939f0bd411c27af13d80014eb0c36fae9fe7",
        "RSHE/Build/Autumn_2_2026-27/SHA256SUMS.txt": "2452ba679bb0acdcc3252b497ee9463ab47b6e70ede3693acc2d4fdd085e0a6b",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W01/SHA256SUMS.txt": "e56ed9b0ef3f2bdc8e228ad211f3a431eab2cc104f39df4a2e18602da04d8ff1",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W02/SHA256SUMS.txt": "5634dfcbf572168b5be66dc25aa1df9ccac13a1bad60982fde1c3befe2f53b79",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W03/SHA256SUMS.txt": "445266d3038e4ccc3ed37f0a8d7311d6efdec074f8aeffcba97074d74600dab5",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W04/SHA256SUMS.txt": "f51a362b38fbd23633856a439d6cb90b59093205ddf71bcf646ad9c2a1cb1f1a",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W05/SHA256SUMS.txt": "c2d9c0dd691fee93a249a88f9b4f6635340d89fee0fc0f989aa940a825d53044",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W06/SHA256SUMS.txt": "03066f7795b2960e64bc92d7f408c118277c8d927ac51e0b6922bd53b39c9315",
        "Science/Build/Autumn_2_2026-27/SCI_BUILD_A2_W07/SHA256SUMS.txt": "93c4898c1a311ee6c19e4d66b69f6f353fbee264587b12d1488e44f19a7877dd",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W01/SHA256SUMS.txt": "6c9de26b51a2cef18f30e3a68dd8cbde245e635450e0638ff1af7d9445598790",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W02/SHA256SUMS.txt": "725042b9b08c3934d9c572a42b64660c39a935a85e1dbd75fb7b7d4492b626c2",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W03/SHA256SUMS.txt": "ca3068ea0c31d1fc6d2e64628c4f43353b999b26758fbf5aff0244bd38224e7a",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W04/SHA256SUMS.txt": "299f7c929e9d74ed55d0fba265ab644cc4692d9d4781f66bd573f95e14bb910e",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W05/SHA256SUMS.txt": "30190d1c5ac7a398ffe8fcd3f733442e7c93b86100575765a2519d1d7ac7cf8d",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W06/SHA256SUMS.txt": "5c61c7fd514e58444a4aeb2b1979be63a6fd50a7d6b34d83fc4ae678072ab29a",
        "Science/Grow/Autumn_2_2026-27/GROW_SCI_A2_W07/SHA256SUMS.txt": "4ab9ed445bf8926008bb16ec9fd422173fb2473dd8ba503438fbca3e80c4de80",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W01/SHA256SUMS.txt": "0d8f8fb664eb8698e76eaed47520569fe351a8e15027803932229aa2ccada2b6",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W02/SHA256SUMS.txt": "c405981c88f1bbd00a3cd028da5ce1cbfff1e9ecfc1e9bd5d5860954329085b2",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W03/SHA256SUMS.txt": "c46bd84d63dd65c0547ef17a6dc8eb582f7b43e9de3cca5e7649165b19405e7b",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W04/SHA256SUMS.txt": "a5bb1c38ee356642623123ebad460ef8857465b0ce048e0f4f1e7bf943d97d13",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W05/SHA256SUMS.txt": "e2d0ed800af588db6e3b9fd3e355d123e74e1ddac93e495fd8ddb8c1883bb440",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W06/SHA256SUMS.txt": "1ae3805c80be3385c4ee26557738280fedeb7dec19c92fa824169ec0e344fd7e",
        "Science/Launch/Autumn_2_2026-27/SCI_LAUNCH_A2_W07/SHA256SUMS.txt": "a93030ccf4007c432cdac237ce9a693ce851507017863695f7dc5ca69653a647",
        "Vocational/Build/Autumn_2_2026-27/SHA256SUMS.txt": "2643ae91aa146e131a03d38eb89b4f452b0fbd169440b9ee501f75428e2647b2",
        "Vocational/Launch/Autumn_2_2026-27/SHA256SUMS.txt": "ed3a712eb6d8e82e342421a4504da23359a1e0a9479591493d80c4ce9d8e0fc4",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P1.html": "8382b7864fdda9e6d396b1a349a07580f86bdd1bbb850644bc33b11d4fc5bea7",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P2.html": "525193f04c55c71db0fac8be29db883eeebf3c7584ed334816149aab6daf29e5",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P1.html": "c0d07c2781dfb04d4fd4db46f6d8961cb1915259c244a00e767c96f6b6f24b0a",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P2.html": "ab1d5db5f72835e7413cd704b06e50b9dc83afd048b924f152f482c58f21072a",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P1.html": "e88bc3b097836a54ae640df90126453153a3f3e2a1fc854eadd0f7b9a4326db9",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P2.html": "dca4c70b3279bce50bb1a259991b847f50b600371875a489ce50b47419708a26",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P1.html": "6361a4aeb874b52e54f8aa58b82261dc4a81d2793d95a4e0cc41cf7e506d4449",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P2.html": "32305f635b9c6c2ac4621829b23975ea333820822ea00b1d9b7d73b0658e0e13",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P1.html": "d25c0a9631c61e3ba3ee0c9d8c6aaba357d4d84e74ef48010b057013f034384a",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P2.html": "b3ec7c513089482c7d544292e39ced8ce238c5aed2efbd27254ac9715ee597c1",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P1.html": "7241ac487e7c7f2d89bcff966063bcda847a9b5613fba85df6a5aea7fb10a4b6",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P2.html": "a535afab0d4733fae0dc9257f9bdb7a51cfbe3b70c7541c1b2c20f344cde53db",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P1.html": "113dd7d5329d481846c98082c7d60825a3d880069b70346bc26ef9c0c088232d",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P2.html": "d400431e866f825723f250c39c3716ca9803bcd94d7f09e169806d48f1b46fd5",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P1.html": "8cf037aab4812e0869afc3e6d4299eed0410e5cda6243c2bc815e29752765321",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P2.html": "2458c968bdb2b1d217482bfac86a78d0989aab4eaed254832a74763327c5969f",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P1.html": "62fd0e06c18aca19844cc9332d2f9c82976b471b4433ae39b382284cb27230e4",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P2.html": "09cb56d3e8f120b30fa8ede948beeb1dcc5f6eba74e8ac4d9866548cf9800fd6",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P1.html": "d46469dd1abd1431ad030eb3bcc81d32bcb60bff2216b03c9d117c9863708c72",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P2.html": "0941f44adc33ee3d466d6bef9b1034425ddc6b4a646813a078b71962f8f710f6",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W03/SCI_LAUNCH_A1_W03_L1.html": "62cef91239e568f6ee59416f74959ee113ed962cd87b98f46b7091d80c951b76",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W03/SCI_LAUNCH_A1_W03_L2.html": "3eb3cc047637bdaaf862fd551c47aff6ed5337763b15c9a6d184984535a1ffe8",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W03/SCI_LAUNCH_A1_W03_L3.html": "52965155e8e1aade87dba568cb5c9df6a06d8e2d895aa4280e23255ac78577b4",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W04/SCI_LAUNCH_A1_W04_L1.html": "030e1330eccda6dd09c977c91133444bec7ea4f3c09d701e2a3b5be186d99950",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W04/SCI_LAUNCH_A1_W04_L2.html": "e4efb4836be78c598ffab14b763481838486e4a753b3e43342a78585f8b3ea58",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W04/SCI_LAUNCH_A1_W04_L3.html": "a18bc24efd92d9e15fcb6957563617fbb5ae894be73b8318d0edfc47012dd8b9",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W05/SCI_LAUNCH_A1_W05_L1.html": "f5887f24c08139760e5e51da70a1fa9d2c46dd734bcba34232fec25636d6906f",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W05/SCI_LAUNCH_A1_W05_L2.html": "3a29379ce54d9abe9c5d20c85d06ee4bb277f1df173e3989b62d4bcfabb615ec",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W05/SCI_LAUNCH_A1_W05_L3.html": "240e637dceda5750e1118c63648016ac30579bbebd341b1f9be563f059466c33",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W06/SCI_LAUNCH_A1_W06_L1.html": "b567e903e3f56acbbbe4dd3ac41691e0c87652f5b57a196fd58a094b13628179",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W06/SCI_LAUNCH_A1_W06_L2.html": "a8c7d4814b2515666c32b9b408044de97b40c97786418f6e0108880e6eef9588",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W06/SCI_LAUNCH_A1_W06_L3.html": "231d6c051d68499780d2da97e1555e36826815ab5773d1bd0529edbc3ba3baa3",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W07/SCI_LAUNCH_A1_W07_L1.html": "0a5dc897e3f95b109503b43a2527bfe5e0e9cbb6ceeccea69d26177e0c483be8",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W07/SCI_LAUNCH_A1_W07_L2.html": "3042487370f645e78941eb7f227b83e1c7cd25dba349766399dff54637f17f90",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W07/SCI_LAUNCH_A1_W07_L3.html": "24d9085b2e9d25bc3b8e53ddcc9bfb618c838693a9b69ac4d7d4ad91445f93e4",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W03/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W04/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W05/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W06/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Launch/Autumn_1_2026-27/SCI_LAUNCH_A1_W07/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Science/Build/Autumn_1_2026-27/manifest_a1_aaa.json": "e3ad81b46033d79b6b34dc9e8e0c67722cf49b5f7612757445c9a4299d317e8c",
        "Science/Grow/Autumn_1_2026-27/manifest_a1_aaa.json": "797cfd06e0de9914fc12b0e30acbcb00d144af38116f0d6f02a99e2cea87b6b1",
        "Science/Launch/Autumn_1_2026-27/manifest_a1_aaa.json": "5174186fc3bf0f8a3e3b09e1b01e93d526dec53700fa6761b76cb1a9a133dbb7",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P1.html": "b2b85b1eed3cd0cde74cd406faa0f99cacd8b1f9b789fc5c3a86aab41b82cfb0",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P2.html": "027aac8cee768bf892e478c8c804c059b63b6c00ed3b82c397e6225092696669",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P1.html": "5944d0685154250a3f066ead5469d1921b0750d83b5697f954ab3959c88512e9",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P2.html": "a763c24644952e45cdb1fcd04230f1f970e1054f19fa8da4318dcdf3aebcb39a",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P1.html": "65adc909dd7657410913b0c5e151fea9fe9b123e04e09f7a1264467e2276bf5c",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P2.html": "6de47c8f3769f74d101496dcec45e34aed09daab31ef95b6bb0b4c4598711164",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P1.html": "aa26654746ad8827a346083b040cdb29922f507fb40a290d12b140ad535b320e",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P2.html": "0f05c2876ce3e136ac61a0378cedadac56673a32e9d315d9f7191359dd82436a",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P1.html": "edd4e3266194605f0db59639aab76615f922ee18c8d6c27d454704a5e16d573c",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P2.html": "b0e9d4ed2ab11dbf9a190ed50fe6a2821619689e27b43b1d97ebb191cb2f687b",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P1.html": "aaf3c11f1d1ec9e896255aec5721dc9ab5e05ebd5b73392e5994b836f4bc2970",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P2.html": "8f9c6fd8576ca54f0e5dc3a17f9fd64df63479c1232d4165a56de14048decfb8",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P1.html": "4841419ae78edb529073e9b0720da281d07bdafa029447bf1d512be0e75fb011",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P2.html": "b4319facdcb92e0ce383db52aa9d93e43eb761dccdc535398ce13a80e5da2e9d",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P1.html": "1a2b471255ba8c436c398ee68dac1b1b28ad3911abe61dea3d3bf96cdf060bad",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P2.html": "70f093d1936435b34921b29897a50dd9e6e0886493dd5d22e9cea170f49210b8",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P1.html": "fa215fe51da3c9d2e7c1b06ea4935faeabb7a957a1696bb657b2f0a9cb592f22",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P2.html": "c1451b98995841a0a0bd92c909b2dd6f2641758ec6865a82451809df13d8fadd",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P1.html": "acdba2a30ffa2a4b6e9d7fe91eb9121e0892500a479139223b996dd731a838e8",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P2.html": "b894bcbfaeb604ffd369c1c99a9271877418fcec712c079668656c58bc6562df",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P1.html": "bb2e5b6b961904019903df514103a7910567f727569f7137de822236f5869f29",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P2.html": "d3be25d5887bd3d77e56158b8522a74cb6c881d972697622c5df9bee81f95742",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P1.html": "64b9b6d803138fa5e0fc606b3aba0f5c76d4fceb2ea3ce922793ad2ac06e5afb",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P2.html": "4d8c4801dd3e988fad8c5a2975e5676f2de52db67257187e7dd51a5ce9ceaf26",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P1.html": "ec92d9954af883db1e965e01f1586cee994fd211481cf013dbde59b09fca6607",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P2.html": "7010de609b2b41e85f6827cedc4871f919f5f35e309155197ba4249771501b8b",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P1.html": "105224fc6a0cb448e335c1d3b648b6423117b093b8d5ea0849fd82be7fee570a",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P2.html": "cc73118987673ddf2b026c274d60e1ae230dc31d8825cb2307dff75aa1e1efbc",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P1.html": "0df90c1a601d61b062991cb9dc7a7828fa2c3d5ced1fc345856cecf3953174de",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P2.html": "4793c5ce61c64e27bd3e55c7a1362aaf2ff9afb1f91d59407047ddc751c57707",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P1.html": "cd2abc409b97862ef34813ad8e3e67706798f6be54ec698a6edab33487037854",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P2.html": "2963771e2eeca2675855765475ca3e8685db9928428d4699d17852f39ae947a1",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P1.html": "5a1a7be9682a471234ffc9ab2422f847277c6cb1368e681e38ed9e2702ce0036",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P2.html": "08586b2ecc6b78a2845117154c2e636ba05f8f716d086a54c64b174260e3c6b5",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P1.html": "72588eb2e4d50dc4b91a208b57b93c697aefb36145c6a9feaef51f1e8b9975ec",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P2.html": "316a4b9283909f7349d947f479caa98d531ba148c0f07a16299f3439b7c5a080",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P1.html": "5fbe860baf0832841a0056e33cbfab6fd09ae12c80aea1253bda23b8f3a80560",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P2.html": "d9f2d6a05a39242c2f335cff67e67cd132591f92bea4dd3ff3e3f324229aa43d",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P1.html": "980afc0614facc359b41e932ef1802b35e31f36e13a2a89fcca0e680bbe61fb0",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P2.html": "537ce528acae8c9caf6f80b8333a5c0866aa45bcdf162da64d4038232c24aced",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P1.html": "a4c34b8f5e211b277319b86fd52b1b30b72936ea9cf1548bcbbefac1c74bb538",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P2.html": "59dd18a90d7e9f6d59f07e37994dbd29a3023d16b7ba2c9578c01b5b1aee500b",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/approved-mark.jpg": "f1095531d88d17f20c7464c62887703321a0872f108d3fb78a4afc0226dac2a7",
        "Art/Build/Autumn_1_2026-27/manifest_a1_aaa.json": "0f0b7eec6daeda548c3ddef439afa5d4740a2dbe172fc45495feeefb9071fb5f",
        "Art/Grow/Autumn_1_2026-27/manifest_a1_aaa.json": "e033e3045b2ba8250e891fe287eec6784bb96156b2b0adb39886cc2fe2590885",
        "Art/Launch/Autumn_1_2026-27/manifest_a1_aaa.json": "d42816956781ac206a57e208e1aa2a736d365e36176b2c306992566e3ac4ef62",
        "Art/Build/CREATIVE_ARTS_A2_W02/Public/ART_BUILD_A2_W02_P1.html": "74706462e2d2d534e0eca66555e821ae73bdb6d73ff1bae2728655ee99d2493d",
        "Art/Build/CREATIVE_ARTS_A2_W02/Public/ART_BUILD_A2_W02_P2.html": "4c477e2e8043fbc3dab9543f9cca98639a9b727ee670dbcfea16e9eeb8746573",
        "Art/Grow/CREATIVE_ARTS_A2_W02/Public/ART_GROW_A2_W02_P1.html": "622ea8ae9fb341dafa81c11342c7b2cd683f287f8feed1d1c68242cd1168d3c3",
        "Art/Grow/CREATIVE_ARTS_A2_W02/Public/ART_GROW_A2_W02_P2.html": "7682e8254eff47f426f74941f1de57e258796fb6308570fcf77200a3ffc60083",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Knowledge_Organiser.html": "1e3fbe313eeacabd4ae52029e8d46eb95b64f4a95b2fdd7b95da4712aab73d9d",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Model_Transcript.txt": "bc1ff074a178966b13ebd461b7bfbcb23fef49f56b7a9817f2942575f3e9c03d",
        "Humanities/Teaching_Packs/HUM_Autumn_2_GROW_Reviewed/GROW/Autumn_2/W02/GROW_A2_W02_Pupil_Resources.html": "d7371ae139cd65d66fe9d82ad6dcdda72b860e142221f446a04ad1c0717a99cb",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Knowledge_Organiser.html": "790f3feeaec2c80e05cd1abe3aba9ea8f50c22b86bc590780a5580b32294cdb8",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Model_Transcript.txt": "b9a55ab1ad4d79c280ce3f8425755d84d863e59dba4b2f423de7e73897aac818",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/LAUNCH_A2_W02_Pupil_Resources.html": "f493d509fc989946df982b61c734103ff17eaeca32fee845089880d11c64df22",
        "Humanities/Teaching_Packs/HUM_Autumn_2_LAUNCH_Reviewed/LAUNCH/Autumn_2/W02/Teaching_Visual_1.svg": "0bab17c7a2ea500fe2868748cec341bc6bc2e094c621800a6400fa4dc9f89b0c",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P1_Editable_Pack.docx": "d7d682b78a44fa51113dee0d4ec49b6a851f298334ab9524df68432aee0ad7b2",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P1_Knowledge_Organiser.pdf": "1f700881499554772a259aaf4e75e439d5c093ad7343f312ed56bf6528249b91",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P1_Pupil_Resources.pdf": "36c7f23fd85e55027a722aa07c1a71cf3a58bd0a80aaa71a45098613661b9d63",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P1_Slides.pptx": "2cf542ea2ce8566d12d0fc168a161994ccb8eed4064e98bde83795f421f72c7b",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P1_Staff_Answers.pdf": "5fa4e8ea61987eadb5c20a13298eb3625451f080142de76a2154451a5ef8e3a6",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P1_TA_Brief.pdf": "8909036e3d87c6aca7253e91f3c592210933c77dd39ccb1acf1732f89119cab3",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P1_Teacher_and_Cover_Plan.docx": "6f7ef25171f5cff0840b4f56531a5e316de6fdb27af56e3c7e204bf497267dae",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P1_Teacher_and_Cover_Plan.pdf": "ef73f1b9715f1519af7101fb326f9159dbcc69947dce4338c14a2947b5f41a37",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P1_Tier_Pack_Standard.pdf": "0e72b4753417ff6baa1dfa9bb9657f614fad583f4a41d0d981f76a5ab8c9a075",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P1_Tier_Pack_Stretch.pdf": "9788c3357ccc593ec3c32a5fd335d4e568800be00f1651065e91c06fc7390904",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P1_Tier_Pack_Supported.pdf": "fc0326243761f172a6e4d222e956dc85051d93f7fb2d7102a775cc3679a352e4",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P1_Word_Page.pdf": "bb41ae1b5894f8cf92c56572a8bce9c5cfd7aecd198de1ece8814058fdf47aec",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P2_Editable_Pack.docx": "b8c2b1614f65464c90d55d28f182a53559e8f8ff9fd134c51130e687e167b816",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P2_Knowledge_Organiser.pdf": "bc9cddefa441adf0e708c038125a04aeed6963c3315b3b1972216e4bbabebf92",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P2_Pupil_Resources.pdf": "48ed15e497a6b8542359adf7dd90092fb238dbd298ee4eb18043adb0c48bbfb7",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P2_Slides.pptx": "678a63203480d4c2af0a70af32866200cb22b46b36b46686f657d8e568fcdf04",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P2_Staff_Answers.pdf": "d842a73b75cc3e1f5c3e4499b874636c0889afffcee01127c88af6b5776d1559",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P2_TA_Brief.pdf": "7143a0859a41c53f3789222191b0605e80563dfcad500164e65537e1c3a0b5c6",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P2_Teacher_and_Cover_Plan.docx": "bcb780c29cd76e831f62349c5120b713bf4684a3ce35fa5db182828d58052433",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P2_Teacher_and_Cover_Plan.pdf": "3fa3ed5f002da9d35daa910da631960c6b9990f65f33808edec16c8a97546dfd",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P2_Tier_Pack_Standard.pdf": "147ef28cae075823c7247a0eb316401960879ca6100ce7a6eacfb271c21a2f4c",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P2_Tier_Pack_Stretch.pdf": "cc8befe82a009bbea580b176b7b015c0f6461c7d07545a70984c9c326998c0a7",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P2_Tier_Pack_Supported.pdf": "f6a9d6c2a5901fac590108f933730ebb7cddadba7b8668d59c5e54f9d97b5978",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W01/ART_BUILD_A1_W01_P2_Word_Page.pdf": "8367cb3d3f4a48272be26512f137080ee03301c462056706b1beb73d8f2688f9",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P1_Editable_Pack.docx": "82d8a72daf1ae0fb1f228c129e24ff630603315cc730f74af2dcc4efcb9ce031",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P1_Knowledge_Organiser.pdf": "00fc6c9e5b2d9f573f12dddd7cbf8d18f182ca98571fe7b72262b20b0a51a092",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P1_Pupil_Resources.pdf": "1d6b00af1e46374c1e4457f649a57dd8a56e53e35fa8a7a96dfa775ac2a7ba20",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P1_Slides.pptx": "2ef65e795c6945f51d2c9a22bb43455f32ab4241f8513b6a4ec5184ab11676cb",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P1_Staff_Answers.pdf": "0f0c0c7df3ea7ad808676e3fef28901fc113056b42a67760fe14fbc790a69d2e",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P1_TA_Brief.pdf": "0af9f5f201123db8d470f60aa74f2cd79a08e5013b281ecbd36ef63bf8661995",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P1_Teacher_and_Cover_Plan.docx": "3d660c332893ce26af7c855213100e6593c4d1d85634752ec2239229c0753aa1",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P1_Teacher_and_Cover_Plan.pdf": "f1d9ac128f06b521842647b0211cfef628e438e9dfa34efef1ec614c2dd15522",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P1_Tier_Pack_Standard.pdf": "d6360f0a7788496f754df39d312960b03bf3e1d282bb6a4a23a0e45e0096a0f2",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P1_Tier_Pack_Stretch.pdf": "ff403b0dc084876f308fc4705422049970b0cd7fa3529620c0069dc4689682bf",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P1_Tier_Pack_Supported.pdf": "0875bef764dd2dbb9a2c1506ce86dc6896633db1a71e186a5150d14d1a8965b9",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P1_Word_Page.pdf": "18fbadb050a0eaa7e1e309ec9343b8d076d5141089170e2bd994bb83d926e782",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P2_Editable_Pack.docx": "11e11cbfc9df692368cbf77535c041c3a63d994117dbade5a8a47c7c36393633",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P2_Knowledge_Organiser.pdf": "e3bf6f5ff6cc2e40fe3d94d29ade8d863845a6296e1977eb2831c10444e49895",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P2_Pupil_Resources.pdf": "ad255a4d70a904345492a323d5355f0fab067dc135c92041d1370921e2c17476",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P2_Slides.pptx": "96ff611a7975191a03a6ad4e30755bf79cde36e772a8e30f7fd580352312f1a4",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P2_Staff_Answers.pdf": "8b5c4a269155c079f5f09b7e7913a0f264575f60efa6d0573238d5d30a789df6",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P2_TA_Brief.pdf": "1f8d2d7e89992c90f3ed1c9ac43b20cfdef2ec851a481643af4a148f205e1b28",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P2_Teacher_and_Cover_Plan.docx": "4a3d7853c05e76416d6c4adb13086783ce08809650405f1843c89b70b95e979c",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P2_Teacher_and_Cover_Plan.pdf": "9e9c36a4180b44e41ce8424bf8c93ecc692c7b79e33415a56b2e55df5f6ec19c",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P2_Tier_Pack_Standard.pdf": "5d3d33474d0f91018346e5bcf668d29b15a70d9b7c9a04910dfddd1b48171496",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P2_Tier_Pack_Stretch.pdf": "80f4eacac12bfda9ee0b474775bd2b2d4f3bf8ce2b3c8ae35f2601a4e56be1c9",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P2_Tier_Pack_Supported.pdf": "31e60158280ff1de4fbf5524975c41b9cbd27776235bcaac9df940221d61da98",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W02/ART_BUILD_A1_W02_P2_Word_Page.pdf": "8198be6a6db2507a80aae1e569e91ded6b19504bb097efd55821fb4fedc004a0",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P1_Editable_Pack.docx": "cb34f801238d6e111d36d92e7702c10b8af1d5283be195ad36af17949ffb6a0f",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P1_Knowledge_Organiser.pdf": "83461a2dab5bf8e38336c089ba44b6aee3750c40e75bc0f599583efaa6657966",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P1_Pupil_Resources.pdf": "fc313725f66a0162fd627f3c13e75567db52eaac4b2de855798c8bb5231c93a5",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P1_Slides.pptx": "052ea509d0e88d7ebbf28711dade1696e99b3da53346990f45df28f157e25474",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P1_Staff_Answers.pdf": "4f94f4bf541116a5213dd7ab0ef2ccf218a46253edd28d5eb720b1f617e74a1b",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P1_TA_Brief.pdf": "e72a29621aa74631fe6f0193a4873d34a802e81aa77103b4c5916d33904cf9a1",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P1_Teacher_and_Cover_Plan.docx": "acf9e8f03c71ea177ee9aefbd81e03124bdac9c1106a16aec37d1b3e97075531",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P1_Teacher_and_Cover_Plan.pdf": "ad37ca4c97c35ee1f66b7d8e8523539e2d6a70d40d942ef5c0fbf38bd56c4512",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P1_Tier_Pack_Standard.pdf": "d90fa73c7732d3971ee249f05d5f5be517ba49cb1dd209d79fcb4285a4d60d72",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P1_Tier_Pack_Stretch.pdf": "f4ed90f8be4152c3abdc2b90241fefac89753bfd0f7f5e505ae8ac592e61e093",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P1_Tier_Pack_Supported.pdf": "b5f46be1e71d5d4f94bc22a2612dd4174a615617f67a3bb1820b171c122a0788",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P1_Word_Page.pdf": "8393b41a6681a74af4f81a63361ab50a63e78e6b4200abc5fe9aba790fef73d3",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P2_Editable_Pack.docx": "afd8222a430782ef9d4380b09720089172e967dfd1d5fd89a1af521118027aca",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P2_Knowledge_Organiser.pdf": "5667bc0ed944de465a94c09cee7bae1e91ea37e2e5d8741e786b406ea118f2cb",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P2_Pupil_Resources.pdf": "fd865f957c4f74e8de8565f7ad9e89f2ee533521c9c6002d17f5d09298bdb062",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P2_Slides.pptx": "14d473605bf11814cff1bfe5ac9618b80e2b1735d3f46f7fed92e55f74781ecd",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P2_Staff_Answers.pdf": "6536783520b5d570cb448692afc7787bbc005f7da80a247c0c8532d25e072634",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P2_TA_Brief.pdf": "2e2a99052b9e1346d1bf021d97e63930c87816877a2f4643052c95bc1326ecc2",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P2_Teacher_and_Cover_Plan.docx": "47c2cb1ce211b25f4af8988e2f838afc6c881ba95eb3a5855f22bb3ba6fa8fcb",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P2_Teacher_and_Cover_Plan.pdf": "014bd1cbb86af7d19ae532ab6e45141ae9979574330627921a19431ab41ff016",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P2_Tier_Pack_Standard.pdf": "c0da7b3595cbf166cfc4cdf747cb994691af73f39440040f68cdf6f1878ebf19",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P2_Tier_Pack_Stretch.pdf": "368d6bf0e498bd30157a450e26f06d0c7eb5a5570c8e3506735a3efbb74f7288",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P2_Tier_Pack_Supported.pdf": "cdd870b2061e6261b79b938887ec8bed1ddd68e39b7b0df381a3c5dffc463083",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W03/ART_BUILD_A1_W03_P2_Word_Page.pdf": "0b2811483bad8a43698c06d6794231fda78288b431a24af345df2e13f6494312",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P1_Editable_Pack.docx": "b446670a50d2a2eb53a9a1bdd53268853eb204ea4026a68799e14c8f96b8fe48",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P1_Knowledge_Organiser.pdf": "b88f418198f9eb17b2e5dfc9f366c1170b0c038ea0bafa4f0832659482ff44dd",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P1_Pupil_Resources.pdf": "8ea0c63b7df7f3a1a8d38206d2203ffda8c416f4b94434d2f399af45de610916",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P1_Slides.pptx": "c310396f554082e479cb9203606a83f7f4ce620a60fc1c42649775114bc57d93",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P1_Staff_Answers.pdf": "41a7f560a0c01e9e3b3fee17a737b18a2e6336814dfdd647d416a52f6229b0f3",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P1_TA_Brief.pdf": "284e8e8974033de5dd2fed01ddef77dd992ddd2de14b35d2892df9b32e41ea5d",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P1_Teacher_and_Cover_Plan.docx": "94f98d13ac84d4cb534e0c0e64b0f91600bcdc53a6a52b2fcb2767cc85959754",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P1_Teacher_and_Cover_Plan.pdf": "83e904ddba2dcf25564f733649c43d27515ff4f3a386c4d16d73c569cc786104",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P1_Tier_Pack_Standard.pdf": "929046ee1937c0e6015399d3462a9990fbe140a8fbc9903b5165a6eedc6aae10",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P1_Tier_Pack_Stretch.pdf": "94a4a79834f05f4e74956eda5e8512937b060af85472f6ba3872b80f6fd0fa70",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P1_Tier_Pack_Supported.pdf": "96eef7e8fc4d5ee041ff561a62aa11d5890196bac0d2cec38cbe3c92f3261a4c",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P1_Word_Page.pdf": "9278897901c715c2ee56579104c8b0fd24b8a9c9843d565fb3bc165190096c71",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P2_Editable_Pack.docx": "e33f485d032ac70b1ab562337a2968c9fe3353c3a107d3e2e541eec5849c4d8f",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P2_Knowledge_Organiser.pdf": "f3f061ded794c7dc2fbda4714dced1545248ce29a78b18abc1c72c1772bf5f3e",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P2_Pupil_Resources.pdf": "ef28b7b08aee5d6585e982adcd6be6667ea70f7b4681056ff1a93557fdf3b3b0",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P2_Slides.pptx": "5e87aa1cf57342f0b0720f4a0b9d08753f58dffda444d0e583ee495f6bc34a31",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P2_Staff_Answers.pdf": "fcf01a01a0d75b88e96685a47bab91a56d45d22760e7cf7e715556e49f846330",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P2_TA_Brief.pdf": "2bae0a3ccab0c350f547dfbd86cb7e115c8fadabb3346b0c74eb0428dc73042c",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P2_Teacher_and_Cover_Plan.docx": "b65e365333db00262da92cc66993e35d7b3a04187635739dfef79c68650644c1",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P2_Teacher_and_Cover_Plan.pdf": "35e3b84b8d01c4c8262ab53071af8594df0ee4127ad6daaed8b5ae555bd31ffd",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P2_Tier_Pack_Standard.pdf": "cb00875bf74bc944331f20bd5ee9356a6db2baebaeeac40f7d49490732a6f566",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P2_Tier_Pack_Stretch.pdf": "b1e7f43ecd18930989b5d4d303b13fb5cbcd19c819ca9a26c252289deb29e0d0",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P2_Tier_Pack_Supported.pdf": "c5e4dbba1f12e190001b0b51780a893ae5ac5117aa8730ec775a0b4c5f11ced4",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W04/ART_BUILD_A1_W04_P2_Word_Page.pdf": "669ff823e92ddeaf58ba405131d155560ed84388359cbdb98b6a4d50630bacf8",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P1_Editable_Pack.docx": "8c35e6a888c8510900deabda13884c2dd2c7810802a222e240760693b8aa5a36",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P1_Knowledge_Organiser.pdf": "12eb2e63c3da03e61c333881548c361ab907365d83c346ac62df69f112bec82e",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P1_Pupil_Resources.pdf": "671594fe271dad7d2d2cdd94983363d33608942ed87a691e726118bc27f46cd3",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P1_Slides.pptx": "c81c2b4f9ab869cd782f88861dca71c719822a0ede198b7268349714cb95d42a",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P1_Staff_Answers.pdf": "d6a64cde06dfaeaa8a02253517318dc330792b348b46ddac5e3612d8f4c3539c",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P1_TA_Brief.pdf": "96916bd6d4ebdfed61a9b85bc06a7a86623e60c483b434056ca6ddd83ccec569",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P1_Teacher_and_Cover_Plan.docx": "768af5d8ccbbf38b4d2116986c7f4a37304cad5cad100cbcfdecf1e37f984e12",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P1_Teacher_and_Cover_Plan.pdf": "232a066b16ed1c027e00b957f4c9aa14bd895ca91ca9da165c0771c754eb1294",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P1_Tier_Pack_Standard.pdf": "29f7c229f245b9e6565682aa15b5a4d2c2c36404c4cb1ee49b26ce165cdf6929",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P1_Tier_Pack_Stretch.pdf": "a80e778de06554e81130142c71363b2171428702954ce058362bb91d8f4f67d3",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P1_Tier_Pack_Supported.pdf": "02be7731bbe4e44037379e884d9952e43e408a3d8b4eb8fcb28cba9fffd3a65b",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P1_Word_Page.pdf": "3ba639fea7c0b4560d8b30c156db59de273d0cfdd20fd7d1403539aaec1592a9",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P2_Editable_Pack.docx": "51904e3e41a7dde7fe5cf0a92a7be3037526d9247c00f3fec2e80ab86e6a90e7",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P2_Knowledge_Organiser.pdf": "c13815ab968bda7fd520220a0ad7eae180af56ec4a44c6673557ae635df8af70",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P2_Pupil_Resources.pdf": "fa2be6ce11549bf3fb97daf18055962d8a922351402801e1fdbc112e2a3bd199",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P2_Slides.pptx": "f57404bec0b9caf0be31f76187329f56b7c1da6f12853dc730cd78cbca3151da",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P2_Staff_Answers.pdf": "53d4b660aed13b244c7087a3fe425b17b72d4bc7b892015c38ede477d49c9d1a",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P2_TA_Brief.pdf": "46bd00c1e85b9c05af27ca998cdb2b37b7b115f3e96870a650d346b3b6858138",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P2_Teacher_and_Cover_Plan.docx": "b58b33efaca7415c514126314a7ae2fc1d698ee2453f4b20ecf65a72a23d340b",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P2_Teacher_and_Cover_Plan.pdf": "4179cbcc366de65f2b852391b1e082027aa2bf09ad19b91bb8b9bf1971a8a8f0",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P2_Tier_Pack_Standard.pdf": "e97a7d0c092f21a23eaae08b99586462dfa9db0eeae1661bd853f32b91fe053c",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P2_Tier_Pack_Stretch.pdf": "f18971c1738590c8e9af575511442247dd7b47a90deddc93eae737f16158dce7",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P2_Tier_Pack_Supported.pdf": "d08398870a23cef0ade11bfaac9f85b0869828c4a812420d02cd612e68a3f3d9",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W05/ART_BUILD_A1_W05_P2_Word_Page.pdf": "3ec74bf953fcdfdafd69d8cbb27d8b5a483cf6cf8aaf3347656b6e99431d4623",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P1_Editable_Pack.docx": "90df7f8506026c6ecca94ccae1c7f46021a1422543a89d063f498be64f6ebabc",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P1_Knowledge_Organiser.pdf": "9ecffc70a54d0a3ea9eec69fa0011084933dcb556ea7caf7eaf815c2b34704f9",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P1_Pupil_Resources.pdf": "15a4b1b1ad4604545f8241629b09878b28123049acb3c4926a25fb5cb9cd59af",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P1_Slides.pptx": "c614d90c8ac8534f2957a26b873d22af342687d1d9b28ca68426bb43b7b455d8",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P1_Staff_Answers.pdf": "9ed5613b90dc6a385ea023357ada5db356f6b5c411d4de80b73dea8ab873586a",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P1_TA_Brief.pdf": "64c7dc36994ae004c8a441a17e8381b433dac2be8b02deea3dbd8a890e4658da",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P1_Teacher_and_Cover_Plan.docx": "74a83c0d60ffa722c22a7846c69201249576ad4f873cc2787f4d9d8e0acd92d8",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P1_Teacher_and_Cover_Plan.pdf": "6add0c7bc24ac46f7d65c6cb9cae032a64a3fbed362c86f5e058e161a148f5d2",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P1_Tier_Pack_Standard.pdf": "64f90ce73d057780f179e4223fdfa5dc8301646481877089a17d3a4d61a77443",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P1_Tier_Pack_Stretch.pdf": "7fd922de644491bbea4053d079bd03a8cadb5275d9a649a82886a4c3faa89b1f",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P1_Tier_Pack_Supported.pdf": "fc36afbccab74e784fb6dd5d006ae87abd77a5d6d76e9fc967f37bdffa986fac",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P1_Word_Page.pdf": "bbf89116944eecc688e94a876c7400ce2fabeee41be5d86f011cd9f708e6d22e",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P2_Editable_Pack.docx": "af85aa58102a4b829c577282623f3744a2f90c2191694f7790ffddb0d414dedd",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P2_Knowledge_Organiser.pdf": "494e715961082d33f2007a13634def22ecdd0a3a5a3d3b64346dbd577751527a",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P2_Pupil_Resources.pdf": "ada123782b02e4f47e16f51ae45232a58d3a5d242802e4f20efb56597e18aae1",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P2_Slides.pptx": "2cac0835828bf8832e8aff9ac5cb18d78ce60bb5f4593a65dd6a6483798ced2d",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P2_Staff_Answers.pdf": "1d5c283cf92b204caba54a64d8a5b925fb4dbf86533f8d43e3aed91eec4896fa",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P2_TA_Brief.pdf": "b81eda978c72d80578da01dc654c6d89880b2d9bc92ccd895144aa16d591e7f0",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P2_Teacher_and_Cover_Plan.docx": "acf257f5221ccc67e5fbe3cf7a4494012e4c0d658201efb9897c4c3ed5a15c2c",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P2_Teacher_and_Cover_Plan.pdf": "d96f4686d0643ba1b6e304afe0ba222fa85fd05c3ac39c18c1ce4e7f566f7e51",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P2_Tier_Pack_Standard.pdf": "3859d1c6a02836d78b48b5a4debcf38d9ca585ddb6a058e0d55bd330586edfbd",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P2_Tier_Pack_Stretch.pdf": "80e99fb12efffe5a7c192f240e4d9d9fe061572e6b51d67401f09ec5e2393342",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P2_Tier_Pack_Supported.pdf": "67f5a65faaa5571acfa8dd9ab1c49c0fac81bc00cda3fa5a4e5c35c7beec3835",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W06/ART_BUILD_A1_W06_P2_Word_Page.pdf": "3343d91e1d8d93db8d448d687679206009d74bce9acd1d26c00f3d76acd0a2a8",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P1_Editable_Pack.docx": "ab7003785009ce2f9b0967856eda94fa8890ff7e49102dfa6159dcd1ded66ffd",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P1_Knowledge_Organiser.pdf": "b9467fe0bc3707d3e1dd366cef5dd10dee8027de2ccb5c66ef240438eb7249d6",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P1_Pupil_Resources.pdf": "926de86f4b0a844f726b794486c7e74452c2a011f0d06af557c402ccd016fddc",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P1_Slides.pptx": "01426360d0a71f619ec3ccad2ee9ebc3051ada5a5590d0561102fa6ed6332ba7",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P1_Staff_Answers.pdf": "3cb948034a9040c3ee579c937870e9c7d4660e42cbe6ab89c909112d9e6debba",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P1_TA_Brief.pdf": "98a5cd07b378584b9647831fd2bafb6451898e474de4f02604159810e29a631e",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P1_Teacher_and_Cover_Plan.docx": "f6c016418031a52fb0a8c4d71ae45816c46b5989fe2965661e23471ff361c2c8",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P1_Teacher_and_Cover_Plan.pdf": "dd774e671fa810e7d1655aa2bbb4c60d21f4c09ba3244156e86900dc1a76dcf8",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P1_Tier_Pack_Standard.pdf": "15ab8e543a81697839077fd6a1214767d4641915bbf999c6ec9b1e7d8024c4a4",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P1_Tier_Pack_Stretch.pdf": "7b7e8797dc3e5a0bf704ce448397bfa8b37ae40209795af1215cee136ff4bfa9",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P1_Tier_Pack_Supported.pdf": "ab27142d446bdf88ca7804011f8b30ed239239b6750afa50344ab6ed9b646bc0",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P1_Word_Page.pdf": "ee397dee30e81d567bac8da12bbff815a9c60d30b0f39b264be0c5e0f18fce44",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P2_Editable_Pack.docx": "6ed7c0d0d9aedcf1b60632a58cff66b7a12ae5eb877fa27bd677a8db005a80a8",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P2_Knowledge_Organiser.pdf": "64ec2be2a6af20bd1f7f2167bbc7e83d3c46b47317beca5a1e14242e509aadaf",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P2_Pupil_Resources.pdf": "24c0f00077df9743e56879003a1bcaef0755fca66cfced7335f766d169ed25d6",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P2_Slides.pptx": "6b808825f6fc7036116c21314b6cd3f0096f3ac631d81b05695246ca1334b87f",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P2_Staff_Answers.pdf": "7984880f00c454cd43ead71c52dca497632bc2d1bab05fc343c1d3f57236ba77",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P2_TA_Brief.pdf": "a20f5b4ef6fc114436882056b7e0b9e9c28fc1c1f5187a11a28581017df60bb2",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P2_Teacher_and_Cover_Plan.docx": "8f85ff2deb6d070103b823b29214a0e5df09eb23f0b7c7b6c40f1c3c9786ecbb",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P2_Teacher_and_Cover_Plan.pdf": "e68c787ef738e8675000ac2bb650b216c05e3e42bce187579f4a85ca1ec51564",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P2_Tier_Pack_Standard.pdf": "9f2843464b62cb9a410905f366a361052cbf62293011e34d8126917d0cdb86d4",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P2_Tier_Pack_Stretch.pdf": "fdb5bcea64b6a35ad17a624d005b5500f3ab6fe4da786af1edcc519ba538711e",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P2_Tier_Pack_Supported.pdf": "db3f10f7ab67f97f6d0fad4a9302f0fd59366805e41c7e898b61ee263b8aa697",
        "Art/Build/Autumn_1_2026-27/ART_BUILD_A1_W07/ART_BUILD_A1_W07_P2_Word_Page.pdf": "52b8b45b8aeb7ff920a779bd1dd79f393a0a8425762ea243aba8928b7ad11a3c",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P1_Editable_Pack.docx": "ad5f24874b5a879b81fa516e074728362a654d64b20bbd365c1ba42580a9f4d2",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P1_Knowledge_Organiser.pdf": "dbaa8b4c1a17d84c1d3b53d99f7e06ae3ea23071ef559bb02eeb775947f1cb7b",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P1_Pupil_Resources.pdf": "ca4daf5305f2cd7cabdcfadd9bfa2aa32bdfc72dfdd1c9bc7d288f724775d1b5",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P1_Slides.pptx": "98ac28d45aeef4c337ec8d81b92cfe5eb9c2821d3bd76cdb942cf04a9bf9cefb",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P1_Staff_Answers.pdf": "5b9a4efa1d4549f7181be3fcdb66b0439d6778e84f96cf5ec425423524836da4",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P1_TA_Brief.pdf": "38dcb01bbcb125b8aa7cbdd48a4b65b673c4282d5c33b1e7c0a16aafb375372d",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P1_Teacher_and_Cover_Plan.docx": "ca101f1878e886057bdc38745804cb05ee491984dcc17366bd43644c742c5ba6",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P1_Teacher_and_Cover_Plan.pdf": "53cb2b0c65958c28c4725b00a7c7c0e478259a12b8bfe4496d788181e244890e",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P1_Tier_Pack_Standard.pdf": "fc4f74c4198b8114b3d0b0dd98fa2ea84c25ee45cbd8562ef2345f736bd8e9c6",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P1_Tier_Pack_Stretch.pdf": "a1b898d4af2ad2f4273cd17d5dca96d723f07a1a5fceb151facc7343c6732688",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P1_Tier_Pack_Supported.pdf": "31051128958031c50d9780237c8a53b65007cfdf693e43dfbc579234387a4108",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P1_Word_Page.pdf": "952230cdca55a8c506c8c543993b796f320e2a08f61766a62710418ce2d962da",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P2_Editable_Pack.docx": "642a517db618a341afc9c0c6cfdab7b7b68f5444fed6449771990cb512605950",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P2_Knowledge_Organiser.pdf": "4ad108dd2c29b60797021f7f3895083bac5fb73f3a12f3f81f33d618e41d6940",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P2_Pupil_Resources.pdf": "2b849ec2af5edfc5b209c4cd2a4453635347fb3605cf4682bd852b19c8d96add",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P2_Slides.pptx": "84af8e0dd8f3a8a3ff38f488b56edf8a6414273da3c2451e85841c150bf22745",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P2_Staff_Answers.pdf": "7e2ac2a844e5e863acc784e2d241b18e044e11e6e4b76c5e085b6f0f59e8c733",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P2_TA_Brief.pdf": "8bd0420d2ca564d750242cc4eebb6e7e47b008d1d2c36625a725d20a8b1d6752",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P2_Teacher_and_Cover_Plan.docx": "1e5290658795cf2f4988b6ca5588dabc20ce4854c8ebc38eec46ff15f755fce7",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P2_Teacher_and_Cover_Plan.pdf": "b0130c6bc134b635cb6654f3e3ba56f40f38e38f5ed303d1f5928f7f022dd921",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P2_Tier_Pack_Standard.pdf": "e8c6b8a7e45088e02b8a843c508216409542f63c652a8dd67cc2c545068c36e6",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P2_Tier_Pack_Stretch.pdf": "105ae2f36e16ed4073fef7b6961bfb57e0aca3b70b80cebaea4f88a7b4977340",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P2_Tier_Pack_Supported.pdf": "8ed16b5e26e7c5fd7d7ccf455e4b40ee12064143759f0f91d8a96c62b856e582",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W01/ART_GROW_A1_W01_P2_Word_Page.pdf": "55ee8d4c815557b16f2828e07272d4155fd006054b6e7de90a11cf15adba567c",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P1_Editable_Pack.docx": "8c8fa0ab45fd88dbb5ced2653ebc9e1dd54b92cb3f6a8b694982c884c4f92a86",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P1_Knowledge_Organiser.pdf": "4790053ef8d9178db797074592f5302e5fa51d16c3403acfaa3b62e8c64bfd52",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P1_Pupil_Resources.pdf": "50f1ba2d57f50a5ac39d2ae34b660c3009999a3144228fac7b56bbac4f6c561a",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P1_Slides.pptx": "e8b75f550b39ba18f80978b288a4126e8b457ba32e79d4f6fb7c95ca8b257a5e",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P1_Staff_Answers.pdf": "e2c0c6affa61e981fa29e7aaf8777aced681d99b9125fdc6e5c3321841dd2804",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P1_TA_Brief.pdf": "0f124ec65aaf54b2f2b58edaccfc41d5015ae57a8b1e69a91d5efd5738d8fb44",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P1_Teacher_and_Cover_Plan.docx": "14961e99267efcfb5eb37ca2e6d3d8684ca9b3c7448111a257e10611947156df",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P1_Teacher_and_Cover_Plan.pdf": "d4dbe8d950aa37cbfe30417e75792904d87bb77906026d7da85e3056e2dc0067",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P1_Tier_Pack_Standard.pdf": "d78510b19ed21e7d3867444c84a52e05af7d42d2e3d2949895afe463ac37b6c0",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P1_Tier_Pack_Stretch.pdf": "ade87f8eaad2a55383faa08fa9f0dc3ddd09d60a975af6b15d0b191f598633c9",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P1_Tier_Pack_Supported.pdf": "b113fcc8341cad8df449e9b7709a37608f659bb45b08ec688a224655ef6fe3b6",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P1_Word_Page.pdf": "a9c21010db3ae7d83926348c864555f304b2fff81833e50e6ba2889e8273c346",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P2_Editable_Pack.docx": "8b349111d9afc0bc75e5b85c34fdb7e253e70cdb636e5529090226e24e3dae8e",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P2_Knowledge_Organiser.pdf": "9e4051779bb8357ee08eb89cd79618576b4531fec20c9a38c7592267163e1ed3",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P2_Pupil_Resources.pdf": "5116afc5b00b97a1e70921367deb2e9d00a19e8282aa2f12764dd73f66388263",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P2_Slides.pptx": "ca90b13f93ffbe9b00a0b044bb760a1951c6bda53b9787d163472fbd95fbf9e7",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P2_Staff_Answers.pdf": "64dcfd7aa100b16831a9c16022a5a9bb8477fadd8b5481a8a800672bb839edd1",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P2_TA_Brief.pdf": "7371e72c272978df737a6816599fc5b801a7f5f49b1916f833d33b4732a6ca50",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P2_Teacher_and_Cover_Plan.docx": "8cc739706fb093fdc796dff60bde87dd583479f6d79de89e56a9be54904e33d2",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P2_Teacher_and_Cover_Plan.pdf": "57ff96e9f5b9ae7e014d611da8ef2af4ac69fbec421c6ef98a7616f8469049be",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P2_Tier_Pack_Standard.pdf": "96b825358b43cfdf757abc2c2968cd32bebe8977c1d71296360315e83c1e62e9",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P2_Tier_Pack_Stretch.pdf": "ee329dab32ca5fb428a0dbf0e4bd0642774a16b0cd396a2c953fe3a2791c5f92",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P2_Tier_Pack_Supported.pdf": "975f2296cbc805a55c7f97e7043cc937ede16f9df93b0c9edff08ed46e3cc466",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W02/ART_GROW_A1_W02_P2_Word_Page.pdf": "9b9a5f5260c4a712441fd60be12c425ff933231df7f4719f393e66696a2c0246",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P1_Editable_Pack.docx": "bc88d54fd89a1545f2c4a1e131c722aebd03ecdb04a1b89f93cea78e72bc95a2",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P1_Knowledge_Organiser.pdf": "b64bb517d991e18f8e388fd970e1a90fbbee48ec6ba900353895b0ec0a9090f9",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P1_Pupil_Resources.pdf": "ec532cef87ff99dbcefe505790da81c4ee8f7713bf3c281e4502ad4eea846d30",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P1_Slides.pptx": "6c77a7ddc678f317af8d878cd588b7a4b20d574b59fc45ea50fea4e3acca232e",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P1_Staff_Answers.pdf": "82f3c71436e1b2eec7980eb8ceff5c2db78d24a980c37941e5d0b04080ef887b",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P1_TA_Brief.pdf": "a642c53bc36ea4e676c32d000d59c0f2a5a192026b2834a3ef0c654ce17edc45",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P1_Teacher_and_Cover_Plan.docx": "48dceb4e61ceb8b7d165bb51d3104b36d4e4929a462bf0e33eb9d11cfbb863eb",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P1_Teacher_and_Cover_Plan.pdf": "bf054cf1e8b806ff0e9498d9933ed2ca5ce0f45456511c1f2afe9b48d167b23e",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P1_Tier_Pack_Standard.pdf": "bbc8dec009c310e705c439e0b36a9f66dcd10c10d4a74780988fcc4812ec1dd2",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P1_Tier_Pack_Stretch.pdf": "2e4317b2ba8ab876b9108ca216f55fca5c87544f682373fcd487196277663989",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P1_Tier_Pack_Supported.pdf": "93406a30f971a48162023c532af28942150d1c8c93673bd553f4f06dcee9a215",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P1_Word_Page.pdf": "37cd9f7bd4f742a8fc06c66c3d0c702030ca93ccac7dc77c6e434e43011f1998",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P2_Editable_Pack.docx": "80cc1da2c13e9ad7cf17e370da5af8636a5442509b97e53bb113cefa3dc300f6",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P2_Knowledge_Organiser.pdf": "4ca1634fc7fad7bae6df825fe190d0d1ce6695226f1b2f8530d60fdd97b8f8c0",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P2_Pupil_Resources.pdf": "b320c949ebf95ffbfdca43b74c33fd1ccd12e59c63d7006b0d6d93d54d81ef78",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P2_Slides.pptx": "a0d9c698c6b391399136bb3c2191293fe49329a888f3a327ad8a845a97efee8e",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P2_Staff_Answers.pdf": "e434593e4fe0d72fa047d27696a852b4e30584ac00bb2a48279a432bf0604942",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P2_TA_Brief.pdf": "0fd6dc942dcb11d12894d8073572dc5a3a930ee03ab17caf570734facba2404a",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P2_Teacher_and_Cover_Plan.docx": "6e6f93d46a3fcce527ddd11149d175bed1e42d8750ee3d50a1baf9da497d708a",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P2_Teacher_and_Cover_Plan.pdf": "17d69f332bee5160e0beb404d99ab93c345904a000aacf41e59b1f54d7dd42ba",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P2_Tier_Pack_Standard.pdf": "d81faa4c1eea41eee324e82b0acfb9e384cd8c5d16fab05315592a4a418fa097",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P2_Tier_Pack_Stretch.pdf": "508a7d4db9daedf7dd1bd320babcbfbb0c9c26c608fd2501c5be2e9ba801f363",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P2_Tier_Pack_Supported.pdf": "f1be548f531f47f2e9ac2d11e37c255652287605a52c913deafe401cf4eac1a9",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W03/ART_GROW_A1_W03_P2_Word_Page.pdf": "c66153b16eb41aee5200cefc93d52ece2d63968e18367e917c5aa7a893bd58be",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P1_Editable_Pack.docx": "38932a3108606ec09b051d4965b366a74e64c896e7807f06eee450fdd45c3f10",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P1_Knowledge_Organiser.pdf": "141a48f17a548b3be51e3f93b1d8dae7713679071ab14180a2b21b3ca9dbb97f",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P1_Pupil_Resources.pdf": "1833b7bf82f89cd4a2291ae3f2777daeabe08b8024b8064817b40af999f8af41",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P1_Slides.pptx": "37e723db2bdc244bf17fa8b73a378886ff4a0dcc89620091eb01a4a95ce6c5d2",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P1_Staff_Answers.pdf": "c4d820e2694d91d841d610d919fa2e05894f978b907d116022ac99f3184fa3fd",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P1_TA_Brief.pdf": "ccdf8e88a76b9d681bbd9dd7d18663d2a2079ea12abe353d7016fee11ffd8172",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P1_Teacher_and_Cover_Plan.docx": "fd313969787d3fb4fada529277edf275b4cc21664ce28b3cc458b52368727287",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P1_Teacher_and_Cover_Plan.pdf": "1215e25c96cd2ce9bcb9e47a5834dd62e49faf33a67b0692becf7ae9a69f559c",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P1_Tier_Pack_Standard.pdf": "d09a6c37effe894c50291de142402ae9d1aa2421adcef039ba64958cba2b5c50",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P1_Tier_Pack_Stretch.pdf": "fd08a45e6dbae3efbd71fd4be044078ab3d25b1af81d94add51731c1d7e105cf",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P1_Tier_Pack_Supported.pdf": "08c547473fd86aac0f3a150547244f48e8c84ec6ca578ed531c062ae5aa9da4b",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P1_Word_Page.pdf": "228e0cf154d8fd9b797ade086cab72d11923ef23dd239c64c3c47c9c04ba6e4e",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P2_Editable_Pack.docx": "af038891b466fa13cb0e5f1964b837f66eaafe6e2f4779e59e39bb3b0e064204",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P2_Knowledge_Organiser.pdf": "aa01f6d7bf127ebeba91d5ad4ce00e0c8a909784067933d4023c9087491efb3e",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P2_Pupil_Resources.pdf": "0487063fca0a0e516355a09e4882e71ed0720967d0982696767da1a2c8094558",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P2_Slides.pptx": "162c0070a3d9874388b30fe377e414d575366bb4586aa6025c4e12d1c6a0cbc3",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P2_Staff_Answers.pdf": "efd1ca7d205769cd15de106e70a464e016ffa55550da79b3bfce60c96b3c2add",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P2_TA_Brief.pdf": "15f0831abc70c13e10e8dc1af10b67ad17a274505deeff36f053ef07f041e9d3",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P2_Teacher_and_Cover_Plan.docx": "6ad8bca262ec6624f064422661c7b836ef8117a36993881016df897bc33c88c9",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P2_Teacher_and_Cover_Plan.pdf": "07de1eea9fb2275eca1587a33b21cdd2a461dc2975a4858b792cff0890a67c94",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P2_Tier_Pack_Standard.pdf": "8eb62d5959cc4a1302f824739cefdac8f3e8796472e5c08e52118643a0ab8c98",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P2_Tier_Pack_Stretch.pdf": "f43fc2219679f3064c4e50aacbd285fa4e0002388bfe25fb4c64e44f3dcc0981",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P2_Tier_Pack_Supported.pdf": "c6935a37eadff6eae8d9bc48a1f0dfe715a568406d0be5a4eaee0d2c2c048033",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W04/ART_GROW_A1_W04_P2_Word_Page.pdf": "c589d791137957b748b4c4d96727043f4ebfbce774d318634c220829ef157c48",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P1_Editable_Pack.docx": "dc09b474d78879f0ed05b57340176e069ca10cfd117c7a0ee909ee978446ced2",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P1_Knowledge_Organiser.pdf": "fd6cad9f7a6f63f8b3fe16f9321b6a2e9f69c2c13f05ecf3ac7d1779b1760717",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P1_Pupil_Resources.pdf": "fb4b2a4ff9c9e83e436b504e5de60f92ce291145d2b15d87a941542154828890",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P1_Slides.pptx": "051f5ee79e9426e43dfc8ba629f50de3c5c8ba0e19f4f8bf38bc802ac0b339ea",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P1_Staff_Answers.pdf": "27775f42e28f95d9a05238a7f7f1737d04a124f5fd86e49b970855fc1bd1fc31",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P1_TA_Brief.pdf": "75d6b96a46a3e1a608b5e8c01b5ad7c9d64737f885fc6c11e1646efbef64f4fd",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P1_Teacher_and_Cover_Plan.docx": "888aec1d14062151dd832b89e12a40edd0541cd521cc540710edcde8f49d436f",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P1_Teacher_and_Cover_Plan.pdf": "4e3d74583d88c979f9d30d0491efab054285f951d06a1bbbcb5c3e7a2c50db6b",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P1_Tier_Pack_Standard.pdf": "0fde81027fece49274360f8d64fb3b57b3850ee2d916d56de941a44917d6b19f",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P1_Tier_Pack_Stretch.pdf": "f43a84e65b35f29ed32720e13e2ba086e2793e39f4bd7d75170732dd2ee1c788",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P1_Tier_Pack_Supported.pdf": "179b296530a03e427cb1f93819b05d4eab8e5b42fa1bd8b40f384e99c8482a20",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P1_Word_Page.pdf": "0110e6077ea9a61843c8834115ffa1b8674a7285bec157257b9e907489ac0ee0",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P2_Editable_Pack.docx": "e12f30bf8c0043dfc922c8d64c2858b6068e5402df9e05d646c8bcad0c29c4d4",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P2_Knowledge_Organiser.pdf": "5c7fb25882755a6859470e5c6fd299884c816a85a24bb118c3ad77d99340108f",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P2_Pupil_Resources.pdf": "03f5466fefe2e2d5e23ba31aa268773a3b5392ed701f38ced8efa0833662cc2f",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P2_Slides.pptx": "8d14316afa8a566f99f7b3f6521f1badd75d375061b615bcba0435874d8bfeed",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P2_Staff_Answers.pdf": "567c2fa37dbc2293ab8ac8b9c2c81e42a48232edde6c3160675529a1ad36b2f6",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P2_TA_Brief.pdf": "e8ceb296b419dc11cac4bbaba8afd0eec4a8823dc2f7ee6d0ba57e6830815ba7",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P2_Teacher_and_Cover_Plan.docx": "0f8990691d6ead0e7e89411199fb6a18ae9b692d1f5e80897eecd613fcd54e06",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P2_Teacher_and_Cover_Plan.pdf": "17b3bc7cbf6d2edd4ddf0269684f7cc2e136d92cfac14144de22fa775314dc42",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P2_Tier_Pack_Standard.pdf": "c45f872639d3d0bbd2d48ddac5cebceaec5a93b029eaee18cec09f1c7130c670",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P2_Tier_Pack_Stretch.pdf": "448cc8a1507cef4f6bcb996fd93ce6ebf3c9501162f7f4329707863297eda685",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P2_Tier_Pack_Supported.pdf": "a84bbdccc9de492b551ca77a1a30792dc941a0d83b6a48253ff309313c3587e3",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W05/ART_GROW_A1_W05_P2_Word_Page.pdf": "0599ac9606ceae78e2bad760176783aef645937be1231bfea58e524f37e34416",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P1_Editable_Pack.docx": "b24e2583173ec1f8f871d0fd238706ffba73ecd11e5b657c03180f0202fb9ea3",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P1_Knowledge_Organiser.pdf": "ef8c4702ae07fd2b070f0b1b2dd8bdd33fc058f0b47fea5ef75351d0466e1792",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P1_Pupil_Resources.pdf": "db7f677a8254dc3fd9652e5ba85c1d4deffb269aa2f8348db6b56fb2304611eb",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P1_Slides.pptx": "e6842a984e042936d073446ba2bdc1fa4a512b0129c0757c8d65c3a8d5020f86",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P1_Staff_Answers.pdf": "0d3df3e0242069dcf14c46f920ded07d87b893cfe82ee287040a2c7728720b88",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P1_TA_Brief.pdf": "ec889a0b012e1e1c3b8ed1dfba5cfec43a49b8d00b1e5d2e3302122c7a94b968",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P1_Teacher_and_Cover_Plan.docx": "e7716f574c308548b577e51787e4e796bbcc5fd4b6597865ddeccb6a5a3de34d",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P1_Teacher_and_Cover_Plan.pdf": "d45669876fd0a1dcafa9ad2bc1f6c17ae9eaea03794aa84f12e502b8e7a93972",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P1_Tier_Pack_Standard.pdf": "5159bb19a3d08ef5fec88a5dc1e10d7e364f95600400754db40456f7cf4e8636",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P1_Tier_Pack_Stretch.pdf": "80325fe1ac30c03e795c6889859e5451f2daba1cc997f34b0fd25e8e41175c61",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P1_Tier_Pack_Supported.pdf": "b9c3022b8246096b905239cdba6d79894aa7f840178a8e3766c9a4a59cc7b111",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P1_Word_Page.pdf": "22922fbe81ac9e3387d6403b7ec26c9882f90ff4aee2ceef0b735069b6c48ce6",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P2_Editable_Pack.docx": "e616f45401a63059ae31ad4ee757783641c4dab0118a8c1cb7ace0c6f2828f71",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P2_Knowledge_Organiser.pdf": "fd0c6a3dd33f700ca47c5665f3bd2863de1fd8bdfe5826d177148416653d466f",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P2_Pupil_Resources.pdf": "656ad193c6b9d8b5c84da2fa4f77b39937e064426170b3de71a6db6037aa680f",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P2_Slides.pptx": "bf2be32dbbb7cf7676e4b8396d5f720eca7199698d6376ba035bb891726a6e52",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P2_Staff_Answers.pdf": "901b54c12e14d31d9d052564a09c040538bfdf465e6960a8e603910424970c25",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P2_TA_Brief.pdf": "d7598f4cb7b3a38799e10e7d7c29ddce06240acc1f418d16d0aa5f5c8f917605",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P2_Teacher_and_Cover_Plan.docx": "2036c699934304f81b82f6dc02d45992e823916477a0b8881f44fdbd48183546",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P2_Teacher_and_Cover_Plan.pdf": "b98a689794a21a11d4607080a2f8f4239266aaa5d48be024ddafdf496d04a5ef",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P2_Tier_Pack_Standard.pdf": "d45c0427d9bb571bc359edeb0cd33be6102963ecc2eb43ab6cddc25e7a6318a3",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P2_Tier_Pack_Stretch.pdf": "cc38d08cc39df3a6ce2bbce85fd41d41552bb026cb8b5db72c9495ac8b86998a",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P2_Tier_Pack_Supported.pdf": "ba0d9690ea8aa8f8cfbef82054c94198fd33fbf6bf1de1a8aa4b89dd1cae375c",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W06/ART_GROW_A1_W06_P2_Word_Page.pdf": "51e329d56d5a9963597c94666720f8b47aaa40d36acfde1b6152292e45e9a170",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P1_Editable_Pack.docx": "faff7cdce28c234e66b3eab2bdc805c02efae102070356e48ae7b9027783f93e",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P1_Knowledge_Organiser.pdf": "6876ff68092b8fb34aea4a065c139518e21236a8a9622243e30ae1a11b5a979a",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P1_Pupil_Resources.pdf": "062eb206ed2444dae8808092393fb9ef45a687b1aa2af2e08c36390a25b38b14",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P1_Slides.pptx": "f35a69779e4e8d99449d56c85305da46c375b49c7f88c815884af10acbf01a5b",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P1_Staff_Answers.pdf": "5469c437db2b18c0aadd8d0dab62d1c3c14dfa56737f7c2c33a3696641b1c130",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P1_TA_Brief.pdf": "c787bbe14c73cd19225719cf092704b6e894a0af2ab501276d51c28ef5d1c505",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P1_Teacher_and_Cover_Plan.docx": "8ed53b6f02aa13da2c2823c8ee4996b0fd4429ed8f4a9b49816b8d2438ae6be5",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P1_Teacher_and_Cover_Plan.pdf": "0d6e872d984832e8d2d53449177f6b94e7e7c8d9df962b6cd5ce6b0c8720acf0",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P1_Tier_Pack_Standard.pdf": "55e6f9e8fdf10b5c5956f15bd56edb3cdc2930a4eb5d075bd0e5fcd00354766a",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P1_Tier_Pack_Stretch.pdf": "740048b8392bd37c3e5748f0e3be9aa192a2289473783b1f0236d7a6de518a13",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P1_Tier_Pack_Supported.pdf": "ff59b9fe0177704b0c0c9a2c00f742d781ae9c7aca33e23c69a0d6a5905c0ef8",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P1_Word_Page.pdf": "307c6559d2e2e0e8ddc5f70c879a42535c783c4addbfddf37915f5f7a315bcf6",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P2_Editable_Pack.docx": "85cb0bf2715f929cde94d56354834b6a70b17bc9881096a5bcc3b7731a8f9ee0",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P2_Knowledge_Organiser.pdf": "16671843976eb67923bbc42f68bced7b5713fd8cf259269e9f71387fad603bc8",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P2_Pupil_Resources.pdf": "55a6df6e7f1c9cd76198bf888e548917ce34f1e41fe98dc873e4a0428e268c15",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P2_Slides.pptx": "a1c6c7ae595be6d536fb458d9fa7ca873f3b46249e087bcbefab5d1082d0f323",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P2_Staff_Answers.pdf": "0819a35e731c07c82a1323be5d3a4c9d290c48501495fdcf87ee602e12a03769",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P2_TA_Brief.pdf": "1140bd23d6c7daa667a7f4122b8cb9eab7b965abb91eb245a15df9d7bbc44eec",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P2_Teacher_and_Cover_Plan.docx": "4d1413d7cce711ac8da033fde73f7f15fcb5ff0d2bb597ef013272c83c710368",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P2_Teacher_and_Cover_Plan.pdf": "e5343c0f6b5ee6f4201d1467393767b6a670a6c35ca818f56cfcf0288ab16ee1",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P2_Tier_Pack_Standard.pdf": "d91e9529b47d3be70fc876fa4c0aa138d801b662454019f52b51f51ba5781af2",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P2_Tier_Pack_Stretch.pdf": "9b6a219d9958a70c2e80b7b5d607369f03d6be5221fe9e446f236ae39574f8fa",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P2_Tier_Pack_Supported.pdf": "fac2d2522c0e2befac7b3be72a4f2c5e864e8630ad6930bf7e9297065b318693",
        "Art/Grow/Autumn_1_2026-27/ART_GROW_A1_W07/ART_GROW_A1_W07_P2_Word_Page.pdf": "7a1dc0126cb69b7f7e0729df0498d35d0e16cc5ab95665afa3272af2a39d54e0",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P1_Editable_Pack.docx": "92a821f1efb305746b0ae487648e6a42954d6e100fe53ba65cd786a15e9d47e6",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P1_Knowledge_Organiser.pdf": "24f4168320ed6debe178295a842430f8b830df1e9e89178d1fcbd35b809ed807",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P1_Pupil_Resources.pdf": "6a47926cb2e2d07342fd1a0ff590e34d2fc43ff9f53d36a55612985310a2e64a",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P1_Slides.pptx": "4f90791b30dd14c27135dcaaf55396875d972285e439de5c3c6fa821547ef942",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P1_Staff_Answers.pdf": "1b0fc16881d8d2f062d75d8093fd79b048d4d02df15578ad414e30c8128437f9",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P1_TA_Brief.pdf": "0f95d22b233c82c447a84040a2c26ff40035d747df0fe81472738a5c876aa393",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P1_Teacher_and_Cover_Plan.docx": "0652b8c4eda2e3bee7548e1aac8e021fb7d5950584814dc9c7bab4e9eb1b9e75",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P1_Teacher_and_Cover_Plan.pdf": "ba1b5da2a454c918c722efd6288232659f6900e8b41831f14c829206cff8e74e",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P1_Tier_Pack_Standard.pdf": "411e2899b73421c96d47d96020dd507c7eff583b3ec8d43815e7b75e8d6a8fb9",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P1_Tier_Pack_Stretch.pdf": "33c0e081aafcefc2133cfaddd9b225e9f72dd1e96c164ebdf762230d2f0045ea",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P1_Tier_Pack_Supported.pdf": "ad9b40d38068cdb7ca1390c610083ce11c4498416825b7c82361a644deebd35d",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P1_Word_Page.pdf": "ba21199e34d98ff9cb3060fb931ed4ec5fe4dd1908f009bfa514886fb2583c94",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P2_Editable_Pack.docx": "f769a97aa02bbd6641513e978ee2a2a746c14b2db5b6dce972d08f9584238b9e",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P2_Knowledge_Organiser.pdf": "6c349b7c64655e8c36cbd6cabe07e58695bf26aa396327a96482b19f506ea9cc",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P2_Pupil_Resources.pdf": "468e33b77e186784b786e808edf78720ba954d77648ca039696b83e25812ccaa",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P2_Slides.pptx": "93e3697a7cfd9c90899f0038e9b449fe3aed2caa32f97b7c604e2d499d8b57f1",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P2_Staff_Answers.pdf": "05a13be235d1f12ad812fbbcfc2ccfc7534411c347e8335cabe708a7dfe56642",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P2_TA_Brief.pdf": "2556aa5865fa794e249c86b135ac0fa2f2f7653319d100698d03a3119d7c7615",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P2_Teacher_and_Cover_Plan.docx": "e78143fafebe3789104fe1cde2ec7a465737c1fa9c41be6b5cee1acf38d83a42",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P2_Teacher_and_Cover_Plan.pdf": "f329ba103e0c4c19ddb0138bdb3c7f4e61a0d79776b2f20068714fe7879bc246",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P2_Tier_Pack_Standard.pdf": "faa375a3a1b08e60ae82d8d1cfc30905f1e2fa975fcf1f3728eabfeef4dd4a92",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P2_Tier_Pack_Stretch.pdf": "3355adfefcf1cc7e72bbf888748366cdc9e02a7630b107a136352bd143125fd3",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P2_Tier_Pack_Supported.pdf": "2f60ef242735d15cd2e4cd65f6faafef037d18c52711b3c753da1dcebb3afb20",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W01/ART_LAUNCH_A1_W01_P2_Word_Page.pdf": "f824d17ecb19972a497536967a07e32dbb9e5a77028f67ff6aa2ef3320a6ec34",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P1_Editable_Pack.docx": "8eeb594f7fb9f6290dd74fa8e23d2bc4193f2423a8b235dc25f4cced31d91041",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P1_Knowledge_Organiser.pdf": "2b09698bdc73f8863a3486c9fecc18e70cfe680b98072912a4544eb2034a489e",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P1_Pupil_Resources.pdf": "8e1b7bf56bd92cf4c485ecf4dfe33f150786e3977ddb1072cb33e94153f1a2b3",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P1_Slides.pptx": "a2ec13a4c0a44ba60ce1c9696ab7b70ce7a80705bc79a1e24e42a7b893cb42c6",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P1_Staff_Answers.pdf": "a3ba86d205725de2f66c9c95cd110b4cabdbff43775a85352eaec4436609b6ad",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P1_TA_Brief.pdf": "a254627661ca3f0e019fda538fa0782325b49fdb65ffdec558300a70d1538208",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P1_Teacher_and_Cover_Plan.docx": "60bc143473e79c12e6d99e912b2016f745bc31ec5143485b6521def2872bbe17",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P1_Teacher_and_Cover_Plan.pdf": "516595fdc8dcf2313d08612a6bfaba80ce7843724883dbb778289e5b97d1baee",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P1_Tier_Pack_Standard.pdf": "167b51bbc1d144e679aad29005faf1ff74c9a168358bc4159c21dda5533001c3",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P1_Tier_Pack_Stretch.pdf": "95a9b5eaaa2630b7b247eb3cb33bbe3e5b7c334006761a0b2497b05ebbf92367",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P1_Tier_Pack_Supported.pdf": "39b96578882bc4bd0f08aeb42dc8b47738309c62f02914bc5fd75cccc4e072c5",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P1_Word_Page.pdf": "3ebf165aed56b32d0fb7cf89d220f9fc337f63137e77b9951bae0a6ba00e1e5f",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P2_Editable_Pack.docx": "3947e1e25fb1521d7d87081eabfbe6436af65f4e093a7e0c3e29b1ef5f654c53",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P2_Knowledge_Organiser.pdf": "d4405f025723958643a4ba3d7fe702352d7dc920e395ab1b048b44c4285c0efe",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P2_Pupil_Resources.pdf": "7ccbef86359206a65e132958bc2bd9d99a1427ebbb74bc176039d1575a708e08",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P2_Slides.pptx": "4e138f1e0002a8b6a8a80ebe6c0e206b1d30989d9c9fdb19b463957b1f88ca7f",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P2_Staff_Answers.pdf": "dbf851aebe79abc3cbd6d0233b5d57c7bfbeea0d1dfe0c4d1513ea9e60c50c44",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P2_TA_Brief.pdf": "89554c6111b2814b468e39865767d8d7b73c2f694e7b467e12a083b65abd556f",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P2_Teacher_and_Cover_Plan.docx": "bf5b80452401c3afd6a20ceb092e2239540a6c613174d1d4dc2aab1bf943caf4",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P2_Teacher_and_Cover_Plan.pdf": "76526f170356354ef85af573f3b1247d18388eb77e557215e8ff6313b5630f87",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P2_Tier_Pack_Standard.pdf": "9cd116beb7003cab3dea6389ae1654220e44946523994f4ff37c1a8b5b6e0d23",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P2_Tier_Pack_Stretch.pdf": "9f6b9c25ac9c1a124f29bfa3beff4d5e2a1177d470e45bed7f4639b61bab1b72",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P2_Tier_Pack_Supported.pdf": "4275a6291ee747812809f0ea4dca9a0d979a4967bd8f3ad27550fd616d3d04c3",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W02/ART_LAUNCH_A1_W02_P2_Word_Page.pdf": "3cbdba01a938e31f999ef7dfc1ba77a19e47ae044572694c6f419d895a1a167a",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P1_Editable_Pack.docx": "ec8c441dcd3e91c8ec0aa85a4c9ba02e326f31bb5947130d0bd3d4b4ee1e7937",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P1_Knowledge_Organiser.pdf": "3d29ea0eb77c070b07aa66cbd67792b80bcb191c332ed1d681fff3b252f61934",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P1_Pupil_Resources.pdf": "75c980951340085a6eb71fe6a463ad98733f69cfdc4294f60612b156784bee18",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P1_Slides.pptx": "2dd797c5e1c9173786852f0d731fd51112b2850efedc316db176bd8cdeda3e2d",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P1_Staff_Answers.pdf": "88bf5152644b695ff4ef76ef9f328b099977185216d0a851ab3755dcd783b1dc",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P1_TA_Brief.pdf": "c219729ff448934e51edf79af692134cbc28e8990d3ea22eed4c0384b0fcc95f",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P1_Teacher_and_Cover_Plan.docx": "5abf7a4204ac5d0aaaebdd6f4c11b3b671aaeaba3eadf5d0242abab6d26dbe63",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P1_Teacher_and_Cover_Plan.pdf": "79a11387120c83ad4b6f493d349ba5f7ff39abaa3331298c537ab530d828a639",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P1_Tier_Pack_Standard.pdf": "93356976d7401f7454bad4d119a71ff95b50371b4580b4945581155fd7d4619a",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P1_Tier_Pack_Stretch.pdf": "4610a91390336e83c4039b25cd78117d33615d9b7cb12fe4bfbcd4a40fe0d705",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P1_Tier_Pack_Supported.pdf": "c80c1e4af2c12ac74727dc8d99d9c27e3fdd8ba10e4cd398db2264dddffc0330",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P1_Word_Page.pdf": "cff22a624a9fb5ce58c116beb71cf1a5447a05adfc9f37dd9fe31bf6d9afc587",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P2_Editable_Pack.docx": "b5582edbcb1b4bf80994c4898146e0ee7979a504fdd72da30eafa7e53598c399",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P2_Knowledge_Organiser.pdf": "31e965842d6fa28242f3ad41d6da4f14295c8a40251a16778e3a80564cfe4bd4",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P2_Pupil_Resources.pdf": "98cfb10c6c6ced2cfef89cf9c26f211970dae3843f5394b78d621ca3cef60fe5",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P2_Slides.pptx": "bca4da97795cbffd254646e9b03087912e92edee179afc91d903f9bbbc3fccdb",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P2_Staff_Answers.pdf": "cbb9f139eb32f58c25f0bb847b9d1523eb850f36fa74a4b27cfc4fd7d0e00738",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P2_TA_Brief.pdf": "c2b5aff163b801067ca57d6282e94a22644702e20b09a1da4d119cfb8bda3c64",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P2_Teacher_and_Cover_Plan.docx": "b388e11218aa40d585f9567fb1bf91fd0da89a7eae9fa68d5bb8812cca6feeed",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P2_Teacher_and_Cover_Plan.pdf": "445c2127ba004d20845cc900f5cec6ea628a56b2f873cccdfb0c1fd9dbb21832",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P2_Tier_Pack_Standard.pdf": "160c2b48cf583dddb7ed88a283f4b56b5badf3152a836de2399fc4bffe731a91",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P2_Tier_Pack_Stretch.pdf": "df2df71952e65557e50bd829045a16c2d51b1f0df7f0e00843983a5f2b9b2f5f",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P2_Tier_Pack_Supported.pdf": "9d2875eaf4a975cb8bb6169ae28a2a062ed2d7077ba86698c239ffed0e33865d",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W03/ART_LAUNCH_A1_W03_P2_Word_Page.pdf": "202cce70c72ca24017098b3810153c63e7200ae91d64ce50534120001d7b2042",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P1_Editable_Pack.docx": "c2d4b706660e40fa5c5679718b2e18a202277a06249ccc69d2a6a88cb79ed8aa",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P1_Knowledge_Organiser.pdf": "003b92cec71e21cf14b16db7778291e17bc526d83d4589f2a7dc55c2ac6b6f17",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P1_Pupil_Resources.pdf": "206f55cc904fe1cb9ba45bce62cb19560873b0af035c43c3976b3ae7ca5e6b75",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P1_Slides.pptx": "be6d706a2931e85bcf323181784c02dee5d8352c89d6217a50f38e872af8e486",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P1_Staff_Answers.pdf": "910224f5033ee75a41823b001a1e483f27d0884d8a4c556f21aaf81f7422488b",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P1_TA_Brief.pdf": "fa94d2fb9aebfe0e51182c556279142ca5fc1f3e6bdfc7405a6912f07dcba5f0",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P1_Teacher_and_Cover_Plan.docx": "c4728e569d0e680b3c6a6983d2f8226ea22762c70aa5bb945db319f26b6f8830",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P1_Teacher_and_Cover_Plan.pdf": "28eccf1da3f47da96811684ab2fd5594a6b5a98c4aa085b72da7d625534d7268",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P1_Tier_Pack_Standard.pdf": "34953d75a6227ab5f8fb9bed0f223fac5cc7e3b423c3021355891db1b105d40b",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P1_Tier_Pack_Stretch.pdf": "394482027822c0410bb53f0b71a1cf5f01ac2ea2d1debdebb51b06826b1ad117",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P1_Tier_Pack_Supported.pdf": "e776faf3a9c2ea98222ae1f64a8361c6eb27e07dcb7fce4648937250dae8221a",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P1_Word_Page.pdf": "4626c98ae68729fa2a19fbef21a17dc168d9c9e9e6ba2a650202e08385af3270",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P2_Editable_Pack.docx": "ade57205724500ddd59c5777f81db5d64b6b994755e72dc04158e4f073d41096",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P2_Knowledge_Organiser.pdf": "c199ab236b355065885779839b44f006645f2998486b15f4b955f6ba86973782",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P2_Pupil_Resources.pdf": "ae56a439658f5016b9e5a1e546f090994a8432e97ffcd2a06b619c12825122f7",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P2_Slides.pptx": "74796a22815a1edb67a346ef8029c8180091e217d803b41178f0aa64ff37bd39",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P2_Staff_Answers.pdf": "fe367dd4262abeadab84bfd303151868f2da4b4338fdf2c226247fc71fe5a5a9",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P2_TA_Brief.pdf": "e0e35b3ea146a7f058a3ac1d397b6e3257ee0fd4f55c9ac0bb95e7a84e7e5beb",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P2_Teacher_and_Cover_Plan.docx": "22b0e9f195c2921d2dc81fc47c0191f7a8d8c9efd398d90914458acba05e555e",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P2_Teacher_and_Cover_Plan.pdf": "39410d65263bee60b501f3d8e006408bc5d52d5d1de76500ee0d36c0c5ee5161",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P2_Tier_Pack_Standard.pdf": "6d10c665935d6505abbb04666b8a1ef45524af0bc3213ad9d3de60d6eeb73a9d",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P2_Tier_Pack_Stretch.pdf": "b694eb81545cc7bade232bc3e9142c41c5d1429bf239878813d9073adc47e5ff",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P2_Tier_Pack_Supported.pdf": "c5a8b4b33393b06c878306af03ec86272d2b56e19821b437c03ff9971049d7a2",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W04/ART_LAUNCH_A1_W04_P2_Word_Page.pdf": "9f802985451920be9db10a3546b58a68cc2549e31673c299cea3a409086d551b",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P1_Editable_Pack.docx": "d38a2ce82ef507056f39ec6b9ef76c8fc1828b7a7f12ffe7560e0ac75cef9693",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P1_Knowledge_Organiser.pdf": "d8c7e05605308285c3ba91b43a8330253ef21e5a905391322337a5228bf35cc7",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P1_Pupil_Resources.pdf": "2005e76de0e79f344842c6d1417fdb489a31ff42d1b4cd36522148a1831c399a",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P1_Slides.pptx": "530b00673c0ad5077920a6549f83c19353d1001c246ca8e25e626179e02515b1",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P1_Staff_Answers.pdf": "02d23d9765dc66f6be9043e3ec590de72617539d7ac5708b0570288feb33afbd",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P1_TA_Brief.pdf": "481834e6a318aa8bb4e234bfb757a96bc95d32cd1e09cacd7af92f4c54bcdeb3",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P1_Teacher_and_Cover_Plan.docx": "299552a0beb6938650b55e3472851c642bc25722938c672260a802d57b5352f4",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P1_Teacher_and_Cover_Plan.pdf": "0329e7e02047615dc494d3957afe285cb9ffb9115b9efee1ae6886d9409371b5",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P1_Tier_Pack_Standard.pdf": "beca66ba863d578b10e164309c5223e6193c1c4b5f80a08689dcc4977ef92b99",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P1_Tier_Pack_Stretch.pdf": "9deeb82c4dae506544989165da09d6fa40db8038559850ed442a1dcd52c0b9ac",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P1_Tier_Pack_Supported.pdf": "e8045361189563ef8a9a0dcc0576944e47cf4766ded2e0e7aac301774572540f",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P1_Word_Page.pdf": "c8a9032716d173c2a9072e7423080095d24d1f711370df5ce785cb29a9e27fd3",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P2_Editable_Pack.docx": "fd5899a504d9dc4968fa052abf3ff008066a6a1c5d2dae38cf881e62c71ae240",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P2_Knowledge_Organiser.pdf": "e2d15f417c50caedd4b72fe299ea29587dbd777ba9a21babbbcd35f84e49555f",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P2_Pupil_Resources.pdf": "ca57d08e8c38bc3a0634a42aff6c6191be09177daf0b5a0c953a633d2bbb7137",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P2_Slides.pptx": "6e9bacb387dbb7aeca50a1ae1a621376bfbd3120b42af524f20c56180cd91a90",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P2_Staff_Answers.pdf": "f072941e5e905616d701ed4f33fcf2acd6480ee060b7c24284aec7646218eaa0",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P2_TA_Brief.pdf": "04fa0c219e22a72ddf0dbbe4713bab40d3eebfbd502c95d2cde5c0e46809f651",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P2_Teacher_and_Cover_Plan.docx": "36c898669fb51b435b5386252659acd5cb69a0356412c82349d41f328223b223",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P2_Teacher_and_Cover_Plan.pdf": "7e6ec7b5fd53696953ec2b5cb98590f3ae7d1c4777a78219198dc31b52c36825",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P2_Tier_Pack_Standard.pdf": "5b36de370c96622fd075a8b2be223a7b4ab2fb637b5f95d6cbb167a51e263cc5",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P2_Tier_Pack_Stretch.pdf": "437c74b7e7bee19e0c0ef47026b55ae223f0a86087d985f35cd43cb1916b67aa",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P2_Tier_Pack_Supported.pdf": "aaa3fdae6b416a08fd2dd64c07385d60c56acab2a8894e63848514c37a07852b",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W05/ART_LAUNCH_A1_W05_P2_Word_Page.pdf": "78a7ff2f24e25cfcd9167c50c0447f9a1a148c5eca9a4da7e4a6a2846a4a165b",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P1_Editable_Pack.docx": "c5a8cee956b7868579744fed5df73a905b6d0e9b50cc3d1268651f91d0e74796",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P1_Knowledge_Organiser.pdf": "07dd56cc3d0772eb7cdd512c98b00c9dcd588c9f222adac37ea13dc3e262adf8",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P1_Pupil_Resources.pdf": "e34525f5a8905768f12368f8403971d609af33c1ad29e84dbad6ef21a0e0ec13",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P1_Slides.pptx": "9687c3b723caf7d4dc1275959c5685e0fc893897a2914e02bfcec7b8e6455603",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P1_Staff_Answers.pdf": "6f7f9b86e6ddcfeaca834ce22f1f6599cc05b9233f2d9e826f626e792916d5cb",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P1_TA_Brief.pdf": "0d7695891fc5837df664d9d24efbf2337bf1d7d74a20428e4342aae43f3b345b",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P1_Teacher_and_Cover_Plan.docx": "34fae99c9bd193521269fdcbb9dd6c0a8f85ba5135406d3244422fd3846f1265",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P1_Teacher_and_Cover_Plan.pdf": "0a60f271c42aa312de7cc12757fd31ca663b43a8a0fdbc9775ec821a77b7c6c9",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P1_Tier_Pack_Standard.pdf": "9c21df8ba235f18d8e62a31e48c0a766b9382ef13e28489517b5b7aff043b826",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P1_Tier_Pack_Stretch.pdf": "795365536f76528a7026528834c99f5e06a24d4ee77bbc7d864683a76d4c4bc2",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P1_Tier_Pack_Supported.pdf": "5e45b4f7e11d4040c5179e50e04199566033953bb8f6149ba14232a80dca8525",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P1_Word_Page.pdf": "76cf4b76ff502f4ce7078b60d70a0baac1b9a977979acd2616da0d19b069c26d",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P2_Editable_Pack.docx": "8bf8ea911e972049822ddede6e5ea46a07d8d109f519015b458f82e38b408311",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P2_Knowledge_Organiser.pdf": "77504b39008d21f82b45d62619709339c298e031b2de8d85f0a326fc110f6819",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P2_Pupil_Resources.pdf": "7016181f2d6bb1803c1679c0032ede6519a4ad5c7a4286041a6557485ddbbe51",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P2_Slides.pptx": "ab98bd9c26fffecbeb8b5de0212bd5eaef2f1710b678516dfcfd7fbb2f2b62b3",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P2_Staff_Answers.pdf": "70e4b7df7dc30630c6bfbefbdec0be6553992dfc45d408d908c94a307d0a70fb",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P2_TA_Brief.pdf": "13684d149f2fe6263b518250cd27ae975d26117b37641c90993d8a6071f4e839",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P2_Teacher_and_Cover_Plan.docx": "a34c4e9c27a647389e419278dd41336ce02fbd901281e3987ebf7a81c2d3cd4c",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P2_Teacher_and_Cover_Plan.pdf": "eb5f76be70f0c862e368f0e79dee191b41621d4d0a3fea45fefe0f1f5cd5d331",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P2_Tier_Pack_Standard.pdf": "af78697e4edc5a1fd8062de12c8577d24b7e435b7d7596e1c7ce54f705579274",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P2_Tier_Pack_Stretch.pdf": "eef854103ac4d331739fa48c04d4936fa75aa3500b2080d6585307042b3943d7",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P2_Tier_Pack_Supported.pdf": "6ef3c715cec4397357957313734824173fe343db4eee9cbc3cfe3211eddb69b6",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W06/ART_LAUNCH_A1_W06_P2_Word_Page.pdf": "75c70ce3f6e58e350ea72a438437c5c5c88ec36e8f2f90ca065d7ed276ff6a94",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P1_Editable_Pack.docx": "161314df5143b511880c74fd1f703d2d6ac05503c463fc915a58b03b79637e50",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P1_Knowledge_Organiser.pdf": "38b36bca5e6d20571ef4e6c40fc9eb1636b7b8649efbb8ec71b33f0935aeeb1e",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P1_Pupil_Resources.pdf": "5932196f36407c7adae6b431952fa3da0c9fbf4c40805cbdfeaaaa43570da1ba",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P1_Slides.pptx": "859bd8decffc1b17a60db8c05ce2cc7cfb2bb53398dba822e1c655050db36703",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P1_Staff_Answers.pdf": "62f5e8fbeedc6161d725a09bb22985187741646ae3a84fa70f2562d968f2a614",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P1_TA_Brief.pdf": "d238a06aa618f544b1559b4eda9edddede3706cf51b1685f9a54a6ced991820b",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P1_Teacher_and_Cover_Plan.docx": "9f8cfa7882a16e04dd4967106bf4dd9f69041ed00a7390904206f32765afa370",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P1_Teacher_and_Cover_Plan.pdf": "f74b23181c91030aac14bfc30020752f997559a19f7ce6a65347102da8e64184",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P1_Tier_Pack_Standard.pdf": "cc9307a4eba1abc6b33cf4bc94389849915118e3f33e251d6bbbcfad4804a80f",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P1_Tier_Pack_Stretch.pdf": "e08495227ce0f92a2529419f0b95d6d75dea3cca7d3bd5b100a8725bf59889cf",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P1_Tier_Pack_Supported.pdf": "e70b18539c0025f2a12d15e8e0ec658706e36ad151c3b0ed583f874655d5b132",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P1_Word_Page.pdf": "dd28fcbe894b89d7fbdbcebe2dd51fa052988c5d829ca82a399f8691d6726795",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P2_Editable_Pack.docx": "1657d6f28cd05d97c1d2ba605c071fbaf25ac70383346fd5350c57777aa70263",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P2_Knowledge_Organiser.pdf": "86458b0cae9019289427ba3ec01ececa8a8c37cfd106740fc0e785e018d2d402",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P2_Pupil_Resources.pdf": "4831b4d76b83366a8b4a6a0f2eb1c966d368e77eeaff244a4880b42cc26a4bc4",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P2_Slides.pptx": "b770cbb789ba1b10dcd51a753c9143cc5950e9c286ef0e2aefc9aa5ec7c9fcd3",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P2_Staff_Answers.pdf": "3027f40886a5222fb57bbad075e31e6e911bb54362180bdcf1181c2eef0c61cf",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P2_TA_Brief.pdf": "e0d9e800314e231105b8c79e31667f19ba2ccc11ad3e4eca0b7f330cf603c3fb",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P2_Teacher_and_Cover_Plan.docx": "e2f1cca4c90125ebb7d6137643956f7f706b97ddf8dfd4689043bf13ba0dd6c5",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P2_Teacher_and_Cover_Plan.pdf": "35656feec32bde126ec6f6b768fe9d996a11de0786863a294f7e88e9bc6478d3",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P2_Tier_Pack_Standard.pdf": "ab14fcd90912c501ac22645d5c9a4c761f3d2d49432897d521ee747653a70536",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P2_Tier_Pack_Stretch.pdf": "b2a0ba866ec37dbaffe74d9ef05853298d7178e54a40d5594efa722acc450945",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P2_Tier_Pack_Supported.pdf": "5e95b9fecc0387bc154fddbbfcdfd80b46214d9046392d8043708ad3dc868c83",
        "Art/Launch/Autumn_1_2026-27/ART_LAUNCH_A1_W07/ART_LAUNCH_A1_W07_P2_Word_Page.pdf": "8a32acd19b02662628e637fee4513d5ad5b0f64ad49921918e76e77905988c5d",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P1_Editable_Pack.docx": "a31dd739b84568f62d248aaf30483c083b8486f1e282ed7591a3a6ae71a04ecd",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P1_Knowledge_Organiser.pdf": "e3e913be88398a926264325e5478b1f431d60800e28c00698d422014acbf0655",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P1_Pupil_Resources.pdf": "04561500f2f3c993ff207f2096f26589354a9df6a84cdae0ce37ab005c7c7e47",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P1_Slides.pptx": "d2754887c16111339821bb29376038c00aa64ff169e00a9e5d5f4eb61f0b79bc",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P1_Staff_Answers.pdf": "8a4e1066742861cb17c6d68fd22e9e9f0b480c4047e3aa8ab33e716c51de1224",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P1_TA_Brief.pdf": "1501e6aed594cff463a7619c7183f66138e242ebcbe017ca345931500ea943a1",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P1_Teacher_and_Cover_Plan.docx": "a929a357a3e17c353323e10eee3b5a889b1aa307536173c00919bb35ce76593e",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P1_Teacher_and_Cover_Plan.pdf": "5afbd176aa0af7836ec892b153595d79683714dba5f4b0f9dffd975eb4d90525",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P1_Tier_Pack_Aspire.pdf": "d110cfeeeb04e49fdbd886047b772fb1fabf521ffa6da46d502ff73cfa57c0b5",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P1_Tier_Pack_Independent.pdf": "493766e723f905651fbc030e2d4c47f584fcd78107985588ae9592e075363615",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P1_Tier_Pack_Supported.pdf": "c30b8af9692402d1066725ca00272aa90cec942d4857adf7c60d7c3bdd4eae0c",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P1_Word_Page.pdf": "75adc2859144e69450898f15e9519ea62921b34c7c9a654301152e701c154af8",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P2_Editable_Pack.docx": "f8053374952f44eb2ab68fb7385c1eb5d2b88110247c3d62eb807d491ec0ce5f",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P2_Knowledge_Organiser.pdf": "8b490094e5bab9ddf9c567dc7f828f669f952e8cdda4c4899a9c1830cebfd2c8",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P2_Pupil_Resources.pdf": "599f1a39a8214a97e1bcd9ad76b5dc8368416ab46b04d2ec16ddf1eebea0f9e7",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P2_Slides.pptx": "d973359cd6018963485b0f43473fd22cf6b7c853ee420bf7c9038c29801a3c23",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P2_Staff_Answers.pdf": "35c31853f5eab54cb5b30cac012b684b4c147326218380f749c36ed46d3c139a",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P2_TA_Brief.pdf": "e19f098e2d6639de8952c518090da9cdb0f73e29284c6b605500e253081efec9",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P2_Teacher_and_Cover_Plan.docx": "ce9ce2261338127096dfec0199673000abd4a7ffbadb4af472519abbb5d5342f",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P2_Teacher_and_Cover_Plan.pdf": "3d3bc2e8668930d1778e8081a5960ec4c9d8c64007e2d21c9d9fd37e3c2a41e4",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P2_Tier_Pack_Aspire.pdf": "4de67c5cd50ffa044580dcf26f85c93e01761683b5f43e727cd76c01f09ad899",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P2_Tier_Pack_Independent.pdf": "9b66be994da75621a2b400f3f889424aa01c2d649298ad53c7f23e65129ca99d",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P2_Tier_Pack_Supported.pdf": "09058d3c0bbcc8cf5fc86258ca39c498d756bf6b3b9901318c55ddd3da1c27b6",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W03/SCI_BUILD_A1_W03_P2_Word_Page.pdf": "3d5355119a97e5d2a61a90672ad70b914b4f4a55eac4ddd557ccd60652bd146e",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P1_Editable_Pack.docx": "b91119d5fabcb71a141b7357187f5273dc372b2102a82f023e68ef3ab26ebe5b",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P1_Knowledge_Organiser.pdf": "8022dc214559b15b66881e7ae31181664d0b2ded11c45112525c7c93a28c88c1",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P1_Pupil_Resources.pdf": "2fba91b3a144984c788f9eef9b72ae6d195b4416d9b4bdb2d0d38d4d1cc162ac",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P1_Slides.pptx": "f907932c8313ee596f1505399b798b0bed8d22b219b92aca6624ab629fd9eb42",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P1_Staff_Answers.pdf": "996590a062faab51e8efc1c2fd166f038d6f5a2da3dbbdb05bed038a9757205a",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P1_TA_Brief.pdf": "e323f080d9eeb2cc8a7f70aeea3ca3d4f9e0c57e11983dda69a770e6fefbbf5f",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P1_Teacher_and_Cover_Plan.docx": "53bedb423712590ee88a4a80a593c4cdfb2f9be196f776411c9e33d3ebc080e3",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P1_Teacher_and_Cover_Plan.pdf": "8b3267b66f75afa27c219bbf732856e78aeab0fb85310f5609886a4c47dd1a04",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P1_Tier_Pack_Aspire.pdf": "8b69067fbfff75560cf17a2b581109c3725b9397f4e2f4f7be51a0bd591afb02",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P1_Tier_Pack_Independent.pdf": "5686ffc5e0a4aff674d9c056801cc7c9a7c79209833280bfe91e0821cb27f73b",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P1_Tier_Pack_Supported.pdf": "173f857466ffc7a140aeb365bd1febee0696a215ffdfac042d98ab3af6b5a656",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P1_Word_Page.pdf": "47e2d3c3db91e1ddca132314ab7f953f6a6652ea5699b05f0c9bda12c74f989f",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P2_Editable_Pack.docx": "ba9abb247f4a7fd350a15b94d5334b333ef292b4dda0b3b529cc5fd2cace42f8",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P2_Knowledge_Organiser.pdf": "b1f66f12bbc4397b0a5be1b0ddf3501298bf2ad07cb008779eab28190d98b565",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P2_Pupil_Resources.pdf": "584fe5da1382b1dfb2636112c631dbf0afa5ef52bb1798185728102e44a9b9c3",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P2_Slides.pptx": "b78011325b5527ec3ed1a66023746a7ddf57e0918a19f57e91846a2a7e5a902b",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P2_Staff_Answers.pdf": "cb0b77675d07c190db2233ad8799ff5ca5138c3cfb3da2ae754f09c1619f5793",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P2_TA_Brief.pdf": "cc9698e3345265adcbab674d851f7b4b7d1b8a52a3b0d4efee2e7b202abe4660",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P2_Teacher_and_Cover_Plan.docx": "bf99b5a96e53afc9faf9fa003f81fff9ecb06cca893c4d08fca9d4c0f83d23a0",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P2_Teacher_and_Cover_Plan.pdf": "616891e0719779b39e9073de436ddb84db22ab9021ded0dd59680ab6c2eca835",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P2_Tier_Pack_Aspire.pdf": "a806ad0091f5b7439f6158f3347a994ac41cff2702a7e5b086c1fb50e4a1ae1f",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P2_Tier_Pack_Independent.pdf": "724b5897bcaf9d98d0737468b1e9608f7a7ccfdc03773f3f5c2281227dbd0c80",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P2_Tier_Pack_Supported.pdf": "ab2b609e94cb2e894f36b9de99a5ff8b2a547fda105bf5d4dd09861b50138d17",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W04/SCI_BUILD_A1_W04_P2_Word_Page.pdf": "ab6665acb9f83217a82ddf820be955e32d3d136d59c9f6ff388bdff47b719f26",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P1_Editable_Pack.docx": "b0bc8cf60e94372643f485610c409172ae2af10649ba5e884ab187a881204281",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P1_Knowledge_Organiser.pdf": "915ad1af6cd668708b899ee0a9354af1554daf18116fea5eb3b6c0325dac7f4b",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P1_Pupil_Resources.pdf": "f3610b966bc44525eb0b61661213ceab197392372ccc3c803d56c9e2ab529748",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P1_Slides.pptx": "66028bc1830269017df93443ecabc90b4a7ab4483483f93ace8a1903a6742c3d",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P1_Staff_Answers.pdf": "4d7bd12b1d4a335a09046a9919f2af94b0b6257affdde80cb243e0a95b366f13",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P1_TA_Brief.pdf": "35286dcb1a6d161c1f8dbfa3da77a0cfdff175325b443ac63206573ac8829fd6",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P1_Teacher_and_Cover_Plan.docx": "e6b699c045b2707bde99ab4b5f69116980e29dae51ebde985eaad677f04a73b9",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P1_Teacher_and_Cover_Plan.pdf": "a5cb4d7f3b4a2109138646ab1f93a016b2267481f3520a32989057ab6abff15d",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P1_Tier_Pack_Aspire.pdf": "55fd955fab0645a6b299b0ec19b129e0ca96920b4d0a36116252d599b2454321",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P1_Tier_Pack_Independent.pdf": "e76f7bbd6fdae3dfde0d5ddc177c176b09e945bbb1e31363578256ebe23ea987",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P1_Tier_Pack_Supported.pdf": "a153ed6768f1b960cafaf0bf2092911c1dfec663c20c54fcee478f6c45b2e20a",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P1_Word_Page.pdf": "74affcd6c79ff629be3068edb12e6f41994a275efa3693af2c6b3ab9eaa346f8",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P2_Editable_Pack.docx": "f98131be71085de35b1342f2d56a0386eb6233bef141278c0c38e73a8f85f4e5",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P2_Knowledge_Organiser.pdf": "1855aaad218d4cf57b00edac01a55b431acc537c922ec1570767382b4c3bca3b",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P2_Pupil_Resources.pdf": "1b1fd1d1d8d0d0849d2c307007e5cb006981b7e8d3624b287b18bb41fa61b726",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P2_Slides.pptx": "b16f40111c68cecb492094fb05a97ffd5aa45c4e89eba314d8f5eadd4f12efa7",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P2_Staff_Answers.pdf": "c2a74bdad47399d9786d6298dfb348436fe99b13da7a033031f4f27df68511c9",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P2_TA_Brief.pdf": "e7b6f296ec260ba104fc216d5776b52bf0ee662838d76bb3489471b1f13152e4",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P2_Teacher_and_Cover_Plan.docx": "0d419f64f3ef5ad5688bd04bb904d860090755fc8dac110ed191f050b46bfe32",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P2_Teacher_and_Cover_Plan.pdf": "6c50e0f04b0b91ebec7c2d45e850e2eac0f4bcd83ba15c042a9d32e1d17668ba",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P2_Tier_Pack_Aspire.pdf": "646dcad5500e44b700bd897cbf6f7d66a96f6ed750591abb1326d596808caee6",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P2_Tier_Pack_Independent.pdf": "07fb21c3bcdcfb03990465e2884fd872a4db8a2cd2dc2adbe152e748bd5d5e95",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P2_Tier_Pack_Supported.pdf": "b0af6e26aa54c490eedd67508a6b19ec77b17f983dd5b149454c819c739e7681",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W05/SCI_BUILD_A1_W05_P2_Word_Page.pdf": "910c399036112a4587395c3aadc7c38b25660a305dc7eb001cc6f798f814ae25",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P1_Editable_Pack.docx": "4137b66dba3a50719dab8564b6ac5860b44baf220303e240474018040d62dd8f",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P1_Knowledge_Organiser.pdf": "6547737a934f4ddc904eaa34d7ed7ca7b1027deed6f6311e131e419283301ca8",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P1_Pupil_Resources.pdf": "ad9439da86b1fc2ba896b4bc5a377736ed21209a7d8abf712b4f57b5f781b58d",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P1_Slides.pptx": "6e03c043dbbb9a408939238101f79ac8e3f0ae7a7df4a136fb00df98ce61f11e",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P1_Staff_Answers.pdf": "a355733336da518bbfae496e104e5be0c048ffac1105fcee3da348267cd8fc03",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P1_TA_Brief.pdf": "2764267d51a8c15b9cf266e538f8fc25fa770c7763e0128ce8010d0e1ee952cf",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P1_Teacher_and_Cover_Plan.docx": "f0401cc378b93076cd7f56a8e28d7f861a1eaf6d902e004c016fee04e677166c",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P1_Teacher_and_Cover_Plan.pdf": "a3a11167a43833afd502ea0fcd677963776998e83fee11ce720f3692c4fe79ba",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P1_Tier_Pack_Aspire.pdf": "d727b0c25345f5530780e18d133566560791ce94d185343a19a2afb7bc7d3491",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P1_Tier_Pack_Independent.pdf": "cad6c89189a436bb9ed1c1e8385ccba3272855eb5213937dfffeb139ee8cf0a2",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P1_Tier_Pack_Supported.pdf": "ca5f25b775f4f42c3dd9946dbc4e2a3ae9dc419f476c896e772e9cfa461f6fff",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P1_Word_Page.pdf": "84dfc55ce36dccd0eaf9a8512404e459e8c6d3ac9b146c1f1d5d7d65f8513d93",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P2_Editable_Pack.docx": "0d1652f2eb10c4c68cfb1917a0e0b714ccf937e07d3f5c663c528cce539e1d08",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P2_Knowledge_Organiser.pdf": "4da993ee5f9d47e500b661980fa0ec57f47853eb1ab40e44562ebcd4a4cc0cca",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P2_Pupil_Resources.pdf": "f72adbcaf3a043b3cb2752ffba3f07dbc817516eb8933feae50e3f2962a4b338",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P2_Slides.pptx": "8555584bccd39d584854f396fbf739bbef83637e6463dbbb4e5d95c1b135ae13",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P2_Staff_Answers.pdf": "7dd3618dd2735f7643554fce30e5866570d4bb21c5146faf1eb55b5cedf36425",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P2_TA_Brief.pdf": "8a5dabc279291f023dea833964a3f4471fc32def04fc10edc3fc2ff577ac5d17",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P2_Teacher_and_Cover_Plan.docx": "d995e66a6d9f9eb22e8d1c362d22a2dbebdb4687a881536dbbb393771f9c77b8",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P2_Teacher_and_Cover_Plan.pdf": "3e0bb94568d84515c2d9890d0ff3b210e0feabb858a8646d6bfefdb0561db7c1",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P2_Tier_Pack_Aspire.pdf": "1a6ca5a94bb6daf56f13d6e07ef429663ace0ef8f96c3007980447b390fec13a",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P2_Tier_Pack_Independent.pdf": "cce2b5424f7dd1e729d9df26a950cbe03958aa2cdd856a81b774029e4e529a95",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P2_Tier_Pack_Supported.pdf": "e72ffe4ef0a91b83cc6b46ad33eb63280613becb06d1ce6031d263dbb4d08230",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W06/SCI_BUILD_A1_W06_P2_Word_Page.pdf": "4a7e1e0fad6254942427b063a2cb2f46c752b9b566eaa339ff5c76af064afab2",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P1_Editable_Pack.docx": "551d505eb1f259ea5cad3cfe7866111324ca0c1309de95f973843f5c874747ac",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P1_Knowledge_Organiser.pdf": "b3c9f43c16191df633f11b3a6256351ee1fc91c4c1e14d02ce18795812386945",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P1_Pupil_Resources.pdf": "9d6b0b81770ada5c4b77708814df5a403b7e5166519b52adbb4ec961f9192ffb",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P1_Slides.pptx": "96ea8fa9ea952e3c55d9f25c85629852563db289af8e21fa3faa4ff0c4642bf2",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P1_Staff_Answers.pdf": "b966ff93551bd78e57722ef843202e0add8bcd700169c34f575889a44b050805",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P1_TA_Brief.pdf": "4a3e6d3bfe04dca4ed56bf554c0a3e0c712230e1572b849e557a06bfd990d253",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P1_Teacher_and_Cover_Plan.docx": "597ede1e593468acf2dad8c1d5559f68a81743957bfcbe124af6bf808ac5bca0",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P1_Teacher_and_Cover_Plan.pdf": "e1f8802534a03a85edbb183cb5255d6f9fbff2cc71587d6111eb1ca22b83da2c",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P1_Tier_Pack_Aspire.pdf": "73c06fbc23fe88fe38ac0ddd9f9d60a1bbebf81b33eeb7ea338864bf7fbd2054",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P1_Tier_Pack_Independent.pdf": "c1cae888be3d8708a324092e52dd46f794514eef22ba027c3c0ca0960e344db8",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P1_Tier_Pack_Supported.pdf": "9e328b8c5dd0a1b2ba33a2d8e1490794e0b278a70375d22fc2b852c0480abdd0",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P1_Word_Page.pdf": "4fd83007b2d374f27dcb926d3340fc51a17f1286bbe5b2c7f07d1649592c13a0",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P2_Editable_Pack.docx": "12262d2a651bf89cb88c44d140d360e5ea364d16b2db39ae5583d5159adda5fa",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P2_Knowledge_Organiser.pdf": "cfbb1203598512c5a916d60c5f68d339c1c30c0521e7344742b79e36d2a6702e",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P2_Pupil_Resources.pdf": "26950e8ed09bcc0534d370eba7acb7e6632d4bb3e4a8cc8cc7e8b2351c2afd90",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P2_Slides.pptx": "ac8a8d1ebb57ff28e062308623121a2c0026870a40a646e3a43e8b97dea3567f",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P2_Staff_Answers.pdf": "01e815220c0f48e6fa758deaf6a1619db320fecad73b241d79ba5137a04d7675",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P2_TA_Brief.pdf": "845d7406c1ba745d1f8be75bc2de28bc5a815af163f3985414ef495485b75cdc",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P2_Teacher_and_Cover_Plan.docx": "0c4364470de2c93edb076e383cb9ec0df154963c645e21e0cfbc881fcee427c1",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P2_Teacher_and_Cover_Plan.pdf": "6c602279a87698b088e53895b0f36687ea0df20206bdda36def6994cec89601f",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P2_Tier_Pack_Aspire.pdf": "34be604a31b09fd14a03cb6c54ab89bb34099880e344bd896310f443a17be45e",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P2_Tier_Pack_Independent.pdf": "de5e0a5cee8d360feb682db4b50f60968e376e40c2efdbe0a31522938dbf410f",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P2_Tier_Pack_Supported.pdf": "31028bdd229254aa84195e7932760e7d03cc742e30e6be129df50d251e729a80",
        "Science/Build/Autumn_1_2026-27/SCI_BUILD_A1_W07/SCI_BUILD_A1_W07_P2_Word_Page.pdf": "cada2be6accd5d88f4a95dfd6a0edf536698e2d8c84eb246b30193e8ea02a91f",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P1_Editable_Pack.docx": "9a0bd3f1e5515a471a20c3ef7b62d4c35822810354d5687983fec10d75239fb5",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P1_Knowledge_Organiser.pdf": "f353670e96b32fd055fa5d7d390eb5f9aac0cb05e271a063c1bb81212372e754",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P1_Pupil_Resources.pdf": "4032b440eb7fdf65c0adc4fc3c99a83513faf39ec552bf83da5ed3728e3926fb",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P1_Slides.pptx": "378c43e1cca7a423ef156bfa979ed567c57cbedb7bfa3c529e7749b5bed9114f",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P1_Staff_Answers.pdf": "9074a2164606716f02104d4478e4bf17d24aeaf11be389f02ebcb2a4706b0743",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P1_TA_Brief.pdf": "13323b8c1aaff098ecc61b87549cdc1454ef1722fe6ebd30745cc3e4e872e82d",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P1_Teacher_and_Cover_Plan.docx": "b0bb852c2d79652c8cba9c8006aadb93919b5e718e8fbe775492fc786e1910a2",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P1_Teacher_and_Cover_Plan.pdf": "eb701fa10066f8e4504087fa21222f6f9ff6c96bd30e6282d8179b6323b4ba9c",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P1_Tier_Pack_Aspire.pdf": "e46811f37f1319d3559a0d9aa913d2a95147445bb18c269e47e0dc4582a852ba",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P1_Tier_Pack_Independent.pdf": "9b1096cddff7f07dc032a3a0eed5386af25e0718bc3952fd1740901caa4a3e66",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P1_Tier_Pack_Supported.pdf": "9c0685400720127cdfeda334b7f7d22b8212088d4dc309d83a08834545869dae",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P1_Word_Page.pdf": "14ced1b7e7bd11a27f8fda73ca2b3939082281d12aa054ed7eaccf5cae555b4a",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P2_Editable_Pack.docx": "9f21bd46ee2ec1282dfbb34e5cbdfaffa925b711eeec5b231bfd914a70d1b488",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P2_Knowledge_Organiser.pdf": "3027edf815e1203e7d63320e6b13fb5bcdf9438f4b45eabaa6c850997fcd5e23",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P2_Pupil_Resources.pdf": "7d2597cff60565bcb93dc81e9c1d30d1559688e6fa497e74fae6f9cc1944fc20",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P2_Slides.pptx": "a1ec6621b89789e4753f5942647c715bdc4f045fdfbf94371d9e8afb4fed0e96",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P2_Staff_Answers.pdf": "c8383dc5236010f913e4a8f938cf166d452f4c576a46f82350b8755d6d06c755",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P2_TA_Brief.pdf": "f880f3fcc4184d1bef354e50c6e75ae30c165da5b8d2c463042f676f6f4a2586",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P2_Teacher_and_Cover_Plan.docx": "3920a3200764be630d81a0c896b3fb15e7bca1ca6c5bc483c975b9d673e109ab",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P2_Teacher_and_Cover_Plan.pdf": "5674d4745f476d405cb40a7c0311747e81c4e29e6326fda275e3e48f99980745",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P2_Tier_Pack_Aspire.pdf": "ad4328685255c02b237b79e705d73a514f1d4285b0f0a6ad4e1687c99bccc582",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P2_Tier_Pack_Independent.pdf": "607be7ca3c344bfb3d4dae37eac1f4aae1dd35e2d86a86b98440fe83f6dca51f",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P2_Tier_Pack_Supported.pdf": "a8c8127e85806b21e0c6be8c8bbb6806ebf27b245dca2daabe71f437d80f6a90",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W03/GROW_SCI_A1_W03_P2_Word_Page.pdf": "7dbf642b80f440c9f18088e337573220c16db9385412257963be88fae3f4c9b0",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P1_Editable_Pack.docx": "9406504b55495adea21d975267828f786f7a83d7514dfbc30f5fd19fa106c790",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P1_Knowledge_Organiser.pdf": "15152916f8f7ff59aa0feb6733430f90aad80fcbf5897a26db59eeab7c925a15",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P1_Pupil_Resources.pdf": "0cdfbffef2a69745477d260a7b764d2c7dec638a2cf357deac91beed7365be02",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P1_Slides.pptx": "aa1877f331306ce62d6ace44ea0b31245dcacb2e417f330b3e300dedb67e48dc",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P1_Staff_Answers.pdf": "4a411af5b687d22d81246fef3e20efb21ce6f84d2b2c445dfe7a26ee531befc8",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P1_TA_Brief.pdf": "005e081e882fef5f86c5331edbaf518e01e74c3abd348b876327fe9a306bfab5",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P1_Teacher_and_Cover_Plan.docx": "d030b62dee75b6ed9b3f1144d4cc573a0e9efb0db9ebe69c357ad6e22f8a435d",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P1_Teacher_and_Cover_Plan.pdf": "4e60d95ddbab929e3921b2f885e11496f9b4a8b58737e567a85347685420878b",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P1_Tier_Pack_Aspire.pdf": "25f7393824f3ef02539fe514dfbc196386291a0f7155be401b3ced1dcf0ea096",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P1_Tier_Pack_Independent.pdf": "9d682826637324b3712156faf32aefca197c7256f8e6891509e5614a6e94fec3",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P1_Tier_Pack_Supported.pdf": "cb7dd52f6a93ff1dd064f818e741d6a079b7ab5937b4b890517f7b8940629860",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P1_Word_Page.pdf": "4845682d6adb9bafd4486658a9f610df051559c666c51f3589b897ba17c2ba3f",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P2_Editable_Pack.docx": "4f03fe16f39dabfc73c7fecd7f78563c7e82608cc2c6cd077029eed27a00e121",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P2_Knowledge_Organiser.pdf": "1abc318e42d5e81a1370dc90a73393d4526197d623f4bf91f9fe5f05f08c6d24",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P2_Pupil_Resources.pdf": "d45f20a5a78a666629eb06b841918e80845ba813221fcd412b83dd8f04092914",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P2_Slides.pptx": "7b62ab9ad5cf55045a50d8602c87ab0c3c6565cd72f668f6f6213528008d47fa",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P2_Staff_Answers.pdf": "5ba5fa864b9fef09992048d81ee9d6bbc28ccbb93008e021ae7f22be68550bd7",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P2_TA_Brief.pdf": "a24b7819f8516803c969202e690855bc0ba57af746493541c89746552db4b89b",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P2_Teacher_and_Cover_Plan.docx": "54099806a60702325e57cb4116f069640ea049c551963eb71f9124c3f4cf9ed4",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P2_Teacher_and_Cover_Plan.pdf": "b626d36d2e3702f207c26021177cdc6ca241d53f09f7d9347de012e09e5607b8",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P2_Tier_Pack_Aspire.pdf": "6404796aff3c76ccec9b52f81aab34f82286676030d13d2c151449b16090d2f1",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P2_Tier_Pack_Independent.pdf": "57a2724a5e3214197ac1fe94841e2c5e56d01f8798554bf6f7b080b8995fc920",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P2_Tier_Pack_Supported.pdf": "d9f346381cdce4ac28aeb1691f6c75cf88e265029d5c7ce3b1e61d1b4b857358",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W04/GROW_SCI_A1_W04_P2_Word_Page.pdf": "0d9561804b7322676dacf851b6422e232a4c2a8a8b2df077e033097ec5c29c6e",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P1_Editable_Pack.docx": "774cbcf992b84d0ceed0ace6266e12a998c6d2c21f0bdf623a6277096168fea1",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P1_Knowledge_Organiser.pdf": "5d9d28cc16413be90d5c8918e280bdf7d9f2218822e836b95c138b73fd09659e",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P1_Pupil_Resources.pdf": "46b18b04f982d1b57b41ac4d874dfea0c53fc555466605d976cfd6d8d32b3d53",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P1_Slides.pptx": "60a03321ed80586bda693921cc0f3d9546b3a7ba9ba63ff472b912ba24fa4532",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P1_Staff_Answers.pdf": "9ef0028f04a1e2b07c47e7e204bffce937433a76579eaca91b9dbd0a7c389e0d",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P1_TA_Brief.pdf": "075c9abab96d04b700b528fedec9ea4e70d5cbb3a84d91c62338e4b704e0dc85",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P1_Teacher_and_Cover_Plan.docx": "81414ccdc221b7b57a6e9a5c88cde8b6b700d61720b38ebd6c56b6b774b14e74",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P1_Teacher_and_Cover_Plan.pdf": "c90e75cc51ea2a69221369da3242bd720240e6f05b41ea3f64603d2aebce99d0",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P1_Tier_Pack_Aspire.pdf": "d3c5ea8e86338615100e19c627096700fff14c5bec39edd9b242b75d48bd97df",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P1_Tier_Pack_Independent.pdf": "3925dc37f0bb63f3510b07f07bfeeb706795b194befeb77cf1f25bc5594ba41c",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P1_Tier_Pack_Supported.pdf": "1a230fadf19be75c1719bea6b48a80a22ce64cc2a895de82b169a6b920ff4679",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P1_Word_Page.pdf": "902b16daf10fd83cb9ed40fcd592bf33e45fae3f0c9877dcdfd404fc17502edb",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P2_Editable_Pack.docx": "58a6b1f58617fb65062a245b69e81682f01a890cb10977cbe3eac264587159a5",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P2_Knowledge_Organiser.pdf": "71cd8a2a9ee1c02c7ac718c94d93f8688ee57c567ad42cb47d3b9eff3af81423",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P2_Pupil_Resources.pdf": "0df4bc4a748c7285898828617cbb52919541d6ceceac66c52c873a99d7f6a011",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P2_Slides.pptx": "b4807bc87dbcee312085ec345e4c886765608bdbf981088241795ec4483dd6d8",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P2_Staff_Answers.pdf": "b2a75c04ef9f56419e613a2ae81ba9236e0ecf3678f1a8c8cca39a880e52ca68",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P2_TA_Brief.pdf": "a34f2646b28dd2a796b259594d135bff279a96e68d78da79d30cd9d17a2344d7",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P2_Teacher_and_Cover_Plan.docx": "a2926c74096ecfb9a23da1ca01de75c4c4d3dbc056290ec47a4131c867c6afcc",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P2_Teacher_and_Cover_Plan.pdf": "db204c022b14120e424262f5e2286def34f3c6934136e95f4c341cf9b5719493",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P2_Tier_Pack_Aspire.pdf": "fe66cdc3a8c99f697c8a09ed7a22105f92a218debbdfc27693d4e79ae160328d",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P2_Tier_Pack_Independent.pdf": "7449e82d8c036a8a6a6a5a5bd6f61084bf14666f069db683e2e58d0a1391e448",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P2_Tier_Pack_Supported.pdf": "153f5f5bc99659f6da53004e26ca4d82b5fafe5a58f1a1013f6ff36281aa75d8",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W05/GROW_SCI_A1_W05_P2_Word_Page.pdf": "d28c713713feb82bf592fd354d8a48d8439e0339c071cc197cd2f77595eecfe5",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P1_Editable_Pack.docx": "58e4b02ef6aee3db0e5d050c58d7280d58e0c1251089ee5c409a479094158e27",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P1_Knowledge_Organiser.pdf": "1f0110e97db5c1ef0ec16b8bae2ac143cc73cc2519d1fa3a58db3309fd1618aa",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P1_Pupil_Resources.pdf": "4c9dac3d1fd9e381aa9f5a4aafb88b65579d3da581dcebe16c830af2d6ac57dd",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P1_Slides.pptx": "cc8d6329f659fcfc88721e1110ec0702c8b698ad8856549b746fa2d733616e27",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P1_Staff_Answers.pdf": "9eb17c0f33ad035835fa3904c6644cb2c8958fdf1bf3bb1b59406472644ed4e5",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P1_TA_Brief.pdf": "e9e1054862e02de85e8eddddca130a816f638d78af256742475ccc00e342e8ad",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P1_Teacher_and_Cover_Plan.docx": "c032f9a96e031083c5c3942d1eca4332795c06763a6582dc197fefad7119eeab",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P1_Teacher_and_Cover_Plan.pdf": "ddca9359f796d1723e62c3d5f6fe66ed99a31a10cf3b6a7af28e3d953f953853",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P1_Tier_Pack_Aspire.pdf": "7fbd60b07b8d443658dd3f53cabcbf1915e3ab1fea6f95145f61511aceec7940",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P1_Tier_Pack_Independent.pdf": "5ee55e1c11b2f30d196f6e77af22a5b74b8e5e19daf11d365d66fbb6454ce38b",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P1_Tier_Pack_Supported.pdf": "fb30b09b380bcad278012e621d507b854d0002badb6c6c57a3dd3fc6ee185e0c",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P1_Word_Page.pdf": "f24f2459172ca0f8addd3e0cc20ef167431b2e0e080443e4038fd414af9946ef",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P2_Editable_Pack.docx": "3fcb78d3e2bb7998d0efd54944ff3f5eefa40aeecb831efaf52515eb7ec74e7a",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P2_Knowledge_Organiser.pdf": "583e3a9d6bae8189a161dbcbee4ecf6017e6f39651b97b21bb78cdc44afd7d64",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P2_Pupil_Resources.pdf": "30243c0592837928d0ec3eccc760e56dc16ade37882200167b64c42cf1fd6a7d",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P2_Slides.pptx": "2308a8f0f6b00444ecdbe410ca9ab10bfabc33d5a0520236107b99f4261aa9b3",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P2_Staff_Answers.pdf": "726d07c85d5228d243caa272af462e809d37142c020651e717e81409f2eae463",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P2_TA_Brief.pdf": "ac1897d62495bf0d7a0b9794e1874ab795012e314c9c287ec20aedf35e542808",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P2_Teacher_and_Cover_Plan.docx": "04281c7849591efb1afe078ce974d3e634e073a5142ab350b70fb4fdde871468",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P2_Teacher_and_Cover_Plan.pdf": "8f7a2edf8e14406679beb148109478d5ffc4b5f2595cc5c9d4888e7e95d8788e",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P2_Tier_Pack_Aspire.pdf": "458255e0b331f0c9d07c39d84b33d64c66da7ac2e9cf5bac1f35f27799f07ace",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P2_Tier_Pack_Independent.pdf": "eb53464a88e137a49607694d1ea5f4f5dd2edc4b19e7f8b40ebb73f19beffcb7",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P2_Tier_Pack_Supported.pdf": "fb5549c67cc4e241fad3d01dfef01e7ff8c264f52e0a47536f58b6a91b64726e",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W06/GROW_SCI_A1_W06_P2_Word_Page.pdf": "4e52c2c6fed707abef7b60270d0b560fe3e75863c3aa595fdbe0cbcfaaa4a81a",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P1_Editable_Pack.docx": "b4b49ae013b8a87286a295389fffe94cbc663981b3f1b96b9cc154cafb3d2319",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P1_Knowledge_Organiser.pdf": "3dd745d37237de8a282e8e04de59bce7398a15447abe4fb8b10937e9c56a9ae0",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P1_Pupil_Resources.pdf": "67886209d5e685538b0bbb095f4574350106aa616e94edb38fb04b10161b8cbd",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P1_Slides.pptx": "b7c59a252d65473afaec6fb9c022b0836d8371bbdb56567176e26e341d7ab837",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P1_Staff_Answers.pdf": "65dbafe023c6c7122537919386986d5bd2fa14c6e43b7ebb1e4ba676ee691d60",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P1_TA_Brief.pdf": "acf58af13711efe0332d51da948482bd8d2e827cfb888a6d09fb636b69c15acf",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P1_Teacher_and_Cover_Plan.docx": "587986e36daccfa6a40ed23a92995164838f9e8d177007f0f8cfd6baf7c6686a",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P1_Teacher_and_Cover_Plan.pdf": "be2d00e7d15706b0e16d23f5fb91b9cf997b278b0648b4f9eb0a4fb7bd7c878a",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P1_Tier_Pack_Aspire.pdf": "b7773421f84df56ebbb51b2ed958629710215a304d07e3375100012eded8ded6",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P1_Tier_Pack_Independent.pdf": "57d85977bbaf52a7d75178cd2068a1782b348b731c74b463825bff0430128120",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P1_Tier_Pack_Supported.pdf": "f574bf60d627d0a532e87d2ee6f46b3663bda2653d8afc53f080fc8d8e7ead2f",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P1_Word_Page.pdf": "bd18e058f43cd63bc5dde7bfe0e3fb8bf6e2cfa0b530edc81381d0e05e5f4246",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P2_Editable_Pack.docx": "8cd1479d1ea8e71b37760dac7e672a4488618a5a1bc8ca5e8d5f5be726458c7c",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P2_Knowledge_Organiser.pdf": "3ad2a488404b7abeba8fa57c306585d111feac2cfadf93762d0e6679b8a7e2d1",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P2_Pupil_Resources.pdf": "0189b64f7adf98b22d69cdffcad9f01d158f98a279f2317e3f073e62c3f9f346",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P2_Slides.pptx": "ae0e3a6221f8581d39355d2bc67b6f565464b3292d65d9c795f3f875f0c5297a",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P2_Staff_Answers.pdf": "72b9b7740f1b246680695c655aa7850f24d78a901b262a4ae433f41ee3173baf",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P2_TA_Brief.pdf": "ec2a2e6e948d9d4d2bd2060db42890bff669a7c35d9e30bc078cff2619866b79",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P2_Teacher_and_Cover_Plan.docx": "8ebe720987d503d4c7f2b18a0870651fa7e49c833dea12fe760fa2eac0e20e0a",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P2_Teacher_and_Cover_Plan.pdf": "d2a77bc3603dab49d5395c738bd4ca1fbb00cb35a2c9ddcc338e32e3199d40d3",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P2_Tier_Pack_Aspire.pdf": "15d5f1c994ca4e0c5ca260829aad5ff67f06e2bd9c1882e312fa0ca24bdbfabb",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P2_Tier_Pack_Independent.pdf": "ef66f6580844e58024763f2b02746471607c5f406cbb32a234d9d510a224763e",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P2_Tier_Pack_Supported.pdf": "3b053c728f75b71b13d1c7a3424da4f0c2e32092a53a8f4ed8da4975fa14d6c2",
        "Science/Grow/Autumn_1_2026-27/GROW_SCI_A1_W07/GROW_SCI_A1_W07_P2_Word_Page.pdf": "b5fd0e62944c2f582ae1c9bbcb998529a17515eab07ca4a1ed85515a4b4f3224",
        "Art/Build/CREATIVE_ARTS_A2_W03/Public/ART_BUILD_A2_W03_P1.html": "7bedd1f07a8d3023994a8f68010449b900fab817a13a7855d4b9d1c253264048",
        "Art/Build/CREATIVE_ARTS_A2_W03/Public/ART_BUILD_A2_W03_P2.html": "a231a516c7284a5e7837d6f9cc0e5c8d0ac7b4094e590b0d66b7ff01afb7cbc7",
        "Art/Build/CREATIVE_ARTS_A2_W04/Public/ART_BUILD_A2_W04_P1.html": "0af7d0d647373dcc8b5c395768f1e5c3813022f1e712dba4b72473216d0fd159",
        "Art/Build/CREATIVE_ARTS_A2_W04/Public/ART_BUILD_A2_W04_P2.html": "33373aa912db5a919459ba750691701631730f62729cb134e8db6cbeb07f3789",
        "Art/Grow/CREATIVE_ARTS_A2_W03/Public/ART_GROW_A2_W03_P1.html": "5a916d8569126b9561e2428333dd66dcd09872329c2fa0051eeec5243faee829",
        "Art/Grow/CREATIVE_ARTS_A2_W03/Public/ART_GROW_A2_W03_P2.html": "31a8a61c069d792d588be5d3439d8fc6fd7353496f38175590ff7659f14cda19",
        "Art/Grow/CREATIVE_ARTS_A2_W04/Public/ART_GROW_A2_W04_P1.html": "e8d813e10d0abed5b0b8175a9960345e0bdf312444934af21f923441fd272c5d",
        "Art/Grow/CREATIVE_ARTS_A2_W04/Public/ART_GROW_A2_W04_P2.html": "d48875579836661833a3eabdb787d529b678eabb534a876eee98e8a19aa5eec6",
        "Careers/Build/Autumn_2_2026-27/CAREERS_BUILD_A2_W08/CAREERS_BUILD_A2_W08.html": "33f737202795340ef5f1740d2fbc1fab38cba0c59d15bb8a24e11cc5cb672e54",
        "Careers/Launch/Autumn_2_2026-27/CAREERS_LAUNCH_A2_W08/CAREERS_LAUNCH_A2_W08.html": "c0674881a561271756a7c4f3b9181023b8661f11c900098831cde20e4717db49",
        "Community_Projects/Autumn_2_2026-27/COMMUNITY_A2_W01/COMMUNITY_A2_W01.html": "3deb010e7fa8c0e956fa88ab235565188db61cf52cd4c79896e1ff5ca8d42544",
        "Community_Projects/Autumn_2_2026-27/COMMUNITY_A2_W03/COMMUNITY_A2_W03.html": "ad0d8d46448911a4c92059392f2080e2e735342d412195f507dd6c03b069e3b8",
        "Community_Projects/Autumn_2_2026-27/COMMUNITY_A2_W04/COMMUNITY_A2_W04.html": "f4ee3efe0b05de93ecfd613668c3a609eb53372278ffe8af5729ac39ddee4d62",
        "Community_Projects/Autumn_2_2026-27/COMMUNITY_A2_W05/COMMUNITY_A2_W05.html": "4fa7fb4240743ae93f57744537da30b94cdd5d42616846cd7adc51955b55bb67",
        "Community_Projects/Autumn_2_2026-27/COMMUNITY_A2_W06/COMMUNITY_A2_W06.html": "d7d6665217e1ddaecbebccd2457ae3c5bc1591559af5a4cb6321fb5e01373452",
        "Community_Projects/Autumn_2_2026-27/COMMUNITY_A2_W07/COMMUNITY_A2_W07.html": "d3cef117b2d65e195df9b0de2590c69a49b2856e10f35459b0f7ff65cd3ded68",
        "Community_Projects/Autumn_2_2026-27/COMMUNITY_A2_W08/COMMUNITY_A2_W08.html": "5b2b26f3e3297f4189bd8f5af0fb84e41b8448a279f8df3e834feb4006040ab2",
        "DT/Launch/Autumn_2_2026-27/DT_LAUNCH_A2_W01/DT_LAUNCH_A2_W01.html": "69538f6eb0a21faaf398e97a2a3af0f2d0a9e0b886e1c401754f6d019a9c95ad",
        "DT/Launch/Autumn_2_2026-27/DT_LAUNCH_A2_W08/DT_LAUNCH_A2_W08.html": "d61e8296e3efb04f018cd7482cba06ec264dea69db4065f81d704ed7651c8788",
        "LAUNCH_ASDAN/W7-W12_2026-27/lessons/ICT/LAUNCH_ICT_A2_W08/Public/ICT_LAUNCH_A2_W08.html": "4e6bee4eafae948abdbe9fb596b6ae9959891e2f09d8819bd2f6d7b45a424463",
        "PSHE/Grow/Autumn_2_2026-27/PSHE_GROW_A2_W01/PSHE_GROW_A2_W01.html": "8f1ec28999bc4885e9317484476ebf7688224636ffdd389e060adea8142b0170",
        "PSHE/Grow/Autumn_2_2026-27/PSHE_GROW_A2_W08/PSHE_GROW_A2_W08.html": "ee9c3bf0c1e67907aadc5c1e8641a3471d7f77234fa7aff5eddbdccd68ebadf9",
        "RSE/Launch/Autumn_2_2026-27/RSE_LAUNCH_A2_W01/RSE_LAUNCH_A2_W01.html": "3081788926d70138a566ef9238fc5c4fdcd88a345643d364d1d433017083a4b7",
        "RSE/Launch/Autumn_2_2026-27/RSE_LAUNCH_A2_W08/RSE_LAUNCH_A2_W08.html": "ee131b6e78561e62269a4f9b3df5f0aca685c7351c076ed66f9fdecf1e64fb54",
        "RSHE/Build/Autumn_2_2026-27/RSHE_BUILD_A2_W01/RSHE_BUILD_A2_W01.html": "e67a48194e4827bc42ae165e93055cb6dbc246b61636796426c252e2d518c0de",
        "RSHE/Build/Autumn_2_2026-27/RSHE_BUILD_A2_W08/RSHE_BUILD_A2_W08.html": "4cac88cd63903600a46d4e4e553c72231f2fe402d9525e3a50b020b28dffc0a6",
        "Vocational/Build/Autumn_2_2026-27/VOC_BUILD_A2_W01/VOC_BUILD_A2_W01.html": "5de670aea7f91604f71274ee85bcb0457d908f7897353b14f2ffed87b1e89a64",
        "Vocational/Build/Autumn_2_2026-27/VOC_BUILD_A2_W03/VOC_BUILD_A2_W03.html": "135c62f65341ea818d9e12e5c9f935b5d1a8f031942cf821ba4b05785ef14f86",
        "Vocational/Build/Autumn_2_2026-27/VOC_BUILD_A2_W04/VOC_BUILD_A2_W04.html": "36ec249208e9d952f7356963ce0f254aca4570448dc8e8a80bdf39425adbc993",
        "Vocational/Build/Autumn_2_2026-27/VOC_BUILD_A2_W05/VOC_BUILD_A2_W05.html": "2cb20e91f73205d34e83f62618ecb069a12400fc279e6666576fd216d89bf757",
        "Vocational/Build/Autumn_2_2026-27/VOC_BUILD_A2_W06/VOC_BUILD_A2_W06.html": "8c5a392781b2778fd9c64339d0e8a1208fcf2cae465c877141171491014bafb2",
        "Vocational/Build/Autumn_2_2026-27/VOC_BUILD_A2_W07/VOC_BUILD_A2_W07.html": "82fad73514517303ae37ced6cea90648d2c709cfeb29113d3d2172591961040f",
        "Vocational/Build/Autumn_2_2026-27/VOC_BUILD_A2_W08/VOC_BUILD_A2_W08.html": "d0bfe5c4d82cdbf7fb49b4b0eea033c4cbe65e1d7defd5bd29f4a58a93274c67",
        "Vocational/Launch/Autumn_2_2026-27/VOC_LAUNCH_A2_W07/VOC_LAUNCH_A2_W07.html": "d4c2573cfb24eff1a92b172514f475b1aea64268de4b2d7f4f632c4a9fbad524",
        "Vocational/Launch/Autumn_2_2026-27/VOC_LAUNCH_A2_W08_L1/VOC_LAUNCH_A2_W08_L1.html": "f36d7fb4e5819639767cd627a1779709d3d7f00152c668d39c6462e44788065a",
        "Vocational/Launch/Autumn_2_2026-27/VOC_LAUNCH_A2_W08_L2/VOC_LAUNCH_A2_W08_L2.html": "a75a50b647563adb992d86017284ba4999be3d2f3452661f57a6a27b182e0dc8",
        "kits/class_tools/Catch_up_Tracker.html": "9810f412b1f81fce0465e0cbdec4c3c0e34475642be2f0f76f44411ceed71f28",
        "kits/class_tools/Class_names.html": "9dd07df35df72997823126c4b99499fddea98dbe78b4b34b223c1ea5dde31000",
        "kits/class_tools/My_tools.html": "9dadc768e06329ca54908a09d0f6ef18be7de4c0548229bd9c9e8e888652511a",
        "kits/class_tools/Practical_log.html": "56cb7d7a6f847cec2ab69700137501589dd32710650ea2c6e9b5cfbab17911fd",
        "kits/class_tools/Requests.html": "c6f34336c15a5692ff6186bb2d0c26090b0c3593f8556496837ec1a437cb4f82",
        "Games/WorldCup_ThreeLions_Final.html": "fcf4f6f1624b990fba86aec53692ffc2423c0c22a0a57cfb14fb3d111ba429c0",
        "Games/WorldCup_v3_MatchDirector.html": "8a35d72c00b255d309b034533c33356a8bcf9f1c51d6cbe17672f080edb3c528",
        "Games/WorldCup_v5_Showdown.html": "f4ab26c52e9c831b3fad8c4927c3ea7821e5dcd5a6e8438dcb020f25797d6159",
        "Games/voxelcraft.html": "2146cd3b20da15d007978c99d9a04138d003fec6ad06f893016e17ae27658941",
        "Games/Match_Director.html": "cf114ae9313c06c4b555fcfff4a49e2fc919dafbbde5a1c34f9474889ca28f74",
        "Games/Cup_Showdown.html": "07796c9e918a214234cee74fdddc15449097f881a7816b144f874b730570bed0",
        "Games/Block_Builder.html": "6241089e5c0f2071faa3729323edad42183144943468a8c8e0a67bad563fc409",
        "5_6 Local Choice/index.html": "5fd8687fe8f818e28405120b1e633bfaedfa6c2a3652a1238dbaa42def833c00",
        "tools/verify_games_offline_runtime.mjs": "0a728df9507068bb93ca4e0fccf7ac481b317e8f6ea67ee4216b3ca501349cb6",
        "tools/verify_playable.mjs": "92be84f1cae169a53a688c6322e02202d226b2f1c6c6661cf24c8549fed95f9e"
    }
}
# END REVIEWED CATALOGUE PINS

# These semantic pins are deliberately outside the movable file/manifest block.
# Neither the catalogue pin tool nor the generic manifest pin tool can bless
# an edited, deleted or reordered original resource, or an extra lesson row.
# Ruling qp-2 (A-wide, os-4, 11 Oct 2026): the original rows are 734 plus the 21 reviewed rows the A19/A24
# catalogue refresh interleaves (additive: with them taken out, the 734 are in their reviewed order, unedited).
CATALOGUE_ORIGINAL_ROWS = 755
CATALOGUE_ORIGINAL_ROWS_SHA256 = "431354c16974f70317db728a2f5de209ec4fc54762fc1ec0da57242ceb2efea7"
# The appended rows are the 49 reviewed hub rows followed, since UX2 D3
# (2026-09-08), by the companion-pack entries DERIVED from
# data/companion-packs.json by tools/ux2/companion_catalogue.py. The count and
# digest below are re-cut by tools/catalogue/pin_catalogue_contract.py from
# rows it has verified against that derivation; an edit to any appended row,
# a removed pack row or an extra lesson row still reds here.
CATALOGUE_SHELF_ROWS = 633
# UX2 A1: keys that may be appended to an original row without moving its
# digest (see catalogue_errors). Nothing else is additive. No original row
# carried either key before the ruling (measured 2026-09-08: 0 of 734), so the
# second set is empty and the allowance cannot launder a pre-existing value.
CATALOGUE_ADDITIVE_TAG_KEYS = frozenset({"halfTerm", "unit"})
CATALOGUE_ORIGINAL_KEYS_BEFORE_TAGS = frozenset()
CATALOGUE_SHELF_ROWS_SHA256 = "2313e761d5a1e10efe631e5c0dba7a20a47ad986bd8a69e12a5a0cfbdaa535da"

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
    # A2-LIST (2026-11-08): a catalogue-side manifest states term and week for a
    # protected pack folder whose own manifest may not change. It is data read by
    # tools/catalogue/build_catalogue.py, not a lesson payload.
    "tools/catalogue/manifest_humanities_build_w9-w14_terms.json",
    "tools/catalogue/manifest_aaa_small_subjects_terms.json"
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
# ORDER HUM-T batch 6 (STANDING RULE L33, 2026-09-20): the publisher pin moves to Site main 8e95534e; the caller
# file therefore changed and this is its digest re-cut from those bytes -- derived with
# sha256sum, never transcribed.
# HUM-T batch 6b (STANDING RULE L33, 2026-09-20): the publisher pin moves to Site main f29214ed; the caller
# file therefore changed and this is its digest re-cut from those bytes -- derived with
# sha256sum, never transcribed.
# ORDER SCI-COMPLETE PASS F: the publisher pin moves to Site main 9600846c, the re-cut
# PASS F admission window (Site #426), which admits the rebuilt Science hub and the
# registrations it links. The caller file therefore changed, and this is its digest re-cut
# from those bytes -- computed, never typed.
# Summer 1 responsive re-delivery (STANDING RULE L33, the ruled pending-then-land fold,
# STOP-RESP-2 step 2, 2026-09-22): the publisher pin moves to Site main aeb47509, the squash
# merge of Site #430, which admits this release's 27 published paths as [main-today, pending]
# transition pairs. The caller file therefore changed and this is its digest re-cut from those
# bytes -- derived with sha256 over the edited file, never transcribed.
#
# NOTE ON ORDER, found by the pre-push battery rather than reasoned: this constant lives in the
# gate copy that must stay byte-identical across Lessons and Apps (the G1 control), so an L33
# carrier bump DRAGS THE GATE COPY -- and therefore the Apps companion -- along with it. The new
# digest cannot be computed until the Site SHA exists, which is only after the step-1 window
# merges, so the Apps companion for a carrier-bearing fold cannot be a single PR opened up front:
# it needs a second companion opened after step 1. Recorded so the next fold plans for it.
# RE-CUT 2026-09-22 (STOP-RESP-4, route A): the carrier is re-bumped to Site main 0f931086,
# the squash merge of Site #431, so education-pages.yml changed again and so does its digest.
# This is the second cut in one fold and it is the cost the standing rule exists to avoid:
# bump the carrier ONCE, LAST, at a SHA that already admits every mover.
# Re-cut 2026-09-22 (the Science hub's generation order, ruling on the S02 STOP): the carrier
# moves to Site main bb283643, the squash merge of Site #433, bumped once and last. Digest
# derived with sha256 over the edited file, never transcribed.
# Re-cut 2026-09-22 (the pure carrier closing the hub fold): the carrier moves to Site main
# dd9831f3, the squash merge of Site #434 (the EQUAL window). Digest derived with sha256 over the
# edited file, never transcribed.
# Re-cut 2026-09-23 (PASS C Autumn 2 batch 1, rulings S1 and S3): the carrier moves to Site main
# c85c12c3, the squash merge of Site #436 (the window's second cut, after the adversarial review;
# #435 admitted the first), bumped once and last. Digest derived with sha256 over the edited file,
# never transcribed.
# Re-cut 2026-09-23 (the Science hub follow-on, route C): the carrier moves to Site main 0fa71565,
# the squash merge of Site #437 (the EQUAL window that also admits the hub's 3 pairs), bumped once
# and last. Digest derived with sha256 over the edited file, never transcribed.
# Re-cut 2026-09-23 (the pure carrier closing PASS C Autumn 2 batch 1's fold): the carrier moves to
# Site main 5251edc8, the squash merge of Site #438 (the EQUAL window). Digest derived with sha256
# over the edited file, never transcribed.
# Re-cut 2026-09-23 (HUB1 v2, Autumn 2 hub badges): the carrier moves to Site main 7d310e1e,
# the squash merge of Site #440 (the window admitting HUB1's 6 pairs), bumped once and last.
# Digest derived with sha256 over the edited file, never transcribed.
# Re-cut 2026-09-23 (the pure carrier closing HUB1 v2's fold): the carrier moves to Site main
# 9fd80be8, the squash merge of Site #442 (the EQUAL window). Digest derived with sha256 over the
# edited file, never transcribed.
# Re-cut 2026-09-25 (Q12, the Science hub stylesheet): the carrier moves to Site main 3e5e489d,
# the squash merge of Site #444 (the window admitting Q12's 2 pairs), bumped once and last.
# Digest derived with sha256 over the edited file, never transcribed.
# Re-cut 2026-09-25 (the pure carrier closing Q12's fold): the carrier moves to Site main
# be9441d7, the squash merge of Site #445 (the EQUAL window). Digest derived with sha256 over the
# edited file, never transcribed.
# Re-cut 2026-09-25 (LAND-A2 Science): the carrier moves to Site main 214749c0, the squash merge of
# Site #448 (window W1: the 21 lessons' rows and the fence's transition pair), bumped once and last.
# Digest derived with sha256 over the edited file, never transcribed.
# Re-cut 2026-09-25 (LAND-A2 Science, the pure carrier): the carrier moves to Site main 079fba99, the squash
# merge of Site #449 (window W2: the refresh, the fence collapsed to one digest, the EQUAL pins). Digest derived
# with sha256 over the edited file, never transcribed.
# Re-cut 2026-09-26 (DLG-1, LAND-A2 R8): the carrier moves to Site main de2ed592, the squash merge of
# Site #450 (window W1: the 194 transition pairs), bumped once and last. Digest derived with sha256 over the
# edited file, never transcribed.
# Re-cut 2026-09-26 (DLG-1, the pure carrier): the carrier moves to Site main 117d4cff, the squash merge of
# Site #451 (window W2: the five EQUAL pins onto Lessons #679 / Apps #189). Digest derived with sha256 over the
# edited file, never transcribed.
# Re-cut 2026-10-04 (Science Week 8, ruling eo): the carrier moves to Site main a71ee9d2, the squash merge of Site #453
# (window W1: the 47 ARRIVING rows and 11 transition pairs), bumped once and last. Digest derived with sha256
# over the edited file, never transcribed.
# Re-cut 2026-10-04 (Science Week 8, the pure carrier): the carrier moves to Site main 73712445, the squash merge of
# Site #454 (window W2: the refresh, the fence collapse and the five EQUAL pins onto Lessons #683 / Apps #191).
# Digest derived with sha256 over the edited file, never transcribed.
# Re-cut 2026-10-05 (RE Week 8, rulings fm-6, fp and fq): the carrier moves to Site main f1d0680c, the squash merge of Site #455
# (window W1: the 30 ARRIVING rows and 9 transition pairs), bumped once and last. Digest derived with sha256
# over the edited file, never transcribed.
# Re-cut 2026-10-05 (RE Week 8, the pure carrier): the carrier moves to Site main ebbc826c, the squash merge of
# Site #456 (window W2: the five EQUAL pins onto Lessons #685 / Apps #193). Digest derived with sha256 over the
# edited file, never transcribed.
# Re-cut 2026-10-06 (the names fix, rulings fv-1 and fv-2): the carrier moves to Site main 2dcb869e, the squash merge of Site #457
# (window W1: the 10 transition pairs), bumped once and last. Digest derived with sha256
# over the edited file, never transcribed.
# Re-cut 2026-10-08 (the names fix, the pure carrier): the carrier moves to Site main d250bfea, the squash merge of
# Site #459 (window W2: the five EQUAL pins onto Lessons #688 / Apps #195). Digest derived with sha256 over the
# edited file, never transcribed.
# Re-cut 2026-10-09 (names-fix PR 9, the pure carrier): the carrier moves to Site main 47276941, the squash merge of
# Site #462 (window W2: the five EQUAL pins onto Lessons #690 / Apps #198). Digest derived with sha256 over the
# edited file, never transcribed.
# Re-cut 2026-10-09 (the subject-hub noindex fix (jw-1), ruling ni): the carrier moves to Site main df664434, the squash merge of Site #465
# (window W1: the 0 ARRIVING rows and 1 transition pairs), bumped once and last. Digest derived with sha256
# over the edited file, never transcribed.
# Re-cut 2026-10-11 (os-4 patch set A25, ruling os-4): the carrier moves to Site main c1be14aa, the squash merge of Site #468
# (window W1: the 0 ARRIVING rows and 83 transition pairs), bumped once and last. Digest derived with sha256
# over the edited file, never transcribed.
# Re-cut 2026-10-12 (os-4 patch set A25, ruling os-4): the carrier moves to Site main 27f47031, the squash merge of Site #469
# (window W1: the 0 ARRIVING rows and 86 transition pairs), bumped once and last. Digest derived with sha256
# over the edited file, never transcribed.
# Re-cut 2026-10-13 (io-3 Autumn 2 Week 1, ruling rd): the carrier moves to Site main 9402e0a8, the squash merge of Site #471
# (window W1: the 110 ARRIVING rows and 1 transition pairs), bumped once and last. Digest derived with sha256
# over the edited file, never transcribed.
# Re-cut 2026-10-13 (io-3 Autumn 2 Week 1, ruling rf-4): the carrier moves to Site main 35251ca7, the squash merge of Site #474
# (the io-3 collapse window: no new rows), bumped once and last. Digest derived with sha256 over the edited file, never transcribed.
# Re-cut 2026-10-15 (Humanities Spring 1 window W1, ruling sd): the carrier moves to Site main a82d4d5b, the squash merge of Site #475
# (window W1: 26 transition pairs, 0 ARRIVING rows), bumped once. Digest derived with sha256
# over the edited file, never transcribed.
# Re-cut 2026-10-17 (RE Spring 1, rulings sr and ss): the carrier moves to Site main e076e4bd, the squash merge of Site #476
# (window W1: the 272 ARRIVING rows and 4 transition pairs), bumped once and last. Digest derived with sha256
# over the edited file, never transcribed.
# Re-cut 2026-10-18 (Week 8 Science, ruling sy): the carrier moves to Site main 6049e6f0, the squash merge of Site #477
# (window W1: the 51 ARRIVING rows and 50 transition pairs), bumped once and last. Digest derived with sha256
# over the edited file, never transcribed.
# Re-cut 2026-10-21 (the tm drawer and outcome changes, ruling tm): the carrier moves to Site main cfc92e84, the squash merge of Site #478
# (window W1: 16 moved rows, 0 arriving), bumped once and last. Digest derived with sha256
# over the edited file, never transcribed.
# Re-cut 2026-10-22 (TQ Week 8 pack reachability, ruling tq-1): the carrier moves to Site main 6ad7a729, the squash merge of Site #480
# (window W1: 14 moved rows, 0 arriving; the usage fence for tq's flight), bumped once and last. Digest derived with sha256
# over the edited file, never transcribed.
# Re-cut 2026-10-23 (uf, the two Assembly pages and decks, rulings uf, uh add.1, uf add.3): the carrier moves to Site main c6687cf6, the squash merge of Site #484
# (window W1: 4 ARRIVING rows, 9 pairs; the usage fence for uf's flight), bumped once and last. Digest derived with sha256
# over the edited file, never transcribed.
# Re-cut 2026-11-01 (Merge Letters A1-A6, LD28 standing step): the carrier moves to Site main e25aa76a, the squash merge of Site #533.
# Re-cut 2026-11-03 (Ruling M-AD): the carrier moves to Site main ca4b63ce, the squash merge of the admission PR #588 (Lessons f154ac7a).
# Re-cut 2026-11-04 (Ruling M-AE): the carrier moves to Site main 6aab2483, the squash merge of the admission PR #592 (Lessons fac84ac8).
# Re-cut 2026-11-04 (Ruling M-AE add.1): the carrier moves to Site main ede20ceb, the squash merge of the admission PR #593 (Lessons d406243e).
# Re-cut 2026-11-06 (owner pin edit 15b93935 on main, owner approved the re-cut): the carrier moves to Site main 6c62e842, the squash merge of Site #600.
# Re-cut 2026-11-06 (owner pin edit b4e6522c on main, owner approved the re-cut): the carrier moves to Site main fc91ab2a, the squash merge of Site #604.
# Re-cut 2026-11-06 (owner pin edit de25c187 on main, owner approved the merge): the carrier moves to Site main fb287c0c, the merge of Site #605 (the Humanities and RE Autumn 2 admission).
# Re-cut 2026-11-06 (owner pin edit d7c3a5de on main, owner approved the merge): the carrier moves to Site main e90a1c20, the merge of Site #606 (the site pages, sitemap and kitchen working-notes admission).
# Re-cut 2026-11-07 (owner pin edit on main, owner approved the merge): the carrier moves to Site main fba8a87f, the merge of Site #610 (the reviewed-title Humanities and RE pack pages admission).
# Re-cut 2026-11-07 (owner pin edit on main): the carrier moves to Site main 027fe921, the merge of Site #612 (the 41 pack manifests Lessons #816 publishes).
# Re-cut 2026-11-07 (owner pin edit on the pathway-labels branch): the carrier moves to Site main 3a89a748, the merge of Site #613 (the pathway-labels phase 1 admission rows).
# Re-cut 2026-11-07 (owner pin edit on the subject-page pathway-labels branch): the carrier moves to Site main 8ee4d3e6, the merge of Site #614 (admission rows for the four relabelled catalogue files).
# Re-cut 2026-11-07 (owner pin edit on the Autumn 2 lesson-list branch): the carrier moves to Site main 3cd0d4f2, the merge of Site #615 (admission of the files Lessons #821 changes). Re-cut from the caller bytes.
# Re-cut 2026-11-08 (owner pin edit on the Autumn 1 AAA lesson branch): the carrier moves to Site main 1b215d2d, the merge of Site #616 (admission of the files Lessons #822 adds and changes). Re-cut from the caller bytes.
# Re-cut 2026-11-08 (owner pin edit cc40d39c on the Science Autumn 1 list-fix branch): the carrier moves to Site main 0ac6944b, the merge of Site #617 (admission of the list fix: subject.html, terms-and-styles.json, the 15 unlisted SUMMIT pages).
# Re-cut 2026-11-08 (owner pin edit b91dcad6 on the Week 2 QR-page branch): the carrier moves to Site main 5d40754c, the merge of Site #619 (admission of the Week 2 QR-page edits); the caller digest is re-cut from those bytes.
# Re-cut 2026-11-08 (owner pin edit on this branch): the carrier moves to Site main 85b7bb5c, the merge of Site #621 (registry baseline for the Autumn 2 landing and the scheme-of-work label admission, after Site #620 admitted the Autumn 2 pages); the caller digest is re-cut from the owner's committed bytes (both pin lines moved, one trailing blank line).
# Pre-cut 2026-11-08 (owner pin edit on this branch): the carrier moves to Site 4288540e, the head of Site #622 (the publisher build job timeout raised from 15 to 30 minutes, the only change on top of Site main 85b7bb5c); the Autumn 2 publication run was cancelled twice by the 15-minute limit while its admission proof was passing. Pre-cut for both pin lines moved and nothing else changed; re-cut from the owner's committed bytes if they differ.
    "lessons": "7a7167cfb533961cfe2ad4e677378393abcda9fc1de7b6916b521289046a91ad",
# Advanced 2026-09-16 (served-defect amendment D-2): the Apps repository moved its own
# publisher pin to the Site carrier that carries EDU-D3, so its caller file changed. This is
# that file's digest on Apps main, re-cut from its bytes.
# Re-cut 2026-10-08 (the names fix, the pure carrier; fv-4): the Apps repository moves its own publisher pin to Site main d250bfea,
# the squash merge of Site #459, so its caller file changed. Digest derived with sha256 over the edited file, never transcribed.
# Re-cut 2026-10-22 (ruling ty, ty-2, option A): the Apps repository moves its own publisher pin d250bfea -> cfc92e84,
# the squash merge of Site #478 and the builder Lessons already publishes with, so its caller file changed. Digest
# derived with sha256 over the edited file, never transcribed.
# Re-cut 2026-11-01 (Merge Letters A1-A6, LD28 standing step): the Apps repository moves its own publisher pin cfc92e84 -> e25aa76a,
# the squash merge of Site #533. Digest derived with sha256 over the edited file, never transcribed.
    "apps": "7823f26e59b1e4d8059aff5eafa7cf9691a0de6f9c49dc664c85c960da71b02c"
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
    # Re-cut 2026-10-22 (ruling ty, ty-2, option A): PUBLISHED re-derived from the Site cfc92e84 registry, the one
    # builder both estates now publish with (lessons "" d74addfa, subject.html b2a6f3cb, apps "" 53d82c52); digest
    # taken from the edited file, never typed.
    "tools/sw2/check_tokens_inert.cjs": "2cbb482b66a72cbba628fba80b8fbdd431553356c95a66d36614fa35189d6434",
    ".github/workflows/verify-lundyloop-professional-os.yml": "db2f0404944884869d84349a68b80858f81af8dbfb7eb64ddec71151f7928256",
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
    # RULING um, um add.1 (24 Oct 2026, reading (ii)): the 42 format collections a unit zip fully contains,
    # removed from the publication. Their deletions are admitted by exact path; nothing else, no folder, no pattern.
    "BUILD_ASDAN/FoodWise/Teaching_Packs/BUILD/downloads/BUILD_FoodWise_Autumn1_W1-W6_DOCX_Collection.zip",
    "BUILD_ASDAN/FoodWise/Teaching_Packs/BUILD/downloads/BUILD_FoodWise_Autumn1_W1-W6_PDF_Collection.zip",
    "BUILD_ASDAN/FoodWise/Teaching_Packs/BUILD/downloads/BUILD_FoodWise_Autumn1_W1-W6_PPTX_Collection.zip",
    "Careers/Teaching_Packs/BUILD/downloads/BUILD_Careers_Autumn1_W1-W7_DOCX_Collection.zip",
    "Careers/Teaching_Packs/BUILD/downloads/BUILD_Careers_Autumn1_W1-W7_PDF_Collection.zip",
    "Careers/Teaching_Packs/BUILD/downloads/BUILD_Careers_Autumn1_W1-W7_PPTX_Collection.zip",
    "Careers/Teaching_Packs/GROW/downloads/GROW_Careers_Autumn1_W1-W7_DOCX_Collection.zip",
    "Careers/Teaching_Packs/GROW/downloads/GROW_Careers_Autumn1_W1-W7_PDF_Collection.zip",
    "Careers/Teaching_Packs/GROW/downloads/GROW_Careers_Autumn1_W1-W7_PPTX_Collection.zip",
    "DT_Textiles/Teaching_Packs/BUILD/downloads/BUILD_Textiles_Autumn1_W5-W7_DOCX_Collection.zip",
    "DT_Textiles/Teaching_Packs/BUILD/downloads/BUILD_Textiles_Autumn1_W5-W7_PDF_Collection.zip",
    "DT_Textiles/Teaching_Packs/BUILD/downloads/BUILD_Textiles_Autumn1_W5-W7_PPTX_Collection.zip",
    "DT_Textiles/Teaching_Packs/GROW/downloads/GROW_Textiles_Autumn1_W5-W7_DOCX_Collection.zip",
    "DT_Textiles/Teaching_Packs/GROW/downloads/GROW_Textiles_Autumn1_W5-W7_PDF_Collection.zip",
    "DT_Textiles/Teaching_Packs/GROW/downloads/GROW_Textiles_Autumn1_W5-W7_PPTX_Collection.zip",
    "GROW_FoodWise/Teaching_Packs/GROW/downloads/GROW_FoodWise_Autumn1_W1-W4_DOCX_Collection.zip",
    "GROW_FoodWise/Teaching_Packs/GROW/downloads/GROW_FoodWise_Autumn1_W1-W4_PDF_Collection.zip",
    "GROW_FoodWise/Teaching_Packs/GROW/downloads/GROW_FoodWise_Autumn1_W1-W4_PPTX_Collection.zip",
    "Humanities/Teaching_Packs/BUILD/downloads/BUILD_Humanities_Autumn1_W3-W7_DOCX_Collection.zip",
    "Humanities/Teaching_Packs/BUILD/downloads/BUILD_Humanities_Autumn1_W3-W7_PDF_Collection.zip",
    "Humanities/Teaching_Packs/BUILD/downloads/BUILD_Humanities_Autumn1_W3-W7_PPTX_Collection.zip",
    "Humanities/Teaching_Packs/GROW/downloads/GROW_Humanities_Autumn1_W3-W7_DOCX_Collection.zip",
    "Humanities/Teaching_Packs/GROW/downloads/GROW_Humanities_Autumn1_W3-W7_PDF_Collection.zip",
    "Humanities/Teaching_Packs/GROW/downloads/GROW_Humanities_Autumn1_W3-W7_PPTX_Collection.zip",
    "Humanities/Teaching_Packs/LAUNCH/downloads/LAUNCH_Humanities_Autumn1_W3-W7_DOCX_Collection.zip",
    "Humanities/Teaching_Packs/LAUNCH/downloads/LAUNCH_Humanities_Autumn1_W3-W7_PDF_Collection.zip",
    "Humanities/Teaching_Packs/LAUNCH/downloads/LAUNCH_Humanities_Autumn1_W3-W7_PPTX_Collection.zip",
    "ICT/Teaching_Packs/GROW/downloads/GROW_ICT_Autumn1_W1-W7_DOCX_Collection.zip",
    "ICT/Teaching_Packs/GROW/downloads/GROW_ICT_Autumn1_W1-W7_PDF_Collection.zip",
    "ICT/Teaching_Packs/GROW/downloads/GROW_ICT_Autumn1_W1-W7_PPTX_Collection.zip",
    "ICT/Teaching_Packs/GROW_Computing/downloads/GROW_Computing_W1-W8_DOCX_Collection.zip",
    "ICT/Teaching_Packs/GROW_Computing/downloads/GROW_Computing_W1-W8_PDF_Collection.zip",
    "ICT/Teaching_Packs/GROW_Computing/downloads/GROW_Computing_W1-W8_PPTX_Collection.zip",
    "PSHE/Teaching_Packs/GROW/downloads/GROW_PSHE_All_About_Me_W1-W7_DOCX_Collection.zip",
    "PSHE/Teaching_Packs/GROW/downloads/GROW_PSHE_All_About_Me_W1-W7_PDF_Collection.zip",
    "PSHE/Teaching_Packs/GROW/downloads/GROW_PSHE_All_About_Me_W1-W7_PPTX_Collection.zip",
    "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3-W7_DOCX_Collection.zip",
    "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3-W7_PDF_Collection.zip",
    "Science/Teaching_Packs/BUILD/downloads/BUILD_Science_Autumn1_W3-W7_PPTX_Collection.zip",
    "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3-W7_DOCX_Collection.zip",
    "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3-W7_PDF_Collection.zip",
    "Science/Teaching_Packs/LAUNCH/downloads/LAUNCH_Science_Autumn1_W3-W7_PPTX_Collection.zip",
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
    # tp add.2: the UX2 census reporter and its controls follow ux2-gates.yml's proof
    # outputs; a proof added there must be added to the census in the same change.
    "tools/ux2/drift_census.py",
    "tools/ux2/test_drift_census.py",
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
    "Humanities/Teaching_Packs/SHA256SUMS.txt",
    "Science/Teaching_Packs/BUILD/SHA256SUMS.txt",
    "Science/Teaching_Packs/GROW/SHA256SUMS.txt",
    "Science/Teaching_Packs/LAUNCH/SHA256SUMS.txt"
}

# rm-2 (13 Oct 2026; a red-first plan, local build): the ri-5 Group 1 scheme-source edits. These are
# workbooks and their text dumps, not served files. Each path is admitted through the boundary only while its
# bytes equal the sum below: no folder, no pattern, nothing else widened.
SCHEME_SOURCE_EXACT_SHA256 = {
    "_passpq/DECISIONS_YEAR2.md": "045146ae58357f4f92996be5d2f4a3c6e5293cffd19e1bd4d37e9064ea213461",   # rp-2 (a): Group 2 record line, not served
    "_sownb/VB_STATE.json": "fd21c2f5a6affaf7b5f495af3b2e8831897493e361ed7de50ae57e5bb85eb01d",   # rp-2 (a): Group 2 record line, not served
    "_sownb/vb/WRONG_BEFORE_RIGHT.md": "37adc9cf88a7f9832e8844e1f8681e9bfb76fb8866d6f53959a05add42b521bb",   # rp-2 (a): Group 2 record line, not served
    "Build/_Archive_VersionA_LivingIndependently/BUILD_SOW_2026-27_vA_with_LivingIndependently.xlsx": "b5cee8c3413e0487c630331057deb1b16c03805084e113e96094a3d2cadc397f",
    "_authoring/science_2026-27/_toolchain/scheme_references/BUILD_SOW.xlsx": "b5abd199abfa8c3de4608533fcef9e917a61b148419a102dfff6708302139cd0",
    "_authoring/science_2026-27/_toolchain/scheme_references/GROW_SOW.xlsx": "41ff0a4a4211da89466f5634f58a5074b6f4be6c7036118aab1e0e9d3145d7b3",
    "_authoring/science_2026-27/_toolchain/scheme_references/LAUNCH_SOW.xlsx": "b8063b7d6b3989f71375b5f2c3a62b9ebcd3be1bb1933706a009473c7b19ee02",
    "_passla/inputs/LAUNCH KS4 - 2026-27.xlsx": "92ceefa450b770af738a1a65797047555c796e890c19cb54286662968fde90a9",
    "_passsb/inputs/Build SOW 2026-2027.xlsx": "b5abd199abfa8c3de4608533fcef9e917a61b148419a102dfff6708302139cd0",
    "_passsg/inputs/GROW SOW 2026-27.xlsx": "41ff0a4a4211da89466f5634f58a5074b6f4be6c7036118aab1e0e9d3145d7b3",
    "_passsl/inputs/LAUNCH KS4 - 2026-27.xlsx": "b8063b7d6b3989f71375b5f2c3a62b9ebcd3be1bb1933706a009473c7b19ee02",
    "_sca1/inputs/BUILD_SOW.txt": "6491c014baba83b6091686a4e40156b94443341265432786db41c7c67a52df42",
    "_sca1/inputs/GROW_SOW.txt": "e034ba648284b16ac3388b6e0ea441e34072ac30ab7286780b243f41ef7f39c6",
    "_sca1/inputs/LAUNCH_KS4.xlsx": "92ceefa450b770af738a1a65797047555c796e890c19cb54286662968fde90a9",
    "_sca1/inputs/LAUNCH_SOW.txt": "5881aaaedc0fcb238ccac9549b79176fcac4a5cbdd7c610cd1e77b0ee3c85d1d"
}


# RULING wa-2 (c) (26 Oct 2026): M1, the subject-folder rename. The files M1 edits in place (outside the moved folders)
# whose new bytes are the rename map applied to their previous bytes (with M1's digest re-pins), each admitted by its exact
# reviewed digest -- the same rule as SCHEME_SOURCE_EXACT_SHA256, no folder, no pattern. Generated from the new digests
# of those files; the proof that each reproduces is in the readback. Any other byte in any of them reds as before.
M1_RENAME_EXACT_SHA256 = {
    ".github/workflows/arts-award-legacy-reader.yml": "7a913da583eb3af9ade0a5f0e434611f911da34c45f093a0169794ad1c9a6a7a",
    ".github/workflows/arts-award-reader.yml": "73fba96fa95fe427f490594011231376fe4df8b9cdb842721930cb4dffdc114e",
    ".github/workflows/glv3-production-byte-check.yml": "b0de87ca9bc68553b14a05c2f8c0ece512acc75ee1066d77aee6be3ea8f25f0e",
    "BUILD_Estate_v3/index.html": "302893d70d13f5ed91521614e9bc5f156f3a1fa32a93c32fce0d3cb465de3d1f",
    "GROW_Estate_v3/index.html": "e39e4acf6cf1b85b03cb444dc30380a88174ae9f302132b38da305e6decb148f",
    "LAUNCH_Estate_v3/index.html": "a1beccc6e45ac8484d2be9d56815fdec7cb3db99b9ed6599f52351df38b36255",
    "Launch/Slideshows/LAUNCH_ART_W8_Complete_The_Review.html": "cac083b1fa61722545dd14c4597aa3dcf236b5ed05eb8416d4276b71501406e8",
    "LundyLoop/tools/print_pack_audit.py": "a2297e2db4a0c91b4dcb5f54bc9254f28e7b5962442e806fe55cc6de30db26b0",
    "Teaching_Packs/LANDING_MANIFEST.json": "60db3016994171e92ee00e8ed76eaf39d4724f9b5322fbdab2ad64ba6f357078",
    "Teaching_Packs/index.html": "358d350e6bfd5bfd64d1e08745c3af0aafb73f2b4e1d09360b40085d45d5d461",
    "_glv3/COUNT_RECONCILIATION.json": "db359403e422d260bde5ad4800f31238ef72ef692de226dde937fc5c04b668ea",
    "_glv3/GATES_STATIC.json": "3dbfcc8a6b3ee1584e40151b7092b6562f5e52d5129ba43eb57195167e3b502f",
    "_glv3/INPUT_INTEGRITY.json": "9356996b209ea80db820a892afc2babf4499fa52f4dd2794439661306abe3020",
    "_glv3/PROTECTED_TREES.json": "88b091c791c5de41df74cb1176fff94a8508b83428ecfa00d7a1e9ffcdc05fef",
    "_glv3/run_manifest.json": "f56b52d992d6fd0ade237e4758e930512e741f7041dabc0cf33475f7e0d47fed",
    "_sownb/feb/tools/g18_content_floor.py": "7ba0fa91a6462a3603387bff57023ddb813e75f5fda0cb995c04b702776e3718",
    "_sownb/feb/tools/g18_measurement.py": "37d79bb3d0b3fab60abaca58b1da099b867cfe08f1f70b22a50a469d2c5758f5",
    "_sownb/vb/tools/attribution_control.py": "6583d41561555b64a1d01e92cf7b5c71ba52a50a1442eb60c664b8e2393708ab",
    "_sownb/vb/tools/cell_coverage.py": "255d6df5e9524aeb44ad186f2fb3ba46d4ed037d04a9a1e698d7f5a83409e17a",
    "_sownb/vb/tools/g18_v2_family_floor.py": "c368d6600e44a782c6499273664f7802282660554d3d72fa5eed701556937ea0",
    "_sownb/vb/tools/g29_plan_binding.py": "6cce40c3b0812e145209459b7d2228ebfc8131f80c966552ddbd7ee1ed966264",
    "build-anim/inject.py": "5aff881a7a3b874eede704128e44d20f2bb70105e21b74bf4cd042aedd2cbfa9",
    "checksums/SC3R2_BUILD_A1_W08/SHA256SUMS": "035dbbcec311aa22818ff362f7a72a74e58a9f4e2338ce98cb5d56a083fb0015",
    "checksums/SC3R2_GROW_A1_W08/SHA256SUMS": "771bcbae1b106f7621ab2d2e04540b208845fc587906afa939592b45fc8d1de9",
    "checksums/SC3R2_LAUNCH_A1_W08/SHA256SUMS": "6af50dd7e73bf6c53fbfd274384227f4491c7109bc6be6a956703123ffe922ab",
    "grow-anim/inject.py": "9e4713ce537b37692593e5c9a185e8a5f17f24e45782a768b1e39bbe6e256b0c",
    "grow-anim/wire_lessons.py": "f047f8e88fad8b22219a8bd005a1aa19c3d43bb835abf0dcd76d605669845720",
    "quality/LESSON_AUDIT_SCHEMA.json": "e8488124a719d0f8aa535fdfbbfbc1cb1b7ff2ace86d83090bb9494da2816406",
    "quality/LUNDY_HUMANITIES_SPECIMEN_MANIFEST.json": "9e4576581922d9a1673657175eb13a4089de73b369a194ec6466a35548c04b3a",
    "quality/QUALIFICATION_CLAIMS_REGISTRY.json": "94e863e707b5b0c1b434a6dd4d19f9a37738bc6ae6770ae6eda96e46c566e1f0",
    "review/estate-exec/validate_estate_exec.py": "7024b5dce23969ef3b809fefbedd8bfa2eb75ad3ec3614a9ab5939d59d4a4599",
    "tools/artsaward/BRONZE_ACTIVITY_TARGETS.json": "7b9b2d2ecb2a686db77d190ed18fe4cd6a7772ea2f6fe84c8a6cb4a831c665c3",
    "tools/artsaward/BRONZE_DONORS.json": "ed5db7ffec5ddafa8d1d8575a96392ea6e6824c494c724155f1dd60b8b86f21b",
    "tools/artsaward/BRONZE_TARGETS.json": "f6582503d52952a49a98d8d0dcef8f795f467428be24ebd728ee07e37b7bfcbd",
    "tools/artsaward/EXPLORE_ACTIVITY_TARGETS.json": "3f217eea5e576d71270a9892f4d077449d870e1ccd8c3f0c83b877b8253da6b6",
    "tools/artsaward/EXPLORE_DONORS.json": "b92450611a4af8a2e15156a12ae199fdaee2469123c5cbf6ae625e0dc5396234",
    "tools/artsaward/EXPLORE_TARGETS.json": "51445d99ee7c52a10c4d2f1788f216a07a8fb5755107a3217c325e2256ce1d8f",
    "tools/artsaward/SILVER_ACTIVITY_TARGETS.json": "7ad6ca91eef5092ba375056c5413391e5b8f08dcbc490567733175a4cb53280e",
    "tools/artsaward/SILVER_DONORS.json": "e155f4e35d2d63c9fce2d05bebaa711fc87d12de93ed3ad5495ea1fdd24622a1",
    "tools/artsaward/SILVER_TARGETS.json": "d42052c0da3faa5c415c6a6a5996b380881a145b5d9e4c36efce606e5a4ab097",
    "tools/artsaward/legacy_slot_adapter_selftest.cjs": "7b00b6819b6093d1528f1a4c8e6d2b9f1f10ccceec079c5b073018091285df1a",
    "tools/artsaward/legacy_slot_browser.cjs": "b75f066f982bc8887a47f1a8caadb8fd00d76390e66c68edb20ff103134d7d2c",
    "tools/artsaward/venue_classify.py": "c4e7a6ae50635e0832674640df3f008e33369d4f747dca67f1ba1c70a367ff1c",
    "tools/build_resources/W8A_ACCEPTANCE.json": "9475262a4e6389a5145f4c7f2af7c70e1d561eacd7160d56941726a2f70a7dde",
    "tools/build_resources/admit_sx3_release.py": "2d7c7309e81b1f7bddc82c03d5720116e2eac23a49626716d11b660f98e01515",
    "tools/build_resources/admit_w8a_chassis.py": "69ec305cb48ff64f232be7ee67dbd9bef8be789271d22a8b0e78bd97805d7c2c",
    "tools/build_resources/author_w8a_chassis.py": "88a3cefc8e7a6930d65afbe22d818008c9838347681622e7fe16c381e410acf4",
    "tools/build_staff_pack.py": "2e7d2063e10018004aad5c4439584377ef8316d5c48ba52d8280cf9c6a0d1cae",
    "tools/catalogue/PUBLICATION_ARCHIVE.json": "54f917e15f56f3988fed321e5696bc61ecaa234123599e539abf3863f909a729",
    "tools/catalogue/prepare_dy4_bind.py": "1dc4bccf7d53f042beaa6d42af638e25a6a17e121c309660ae1b1afcc19e273d",
    "tools/catalogue/test_build_catalogue_merge.py": "a059308af1159a27fcd66c88b3fd164122d918f82b3eb63ae22402ba9a5f7285",
    "tools/chassis_census.py": "6f32664de6cc0ed489b1298c552cd98c2b9adc5ec22467c48655af1cd55c932f",
    "tools/cx2_r10_estate_sweep.py": "2f61e24d93ff0d73383f0baa3c1b61e6bb30ecb9162fb97027901d8b480d9569",
    "tools/donors/ART_DONOR_v1/GROW_chassis.html": "2f24f54692fb7ab70799fc611eeaffb4b690f36031c40aba72e3f990493c8244",
    "tools/donors/ART_DONOR_v1/README.md": "5d0a13d1998c28f488cf36ddc54a33749c171ed235a5cf84806bbd3e7e5af5e6",
    "tools/downloads/definitions/bronze-arts-award-main.json": "0012f6ec4689b7d1157777ebe4c85084cfd8d867cbc0d4e20c2cd052373e66b6",
    "tools/downloads/definitions/build-science-aut1-main.json": "43ff4716dca29a734f54e77c8d1f889d250ae954a57ae8ffeaa116e9df081c88",
    "tools/downloads/definitions/build-science-aut2-main.json": "1114bdea6165202760e83e859dfa6ea57f636a717bb7c3daf8d9d34bfd4d4120",
    "tools/downloads/definitions/build-science-spr1-main.json": "d7a8866f53df4be8a26f47f1c869f6dcd70a0ab858606c0ce53c5e929b4c39d4",
    "tools/downloads/definitions/explore-arts-award-main.json": "0e38be04758decb564219c75d8a790228a89b59337c9c9efa52f387d9329d4ee",
    "tools/downloads/definitions/grow-science-aut1-main.json": "8f78d60e707a29a798bbca2cbd08cdfe59454cf5f3921e2346bee64d6353647b",
    "tools/downloads/definitions/grow-science-aut2-main.json": "f3bdc04b72895c032a24db6ea22caea65995c6c8b77bbfa84c85d441bac28552",
    "tools/downloads/definitions/grow-science-spr1-main.json": "2ee78a7886548383cd1d6836ad96883b3a7ae36f4752d4c3dab50db92a93efa0",
    "tools/downloads/definitions/launch-science-aut2-main.json": "4631fd2952e7e2165e15730de55db4ebddee6612230c6cffe0c205dd299a0398",
    "tools/downloads/definitions/launch-science-spr1-main.json": "1373c1fe6b5e847e27d38a11f913066ce6b192e96eaf1aab2d4ee6fc34153db8",
    "tools/downloads/definitions/silver-arts-award-main.json": "46d88cb7b4676dfec884a5016cf7e34485ecfeb51006faabc1d88a48082ac4e6",
    "tools/downloads/test_science_offline_pack.py": "0880a4cd3c298489e65a5d357806ddcfa7f36127d3c69b8103744019cd9564d7",
    "tools/downloads/verify_definitions.py": "c8e9c2e4b8b4d8cc2fa0605f645d95d72d6223d5ba7c69d1d52db015cb4a2443",
    "tools/easter/BATCH3_DONORS.json": "9cd370ae1d160870c008721b2342fe7638aaa19307863bd2ac6ac0f7bfe769ce",
    "tools/easter/BATCH3_TARGETS.json": "5fed7ba3d275f158d34322d348dc6fc9ff0e58357003e62382037ae31a12c107",
    "tools/easter/BATCH4_DONORS.json": "e7ecd9d778d662d474708a4b27ee002c9137424563ec06f90ffb32280c33d164",
    "tools/easter/BATCH4_TARGETS.json": "28f973153b4d4583d6cd03281b3997c5a89effa5b95c6cf66d8aeff39fe88cac",
    "tools/easter/CLASSROOM_LIGHTER_TARGETS.json": "abc8df5f4eae80145c26f44276be9a223a7b1a007d189f90975bc2cfbe735a10",
    "tools/easter/CLASSROOM_TARGETS.json": "891ae955f3b06229427a6e1041c463a027032b93f7881865c85747ec4f82c526",
    "tools/easter/EASTER_TARGETS.json": "3f67b567c4d8cd103bc183ac78afcea998a385e2a4e56e5903e2755b4408b89a",
    "tools/easter/GREEN_REFERENCE_DECKS.json": "9bca2e3db355e469df24498bd0543a93826fa180e29b3b8b3d0b440bcef90062",
    "tools/easter/award_browser_fixture.py": "a0980d43cf3e3db7be0478d8c78d1cd26343c0c8964328c4635e1e2cbf2dd29b",
    "tools/easter/build_batch_targets.py": "265958d5d8e9379cdafbee8b7120de614a5bd04d8186a717cc1605c9b82cf1bd",
    "tools/easter/build_from_specs.py": "462542d256dbfe617565b7bb416fc10e805e853398f8306a9d301e4088a8df82",
    "tools/easter/chrome_flip_list.py": "121ff7ec92c357532968b0b5359ca4ed4fdacc204c4f7686d6ebc56bea30e605",
    "tools/easter/dedupe_sweep.py": "2eedc923cb58920e444775d63fa05055359ad5d9013a989593192d71176d86a9",
    "tools/easter/manifest_sequence.py": "172503d7d5eb10a24eeca2ad7fda539b9921ffb11203e8b8b4e5a440ab1de877",
    "tools/easter/pick_art_donor.py": "089d04a5882f8161541e89eb6bc531971a1aa1c658c11acf9014e254216cf098",
    "tools/fieldops/README.md": "403825ff409337675d95ccde06fb5c022aeab1cee7fadb98ee21606605387460",
    "tools/fieldops/build.mjs": "216f493a1307b497ca75a0b1c7734bc3f18de572c2348676f83e3b08f533fe7c",
    "tools/fieldops/controls.mjs": "705af245197977fb47338155ad190942884fc6aceb9a914a77e0d7fe8f0ecab3",
    "tools/fieldops/split_transport.mjs": "3d818e13bd672bc294fa354bfe04ce0f502f90b2d9b8ce669b0bc126d25cbefe",
    "tools/fieldops/staging/00_BUILD_FieldOps_Teacher_Studio.html": "407439c9c76fcd87064b2e9ed1c31bd6d0d295dd89f4740062d263512720d3aa",
    "tools/fixtures/pr124/workflows/glv3-production-byte-check.yml": "b0de87ca9bc68553b14a05c2f8c0ece512acc75ee1066d77aee6be3ea8f25f0e",
    "tools/fixtures/pr124/workflows/glv3-verify.yml": "c9e59c8ae624c8a997b3bd9b3782afdcfbf73806969a6f6ebab66cd8d67bc983",
    "tools/grow_resources/arrival_checks.py": "bd8362be676e8fc7ce1dcc8e23af7c89ff67fe3ee3e2935565fe692ec166daf9",
    "tools/grow_resources/author_w3_feedback.py": "c94409a281b5c03c1c97ae03e5350ac747bd6e56d37859facd76af556aa4ace3",
    "tools/grow_resources/author_w3_slides.py": "4fceea67e275f6f1672fb968f4a30e57d76c47f68a445767527e4deae6540c25",
    "tools/grow_resources/author_w3a_arrival.py": "2738c0404563e2326a7502dee27be2aa5fae2d1c775dc49ec5d877ba0f98ab5a",
    "tools/grow_resources/author_w3a_organiser_exit.py": "cc8060cafea0014d7d1a55ad810c61ebd1da81d40cbb268ca9d1992fe5f7d854",
    "tools/grow_resources/browser_checks.cjs": "cc210c3e3c42c1a3c0427e01e34bc5bb1fb9635e6d2f147160f5ea375e5dc715",
    "tools/grow_resources/build_resources.py": "859e7401228a8d98b89f2ff0b0caee465b7ad4234f6650fa03fbaa5705d2d3e2",
    "tools/grow_resources/check_resources.py": "c471de9f2d24e4421c13102210d8c4a9a7e0d533e475ef532f442d3634731b1f",
    "tools/grow_resources/feedback_checks.py": "aefee5e30756327e49e5eefcba1a91090d4301ef36ebbc5b30f2d5a5a74bd5cf",
    "tools/grow_resources/focus_checks.cjs": "75d08c268252d1782daa5708ac63cec74e769754adb7d1a40de5c3a18727f7ce",
    "tools/grow_resources/friction_acceptance.py": "f9d71e35e83a16e0292f0f3ff6f769a5128b8952eff3d9e3075c02fb932ba6fb",
    "tools/grow_resources/organiser_exit_checks.py": "bfed534d64285302de29f3f4e841a15de7c34b48c0b8d124e0d9a05a86d1cd0a",
    "tools/grow_resources/refresh_w3_pack_records.py": "1f010687251fd64d4070992e7157e77de6c648b412999a42c9c639566a2d97df",
    "tools/hum/DLG1_PAIRS.json": "dd4c854af722e969c4261e748942a20f8f4db8ade44649538df0b0e16f8a1618",
    "tools/hum/arrival_week_exceptions.json": "ad0e1a8fea71ecccfb3707cefa423af4d027c02cd0602a4c4f6d67339aad3e87",
    "tools/hum/check_arrival_surfaces.py": "3aa54c8ab3946d2c078eca0073bb9a9369325d5f968e2e7e347e23b1e1431c34",
    "tools/hum/check_carrier_pure.py": "ca86a43031c4bfec0e559759d020ec5ef9029b56b16310cbe0fe57d381500ba6",
    "tools/hum/check_dialog_audience.cjs": "f9fa4688772bb012a73d614a4799aa36667aca2d9562fbcd7cc030bf3f10018c",
    "tools/hum/check_lesson_floor.cjs": "bed2465f7b63d06ef522103b2eb3fe923570e06379e76e3e68e2cb4573e41019",
    "tools/hum/dialog_audience_exceptions.json": "66986cf0f627b6dc78094cbbef889e396ced511a1a11edaa14fffd074a0856e0",
    "tools/hum/fix_dialog_audience.py": "ebe88f05eb8cc8ee4ff7214e720e33ac1c4f2bdfcdc1d8f05876b7a868222f36",
    "tools/hum/lesson_floor_known_red.json": "2a3795e23fbd1d77bcd313ef2b60555ac1a716328ecc269625faf387ac12014f",
    "tools/humanities_resources/STATIC_CHECK_RESULTS.json": "d8512ae1801218656d880ae9cc2d54603633f074d1d5ad8dde52c35f95b5fae0",
    "tools/humanities_resources/browser_checks.cjs": "3cd28955bac641364275700c1021dd901691b14ed66dc2a678a79b2787ea677f",
    "tools/launch_resources/W4L1_ACCEPTANCE.json": "f76b26e3cccb5926665c0ad43cfc9de43434b12ce2fd2d35afb98dbad437fe0e",
    "tools/launch_resources/author_w4l1.py": "a4c97b467aa101320099ffb00605ab5e71d8c2895a6e4c8c8f79a494e0de9b9f",
    "tools/launch_resources/author_w4l1_natives.py": "62dd0ef2244c9833cbc63e1a865878ea854b3b4f194710f408c12641cd417a38",
    "tools/lf1/check_admission_move.py": "b3751f7b034ea3e677ba7e3851b1b799d98986bdb4e828e9a632f44a801b59e2",
    "tools/relabel_public.py": "c81e059367a92c4cd30559853aeec35e53c9a4c7ceed31dd249b21cf82df0b9d",
    "tools/rw1/clear_home_link.py": "4481025a3caa09ee04ac9b8adea6d228cff3f0cbcd285b643829366ada06924b",
    "tools/rw1/dock_guide.py": "90a29d9f5497d46c79b061cd7f9287cae4694da6f7005c62b775b4a4f5fc1610",
    "tools/rw1/edits/W8B_plain_language.json": "5f3fa6d7b60ce5fcee2e0c8a222b4d7fa96d96265b3628ddaa6e60602e209dbd",
    "tools/rw1/parity.py": "392a6c5c53903384efee998f7257cdef200adf957bfbff83f7f57d4ff92adecc",
    "tools/rw1/pathways.py": "5bdc3d505903925c1d4abd7cd89a0ea3150e237e287183b7e79ef8bfa4796889",
    "tools/rw1/restore_lesson_config.py": "61f6b614a4bb22b15e85be538704eee6aa7585e9a88de38818b93d9b96f7f7e5",
    "tools/rx3_land.py": "92751ac6fb8885ac5f67dd3333f8dc3f894d2951d087a9727a86596f48032c17",
    "tools/sci/select_manifest_decks.py": "94e410bf7039c2cfe3e8ef10c1fa55d788cffb2c11a91e987844f1c9b9721d7d",
    "tools/science_pack/RESOURCE_CONTENT.json": "499da104f87c775b6de314d78477decba79baf41cbcf8ae6ea60637c66c35c70",
    "tools/science_pack/check_resource_dom.cjs": "ea837caafd3e6ddc1e966d7e731272f314c129a69999bf747b3e8c946150640c",
    "tools/science_pack/model_fixtures.json": "0c1f9689780131efc3bc2c251176a36ba1aad206b2eb594034c0a21784719667",
    "tools/science_pack/rebuild_resources.py": "ca3d4f06c2bb929ca2432d633450be6ae06a2bc1566bf3c235e57c8e92e46c6f",
    "tools/science_teaching_packs/cx2_s3_offline_edition.py": "6bba82926beb47bc49f6dd8acd06b3753762880a48de1f25460caa22b987ad4a",
    "tools/science_teaching_packs/test_source_binding.py": "f076213cfe8f8dfeaccef780a746191d86412f29380be232696e67442eb4abbc",
    "tools/stage_b_announcer.py": "41c95d4a3dcccb871d9edc0d9e0f023bb8930dec14e0c1ad6b9d383322bd3f6b",
    "tools/sx3/admit_landing_decks.py": "2ec9498f93c74079c007f31c76ec3dd6a0b82f15c3faaf6172b5a8252f3c0d54",
    "tools/sx3/align_shelf_titles.py": "826fe78ab4781d3d49418c7a97f844695539c43190f6122bae5a351ef8615dce",
    "tools/sx3/check_landing_titles.py": "446ca22a7adf531211bc346aea29029593e5141c699185582d12d65951409e55",
    "tools/sx3/test_admit_landing_decks.py": "536d68a8292e096a02aea30131f7e555b7591eff0f21748c8ef7d10e5e2278a7",
    "tools/ux2/add_edu_q1_companions.py": "b176374b6be6b49575e6daf42b720cc40e2df7642cf683f639ebb3bea09c5d63",
    "tools/ux2/lesson-outcome-baseline.json": "6590bec9c3ad848e87f8fd1237abb140d0e566e33bedfece69391a980c29ff7f",
    "tools/ux2/place_companion_packs.py": "3b6396a5397b6eceaa42885986f9fb7b5acc37d653ff7c2e1c6e31a25c9379bc",
    "tools/verify_fieldops_served.mjs": "af04a4099c6bb89d7787b8057f80a4aa842495b90da18b357e5b5b977344b0d7"
}
# RULING wb-1 (26 Oct 2026): the two Art manifests of the GROW and LAUNCH v3 trees, moved by M1 outside the protected
# trees and rewritten by the rename map only (each reproduces byte for byte), by exact digest.
WB1_MOVED_EXACT_SHA256 = {
    "GROW_Estate_v3/Art/manifest-v3.json": "8f376fd9fbf6d808481ad49098c452d0eb97cf3af3a0fa73cfcf7fc8307a6af9",
    "LAUNCH_Estate_v3/Art/manifest-v3.json": "e76aa2a810ba4a958028096b9b80f25090feb0f97347f7acf55e70636244512d"
}
# RULING wa-3 (26 Oct 2026): the BUILD D&T community hub, title and heading only (the word dropped), by exact digest.
WA3_EXACT_SHA256 = {
    "build_dt_upcycling.html": "3091a2e84328bef46aa9ecb532dbb5f64e46bd037037ed8f7daee5a41037d876"
}


def exact_byte_admitted(root: Path, changed: set[str]) -> set[str]:
    exact = {**SCHEME_SOURCE_EXACT_SHA256, **M1_RENAME_EXACT_SHA256, **WB1_MOVED_EXACT_SHA256, **WA3_EXACT_SHA256}
    return {rel for rel in changed if rel in exact and (root / rel).is_file()
            and digest(root / rel) == exact[rel]}


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
# Scope is exact and explicit: a pinned manifest is expanded only at
# <root>/<one path segment>/SHA256SUMS.txt for a root named in
# CATALOGUE_PACK_MANIFEST_ROOTS. The first root is the shape the HUM-D5 packs land
# in. The PIN1 re-pin ruling (7 Nov 2026) added the rest: PR #811's exact per-file
# pins took the derived workflow to 567,566 bytes and GitHub refused to load it
# again, so the non-HTML members of the Science Autumn 2 packs and of the Autumn 2
# engagement editions moved to manifests under the roots listed below, one root
# per pathway-term, lesson or pack folder. Members under every listed root are
# expanded and digest-checked here on every run. A root not listed is still not
# judged: the Science/Teaching_Packs manifests and the pathway-level Science
# manifests (W8-W13 and the like) stay outside it, so no file that was never part
# of a ruling is newly judged here.
CATALOGUE_PACK_MANIFEST_ROOTS = (
    "Humanities/Teaching_Packs",
    "Science/Build/Autumn_2_2026-27",
    "Science/Grow/Autumn_2_2026-27",
    "Science/Launch/Autumn_2_2026-27",
    "Art/Build/ART_BUILD_A2_W05_P1",
    "Art/Build/ART_BUILD_A2_W05_P2",
    "Art/Build/ART_BUILD_A2_W06_P1",
    "Art/Build/ART_BUILD_A2_W06_P2",
    "Art/Grow/ART_GROW_A2_W05_P1",
    "Art/Grow/ART_GROW_A2_W05_P2",
    "Art/Grow/ART_GROW_A2_W06_P1",
    "Art/Grow/ART_GROW_A2_W06_P2",
    "Art/Grow/ART_GROW_A2_W07_P1",
    "Art/Grow/ART_GROW_A2_W07_P2",
    "Careers/Build",
    "Careers/Launch",
    "DT/Launch",
    "PSHE/Grow",
    "RSE/Launch",
    "RSHE/Build",
    "Vocational/Build",
    "Vocational/Launch",
    "ICT/Teaching_Packs/GROW_Computing_Autumn2",
)
CATALOGUE_PACK_MANIFEST_NAME = "SHA256SUMS.txt"


def catalogue_pack_manifests(pins: dict) -> list[str]:
    """The pinned pack manifests whose listed members this gate expands."""
    roots = [root.split("/") for root in CATALOGUE_PACK_MANIFEST_ROOTS]
    return [rel for rel in sorted(pins)
            if rel.split("/")[-1] == CATALOGUE_PACK_MANIFEST_NAME
            and any(rel.split("/")[:len(root)] == root
                    and len(rel.split("/")) == len(root) + 2 for root in roots)]


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
            errors.append(f"reviewed catalogue requires the original {CATALOGUE_ORIGINAL_ROWS} rows plus exactly the reviewed hub rows")
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
    if not pins or "index.html" not in pins or "humanities.html" not in pins:
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

# RULING vz-4 (M1): the one rename map, every old path -> the new path it moved to. A move whose
# bytes are identical at the new path counts as unchanged; a moved file whose bytes changed is a
# change of its NEW path and meets the boundary and the fence like any other. The map is bound by
# its digest (a map whose bytes differ is refused, never read) and admits nothing by itself. A
# repository without the file (the Apps copy of this gate) has no moves to resolve.
RENAME_MAP_PATH = "tools/catalogue/M1_RENAME_MAP.json"
RENAME_MAP_SHA256 = "a815038114ff60fb7400d24a880a0a39ce7e678f483c9bd510346a63a6a83ce1"


def rename_map(root: Path) -> dict[str, str]:
    path = root / RENAME_MAP_PATH
    if not path.is_file():
        return {}
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != RENAME_MAP_SHA256:
        raise ValueError(f"unreviewed rename map: {RENAME_MAP_PATH}")
    declared = json.loads(data)
    # RULING wb-5: the moves are "pairs" only; "historicalPairs" (deleted before the move) are history and this gate,
    # which resolves moves and nothing else, never reads them.
    return dict(declared["pairs"])


def _tree_entries(root: Path, ref: str, paths: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    paths = sorted(set(paths))
    for at in range(0, len(paths), 1000):
        raw = subprocess.run(["git", "ls-tree", "-z", ref, "--", *paths[at:at + 1000]],
                             cwd=root, capture_output=True, check=True).stdout.decode("utf-8")
        for record in raw.split("\0"):
            if record:
                fields, rel = record.split("\t", 1)
                mode, _kind, blob = fields.split()
                found[rel] = f"{mode} {blob}"
    return found


def changed_paths(root: Path, base_ref: str, rows: list[tuple[str, str]]) -> set[str]:
    """M and D rows of a --no-renames diff, with each move the rename map names resolved: the old
    path's deletion leaves the set, and the new path joins it only if its bytes differ."""
    changed = {rel for status, rel in rows if status in ("M", "D")}
    backwards = {new: old for old, new in rename_map(root).items()}
    added = [rel for status, rel in rows if status == "A" and rel in backwards]
    if not added:
        return changed
    merge_base = subprocess.run(["git", "merge-base", base_ref, "HEAD"], cwd=root,
                                capture_output=True, text=True, check=True).stdout.strip()
    olds = [backwards[rel] for rel in added]
    before = _tree_entries(root, merge_base, olds)
    head = _tree_entries(root, "HEAD", olds + added)
    for rel in added:
        old = backwards[rel]
        if old in before and old not in head and old in changed:
            changed.discard(old)
            if before[old] != head.get(rel):
                changed.add(rel)
    return changed


# RULING wb-2 (26 Oct 2026): the one M1 replacement transaction (the change-boundary verifier declares it), bound here by
# the same digest. A file whose bytes differ is refused, never read; a repository without it (Apps) has none.
M1_TRANSACTION_PATH = "_glv3/M1_REPLACEMENT_TRANSACTION.json"
M1_TRANSACTION_SHA256 = "c508f9b3471df8462761136d198f332349a71f756b76709e5afa5545ea0b2268"


def m1_transaction_after(root: Path) -> dict[str, str]:
    path = root / M1_TRANSACTION_PATH
    if not path.is_file():
        return {}
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != M1_TRANSACTION_SHA256:
        raise ValueError(f"unreviewed M1 replacement transaction: {M1_TRANSACTION_PATH}")
    return {rel: row["afterSha256"] for rel, row in json.loads(data)["files"].items()}


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
    # RULING wb-2 (26 Oct 2026): a fenced deck whose bytes are exactly its M1 transaction after-digest (the rename map
    # rewrite, declared in M1_TRANSACTION_PATH) is accepted; every other change to a fenced deck is refused as before.
    try:
        after = m1_transaction_after(root)
    except (ValueError, OSError) as exc:
        return [str(exc)]
    hit = [rel for rel in hit if not (rel in after and (root / rel).is_file() and digest(root / rel) == after[rel])]
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
             if rel.startswith("Science/") and rel.endswith(".html")]
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
        THEME_COPY: canonical / "theme.js"
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
            # RULING vz-4: --no-renames, so a move is its deletion and its addition, and the
            # rename map (changed_paths) resolves each one it names; nothing else is resolved.
            ["git", "diff", "--name-status", "-z", "--no-renames", "--diff-filter=AMD", f"{base_ref}...HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
        )
        if proc.returncode:
            errors.append(f"git diff failed: {proc.stderr.strip()}")
        else:
            fields = proc.stdout.split("\0")
            if fields and fields[-1] == "":
                fields.pop()
            changed = changed_paths(root, base_ref, list(zip(fields[::2], fields[1::2])))
            errors.extend(boundary_errors(changed - exact_byte_admitted(root, changed), kind))   # rm-2
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
                admitted = m1_transaction_after(root)
                # The red control uses a fenced deck the M1 transaction does not admit at its current bytes (wb-2).
                one = next(row["path"] for row in fenced if row["path"] not in admitted)
                if not fence_errors(root, {one}, "lessons"):
                    raise RuntimeError("the fence let a fenced deck through: " + one)
                if fence_errors(root, {"Science/Build/does-not-exist.html"}, "lessons"):
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
                # RULING wb-2: a fenced deck at exactly its transaction after-digest is accepted; one changed byte is refused.
                taken = [row["path"] for row in fenced if row["path"] in admitted]
                for rel in taken:
                    if fence_errors(root, {rel}, "lessons"):
                        raise RuntimeError("the fence refused a fenced deck at its M1 transaction bytes: " + rel)
                    with tempfile.TemporaryDirectory(prefix="mbm-fence-m1-") as scratch:
                        fence_fixture = Path(scratch)
                        for copy in (FENCE_PATH, M1_TRANSACTION_PATH, rel):
                            (fence_fixture / copy).parent.mkdir(parents=True, exist_ok=True)
                            shutil.copyfile(root / copy, fence_fixture / copy)
                        if fence_errors(fence_fixture, {rel}, "lessons"):
                            raise RuntimeError("the fence refused the transaction bytes in a fence_fixture: " + rel)
                        data = bytearray((fence_fixture / rel).read_bytes())
                        data[len(data) // 2] ^= 0x01
                        (fence_fixture / rel).write_bytes(bytes(data))
                        if not fence_errors(fence_fixture, {rel}, "lessons"):
                            raise RuntimeError("the fence let a one-byte change to a fenced deck through: " + rel)
                # RULING wb-5: a historical pair of the rename map cannot admit a move here.
                declared = json.loads((root / RENAME_MAP_PATH).read_bytes()) if (root / RENAME_MAP_PATH).is_file() else {}
                for old, new in declared.get("historicalPairs", {}).items():
                    if changed_paths(root, "HEAD", [("D", old), ("A", new)]) != {old}:
                        raise RuntimeError("a historical rename pair was resolved as a move: " + new)
                print(f"SX3 fence controls: {len(fenced)} fenced path(s) red / unfenced path green / apps estate quiet / empty and unreadable fence red / {len(taken)} at M1 transaction bytes green, one byte off red")
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
