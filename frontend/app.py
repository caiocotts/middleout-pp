"""
Flask backend for the Middleout compression frontend.
Serves static files and exposes a /api/process endpoint.
"""

import sys
import os
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Make letter_based importable
REPO_ROOT = Path(__file__).parent.parent
LETTER_BASED = REPO_ROOT / "letter_based"
sys.path.insert(0, str(LETTER_BASED))

# Import the algorithmic compressor (pure Python, no Ollama needed)
from main import compress, decompress  # noqa: E402

app = Flask(__name__, static_folder="static")
CORS(app)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/process", methods=["POST"])
def process():
    data = request.get_json(force=True)
    text: str = data.get("text", "")

    if not text.strip():
        return jsonify({"error": "Empty input"}), 400

    # --- Algorithmic compression (always runs) ---
    try:
        compressed = compress(text)
    except Exception as exc:
        return jsonify({"error": f"Compression failed: {exc}"}), 500

    original_chars = len(text)
    compressed_chars = len(compressed)
    ratio = (1 - compressed_chars / original_chars) * 100 if original_chars else 0

    # --- LLM decompression (optional — needs Ollama running) ---
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
