"""Speech-to-text using mlx-whisper (macOS Apple Silicon only)."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Suppress HuggingFace progress bars before any imports
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TQDM_DISABLE"] = "1"

_DEFAULT_MODEL = "mlx-community/whisper-turbo"


def transcribe_audio(
    audio_path: str,
    model: str = _DEFAULT_MODEL,
    language: str = "zh",
) -> List[Dict[str, Any]]:
    """Transcribe a local audio file using mlx-whisper.

    Returns list of segments: [{"start": 0.0, "end": 2.5, "text": "..."}]
    Raises RuntimeError if mlx-whisper is not installed.
    """
    try:
        import mlx_whisper
    except ImportError:
        raise RuntimeError(
            "mlx-whisper not installed. Install with: pip install mlx-whisper\n"
            "Requires macOS with Apple Silicon."
        )

    import io
    import sys
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        result = mlx_whisper.transcribe(
            audio_path,
            path_or_hf_repo=model,
            language=language,
            verbose=False,
        )
    finally:
        sys.stderr = old_stderr

    segments = []
    for seg in result.get("segments", []):
        text = " ".join(seg.get("text", "").split())
        if text:
            segments.append({
                "start": round(seg.get("start", 0), 1),
                "end": round(seg.get("end", 0), 1),
                "text": text,
            })
    return segments


def transcribe_from_url(
    client,
    url: str,
    model: str = _DEFAULT_MODEL,
    language: str = "zh",
    quiet: bool = False,
) -> List[Dict[str, Any]]:
    """Download audio from URL via ffmpeg, then transcribe.

    This is a helper for transcribing bilibili audio streams directly.
    """
    import shutil
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found in PATH.")

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = os.path.join(tmpdir, "audio.wav")
        cmd = [
            "ffmpeg",
            "-headers", "Referer: https://www.bilibili.com/\r\n",
            "-i", url,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            wav_path, "-y", "-loglevel", "quiet",
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError("ffmpeg audio extraction failed")

        if not quiet:
            print("Transcribing with mlx-whisper...")
        return transcribe_audio(wav_path, model=model, language=language)
