/* ScoreForge — Web Audio playback engine.
 * Lightweight subtractive/additive synth patches per instrument family, so the
 * whole app works offline with a tiny footprint. Notes are scheduled ahead of
 * time on an AudioContext; a rAF loop drives the visual play cursor.
 */
'use strict';

const Playback = (() => {
  let ctx = null;
  let master = null;
  let partGains = [];
  let playing = false;
  let startTime = 0;
  let sequence = [];
  let totalDur = 0;
  let rafId = 0;
  let onTick = null;
  let onEnd = null;
  let activeNodes = [];

  function ensureContext() {
    if (!ctx) {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      master = ctx.createDynamicsCompressor();
      master.threshold.value = -18;
      master.knee.value = 20;
      master.ratio.value = 8;
      const out = ctx.createGain();
      out.gain.value = 0.9;
      master.connect(out);
      out.connect(ctx.destination);
    }
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
  }

  function midiToFreq(midi) {
    return 440 * Math.pow(2, (midi - 69) / 12);
  }

  /* Patch definitions: how each family sounds.
   * a/d/r: envelope seconds; s: sustain level; osc: [type, detuneCents, gain][]
   * lp: lowpass cutoff as multiple of fundamental; lpMax caps the cutoff.
   */
  const PATCHES = {
    piano:   { a: 0.004, d: 1.1, s: 0.12, r: 0.25, decayToS: true, osc: [['triangle', 0, 0.8], ['sine', 0, 0.4], ['triangle', 2, 0.15]], lp: 8, lpMax: 6500 },
    epiano:  { a: 0.004, d: 0.9, s: 0.2, r: 0.2, decayToS: true, osc: [['sine', 0, 0.8], ['triangle', 0, 0.25]], lp: 6, lpMax: 5000 },
    organ:   { a: 0.03, d: 0.05, s: 0.9, r: 0.12, osc: [['sine', 0, 0.5], ['sine', 1200, 0.3], ['sine', 1902, 0.18], ['sine', 2400, 0.12]], lp: 12, lpMax: 8000 },
    strings: { a: 0.14, d: 0.2, s: 0.8, r: 0.3, osc: [['sawtooth', -6, 0.35], ['sawtooth', 6, 0.35], ['sawtooth', 0, 0.2]], lp: 5, lpMax: 4500, vibrato: true },
    pluck:   { a: 0.002, d: 0.7, s: 0.0, r: 0.15, decayToS: true, osc: [['triangle', 0, 0.9], ['square', 0, 0.12]], lp: 7, lpMax: 5200 },
    flute:   { a: 0.09, d: 0.1, s: 0.85, r: 0.18, osc: [['sine', 0, 0.85], ['triangle', 0, 0.12]], lp: 4, lpMax: 4000, vibrato: true, breath: 0.012 },
    reed:    { a: 0.06, d: 0.1, s: 0.85, r: 0.15, osc: [['square', 0, 0.35], ['sawtooth', 0, 0.2], ['sine', 0, 0.25]], lp: 5, lpMax: 4200, vibrato: true },
    sax:     { a: 0.05, d: 0.15, s: 0.85, r: 0.18, osc: [['sawtooth', 0, 0.45], ['square', 0, 0.18], ['sine', 0, 0.2]], lp: 4.5, lpMax: 4200, vibrato: true },
    brass:   { a: 0.05, d: 0.12, s: 0.85, r: 0.16, osc: [['sawtooth', 0, 0.55], ['sawtooth', 4, 0.25]], lp: 6, lpMax: 5500, vibrato: true },
    lead:    { a: 0.01, d: 0.1, s: 0.8, r: 0.12, osc: [['square', -4, 0.35], ['sawtooth', 4, 0.35]], lp: 8, lpMax: 7000 },
    pad:     { a: 0.35, d: 0.3, s: 0.85, r: 0.6, osc: [['sawtooth', -8, 0.22], ['sawtooth', 8, 0.22], ['triangle', 0, 0.3]], lp: 4, lpMax: 3600 },
    bass:    { a: 0.006, d: 0.5, s: 0.4, r: 0.15, decayToS: true, osc: [['triangle', 0, 0.7], ['sine', 0, 0.4], ['sawtooth', 0, 0.08]], lp: 4, lpMax: 1800 },
    choir:   { a: 0.22, d: 0.25, s: 0.85, r: 0.4, osc: [['sine', 0, 0.5], ['triangle', -7, 0.2], ['triangle', 7, 0.2]], lp: 3.5, lpMax: 3000, vibrato: true, breath: 0.008 },
    bells:   { a: 0.002, d: 1.4, s: 0.0, r: 0.3, decayToS: true, osc: [['sine', 0, 0.7], ['sine', 1902, 0.25], ['sine', 3100, 0.1]], lp: 16, lpMax: 9000 },
    timpani: { a: 0.003, d: 0.9, s: 0.0, r: 0.2, decayToS: true, osc: [['sine', 0, 0.9], ['sine', 150, 0.3]], lp: 3, lpMax: 900, noise: 0.15, noiseDecay: 0.12 },
  };

  function scheduleTone(dest, patch, freq, t, dur, vel) {
    const p = PATCHES[patch] || PATCHES.piano;
    const env = ctx.createGain();
    env.gain.value = 0;
    env.connect(dest);

    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = Math.min(p.lpMax, freq * p.lp);
    filter.Q.value = 0.7;
    filter.connect(env);

    const stopAt = t + dur + p.r + 0.05;

    for (const [type, det, g] of p.osc) {
      const osc = ctx.createOscillator();
      osc.type = type;
      osc.frequency.value = freq;
      osc.detune.value = det;
      const og = ctx.createGain();
      og.gain.value = g * vel;
      osc.connect(og);
      og.connect(filter);
      if (p.vibrato && dur > 0.25) {
        const lfo = ctx.createOscillator();
        lfo.frequency.value = 5.2;
        const lfoGain = ctx.createGain();
        lfoGain.gain.value = freq * 0.006;
        lfo.connect(lfoGain);
        lfoGain.connect(osc.frequency);
        lfo.start(t + 0.15);
        lfo.stop(stopAt);
        activeNodes.push(lfo);
      }
      osc.start(t);
      osc.stop(stopAt);
      activeNodes.push(osc);
    }

    if (p.noise || p.breath) {
      const nsrc = makeNoise();
      const ng = ctx.createGain();
      const level = (p.noise || p.breath) * vel;
      ng.gain.setValueAtTime(level, t);
      if (p.noiseDecay) ng.gain.exponentialRampToValueAtTime(0.0001, t + p.noiseDecay);
      nsrc.connect(ng);
      ng.connect(filter);
      nsrc.start(t);
      nsrc.stop(p.noiseDecay ? t + p.noiseDecay + 0.02 : stopAt);
      activeNodes.push(nsrc);
    }

    // amplitude envelope
    const peak = 0.9 * vel;
    env.gain.setValueAtTime(0, t);
    env.gain.linearRampToValueAtTime(peak, t + p.a);
    if (p.decayToS) {
      env.gain.setTargetAtTime(peak * p.s, t + p.a, p.d / 3);
    } else {
      env.gain.linearRampToValueAtTime(peak * p.s, t + p.a + p.d);
    }
    env.gain.setValueAtTime(env.gain.value !== undefined ? peak * Math.max(p.s, 0.0001) : peak, Math.max(t + p.a, t + dur));
    env.gain.linearRampToValueAtTime(0.0001, t + dur + p.r);
  }

  let noiseBuf = null;
  function makeNoise() {
    if (!noiseBuf) {
      noiseBuf = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
      const d = noiseBuf.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    const src = ctx.createBufferSource();
    src.buffer = noiseBuf;
    src.loop = true;
    return src;
  }

  /* Unpitched drum sounds. */
  function scheduleDrum(dest, sound, t, vel) {
    const g = ctx.createGain();
    g.connect(dest);
    const end = (dur, level) => {
      g.gain.setValueAtTime(level * vel, t);
      g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    };
    if (sound === 'kick' || sound === 'tomHi' || sound === 'tomMid' || sound === 'tomLo' || sound === 'timpani') {
      const f0 = { kick: 120, tomHi: 220, tomMid: 170, tomLo: 130, timpani: 110 }[sound];
      const osc = ctx.createOscillator();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(f0, t);
      osc.frequency.exponentialRampToValueAtTime(Math.max(35, f0 * 0.35), t + 0.18);
      osc.connect(g);
      end(sound === 'kick' ? 0.22 : 0.3, 1.0);
      osc.start(t);
      osc.stop(t + 0.35);
      activeNodes.push(osc);
    } else if (sound === 'snare') {
      const n = makeNoise();
      const bp = ctx.createBiquadFilter();
      bp.type = 'bandpass'; bp.frequency.value = 1800; bp.Q.value = 0.8;
      n.connect(bp); bp.connect(g);
      end(0.16, 0.8);
      n.start(t); n.stop(t + 0.2);
      const osc = ctx.createOscillator();
      const og = ctx.createGain();
      osc.type = 'triangle'; osc.frequency.value = 190;
      og.gain.setValueAtTime(0.5 * vel, t);
      og.gain.exponentialRampToValueAtTime(0.0001, t + 0.09);
      osc.connect(og); og.connect(dest);
      osc.start(t); osc.stop(t + 0.12);
      activeNodes.push(n, osc);
    } else { // cymbals / hats
      const n = makeNoise();
      const hp = ctx.createBiquadFilter();
      hp.type = 'highpass';
      hp.frequency.value = sound === 'ride' ? 5000 : 7000;
      n.connect(hp); hp.connect(g);
      const durs = { hihat: 0.06, hihatOpen: 0.4, crash: 0.9, ride: 0.5 };
      end(durs[sound] || 0.2, sound === 'crash' ? 0.8 : 0.5);
      n.start(t); n.stop(t + (durs[sound] || 0.2) + 0.05);
      activeNodes.push(n);
    }
  }

  /* Flatten the score into a schedule. Tied notes merge into one long note. */
  function buildSequence(score) {
    const secPerTick = 60 / (score.tempo * TICKS_PER_QUARTER);
    const seq = [];
    let total = 0;
    score.parts.forEach((part, p) => {
      const inst = getInstrument(part.instrumentId);
      let t = 0;
      const consumed = new Set();
      part.measures.forEach((measure, m) => {
        measure.events.forEach((ev, e) => {
          const durSec = eventTicks(ev) * secPerTick;
          const key = m + ':' + e;
          if (ev.type === 'note' && !consumed.has(key)) {
            // merge following tied notes with identical pitches
            let noteDur = durSec;
            let cm = m, ce = e, cev = ev;
            while (cev.tie) {
              const next = nextNote(part, cm, ce);
              if (!next || next.ev.type !== 'note') break;
              if (!samePitches(cev.keys, next.ev.keys)) break;
              noteDur += eventTicks(next.ev) * secPerTick;
              consumed.add(next.m + ':' + next.e);
              cm = next.m; ce = next.e; cev = next.ev;
            }
            const vel = ev.dynamic ? ({ pp: 0.35, p: 0.5, mp: 0.65, mf: 0.8, f: 0.95, ff: 1.1 }[ev.dynamic] || 0.8) : 0.8;
            seq.push({
              t, dur: noteDur, p, m, e,
              kit: !!inst.kit,
              patch: inst.patch,
              vel,
              keys: ev.keys.map((k) => Object.assign({}, k)),
            });
          }
          t += durSec;
        });
      });
      total = Math.max(total, t);
    });
    seq.sort((a, b) => a.t - b.t);
    return { seq, total };
  }

  function nextNote(part, m, e) {
    let mm = m, ee = e + 1;
    while (mm < part.measures.length) {
      const evs = part.measures[mm].events;
      if (ee < evs.length) return { m: mm, e: ee, ev: evs[ee] };
      mm += 1; ee = 0;
    }
    return null;
  }

  function samePitches(a, b) {
    if (a.length !== b.length) return false;
    const am = a.map(pitchToMidi).sort();
    const bm = b.map(pitchToMidi).sort();
    return am.every((v, i) => v === bm[i]);
  }

  function drumSoundForKey(keyPitch) {
    const midi = pitchToMidi(keyPitch);
    let best = DRUM_KIT[0];
    let bd = Infinity;
    for (const d of DRUM_KIT) {
      const dd = Math.abs(pitchToMidi(d.key) - midi);
      if (dd < bd) { bd = dd; best = d; }
    }
    return best.sound;
  }

  function play(score, callbacks) {
    stop();
    ensureContext();
    onTick = callbacks && callbacks.onTick;
    onEnd = callbacks && callbacks.onEnd;

    partGains = score.parts.map((part) => {
      const g = ctx.createGain();
      g.gain.value = part.mute ? 0 : part.volume;
      g.connect(master);
      return g;
    });

    const built = buildSequence(score);
    sequence = built.seq;
    totalDur = built.total;
    const t0 = ctx.currentTime + 0.12;
    startTime = t0;

    for (const n of sequence) {
      const dest = partGains[n.p];
      if (n.kit) {
        for (const k of n.keys) scheduleDrum(dest, drumSoundForKey(k), t0 + n.t, n.vel);
      } else {
        for (const k of n.keys) {
          scheduleTone(dest, n.patch, midiToFreq(pitchToMidi(k)), t0 + n.t, Math.max(0.05, n.dur * 0.96), n.vel);
        }
      }
    }

    playing = true;
    const tick = () => {
      if (!playing) return;
      const now = ctx.currentTime - startTime;
      if (onTick) onTick(now, sequence, totalDur);
      if (now > totalDur + 0.5) {
        stop();
        if (onEnd) onEnd();
        return;
      }
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
  }

  function stop() {
    playing = false;
    if (rafId) cancelAnimationFrame(rafId);
    rafId = 0;
    for (const n of activeNodes) {
      try { n.stop(0); } catch (e) { /* already stopped */ }
    }
    activeNodes = [];
    for (const g of partGains) {
      try { g.disconnect(); } catch (e) { /* detached */ }
    }
    partGains = [];
  }

  function isPlaying() { return playing; }

  /* Short preview when entering notes / tapping piano keys. */
  function preview(instrumentId, pitchOrDrum) {
    ensureContext();
    const inst = getInstrument(instrumentId);
    const g = ctx.createGain();
    g.gain.value = 0.8;
    g.connect(master);
    const t = ctx.currentTime + 0.01;
    if (inst.kit) {
      scheduleDrum(g, pitchOrDrum, t, 0.9);
    } else {
      scheduleTone(g, inst.patch, midiToFreq(pitchToMidi(pitchOrDrum)), t, 0.35, 0.85);
    }
    setTimeout(() => { try { g.disconnect(); } catch (e) {} }, 2500);
  }

  return { play, stop, isPlaying, preview, buildSequence };
})();
