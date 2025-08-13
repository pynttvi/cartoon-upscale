#!/bin/bash

START_PART="$1"
MID_PART="$2"
END_PART="$3"
OUTPUT="$4"


LIST_FILE="concat_list.txt"
echo "file '$START_PART'" > "$LIST_FILE"
echo "file '$MID_PART'" >> "$LIST_FILE"

# Only add END_PART if provided
if [ -n "$END_PART" ] && [ "$END_PART" != "$OUTPUT" ]; then
  echo "file '$END_PART'" >> "$LIST_FILE"
fi

ffmpeg -f concat -safe 0 -i "$LIST_FILE" -c copy "$OUTPUT"

rm "$LIST_FILE"

echo "✅ Done! Output: $OUTPUT"
