# Video Editing Studio

This repo is set up as a conversation-driven **video editing studio** for Claude Code.
Drop a raw video file in, describe the edit you want, and Claude takes it through the
full pipeline: transcribe → cut → remove filler words → color grade → motion graphics →
burned subtitles → `final.mp4`.

Two open-source, agent-native toolkits are vendored as skills under `.claude/skills/`:

| Toolkit | Source | Role in the pipeline |
| --- | --- | --- |
| **video-use** | [browser-use/video-use](https://github.com/browser-use/video-use) | The editor. Transcribes, finds/removes filler words and dead air, cuts on word boundaries, color grades, burns subtitles, renders. |
| **HyperFrames** | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | The motion-graphics engine. HTML/CSS/GSAP compositions rendered deterministically to MP4 — title cards, lower thirds, kinetic captions, animated overlays. |

video-use treats audio (the word-level transcript) as the source of truth and calls out
to an animation engine for overlays. HyperFrames is the primary animation engine of the four
it supports (HyperFrames, Remotion, Manim, PIL), so the two fit together as one pipeline.

## The pipeline

```
raw footage ──▶ video-use ────────────────────────────────▶ HyperFrames ──▶ video-use ──▶ final.mp4
               transcribe · cut · de-filler · grade          motion graphics   composite + burn subtitles
```

1. **Inventory & transcribe** — `ffprobe` + ElevenLabs Scribe produce a word-level,
   speaker-tagged transcript (`takes_packed.md`).
2. **Confirm a plan** — video-use proposes a strategy in plain English and waits for your
   OK before touching anything. *Ask → confirm → execute → iterate → persist.*
3. **Cut & clean** — filler words ("um", "uh", false starts) and dead air removed on word
   boundaries; 30 ms audio fades at every cut. Decisions live in `edl.json`.
4. **Grade** — per-segment color correction during extraction.
5. **Motion graphics** — overlays are built as HyperFrames compositions (parallel
   sub-agents for multiple animations) and composited as overlay tracks.
6. **Subtitles last** — styled captions burned in after overlays.
7. **Self-evaluate & render** — output checked at cut boundaries, then rendered to
   `<videos_dir>/edit/final.mp4`.

## How to use it

1. Put your raw clip(s) anywhere in the repo (e.g. a `videos/` folder you create, or any
   working folder). Sources are never modified — all work lands in an `edit/` subfolder.
2. Ask in plain language, e.g.:
   - *"Edit this into a tight 60-second launch video and cut all the ums."*
   - *"Remove the filler words and dead air, then add a title card and lower-third name tags."*
   - *"Add kinetic captions and a animated intro to this talking-head clip."*
3. Claude confirms the plan, executes, and shows a 720p preview before final render.

The `video-use` skill (`.claude/skills/video-use/SKILL.md`) holds the hard
production-correctness rules; the `hyperframes` skill family holds the motion-graphics
craft. Claude loads them on demand.

## Environment & dependencies

A **SessionStart hook** (`.claude/hooks/session-start.sh`, registered in
`.claude/settings.json`) prepares each Claude Code on the web session automatically:

- installs **ffmpeg / ffprobe** (required by both toolkits)
- installs the **video-use Python deps** (`requests`, `librosa`, `matplotlib`, `pillow`, `numpy`)
- verifies **Node ≥ 22** for HyperFrames (its CLI runs via `npx hyperframes`, no global install)

It's idempotent and only runs in remote sessions; on a local machine, install those three
yourself.

### API key for transcription

video-use transcribes with **ElevenLabs Scribe**, which needs an API key:

```bash
export ELEVENLABS_API_KEY=sk_...        # or add it to your environment config
```

No key? Use the bundled **local Whisper fallback** — it writes a transcript in the exact
shape the cutting pipeline expects (no ElevenLabs account needed):

```bash
uv pip install --system faster-whisper                                   # one-time
python .claude/skills/video-use/helpers/transcribe_local.py <clip.mp4>   # -> edit/transcripts/<clip>.json
python .claude/skills/video-use/helpers/pack_transcripts.py --edit-dir <clip_parent>/edit
```

The local path has **no speaker diarization** (single speaker assumed) and no audio-event
tags, but cutting and filler removal work the same since they key off word boundaries and
silence. ElevenLabs Scribe stays the recommended path for multi-speaker interviews because
of its word-level speaker IDs.

## Dropping footage

Put raw clips in `videos/` (or any folder) and ask in plain language. Sources are never
modified — all work lands in an `edit/` subfolder. Media files aren't committed to git
(see `videos/.gitignore`).

## Vendored skills

```
.claude/skills/
├── video-use/              # the editor (SKILL.md + helpers/ + nested manim-video skill)
├── hyperframes/            # motion-graphics authoring (HTML/CSS/GSAP compositions)
├── hyperframes-cli/        # init · lint · inspect · preview · render
├── hyperframes-media/      # TTS · transcribe · background removal
├── hyperframes-registry/   # install catalog blocks/components
├── gsap, css-animations, animejs, waapi,
│   lottie, three, typegpu, tailwind        # animation adapters
├── website-to-hyperframes  # turn a URL into a video
├── remotion-to-hyperframes # port a Remotion project
└── contribute-catalog      # contribute back to the HyperFrames registry
```

These are pinned copies. To update, re-pull from the upstream repos and copy their
`skills/` directories back into `.claude/skills/`.
