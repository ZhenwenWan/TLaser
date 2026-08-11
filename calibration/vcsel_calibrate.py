#!/usr/bin/env python3
"""
VCSEL LIV Telemetry Parameter Calibration.
Fits thermal resistance, series resistance, top DBR mirror reflectivity, and carrier
recombination rates against standard-compliant measured data using L-BFGS-B.
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize

# Inject paths
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR / "simulator"))
sys.path.append(str(ROOT_DIR / "calibration"))

try:
    from vcsel_simulator import VCSELSimulator
    from vcsel_validator import validate_vcsel_liv
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def run_vcsel_calibration(
    data_file: str | None = None,
    output_dir: Path | str | None = None,
    smoke_test: bool = False,
) -> dict:
    """
    Fits VCSEL device parameters (R_th, R_series, R_DBR_top, A_recomb, C_recomb)
    to match measured L-I-V curves.
    """
    if output_dir is None:
        output_dir = ROOT_DIR / "data"
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load and validate data
    if data_file is None:
        print("No monitoring dataset supplied. Generating mock VCSEL dataset with noise...")
        # Create a mock valid file
        aperture_dia_um = 8.0
        T_ambient_K = 298.0
        mock_sim = VCSELSimulator(aperture_dia_um=aperture_dia_um, T_ambient=T_ambient_K)
        # Apply true parameter drift
        mock_sim.R_th = 1500.0  # Nominally 1200
        mock_sim.R_series = 68.0  # Nominally 60
        mock_sim.R_DBR_top = 0.994  # Nominally 0.995
        
        currents = np.linspace(1.0, 10.0, 10)
        powers = []
        voltages = []
        for cur in currents:
            res = mock_sim.solve_radial_profiles(cur)
            # Add 2% random noise
            powers.append(res["P_opt_mW"] * (1.0 + 0.02 * np.random.randn()))
            voltages.append(res["V_term"] * (1.0 + 0.01 * np.random.randn()))
            
        data = {
            "current_mA": list(currents),
            "voltage_V": list(voltages),
            "optical_power_mW": list(powers),
            "metadata": {
                "device_id": "VCSEL-MOCK-ACC-01",
                "device_family": "vcsel",
                "aperture_dia_um": aperture_dia_um,
                "T_ambient_K": T_ambient_K
            }
        }
    else:
        # Validate file
        ok, err = validate_vcsel_liv(data_file)
        if not ok:
            raise ValueError(f"VCSEL LIV Data validation failed: {err}")
            
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

    currents = np.array(data["current_mA"])
    meas_voltages = np.array(data["voltage_V"])
    meas_powers = np.array(data["optical_power_mW"])
    
    aperture_dia_um = data["metadata"].get("aperture_dia_um", 8.0)
    T_ambient_K = data["metadata"].get("T_ambient_K", 298.0)
    
    # 2. Optimization setup
    # Parameters to optimize:
    # 0: R_th (500 to 2500)
    # 1: R_series (20 to 150)
    # 2: R_DBR_top (0.990 to 0.998)
    # 3: A_mult (0.5 to 3.0)
    # 4: C_mult (0.5 to 3.0)
    
    initial_guess = [1200.0, 60.0, 0.995, 1.0, 1.0]
    bounds = [
        (500.0, 2500.0),
        (20.0, 150.0),
        (0.990, 0.998),
        (0.5, 3.0),
        (0.5, 3.0)
    ]
    
    # Objective function
    def objective(x):
        R_th_val, R_s_val, R_dbr_val, A_mult, C_mult = x
        
        sim = VCSELSimulator(
            aperture_dia_um=aperture_dia_um,
            R_DBR_top=R_dbr_val,
            R_th=R_th_val,
            T_ambient=T_ambient_K
        )
        sim.R_series = R_s_val
        sim.A_recomb = sim.A_recomb * A_mult
        sim.C_recomb = sim.C_recomb * C_mult
        
        sim_powers = []
        sim_voltages = []
        
        for cur in currents:
            out = sim.solve_radial_profiles(cur)
            sim_powers.append(out["P_opt_mW"])
            sim_voltages.append(out["V_term"])
            
        sim_powers = np.array(sim_powers)
        sim_voltages = np.array(sim_voltages)
        
        # Loss: Sum of squares balanced by scales (voltage is around 2V, power is around 2mW)
        power_loss = np.mean((sim_powers - meas_powers)**2)
        voltage_loss = np.mean((sim_voltages - meas_voltages)**2)
        
        return power_loss + 10.0 * voltage_loss

    # Minimize
    max_iter = 2 if smoke_test else 20
    
    print("\nRunning VCSEL parameter calibration optimization...")
    res = minimize(
        objective,
        initial_guess,
        method='L-BFGS-B',
        bounds=bounds,
        options={'maxiter': max_iter}
    )
    
    cal_R_th, cal_R_s, cal_R_dbr, cal_A_mult, cal_C_mult = res.x
    
    # 3. Save calibrated parameters
    calibrated_params = {
        "device_family": "vcsel",
        "device_id": data["metadata"].get("device_id", "Unknown"),
        "success": bool(res.success),
        "message": res.message,
        "loss": float(res.fun),
        "calibrated_values": {
            "R_th_K_W": float(cal_R_th),
            "R_series_Ohm": float(cal_R_s),
            "R_DBR_top": float(cal_R_dbr),
            "A_recomb_multiplier": float(cal_A_mult),
            "C_recomb_multiplier": float(cal_C_mult)
        }
    }
    
    param_path = output_dir / "vcsel_calibrated_params.json"
    with open(param_path, "w", encoding="utf-8") as f:
        json.dump(calibrated_params, f, indent=4)
    print(f"Calibrated parameters saved to {param_path}")
    
    # 4. Generate Fit Plots
    # Create final calibrated simulator to compute curves
    final_sim = VCSELSimulator(
        aperture_dia_um=aperture_dia_um,
        R_DBR_top=cal_R_dbr,
        R_th=cal_R_th,
        T_ambient=T_ambient_K
    )
    final_sim.R_series = cal_R_s
    final_sim.A_recomb = final_sim.A_recomb * cal_A_mult
    final_sim.C_recomb = final_sim.C_recomb * cal_C_mult
    
    # Compute smooth fit curves
    fit_currents = np.linspace(currents.min(), currents.max(), 50)
    fit_powers = []
    fit_voltages = []
    for cur in fit_currents:
        out = final_sim.solve_radial_profiles(cur)
        fit_powers.append(out["P_opt_mW"])
        fit_voltages.append(out["V_term"])
        
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), facecolor="#0d1117")
        ax1.set_facecolor("#161b22")
        ax2.set_facecolor("#161b22")
        
        # Plot 1: Power Fit
        ax1.scatter(currents, meas_powers, color="#58a6ff", label="Measured", zorder=3)
        ax1.plot(fit_currents, fit_powers, color="#39d353", linewidth=2, label="Digital Twin Fit", zorder=2)
        ax1.set_title("L-I Curve Fit", fontsize=11, fontweight="bold", color="white")
        ax1.set_xlabel("Current (mA)", fontsize=9, color="#8b949e")
        ax1.set_ylabel("Optical Power (mW)", fontsize=9, color="#8b949e")
        ax1.grid(True, linestyle="--", alpha=0.3, color="#30363d")
        ax1.legend(fontsize=9, edgecolor="#30363d")
        ax1.tick_params(colors="#8b949e", labelsize=8)
        for spine in ax1.spines.values():
            spine.set_color("#30363d")
            
        # Plot 2: Voltage Fit
        ax2.scatter(currents, meas_voltages, color="#ff7b72", label="Measured", zorder=3)
        ax2.plot(fit_currents, fit_voltages, color="#39d353", linewidth=2, label="Digital Twin Fit", zorder=2)
        ax2.set_title("V-I Curve Fit", fontsize=11, fontweight="bold", color="white")
        ax2.set_xlabel("Current (mA)", fontsize=9, color="#8b949e")
        ax2.set_ylabel("Terminal Voltage (V)", fontsize=9, color="#8b949e")
        ax2.grid(True, linestyle="--", alpha=0.3, color="#30363d")
        ax2.legend(fontsize=9, edgecolor="#30363d")
        ax2.tick_params(colors="#8b949e", labelsize=8)
        for spine in ax2.spines.values():
            spine.set_color("#30363d")
            
        plt.tight_layout()
        
        plot_path_svg = output_dir / "vcsel_calibration_fit.svg"
        plot_path_png = output_dir / "vcsel_calibration_fit.png"
        
        plt.savefig(plot_path_svg, facecolor=fig.get_facecolor(), edgecolor='none')
        plt.savefig(plot_path_png, facecolor=fig.get_facecolor(), edgecolor='none', dpi=150)
        plt.close(fig)
        print(f"Fit plots saved successfully to {plot_path_svg}")
    except Exception as e:
        print(f"Warning: Failed to render matplotlib fit plots: {e}")
        
    return calibrated_params

if __name__ == "__main__":
    # Smoke run
    res = run_vcsel_calibration(smoke_test=True)
    print("Calibrated series resistance:", res["calibrated_values"]["R_series_Ohm"])
