#!/usr/bin/env python3
"""
Generate a high-fidelity MP4 demonstration video for TLaser.
Sweeps design parameters in real-time and visualizes multiphysics steady states.
Simulates the Streamlit interface for live monitoring sweeps.
"""

import sys
import os
from pathlib import Path

# Dependency Check
try:
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import cv2
except ImportError as e:
    print(f"Dependency Error: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

# Conditional path injection for local PyTorch libs
try:
    import torch
except ImportError:
    print("Error: PyTorch not found. Please activate virtual environment.")
    sys.exit(1)

# Import TLaser surrogate wrapper
TLASER_DIR = Path(__file__).resolve().parent
sys.path.append(str(TLASER_DIR / "surrogate"))
sys.path.append(str(TLASER_DIR / "calibration"))

try:
    from pinn_surrogate import PINNSurrogate
except ImportError as e:
    print(f"Error importing pinn_surrogate: {e}")
    sys.exit(1)

surrogate = PINNSurrogate(TLASER_DIR)

# Output video settings
video_path = TLASER_DIR / "TLaser_Demonstration.mp4"
fps = 15
width, height = 1280, 720
total_frames = 150  # 10 seconds at 15 FPS

# Initialize OpenCV VideoWriter with HTML5-compatible avc1 (H.264) codec
fourcc = cv2.VideoWriter_fourcc(*'avc1')
video = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))

if not video.isOpened():
    print(f"Error: Failed to open OpenCV VideoWriter for writing at {video_path}")
    sys.exit(1)

print(f"Generating animation simulating the TLaser sweeps ({total_frames} frames)...")

# Define Sweep Sequences
r1_seq = np.ones(total_frames) * 0.90
r2_seq = np.ones(total_frames) * 0.05
L_seq = np.ones(total_frames) * 300.0
T0_seq = np.ones(total_frames) * 298.0
I_seq = np.ones(total_frames) * 0.15
w_seq = np.ones(total_frames) * 2.8
d_seq = np.ones(total_frames) * 0.342

# Sweep Active Region Current I (Frames 0 to 50): 0.05A -> 0.40A
I_seq[0:50] = np.linspace(0.05, 0.40, 50)
# Sweep Work Temperature T0 (Frames 50 to 100): 298K -> 350K
T0_seq[50:100] = np.linspace(298.0, 350.0, 50)
# Sweep Ridge Width w (Frames 100 to 150): 2.8um -> 4.0um
w_seq[100:150] = np.linspace(2.8, 4.0, 50)

# Setup Matplotlib Figure
plt.style.use('dark_background')
fig = plt.figure(figsize=(16, 9), facecolor="#0d1117")

# Sidebar axes (left dashboard mockup)
ax_sidebar = fig.add_axes([0, 0, 0.22, 1.0], facecolor="#161b22")
ax_sidebar.axis("off")

# Dashboard viewports
ax_carrier = fig.add_axes([0.26, 0.15, 0.33, 0.65], facecolor="#172a45")
ax_optical = fig.add_axes([0.63, 0.15, 0.33, 0.65], facecolor="#172a45")

def write_frame_to_video():
    fig.canvas.draw()
    try:
        if hasattr(fig.canvas, 'buffer_rgba'):
            img = np.asarray(fig.canvas.buffer_rgba())
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        else:
            img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    except Exception:
        img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
    img_bgr = cv2.resize(img_bgr, (width, height))
    video.write(img_bgr)

# Render Loop
for frame in range(total_frames):
    r1 = r1_seq[frame]
    r2 = r2_seq[frame]
    L = L_seq[frame]
    T0 = T0_seq[frame]
    I_active = I_seq[frame]
    w_active = w_seq[frame]
    d_active = d_seq[frame]
    
    # Run PINN prediction
    res = surrogate.predict(
        R1=r1,
        R2=r2,
        L_um=L,
        T0=T0,
        I_active=I_active,
        w_active_um=w_active,
        d_active_um=d_active
    )
    
    P_opt = res["P_opt"]
    wpe = res["wpe"]
    I_total = res["I_total"]
    N_prof = res["N"]
    P_prof = res["P"]
    z_grid = res["z_grid"]
    
    # 1. DRAW SIDEBAR
    ax_sidebar.clear()
    ax_sidebar.axis("off")
    ax_sidebar.set_facecolor("#161b22")
    ax_sidebar.axvline(x=0.99, color="#30363d", linewidth=1.5)
    
    ax_sidebar.text(0.08, 0.94, "TLaser Control Center", color="#64ffda", fontsize=14, fontweight="bold")
    ax_sidebar.text(0.08, 0.90, "Language: English", color="#8b949e", fontsize=8.5)
    ax_sidebar.plot([0.08, 0.92], [0.86, 0.86], color="#30363d", lw=1)
    
    # Draw parameters status
    def draw_param(y, label, val_str):
        ax_sidebar.text(0.08, y, label, color="#8b949e", fontsize=8)
        ax_sidebar.text(0.92, y, val_str, color="#ffffff", fontsize=8, ha="right", fontweight="bold")

    draw_param(0.81, "Rear Refl R1", f"{r1:.2f}")
    draw_param(0.77, "Front Refl R2", f"{r2:.2f}")
    draw_param(0.73, "Cavity Length L", f"{L:.0f} um")
    draw_param(0.69, "Ridge Width w", f"{w_active:.2f} um")
    draw_param(0.65, "Active Thickness d", f"{d_active:.3f} um")
    draw_param(0.61, "Ambient Temp T0", f"{T0:.1f} K")
    draw_param(0.57, "Active Current I", f"{I_active:.2f} A")
    
    ax_sidebar.plot([0.08, 0.92], [0.52, 0.52], color="#30363d", lw=1)
    
    # Output metrics
    ax_sidebar.text(0.08, 0.47, "Digital Twin Metrics", color="#64ffda", fontsize=10, fontweight="bold")
    draw_param(0.42, "Output Power", f"{P_opt * 1000.0:.1f} mW")
    draw_param(0.38, "WPE", f"{wpe * 100.0:.3f} %")
    draw_param(0.34, "Total Current", f"{I_total:.3f} A")
    
    # 2. DRAW VIEWPORTS
    fig.texts.clear()
    fig.text(0.26, 0.93, "TLaser Digital Twin Simulation Sweeps", color="#ffffff", fontsize=16, fontweight="bold")
    fig.text(0.26, 0.90, "Real-time longitudinal multi-physics mapping along the active quantum well", color="#8b949e", fontsize=9.5)
    fig.text(0.96, 0.93, f"Frame {frame+1}/{total_frames}", color="#8b949e", fontsize=9, ha="right")
    
    # Plot 1: Carrier Density
    ax_carrier.clear()
    ax_carrier.plot(z_grid, N_prof / 1e18, color="#ff7b72", linewidth=2.5)
    ax_carrier.set_title("Carrier Density N(z)", color="white", fontsize=10, fontweight="bold")
    ax_carrier.set_xlabel("z Position (um)", color="#8b949e", fontsize=8.5)
    ax_carrier.set_ylabel("N (10^18 cm^-3)", color="#8b949e", fontsize=8.5)
    ax_carrier.grid(True, linestyle="--", alpha=0.3, color="#233554")
    ax_carrier.tick_params(colors="#8b949e", labelsize=8)
    for spine in ax_carrier.spines.values():
        spine.set_color("#30363d")
        
    # Plot 2: Optical Power
    ax_optical.clear()
    ax_optical.plot(z_grid, P_prof * 1000.0, color="#64ffda", linewidth=2.5)
    ax_optical.set_title("Optical Power Profile P(z)", color="white", fontsize=10, fontweight="bold")
    ax_optical.set_xlabel("z Position (um)", color="#8b949e", fontsize=8.5)
    ax_optical.set_ylabel("Power (mW)", color="#8b949e", fontsize=8.5)
    ax_optical.grid(True, linestyle="--", alpha=0.3, color="#233554")
    ax_optical.tick_params(colors="#8b949e", labelsize=8)
    for spine in ax_optical.spines.values():
        spine.set_color("#30363d")
        
    write_frame_to_video()
    if (frame + 1) % 30 == 0:
        print(f"Rendered {frame+1}/{total_frames} frames...")

video.release()
plt.close(fig)
print(f"Animation successfully saved to {video_path}")
