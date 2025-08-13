import os
import sys
import subprocess
from pathlib import Path
import json
import shutil
import time
from settings import SETTINGS
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import tempfile

from util.estimate_png_frames_size import plan_chunks_for_shm


def load_progress():
    pf = Path(SETTINGS["working_dir"]) / SETTINGS["batched_progress_file"]
    if pf.exists():
        with open(pf) as f:
            return json.load(f)
    # If not found, initialize with empty progress
    return {
        "splits_done": [],
        "parts_processed": [],
        "joined": False,
    }


def save_progress(progress):
    pf = Path(SETTINGS["working_dir"]) / SETTINGS["batched_progress_file"]
    with open(pf, "w") as f:
        json.dump(progress, f, indent=2)


def split_video(input_path, pieces, split_dir):
    # Get duration
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(input_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    duration = float(result.stdout.strip())
    piece_len = duration / pieces

    split_paths = []

    for i in range(pieces):
        part_path = Path(split_dir) / f"input_part_{i+1:02d}.mp4"
        start = i * piece_len
        split_args = ["ffmpeg", "-y", "-ss", str(start), "-i", str(input_path)]
        if i < pieces - 1:
            split_args += ["-t", str(piece_len)]
        # H.265 (HEVC) re-encode for clean, accurate split
        split_args += [
            "-c:v",
            "hevc_nvenc",
            "-c:a",
            "aac",
            "-preset",
            "fast",
            "-crf",
            "23",
            str(part_path),
        ]
        subprocess.run(split_args, check=True)
        split_paths.append(str(part_path))

    return split_paths


def join_videos(
    parts_folder, output_path, delete_parts=True, pattern=r"input_part_\d{2}\.mp4"
):
    # Find, filter, and sort part files
    parts_folder = Path(parts_folder)
    part_files = [
        f for f in parts_folder.glob("*.mp4") if re.fullmatch(pattern, f.name)
    ]
    part_files.sort(key=lambda f: int(re.search(r"(\d{2})", f.name).group(1)))

    clean_files = [str(f) for f in part_files if f.is_file()]

    if not clean_files:
        print("No video parts found to join!")
        return

    with tempfile.NamedTemporaryFile("w", delete=False) as tf:
        for part in clean_files:
            tf.write(f"file '{os.path.abspath(part)}'\n")
        temp_path = tf.name

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                temp_path,
                "-c",
                "copy",
                str(output_path),
            ],
            check=True,
        )
        print(f"✅ Joined {len(clean_files)} parts into {output_path}")
    finally:
        os.unlink(temp_path)

    # --- Delete part files, if wanted
    if delete_parts:
        for f in clean_files:
            try:
                Path(f).unlink()
                print(f"🗑️ Deleted split part: {f}")
            except Exception as e:
                print(f"⚠️ Could not delete split part {f}: {e}")


gpu_id = SETTINGS["primary_gpu"]


def process_part(idx, part):
    global gpu_id
    gpu_id = str((gpu_id + 1) % SETTINGS["gpus_used_count"])
    env = os.environ.copy()
    env["GPU"] = gpu_id  # Only if your pipeline uses this (see below!)

    print(f"\n=== Processing part {idx+1} on GPU {gpu_id} ===")
    subprocess.run(
        ["python3", "upscale_pipeline.py", part, gpu_id],
        env=env,
        check=True,
    )

    # === Remove work folder for this part ===
    part_name = Path(part).stem
    part_workdir = Path(SETTINGS["working_dir_base"], f"work_{part_name}")
    if part_workdir.exists():
        print(f"🧹 Deleting work folder for {part_name}: {part_workdir}")
        shutil.rmtree(part_workdir, ignore_errors=True)
    else:
        print(f"⚠️ Work folder not found: {part_workdir}")

    # === Remove split .mp4 part after processing ===
    try:
        Path(part).unlink()
        print(f"🗑️ Deleted split part: {part}")
    except Exception as e:
        print(f"⚠️ Could not delete split part {part}: {e}")


# --- Example usage:
if __name__ == "__main__":
    task_start = time.time()
    if len(sys.argv) < 2:
        print("Usage: pipeline.py <input.mp4> (<pieces>)")
        sys.exit(1)

    input_video = Path(sys.argv[1])

    if len(sys.argv) < 3:
        pieces = (
            plan_chunks_for_shm(video_path=input_video, safety_multiplier=4)[
                "num_chunks"
            ]
            * SETTINGS["gpus_used_count"]
            + 1
        )
        print(f"Chunks needed: {pieces}")
    else:
        pieces = int(sys.argv[2])

    NAME = input_video.stem
    SETTINGS["file_name"] = NAME
    working_dir = os.path.abspath(Path(SETTINGS["working_dir_base"], f"work_{NAME}"))
    SETTINGS["working_dir"] = working_dir

    # 1. Split video
    split_dir = Path(working_dir, "splits")
    split_dir.mkdir(exist_ok=True, parents=True)
    parts = split_video(input_video, pieces, split_dir)
    print("Splits:", parts)

    # 2. Process each part (call your full pipeline here)
    with ThreadPoolExecutor(max_workers=SETTINGS["gpus_used_count"]) as executor:
        futures = []
        for idx, part in enumerate(parts):
            futures.append(executor.submit(process_part, idx, part))
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                print(f"❌ Error in parallel part: {e}")

        # 3. Join all encoded pieces (assume output is in OUTFOLDER, update as needed)
        processed_parts = [
            f"{SETTINGS["final_output_folder"]}/{Path(p).stem}.mp4" for p in parts
        ]
        final_out = Path(SETTINGS["final_output_folder"], f"{input_video.stem}.mp4")
    join_videos(
        SETTINGS["final_output_folder"],
        str(Path(SETTINGS["final_output_folder"], f"{NAME}.mp4")),
    )
    print(f"\n✅ Final joined output: {NAME}.mp4")

    task_end = time.time()
    elapsed = task_end - task_start

    hours, remainder = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(remainder, 60)
    print(
        f"⏱️ Batched Pipeline task done in {hours}h {minutes}m {seconds}s ({elapsed:.2f} sec)."
    )
