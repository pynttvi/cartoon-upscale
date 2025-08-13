#!/usr/bin/env python3

import os
import json
import subprocess
from pathlib import Path
import time
import sys
from settings import SETTINGS


if len(sys.argv) < 2:
    print("❌ Usage: {} <input.iso or input.mp4>".format(sys.argv[0]))
    exit(1)

# Usage: waifu2x-ncnn-vulkan -i infile -o outfile [options]...
#
#  -h                   show this help
#  -v                   verbose output
#  -i input-path        input image path (jpg/png/webp) or directory
#  -o output-path       output image path (jpg/png/webp) or directory
#  -n noise-level       denoise level (-1/0/1/2/3, default=0)
#  -s scale             upscale ratio (1/2/4/8/16/32, default=2)
#  -t tile-size         tile size (>=32/0=auto, default=0) can be 0,0,0 for multi-gpu
#  -m model-path        waifu2x model path (default=models-cunet)
#  -g gpu-id            gpu device to use (-1=cpu, default=auto) can be 0,1,2 for multi-gpu
#  -j load:proc:save    thread count for load/proc/save (default=1:2:2) can be 1:2,2,2:2 for multi-gpu
#  -x                   enable tta mode
#  -f format            output image format (jpg/png/webp, default=ext/png)


# Usage: rife-ncnn-vulkan -0 infile -1 infile1 -o outfile [options]...
#        rife-ncnn-vulkan -i indir -o outdir [options]...

#   -h                   show this help
#   -v                   verbose output
#   -0 input0-path       input image0 path (jpg/png/webp)
#   -1 input1-path       input image1 path (jpg/png/webp)
#   -i input-path        input image directory (jpg/png/webp)
#   -o output-path       output image path (jpg/png/webp) or directory
#   -n num-frame         target frame count (default=N*2)
#   -s time-step         time step (0~1, default=0.5)
#   -m model-path        rife model path (default=rife-v2.3)
#   -g gpu-id            gpu device to use (-1=cpu, default=auto) can be 0,1,2 for multi-gpu
#   -j load:proc:save    thread count for load/proc/save (default=1:2:2) can be 1:2,2,2:2 for multi-gpu
#   -x                   enable spatial tta mode
#   -z                   enable temporal tta mode
#   -u                   enable UHD mode
#   -f pattern-format    output image filename pattern format (%08d.jpg/png/webp, default=ext/%08d.png)


# === HELPER FUNCTIONS ===
def load_progress():
    if Path(SETTINGS["working_dir"], SETTINGS["progress_file"]).exists():
        with open(Path(SETTINGS["working_dir"], SETTINGS["progress_file"])) as f:
            return json.load(f)
    return {"processed": []}


def save_progress(progress):
    with open(Path(SETTINGS["working_dir"], SETTINGS["progress_file"]), "w") as f:
        json.dump(progress, f, indent=2)


def run_command(cmd, shell=False, hide_output=False):
    if hide_output:
        subprocess.run(
            cmd,
            shell=shell,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        print(f"▶️ Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        subprocess.run(cmd, shell=shell, check=True)


# === STEP 1: Extract DVD to MP4 ===
def extract_dvd():
    run_command(["bash", "0_extract_dvd_to_mp4.sh", SETTINGS["input_path"]])


# === OR 1: Preprocess mp4 ===
def preprocess_mp4():
    run_command(["bash", "1_preprocess_mp4.sh", SETTINGS["input_path"]])


# === STEP 2: Extract Frames ===
def extract_frames():
    run_command(["bash", "2_extract_frames.sh", SETTINGS["input_path"]])


# === STEP 3: Upscale Frames in Batches ===
def upscale_frames():
    input_dir = Path(SETTINGS["working_dir"]) / "frames"
    output_dir = Path(SETTINGS["working_dir"]) / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        SETTINGS["waifu2x_path"],
        "-i",
        str(input_dir),
        "-o",
        str(output_dir),
        "-n",
        str(SETTINGS["noise"]),
        "-s",
        str(SETTINGS["scale"]),
        "-m",
        SETTINGS["waifu_model"],
        "-g",
        str(SETTINGS["primary_gpu"]),
        "-j",
        str(SETTINGS["threads"]),
    ]
    print(f"▶️ Upscaling entire folder: {input_dir} → {output_dir}")
    run_command(cmd, hide_output=False)  # Show output for debugging

    run_command(["rm", "-rf", str(input_dir)])
    print("✅ Folder upscaling complete.")


# === STEP 4: Interpolate frames ===
def interpolate_frames():
    input_dir = Path(SETTINGS["working_dir"]) / "output"
    output_dir = Path(SETTINGS["working_dir"]) / "interpolated"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        SETTINGS["rife_path"],
        "-i",
        str(input_dir),
        "-o",
        str(output_dir),
        "-m",
        SETTINGS.get("rife_model", "rife-anime"),
        "-g",
        str(SETTINGS["primary_gpu"]),
        "-j",
        str(SETTINGS["threads"]),
    ]
    print(f"▶️ Interpolating entire folder: {input_dir} → {output_dir}")
    run_command(cmd, hide_output=False)  # Show output for debugging

    print("✅ Folder interpolation complete.")


# === STEP 5: Encode Final MP4 ===
def encode_video():
    run_command(
        [
            "bash",
            "3_encode_final_mp4.sh",
            SETTINGS["input_path"],
            SETTINGS["final_encoder"],
            SETTINGS["final_output_folder"],
        ]
    )


# === MAIN ===
if __name__ == "__main__":
    import sys

    task_start = time.time()
    if len(sys.argv) < 2:
        print("❌ Usage: {} <input.iso or input.mp4>".format(sys.argv[0]))
        exit(1)

    if len(sys.argv) > 2:
        SETTINGS["primary_gpu"] = sys.argv[2]
    elif os.environ.get("GPU"):
        SETTINGS["primary_gpu"] = os.environ["GPU"]

    SETTINGS["input_path"] = sys.argv[1]
    NAME = Path(SETTINGS["input_path"]).stem
    SETTINGS["file_name"] = NAME
    SETTINGS["working_dir"] = os.path.abspath(
        Path(SETTINGS["working_dir_base"], f"work_{NAME}")
    )

    # Comment/uncomment steps as needed
    # extract_dvd()
    preprocess_mp4()
    extract_frames()
    upscale_frames()
    interpolate_frames()
    encode_video()

    task_end = time.time()
    elapsed = task_end - task_start

    hours, remainder = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(remainder, 60)
    print(
        f"⏱️ Upscale Pipeline task done in {hours}h {minutes}m {seconds}s ({elapsed:.2f} sec)."
    )
