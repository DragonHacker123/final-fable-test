/* ScoreForge — notation rendering with VexFlow.
 * Draws the whole score as one horizontally scrollable system: parts stacked
 * vertically, measures aligned across parts. Returns hit boxes for tap
 * selection and SVG element refs for the playback cursor.
 */
'use strict';

const Renderer = (() => {
  const VF = Vex.Flow;

  const PART_H = 110;
  const TOP_PAD = 28;
  const LEFT_PAD = 8;

  function vexDuration(ev) {
    let d = ev.dur;
    if (ev.dots === 1) d += 'd';
    if (ev.type === 'rest') d += 'r';
    return d;
  }

  function restKeyForClef(clef) {
    switch (clef) {
      case 'bass': return 'd/3';
      case 'alto': return 'c/4';
      default: return 'b/4';
    }
  }

  /* Decide whether a note pitch needs a visible accidental, tracking
   * alterations previously shown in the same measure (standard notation
   * behavior: an accidental lasts for the rest of the measure).
   */
  function neededAccidental(pitch, fifths, measureState) {
    const stateKey = pitch.step + pitch.oct;
    const active = measureState.has(stateKey)
      ? measureState.get(stateKey)
      : keyAlterForStep(fifths, pitch.step);
    if (pitch.alter === active) return null;
    measureState.set(stateKey, pitch.alter);
    if (pitch.alter === 1) return '#';
    if (pitch.alter === -1) return 'b';
    if (pitch.alter === 2) return '##';
    if (pitch.alter === -2) return 'bb';
    return 'n';
  }

  function buildStaveNote(ev, part, score, measureState) {
    if (ev.type === 'rest') {
      return new VF.StaveNote({
        keys: [restKeyForClef(part.clef)],
        duration: vexDuration(ev),
        clef: part.clef,
        auto_stem: true,
      });
    }
    const note = new VF.StaveNote({
      keys: ev.keys.map(pitchToVexKey),
      duration: vexDuration(ev),
      clef: part.clef,
      auto_stem: true,
    });
    if (part.clef !== 'percussion') {
      ev.keys.forEach((k, i) => {
        const acc = neededAccidental(k, score.fifths, measureState);
        if (acc) note.addModifier(new VF.Accidental(acc), i);
      });
    }
    if (ev.dots === 1) VF.Dot.buildAndAttach([note], { all: true });
    if (ev.dynamic) {
      const ann = new VF.Annotation(ev.dynamic)
        .setFont('serif', 12, 'italic bold')
        .setVerticalJustification(VF.Annotation.VerticalJustify.BOTTOM);
      note.addModifier(ann, 0);
    }
    return note;
  }

  function measureContentWidth(score, mIdx) {
    let maxEvents = 1;
    for (const part of score.parts) {
      maxEvents = Math.max(maxEvents, part.measures[mIdx].events.length);
    }
    return Math.min(420, Math.max(96, 40 + maxEvents * 40));
  }

  function firstMeasureModWidth(score) {
    return 34 + 26 + Math.abs(score.fifths) * 11 + 8;
  }

  /* Render into container (a div). selection may be null.
   * Returns { hits, measureRects, noteEls, width, height }.
   */
  function render(score, container, selection) {
    container.innerHTML = '';
    const nParts = score.parts.length;
    const nMeasures = measureCount(score);

    const widths = [];
    let totalW = LEFT_PAD;
    for (let m = 0; m < nMeasures; m++) {
      let w = measureContentWidth(score, m);
      if (m === 0) w += firstMeasureModWidth(score);
      widths.push(w);
      totalW += w;
    }
    totalW += 20;
    const totalH = TOP_PAD + nParts * PART_H + 16;

    const renderer = new VF.Renderer(container, VF.Renderer.Backends.SVG);
    renderer.resize(totalW, totalH);
    const ctx = renderer.getContext();

    const hits = [];
    const measureRects = [];
    const noteEls = {};

    // staves indexed [part][measure] so connectors can be drawn afterwards
    const staves = [];
    for (let p = 0; p < nParts; p++) staves.push([]);

    let x = LEFT_PAD;
    for (let m = 0; m < nMeasures; m++) {
      const w = widths[m];
      const voices = [];
      const drawJobs = [];

      for (let p = 0; p < nParts; p++) {
        const part = score.parts[p];
        const y = TOP_PAD + p * PART_H;
        const stave = new VF.Stave(x, y, w);
        if (m === 0) {
          stave.addClef(part.clef);
          if (part.clef !== 'percussion') stave.addKeySignature(keySigVexName(score.fifths));
          stave.addTimeSignature(score.timeSig.num + '/' + score.timeSig.den);
        }
        if (m === nMeasures - 1) stave.setEndBarType(VF.Barline.type.END);
        stave.setContext(ctx).draw();
        staves[p].push(stave);

        const measure = part.measures[m];
        const measureState = new Map();
        const notes = measure.events.map((ev) => buildStaveNote(ev, part, score, measureState));

        // selection highlight
        if (selection && selection.p === p && selection.m === m && notes[selection.e]) {
          notes[selection.e].setStyle({ fillStyle: '#2563eb', strokeStyle: '#2563eb' });
        }

        const voice = new VF.Voice({ num_beats: score.timeSig.num, beat_value: score.timeSig.den });
        voice.setMode(VF.Voice.Mode.SOFT);
        voice.addTickables(notes);
        voices.push(voice);
        drawJobs.push({ voice, stave, notes, p, m, part, measure });

        measureRects.push({ p, m, x, y: y - 14, w, h: PART_H });
      }

      const fmtWidth = w - (m === 0 ? firstMeasureModWidth(score) : 0) - 18;
      const formatter = new VF.Formatter();
      for (const v of voices) formatter.joinVoices([v]);
      formatter.format(voices, Math.max(30, fmtWidth));

      for (const job of drawJobs) {
        job.voice.draw(ctx, job.stave);
        const beams = VF.Beam.generateBeams(job.notes.filter((n) => !n.isRest()));
        beams.forEach((b) => b.setContext(ctx).draw());

        // same-measure and hanging cross-measure ties
        job.measure.events.forEach((ev, e) => {
          if (ev.type !== 'note' || !ev.tie) return;
          const first = job.notes[e];
          const indices = ev.keys.map((_, i) => i);
          if (e + 1 < job.notes.length && job.measure.events[e + 1].type === 'note') {
            const nextIdx = job.measure.events[e + 1].keys.map((_, i) => i)
              .slice(0, indices.length);
            new VF.StaveTie({
              first_note: first, last_note: job.notes[e + 1],
              first_indices: indices, last_indices: nextIdx.length ? nextIdx : [0],
            }).setContext(ctx).draw();
          } else {
            new VF.StaveTie({
              first_note: first, last_note: null,
              first_indices: indices, last_indices: indices,
            }).setContext(ctx).draw();
          }
        });

        // hit boxes + svg refs
        job.notes.forEach((n, e) => {
          try {
            const bb = n.getBoundingBox();
            hits.push({ p: job.p, m: job.m, e, x: bb.x, y: bb.y, w: bb.w, h: bb.h });
          } catch (err) { /* keep rendering */ }
          const el = n.getSVGElement ? n.getSVGElement() : null;
          if (el) noteEls[job.p + ':' + job.m + ':' + e] = el;
        });
      }

      // measure number above the top part
      if (m % 2 === 0) {
        ctx.save();
        ctx.setFont('sans-serif', 9, '');
        ctx.setFillStyle('#94a3b8');
        ctx.fillText(String(m + 1), x + 4, TOP_PAD - 4);
        ctx.restore();
      }

      x += w;
    }

    // system-left connector + bracket for multiple parts
    if (nParts > 1) {
      const conn = new VF.StaveConnector(staves[0][0], staves[nParts - 1][0]);
      conn.setType(VF.StaveConnector.type.SINGLE_LEFT).setContext(ctx).draw();
    }

    // part names
    ctx.save();
    ctx.setFont('sans-serif', 10, '');
    ctx.setFillStyle('#64748b');
    for (let p = 0; p < nParts; p++) {
      ctx.fillText(score.parts[p].name, LEFT_PAD + 4, TOP_PAD + p * PART_H - 2);
    }
    ctx.restore();

    return { hits, measureRects, noteEls, width: totalW, height: totalH };
  }

  /* Map a tap at SVG coordinates to a selection, using note hit boxes first,
   * then falling back to the tapped measure's nearest event by x.
   */
  function hitTest(layout, px, py) {
    const PAD = 10;
    let best = null;
    let bestDist = Infinity;
    for (const h of layout.hits) {
      if (px >= h.x - PAD && px <= h.x + h.w + PAD && py >= h.y - PAD && py <= h.y + h.h + PAD) {
        const cx = h.x + h.w / 2;
        const cy = h.y + h.h / 2;
        const d = (px - cx) * (px - cx) + (py - cy) * (py - cy);
        if (d < bestDist) { bestDist = d; best = { p: h.p, m: h.m, e: h.e }; }
      }
    }
    if (best) return best;
    for (const r of layout.measureRects) {
      if (px >= r.x && px <= r.x + r.w && py >= r.y && py <= r.y + r.h) {
        let nearest = null;
        let nd = Infinity;
        for (const h of layout.hits) {
          if (h.p !== r.p || h.m !== r.m) continue;
          const d = Math.abs(px - (h.x + h.w / 2));
          if (d < nd) { nd = d; nearest = { p: h.p, m: h.m, e: h.e }; }
        }
        if (nearest) return nearest;
        return { p: r.p, m: r.m, e: 0 };
      }
    }
    return null;
  }

  return { render, hitTest, PART_H, TOP_PAD };
})();
