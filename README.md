# Matt's Apps — Studio Suite

by **Matt Roper**

A collection of **23 self-contained, offline, single-file web tools** for the classroom. Every tool is one `.html` file with no installation, no accounts, no servers and no internet required after download — just open it in a browser (Chromebook, phone, tablet or desktop). Nothing a pupil makes ever leaves the device.

Built by Matt Roper for an SEMH alternative-provision setting: big touch targets, calm visuals, no leaderboards, and accessibility (reduced-motion support, keyboard handling) as defaults.

## ▶ Quick start

**Option A — just open the files.** Download the repository (green **Code** button → **Download ZIP**), unzip it, and open **`index.html`** (or **`Suite_Hub.html`**) in your browser. Every tool launches from there.

**Option B — host it free on GitHub Pages.** In the repository, go to **Settings → Pages**, set the source to the `main` branch, and save. After a minute your suite is live at:

```
https://<your-username>.github.io/<repository-name>/
```

Share that single link with staff or pupils and bookmark it.

## 🧰 The tools

### Make & create
| Tool | What it does |
|---|---|
| **Craft Studio** | Write real typed code to drive a robot through a block world — ten levels from sequences to loops to selection, plus a free-build sandbox. |
| **Web Studio** | Build a real web page in HTML & CSS with a live preview; exports a standalone `.html` page. |
| **Animation Studio** | Stop-motion animation with onion-skinning; exports a `.webm` film. |
| **Video Studio** | A timeline video editor — clips, titles, transitions, music and voiceover. |
| **Audio Studio** | Record, edit and trim sound; screen-recording for teaching clips; a soundboard and a class noise meter. |
| **Music Studio** | A five-track groove-box (drums, bass, two melodies, chord pad) with key/scale choice, per-step note length, song arrangement and instant WAV export. |

### Art & design
| Tool | What it does |
|---|---|
| **Art Studio** | A layered paint app with symmetry and stamps. |
| **Design Studio** | Posters, certificates and layouts with magnetic snapping; PNG and PDF export. |
| **Photo Studio** | Combine photos, stickers and text; masks, filters and cut-outs. |
| **Comic Studio** | Multi-panel comics with speech/think/shout bubbles, captions, stickers and photo or colour panels; exports PNG and PDF. |

### Documents
| Tool | What it does |
|---|---|
| **PDF Studio** | Annotate, edit text, and reorder/merge/split pages. |
| **Evidence Binder** | Capture and tag pupil work against unit outcomes; builds a print-ready PDF portfolio per pupil; full backup/restore as a `.zip`. |

### Learn & organise
| Tool | What it does |
|---|---|
| **Graph & Data Studio** | Turn a results table into a labelled bar/line/scatter/pie chart, with mean, median, range and more worked out automatically. |
| **Typing Tutor** | Build typing speed and accuracy across home/top/bottom rows, words, sentences and capitals, with an on-screen guide keyboard. |
| **Message & Email Studio** | Coaches clear, polite, well-structured messages for real situations (emailing a teacher, replying to a college, asking for help, apologising, making a fair complaint), with a live checklist. Never sends anything. |
| **Writing Frames Studio** | Scaffolded writing for any genre (recount, persuasive, story mountain, science write-up, comic-to-paragraph, formal letter): each frame breaks the task into boxes with sentence starters and word banks, then stitches them into a finished piece to copy or save. |
| **Flashcards & Quiz Studio** | Make revision decks (term + meaning) for any subject, then revise with spaced-repetition flip-cards (tricky cards return sooner) or auto-generated multiple-choice quizzes. Pupils can build their own decks. |
| **Now / Next Board** | A calm visual schedule for transitions — Now / Next / Then cards with pictures. |

### Teacher tools
| Tool | What it does |
|---|---|
| **Classroom Toolkit** | Four classroom utilities in one: a fair random name picker (no repeats until everyone's had a turn), a balanced group maker, a calm visual countdown timer, and a class noise meter. |
| **Seating Plan Studio** | Drag pupils onto a desk layout (rows, pairs, group tables or U-shape), flag "keep apart" pairs that warn if seated together, auto-fill fairly, and export the plan as a picture to print. |
| **Rubric & Feedback Studio** | Build a reusable marking rubric (criteria, weighted levels), tick a level per criterion for each pupil, and it computes a grade and writes structured strengths-first feedback (What went well / Even better if / Next steps). Export a printable PDF feedback sheet per pupil. |

### Calm corner
| Tool | What it does |
|---|---|
| **Feelings Check-in** | A calm, private Zones-style check-in: a pupil taps how they're arriving (Blue / Green / Yellow / Red), picks a feeling word, and gets matched, doable calming or alerting strategies — plus guided breathing and an optional "show my teacher" screen. Nothing is ever saved. Validating, never corrective; gently signposts a trusted adult for big feelings. |
| **Regulation Station** | A wellbeing aid — guided breathing, 5-4-3-2-1 grounding, muscle-release, generated calm sounds and a quiet timer. Nothing is recorded. |

## 🔒 Privacy & safety

- **Everything runs locally in the browser.** No data is uploaded anywhere; there are no analytics, accounts or trackers.
- Tools that keep your work (e.g. Evidence Binder, Comic Studio) save it in that browser on that device using local storage — treat the device and any exported backups with the same care as a paper file.
- The tools are designed to be classroom-safe: Web Studio's preview disables `<script>`, Message & Email Studio cannot send, and Regulation Station keeps no mood log.

## 🛠 Technical notes

- Each file is plain HTML + CSS + vanilla JavaScript. Two tools load small, well-known libraries from a CDN when online (PDF Studio uses pdf.js and pdf-lib); the rest are fully self-contained.
- No build step. To tweak a tool, edit its `.html` file and refresh.
- Tested on Chromebook, phone and desktop browsers.

## 📄 Licence & use

Created by **Matt Roper**. Free to use and adapt for educational purposes.
