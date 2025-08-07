#!/bin/bash
# Use only if you run upscale_pipeline directly
ISO="$1"
if [ -z "$ISO" ]; then
  echo "❌ Usage: $0 input.iso"
  exit 1
fi
WORKDIR_BASE="/dev/shm"
NAME=$(basename "$ISO" .iso)
WORKDIR="$WORKDIR_BASE/work_$NAME"
mkdir -p "$WORKDIR"
cd "$WORKDIR" || exit 1

echo "[1/3] Extracting ISO..."
7z x "$ISO" -odvdmount

echo "[2/3] Extracting VOBs..."
mkdir -p working
find dvdmount/VIDEO_TS -maxdepth 1 -type f -name "VTS_*.VOB" | grep -v '_0\.VOB' | sort > vob_list.txt
rm -f filelist.txt
while read -r vob; do echo "file '$vob'" >> filelist.txt; done < vob_list.txt
ffmpeg -f concat -safe 0 -i filelist.txt -c copy working/raw.mpg

echo "[3/3] Deinterlacing and denoising..."
ffmpeg -i working/raw.mpg -vf "yadif,hqdn3d,gradfun=strength=0.6,deflicker,scale=iw:ih,format=yuv420p" \
  -c:v hevc_nvenc -preset p4 -cq 23 working/clean.mp4

echo "✅ DVD extraction complete."
