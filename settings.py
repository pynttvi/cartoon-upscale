SETTINGS = {
    # File info (to be filled in at runtime)
    "file_name": "EMPTY_FILE_NAME",
    "input_path": "EMPTY_INPUT_PATH",
    "working_dir": "EMPTY_WORKING_DIR",
    # Paths and models
    "working_dir_base": "/dev/shm",  # For orchestrator
    "waifu2x_path": "./waifu/waifu2x-ncnn-vulkan-20250504-ubuntu/waifu2x-ncnn-vulkan",
    "waifu_model": "models-upconv_7_anime_style_art_rgb",
    "rife_model": "rife-anime",
    "rife_path": "./rife/rife-ncnn-vulkan-20221029-ubuntu/rife-ncnn-vulkan",
    # Where to place final outputs
    "final_output_folder": "/mnt/m2/upscaled/",
    # Progress files
    "progress_file": "pipeline_progress.json",  # for main pipeline
    "batched_progress_file": "batched_progress.json",  # for splitting/orchestrator
    # Processing settings
    "scale": 2,
    "noise": 3,
    "primary_gpu": 1,
    "gpus_used_count": 2,
    "framerate": 25,
    "batch_size": 20,
    "threads": "2:1:9",
    "final_encoder": "h264",
}
