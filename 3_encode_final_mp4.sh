#!/bin/bash
INPUT="$1"
CODEC="${2:-h264}"  # default to h264 if not specified
OUTFOLDER="$3"

if [ -z "$INPUT" ]; then
  echo "❌ Usage: $0 input.suffix [h264|h265] [optional_output_folder]"
  exit 1
fi

WORKDIR_BASE="/dev/shm"
NAME=$(basename "$INPUT" )
STEM="${NAME%.*}"
WORKDIR="$WORKDIR_BASE/work_$STEM"
cd "$WORKDIR" || exit 1

FRAMERATE=50

if [ "$CODEC" == "h264" ]; then
  echo "[Encoding to H.264 with NVENC...]"
  ffmpeg -framerate $FRAMERATE -pattern_type glob -i "interpolated/*.png" \
    -vf "tblend=all_mode=average,framestep=2" -r 25 -c:v h264_nvenc -pix_fmt yuv420p "tmp_${STEM}_upscaled.mp4"
elif [ "$CODEC" == "h265" ]; then
  echo "[Encoding to H.265 with NVENC...]"
  ffmpeg -framerate $FRAMERATE -pattern_type glob -i "interpolated/*.png" \
    -c:v hevc_nvenc -preset p4 -rc vbr -cq 23 -b:v 0 -pix_fmt yuv420p -movflags +faststart "tmp_${STEM}_upscaled.mp4"
else
  echo "❌ Invalid codec: $CODEC. Use 'h264' or 'h265'."
  exit 1
fi

# === [2] Add audio ===
ffmpeg -i "tmp_${STEM}_upscaled.mp4" -i preprocessed/clean.mp4 -c copy -map 0:v:0 -map 1:a:0? "${STEM}_upscaled.mp4"
rm tmp_${STEM}_upscaled.mp4

# === [3] Move to output folder if specified ===
if [ -n "$OUTFOLDER" ] && [ -d "$OUTFOLDER" ]; then
  echo "📦 Moving output to $OUTFOLDER/"
  mv "${STEM}_upscaled.mp4" "$OUTFOLDER/${STEM}.mp4"
  FINAL_PATH="${OUTFOLDER}/${STEM}.mp4"
else
  FINAL_PATH="${WORKDIR}/${STEM}.mp4"
fi

echo "✅ Done! Output video: $FINAL_PATH"
