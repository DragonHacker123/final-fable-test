/* ScoreForge — UI controller: library screen, editor screen, dialogs. */
'use strict';

(() => {
  const $ = (id) => document.getElementById(id);

  /* ---------------- state ---------------- */
  const Editor = {
    score: null,
    sel: { p: 0, m: 0, e: 0 },
    dur: 'q',
    dots: 0,
    chordMode: false,
    octShift: 0, // shifts the piano keyboard
    layout: null,
    undoStack: [],
    redoStack: [],
    saveTimer: 0,
  };

  /* ---------------- helpers ---------------- */

  function toast(msg) {
    const el = $('toast');
    el.textContent = msg;
    el.classList.remove('hidden');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.add('hidden'), 2200);
  }

  function openSheet(html) {
    $('sheet').innerHTML = html;
    $('overlay').classList.remove('hidden');
  }

  function closeSheet() {
    $('overlay').classList.add('hidden');
    $('sheet').innerHTML = '';
  }

  $('overlay').addEventListener('click', (ev) => {
    if (ev.target === $('overlay')) closeSheet();
  });

  function fmtDate(ts) {
    const d = new Date(ts);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  }

  /* ---------------- library screen ---------------- */

  function showLibrary() {
    Playback.stop();
    updatePlayButton(false);
    if (Editor.score) persistNow();
    Editor.score = null;
    $('screen-editor').classList.add('hidden');
    $('screen-library').classList.remove('hidden');
    renderLibrary();
  }

  function renderLibrary() {
    const list = $('score-list');
    const scores = Storage.listScores();
    if (!scores.length) {
      list.innerHTML = '<div class="empty-lib">No scores yet.<br>Tap <b>+</b> to start composing &mdash; unlimited scores, every instrument, all free.</div>';
      return;
    }
    list.innerHTML = '';
    for (const meta of scores) {
      const card = document.createElement('div');
      card.className = 'score-card';
      const parts = (meta.parts || []).slice(0, 3).join(', ') + ((meta.parts || []).length > 3 ? '…' : '');
      card.innerHTML =
        '<div class="meta"><div class="title"></div><div class="sub"></div></div>' +
        '<button class="more" title="Score options">&#8942;</button>';
      card.querySelector('.title').textContent = meta.title || 'Untitled';
      card.querySelector('.sub').textContent = parts + ' · ' + fmtDate(meta.updatedAt);
      card.querySelector('.meta').addEventListener('click', () => openScore(meta.id));
      card.querySelector('.more').addEventListener('click', () => scoreCardMenu(meta));
      list.appendChild(card);
    }
  }

  function scoreCardMenu(meta) {
    openSheet(
      '<h2></h2>' +
      '<button class="menu-item" id="mi-open"><span class="mi">&#128193;</span>Open</button>' +
      '<button class="menu-item" id="mi-rename"><span class="mi">&#9998;</span>Rename</button>' +
      '<button class="menu-item" id="mi-dup"><span class="mi">&#10697;</span>Duplicate</button>' +
      '<button class="menu-item danger" id="mi-del"><span class="mi">&#128465;</span>Delete</button>'
    );
    $('sheet').querySelector('h2').textContent = meta.title || 'Untitled';
    $('mi-open').onclick = () => { closeSheet(); openScore(meta.id); };
    $('mi-rename').onclick = () => {
      closeSheet();
      promptDialog('Rename score', meta.title, (val) => {
        const s = Storage.loadScore(meta.id);
        if (s) { s.title = val || s.title; Storage.saveScore(s); renderLibrary(); }
      });
    };
    $('mi-dup').onclick = () => { closeSheet(); Storage.duplicateScore(meta.id); renderLibrary(); toast('Duplicated'); };
    $('mi-del').onclick = () => {
      closeSheet();
      confirmDialog('Delete "' + (meta.title || 'Untitled') + '"? This cannot be undone.', () => {
        Storage.deleteScore(meta.id);
        renderLibrary();
        toast('Score deleted');
      });
    };
  }

  function promptDialog(title, initial, cb) {
    openSheet(
      '<h2></h2>' +
      '<div class="row"><input type="text" id="pd-input"></div>' +
      '<div class="actions"><button class="btn ghost2 btn-cancel" id="pd-cancel" style="background:#e2e8f0;color:#0f172a">Cancel</button>' +
      '<button class="btn" id="pd-ok">OK</button></div>'
    );
    $('sheet').querySelector('h2').textContent = title;
    const input = $('pd-input');
    input.value = initial || '';
    input.focus();
    $('pd-cancel').onclick = closeSheet;
    $('pd-ok').onclick = () => { const v = input.value.trim(); closeSheet(); cb(v); };
  }

  function confirmDialog(msg, cb) {
    openSheet(
      '<h2>Are you sure?</h2><p id="cd-msg" style="color:#475569;font-size:14.5px"></p>' +
      '<div class="actions"><button class="btn" id="cd-cancel" style="background:#e2e8f0;color:#0f172a">Cancel</button>' +
      '<button class="btn danger" id="cd-ok">Delete</button></div>'
    );
    $('cd-msg').textContent = msg;
    $('cd-cancel').onclick = closeSheet;
    $('cd-ok').onclick = () => { closeSheet(); cb(); };
  }

  $('btn-new-score').addEventListener('click', () => {
    promptDialog('New score — title', '', (title) => {
      const score = newScore(title || 'Untitled score', ['piano']);
      Storage.saveScore(score);
      openScore(score.id);
    });
  });

  $('btn-import').addEventListener('click', async () => {
    try {
      const f = await importTextFile('.musicxml,.xml,.json,application/xml,application/json');
      let score;
      if (f.text.trim().startsWith('{')) {
        score = JSON.parse(f.text);
        if (!score.parts || !score.timeSig) throw new Error('Not a ScoreForge file');
        score.id = uid();
      } else {
        score = MusicXML.importScore(f.text);
      }
      Storage.saveScore(score);
      renderLibrary();
      toast('Imported "' + score.title + '"');
    } catch (e) {
      toast('Import failed: ' + e.message);
    }
  });

  /* ---------------- editor: lifecycle ---------------- */

  function openScore(id) {
    const score = Storage.loadScore(id);
    if (!score) { toast('Could not open score'); return; }
    Editor.score = score;
    Editor.sel = { p: 0, m: 0, e: 0 };
    Editor.undoStack = [];
    Editor.redoStack = [];
    Editor.chordMode = false;
    Editor.octShift = 0;
    $('screen-library').classList.add('hidden');
    $('screen-editor').classList.remove('hidden');
    syncHeader();
    buildPiano();
    rerender();
  }

  function syncHeader() {
    $('editor-title').textContent = Editor.score.title || 'Untitled';
    $('btn-tempo').innerHTML = '&#9833;=' + Editor.score.tempo;
  }

  function persistNow() {
    if (Editor.score) Storage.saveScore(Editor.score);
  }

  function schedulePersist() {
    clearTimeout(Editor.saveTimer);
    Editor.saveTimer = setTimeout(persistNow, 400);
  }

  /* Run a mutation with undo snapshot + autosave + re-render. */
  function mutate(fn) {
    if (!Editor.score) return;
    Editor.undoStack.push(JSON.stringify(Editor.score));
    if (Editor.undoStack.length > 100) Editor.undoStack.shift();
    Editor.redoStack = [];
    fn(Editor.score);
    clampSelection();
    schedulePersist();
    rerender();
  }

  function undo() {
    if (!Editor.undoStack.length) { toast('Nothing to undo'); return; }
    Editor.redoStack.push(JSON.stringify(Editor.score));
    Editor.score = JSON.parse(Editor.undoStack.pop());
    clampSelection();
    schedulePersist();
    syncHeader();
    rerender();
  }

  function redo() {
    if (!Editor.redoStack.length) { toast('Nothing to redo'); return; }
    Editor.undoStack.push(JSON.stringify(Editor.score));
    Editor.score = JSON.parse(Editor.redoStack.pop());
    clampSelection();
    schedulePersist();
    syncHeader();
    rerender();
  }

  function clampSelection() {
    const s = Editor.score;
    const sel = Editor.sel;
    sel.p = Math.min(sel.p, s.parts.length - 1);
    const part = s.parts[sel.p];
    sel.m = Math.min(sel.m, part.measures.length - 1);
    sel.e = Math.min(sel.e, part.measures[sel.m].events.length - 1);
    if (sel.e < 0) sel.e = 0;
  }

  function rerender() {
    if (!Editor.score) return;
    Editor.layout = Renderer.render(Editor.score, $('score-canvas'), Editor.sel);
    updateToolbarState();
    updateInputBar();
  }

  /* ---------------- editor: toolbar state ---------------- */

  function updateToolbarState() {
    document.querySelectorAll('#dur-group .tbtn[data-dur]').forEach((b) => {
      b.classList.toggle('active', b.dataset.dur === Editor.dur);
    });
    $('btn-dot').classList.toggle('active', Editor.dots === 1);
    $('btn-chord').classList.toggle('active', Editor.chordMode);
    const ev = getEvent(Editor.score, Editor.sel);
    $('btn-tie').classList.toggle('active', !!(ev && ev.tie));
    document.querySelectorAll('.tbtn.dyn').forEach((b) => {
      b.classList.toggle('active', !!(ev && ev.dynamic === b.dataset.dyn));
    });
  }

  document.querySelectorAll('#dur-group .tbtn[data-dur]').forEach((b) => {
    b.addEventListener('click', () => {
      Editor.dur = b.dataset.dur;
      // applying a duration to the selected event immediately, Flat-style
      const ev = getEvent(Editor.score, Editor.sel);
      if (ev && ev.type === 'note') {
        mutate(() => setEventDuration(Editor.score, Editor.sel, Editor.dur, Editor.dots));
      } else {
        updateToolbarState();
      }
    });
  });

  $('btn-dot').addEventListener('click', () => {
    Editor.dots = Editor.dots === 1 ? 0 : 1;
    const ev = getEvent(Editor.score, Editor.sel);
    if (ev && ev.type === 'note') {
      mutate(() => setEventDuration(Editor.score, Editor.sel, ev.dur, Editor.dots));
    } else {
      updateToolbarState();
    }
  });

  $('btn-sharp').addEventListener('click', () => mutate(() => applyAccidental(Editor.score, Editor.sel, 1)));
  $('btn-flat').addEventListener('click', () => mutate(() => applyAccidental(Editor.score, Editor.sel, -1)));
  $('btn-natural').addEventListener('click', () => mutate(() => applyAccidental(Editor.score, Editor.sel, 0)));
  $('btn-tie').addEventListener('click', () => mutate(() => toggleTie(Editor.score, Editor.sel)));

  document.querySelectorAll('.tbtn.dyn').forEach((b) => {
    b.addEventListener('click', () => mutate(() => setDynamic(Editor.score, Editor.sel, b.dataset.dyn)));
  });

  $('btn-rest').addEventListener('click', () => {
    mutate(() => {
      const idx = insertRest(Editor.score, Editor.sel, Editor.dur, Editor.dots);
      if (idx >= 0) Editor.sel = moveSelection(Editor.score, { p: Editor.sel.p, m: Editor.sel.m, e: idx }, 1);
    });
  });

  $('btn-erase').addEventListener('click', () => mutate(() => deleteEvent(Editor.score, Editor.sel)));
  $('btn-chord').addEventListener('click', () => {
    Editor.chordMode = !Editor.chordMode;
    updateToolbarState();
    toast(Editor.chordMode ? 'Chord mode: keys add notes to the selected note' : 'Chord mode off');
  });

  $('btn-undo').addEventListener('click', undo);
  $('btn-redo').addEventListener('click', redo);
  $('btn-add-measure').addEventListener('click', () => mutate(() => addMeasures(Editor.score, 1)));

  /* ---------------- editor: selection + navigation ---------------- */

  $('score-canvas').addEventListener('click', (ev) => {
    if (!Editor.layout) return;
    const svg = $('score-canvas').querySelector('svg');
    if (!svg) return;
    const r = svg.getBoundingClientRect();
    const hit = Renderer.hitTest(Editor.layout, ev.clientX - r.left, ev.clientY - r.top);
    if (hit) {
      Editor.sel = hit;
      const e = getEvent(Editor.score, Editor.sel);
      if (e && e.type === 'note') {
        Editor.dur = e.dur;
        Editor.dots = e.dots || 0;
      }
      rerender();
    }
  });

  $('btn-prev').addEventListener('click', () => { Editor.sel = moveSelection(Editor.score, Editor.sel, -1); rerender(); scrollToSelection(); });
  $('btn-next').addEventListener('click', () => { Editor.sel = moveSelection(Editor.score, Editor.sel, 1); rerender(); scrollToSelection(); });
  $('btn-pitch-up').addEventListener('click', () => mutate(() => transposeEvent(Editor.score, Editor.sel, 1)));
  $('btn-pitch-down').addEventListener('click', () => mutate(() => transposeEvent(Editor.score, Editor.sel, -1)));

  function scrollToSelection() {
    if (!Editor.layout) return;
    const hit = Editor.layout.hits.find((h) => h.p === Editor.sel.p && h.m === Editor.sel.m && h.e === Editor.sel.e);
    if (!hit) return;
    const sc = $('score-scroll');
    const target = hit.x - sc.clientWidth / 2;
    sc.scrollTo({ left: Math.max(0, target), behavior: 'smooth' });
  }

  /* ---------------- editor: piano & drum input ---------------- */

  const WHITE_STEPS = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];
  // black key x-centers as a fraction of two-octave white width (7 whites per octave)
  const BLACKS = [
    { after: 0, pc: 1 }, { after: 1, pc: 3 }, { after: 3, pc: 6 }, { after: 4, pc: 8 }, { after: 5, pc: 10 },
  ];

  function currentBaseOctave() {
    const part = Editor.score.parts[Editor.sel.p];
    const inst = getInstrument(part.instrumentId);
    return (inst.oct || 4) + Editor.octShift;
  }

  function buildPiano() {
    const piano = $('piano');
    piano.innerHTML = '';
    const nOct = 2;
    const baseOct = 0; // octave labels are resolved at press time
    for (let o = 0; o < nOct; o++) {
      for (let w = 0; w < 7; w++) {
        const key = document.createElement('button');
        key.className = 'pkey-white';
        key.dataset.oct = o;
        key.dataset.step = WHITE_STEPS[w];
        if (WHITE_STEPS[w] === 'C') key.textContent = 'C';
        key.addEventListener('pointerdown', (e) => { e.preventDefault(); pressPitchKey(key.dataset.step, +key.dataset.oct, 0); });
        piano.appendChild(key);
      }
    }
    // black keys positioned over the white keys
    const totalWhites = nOct * 7;
    for (let o = 0; o < nOct; o++) {
      for (const b of BLACKS) {
        const key = document.createElement('button');
        key.className = 'pkey-black';
        const whiteIndex = o * 7 + b.after;
        const left = ((whiteIndex + 1) / totalWhites) * 100;
        key.style.left = 'calc(' + left + '% - 4%)';
        key.dataset.oct = o;
        key.dataset.pc = b.pc;
        key.addEventListener('pointerdown', (e) => {
          e.preventDefault();
          pressChromaticKey(+key.dataset.pc, +key.dataset.oct);
        });
        piano.appendChild(key);
      }
    }
    void baseOct;
  }

  function buildDrumPads() {
    const wrap = $('drumpads');
    wrap.innerHTML = '';
    for (const d of DRUM_KIT) {
      const b = document.createElement('button');
      b.className = 'dpad';
      b.textContent = d.label;
      b.addEventListener('pointerdown', (e) => { e.preventDefault(); pressDrumPad(d); });
      wrap.appendChild(b);
    }
  }

  function updateInputBar() {
    const part = Editor.score.parts[Editor.sel.p];
    const inst = getInstrument(part.instrumentId);
    const isKit = !!inst.kit;
    $('piano-wrap').classList.toggle('hidden', isKit);
    $('drumpads').classList.toggle('hidden', !isKit);
    if (isKit && !$('drumpads').children.length) buildDrumPads();
  }

  function enterNote(pitch) {
    const part = Editor.score.parts[Editor.sel.p];
    Playback.preview(part.instrumentId, pitch);
    if (Editor.chordMode) {
      const ev = getEvent(Editor.score, Editor.sel);
      if (ev && ev.type === 'note') {
        mutate(() => toggleChordPitch(Editor.score, Editor.sel, pitch));
        return;
      }
    }
    mutate(() => {
      const idx = insertNote(Editor.score, Editor.sel, pitch, Editor.dur, Editor.dots);
      if (idx >= 0) {
        Editor.sel = moveSelection(Editor.score, { p: Editor.sel.p, m: Editor.sel.m, e: idx }, 1);
        // grow the score when the cursor reaches the final measure
        const part2 = Editor.score.parts[Editor.sel.p];
        if (Editor.sel.m === part2.measures.length - 1) addMeasures(Editor.score, 0);
      }
    });
    scrollToSelection();
  }

  function pressPitchKey(step, octOffset, alterIgnored) {
    const oct = currentBaseOctave() + octOffset;
    const fifths = Editor.score.fifths;
    const alter = keyAlterForStep(fifths, step);
    enterNote({ step, oct, alter });
  }

  function pressChromaticKey(pc, octOffset) {
    const oct = currentBaseOctave() + octOffset;
    const midi = 12 * (oct + 1) + pc;
    enterNote(midiToPitch(midi, Editor.score.fifths));
  }

  function pressDrumPad(drum) {
    const part = Editor.score.parts[Editor.sel.p];
    Playback.preview(part.instrumentId, drum.sound);
    if (Editor.chordMode) {
      const ev = getEvent(Editor.score, Editor.sel);
      if (ev && ev.type === 'note') {
        mutate(() => toggleChordPitch(Editor.score, Editor.sel, drum.key));
        return;
      }
    }
    mutate(() => {
      const idx = insertNote(Editor.score, Editor.sel, drum.key, Editor.dur, Editor.dots);
      if (idx >= 0) Editor.sel = moveSelection(Editor.score, { p: Editor.sel.p, m: Editor.sel.m, e: idx }, 1);
    });
    scrollToSelection();
  }

  $('btn-oct-up').addEventListener('click', () => { Editor.octShift = Math.min(3, Editor.octShift + 1); toast('Octave +' + Editor.octShift); });
  $('btn-oct-down').addEventListener('click', () => { Editor.octShift = Math.max(-3, Editor.octShift - 1); toast('Octave ' + Editor.octShift); });

  /* ---------------- editor: playback ---------------- */

  function updatePlayButton(playing) {
    const b = $('btn-play');
    b.classList.toggle('playing', playing);
    b.innerHTML = playing ? '&#9632;' : '&#9654;';
  }

  let lastLit = [];
  $('btn-play').addEventListener('click', () => {
    if (Playback.isPlaying()) {
      Playback.stop();
      updatePlayButton(false);
      clearLit();
      return;
    }
    persistNow();
    updatePlayButton(true);
    Playback.play(Editor.score, {
      onTick: (now, seq) => {
        clearLit();
        const sc = $('score-scroll');
        let scrolled = false;
        for (const n of seq) {
          if (now >= n.t && now < n.t + n.dur) {
            const el = Editor.layout && Editor.layout.noteEls[n.p + ':' + n.m + ':' + n.e];
            if (el) {
              el.classList.add('vf-playing');
              lastLit.push(el);
              if (!scrolled) {
                const hit = Editor.layout.hits.find((h) => h.p === n.p && h.m === n.m && h.e === n.e);
                if (hit) {
                  const target = hit.x - sc.clientWidth * 0.35;
                  if (Math.abs(sc.scrollLeft - Math.max(0, target)) > 30) {
                    sc.scrollTo({ left: Math.max(0, target) });
                  }
                  scrolled = true;
                }
              }
            }
          }
        }
      },
      onEnd: () => { updatePlayButton(false); clearLit(); },
    });
  });

  function clearLit() {
    for (const el of lastLit) el.classList.remove('vf-playing');
    lastLit = [];
  }

  $('btn-tempo').addEventListener('click', () => {
    openSheet(
      '<h2>Tempo</h2>' +
      '<div class="row"><label>BPM</label><input type="range" id="tempo-range" min="30" max="240" step="1"></div>' +
      '<div class="row"><label>Value</label><input type="number" id="tempo-num" min="30" max="240"></div>' +
      '<div class="actions"><button class="btn" id="tempo-ok">Done</button></div>'
    );
    const range = $('tempo-range');
    const num = $('tempo-num');
    range.value = num.value = Editor.score.tempo;
    range.oninput = () => { num.value = range.value; };
    num.oninput = () => { range.value = num.value; };
    $('tempo-ok').onclick = () => {
      const v = Math.max(30, Math.min(240, parseInt(num.value, 10) || 120));
      closeSheet();
      mutate((s) => { s.tempo = v; });
      syncHeader();
    };
  });

  /* ---------------- editor: parts panel ---------------- */

  $('btn-parts').addEventListener('click', showPartsPanel);

  function showPartsPanel() {
    const s = Editor.score;
    let html = '<h2>Instruments &amp; parts</h2><div id="parts-list"></div>' +
      '<div class="actions"><button class="btn" id="add-part">+ Add instrument</button></div>' +
      '<p style="color:#94a3b8;font-size:12px;margin:10px 0 0">All instruments are free. Add as many parts as you like.</p>';
    openSheet(html);
    const list = $('parts-list');
    s.parts.forEach((part, p) => {
      const row = document.createElement('div');
      row.className = 'part-row' + (p === Editor.sel.p ? ' selected' : '');
      row.innerHTML =
        '<div class="pname"><div class="n1"></div><div class="n2"></div></div>' +
        '<input type="range" min="0" max="1" step="0.05" title="Volume">' +
        '<button class="pbtn mute" title="Mute"></button>' +
        '<button class="pbtn del" title="Remove part">&#128465;</button>';
      row.querySelector('.n1').textContent = part.name;
      row.querySelector('.n2').textContent = getInstrument(part.instrumentId).family + ' · ' + part.clef + ' clef';
      const vol = row.querySelector('input');
      vol.value = part.volume;
      vol.addEventListener('change', () => { part.volume = parseFloat(vol.value); schedulePersist(); });
      const muteBtn = row.querySelector('.mute');
      const setMuteUi = () => {
        muteBtn.innerHTML = part.mute ? '&#128263;' : '&#128266;';
        muteBtn.classList.toggle('muted', part.mute);
      };
      setMuteUi();
      muteBtn.addEventListener('click', () => { part.mute = !part.mute; setMuteUi(); schedulePersist(); });
      row.querySelector('.del').addEventListener('click', () => {
        if (s.parts.length <= 1) { toast('A score needs at least one part'); return; }
        mutate(() => removePart(s, p));
        closeSheet();
        showPartsPanel();
      });
      row.querySelector('.pname').addEventListener('click', () => {
        Editor.sel = { p, m: 0, e: 0 };
        closeSheet();
        rerender();
        scrollToSelection();
      });
      list.appendChild(row);
    });
    $('add-part').onclick = showInstrumentPicker;
  }

  function showInstrumentPicker() {
    let html = '<h2>Add instrument</h2>' +
      '<input type="text" id="inst-q" class="inst-search" placeholder="Search instruments…">' +
      '<div id="inst-list"></div>';
    openSheet(html);
    const listEl = $('inst-list');
    const q = $('inst-q');
    const renderList = () => {
      const term = q.value.trim().toLowerCase();
      listEl.innerHTML = '';
      for (const fam of INSTRUMENT_FAMILIES) {
        for (const inst of fam.items) {
          if (term && !inst.name.toLowerCase().includes(term) && !fam.family.toLowerCase().includes(term)) continue;
          const b = document.createElement('button');
          b.className = 'inst-item';
          b.innerHTML = '<span></span><span class="fam"></span>';
          b.firstChild.textContent = inst.name;
          b.lastChild.textContent = fam.family;
          b.addEventListener('click', () => {
            mutate(() => addPart(Editor.score, inst.id));
            Editor.sel = { p: Editor.score.parts.length - 1, m: 0, e: 0 };
            closeSheet();
            rerender();
            toast(inst.name + ' added');
          });
          listEl.appendChild(b);
        }
      }
    };
    q.addEventListener('input', renderList);
    renderList();
  }

  /* ---------------- editor: menu, settings, export ---------------- */

  $('btn-menu').addEventListener('click', () => {
    openSheet(
      '<h2>Score</h2>' +
      '<button class="menu-item" id="m-settings"><span class="mi">&#9881;</span>Score settings (title, key, time)</button>' +
      '<button class="menu-item" id="m-parts"><span class="mi">&#127932;</span>Instruments &amp; parts</button>' +
      '<button class="menu-item" id="m-export-xml"><span class="mi">&#128229;</span>Export MusicXML (.musicxml)</button>' +
      '<button class="menu-item" id="m-export-json"><span class="mi">&#128190;</span>Export ScoreForge file (.json)</button>' +
      '<button class="menu-item" id="m-add4"><span class="mi">+</span>Add 4 measures</button>' +
      '<button class="menu-item" id="m-delm"><span class="mi">&#8722;</span>Delete current measure</button>' +
      '<button class="menu-item danger" id="m-del"><span class="mi">&#128465;</span>Delete score</button>'
    );
    $('m-settings').onclick = () => { closeSheet(); showSettings(); };
    $('m-parts').onclick = () => { closeSheet(); showPartsPanel(); };
    $('m-export-xml').onclick = () => {
      closeSheet();
      const where = exportTextFile(fileNameFor(Editor.score.title, '.musicxml'),
        'application/vnd.recordare.musicxml+xml', MusicXML.exportScore(Editor.score));
      toast(where === 'downloads' ? 'Saved to Downloads' : 'Downloading…');
    };
    $('m-export-json').onclick = () => {
      closeSheet();
      const where = exportTextFile(fileNameFor(Editor.score.title, '.scoreforge.json'),
        'application/json', JSON.stringify(Editor.score, null, 1));
      toast(where === 'downloads' ? 'Saved to Downloads' : 'Downloading…');
    };
    $('m-add4').onclick = () => { closeSheet(); mutate(() => addMeasures(Editor.score, 4)); };
    $('m-delm').onclick = () => {
      closeSheet();
      mutate(() => { if (!removeMeasure(Editor.score, Editor.sel.m)) toast('Cannot delete the only measure'); });
    };
    $('m-del').onclick = () => {
      closeSheet();
      confirmDialog('Delete this score permanently?', () => {
        Storage.deleteScore(Editor.score.id);
        Editor.score = null;
        showLibrary();
      });
    };
  });

  function showSettings() {
    const s = Editor.score;
    const keyOpts = KEY_SIGS.map((k) => '<option value="' + k.fifths + '">' + k.name + '</option>').join('');
    const tsOpts = ['2/4', '3/4', '4/4', '5/4', '6/8', '9/8', '12/8', '2/2', '3/8']
      .map((t) => '<option>' + t + '</option>').join('');
    openSheet(
      '<h2>Score settings</h2>' +
      '<div class="row"><label>Title</label><input type="text" id="st-title"></div>' +
      '<div class="row"><label>Composer</label><input type="text" id="st-composer"></div>' +
      '<div class="row"><label>Key</label><select id="st-key">' + keyOpts + '</select></div>' +
      '<div class="row"><label>Time</label><select id="st-time">' + tsOpts + '</select></div>' +
      '<div class="actions"><button class="btn" id="st-ok">Save</button></div>'
    );
    $('st-title').value = s.title;
    $('st-composer').value = s.composer || '';
    $('st-key').value = String(s.fifths);
    $('st-time').value = s.timeSig.num + '/' + s.timeSig.den;
    $('st-ok').onclick = () => {
      const title = $('st-title').value.trim() || 'Untitled score';
      const composer = $('st-composer').value.trim();
      const fifths = parseInt($('st-key').value, 10);
      const [num, den] = $('st-time').value.split('/').map((x) => parseInt(x, 10));
      closeSheet();
      mutate((sc) => {
        sc.title = title;
        sc.composer = composer;
        sc.fifths = fifths;
        if (num !== sc.timeSig.num || den !== sc.timeSig.den) setTimeSignature(sc, num, den);
      });
      syncHeader();
    };
  }

  $('editor-title').addEventListener('click', showSettings);
  $('btn-back').addEventListener('click', showLibrary);

  /* Android hardware back button: MainActivity calls window.appBack(). */
  window.appBack = () => {
    if (!$('overlay').classList.contains('hidden')) { closeSheet(); return true; }
    if (!$('screen-editor').classList.contains('hidden')) { showLibrary(); return true; }
    return false; // at library root: let Android close the app
  };

  window.addEventListener('pagehide', persistNow);
  document.addEventListener('visibilitychange', () => { if (document.hidden) persistNow(); });

  /* ---------------- boot ---------------- */
  renderLibrary();
})();
