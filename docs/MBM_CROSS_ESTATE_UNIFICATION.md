# Made by Matt cross-estate unification — Apps

Sentinel: `mbm-cross-estate-unification-lessons-apps-2026-08-08`

## Scope and baseline

This release starts from Matt-s-Apps- `main` commit `298c4381982ef44e69f6b4f20b9dc015bb5ed96d` and upgrades the public `/Matt-s-Apps-/` creator hub. It does not inject a platform shell into the individual studios or alter their specialised controls, storage or offline-first operation.

The measured starting estate contains 40 tracked files, including 31 HTML files, one CSS file, one JavaScript file and three JSON files. `apps.json` remains the catalogue source of truth and currently contains 31 studios across seven spaces: Teacher tools 10, Make & create 6, Art & design 5, Documents 1, Learn & organise 6, Calm corner 2 and Play & explore 1.

## Deployment topology

GitHub-hosted verification established that `https://madebymatt.uk/Matt-s-Apps-/` and `https://madebymatt.uk/Matt-s-Apps-/apps.json` are served as a project mount under the same `madebymatt.uk` origin as Home, Games, Lessons, Tools and Resources. Public path casing remains `/Matt-s-Apps-/`.

## Canonical platform source

The design and interaction reference is `MattRoper1977/mattroper1977.github.io` at measured commit `4681ba6b4533745f42542c1591a4bda5de0b8cfc`.

This repository carries controlled local copies so the creator hub does not require the main-site asset server to function:

- `assets/mbm-platform.css` — SHA-256 `e3eb9b83d3c791eca059386999c306711678877bba27248cc78a1ef584e1031d`
- `assets/mbm-platform.js` — SHA-256 `0958a73a78a9f6d428d6cbe6c77a8a1cd5f015022ce9a6acbba92e6bee901fd2`
- `assets/mbm-theme.js` — SHA-256 `5d711139ee95f2a9814917c516ffe674fbd52fd0b42c8fd6e22a1efbc19f002b`
- `assets/mbm-hub.css` — shared Lessons/Apps integration layer, SHA-256 `1643f51bcfe7f89923e908cf4f79b36a80d8bfa767779ab1c9cebe2e1a8b513c`

The permanent contract test compares these copies with the current canonical
repository. `mbm-platform.css` and `mbm-platform.js` must match it byte-for-byte.
`mbm-theme.js` is not a maintained file at all: it is **generated** from the
site repository's `theme.js` by `tools/sync_theme.py`, and the test asserts it
is that file verbatim behind one header line — the same strictness, plus a
notice at the top of the copy telling the next person where to edit. The digest
above is written by the same run that writes the copy, so it cannot go stale on
its own. See `docs/THEME_ENGINE.md` in the site repository.

Updating the platform shell is therefore an explicit synchronisation operation
rather than silent drift.

## What changes

- A common Made by Matt header with the route order Games, Lessons, Apps, Tools and Resources.
- Correct Apps current-page state and stable case-sensitive URLs.
- The canonical mobile drawer, Escape/outside dismissal, focus return and scroll lock.
- The canonical `mbm_reading_theme` background preference using a repo-local theme engine.
- Stronger hub spacing, surface, card, focus, touch and responsive treatment while retaining the Apps creative/productive identity.
- Keyboard-scrollable audience and space rails.
- Accessible live result announcements and a clear-filter route.
- Defensive manifest loading and link handling.
- The lead studio count is now derived from `apps.json`, correcting the stale authored number without creating another hard-coded copy.

Application names, descriptions, audience mapping, categories, logo markup and studio source files remain unchanged.

## Offline and standalone boundary

Only the hub and its local shared assets are in scope. The verifier rejects any changed path outside the explicit allow-list, including all 31 individual studio files and `apps.json`.

The browser gate also opens representative creative, data-management, wellbeing and classroom studios after the hub changes. This proves that the release has not introduced mandatory platform dependencies, global CSS collisions or navigation/runtime regressions into standalone applications.

## Verification

Run locally or in CI:

```bash
python tools/verify_cross_estate_unification.py \
  --base origin/main \
  --canonical _reference/site \
  --self-test

MBM_BASE_URL=http://127.0.0.1:4173/Matt-s-Apps-/ \
  node tools/verify_cross_estate_browser.mjs
```

The static positive control deliberately changes `/Lessons/` to `/lessons/` in a temporary fixture and must fail before the release can pass. The same navigation contract is used in both repositories, so this catches case drift from either hub.
