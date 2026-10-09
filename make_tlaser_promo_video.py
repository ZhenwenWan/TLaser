import math
import os
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(".video_vendor").resolve()))

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


W, H = 1280, 720
FPS = 8
OUT = Path("TLaser_promo_partner_video.mp4")
STORYBOARD = Path("TLaser_promo_storyboard.txt")

ASSET_DIR = Path(r"C:\Users\aw4wz\Documents\Codex\Lasers\Pages")
LOCAL_DIR = Path(r"C:\Users\aw4wz\Documents\Codex\TLaser")

ASSETS = {
    "module": ASSET_DIR / "optical_module_3d.jpg",
    "internals": ASSET_DIR / "exploded_module_internals.jpg",
    "chip": ASSET_DIR / "laser_chip_zoom.jpg",
    "live": ASSET_DIR / "3d_live_laser_chip.jpg",
    "long": ASSET_DIR / "3d_transparent_longitudinal_slice.jpg",
    "trans": ASSET_DIR / "3d_transparent_transverse_slice.jpg",
    "plaser": ASSET_DIR / "plaser_physics_schematic.jpg",
    "inverse": ASSET_DIR / "tlaser_inverse_workflow.jpg",
    "train": ASSET_DIR / "pinn_training_loss.png",
    "calibration": ASSET_DIR / "calibration_fit.png",
    "mobile_cover": ASSET_DIR / "tlaser_mobile_post_cn.jpg",
    "dashboard": LOCAL_DIR / "docs" / "mobile_post" / "dashboard_mobile.png",
}


def font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


FONT_TITLE = font(50, True)
FONT_H1 = font(34, True)
FONT_H2 = font(27, True)
FONT_BODY = font(23)
FONT_SMALL = font(18)
FONT_TINY = font(15)


def load_cover(path, t=0.0, zoom=1.08):
    img = Image.open(path).convert("RGB")
    iw, ih = img.size
    scale = max(W / iw, H / ih) * (1.0 + (zoom - 1.0) * t)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    # Gentle pan to keep still imagery alive without inventing visuals.
    max_x = max(0, nw - W)
    max_y = max(0, nh - H)
    x = int(max_x * (0.5 + 0.35 * math.sin((t - 0.5) * math.pi)))
    y = int(max_y * (0.5 + 0.25 * math.cos(t * math.pi)))
    img = img.crop((x, y, x + W, y + H))
    img = ImageEnhance.Contrast(img).enhance(1.05)
    return img


_OVERLAY = None


def gradient_overlay(img, left_alpha=170, bottom_alpha=120):
    global _OVERLAY
    if _OVERLAY is None:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pix = overlay.load()
        for y in range(H):
            for x in range(W):
                a = int(max(left_alpha * (1 - x / W) ** 1.8, bottom_alpha * (y / H) ** 2.0))
                pix[x, y] = (3, 8, 18, min(210, a))
        _OVERLAY = overlay
    return Image.alpha_composite(img.convert("RGBA"), _OVERLAY).convert("RGB")


def text_box(draw, xy, lines, title=None, width=760, fill=(8, 16, 30, 205)):
    x, y = xy
    pad_x, pad_y = 22, 20
    wrapped = []
    if title:
        wrapped.append(("title", title))
    for line in lines:
        chunks = textwrap.wrap(line, width=max(12, width // 25), break_long_words=False)
        for chunk in chunks:
            wrapped.append(("body", chunk))
    line_heights = [40 if kind == "title" else 30 for kind, _ in wrapped]
    box_h = pad_y * 2 + sum(line_heights) + 8 * max(0, len(wrapped) - 1)
    draw.rounded_rectangle((x, y, x + width, y + box_h), radius=18, fill=fill, outline=(70, 130, 190, 145), width=2)
    yy = y + pad_y
    for kind, txt in wrapped:
        if kind == "title":
            draw.text((x + pad_x, yy), txt, font=FONT_H2, fill=(245, 250, 255))
            yy += 43
        else:
            draw.text((x + pad_x, yy), txt, font=FONT_BODY, fill=(226, 234, 242))
            yy += 33


def draw_caption(draw, text):
    lines = textwrap.wrap(text, width=34, break_long_words=False)
    y0 = H - 32 - 29 * len(lines)
    draw.rounded_rectangle((130, y0 - 14, W - 130, H - 28), radius=12, fill=(3, 8, 18, 205))
    y = y0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=FONT_BODY)
        draw.text(((W - (bbox[2] - bbox[0])) / 2, y), line, font=FONT_BODY, fill=(255, 255, 255))
        y += 29


def draw_brand(draw):
    draw.text((48, 36), "TLaser", font=FONT_H2, fill=(255, 255, 255))
    draw.text((48, 70), "光通信激光器数字孪生平台", font=FONT_SMALL, fill=(188, 211, 232))


def draw_progress(draw, scene_idx, n_scenes, local_t):
    x0, y0, bar_w, bar_h = 48, H - 48, W - 96, 6
    draw.rounded_rectangle((x0, y0, x0 + bar_w, y0 + bar_h), radius=4, fill=(255, 255, 255, 55))
    total_t = (scene_idx + local_t) / n_scenes
    draw.rounded_rectangle((x0, y0, x0 + int(bar_w * total_t), y0 + bar_h), radius=4, fill=(88, 190, 255, 210))


def scene_base(asset_key, local_t):
    img = load_cover(ASSETS[asset_key], local_t)
    img = gradient_overlay(img)
    draw = ImageDraw.Draw(img, "RGBA")
    draw_brand(draw)
    return img, draw


def architecture_frame(local_t):
    img, draw = scene_base("plaser", local_t)
    draw.text((64, 136), "不是单点 AI 软件，而是一套技术体系", font=FONT_H1, fill=(255, 255, 255))
    cards = [
        ("Lasers", "高精度物理发动机\n电、光、热、多物理过程", (80, 240), (49, 111, 164)),
        ("PLaser", "AI 加速器\nPINN 从物理与数据中学习", (460, 240), (86, 137, 70)),
        ("TLaser", "工程师可用平台\n预测、标定、报告、API", (840, 240), (166, 107, 45)),
    ]
    for name, desc, (x, y), color in cards:
        draw.rounded_rectangle((x, y, x + 320, y + 170), radius=18, fill=color + (218,), outline=(255, 255, 255, 90), width=2)
        draw.text((x + 24, y + 24), name, font=FONT_H1, fill=(255, 255, 255))
        yy = y + 82
        for line in desc.split("\n"):
            draw.text((x + 34, yy), line, font=FONT_SMALL, fill=(235, 244, 250))
            yy += 40
    for ax in (418, 798):
        draw.line((ax, 320, ax + 45, 320), fill=(255, 255, 255, 210), width=6)
        draw.polygon([(ax + 45, 320), (ax + 30, 306), (ax + 30, 334)], fill=(255, 255, 255, 210))
    draw_caption(draw, "Lasers 负责算清楚，PLaser 负责算得快，TLaser 负责用起来。")
    return img


def metric_frame(local_t):
    img, draw = scene_base("train" if local_t < 0.5 else "calibration", local_t)
    text_box(
        draw,
        (64, 160),
        ["大量历史仿真数据 + 真实测试数据", "把复杂物理问题压缩为快速 AI 预测模型"],
        title="为什么需要 AI？",
        width=570,
    )
    draw.rounded_rectangle((790, 160, 1180, 375), radius=20, fill=(8, 16, 30, 218), outline=(88, 190, 255, 140), width=2)
    draw.text((825, 190), "原型测试", font=FONT_H2, fill=(210, 232, 250))
    draw.text((825, 240), "< 5 ms", font=FONT_TITLE, fill=(255, 255, 255))
    draw.text((825, 302), "单次预测", font=FONT_SMALL, fill=(188, 211, 232))
    draw.text((980, 246), "R² > 0.997", font=FONT_H1, fill=(255, 228, 150))
    draw_caption(draw, "原来需要认真算的问题，现在可以快速预测。")
    return img


def inverse_frame(local_t):
    img, draw = scene_base("inverse", local_t)
    text_box(
        draw,
        (60, 136),
        ["输入真实 L-I-V 测试曲线", "反向寻找无法直接测量的内部关键参数", "形成：设计 → 仿真 → 制造 → 测试 → AI分析 → 校准 → 再设计"],
        title="真正有价值：不仅预测，还能找原因",
        width=620,
    )
    draw_caption(draw, "工程师不只知道结果不对，还能更快判断为什么不对。")
    return img


def market_frame(local_t):
    img, draw = scene_base("module" if local_t < 0.5 else "internals", local_t)
    draw.text((64, 130), "这到底能卖给谁？", font=FONT_H1, fill=(255, 255, 255))
    items = [
        ("光芯片企业", "设计、测试、校准"),
        ("光模块企业", "器件筛选与模型复用"),
        ("测试设备企业", "API 与私有化部署"),
    ]
    y = 223
    for title, desc in items:
        draw.rounded_rectangle((74, y, 540, y + 78), radius=14, fill=(8, 16, 30, 205), outline=(255, 255, 255, 80), width=2)
        draw.text((98, y + 16), title, font=FONT_H2, fill=(255, 255, 255))
        draw.text((290, y + 22), desc, font=FONT_SMALL, fill=(188, 211, 232))
        y += 94
    draw_caption(draw, "先做联合验证和模型定制，再进入 SaaS、私有化部署和设备 API。")
    return img


SCENES = [
    {
        "duration": 20,
        "asset": "chip",
        "title": "投资人能马上理解的问题",
        "lines": ["设计图纸告诉你它应该跑多快。", "真实制造后，性能为什么会偏离设计值？", "光通信激光器芯片内部参数，很难直接测出来。"],
        "caption": "TLaser 解决的，就是仿真和实测之间为什么有偏差。",
    },
    {"duration": 35, "custom": architecture_frame},
    {
        "duration": 20,
        "asset": "long",
        "title": "真实世界比模型复杂",
        "lines": ["工艺偏差、材料差异、温度环境变化", "还有复杂的量子物理效应", "高精度模型很重要，但还不够。"],
        "caption": "真实芯片不会保证完全按电脑模型表现。",
    },
    {"duration": 20, "custom": metric_frame},
    {"duration": 35, "custom": inverse_frame},
    {"duration": 30, "custom": market_frame},
    {
        "duration": 20,
        "asset": "live",
        "title": "一句话记住 TLaser",
        "lines": ["Lasers 是物理内核", "PLaser 是 AI 加速器", "TLaser 是数字孪生产品平台", "连接物理模型、海量数据和真实测试。"],
        "caption": "让工程师更快知道：这颗芯片为什么和设计不一样，下一步应该怎么改。",
    },
]


def normal_scene(scene, local_t):
    img, draw = scene_base(scene["asset"], local_t)
    draw.text((64, 126), scene["title"], font=FONT_H1, fill=(255, 255, 255))
    text_box(draw, (64, 200), scene["lines"], width=570)
    draw_caption(draw, scene["caption"])
    return img


def write_storyboard():
    lines = [
        "TLaser 推广视频分镜",
        f"输出：{OUT}",
        "素材优先来自 C:\\Users\\aw4wz\\Documents\\Codex\\Lasers\\Pages",
        "",
    ]
    elapsed = 0
    for idx, scene in enumerate(SCENES, 1):
        dur = scene["duration"]
        if "custom" in scene:
            title = scene["custom"].__name__
        else:
            title = scene["title"]
        lines.append(f"{idx}. {elapsed:03d}s-{elapsed + dur:03d}s | {title}")
        elapsed += dur
    STORYBOARD.write_text("\n".join(lines), encoding="utf-8")


def main():
    for name, path in ASSETS.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing asset {name}: {path}")

    write_storyboard()
    writer = imageio.get_writer(
        OUT,
        fps=FPS,
        codec="libx264",
        quality=8,
        macro_block_size=16,
        ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
    )
    try:
        scene_count = len(SCENES)
        for idx, scene in enumerate(SCENES):
            frames = int(scene["duration"] * FPS)
            for f in range(frames):
                local_t = f / max(1, frames - 1)
                if "custom" in scene:
                    img = scene["custom"](local_t)
                else:
                    img = normal_scene(scene, local_t)
                draw = ImageDraw.Draw(img, "RGBA")
                draw_progress(draw, idx, scene_count, local_t)
                writer.append_data(np.asarray(img))
    finally:
        writer.close()
    print(f"saved={OUT.resolve()}")
    print(f"storyboard={STORYBOARD.resolve()}")


if __name__ == "__main__":
    main()
