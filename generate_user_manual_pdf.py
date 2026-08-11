#!/usr/bin/env python3
"""
Generate a professional, high-fidelity 5-page PDF User Manual for TLaser.
Embeds the generated workflow diagrams, physical explainers, dashboard screenshots,
and validation charts directly into the PDF layout.
"""

from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

# Setup paths
TLASER_DIR = Path(__file__).resolve().parent
output_pdf_path = TLASER_DIR / "Doc" / "TLaser_User_Manual.pdf"
assets_dir = TLASER_DIR / "docs" / "manual_assets"
assets_dir.mkdir(parents=True, exist_ok=True)

# Theme Colors
BG_COLOR = "#0a192f"
PANEL_COLOR = "#172a45"
ACCENT_GREEN = "#64ffda"
ACCENT_RED = "#ff7b72"
TEXT_COLOR = "#ffffff"
MUTED_TEXT = "#8892b0"

def add_header(ax, title):
    ax.text(0.05, 0.95, "TLASER DIODE LASER DIGITAL TWIN", color=ACCENT_GREEN, fontsize=10, fontweight="bold", alpha=0.8)
    ax.text(0.05, 0.91, title.upper(), color=TEXT_COLOR, fontsize=15, fontweight="bold")
    ax.plot([0.05, 0.95], [0.89, 0.89], color="#233554", transform=ax.transAxes, linewidth=1.5)

def add_footer(ax, page_num):
    ax.plot([0.05, 0.95], [0.08, 0.08], color="#233554", transform=ax.transAxes, linewidth=1.0)
    ax.text(0.05, 0.05, "Copyright (c) 2026 Zhenwen Wan (AI + Simulation Expert). All rights reserved.", color=MUTED_TEXT, fontsize=8)
    ax.text(0.90, 0.05, f"Page {page_num}", color=MUTED_TEXT, fontsize=9)

def draw_paragraph(ax, text, x, y, max_len=95, line_height=0.019, color="#e6f1ff", fontsize=9.2):
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

def embed_image(fig, img_path, left, bottom, w, h):
    if img_path.exists():
        img = plt.imread(str(img_path))
        img_ax = fig.add_axes([left, bottom, w, h], facecolor="none")
        img_ax.imshow(img)
        img_ax.axis("off")
    else:
        # Fallback placeholder box
        img_ax = fig.add_axes([left, bottom, w, h], facecolor=PANEL_COLOR)
        img_ax.text(0.5, 0.5, f"Asset Missing:\n{img_path.name}", color=ACCENT_RED, ha='center', va='center')
        img_ax.axis("off")

# Initialize PDF compilation
with PdfPages(str(output_pdf_path)) as pdf:
    # ====================================================
    # Page 1: Cover Page
    # ====================================================
    fig = plt.figure(figsize=(8.5, 11), facecolor=BG_COLOR)
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    
    # Techy background accent lines
    ax.plot([0, 1], [0.85, 0.85], color=PANEL_COLOR, linewidth=3)
    ax.plot([0, 1], [0.15, 0.15], color=PANEL_COLOR, linewidth=3)
    
    # Title
    ax.text(0.1, 0.68, "TLaser", color=ACCENT_GREEN, fontsize=54, fontweight="bold")
    ax.text(0.1, 0.58, "Real-Time Digital Twin &\nParameter Calibration Platform", color=TEXT_COLOR, fontsize=24, fontweight="bold", linespacing=1.3)
    ax.text(0.1, 0.50, "A Physics-Informed Neural Network Surrogate Suite for Diode Lasers", color=MUTED_TEXT, fontsize=12, style="italic")
    
    # Highlight box
    ax.text(0.1, 0.38, "USER MANUAL & TECHNICAL REFERENCE", color=ACCENT_GREEN, fontsize=11, fontweight="bold", bbox=dict(boxstyle="square,pad=0.5", facecolor=PANEL_COLOR, edgecolor=ACCENT_GREEN, linewidth=1))
    
    # Meta Details
    ax.text(0.1, 0.28, "TARGET AUDIENCE:", color=MUTED_TEXT, fontsize=9, fontweight="bold")
    ax.text(0.1, 0.25, "Diode Laser Engineers, Optoelectronics Researchers & System Operators", color=TEXT_COLOR, fontsize=10.5)
    
    ax.text(0.1, 0.20, "AUTHOR & SERVICE SCOPE:", color=MUTED_TEXT, fontsize=9, fontweight="bold")
    ax.text(0.1, 0.17, "Zhenwen Wan (AI + Simulation Expert  |  Service: Custom PINN Surrogates)", color=TEXT_COLOR, fontsize=10)
    
    pdf.savefig(fig, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    
    # ====================================================
    # Page 2: Digital Twin Architecture & Mapping
    # ====================================================
    fig = plt.figure(figsize=(8.5, 11), facecolor=BG_COLOR)
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    
    add_header(ax, "1. Digital Twin Architecture & Solver Mapping")
    
    y = 0.84
    # Section 1
    ax.text(0.05, y, "Section 1.1: Physical Device & Cavity Discretization", color=ACCENT_GREEN, fontsize=10.5, fontweight="bold")
    y -= 0.02
    p1_txt = (
        "Telecom diode lasers emit coherent light through cleaved mirror facets. Modeling longitudinal carrier "
        "recombination requires solvingcoupled wave-carrier equations along the propagation z-axis cavity. "
        "The cavity is discretized into a 51-point longitudinal grid to capture spatial hole burning (SHB) depletion."
    )
    y = draw_paragraph(ax, p1_txt, 0.05, y)
    
    # Section 2
    y -= 0.015
    ax.text(0.05, y, "Section 1.2: 7D Geometrical Sweeps & Dataset Generation", color=ACCENT_GREEN, fontsize=10.5, fontweight="bold")
    y -= 0.02
    p2_txt = (
        "The high-fidelity simulation sweeping tool runs random sweeps over the 7D parametric workspace: "
        "rear/front reflectivities R1/R2, cavity length L, ambient temperature T0, injection active current, "
        "active width w_active, and active layer thickness d_active. This covers 1500 samples saved in data files."
    )
    y = draw_paragraph(ax, p2_txt, 0.05, y)

    # Section 3
    y -= 0.015
    ax.text(0.05, y, "Section 1.3: Physical Rate Equation Core", color=ACCENT_GREEN, fontsize=10.5, fontweight="bold")
    y -= 0.02
    p3_txt = (
        "The underlying core is a steady-state quasi-3D optoelectronic-thermal coupled physical simulator. "
        "It acts as the reference data synthesizer, evaluating carrier continuity, non-radiative Auger "
        "losses, and optical output power fields under high current injections."
    )
    y = draw_paragraph(ax, p3_txt, 0.05, y)
    
    # Embed reference graphics
    embed_image(fig, assets_dir / "pinn_training_loss.png", 0.15, 0.14, 0.70, 0.22)
    ax.text(0.5, 0.10, "Figure 1.1: Surrogate PINN training convergence and residual loss history.", color=MUTED_TEXT, fontsize=8, ha='center', style='italic')
    
    add_footer(ax, 2)
    pdf.savefig(fig, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    
    # ====================================================
    # Page 3: Streamlit Interface & Calibration Dashboard
    # ====================================================
    fig = plt.figure(figsize=(8.5, 11), facecolor=BG_COLOR)
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    
    add_header(ax, "2. Streamlit Control App & Calibration Dashboard")
    
    y = 0.84
    # Dashboard description
    ax.text(0.05, y, "Section 2.1: Interactive Sweeps Dashboard", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    y -= 0.022
    m1_txt = (
        "The dashboard (app.py) provides real-time digital twin sweeps with under 5 milliseconds latency. "
        "The sidebar controls the 7D configuration, updating 1D carrier and optical power profiles. "
        "Bilingual language toggles (English/Chinese) enable international usability."
    )
    y = draw_paragraph(ax, m1_txt, 0.05, y)
    
    # Calibration Loop description
    y -= 0.015
    ax.text(0.05, y, "Section 2.2: Online Parameter Calibration Engine", color=ACCENT_GREEN, fontsize=11, fontweight="bold")
    y -= 0.022
    m2_txt = (
        "The calibration loop fits physical drifts by matching real-time measured Light-Current-Voltage (L-I-V) curves. "
        "The engine calibrates internal loss alpha_i, confinement factor Gamma, Auger recombination scaling, "
        "series resistance Rs, and shunt resistance Rsh. Ingestion interfaces support JSON and CSV file uploads."
    )
    y = draw_paragraph(ax, m2_txt, 0.05, y)
    
    # Embed calibration comparison chart
    embed_image(fig, assets_dir / "calibration_fit.png", 0.15, 0.14, 0.70, 0.22)
    ax.text(0.5, 0.10, "Figure 2.1: L-I and V-I curves fitting comparison before and after calibration.", color=MUTED_TEXT, fontsize=8, ha='center', style='italic')
    
    add_footer(ax, 3)
    pdf.savefig(fig, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    
    # ====================================================
    # Page 4: Scientific Methodology & Mathematical Formulations
    # ====================================================
    fig = plt.figure(figsize=(8.5, 11), facecolor=BG_COLOR)
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    
    add_header(ax, "3. Scientific Methodology & Formulations")
    
    y = 0.84
    # Carrier rate equation
    ax.text(0.05, y, "Section 3.1: Carrier Continuity Residual", color=ACCENT_GREEN, fontsize=10.5, fontweight="bold")
    y -= 0.02
    p5_txt = (
        "The PINN training optimizer penalizes non-physical steady-state carrier deviations along the cavity grid: "
        "G_inj - R_rec(N(z)) - R_stim(N(z), P(z)) = 0. G_inj integrates active width and thickness: "
        "I_active / (q0 * L * w_active * d_active). Recombination includes Shockley-Read-Hall, radiative, "
        "and temperature-dependent non-radiative Auger processes."
    )
    y = draw_paragraph(ax, p5_txt, 0.05, y)
    
    # Wave propagation equation
    y -= 0.015
    ax.text(0.05, y, "Section 3.2: Second-Order Photon Wave Intensity Residual", color=ACCENT_GREEN, fontsize=10.5, fontweight="bold")
    y -= 0.02
    p6_txt = (
        "Optical waves propagation utilizes the second-order derivative approximation along the cavity: "
        "d2P/dz2 - (Gamma * g(z) - alpha_i)^2 * P(z) = 0. This total power residual on all internal grid "
        "nodes ensures the intensity curvature conforms to coupled longitudinal wave propagation."
    )
    y = draw_paragraph(ax, p6_txt, 0.05, y)
    
    # Validation
    y -= 0.015
    ax.text(0.05, y, "Section 3.3: Neural Surrogate Architecture", color=ACCENT_GREEN, fontsize=10.5, fontweight="bold")
    y -= 0.02
    p7_txt = (
        "The surrogate model PINNLaser uses dense layers with GELU activation. It maps the 7D parametric input "
        "vector to a 105D array representing total power, WPE, current, and longitudinal grid distributions. "
        "Input scale mappings are normalized within [0, 1] during backpropagation optimization."
    )
    y = draw_paragraph(ax, p7_txt, 0.05, y)
    
    # Draw physical schematic
    rect_phys = plt.Rectangle((0.15, 0.14), 0.70, 0.18, facecolor=PANEL_COLOR, edgecolor="#233554", lw=1.5, transform=ax.transAxes)
    ax.add_patch(rect_phys)
    ax.text(0.5, 0.28, "TLaser Physics Constraints Model", color="#ffffff", fontsize=11, fontweight="bold", ha="center")
    ax.text(0.5, 0.23, "Loss = Loss_Data + w_c * Loss_Carrier + w_p * Loss_Photon + w_s * Loss_Smooth", color=ACCENT_GREEN, fontsize=9.5, fontweight="bold", ha="center", fontfamily="monospace")
    ax.text(0.5, 0.18, "Enforces wave propagation & carrier continuity on 51 longitudinal grid nodes.", color=MUTED_TEXT, fontsize=8.5, ha="center")
    
    add_footer(ax, 4)
    pdf.savefig(fig, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    
    # ====================================================
    # Page 5: Setup, Commands & Troubleshooting
    # ====================================================
    fig = plt.figure(figsize=(8.5, 11), facecolor=BG_COLOR)
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    
    add_header(ax, "4. Environment Setup, Commands & Troubleshooting")
    
    y = 0.84
    ax.text(0.05, y, "Section 4.1: Code Compilation Commands", color=ACCENT_GREEN, fontsize=10.5, fontweight="bold")
    y -= 0.02
    
    # We draw commands as clean text
    def draw_code(y_pos, cmd):
        ax.text(0.08, y_pos, "  >  " + cmd, color=ACCENT_GREEN, fontsize=9, fontfamily="monospace")
        return y_pos - 0.025
        
    y = draw_code(y, "python simulator/generate_dataset.py --num-samples 1500")
    y = draw_code(y, "python surrogate/train.py --epochs 600")
    y = draw_code(y, "python calibration/calibrate.py --data-file data/monitored_liv.json")
    y = draw_code(y, "python verify_pipeline.py")
    y = draw_code(y, "python -m streamlit run app.py")
    
    y -= 0.01
    ax.text(0.05, y, "Section 4.2: Input Schema Specifications", color=ACCENT_GREEN, fontsize=10.5, fontweight="bold")
    y -= 0.02
    p8_txt = (
        "JSON file structure requires fields: current_A, voltage_V, and optical_power_W containing arrays of floats. "
        "CSV format requires a header line, followed by three columns in order: Current (A), Voltage (V), and Power (W)."
    )
    y = draw_paragraph(ax, p8_txt, 0.05, y)
    
    y -= 0.01
    ax.text(0.05, y, "Section 4.3: Troubleshooting & Operations", color=ACCENT_GREEN, fontsize=10.5, fontweight="bold")
    y -= 0.02
    p9_txt = (
        "For CUDA/PyTorch package errors, force-install the CPU wheel using the whl index parameter. "
        "If model loading fails, verify scale parameters pinn_scale_params.npz exist in data/ folders. "
        "Always execute verification using verify_pipeline.py to validate code syntax and dataset shapes."
    )
    y = draw_paragraph(ax, p9_txt, 0.05, y)
    
    # Author contact info
    rect_author = plt.Rectangle((0.05, 0.14), 0.90, 0.16, facecolor=PANEL_COLOR, edgecolor="#233554", lw=1, transform=ax.transAxes)
    ax.add_patch(rect_author)
    ax.text(0.10, 0.26, "Zhenwen Wan (AI + Simulation Expert)", color="#ffffff", fontsize=11, fontweight="bold")
    ax.text(0.10, 0.22, "Contact for commercial collaborations or custom PINN solutions: aw4wzw@gmail.com", color=MUTED_TEXT, fontsize=9)
    ax.text(0.10, 0.17, "Project Repository: https://github.com/ZhenwenWan/TLaser", color=ACCENT_GREEN, fontsize=9, fontfamily="monospace")
    
    add_footer(ax, 5)
    pdf.savefig(fig, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()

print(f"Compilation complete. PDF User Manual saved to {output_pdf_path}")
