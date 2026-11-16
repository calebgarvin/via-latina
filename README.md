# Via Latina

A private, offline Progressive Web App for reading *Lingua Latina per se Illustrata, Pars I: Familia Romana*
(chapters I–XXXV) in one year, 10–15 minutes a day, with a pixel-art road through Rome as the progress map.

- 312 reading days (6 a week) + a weekly catch-up/review day → 52 weeks.
- Each day: a short reading (~140 words, shorter at the start; tap any word for its gloss and margin note),
  then 6–10 review items: spaced-repetition flashcards (SM-2: Again/Hard/Good/Easy), ending/case/conjugation drills
  that only use grammar already introduced, and comprehension questions in simple Latin (with an optional English hint).
- Finishing the review walks your Roman one stop further along the via. Chapters are districts with a title card and a
  triumphal arch; every week ends at a rest stop with a milestone; the Capitol is the final stop.
- Plain HTML/CSS/JS, no build step for the app, no backend, no external requests at runtime. Works fully offline.

> **The book text is copyrighted.** The site is public, so all book content (text, vocabulary, questions) is shipped
> only as `content.enc`, encrypted with AES-256-GCM using a key derived (PBKDF2-SHA256, 310 000 iterations) from your
> passphrase. Without the passphrase the site shows only a lock screen. The unencrypted sources and the build scripts
> live in `content-src/`, which is git-ignored and must never be committed.

---

## 1. Build / encrypt the content

Requirements: Node 18+ and Python 3 (the content scripts use only the standard library, plus Pillow for the art script).

The OCR stage has already been run; its results are cached in `content-src/work/`. To (re)build the encrypted file:

```bash
node content-src/build.mjs
```

It asks for your passphrase (or reads it from `LL_PASSPHRASE`) and writes `content.enc` and `content.version`.
Choose a long passphrase (a few unrelated words). The salt is kept in `content-src/work/salt.bin`, so rebuilding with the
**same** passphrase keeps your phone unlocked; a new passphrase means re-entering it once on each device.

If you change the vocabulary (`content-src/vocab/*.txt`) or the tools, run the whole pipeline:

```bash
sh content-src/rebuild.sh
```

That rebuilds the content, the schedule and review items, the OCR report, `content.enc`, and runs the validator.

**Keep a private backup of `content-src/`** (for example in iCloud Drive). It is the only copy of the extracted text and
vocabulary, and it never goes to GitHub.

### Validate

```bash
node tools/validate.mjs
```

It checks that every day 1–312 has text, vocabulary and review items, that no reading starts or ends mid-sentence,
that every paragraph is scheduled, and that every asset in `assets/assets.json` exists at its declared size.
Add `--enc` to validate the shipped encrypted file instead (asks for the passphrase).

### The OCR report

`content-src/OCR_REPORT.md` lists everything the extraction was unsure about: unknown words (with chapter and line), automatic
OCR corrections, lines dropped as illustration text, line-numbering gaps, and chapters whose lectio markers could not be found.
It stays private because it quotes the book.

## 2. Deploy to GitHub Pages

1. Commit and push everything (git ignores `content-src/` and the PDF):
   ```bash
   git add -A
   git commit -m "Update content"
   git push
   ```
2. On GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main` / root**.
3. After a minute the app is at `https://<username>.github.io/<repo>/`. All paths are relative, so the project subpath works.

Updates: push again. The service worker serves the cached app instantly and refreshes it in the background, so changes
show on the next launch. If you change files under `js/` or `css/`, also bump `CACHE` in `sw.js` (for example `via-latina-v2`).

The page has `noindex` meta tags. The repo is public, but it contains only code, art and the encrypted content.

## 3. Install on iPhone

1. Open the Pages URL in **Safari** (iOS 16.4 or newer).
2. Enter your passphrase once. The decryption key is then cached on the device.
3. Tap **Share → Add to Home Screen**, then launch Via Latina from the home screen icon.
4. Open it once while online so everything is cached. After that it works in airplane mode.

The home-screen app has its own storage, separate from Safari's, so you'll enter the passphrase once more on its first launch.

## 4. Back up and restore progress

Progress lives only on the device, in IndexedDB with a localStorage mirror; the app asks iOS for persistent storage.

- **Export:** Optiōnēs → *Export backup* opens the iOS share sheet. Save the `via-latina-backup-YYYY-MM-DD.json` file to Files/iCloud Drive or mail it to yourself.
  The app shows a gentle reminder if your last backup is more than 30 days old.
- **Restore:** Optiōnēs → *Import backup* → pick the file. It replaces the progress on that device.

## Schedule rules

- The default catch-up day is Sunday; change it in Optiōnēs. If you're behind, the catch-up day serves the next reading. If you're caught up, it's a relaxed cumulative review.
- More than a week behind? The map offers two choices: *double up* (two readings a day until caught up) or *move the finish date*. Nothing is ever lost.
- Rest days never break a streak.
- Read ahead whenever you like.

## Project layout

```
index.html, manifest.webmanifest, sw.js   app shell, PWA manifest, offline cache
css/app.css                               styles (light/dark, safe areas)
js/                                       app modules (no framework, ES modules)
content.enc                               encrypted course content (the only book data in the repo)
assets/assets.json + PNGs                 all art; the app reads nothing else (see ART_GUIDE.md)
icons/                                    home-screen icons (also listed in assets.json)
tools/validate.mjs                        validation script
tools/make_placeholder_art.py             regenerates placeholder art, assets.json and ART_GUIDE.md
tools/serve.mjs                           local test server: node tools/serve.mjs  → http://127.0.0.1:8765
content-src/  (git-ignored)               OCR pipeline, vocabulary, schedule builder, encryption script, OCR report
```

## Swapping in the final art

See [ART_GUIDE.md](ART_GUIDE.md). To swap art, replace the PNGs at the same size, or edit `assets/assets.json`
(frame counts, fps and anchors are read from there). No code changes are needed.
If you re-run `make_placeholder_art.py` after adding real art, pass `--keep` so existing PNGs aren't overwritten.
