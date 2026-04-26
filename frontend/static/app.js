/* ========================================================
   Middleout Frontend — app.js
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

// Pipeline elements
const stepCompress   = document.getElementById('step-compress');
const stepDecompress = document.getElementById('step-decompress');
const stepDone       = document.getElementById('step-done');
const line1          = document.getElementById('line-1');
const line2          = document.getElementById('line-2');

// Stat elements
const statOriginal   = document.getElementById('stat-original');
const statCompressed = document.getElementById('stat-compressed');
const statRatio      = document.getElementById('stat-ratio');

// Text panels
const textOriginal   = document.getElementById('text-original');
const textCompressed = document.getElementById('text-compressed');
const textDecoded    = document.getElementById('text-decoded');
const decompressNote = document.getElementById('decompress-note');

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
  if (!file || file.type !== 'text/plain' && !file.name.endsWith('.txt')) {
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

function showProcessing() {
  uploadSect.hidden = true;
  results.hidden    = true;
  processing.hidden = false;
  loadingBarWrap.hidden = true;   // hidden until LLM phase starts
  // reset pipeline
  [stepCompress, stepDecompress, stepDone].forEach(s => {
    s.classList.remove('active', 'done');
  });
  [line1, line2].forEach(l => l.classList.remove('filled'));
  stepCompress.classList.add('active');
}

function pipelineProgress(stage) {
  // stage: 'decompress' | 'done'
  if (stage === 'decompress') {
    stepCompress.classList.remove('active');
    stepCompress.classList.add('done');
    line1.classList.add('filled');
    stepDecompress.classList.add('active');
    // Show loading bar now that we're waiting for Ollama
    loadingBarWrap.hidden = false;
    loadingBarLabel.textContent = 'Running LLM decompression…';
  } else if (stage === 'done') {
    loadingBarWrap.hidden = true;     // hide bar when done
    stepDecompress.classList.remove('active');
    stepDecompress.classList.add('done');
    line2.classList.add('filled');
    stepDone.classList.add('active');
    setTimeout(() => {
      stepDone.classList.remove('active');
      stepDone.classList.add('done');
    }, 400);
  }
}

function showResults(data) {
  processing.hidden = true;
  results.hidden    = false;

  // Stats
  statOriginal.textContent   = fmtChars(data.stats.original_chars);
  statCompressed.textContent = fmtChars(data.stats.compressed_chars);
  statRatio.textContent      = `${data.stats.ratio}% smaller`;

  // Panels
  textOriginal.textContent   = data.original;
  textCompressed.textContent = data.compressed;

  if (data.decompressed) {
    textDecoded.textContent    = data.decompressed;
    decompressNote.hidden      = true;
  } else {
    textDecoded.textContent    = '(LLM decompression unavailable)';
    decompressNote.hidden      = false;
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

  // Lock immediately — disable button so the user can’t queue another call
  isProcessing = true;
  runBtn.disabled = true;
  runBtn.querySelector('.run-btn-label').textContent = 'Processing…';

  const text = await currentFile.text();

  showProcessing();

  // Tiny delay so the pipeline animation is visible before the fetch
  await new Promise(r => setTimeout(r, 500));

  let data;
  try {
    const res = await fetch('/api/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || 'Server error');
    }

    // Compression is instant; now we wait for the LLM — show the loading bar
    pipelineProgress('decompress');

    data = await res.json();
  } catch (err) {
    // On error: restore UI so the user can try again
    isProcessing = false;
    runBtn.disabled = false;
    runBtn.querySelector('.run-btn-label').textContent = 'Compress & Decode';
    processing.hidden = true;
    uploadSect.hidden = false;
    alert('Error: ' + err.message);
    return;
  }

  pipelineProgress('done');
  await new Promise(r => setTimeout(r, 600));

  showResults(data);

  // Unlock after results are shown
  isProcessing = false;
  runBtn.disabled = false;
  runBtn.querySelector('.run-btn-label').textContent = 'Compress & Decode';
});

/* ── copy buttons ───────────────────────────────────────── */
document.querySelectorAll('.copy-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const targetId = btn.dataset.target;
    const el = document.getElementById(targetId);
    if (!el) return;
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
