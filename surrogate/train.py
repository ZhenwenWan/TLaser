#!/usr/bin/env python3
"""
Train PINN Laser Model for TLaser.
Loads the 7D simulated dataset, trains a PyTorch Physics-Informed Neural Network (PINN)
surrogate model with carrier and photon propagation residual losses, and saves weights.
"""

from __future__ import annotations
import os
import sys
import math
import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# Enforce single-thread execution
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import torch
torch.set_num_threads(1)
import torch.nn as nn
import torch.optim as optim

# Add local path to import PINNLaser
sys.path.append(str(Path(__file__).resolve().parent))
from model import PINNLaser

def main():
    parser = argparse.ArgumentParser(description="Train PINN surrogate model for TLaser.")
    parser.add_argument("--epochs", type=int, default=600, help="Number of training epochs")
    parser.add_argument("--smoke-test", action="store_true", help="Run quick verification with 5 epochs")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory containing dataset and target for weights")
    args = parser.parse_args()
    
    epochs = 5 if args.smoke_test else args.epochs
    
    current_dir = Path(__file__).resolve().parent
    repo_dir = current_dir.parent
    data_dir = Path(args.output_dir) if args.output_dir else repo_dir / "data"
    
    inputs_path = data_dir / "pinn_inputs.npy"
    targets_path = data_dir / "pinn_targets.npy"
    
    if not inputs_path.exists() or not targets_path.exists():
        raise FileNotFoundError(
            f"Dataset files not found at {data_dir}. Please run dataset generation first!"
        )
        
    inputs = np.load(str(inputs_path))
    targets = np.load(str(targets_path))
    
    # Scale inputs/targets
    in_min = np.array([0.1, 0.05, 0.01, 250.0, 0.01, 1.5e-4, 1.0e-5], dtype=np.float32)
    in_max = np.array([0.95, 0.5, 0.1, 360.0, 0.5, 4.0e-4, 5.0e-5], dtype=np.float32)
    
    out_min = np.zeros(105, dtype=np.float32)
    out_max = np.ones(105, dtype=np.float32)
    out_max[0] = 1.0      # P_opt max ~1W
    out_max[1] = 0.5      # WPE max ~50%
    out_max[2] = 20.0     # I_total max ~20A
    out_max[3:54] = 1.0e19 # N profile max ~1e19
    out_max[54:105] = 20.0 # P profile max ~20W
    
    # Save scale parameters for future client usage
    np.savez(
        str(data_dir / "pinn_scale_params.npz"),
        in_min=in_min,
        in_max=in_max,
        out_min=out_min,
        out_max=out_max
    )
    
    # Scale dataset
    scaled_inputs = (inputs - in_min) / (in_max - in_min)
    scaled_targets = (targets - out_min) / (out_max - out_min)
    
    # Limit samples for smoke test to make it extremely fast
    if args.smoke_test:
        scaled_inputs = scaled_inputs[:10]
        scaled_targets = scaled_targets[:10]
        
    # Tensors
    X_train = torch.FloatTensor(scaled_inputs)
    y_train = torch.FloatTensor(scaled_targets)
    
    # Model
    model = PINNLaser(7, 105)
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    
    # Constants for physics residuals
    q0 = 1.60213377e-19
    E_phot = 6.62607015e-34 * 1.934e14
    
    print(f"\nTraining the TLaser PINN surrogate...")
    print(f"  Training Epochs: {epochs}")
    print(f"  Training Samples: {X_train.shape[0]}")
    if args.smoke_test:
        print("  [SMOKE TEST MODE ENABLED]")
        
    loss_history = []
    
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        
        pred = model(X_train)
        
        # 1. Data regression loss (MSE)
        loss_data = nn.MSELoss()(pred, y_train)
        
        # Unscale variables for physics computation
        X_unscaled = X_train * torch.FloatTensor(in_max - in_min) + torch.FloatTensor(in_min)
        pred_unscaled = pred * torch.FloatTensor(out_max - out_min) + torch.FloatTensor(out_min)
        
        T0 = X_unscaled[:, 3]
        L = X_unscaled[:, 2]
        I_active = X_unscaled[:, 4]
        w_active = X_unscaled[:, 5]
        d_active = X_unscaled[:, 6]
        
        A_act = w_active * d_active
        I_2d_unit = I_active / L
        G_inj = I_2d_unit / (q0 * A_act)
        
        # Temp scaling laws
        temp_gain_scale = torch.exp(-(T0 - 300.0) / 120.0)
        temp_ntr_scale = (T0 / 300.0)**1.5
        temp_auger_scale = (T0 / 300.0)**2.0
        
        g0_gain = 1200.0 * temp_gain_scale
        N_tr = 1.0e18 * temp_ntr_scale
        C_recomb = 3.0e-29 * temp_auger_scale
        
        # Evaluated nodes for carrier rate equation residual (subset for efficiency)
        nodes_carrier = [0, 12, 25, 37, 50]
        phys_residual_carrier = 0.0
        
        for k in nodes_carrier:
            N_node = pred_unscaled[:, 3 + k]
            P_node = pred_unscaled[:, 54 + k]
            
            N_scaled = N_node / 1.0e18
            N_tr_scaled = N_tr / 1.0e18
            
            # Logarithmic gain
            gain_node = g0_gain * (torch.log(torch.clamp(N_scaled / N_tr_scaled, min=1.0e-3)))
            gain_node = torch.clamp(gain_node, min=0.0)
            
            C_recomb_scaled = 30000.0 * temp_auger_scale
            R_rec = (1.0e26 * N_scaled) + (1.0e26 * N_scaled**2) + C_recomb_scaled * N_scaled**3
            R_stim = (gain_node * P_node) / (A_act * E_phot)
            
            f_N = G_inj - R_rec - R_stim
            phys_residual_carrier += torch.mean((f_N / 1.0e27)**2)
            
        loss_carrier = phys_residual_carrier / len(nodes_carrier)
        
        # 2. Physics-informed loss: Photon propagation equation residual
        # d2P/dz2 - (Gamma*g(z) - alpha_i)^2 * P(z) = 0
        N_prof = pred_unscaled[:, 3:54]
        P_prof = pred_unscaled[:, 54:105]
        
        N_scaled_prof = N_prof / 1.0e18
        N_tr_scaled_batch = N_tr[:, None] / 1.0e18
        
        # Vectorized local gain (shape: [Batch, 51])
        g_prof = g0_gain[:, None] * torch.log(torch.clamp(N_scaled_prof / N_tr_scaled_batch, min=1.0e-3))
        g_prof = torch.clamp(g_prof, min=0.0)
        
        Gamma = 0.05
        alpha_i = 10.0
        k_local = Gamma * g_prof - alpha_i
        
        # Central difference second derivative for P(z)
        dz = L / 50.0
        d2P_dz2 = (P_prof[:, 2:] - 2.0 * P_prof[:, 1:-1] + P_prof[:, :-2]) / (dz[:, None]**2)
        
        # Photon propagation residual on all internal grid points [1:-1]
        photon_res = d2P_dz2 - (k_local[:, 1:-1]**2) * P_prof[:, 1:-1]
        loss_photon = torch.mean((photon_res / 10.0)**2)
        
        # 3. Spatial smoothness regularization (TV + Laplacian)
        diff1_N = pred[:, 4:54] - pred[:, 3:53]
        diff1_P = pred[:, 55:105] - pred[:, 54:104]
        loss_smooth1 = torch.mean(diff1_N**2) + torch.mean(diff1_P**2)
        
        diff2_N = pred[:, 5:54] - 2 * pred[:, 4:53] + pred[:, 3:52]
        diff2_P = pred[:, 56:105] - 2 * pred[:, 55:104] + pred[:, 54:103]
        loss_smooth2 = torch.mean(diff2_N**2) + torch.mean(diff2_P**2)
        
        loss_smooth = loss_smooth1 + 10.0 * loss_smooth2
        
        # Combined Loss: data + carrier rate + photon propagation + smoothness
        loss = loss_data + 0.05 * loss_carrier + 0.05 * loss_photon + 1.5 * loss_smooth
        
        loss.backward()
        optimizer.step()
        
        loss_history.append(loss.item())
        if (epoch + 1) % 50 == 0 or args.smoke_test:
            print(f"  Epoch {epoch+1:3d}/{epochs}: Loss = {loss.item():.6e} (Data={loss_data.item():.6e}, Carrier={loss_carrier.item():.6e}, Photon={loss_photon.item():.6e}, Smooth={loss_smooth.item():.6e})")
            
    # Save model weights
    torch.save(model.state_dict(), str(data_dir / "pinn_laser_model.pt"))
    print("\nModel saved successfully as pinn_laser_model.pt")
    
    # Output final metrics
    print("\n=== FINAL SURROGATE METRICS ===")
    print(f"  Final Combined Loss:    {loss_history[-1]:.6e}")
    print(f"  Final Data MSE Loss:    {loss_data.item():.6e}")
    print(f"  Final Carrier Res Loss: {loss_carrier.item():.6e}")
    print(f"  Final Photon Res Loss:  {loss_photon.item():.6e}")
    print(f"  Final Smoothness Loss:  {loss_smooth.item():.6e}")
    
    # Save training loss plot
    plt.figure(figsize=(8, 5))
    plt.plot(loss_history, color="#64ffda", linewidth=2.5)
    plt.title("TLaser PINN Surrogate Training Loss History", color="white", fontsize=12)
    plt.xlabel("Epoch", color="white")
    plt.ylabel("Loss", color="white")
    plt.grid(True, linestyle="--", alpha=0.3, color="#555555")
    plt.gca().set_facecolor("#1e1e1e")
    plt.gcf().patch.set_facecolor("#121212")
    plt.gca().tick_params(colors="white")
    for spine in plt.gca().spines.values():
        spine.set_color("#555555")
    plt.yscale("log")
    
    plot_path = data_dir / "pinn_training_loss.svg"
    plt.savefig(plot_path, dpi=300, facecolor=plt.gcf().get_facecolor(), edgecolor="none")
    plot_path_png = data_dir / "pinn_training_loss.png"
    plt.savefig(plot_path_png, dpi=300, facecolor=plt.gcf().get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Saved training loss plot to {plot_path} and {plot_path_png}")

if __name__ == "__main__":
    main()
