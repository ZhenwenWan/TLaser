#!/usr/bin/env python3
"""
Generate 9:16 vertical mobile presentation slide cards for TLaser.
Embeds the generated calibration curves and training plots programmatically.
"""

from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Setup directories
MOBILE_DIR = Path(__file__).resolve().parent
TLASER_DIR = MOBILE_DIR.parent.parent
output_dir = MOBILE_DIR
output_dir.mkdir(parents=True, exist_ok=True)

# Theme Colors
BG_COLOR = "#0a192f"
PANEL_COLOR = "#172a45"
ACCENT_GREEN = "#64ffda"
ACCENT_RED = "#ff7b72"
TEXT_COLOR = "#ffffff"
MUTED_TEXT = "#8892b0"

def save_slide(filename, draw_func):
    # Standard 9:16 aspect ratio card (1080 x 1920 scaled to matplotlib inches)
    fig = plt.figure(figsize=(5.4, 9.6), facecolor=BG_COLOR)
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    
    # Outer thin border
    rect = plt.Rectangle((0.02, 0.02), 0.96, 0.96, fill=False, edgecolor="#233554", lw=1.5, transform=ax.transAxes)
    ax.add_patch(rect)
    
    # Top brand banner
    ax.text(0.5, 0.94, "TLASER DIODE LASER TWIN", color=ACCENT_GREEN, fontsize=9, fontweight="bold", ha="center", alpha=0.8)
    ax.plot([0.1, 0.9], [0.92, 0.92], color="#233554", transform=ax.transAxes, linewidth=1.0)
    
    # Draw custom content
    draw_func(fig, ax)
    
    # Bottom footer brand
    ax.plot([0.1, 0.9], [0.08, 0.08], color="#233554", transform=ax.transAxes, linewidth=1.0)
    ax.text(0.5, 0.05, "Zhenwen Wan (AI + Simulation Expert)", color=MUTED_TEXT, fontsize=8, ha="center")
    
    plot_path = output_dir / filename
    plt.savefig(plot_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Generated mobile story slide card: {plot_path}")

def embed_image_to_axes(fig, img_path, left, bottom, w, h):
    if img_path.exists():
        img = plt.imread(str(img_path))
        img_ax = fig.add_axes([left, bottom, w, h], facecolor="none")
        img_ax.imshow(img)
        img_ax.axis("off")
    else:
        img_ax = fig.add_axes([left, bottom, w, h], facecolor=PANEL_COLOR)
        img_ax.text(0.5, 0.5, "Plot Asset\nNot Found", color=ACCENT_RED, ha='center', va='center', fontsize=9)
        img_ax.axis("off")

def draw_paragraph(ax, text, x, y, max_len=45, line_height=0.025, color="#e6f1ff", fontsize=10):
    words = text.split()
    curr_line = ""
    lines = []
    for word in words:
        if len(curr_line + " " + word) < max_len:
            curr_line += (" " if curr_line else "") + word
        else:
            lines.append(curr_line)
            curr_line = word
    if curr_line:
        lines.append(curr_line)
        
    for line in lines:
        ax.text(x, y, line, color=color, fontsize=fontsize, transform=ax.transAxes, alpha=0.9)
        y -= line_height
    return y

# ====================================================
# Slide Definitions
# ====================================================

# Card 1: Cover
def draw_cover(fig, ax):
    ax.text(0.5, 0.65, "TLaser", color=ACCENT_GREEN, fontsize=42, fontweight="bold", ha="center")
    ax.text(0.5, 0.56, "Real-Time Digital Twin\n& Parameter Calibration", color=TEXT_COLOR, fontsize=18, fontweight="bold", ha="center", linespacing=1.3)
    
    p_text = "Instant neural surrogate predictions and online physical drift optimization for telecom diode lasers."
    draw_paragraph(ax, p_text, 0.1, 0.44, max_len=40, line_height=0.025, color=MUTED_TEXT, fontsize=10.5)
    
    rect_box = plt.Rectangle((0.15, 0.22), 0.70, 0.12, facecolor=PANEL_COLOR, edgecolor=ACCENT_GREEN, lw=1.0, transform=ax.transAxes)
    ax.add_patch(rect_box)
    ax.text(0.5, 0.29, "USER-FACING STORYBOARD", color="#ffffff", fontsize=11, fontweight="bold", ha="center")
    ax.text(0.5, 0.25, "Real-Time Health Monitoring", color=ACCENT_GREEN, fontsize=9.5, ha="center")

# Card 2: The Core Problem
def draw_problem(fig, ax):
    ax.text(0.1, 0.82, "01. THE PROBLEM", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    ax.text(0.1, 0.77, "CAE Solvers Are Too Slow", color=TEXT_COLOR, fontsize=16, fontweight="bold")
    
    p_text = (
        "Traditional 2D finite-element electromagnetic and thermal solvers "
        "take tens of seconds to run a single sweep. This makes interactive "
        "optodynamic design tuning and live physical device health monitoring impossible."
    )
    draw_paragraph(ax, p_text, 0.1, 0.70, max_len=38, line_height=0.026)
    
    # Flow illustration
    rect_box1 = plt.Rectangle((0.15, 0.35), 0.70, 0.20, facecolor=PANEL_COLOR, edgecolor="#233554", lw=1.0, transform=ax.transAxes)
    ax.add_patch(rect_box1)
    ax.text(0.5, 0.50, "Full mesh FEM/TCAD solver\n\n\n\n\n\n\n\n", color=MUTED_TEXT, fontsize=9, ha="center")
    ax.text(0.5, 0.44, "25 Seconds per Sweep", color=ACCENT_RED, fontsize=12, fontweight="bold", ha="center")

# Card 3: Workflow
def draw_workflow(fig, ax):
    ax.text(0.1, 0.82, "02. THE SOLUTION", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    ax.text(0.1, 0.77, "Neural Surrogate Workflow", color=TEXT_COLOR, fontsize=16, fontweight="bold")
    
    p_text = (
        "TLaser bridges CAE simulations with deep learning using a four-step digital twin pipeline:"
    )
    draw_paragraph(ax, p_text, 0.1, 0.72, max_len=38)
    
    # 4 Steps blocks
    def draw_step(y_pos, num, title, desc):
        rect = plt.Rectangle((0.1, y_pos), 0.80, 0.08, facecolor=PANEL_COLOR, edgecolor="#233554", lw=1.0, transform=ax.transAxes)
        ax.add_patch(rect)
        ax.text(0.13, y_pos + 0.045, f"{num}. {title}", color=ACCENT_GREEN, fontsize=9.5, fontweight="bold")
        ax.text(0.13, y_pos + 0.015, desc, color=MUTED_TEXT, fontsize=8.5)
        
    draw_step(0.56, "1", "High-Fidelity Sweeps", "Generate 1,500 physical reference records.")
    draw_step(0.46, "2", "PINN Backpropagation", "Train model penalizing wave continuity residuals.")
    draw_step(0.36, "3", "Instant Predictions", "Estimate spatial hole burning in under 5ms.")
    draw_step(0.26, "4", "Online Calibration", "Optimize parameters against monitored L-I-V curves.")

# Card 4: Predictions
def draw_predictions(fig, ax):
    ax.text(0.1, 0.82, "03. REAL-TIME RUN", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    ax.text(0.1, 0.77, "PINN Surrogate Sweep", color=TEXT_COLOR, fontsize=16, fontweight="bold")
    
    p_text = (
        "The PINN surrogate instantly predicts longitudinal profiles and scalar metrics with >0.997 accuracy."
    )
    draw_paragraph(ax, p_text, 0.1, 0.72, max_len=38)
    
    # Embed training loss plot
    embed_image_to_axes(fig, TLASER_DIR / "data" / "pinn_training_loss.png", 0.1, 0.32, 0.80, 0.32)
    ax.text(0.5, 0.28, "Training Loss history showing clean convergence.", color=MUTED_TEXT, fontsize=8.5, ha="center")

# Card 5: Active Calibration
def draw_calibration(fig, ax):
    ax.text(0.1, 0.82, "04. OPTIMIZATION", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    ax.text(0.1, 0.77, "Online Parameters Fit", color=TEXT_COLOR, fontsize=16, fontweight="bold")
    
    p_text = (
        "Parameter calibration matches measured L-I-V curves to calibrate internal optical loss alpha_i, Gamma, and Auger coefficients."
    )
    draw_paragraph(ax, p_text, 0.1, 0.72, max_len=38)
    
    # Embed curve fit plot
    embed_image_to_axes(fig, TLASER_DIR / "data" / "calibration_fit.png", 0.1, 0.32, 0.80, 0.32)
    ax.text(0.5, 0.28, "Calibrated fits matching noisy measurement points.", color=MUTED_TEXT, fontsize=8.5, ha="center")

# Card 6: Limitations
def draw_limitations(fig, ax):
    ax.text(0.1, 0.82, "05. BOUNDARIES", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    ax.text(0.1, 0.77, "Engineering Limitations", color=TEXT_COLOR, fontsize=16, fontweight="bold")
    
    p_text = (
        "Digital twin representations require strict boundaries to guide operations safely:"
    )
    draw_paragraph(ax, p_text, 0.1, 0.72, max_len=38)
    
    rect_box = plt.Rectangle((0.1, 0.35), 0.80, 0.28, facecolor=PANEL_COLOR, edgecolor=ACCENT_RED, lw=1.0, transform=ax.transAxes)
    ax.add_patch(rect_box)
    
    draw_paragraph(ax, "[!] Reduced Model Approximation", 0.14, 0.58, color=ACCENT_RED, fontsize=10.5)
    draw_paragraph(ax, "The internal solver is a quasi-3D mathematical surrogate, not a substitute for full spatial TCAD. Validation relies on available sensor telemetry.", 0.14, 0.53, max_len=32, color=TEXT_COLOR, fontsize=9.5)

# Card 7: Call to Action
def draw_cta(fig, ax):
    ax.text(0.5, 0.78, "TLaser Platform", color=ACCENT_GREEN, fontsize=28, fontweight="bold", ha="center")
    ax.text(0.5, 0.70, "Run and Test Locally", color=TEXT_COLOR, fontsize=16, fontweight="bold", ha="center")
    
    rect = plt.Rectangle((0.1, 0.40), 0.80, 0.20, facecolor=PANEL_COLOR, edgecolor="#233554", lw=1.0, transform=ax.transAxes)
    ax.add_patch(rect)
    ax.text(0.5, 0.54, "Get Started immediately:", color=TEXT_COLOR, fontsize=10, ha="center")
    ax.text(0.5, 0.48, "python -m streamlit run app.py", color=ACCENT_GREEN, fontsize=11, fontfamily="monospace", ha="center", fontweight="bold")
    
    ax.text(0.5, 0.32, "Download User Manuals (PDF) at:\nzhenwenwan.github.io/Pages/TLaser.html", color=MUTED_TEXT, fontsize=10, ha="center")
    ax.text(0.5, 0.20, "Developer: aw4wzw@gmail.com\nRepository: github.com/ZhenwenWan/TLaser", color=MUTED_TEXT, fontsize=9.5, ha="center")

# List of slides
slides = [
    ("cover.png", draw_cover),
    ("problem.png", draw_problem),
    ("workflow.png", draw_workflow),
    ("dashboard_mobile.png", draw_predictions),
    ("calibration_mobile.png", draw_calibration),
    ("limitations.png", draw_limitations),
    ("cta.png", draw_cta),
]

for filename, func in slides:
    save_slide(filename, func)

print("\nAll 9:16 mobile presentation slide cards generated successfully!")
