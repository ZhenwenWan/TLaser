#!/usr/bin/env python3
"""
PINN Surrogate Wrapper for TLaser.
Loads the trained PyTorch model and scale parameters to perform instant predictions.
"""

from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
from scipy.signal import savgol_filter

# Import the model class from the local folder
sys.path.append(str(Path(__file__).resolve().parent))
from model import PINNLaser

class PINNSurrogate:
    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        
        # Load scale parameters
        scale_path = model_dir / "data" / "pinn_scale_params.npz" if (model_dir / "data").exists() else model_dir / "pinn_scale_params.npz"
        if not scale_path.exists():
            raise FileNotFoundError(f"Scale parameters not found at {scale_path}")
            
        data = np.load(str(scale_path))
        self.in_min = data["in_min"]
        self.in_max = data["in_max"]
        self.out_min = data["out_min"]
        self.out_max = data["out_max"]
        
        # Initialize and load model weights
        self.model = PINNLaser(7, 105)
        model_path = model_dir / "data" / "pinn_laser_model.pt" if (model_dir / "data").exists() else model_dir / "pinn_laser_model.pt"
        if not model_path.exists():
            raise FileNotFoundError(f"Model weights not found at {model_path}")
            
        self.model.load_state_dict(torch.load(str(model_path), map_location=torch.device('cpu')))
        self.model.eval()
        
    def predict(
        self,
        R1: float,
        R2: float,
        L_um: float,
        T0: float,
        I_active: float,
        w_active_um: float | None = None,
        d_active_um: float | None = None
    ) -> dict[str, np.ndarray | float]:
        """
        Instantly predicts laser performance metrics and profiles.
        """
        L = L_um * 1e-4  # cm
        w = (w_active_um if w_active_um is not None else 2.8) * 1e-4  # cm
        d = (d_active_um if d_active_um is not None else 0.342) * 1e-4  # cm
        
        # Input vector
        in_vec = np.array([R1, R2, L, T0, I_active, w, d], dtype=np.float32)
        
        # Scale
        scaled_in = (in_vec - self.in_min) / (self.in_max - self.in_min)
        scaled_in_tensor = torch.FloatTensor(scaled_in).unsqueeze(0)
        
        # Predict
        with torch.no_grad():
            scaled_out = self.model(scaled_in_tensor).numpy().squeeze(0)
            
        # Unscale
        out_vec = scaled_out * (self.out_max - self.out_min) + self.out_min
        
        # Parse outputs
        P_opt = float(max(out_vec[0], 0.0))
        wpe = float(max(out_vec[1], 0.0))
        I_total = float(max(out_vec[2], 0.0))
        
        N_profile = np.clip(out_vec[3:54], a_min=1.0e15, a_max=None)
        P_profile = np.clip(out_vec[54:105], a_min=0.0, a_max=None)
        
        # Smooth profiles using Savitzky-Golay filter to ensure physical smoothness
        N_profile = np.clip(savgol_filter(N_profile, window_length=15, polyorder=3), a_min=1.0e15, a_max=None)
        P_profile = np.clip(savgol_filter(P_profile, window_length=15, polyorder=3), a_min=0.0, a_max=None)
        
        z_grid = np.linspace(0.0, L_um, 51)
        
        return {
            "P_opt": P_opt,
            "wpe": wpe,
            "I_total": I_total,
            "N": N_profile,
            "P": P_profile,
            "z_grid": z_grid
        }
