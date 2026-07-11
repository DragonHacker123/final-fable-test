# Synthwave Studio

A complete synthwave production rig in a **single self-contained HTML file**:
polyphonic synths, a drum machine, a 64-step sequencer, tempo-synced ping-pong
delay, convolution reverb, and a neon-horizon visualizer — all built from raw
Web Audio API nodes. No samples, no libraries, no network.

**Open `index.html` and press Play.** A demo song in A minor (Am–F–C–G) is
pre-loaded across all seven tracks.

## Tracks

| Track | Engine |
|-------|--------|
| LEAD | detuned saw stack → resonant lowpass with filter envelope |
| ARP | bright synth with sidechain-style pumping against the kick |
| BASS | fat mono saw/square bass |
| KICK | pitch-swept sine thump (pure synthesis) |
| SNARE | filtered noise burst + tonal body |
| HAT / OPEN H | shaped high-passed noise |

Every drum is synthesized from oscillators and noise buffers at runtime —
there is not a single audio file in the project.

## Features

- **16 steps × 4 bars** per track; click cells to edit the pattern, with
  per-track volume, mute, and delay/reverb sends
- **Playable lead**: computer keys A–K are a piano row (W/E/T/Y/U sharps),
  with octave switching
- **ADSR envelopes**, LFO, resonant filters — classic subtractive voice
  architecture per synth patch
- **Tempo-synced dotted-eighth ping-pong delay** and a **convolver reverb**
  whose impulse response is procedurally generated noise-decay (no IR file)
- **Lookahead scheduler**: audio events are queued against the AudioContext
  clock a chunk ahead of time, so playback stays sample-accurate even when
  the UI thread hiccups — the standard "two clocks" Web Audio pattern
- **Visualizer**: neon grid horizon, setting sun, and spectrum bars driven by
  an AnalyserNode, all canvas-drawn
- BPM slider (70–160, default 106); AudioContext resumes on first
  gesture to satisfy autoplay policies

## Architecture

One `AudioContext` graph: per-track voice → track gain → master bus, with
parallel send buses for delay and reverb. The sequencer's `schedulerTick`
runs on a short interval, scheduling every step that falls inside the
lookahead window using exact AudioContext timestamps.
