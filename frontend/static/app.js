/* ========================================================
   Middleout Frontend — app.js
   Two-phase flow:
     Phase 1 → /api/compress  (instant, shows original + compressed immediately)
     Phase 2 → /api/decompress (LLM, fills decoded panel when ready)
   ======================================================== */

const dropZone     = document.getElementById('drop-zone');
const fileInput    = document.getElementById('file-input');
const browseTrig   = document.getElementById('browse-trigger');
const filePill     = document.getElementById('file-pill');
const filePillName = document.getElementById('file-pill-name');
const filePillSize = document.getElementById('file-pill-size');
const filePillRem  = document.getElementById('file-pill-remove');
const runBtn       = document.getElementById('run-btn');
const processing   = document.getElementById('processing');
const results      = document.getElementById('results');
const uploadSect   = document.getElementById('upload-section');

// Stat elements
const statOriginal   = document.getElementById('stat-original');
const statCompressed = document.getElementById('stat-compressed');
const statRatio      = document.getElementById('stat-ratio');

// Text panels
const textOriginal    = document.getElementById('text-original');
const textCompressed  = document.getElementById('text-compressed');
const textDecoded     = document.getElementById('text-decoded');
const decompressNote  = document.getElementById('decompress-note');
const decodedSkeleton = document.getElementById('decoded-skeleton');
const decodedBadge    = document.getElementById('decoded-badge');
const decodedCopyBtn  = document.getElementById('decoded-copy-btn');

// Loading bar (kept for backwards compat but no longer used in new flow)
const loadingBarWrap  = document.getElementById('loading-bar-wrap');
const loadingBarLabel = document.getElementById('loading-bar-label');

const resetBtn = document.getElementById('reset-btn');

let currentFile = null;
let isProcessing = false;  // guard against duplicate submissions

/* ── helpers ───────────────────────────────────────────── */
function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fmtChars(n) {
  return n.toLocaleString() + ' chars';
}

function setFile(file) {
  if (!file || (file.type !== 'text/plain' && !file.name.endsWith('.txt'))) {
    alert('Please upload a plain .txt file.');
    return;
  }
  currentFile = file;
  filePillName.textContent = file.name;
  filePillSize.textContent = fmtSize(file.size);
  filePill.hidden = false;
  runBtn.disabled = false;
}

function clearFile() {
  currentFile = null;
  fileInput.value = '';
  filePill.hidden = true;
  runBtn.disabled = true;
}

function showUpload() {
  results.hidden    = true;
  processing.hidden = true;
  uploadSect.hidden = false;
}

/* ── Phase 1: show original + compressed right away ────── */
function showPartialResults(data) {
  uploadSect.hidden = true;
  processing.hidden = true;
  results.hidden    = false;

  statOriginal.textContent   = fmtChars(data.stats.original_chars);
  statCompressed.textContent = fmtChars(data.stats.compressed_chars);
  statRatio.textContent      = `${data.stats.ratio}% smaller`;

  textOriginal.textContent  = data.original;
  textCompressed.textContent = data.compressed;

  // Decoded panel → show skeleton while LLM runs
  textDecoded.hidden     = true;
  decompressNote.hidden  = true;
  decodedSkeleton.hidden = false;
  decodedBadge.classList.add('decoding');
  decodedCopyBtn.disabled = true;
  decodedCopyBtn.style.opacity = '0.35';
}

/* ── Phase 2: fill in decoded panel once LLM is done ───── */
function showDecompressed(data) {
  decodedSkeleton.hidden = true;
  decodedBadge.classList.remove('decoding');
  decodedCopyBtn.disabled = false;
  decodedCopyBtn.style.opacity = '';

  if (data.decompressed) {
    textDecoded.hidden    = false;
    textDecoded.textContent = data.decompressed;
    decompressNote.hidden = true;
  } else {
    textDecoded.hidden    = false;
    textDecoded.textContent = '(LLM decompression unavailable)';
    decompressNote.hidden = false;
    decompressNote.textContent = '⚠ ' + (data.decompress_error || 'Ollama not running');
  }
}

/* ── drag-and-drop ──────────────────────────────────────── */
dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
['dragleave', 'dragend'].forEach(evt => {
  dropZone.addEventListener(evt, () => dropZone.classList.remove('drag-over'));
});
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
});

/* ── click to browse ───────────────────────────────────── */
browseTrig.addEventListener('click', e => { e.stopPropagation(); fileInput.click(); });
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('keydown', e => {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) setFile(fileInput.files[0]);
});

/* ── remove file ────────────────────────────────────────── */
filePillRem.addEventListener('click', e => { e.stopPropagation(); clearFile(); });

/* ── MAIN RUN ───────────────────────────────────────── */
runBtn.addEventListener('click', async () => {
  if (!currentFile || isProcessing) return;

  // Lock immediately
  isProcessing = true;
  runBtn.disabled = true;
  runBtn.querySelector('.run-btn-label').textContent = 'Compressing…';

  const text = await currentFile.text();

  // ── Phase 1: algorithmic compression (instant) ───────
  let compressData;
  try {
    const res = await fetch('/api/compress', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || 'Compression failed');
    }
    compressData = await res.json();
  } catch (err) {
    isProcessing = false;
    runBtn.disabled = false;
    runBtn.querySelector('.run-btn-label').textContent = 'Compress & Decode';
    alert('Error: ' + err.message);
    return;
  }

  // Show original + compressed immediately, skeleton in decoded panel
  showPartialResults(compressData);
  runBtn.querySelector('.run-btn-label').textContent = 'Decoding…';

  // ── Phase 2: LLM decompression (slow, background) ───
  try {
    const res2 = await fetch('/api/decompress', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ compressed: compressData.compressed }),
    });
    if (!res2.ok) {
      const err = await res2.json().catch(() => ({ error: res2.statusText }));
      throw new Error(err.error || 'Decompression failed');
    }
    const decompressData = await res2.json();
    showDecompressed(decompressData);
  } catch (err) {
    showDecompressed({ decompressed: null, decompress_error: err.message });
  }

  // Unlock
  isProcessing = false;
  runBtn.disabled = false;
  runBtn.querySelector('.run-btn-label').textContent = 'Compress & Decode';
});

/* ── copy buttons ───────────────────────────────────────── */
document.querySelectorAll('.copy-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    if (btn.disabled) return;
    const targetId = btn.dataset.target;
    const el = document.getElementById(targetId);
    if (!el || el.hidden) return;
    await navigator.clipboard.writeText(el.textContent).catch(() => {});
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = 'Copy'; btn.classList.remove('copied'); }, 1800);
  });
});

/* ── reset ──────────────────────────────────────────────── */
resetBtn.addEventListener('click', () => {
  clearFile();
  showUpload();
});
