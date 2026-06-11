#!/bin/bash
# SessionStart hook — prepares this repo as a video editing studio.
# Installs the system + language deps that video-use and HyperFrames need.
# Idempotent: safe to run every session; skips work that's already done.
set -euo pipefail

# Only run in Claude Code on the web (remote) sessions. On a local machine
# you manage these tools yourself.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

log() { echo "[studio-setup] $*"; }

# --- 1. ffmpeg / ffprobe (required by both video-use and HyperFrames) ---
if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
  log "ffmpeg already present: $(ffmpeg -version | head -1)"
else
  log "installing ffmpeg..."
  export DEBIAN_FRONTEND=noninteractive
  # Try the package cache directly first — it's usually warm and avoids
  # `apt-get update`, which can fail on blocked third-party PPAs.
  if ! apt-get install -y -qq ffmpeg >/dev/null 2>&1; then
    log "cache install failed; refreshing main repos (ignoring PPAs)..."
    apt-get update -qq -o Dir::Etc::sourceparts="-" >/dev/null 2>&1 || true
    apt-get install -y -qq ffmpeg >/dev/null
  fi
  log "ffmpeg installed: $(ffmpeg -version | head -1)"
fi

# --- 2. video-use Python deps (transcript packing, waveforms, grading) ---
# Installed system-wide so the helpers run with plain `python3`.
log "installing video-use Python deps..."
uv pip install --system --quiet \
  requests librosa matplotlib pillow numpy
log "Python deps ready."

# --- 3. Verify Node / npx for HyperFrames (CLI runs via `npx hyperframes`) ---
if command -v node >/dev/null 2>&1; then
  NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
  if [ "$NODE_MAJOR" -lt 22 ]; then
    log "WARNING: HyperFrames needs Node >= 22, found $(node --version)"
  else
    log "node ok: $(node --version)"
  fi
else
  log "WARNING: node not found — HyperFrames (npx hyperframes) will not run"
fi

log "studio ready: drop footage in a folder and ask Claude to edit it."
