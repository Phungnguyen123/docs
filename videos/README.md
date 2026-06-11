# Drop footage here

Put your raw clip(s) in this folder (or any working folder), then ask Claude to
edit them — e.g. *"cut all the ums and add a title card"*.

- **Sources are never modified.** All work lands in an `edit/` subfolder next to
  the source (transcripts, `takes_packed.md`, `edl.json`, graded clips, overlays,
  and the final render at `edit/final.mp4`).
- **Media is not committed to git.** The `.gitignore` in this folder keeps video
  files and render artifacts out of the repo — only this README is tracked.

## Transcription

The pipeline transcribes first. Two options:

- **ElevenLabs Scribe (recommended)** — word-level timestamps + speaker tags.
  Needs `ELEVENLABS_API_KEY` (in the environment, or in
  `.claude/skills/video-use/.env`).
- **Local Whisper (no key)** — run
  `python .claude/skills/video-use/helpers/transcribe_local.py <clip>`
  (first install: `uv pip install --system faster-whisper`). No speaker
  diarization, but fine for single-speaker / talking-head footage.

See the repo root `CLAUDE.md` for the full pipeline.
