/* ScoreForge — score data model and editing operations.
 *
 * Invariant: every measure of every part is always exactly "full" — the sum of
 * its event ticks equals the measure capacity for the score's time signature.
 * Empty space is represented by rests, so note entry replaces rests/notes at
 * the cursor rather than shifting later music around.
 *
 * Durations use ticks with quarter note = 480.
 */
'use strict';

const TICKS_PER_QUARTER = 480;

const DUR_TICKS = { w: 1920, h: 960, q: 480, '8': 240, '16': 120, '32': 60 };
const DUR_ORDER = ['w', 'h', 'q', '8', '16', '32'];

function eventTicks(ev) {
  let t = DUR_TICKS[ev.dur];
  if (ev.dots === 1) t = t * 1.5;
  else if (ev.dots === 2) t = t * 1.75;
  return t;
}

function durWithDotsTicks(dur, dots) {
  return eventTicks({ dur, dots });
}

function measureCapacity(timeSig) {
  return timeSig.num * (4 * TICKS_PER_QUARTER) / timeSig.den;
}

/* Decompose a tick count into a sequence of {dur, dots} greedy from long to
 * short. Used for rest padding and for splitting notes at measure boundaries.
 * Falls back to dropping a remainder smaller than a 32nd (cannot occur with
 * our duration set, but keeps the loop total).
 */
function decomposeTicks(ticks) {
  const out = [];
  let left = ticks;
  while (left >= DUR_TICKS['32']) {
    let placed = false;
    for (const d of DUR_ORDER) {
      const base = DUR_TICKS[d];
      if (base * 1.5 <= left && base * 1.5 !== base && Number.isInteger(base * 1.5)) {
        // Prefer a dotted value only when it fits exactly or leads the greedy fill.
        if (base <= left && base * 1.5 <= left && (left === base * 1.5)) {
          out.push({ dur: d, dots: 1 });
          left -= base * 1.5;
          placed = true;
          break;
        }
      }
      if (base <= left) {
        out.push({ dur: d, dots: 0 });
        left -= base;
        placed = true;
        break;
      }
    }
    if (!placed) break;
  }
  return out;
}

function makeRest(dur, dots) {
  return { type: 'rest', dur, dots: dots || 0 };
}

function makeRestsForTicks(ticks) {
  return decomposeTicks(ticks).map((d) => makeRest(d.dur, d.dots));
}

function makeEmptyMeasure(timeSig) {
  return { events: makeRestsForTicks(measureCapacity(timeSig)) };
}

function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

/* ---------------- key signatures ---------------- */

const KEY_SIGS = [
  { fifths: 0,  name: 'C major / A minor',   vex: 'C' },
  { fifths: 1,  name: 'G major / E minor',   vex: 'G' },
  { fifths: 2,  name: 'D major / B minor',   vex: 'D' },
  { fifths: 3,  name: 'A major / F# minor',  vex: 'A' },
  { fifths: 4,  name: 'E major / C# minor',  vex: 'E' },
  { fifths: 5,  name: 'B major / G# minor',  vex: 'B' },
  { fifths: 6,  name: 'F# major / D# minor', vex: 'F#' },
  { fifths: -1, name: 'F major / D minor',   vex: 'F' },
  { fifths: -2, name: 'Bb major / G minor',  vex: 'Bb' },
  { fifths: -3, name: 'Eb major / C minor',  vex: 'Eb' },
  { fifths: -4, name: 'Ab major / F minor',  vex: 'Ab' },
  { fifths: -5, name: 'Db major / Bb minor', vex: 'Db' },
  { fifths: -6, name: 'Gb major / Eb minor', vex: 'Gb' },
];

const SHARP_ORDER = ['F', 'C', 'G', 'D', 'A', 'E', 'B'];
const FLAT_ORDER = ['B', 'E', 'A', 'D', 'G', 'C', 'F'];

function keySigVexName(fifths) {
  const k = KEY_SIGS.find((k) => k.fifths === fifths);
  return k ? k.vex : 'C';
}

/* Default alteration for a step under a key signature: 1, 0 or -1. */
function keyAlterForStep(fifths, step) {
  if (fifths > 0) return SHARP_ORDER.slice(0, fifths).includes(step) ? 1 : 0;
  if (fifths < 0) return FLAT_ORDER.slice(0, -fifths).includes(step) ? -1 : 0;
  return 0;
}

/* ---------------- pitch helpers ---------------- */

const STEP_SEMITONES = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
const STEPS = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];

function pitchToMidi(p) {
  return 12 * (p.oct + 1) + STEP_SEMITONES[p.step] + p.alter;
}

/* Spell a MIDI note as step/alter/oct, respecting the key signature where
 * possible, otherwise preferring sharps in sharp keys and flats in flat keys.
 */
function midiToPitch(midi, fifths) {
  const pc = ((midi % 12) + 12) % 12;
  const octRaw = Math.floor(midi / 12) - 1;
  // candidate spellings for each pitch class: [step, alter]
  const CAND = {
    0: [['C', 0], ['B', 1]],
    1: [['C', 1], ['D', -1]],
    2: [['D', 0]],
    3: [['D', 1], ['E', -1]],
    4: [['E', 0], ['F', -1]],
    5: [['F', 0], ['E', 1]],
    6: [['F', 1], ['G', -1]],
    7: [['G', 0]],
    8: [['G', 1], ['A', -1]],
    9: [['A', 0]],
    10: [['A', 1], ['B', -1]],
    11: [['B', 0], ['C', -1]],
  }[pc];
  let best = CAND[0];
  // prefer a spelling that matches the key signature exactly
  for (const c of CAND) {
    if (keyAlterForStep(fifths, c[0]) === c[1]) { best = c; break; }
  }
  if (best === CAND[0] && CAND.length > 1 && keyAlterForStep(fifths, CAND[0][0]) !== CAND[0][1]) {
    // no natural/key match: sharp keys prefer sharps, flat keys prefer flats
    if (fifths < 0) {
      const flat = CAND.find((c) => c[1] === -1);
      if (flat) best = flat;
    } else {
      const sharp = CAND.find((c) => c[1] === 1);
      if (sharp) best = sharp;
    }
  }
  const [step, alter] = best;
  // octave correction for B#/Cb wrapping
  let oct = octRaw;
  if (step === 'B' && alter === 1) oct -= 1;
  if (step === 'C' && alter === -1) oct += 1;
  return { step, oct, alter };
}

function pitchToVexKey(p) {
  const acc = p.alter === 1 ? '#' : p.alter === -1 ? 'b' : p.alter === 2 ? '##' : p.alter === -2 ? 'bb' : '';
  return p.step.toLowerCase() + acc + '/' + p.oct;
}

/* Diatonic step up/down within the current key signature. */
function stepPitch(p, dir, fifths) {
  let idx = STEPS.indexOf(p.step) + dir;
  let oct = p.oct;
  if (idx < 0) { idx += 7; oct -= 1; }
  if (idx > 6) { idx -= 7; oct += 1; }
  const step = STEPS[idx];
  return { step, oct, alter: keyAlterForStep(fifths, step) };
}

/* ---------------- score construction ---------------- */

const DEFAULT_MEASURES = 8;

function newPart(instrumentId, timeSig, measureCount) {
  const inst = getInstrument(instrumentId);
  const measures = [];
  for (let i = 0; i < measureCount; i++) measures.push(makeEmptyMeasure(timeSig));
  return {
    id: uid(),
    instrumentId,
    name: inst.name,
    clef: inst.clef,
    volume: 0.8,
    mute: false,
    measures,
  };
}

function newScore(title, instrumentIds) {
  const timeSig = { num: 4, den: 4 };
  const score = {
    id: uid(),
    title: title || 'Untitled score',
    composer: '',
    tempo: 120,
    timeSig,
    fifths: 0,
    createdAt: Date.now(),
    updatedAt: Date.now(),
    parts: [],
  };
  for (const iid of (instrumentIds && instrumentIds.length ? instrumentIds : ['piano'])) {
    score.parts.push(newPart(iid, timeSig, DEFAULT_MEASURES));
  }
  return score;
}

/* ---------------- editing operations ----------------
 * All operations mutate the score in place. app.js wraps them in
 * Editor.mutate() which handles undo snapshots + persistence + re-render.
 */

function measureCount(score) {
  return score.parts.length ? score.parts[0].measures.length : 0;
}

function addMeasures(score, n) {
  for (const part of score.parts) {
    for (let i = 0; i < n; i++) part.measures.push(makeEmptyMeasure(score.timeSig));
  }
}

function removeMeasure(score, mIdx) {
  if (measureCount(score) <= 1) return false;
  for (const part of score.parts) part.measures.splice(mIdx, 1);
  return true;
}

function addPart(score, instrumentId) {
  score.parts.push(newPart(instrumentId, score.timeSig, measureCount(score) || DEFAULT_MEASURES));
}

function removePart(score, pIdx) {
  if (score.parts.length <= 1) return false;
  score.parts.splice(pIdx, 1);
  return true;
}

/* Tick offset of event eIdx within its measure. */
function eventOffset(measure, eIdx) {
  let t = 0;
  for (let i = 0; i < eIdx; i++) t += eventTicks(measure.events[i]);
  return t;
}

/* Replace the region starting at event eIdx with a new event (note or rest) of
 * `ticks` ticks. Consumes following events as needed; if a consumed event
 * extends past the region, the overhang is refilled with rests. If `ticks`
 * exceeds the space remaining in the measure, the inserted note is split into
 * tied notes that fill the remaining space (no spill into the next measure).
 * Returns the index of the (first) inserted event, or -1.
 */
function replaceAt(score, part, mIdx, eIdx, ticks, makeEvent) {
  const measure = part.measures[mIdx];
  const cap = measureCapacity(score.timeSig);
  const start = eventOffset(measure, eIdx);
  const remaining = cap - start;
  if (remaining <= 0) return -1;
  const useTicks = Math.min(ticks, remaining);

  // consume events covering [start, start+useTicks)
  let consumed = 0;
  let count = 0;
  while (consumed < useTicks && eIdx + count < measure.events.length) {
    consumed += eventTicks(measure.events[eIdx + count]);
    count += 1;
  }
  const overhang = consumed - useTicks;

  const pieces = decomposeTicks(useTicks);
  const inserted = [];
  for (let i = 0; i < pieces.length; i++) {
    const ev = makeEvent(pieces[i]);
    if (ev.type === 'note' && i < pieces.length - 1) ev.tie = true;
    inserted.push(ev);
  }
  for (const r of makeRestsForTicks(overhang)) inserted.push(r);

  measure.events.splice(eIdx, count, ...inserted);
  return eIdx;
}

/* Insert a note with the given pitch at the cursor. Returns new event index. */
function insertNote(score, sel, pitch, dur, dots) {
  const part = score.parts[sel.p];
  const ticks = durWithDotsTicks(dur, dots);
  return replaceAt(score, part, sel.m, sel.e, ticks, (piece) => ({
    type: 'note',
    dur: piece.dur,
    dots: piece.dots,
    keys: [Object.assign({}, pitch)],
  }));
}

/* Insert a rest of the toolbar duration at the cursor. */
function insertRest(score, sel, dur, dots) {
  const part = score.parts[sel.p];
  const ticks = durWithDotsTicks(dur, dots);
  return replaceAt(score, part, sel.m, sel.e, ticks, (piece) => makeRest(piece.dur, piece.dots));
}

/* Turn the selected note back into rests. */
function deleteEvent(score, sel) {
  const part = score.parts[sel.p];
  const measure = part.measures[sel.m];
  const ev = measure.events[sel.e];
  if (!ev) return;
  const ticks = eventTicks(ev);
  measure.events.splice(sel.e, 1, ...makeRestsForTicks(ticks));
}

/* Add a pitch to the selected note (chord entry), or remove it if present. */
function toggleChordPitch(score, sel, pitch) {
  const ev = getEvent(score, sel);
  if (!ev || ev.type !== 'note') return false;
  const midi = pitchToMidi(pitch);
  const existing = ev.keys.findIndex((k) => pitchToMidi(k) === midi);
  if (existing >= 0) {
    if (ev.keys.length > 1) ev.keys.splice(existing, 1);
  } else {
    ev.keys.push(Object.assign({}, pitch));
    ev.keys.sort((a, b) => pitchToMidi(a) - pitchToMidi(b));
  }
  return true;
}

function getEvent(score, sel) {
  const part = score.parts[sel.p];
  if (!part) return null;
  const measure = part.measures[sel.m];
  if (!measure) return null;
  return measure.events[sel.e] || null;
}

/* Change the duration of the selected event in place (re-padding around it). */
function setEventDuration(score, sel, dur, dots) {
  const ev = getEvent(score, sel);
  if (!ev) return;
  const part = score.parts[sel.p];
  const ticks = durWithDotsTicks(dur, dots);
  if (ev.type === 'note') {
    const keys = ev.keys.map((k) => Object.assign({}, k));
    const dyn = ev.dynamic;
    const idx = replaceAt(score, part, sel.m, sel.e, ticks, (piece) => ({
      type: 'note', dur: piece.dur, dots: piece.dots,
      keys: keys.map((k) => Object.assign({}, k)),
    }));
    const nev = part.measures[sel.m].events[idx];
    if (nev && dyn) nev.dynamic = dyn;
  } else {
    replaceAt(score, part, sel.m, sel.e, ticks, (piece) => makeRest(piece.dur, piece.dots));
  }
}

/* Move all pitches of the selected note by a diatonic step (dir = +1/-1). */
function transposeEvent(score, sel, dir) {
  const ev = getEvent(score, sel);
  if (!ev || ev.type !== 'note') return;
  ev.keys = ev.keys.map((k) => stepPitch(k, dir, score.fifths));
}

/* Apply an accidental (alter value) to all pitches of the selected note.
 * alter: 1 sharp, -1 flat, 0 natural. Applying the same alter twice resets to
 * the key-signature default.
 */
function applyAccidental(score, sel, alter) {
  const ev = getEvent(score, sel);
  if (!ev || ev.type !== 'note') return;
  for (const k of ev.keys) {
    k.alter = (k.alter === alter) ? keyAlterForStep(score.fifths, k.step) : alter;
  }
}

function toggleTie(score, sel) {
  const ev = getEvent(score, sel);
  if (!ev || ev.type !== 'note') return;
  ev.tie = !ev.tie;
}

function setDynamic(score, sel, dyn) {
  const ev = getEvent(score, sel);
  if (!ev || ev.type !== 'note') return;
  ev.dynamic = (ev.dynamic === dyn) ? undefined : dyn;
}

/* Change the score's time signature and reflow every part's events into new
 * measure boundaries. Whole events are kept; an event that does not fit in the
 * remainder of a measure moves to the next one (the gap is filled with rests).
 */
function setTimeSignature(score, num, den) {
  score.timeSig = { num, den };
  const cap = measureCapacity(score.timeSig);
  for (const part of score.parts) {
    const stream = [];
    for (const m of part.measures) {
      for (const ev of m.events) {
        // drop padding rests; they get regenerated
        stream.push(ev);
      }
    }
    // remove trailing rests so we do not create empty tail measures beyond need
    const notes = stream.filter((e) => e.type === 'note');
    const measures = [];
    let cur = { events: [] };
    let used = 0;
    for (const ev of stream) {
      let t = eventTicks(ev);
      if (ev.type === 'rest' && used + t > cap) {
        // shrink boundary-crossing rests to fit
        const fit = cap - used;
        for (const r of makeRestsForTicks(fit)) { cur.events.push(r); }
        used = cap;
      } else if (used + t > cap) {
        // note does not fit: pad measure, push note to next
        for (const r of makeRestsForTicks(cap - used)) cur.events.push(r);
        measures.push(cur);
        cur = { events: [] };
        used = 0;
        if (t > cap) { // clamp very long notes to one measure
          const pieces = decomposeTicks(cap);
          pieces.forEach((piece, i) => {
            const n = { type: 'note', dur: piece.dur, dots: piece.dots, keys: ev.keys.map((k) => Object.assign({}, k)) };
            if (i < pieces.length - 1) n.tie = true;
            cur.events.push(n);
          });
          used = cap;
          continue;
        }
        cur.events.push(ev);
        used += t;
      } else {
        cur.events.push(ev);
        used += t;
      }
      if (used === cap) {
        measures.push(cur);
        cur = { events: [] };
        used = 0;
      }
    }
    if (used > 0) {
      for (const r of makeRestsForTicks(cap - used)) cur.events.push(r);
      measures.push(cur);
    }
    if (measures.length === 0) measures.push(makeEmptyMeasure(score.timeSig));
    part.measures = measures;
    void notes;
  }
  // equalize measure counts across parts
  const maxM = Math.max(...score.parts.map((p) => p.measures.length));
  for (const part of score.parts) {
    while (part.measures.length < maxM) part.measures.push(makeEmptyMeasure(score.timeSig));
  }
}

/* Move the cursor one event forward/back across measure boundaries.
 * Returns a new selection object (or the same one at the edges).
 */
function moveSelection(score, sel, dir) {
  const part = score.parts[sel.p];
  if (!part) return sel;
  let { m, e } = sel;
  e += dir;
  while (true) {
    const measure = part.measures[m];
    if (!measure) break;
    if (e < 0) {
      if (m === 0) { e = 0; break; }
      m -= 1;
      e = part.measures[m].events.length - 1;
    } else if (e >= measure.events.length) {
      if (m === part.measures.length - 1) { e = measure.events.length - 1; break; }
      m += 1;
      e = 0;
    } else break;
  }
  return { p: sel.p, m, e };
}
