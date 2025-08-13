import json
import math
import os
import subprocess
import tempfile
from glob import glob
from pathlib import Path
from typing import Optional, Dict, Any


def _run(cmd):
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True
    )


def _human(bytes_val: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    v = float(bytes_val)
    while v >= 1024 and i < len(units) - 1:
        v /= 1024.0
        i += 1
    return f"{v:.2f} {units[i]}"


def _probe(video_path: str) -> Dict[str, Any]:
    """
    Returns dict with width, height, fps, duration_seconds.
    Requires ffprobe in PATH.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        video_path,
    ]
    res = _run(cmd)
    data = json.loads(res.stdout)

    stream = data["streams"][0]
    fmt = data["format"]

    width = int(stream["width"])
    height = int(stream["height"])

    afr = stream.get("avg_frame_rate", "0/1")
    num, den = afr.split("/")
    fps = float(num) / float(den) if float(den) != 0 else 0.0

    duration = float(fmt.get("duration", 0.0))
    return {"width": width, "height": height, "fps": fps, "duration_seconds": duration}


def estimate_png_frames_size(
    video_path: str,
    sample_seconds: int = 5,
    png_pattern: str = "frame_%06d.png",
    assumed_png_ratio: float = 0.5,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Estimate disk space for extracting PNG frames with:
        ffmpeg -i <video> frames/frame_%06d.png
    Notes:
    - PNG ignores -qscale; size depends on resolution & content.
    - If `sample_seconds` > 0, we extract a short sample to measure average PNG size.
    - If sampling fails, we fall back to a heuristic (raw RGB * assumed_png_ratio).

    Parameters
    ----------
    video_path : str
        Path to the input video.
    sample_seconds : int
        How many seconds to sample for measuring real PNG sizes. Set to 0 to skip sampling.
    png_pattern : str
        Output naming pattern (only used for sampling). Must end with .png.
    assumed_png_ratio : float
        Fallback ratio: estimated_png_size_per_frame ≈ raw_rgb_bytes_per_frame * ratio.
        Typical range 0.3–0.7; default 0.5.
    verbose : bool
        Print a few details.

    Returns
    -------
    dict with:
      - width, height, fps, duration_seconds, total_frames
      - avg_frame_size_bytes (measured or estimated)
      - estimated_total_bytes
      - human_readable fields for convenience
      - method: "sampled" or "heuristic"
    """
    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    info = _probe(video_path)
    width, height, fps, duration = (
        info["width"],
        info["height"],
        info["fps"],
        info["duration_seconds"],
    )
    total_frames = int(round(fps * duration)) if fps and duration else 0

    if verbose:
        print(
            f"Probed: {width}x{height}, {fps:.3f} fps, {duration:.3f} s, ~{total_frames} frames"
        )

    avg_frame_size_bytes = None
    method = "heuristic"

    # Try sampling if requested
    if sample_seconds and sample_seconds > 0 and total_frames > 0:
        try:
            with tempfile.TemporaryDirectory() as td:
                out_pattern = str(Path(td) / png_pattern)
                # Extract up to sample_seconds from the start (quiet errors)
                cmd = [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    video_path,
                    "-t",
                    str(sample_seconds),
                    out_pattern,
                ]
                _run(cmd)

                files = sorted(glob(str(Path(td) / "*.png")))
                if files:
                    sizes = [os.path.getsize(f) for f in files]
                    avg_frame_size_bytes = sum(sizes) / len(sizes)
                    method = "sampled"
                    if verbose:
                        print(
                            f"Sampled {len(files)} frames, avg {avg_frame_size_bytes:.1f} bytes"
                        )
        except Exception as e:
            if verbose:
                print(f"Sampling failed ({e}); using heuristic.")

    # Heuristic fallback
    if avg_frame_size_bytes is None:
        raw_rgb_per_frame = width * height * 3  # 8-bit RGB
        avg_frame_size_bytes = raw_rgb_per_frame * assumed_png_ratio
        if verbose:
            print(
                f"Heuristic avg frame size ≈ {_human(avg_frame_size_bytes)} "
                f"(ratio={assumed_png_ratio})"
            )

    estimated_total_bytes = avg_frame_size_bytes * max(total_frames, 0)

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "duration_seconds": duration,
        "total_frames": total_frames,
        "avg_frame_size_bytes": avg_frame_size_bytes,
        "avg_frame_size_human": _human(avg_frame_size_bytes),
        "estimated_total_bytes": estimated_total_bytes,
        "estimated_total_human": _human(estimated_total_bytes),
        "method": method,
    }


def get_shm_stats(path: str = "/dev/shm"):
    """
    Return total and available bytes for a tmpfs-like mount (e.g., /dev/shm).
    """
    st = os.statvfs(path)
    total = st.f_frsize * st.f_blocks
    avail = st.f_frsize * st.f_bavail
    return {"path": path, "total_bytes": total, "available_bytes": avail}


def plan_chunks_for_shm(
    video_path: str,
    safety_multiplier: float = 3,
    sample_seconds: int = 5,
    assumed_png_ratio: float = 0.5,
    shm_path: str = "/dev/shm",
    verbose: bool = False,
):
    """
    Plan how many pieces to cut the video into so that PNG frames for each piece
    fit into /dev/shm, assuming you need `safety_multiplier` × frames size
    available in shm (default 1.5x).

    Returns a dict with:
      - shm_total_bytes, shm_available_bytes
      - estimated_total_bytes (PNG), avg_frame_size_bytes
      - allowed_bytes_per_chunk (PNG payload per chunk)
      - frames_per_chunk, seconds_per_chunk
      - num_chunks, total_frames, fps, duration_seconds
    """
    # 1) Size estimate (reuses probe+sampling/heuristic)
    est = estimate_png_frames_size(
        video_path,
        sample_seconds=sample_seconds,
        assumed_png_ratio=assumed_png_ratio,
        verbose=verbose,
    )

    # 2) SHM capacity
    shm = get_shm_stats(shm_path)
    shm_avail = shm["available_bytes"]
    if shm_avail <= 0:
        raise RuntimeError(f"No available space on {shm_path}")

    # 3) How many PNG bytes can a single chunk use?
    # Need safety_multiplier * (chunk_png_bytes) <= shm_avail
    allowed_bytes_per_chunk = math.floor(shm_avail / safety_multiplier)
    if allowed_bytes_per_chunk <= 0:
        raise RuntimeError(
            f"Available space on {shm_path} ({_human(shm_avail)}) is too small "
            f"for safety multiplier {safety_multiplier}."
        )

    avg_frame = est["avg_frame_size_bytes"]
    total_frames = max(1, est["total_frames"])  # avoid div-by-zero later
    fps = est["fps"] or 0.0
    duration = est["duration_seconds"] or 0.0

    # 4) Frames per chunk (at least 1)
    frames_per_chunk = max(1, allowed_bytes_per_chunk // max(1, int(avg_frame)))
    num_chunks = math.ceil(total_frames / frames_per_chunk)

    # 5) Seconds per chunk (use fps if available)
    seconds_per_chunk = (frames_per_chunk / fps) if fps > 0 else None

    # 6) Final packaging
    result = {
        "shm_path": shm_path,
        "shm_total_bytes": shm["total_bytes"],
        "shm_available_bytes": shm_avail,
        "required_multiplier": safety_multiplier,
        "avg_frame_size_bytes": avg_frame,
        "avg_frame_size_human": _human(avg_frame),
        "estimated_total_bytes": est["estimated_total_bytes"],
        "estimated_total_human": est["estimated_total_human"],
        "allowed_bytes_per_chunk": allowed_bytes_per_chunk,
        "allowed_bytes_per_chunk_human": _human(allowed_bytes_per_chunk),
        "total_frames": total_frames,
        "fps": fps,
        "duration_seconds": duration,
        "frames_per_chunk": int(frames_per_chunk),
        "seconds_per_chunk": seconds_per_chunk,
        "seconds_per_chunk_human": (
            _human(seconds_per_chunk) if seconds_per_chunk else None
        ),
        "num_chunks": int(num_chunks),
        "estimation_method": est["method"],
    }

    if verbose:
        print(
            f"SHM available: {_human(shm_avail)} | "
            f"Allowed per chunk (PNG): {_human(allowed_bytes_per_chunk)} | "
            f"Frames/chunk: {result['frames_per_chunk']} | "
            f"Chunks: {result['num_chunks']}"
        )
        if seconds_per_chunk:
            print(f"~{seconds_per_chunk:.2f} s per chunk at {fps:.3f} fps")

    return result


# --- Example usage ---
# plan = plan_chunks_for_shm(
#     "preprocessed/clean.mp4",
#     safety_multiplier=1.5,
#     sample_seconds=5,
#     verbose=True,
# )
# print(plan["num_chunks"], "chunks")
