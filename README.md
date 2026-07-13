# ScoreForge

A free, open music composition app for Android. Write sheet music with
unlimited scores and unlimited instruments — every feature is free, there is no
paid tier, no account, and it works fully offline.

Inspired by the workflow of browser-based notation editors, built from scratch
with open-source components.

## Features

- **Notation editor** — enter notes and rests on a real engraved staff
  (whole through 32nd notes, dots, ties, sharps/flats/naturals, chords,
  dynamics), with tap-to-select and step-wise transposition.
- **Unlimited scores** — the library holds as many scores as your device can
  store. Create, rename, duplicate, delete.
- **Unlimited parts & instruments** — 70+ instruments across keyboards,
  strings, woodwinds, brass, guitars, voices, pitched percussion, synths, and a
  drum set with pad entry. All free.
- **Playback** — hear the whole arrangement with per-instrument synthesized
  sounds, per-part volume and mute, tempo from 30–240 BPM, and a moving play
  highlight that follows the score.
- **Key & time signatures** — all major/minor keys up to 6 sharps/flats;
  2/4, 3/4, 4/4, 5/4, 6/8, 9/8, 12/8, 2/2, 3/8 with automatic reflow.
- **Import / export** — MusicXML export (opens in MuseScore, Flat, Sibelius,
  Finale…), MusicXML import, and a native `.scoreforge.json` backup format.
  Exports land in your Downloads folder.
- **Offline & private** — no network access, no telemetry, no sign-in.
  Scores are saved on-device automatically as you edit.

## Getting the APK

Every push to this repository builds a debug-signed APK via GitHub Actions:

1. Open the repo's **Actions** tab and pick the latest **Build APK** run.
2. Download the **ScoreForge-apk** artifact (a zip containing
   `ScoreForge-debug.apk`).
3. Copy the APK to the phone, tap it, and allow *Install from unknown sources*
   when prompted. Android 8.0 (API 26) or newer is required.

## Building locally

Requirements: JDK 17, Android SDK (API 34), Gradle 8.7+.

```bash
cd android
gradle assembleDebug        # or ./gradlew if you generate a wrapper
# output: android/app/build/outputs/apk/debug/app-debug.apk
```

## Project layout

```
android/                        Android WebView wrapper (no dependencies)
  app/src/main/java/...         MainActivity: WebView + file export bridge
  app/src/main/assets/www/      the actual app (vanilla JS, offline)
    js/model.js                 score data model + editing operations
    js/renderer.js              staff rendering (VexFlow) + tap hit-testing
    js/playback.js              Web Audio synth engine + scheduler
    js/musicxml.js              MusicXML export / import
    js/instruments.js           instrument catalog (all free)
    js/storage.js               localStorage persistence + file export
    js/app.js                   UI controller
  app/src/main/assets/www/vendor/vexflow-bravura.js   VexFlow 4.2.5 (MIT)
.github/workflows/build-apk.yml CI: builds the debug APK artifact
```

The web app also runs in any desktop browser for development: serve
`android/app/src/main/assets/www/` with any static file server.

## License notes

VexFlow is © Mohit Muthanna Cheppudira, MIT license. Everything else in this
repository is original code.
