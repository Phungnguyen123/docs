"""Local, no-API-key transcription fallback for video-use.

Drop-in alternative to `helpers/transcribe.py` when no ELEVENLABS_API_KEY is
available. Runs faster-whisper locally and writes a transcript JSON in the
SAME shape video-use's `pack_transcripts.py` expects — a `words` list whose
entries are typed `word` / `spacing`, each with `start`/`end`, so phrase
grouping on silence still works.

Differences vs ElevenLabs Scribe:
  - No speaker diarization. `speaker_id` is null on every word, so the packed
    transcript won't carry S0/S1 tags. Cutting still works (it keys off word
    boundaries and silence gaps, not speakers).
  - No audio-event tagging (no "(laughs)" etc.).
For talking-head / single-speaker footage this is usually plenty. For
multi-speaker interviews, Scribe is still the better path.

Requires faster-whisper (not in the default session hook — install on demand):
    uv pip install --system faster-whisper

Usage:
    python helpers/transcribe_local.py <video_path>
    python helpers/transcribe_local.py <video_path> --edit-dir /custom/edit
    python helpers/transcribe_local.py <video_path> --language en
    python helpers/transcribe_local.py <video_path> --model small
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def extract_audio(video_path: Path, dest: Path) -> None:
    """Mono 16 kHz PCM wav — same as the Scribe path expects."""
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def build_words(segments) -> tuple[list[dict], str]:
    """Flatten faster-whisper segments into a Scribe-shaped `words` list.

    Emits a `spacing` entry for the gap between each consecutive word so that
    pack_transcripts can break phrases on silence exactly as it does for Scribe.
    """
    words: list[dict] = []
    texts: list[str] = []
    prev_end: float | None = None

    for seg in segments:
        for w in (seg.words or []):
            start = float(w.start)
            end = float(w.end)
            text = w.word.strip()
            if not text:
                continue
            if prev_end is not None and start > prev_end:
                # gap between words -> spacing entry carrying the silence
                words.append({"type": "spacing", "text": " ", "start": prev_end, "end": start})
            words.append({
                "type": "word",
                "text": text,
                "start": start,
                "end": end,
                "speaker_id": None,
            })
            texts.append(text)
            prev_end = end

    return words, " ".join(texts)


def transcribe_one(
    video: Path,
    edit_dir: Path,
    language: str | None = None,
    model_size: str = "base",
    verbose: bool = True,
) -> Path:
    """Transcribe a single video locally. Returns path to transcript JSON.

    Cached: returns the existing path immediately if the transcript exists,
    so it never re-transcribes an unchanged source.
    """
    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcripts_dir / f"{video.stem}.json"

    if out_path.exists():
        if verbose:
            print(f"cached: {out_path.name}")
        return out_path

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit(
            "faster-whisper not installed. Run:\n"
            "    uv pip install --system faster-whisper"
        )

    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{video.stem}.wav"
        if verbose:
            print(f"  extracting audio from {video.name}", flush=True)
        extract_audio(video, audio)

        if verbose:
            print(f"  loading whisper model '{model_size}' (downloads on first run)", flush=True)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        if verbose:
            print("  transcribing locally...", flush=True)
        segments, info = model.transcribe(
            str(audio),
            language=language,
            word_timestamps=True,
            vad_filter=True,
        )
        words, full_text = build_words(segments)

    payload = {
        "language_code": getattr(info, "language", language) or "",
        "text": full_text,
        "words": words,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    dt = time.time() - t0

    if verbose:
        kb = out_path.stat().st_size / 1024
        word_count = sum(1 for w in words if w["type"] == "word")
        print(f"  saved: {out_path.name} ({kb:.1f} KB) in {dt:.1f}s")
        print(f"    words: {word_count}  (no speaker tags — local fallback)")

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Transcribe a video locally with faster-whisper (no API key)"
    )
    ap.add_argument("video", type=Path, help="Path to video file")
    ap.add_argument(
        "--edit-dir", type=Path, default=None,
        help="Edit output directory (default: <video_parent>/edit)",
    )
    ap.add_argument(
        "--language", type=str, default=None,
        help="Optional ISO language code (e.g., 'en'). Omit to auto-detect.",
    )
    ap.add_argument(
        "--model", type=str, default="base",
        help="Whisper model size: tiny|base|small|medium|large-v3 (default: base)",
    )
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")

    edit_dir = (args.edit_dir or (video.parent / "edit")).resolve()
    transcribe_one(
        video=video,
        edit_dir=edit_dir,
        language=args.language,
        model_size=args.model,
    )


if __name__ == "__main__":
    main()
