#!/bin/bash

# Usage: ./convert_h265_to_h264.sh /path/to/input /path/to/output

INPUT_DIR="$1"
OUTPUT_DIR="$2"

if [ -z "$INPUT_DIR" ] || [ -z "$OUTPUT_DIR" ]; then
  echo "Usage: $0 /path/to/input /path/to/output"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

for FILE in "$INPUT_DIR"/*.mp4; do
  BASENAME=$(basename "$FILE")
  OUTPUT_FILE="$OUTPUT_DIR/$BASENAME"
  echo "Converting $FILE to $OUTPUT_FILE"
  #ffmpeg -i "$FILE" -vf "deband,hqdn3d=1.5:1.5:6:6,unsharp=5:5:0.7:5:5:0.0" -c:v libx264 -crf 20 -preset fast -c:a copy "$OUTPUT_FILE"
  #ffmpeg -i "$FILE"-vf "deflicker,tblend=all_mode=average" -r 25 "$OUTPUT_FILE"
  # Convert to h264
  #ffmpeg -i "$FILE" -c:v libx264 -preset fast -crf 23 -c:a copy "$OUTPUT_FILE"
done
