import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".video_vendor").resolve()))

import imageio_ffmpeg


src = Path("TLaser_promo_partner_video.mp4")
dst = Path("TLaser_promo_partner_video_720p_share.mp4")
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
cmd = [
    ffmpeg,
    "-y",
    "-i",
    str(src),
    "-c:v",
    "libx264",
    "-preset",
    "slow",
    "-crf",
    "26",
    "-pix_fmt",
    "yuv420p",
    "-movflags",
    "+faststart",
    "-an",
    str(dst),
]
subprocess.run(cmd, check=True)
print(f"saved={dst.resolve()}")
