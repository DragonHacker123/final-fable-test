/* ScoreForge — instrument catalog.
 * Every instrument is available to every user, free, no tiers.
 * patch: synth patch key used by playback.js
 * clef:  default clef for new parts
 * oct:   preferred default octave for note entry
 * kit:   true => unpitched percussion part (drum pads instead of piano)
 */
'use strict';

const INSTRUMENT_FAMILIES = [
  {
    family: 'Keyboards',
    items: [
      { id: 'piano',        name: 'Piano',            patch: 'piano',  clef: 'treble', oct: 4 },
      { id: 'bright-piano', name: 'Bright Piano',     patch: 'piano',  clef: 'treble', oct: 4 },
      { id: 'electric-piano', name: 'Electric Piano', patch: 'epiano', clef: 'treble', oct: 4 },
      { id: 'harpsichord',  name: 'Harpsichord',      patch: 'pluck',  clef: 'treble', oct: 4 },
      { id: 'clavinet',     name: 'Clavinet',         patch: 'epiano', clef: 'treble', oct: 4 },
      { id: 'celesta',      name: 'Celesta',          patch: 'bells',  clef: 'treble', oct: 5 },
      { id: 'organ',        name: 'Pipe Organ',       patch: 'organ',  clef: 'treble', oct: 4 },
      { id: 'reed-organ',   name: 'Reed Organ',       patch: 'organ',  clef: 'treble', oct: 4 },
      { id: 'accordion',    name: 'Accordion',        patch: 'organ',  clef: 'treble', oct: 4 },
      { id: 'harmonica',    name: 'Harmonica',        patch: 'reed',   clef: 'treble', oct: 4 },
    ],
  },
  {
    family: 'Strings',
    items: [
      { id: 'violin',       name: 'Violin',           patch: 'strings', clef: 'treble', oct: 4 },
      { id: 'viola',        name: 'Viola',            patch: 'strings', clef: 'alto',   oct: 3 },
      { id: 'cello',        name: 'Cello',            patch: 'strings', clef: 'bass',   oct: 3 },
      { id: 'contrabass',   name: 'Contrabass',       patch: 'strings', clef: 'bass',   oct: 2 },
      { id: 'string-ens',   name: 'String Ensemble',  patch: 'strings', clef: 'treble', oct: 4 },
      { id: 'pizzicato',    name: 'Pizzicato Strings',patch: 'pluck',   clef: 'treble', oct: 4 },
      { id: 'harp',         name: 'Harp',             patch: 'pluck',   clef: 'treble', oct: 4 },
      { id: 'fiddle',       name: 'Fiddle',           patch: 'strings', clef: 'treble', oct: 4 },
    ],
  },
  {
    family: 'Woodwinds',
    items: [
      { id: 'flute',        name: 'Flute',            patch: 'flute', clef: 'treble', oct: 5 },
      { id: 'piccolo',      name: 'Piccolo',          patch: 'flute', clef: 'treble', oct: 5 },
      { id: 'recorder',     name: 'Recorder',         patch: 'flute', clef: 'treble', oct: 5 },
      { id: 'pan-flute',    name: 'Pan Flute',        patch: 'flute', clef: 'treble', oct: 5 },
      { id: 'oboe',         name: 'Oboe',             patch: 'reed',  clef: 'treble', oct: 4 },
      { id: 'english-horn', name: 'English Horn',     patch: 'reed',  clef: 'treble', oct: 4 },
      { id: 'clarinet',     name: 'Clarinet',         patch: 'reed',  clef: 'treble', oct: 4 },
      { id: 'bass-clarinet',name: 'Bass Clarinet',    patch: 'reed',  clef: 'bass',   oct: 3 },
      { id: 'bassoon',      name: 'Bassoon',          patch: 'reed',  clef: 'bass',   oct: 3 },
      { id: 'soprano-sax',  name: 'Soprano Sax',      patch: 'sax',   clef: 'treble', oct: 4 },
      { id: 'alto-sax',     name: 'Alto Sax',         patch: 'sax',   clef: 'treble', oct: 4 },
      { id: 'tenor-sax',    name: 'Tenor Sax',        patch: 'sax',   clef: 'treble', oct: 3 },
      { id: 'baritone-sax', name: 'Baritone Sax',     patch: 'sax',   clef: 'bass',   oct: 3 },
      { id: 'ocarina',      name: 'Ocarina',          patch: 'flute', clef: 'treble', oct: 5 },
    ],
  },
  {
    family: 'Brass',
    items: [
      { id: 'trumpet',      name: 'Trumpet',          patch: 'brass', clef: 'treble', oct: 4 },
      { id: 'cornet',       name: 'Cornet',           patch: 'brass', clef: 'treble', oct: 4 },
      { id: 'flugelhorn',   name: 'Flugelhorn',       patch: 'brass', clef: 'treble', oct: 4 },
      { id: 'french-horn',  name: 'French Horn',      patch: 'brass', clef: 'treble', oct: 3 },
      { id: 'trombone',     name: 'Trombone',         patch: 'brass', clef: 'bass',   oct: 3 },
      { id: 'bass-trombone',name: 'Bass Trombone',    patch: 'brass', clef: 'bass',   oct: 2 },
      { id: 'euphonium',    name: 'Euphonium',        patch: 'brass', clef: 'bass',   oct: 3 },
      { id: 'tuba',         name: 'Tuba',             patch: 'brass', clef: 'bass',   oct: 2 },
      { id: 'brass-ens',    name: 'Brass Section',    patch: 'brass', clef: 'treble', oct: 4 },
    ],
  },
  {
    family: 'Guitars & Plucked',
    items: [
      { id: 'nylon-guitar', name: 'Classical Guitar', patch: 'pluck', clef: 'treble', oct: 3 },
      { id: 'steel-guitar', name: 'Acoustic Guitar',  patch: 'pluck', clef: 'treble', oct: 3 },
      { id: 'electric-guitar', name: 'Electric Guitar', patch: 'epiano', clef: 'treble', oct: 3 },
      { id: 'overdrive-guitar', name: 'Overdriven Guitar', patch: 'lead', clef: 'treble', oct: 3 },
      { id: 'banjo',        name: 'Banjo',            patch: 'pluck', clef: 'treble', oct: 3 },
      { id: 'mandolin',     name: 'Mandolin',         patch: 'pluck', clef: 'treble', oct: 4 },
      { id: 'ukulele',      name: 'Ukulele',          patch: 'pluck', clef: 'treble', oct: 4 },
      { id: 'sitar',        name: 'Sitar',            patch: 'pluck', clef: 'treble', oct: 4 },
      { id: 'koto',         name: 'Koto',             patch: 'pluck', clef: 'treble', oct: 4 },
    ],
  },
  {
    family: 'Bass',
    items: [
      { id: 'acoustic-bass', name: 'Acoustic Bass',   patch: 'bass', clef: 'bass', oct: 2 },
      { id: 'electric-bass', name: 'Electric Bass',   patch: 'bass', clef: 'bass', oct: 2 },
      { id: 'fretless-bass', name: 'Fretless Bass',   patch: 'bass', clef: 'bass', oct: 2 },
      { id: 'slap-bass',     name: 'Slap Bass',       patch: 'bass', clef: 'bass', oct: 2 },
      { id: 'synth-bass',    name: 'Synth Bass',      patch: 'bass', clef: 'bass', oct: 2 },
    ],
  },
  {
    family: 'Voice',
    items: [
      { id: 'soprano', name: 'Soprano',  patch: 'choir', clef: 'treble', oct: 5 },
      { id: 'alto',    name: 'Alto',     patch: 'choir', clef: 'treble', oct: 4 },
      { id: 'tenor',   name: 'Tenor',    patch: 'choir', clef: 'treble', oct: 3 },
      { id: 'bass-voice', name: 'Bass',  patch: 'choir', clef: 'bass',   oct: 3 },
      { id: 'choir',   name: 'Choir Aahs', patch: 'choir', clef: 'treble', oct: 4 },
      { id: 'voice-oohs', name: 'Voice Oohs', patch: 'choir', clef: 'treble', oct: 4 },
    ],
  },
  {
    family: 'Pitched Percussion',
    items: [
      { id: 'xylophone',    name: 'Xylophone',        patch: 'bells', clef: 'treble', oct: 5 },
      { id: 'marimba',      name: 'Marimba',          patch: 'bells', clef: 'treble', oct: 4 },
      { id: 'vibraphone',   name: 'Vibraphone',       patch: 'bells', clef: 'treble', oct: 4 },
      { id: 'glockenspiel', name: 'Glockenspiel',     patch: 'bells', clef: 'treble', oct: 5 },
      { id: 'tubular-bells',name: 'Tubular Bells',    patch: 'bells', clef: 'treble', oct: 4 },
      { id: 'timpani',      name: 'Timpani',          patch: 'timpani', clef: 'bass', oct: 2 },
      { id: 'steel-drums',  name: 'Steel Drums',      patch: 'bells', clef: 'treble', oct: 4 },
      { id: 'kalimba',      name: 'Kalimba',          patch: 'bells', clef: 'treble', oct: 4 },
      { id: 'music-box',    name: 'Music Box',        patch: 'bells', clef: 'treble', oct: 5 },
    ],
  },
  {
    family: 'Synths',
    items: [
      { id: 'synth-lead-square', name: 'Synth Lead (Square)', patch: 'lead', clef: 'treble', oct: 4 },
      { id: 'synth-lead-saw',    name: 'Synth Lead (Saw)',    patch: 'lead', clef: 'treble', oct: 4 },
      { id: 'synth-pad-warm',    name: 'Synth Pad (Warm)',    patch: 'pad',  clef: 'treble', oct: 4 },
      { id: 'synth-pad-halo',    name: 'Synth Pad (Halo)',    patch: 'pad',  clef: 'treble', oct: 4 },
      { id: 'synth-strings',     name: 'Synth Strings',       patch: 'pad',  clef: 'treble', oct: 4 },
      { id: 'synth-brass',       name: 'Synth Brass',         patch: 'lead', clef: 'treble', oct: 4 },
      { id: 'theremin',          name: 'Theremin',            patch: 'flute', clef: 'treble', oct: 5 },
    ],
  },
  {
    family: 'Percussion',
    items: [
      { id: 'drum-set', name: 'Drum Set', patch: 'drums', clef: 'percussion', oct: 4, kit: true },
    ],
  },
];

const INSTRUMENTS = {};
for (const fam of INSTRUMENT_FAMILIES) {
  for (const it of fam.items) {
    it.family = fam.family;
    INSTRUMENTS[it.id] = it;
  }
}

function getInstrument(id) {
  return INSTRUMENTS[id] || INSTRUMENTS.piano;
}

/* Drum kit map for unpitched percussion parts: pad label -> staff position + sound.
 * Positions follow common drum-set notation on a 5-line percussion staff.
 */
const DRUM_KIT = [
  { id: 'kick',       label: 'Kick',       key: { step: 'F', oct: 4, alter: 0 }, sound: 'kick' },
  { id: 'snare',      label: 'Snare',      key: { step: 'C', oct: 5, alter: 0 }, sound: 'snare' },
  { id: 'hihat',      label: 'Hi-Hat',     key: { step: 'G', oct: 5, alter: 0 }, sound: 'hihat' },
  { id: 'hihat-open', label: 'Open Hat',   key: { step: 'A', oct: 5, alter: 0 }, sound: 'hihatOpen' },
  { id: 'tom-hi',     label: 'Hi Tom',     key: { step: 'E', oct: 5, alter: 0 }, sound: 'tomHi' },
  { id: 'tom-mid',    label: 'Mid Tom',    key: { step: 'D', oct: 5, alter: 0 }, sound: 'tomMid' },
  { id: 'tom-lo',     label: 'Low Tom',    key: { step: 'A', oct: 4, alter: 0 }, sound: 'tomLo' },
  { id: 'crash',      label: 'Crash',      key: { step: 'B', oct: 5, alter: 0 }, sound: 'crash' },
  { id: 'ride',       label: 'Ride',       key: { step: 'F', oct: 5, alter: 0 }, sound: 'ride' },
];
