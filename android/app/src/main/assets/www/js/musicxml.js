/* ScoreForge — MusicXML export and best-effort import.
 * Exported files open in MuseScore, Flat, Sibelius, Finale, etc.
 * Import reads uncompressed .musicxml / .xml (score-partwise), first voice of
 * each part, mapping to our single-voice model.
 */
'use strict';

const MusicXML = (() => {
  const DIVISIONS = 480; // matches TICKS_PER_QUARTER

  const TYPE_FOR_DUR = { w: 'whole', h: 'half', q: 'quarter', '8': 'eighth', '16': '16th', '32': '32nd' };
  const DUR_FOR_TYPE = { whole: 'w', half: 'h', quarter: 'q', eighth: '8', '16th': '16', '32nd': '32', '64th': '32' };

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function clefXml(clef) {
    switch (clef) {
      case 'bass': return '<clef><sign>F</sign><line>4</line></clef>';
      case 'alto': return '<clef><sign>C</sign><line>3</line></clef>';
      case 'percussion': return '<clef><sign>percussion</sign></clef>';
      default: return '<clef><sign>G</sign><line>2</line></clef>';
    }
  }

  function exportScore(score) {
    const lines = [];
    lines.push('<?xml version="1.0" encoding="UTF-8"?>');
    lines.push('<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">');
    lines.push('<score-partwise version="4.0">');
    lines.push('<work><work-title>' + esc(score.title) + '</work-title></work>');
    lines.push('<identification><creator type="composer">' + esc(score.composer) + '</creator>');
    lines.push('<encoding><software>ScoreForge</software></encoding></identification>');
    lines.push('<part-list>');
    score.parts.forEach((part, i) => {
      lines.push('<score-part id="P' + (i + 1) + '"><part-name>' + esc(part.name) + '</part-name></score-part>');
    });
    lines.push('</part-list>');

    score.parts.forEach((part, pi) => {
      lines.push('<part id="P' + (pi + 1) + '">');
      part.measures.forEach((measure, mi) => {
        lines.push('<measure number="' + (mi + 1) + '">');
        if (mi === 0) {
          lines.push('<attributes>');
          lines.push('<divisions>' + DIVISIONS + '</divisions>');
          lines.push('<key><fifths>' + score.fifths + '</fifths></key>');
          lines.push('<time><beats>' + score.timeSig.num + '</beats><beat-type>' + score.timeSig.den + '</beat-type></time>');
          lines.push(clefXml(part.clef));
          lines.push('</attributes>');
          if (pi === 0) {
            lines.push('<direction placement="above"><direction-type><metronome>' +
              '<beat-unit>quarter</beat-unit><per-minute>' + score.tempo + '</per-minute>' +
              '</metronome></direction-type><sound tempo="' + score.tempo + '"/></direction>');
          }
        }
        measure.events.forEach((ev) => {
          const ticks = eventTicks(ev);
          if (ev.type === 'rest') {
            lines.push('<note><rest/><duration>' + ticks + '</duration>' +
              '<type>' + TYPE_FOR_DUR[ev.dur] + '</type>' + (ev.dots === 1 ? '<dot/>' : '') + '</note>');
          } else {
            ev.keys.forEach((k, ki) => {
              const alterXml = k.alter ? '<alter>' + k.alter + '</alter>' : '';
              lines.push('<note>' + (ki > 0 ? '<chord/>' : '') +
                '<pitch><step>' + k.step + '</step>' + alterXml + '<octave>' + k.oct + '</octave></pitch>' +
                '<duration>' + ticks + '</duration>' +
                (ev.tie ? '<tie type="start"/>' : '') +
                '<type>' + TYPE_FOR_DUR[ev.dur] + '</type>' +
                (ev.dots === 1 ? '<dot/>' : '') +
                (ev.tie || ev.dynamic ? '<notations>' +
                  (ev.tie ? '<tied type="start"/>' : '') +
                  (ki === 0 && ev.dynamic ? '<dynamics><' + ev.dynamic + '/></dynamics>' : '') +
                  '</notations>' : '') +
                '</note>');
            });
          }
        });
        lines.push('</measure>');
      });
      lines.push('</part>');
    });
    lines.push('</score-partwise>');
    return lines.join('\n');
  }

  /* ------- import ------- */

  function text(el, sel) {
    const c = el.querySelector(sel);
    return c ? c.textContent.trim() : null;
  }

  function guessInstrument(name) {
    const n = (name || '').toLowerCase();
    for (const id of Object.keys(INSTRUMENTS)) {
      if (n.includes(INSTRUMENTS[id].name.toLowerCase())) return id;
    }
    if (n.includes('piano')) return 'piano';
    if (n.includes('drum')) return 'drum-set';
    if (n.includes('guitar')) return 'steel-guitar';
    if (n.includes('violin')) return 'violin';
    if (n.includes('flute')) return 'flute';
    if (n.includes('trumpet')) return 'trumpet';
    if (n.includes('sax')) return 'alto-sax';
    if (n.includes('bass')) return 'electric-bass';
    if (n.includes('cello')) return 'cello';
    if (n.includes('voice') || n.includes('vocal')) return 'choir';
    return 'piano';
  }

  /* Convert a MusicXML duration (in the file's divisions) to the closest
   * {dur, dots} we support; returns null when nothing reasonable matches.
   */
  function durationFor(divs, fileDivisions, typeEl, dotted) {
    if (typeEl && DUR_FOR_TYPE[typeEl]) {
      return { dur: DUR_FOR_TYPE[typeEl], dots: dotted ? 1 : 0 };
    }
    const ticks = Math.round(divs * TICKS_PER_QUARTER / fileDivisions);
    let best = null;
    let bd = Infinity;
    for (const d of DUR_ORDER) {
      for (const dots of [0, 1]) {
        const t = durWithDotsTicks(d, dots);
        const diff = Math.abs(t - ticks);
        if (diff < bd) { bd = diff; best = { dur: d, dots }; }
      }
    }
    return best;
  }

  function importScore(xmlText) {
    const doc = new DOMParser().parseFromString(xmlText, 'application/xml');
    if (doc.querySelector('parsererror')) throw new Error('Not a valid MusicXML file');
    const root = doc.querySelector('score-partwise');
    if (!root) throw new Error('Only score-partwise MusicXML is supported');

    const score = newScore(text(root, 'work-title') || 'Imported score', []);
    score.parts = [];
    score.composer = text(root, 'identification creator[type="composer"]') || '';

    const partNames = {};
    root.querySelectorAll('part-list score-part').forEach((sp) => {
      partNames[sp.getAttribute('id')] = text(sp, 'part-name') || 'Part';
    });

    let fileDivisions = 1;
    let firstAttrsDone = false;

    root.querySelectorAll(':scope > part').forEach((partEl) => {
      const pname = partNames[partEl.getAttribute('id')] || 'Part';
      const instId = guessInstrument(pname);
      const part = newPart(instId, score.timeSig, 0);
      part.name = pname;

      partEl.querySelectorAll(':scope > measure').forEach((mEl) => {
        const divEl = text(mEl, 'attributes divisions');
        if (divEl) fileDivisions = parseInt(divEl, 10) || fileDivisions;
        if (!firstAttrsDone) {
          const fifths = text(mEl, 'attributes key fifths');
          if (fifths != null) score.fifths = Math.max(-6, Math.min(6, parseInt(fifths, 10) || 0));
          const beats = text(mEl, 'attributes time beats');
          const beatType = text(mEl, 'attributes time beat-type');
          if (beats && beatType) score.timeSig = { num: parseInt(beats, 10) || 4, den: parseInt(beatType, 10) || 4 };
          const tempo = mEl.querySelector('sound[tempo]');
          if (tempo) score.tempo = Math.round(parseFloat(tempo.getAttribute('tempo'))) || score.tempo;
          const sign = text(mEl, 'attributes clef sign');
          if (sign === 'F') part.clef = 'bass';
          else if (sign === 'C') part.clef = 'alto';
          else if (sign === 'percussion') part.clef = 'percussion';
          firstAttrsDone = true;
        } else {
          const sign = text(mEl, 'attributes clef sign');
          if (sign === 'F' && part.measures.length === 0) part.clef = 'bass';
        }

        const events = [];
        let lastNote = null;
        mEl.querySelectorAll(':scope > note').forEach((nEl) => {
          // skip extra voices/staves to keep the single-voice model
          const voice = text(nEl, 'voice');
          if (voice && voice !== '1') return;
          const staff = text(nEl, 'staff');
          if (staff && staff !== '1') return;

          const isChord = !!nEl.querySelector(':scope > chord');
          const durDivs = parseFloat(text(nEl, 'duration') || '0');
          const typeName = text(nEl, 'type');
          const dotted = !!nEl.querySelector(':scope > dot');
          const dd = durationFor(durDivs, fileDivisions, typeName, dotted);
          if (!dd) return;

          if (nEl.querySelector(':scope > rest')) {
            events.push(makeRest(dd.dur, dd.dots));
            lastNote = null;
            return;
          }
          const step = text(nEl, 'pitch step');
          const octave = text(nEl, 'pitch octave');
          if (!step || octave == null) {
            // unpitched (drums): map to a mid-staff hit
            const pitch = { step: 'C', oct: 5, alter: 0 };
            if (isChord && lastNote) { lastNote.keys.push(pitch); return; }
            lastNote = { type: 'note', dur: dd.dur, dots: dd.dots, keys: [pitch] };
            events.push(lastNote);
            return;
          }
          const pitch = {
            step,
            oct: parseInt(octave, 10),
            alter: parseInt(text(nEl, 'pitch alter') || '0', 10) || 0,
          };
          if (isChord && lastNote) {
            lastNote.keys.push(pitch);
            return;
          }
          const note = { type: 'note', dur: dd.dur, dots: dd.dots, keys: [pitch] };
          if (nEl.querySelector('tie[type="start"], tied[type="start"]')) note.tie = true;
          const dynEl = nEl.querySelector('notations dynamics');
          if (dynEl && dynEl.firstElementChild) {
            const d = dynEl.firstElementChild.tagName.toLowerCase();
            if (['pp', 'p', 'mp', 'mf', 'f', 'ff'].includes(d)) note.dynamic = d;
          }
          events.push(note);
          lastNote = note;
        });
        part.measures.push({ events });
      });
      score.parts.push(part);
    });

    if (!score.parts.length) throw new Error('No parts found in file');

    // normalize: make every measure exactly full and counts equal
    const cap = measureCapacity(score.timeSig);
    const maxM = Math.max(...score.parts.map((p) => p.measures.length), 1);
    for (const part of score.parts) {
      while (part.measures.length < maxM) part.measures.push(makeEmptyMeasure(score.timeSig));
      for (const m of part.measures) {
        let used = 0;
        const kept = [];
        for (const ev of m.events) {
          const t = eventTicks(ev);
          if (used + t > cap) break;
          kept.push(ev);
          used += t;
        }
        for (const r of makeRestsForTicks(cap - used)) kept.push(r);
        m.events = kept;
      }
    }
    score.id = uid();
    score.createdAt = Date.now();
    return score;
  }

  return { exportScore, importScore };
})();
