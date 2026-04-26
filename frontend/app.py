"""
Flask backend for the Middleout compression frontend.
Serves static files and exposes split /api/compress + /api/decompress endpoints.
"""

import sys
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Make letter_based importable
REPO_ROOT = Path(__file__).parent.parent
LETTER_BASED = REPO_ROOT / "letter_based"
sys.path.insert(0, str(LETTER_BASED))

from main import compress, decompress  # noqa: E402

app = Flask(__name__, static_folder="static")
CORS(app)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# ── Phase 1: pure algorithmic compression (instant) ──────────────────────────
@app.route("/api/compress", methods=["POST"])
def compress_route():
    data = request.get_json(force=True)
    text: str = data.get("text", "")

    if not text.strip():
        return jsonify({"error": "Empty input"}), 400

    try:
        compressed = compress(text)
    except Exception as exc:
        return jsonify({"error": f"Compression failed: {exc}"}), 500

    original_chars = len(text)
    compressed_chars = len(compressed)
    ratio = (1 - compressed_chars / original_chars) * 100 if original_chars else 0

    return jsonify({
        "original": text,
        "compressed": compressed,
        "stats": {
            "original_chars": original_chars,
            "compressed_chars": compressed_chars,
            "ratio": round(ratio, 1),
        },
    })


# ── Phase 2: LLM decompression (slow — needs Ollama) ─────────────────────────
@app.route("/api/decompress", methods=["POST"])
def decompress_route():
    data = request.get_json(force=True)
    compressed: str = data.get("compressed", "")

    if not compressed.strip():
        return jsonify({"error": "Empty input"}), 400

    try:
        decompressed = decompress(compressed)
        return jsonify({"decompressed": decompressed, "decompress_error": None})
    except Exception as exc:
        return jsonify({"decompressed": None, "decompress_error": str(exc)})


# ── Legacy combined endpoint (kept for backwards compat) ──────────────────────
@app.route("/api/process", methods=["POST"])
def process():
    data = request.get_json(force=True)
    text: str = data.get("text", "")

    if not text.strip():
        return jsonify({"error": "Empty input"}), 400

    try:
        compressed = compress(text)
    except Exception as exc:
        return jsonify({"error": f"Compression failed: {exc}"}), 500

    original_chars = len(text)
    compressed_chars = len(compressed)
    ratio = (1 - compressed_chars / original_chars) * 100 if original_chars else 0

    decompressed = None
    decompress_error = None
    try:
        decompressed = decompress(compressed)
    except Exception as exc:
        decompress_error = str(exc)

    return jsonify({
        "original": text,
        "compressed": compressed,
        "decompressed": decompressed,
        "decompress_error": decompress_error,
        "stats": {
            "original_chars": original_chars,
            "compressed_chars": compressed_chars,
            "ratio": round(ratio, 1),
        },
    })


if __name__ == "__main__":
    app.run(debug=True, port=5050)
