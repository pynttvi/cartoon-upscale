# cartoon-upscale
Scripts to upscale cartoons with ffmpeg, waifu and rife. Batched pipeline splits original video in pieces to make temp files fit in ramdisk and joins them back together.

These scripts are used to upscale PAL dvd cartoons with NVIDIA RTX 2000 ADA and GeForce 2070, AMD Ryzen 7 9800X3D and 128G RAM

### Download and exctract waifu and rife
Current releases in time of creation

wget https://github.com/nihui/waifu2x-ncnn-vulkan/releases/download/20250504/waifu2x-ncnn-vulkan-20250504-ubuntu.zip -O waifu.zip
unzip waifu.zip -d waifu
rm waifu.zip
chmod +x waifu/waifu2x-ncnn-vulkan-20250504-ubuntu/waifu2x-ncnn-vulkan

wget https://github.com/nihui/rife-ncnn-vulkan/releases/download/20221029/rife-ncnn-vulkan-20221029-ubuntu.zip -O rife.zip
unzip rife.zip -d rife
rm rife.zip
chmod +x rife/rife-ncnn-vulkan-20221029-ubuntu/rife-ncnn-vulkan


### Running
python batched_pipeline.py /path/to/file.iso
or
python upscale_pipeline.py /path/to/file.iso
