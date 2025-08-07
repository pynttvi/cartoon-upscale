#!/bin/bash
INPUT="$1"
if [ -z "$INPUT" ]; then
  echo "❌ Usage: $0 /path/to/mp4"
  exit 1
fi

WORKDIR_BASE="/dev/shm"
NAME=$(basename "$INPUT" )
STEM="${NAME%.*}"
WORKDIR="$WORKDIR_BASE/work_$STEM"

mkdir -p "$WORKDIR"

cd "$WORKDIR" || exit 1

# === [1] PREPROCESS VIDEO ===
echo "🏃[1/5] Preprocessing video..."
mkdir -p preprocessed

#ffmpeg -i "$INPUT" -vf "yadif,hqdn3d,gradfun=strength=0.6, scale=iw:ih,format=yuv420p,deflicker,tblend=all_mode=average" \
ffmpeg -i "$INPUT" -vf "yadif,hqdn3d,gradfun=strength=0.6,deflicker,scale=iw:ih,format=yuv420p" \
  -c:v hevc_nvenc -preset fast -crf 23 preprocessed/clean.mp4