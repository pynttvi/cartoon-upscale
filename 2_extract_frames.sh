#!/bin/bash
INPUT="$1"
if [ -z "$INPUT" ]; then
  echo "❌ Usage: $0 /path/to/input"
  exit 1
fi

WORKDIR_BASE="/dev/shm"
NAME=$(basename "$INPUT" )
STEM="${NAME%.*}"
WORKDIR="$WORKDIR_BASE/work_$STEM"
cd "$WORKDIR" || exit 1

# === [1] EXCTRACT FRAMES ===
echo "[Extracting frames from cleaned video...]"
mkdir -p frames
ffmpeg -i preprocessed/clean.mp4 -qscale:v 1 frames/frame_%06d.png
