import sys
from pathlib import Path

sys.path.insert(0, str(Path(".video_vendor").resolve()))

import imageio.v2 as imageio
from PIL import Image


video = "TLaser_promo_partner_video.mp4"
out_dir = Path("tlaser_promo_frame_check")
out_dir.mkdir(exist_ok=True)
reader = imageio.get_reader(video)
fps = reader.get_meta_data()["fps"]
for sec in [2, 24, 58, 86, 126, 170]:
    frame = reader.get_data(int(sec * fps))
    Image.fromarray(frame).save(out_dir / f"frame_{sec:03d}s.jpg", quality=90)
reader.close()
print(f"saved_frames={out_dir.resolve()}")
