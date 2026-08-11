#!/usr/bin/env python3
"""
Generate a high-fidelity MP4 demonstration video for the VCSEL digital twin mode.
Sweeps design parameters (current, aperture size, thermal resistance) in real-time
and visualizes radial spatial hole burning, current crowding, and thermal rollover.
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

# Import VCSEL Simulator
TLASER_DIR = Path(__file__).resolve().parent
sys.path.append(str(TLASER_DIR / "simulator"))

try:
    from vcsel_simulator import VCSELSimulator
except ImportError as e:
    print(f"Error importing VCSELSimulator: {e}")
    sys.exit(1)

# Output video settings
video_path = TLASER_DIR / "TLaser_VCSEL_Demonstration.mp4"
fps = 15
width, height = 1280, 720
total_frames = 150  # 10 seconds at 15 FPS

# Initialize OpenCV VideoWriter with HTML5-compatible avc1 (H.264) codec
fourcc = cv2.VideoWriter_fourcc(*'avc1')
video = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))

if not video.isOpened():
    print(f"Error: Failed to open OpenCV VideoWriter for writing at {video_path}")
    sys.exit(1)

print(f"Generating VCSEL animation sweeps ({total_frames} frames)...")

# Define Sweep Sequences
aperture_seq = np.ones(total_frames) * 8.0
R_th_seq = np.ones(total_frames) * 1200.0
T_ambient_seq = np.ones(total_frames) * 298.0
I_seq = np.ones(total_frames) * 6.0

# Sweep 1: Current Sweep (Frames 0 to 50): 1 mA -> 12 mA
I_seq[0:50] = np.linspace(1.0, 12.0, 50)
# Sweep 2: Aperture Diameter Sweep (Frames 50 to 100): 8 um -> 4 um (focuses the mode, increases heating)
aperture_seq[50:100] = np.linspace(8.0, 4.0, 50)
# Sweep 3: Thermal Resistance Sweep (Frames 100 to 150): 1200 K/W -> 2200 K/W (triggers heavy rollover)
R_th_seq[100:150] = np.linspace(1200.0, 2200.0, 50)

# Setup Matplotlib Figure
plt.style.use('dark_background')
fig = plt.figure(figsize=(16, 9), facecolor="#0d1117")

# Sidebar axes (left dashboard mockup)
ax_sidebar = fig.add_axes([0, 0, 0.22, 1.0], facecolor="#161b22")
ax_sidebar.axis("off")

# Dashboard viewports
ax_profiles = fig.add_axes([0.26, 0.15, 0.33, 0.65], facecolor="#172a45")
ax_liv = fig.add_axes([0.65, 0.15, 0.31, 0.65], facecolor="#172a45")

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

# Pre-calculate full L-I curve for static plotting overlay in right axis
def get_liv_data(aperture, r_th):
    sim = VCSELSimulator(aperture_dia_um=aperture, R_th=r_th)
    currents = np.linspace(0.1, 14.0, 40)
    powers = []
    voltages = []
    for cur in currents:
        out = sim.solve_radial_profiles(cur)
        powers.append(out["P_opt_mW"])
        voltages.append(out["V_term"])
    return currents, np.array(powers), np.array(voltages)

# Render Loop
for frame in range(total_frames):
    ap = aperture_seq[frame]
    r_th = R_th_seq[frame]
    I_active = I_seq[frame]
    T_amb = T_ambient_seq[frame]
    
    # Run VCSEL Physical Solver
    sim = VCSELSimulator(
        aperture_dia_um=ap,
        R_th=r_th,
        T_ambient=T_amb
    )
    res = sim.solve_radial_profiles(I_total_mA=I_active)
    
    # Get active curves for LIV axis
    liv_currents, liv_powers, liv_voltages = get_liv_data(ap, r_th)
    
    # 1. DRAW SIDEBAR
    ax_sidebar.clear()
    ax_sidebar.axis("off")
    ax_sidebar.set_facecolor("#161b22")
    ax_sidebar.axvline(x=0.99, color="#30363d", linewidth=1.5)
    
    ax_sidebar.text(0.08, 0.94, "TLaser VCSEL Control", color="#64ffda", fontsize=14, fontweight="bold")
    ax_sidebar.text(0.08, 0.90, "VCSEL Mode: Reduced Physics", color="#8b949e", fontsize=8.5)
    ax_sidebar.plot([0.08, 0.92], [0.86, 0.86], color="#30363d", lw=1)
    
    # Draw parameters status
    def draw_param(y, label, val_str):
        ax_sidebar.text(0.08, y, label, color="#8b949e", fontsize=8.5)
        ax_sidebar.text(0.92, y, val_str, color="#ffffff", fontsize=8.5, ha="right", fontweight="bold")

    draw_param(0.81, "Aperture Dia d_ap", f"{ap:.2f} um")
    draw_param(0.77, "Top DBR Refl R_top", f"{sim.R_DBR_top:.4f}")
    draw_param(0.73, "Bottom DBR R_bot", f"{sim.R_DBR_bottom:.4f}")
    draw_param(0.69, "Thermal Res R_th", f"{r_th:.1f} K/W")
    draw_param(0.65, "Cavity Wavelength", f"{sim.lambda_nm:.0f} nm")
    draw_param(0.61, "Ambient Temp T0", f"{T_amb:.1f} K")
    draw_param(0.57, "Operating Current I", f"{I_active:.2f} mA")
    
    ax_sidebar.plot([0.08, 0.92], [0.52, 0.52], color="#30363d", lw=1)
    
    # Output metrics
    ax_sidebar.text(0.08, 0.47, "Digital Twin Outputs", color="#64ffda", fontsize=10, fontweight="bold")
    draw_param(0.42, "Output Power", f"{res['P_opt_mW']:.3f} mW")
    draw_param(0.38, "Voltage Bias", f"{res['V_term']:.3f} V")
    draw_param(0.34, "Wall-Plug Eff (WPE)", f"{res['WPE'] * 100.0:.3f} %")
    draw_param(0.30, "Junction Temp T_j", f"{res['T_junction']:.2f} K")
    draw_param(0.26, "Threshold Current", f"{res['I_th_mA']:.3f} mA")
    
    # 2. DRAW VIEWPORTS
    fig.texts.clear()
    fig.text(0.26, 0.93, "TLaser VCSEL Digital Twin Parameter Sweeps", color="#ffffff", fontsize=16, fontweight="bold")
    fig.text(0.26, 0.90, "Transverse radial profile mapping and self-heating L-I-V curves", color="#8b949e", fontsize=9.5)
    fig.text(0.96, 0.93, f"Frame {frame+1}/{total_frames}", color="#8b949e", fontsize=9, ha="right")
    
    # Plot 1: Radial Profiles (SHB & Current Crowding)
    ax_profiles.clear()
    r_um = res["r_grid_um"]
    
    # Plot normalized carrier density and current density profiles
    l1, = ax_profiles.plot(r_um, res["N"] / 1e18, color="#ff7b72", linewidth=2.5, label="Carrier N (10^18 cm^-3)")
    
    ax_prof_twin = ax_profiles.twinx()
    l2, = ax_prof_twin.plot(r_um, res["I_profile"], color="#79c0ff", linewidth=2.0, linestyle="--", label="Crowded Current (a.u.)")
    l3, = ax_prof_twin.plot(r_um, res["mode_profile"], color="#64ffda", linewidth=1.5, linestyle=":", label="LP01 Mode Profile")
    
    # Add vertical line at aperture boundary
    ax_profiles.axvline(x=ap/2.0, color="#d29922", linestyle="-.", alpha=0.7, label="Oxide Aperture Radius")
    
    ax_profiles.set_title("Radial Transverse Profiles (r-grid)", color="white", fontsize=10, fontweight="bold")
    ax_profiles.set_xlabel("Radial Distance from Center r (um)", color="#8b949e", fontsize=8.5)
    ax_profiles.set_ylabel("Carrier Density (10^18 cm^-3)", color="#8b949e", fontsize=8.5)
    ax_prof_twin.set_ylabel("Normalized Current / Intensity Profile", color="#8b949e", fontsize=8.5)
    ax_profiles.grid(True, linestyle="--", alpha=0.3, color="#233554")
    ax_profiles.tick_params(colors="#8b949e", labelsize=8)
    ax_prof_twin.tick_params(colors="#8b949e", labelsize=8)
    
    # Combine legends
    lines = [l1, l2, l3]
    labels = [line.get_label() for line in lines]
    ax_profiles.legend(lines, labels, loc="upper right", fontsize=8, facecolor="#161b22", edgecolor="#30363d")
    
    for spine in ax_profiles.spines.values():
        spine.set_color("#30363d")
    for spine in ax_prof_twin.spines.values():
        spine.set_color("#30363d")
        
    # Plot 2: Dynamic L-I-V Curves (highlighting thermal rollover)
    ax_liv.clear()
    ax_liv_twin = ax_liv.twinx()
    
    # Plot static curves for the current frame parameters
    ax_liv.plot(liv_currents, liv_powers, color="#64ffda", alpha=0.4, lw=1.5)
    ax_liv_twin.plot(liv_currents, liv_voltages, color="#ff7b72", alpha=0.3, lw=1.5, linestyle="--")
    
    # Highlight current operating point
    ax_liv.scatter([I_active], [res["P_opt_mW"]], color="#64ffda", s=80, edgecolors="white", zorder=5, label="Active Power Point")
    ax_liv_twin.scatter([I_active], [res["V_term"]], color="#ff7b72", s=80, edgecolors="white", zorder=5, label="Active Voltage Point")
    
    ax_liv.set_title("L-I-V Calibration Curves & Rollover", color="white", fontsize=10, fontweight="bold")
    ax_liv.set_xlabel("Injected Current (mA)", color="#8b949e", fontsize=8.5)
    ax_liv.set_ylabel("Optical Output Power (mW)", color="#64ffda", fontsize=8.5)
    ax_liv_twin.set_ylabel("Terminal Voltage (V)", color="#ff7b72", fontsize=8.5)
    
    # Set fixed limits to see curves morph dynamically
    ax_liv.set_ylim(-0.2, 5.0)
    ax_liv_twin.set_ylim(1.2, 3.2)
    
    ax_liv.grid(True, linestyle="--", alpha=0.3, color="#233554")
    ax_liv.tick_params(colors="#8b949e", labelsize=8)
    ax_liv_twin.tick_params(colors="#8b949e", labelsize=8)
    
    for spine in ax_liv.spines.values():
        spine.set_color("#30363d")
    for spine in ax_liv_twin.spines.values():
        spine.set_color("#30363d")
        
    # Draw reduced physics demo label at the bottom of viewports
    fig.text(0.58, 0.05, "VCSEL mode: reduced-physics demonstration", color="#ff7b72", fontsize=9.5, ha="center", style="italic", fontweight="bold")
    
    write_frame_to_video()
    if (frame + 1) % 30 == 0:
        print(f"Rendered {frame+1}/{total_frames} frames...")

video.release()
plt.close(fig)
print(f"VCSEL Animation successfully saved to {video_path}")
