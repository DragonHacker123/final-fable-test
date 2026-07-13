/* ScoreForge — persistence and file export/import.
 * Scores live in localStorage (unlimited count). File export goes through the
 * Android bridge when running inside the APK, or a normal browser download
 * otherwise.
 */
'use strict';

const Storage = {
  INDEX_KEY: 'scoreforge.index',

  _readIndex() {
    try {
      return JSON.parse(localStorage.getItem(this.INDEX_KEY)) || [];
    } catch (e) {
      return [];
    }
  },

  _writeIndex(idx) {
    localStorage.setItem(this.INDEX_KEY, JSON.stringify(idx));
  },

  listScores() {
    return this._readIndex().sort((a, b) => b.updatedAt - a.updatedAt);
  },

  loadScore(id) {
    try {
      return JSON.parse(localStorage.getItem('scoreforge.score.' + id));
    } catch (e) {
      return null;
    }
  },

  saveScore(score) {
    score.updatedAt = Date.now();
    localStorage.setItem('scoreforge.score.' + score.id, JSON.stringify(score));
    const idx = this._readIndex();
    const meta = {
      id: score.id,
      title: score.title,
      composer: score.composer,
      parts: score.parts.map((p) => p.name),
      updatedAt: score.updatedAt,
      createdAt: score.createdAt,
    };
    const at = idx.findIndex((s) => s.id === score.id);
    if (at >= 0) idx[at] = meta; else idx.push(meta);
    this._writeIndex(idx);
  },

  deleteScore(id) {
    localStorage.removeItem('scoreforge.score.' + id);
    this._writeIndex(this._readIndex().filter((s) => s.id !== id));
  },

  duplicateScore(id) {
    const score = this.loadScore(id);
    if (!score) return null;
    score.id = uid();
    score.title = score.title + ' (copy)';
    score.createdAt = Date.now();
    this.saveScore(score);
    return score;
  },
};

/* Sanitize a title into a filename. */
function fileNameFor(title, ext) {
  const base = (title || 'score').replace(/[^\w\- ]+/g, '').trim().replace(/\s+/g, '_') || 'score';
  return base + ext;
}

function exportTextFile(name, mime, text) {
  if (window.AndroidBridge && window.AndroidBridge.saveFile) {
    // btoa needs latin1; encode UTF-8 first
    const b64 = btoa(unescape(encodeURIComponent(text)));
    window.AndroidBridge.saveFile(name, mime, b64);
    return 'downloads';
  }
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 500);
  return 'browser';
}

/* Open a file picker and return the file's text content. */
function importTextFile(accept) {
  return new Promise((resolve, reject) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = accept;
    input.style.display = 'none';
    document.body.appendChild(input);
    input.addEventListener('change', () => {
      const f = input.files && input.files[0];
      if (!f) { input.remove(); return reject(new Error('No file chosen')); }
      const reader = new FileReader();
      reader.onload = () => { input.remove(); resolve({ name: f.name, text: String(reader.result) }); };
      reader.onerror = () => { input.remove(); reject(reader.error); };
      reader.readAsText(f);
    });
    input.click();
  });
}
