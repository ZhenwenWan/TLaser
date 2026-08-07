import sys
import json
import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from scipy.optimize import minimize

# Add simulator folder to python path to import Quasi3DSimulator
sys.path.append(str(Path(__file__).resolve().parent.parent / "simulator"))
from quasi_3d_synthesizer import Quasi3DSimulator

# Define a function to simulate the L-I-V curve for a given set of parameters
def simulate_liv(currents, R1, R2, L_um, T0, w_um, d_um, alpha_i, Gamma, C_mult, R_series, R_shunt):
    L = L_um * 1e-4
    w = w_um * 1e-4
    d = d_um * 1e-4
    
    P_opts = []
    V_terms = []
    I_totals = []
    
    for I_act in currents:
        I_2d = I_act / L
        # Initialize simulator with custom physical constants
        sim = Quasi3DSimulator(
            L_cavity=L,
            R1=R1,
            R2=R2,
            M=51,
            T0=T0,
            w_active=w,
            d_active=d,
            alpha_i=alpha_i
        )
        sim.Gamma = Gamma
        # Scale the default Auger recombination coefficient by C_mult
        sim.C_recomb = sim.C_recomb * C_mult
        
        try:
            res = sim.solve_longitudinal(I_2d, verbose=False)
            P_opt = res["P_opt"]
            
            # Electrical junction voltage based on active current
            V_junction = 0.95 + 0.05 * np.log(max(I_act, 1e-9) / 1e-6 + 1.0)
            
            # Shunt leakage current
            I_shunt = V_junction / R_shunt
            I_tot = I_act + I_shunt
            
            # Terminal voltage
            V_term = V_junction + I_tot * R_series
            
            P_opts.append(P_opt)
            V_terms.append(V_term)
            I_totals.append(I_tot)
        except Exception:
            P_opts.append(0.0)
            V_terms.append(0.0)
            I_totals.append(0.0)
            
    return np.array(P_opts), np.array(V_terms), np.array(I_totals)

def generate_mock_monitoring_data():
    np.random.seed(123)
    # 10 monitoring points of active current from 50mA to 400mA
    currents = np.linspace(0.05, 0.40, 10)
    
    # Real physical device parameters (drifted / unknown to the digital twin)
    true_alpha_i = 12.5       # cm^-1
    true_Gamma = 0.048        # Confinement factor
    true_C_mult = 1.35        # Auger coefficient scaling (multiplier)
    true_R_series = 0.85      # Ohms series resistance
    true_R_shunt = 150.0      # Ohms shunt leakage path resistance
    
    # Static geometry
    R1 = 0.90
    R2 = 0.05
    L_um = 300.0
    T0 = 298.0
    w_um = 2.8
    d_um = 0.342
    
    P_clean, V_clean, I_tot_clean = simulate_liv(
        currents, R1, R2, L_um, T0, w_um, d_um,
        true_alpha_i, true_Gamma, true_C_mult, true_R_series, true_R_shunt
    )
    
    # Add 2% measurement noise
    P_noise = P_clean + np.random.normal(0, 0.02 * (P_clean + 1e-4), size=P_clean.shape)
    V_noise = V_clean + np.random.normal(0, 0.01 * V_clean, size=V_clean.shape)
    
    P_noise = np.clip(P_noise, 0.0, None)
    
    return currents, P_noise, V_noise, {
        "R1": R1, "R2": R2, "L_um": L_um, "T0": T0, "w_um": w_um, "d_um": d_um,
        "true_alpha_i": true_alpha_i, "true_Gamma": true_Gamma, "true_C_mult": true_C_mult,
        "true_R_series": true_R_series, "true_R_shunt": true_R_shunt
    }

def main(args_list=None):
    parser = argparse.ArgumentParser(description="TLaser Digital Twin calibration solver.")
    parser.add_argument("--data-file", type=str, default=None, help="Path to JSON/CSV monitoring dataset")
    parser.add_argument("--smoke-test", action="store_true", help="Run 2 optimization iterations for rapid checks")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory to save fit parameters")
    args = parser.parse_args(args_list)
    
    current_dir = Path(__file__).resolve().parent
    output_dir = Path(args.output_dir) if args.output_dir else current_dir.parent / "data"
    output_dir.mkdir(exist_ok=True)
    
    # Load monitored dataset
    if args.data_file:
        print(f"Loading monitoring data from {args.data_file}...")
        data_path = Path(args.data_file)
        if data_path.suffix == ".json":
            with open(data_path, "r") as f:
                raw_data = json.load(f)
            currents = np.array(raw_data["current_A"])
            P_mon = np.array(raw_data["optical_power_W"])
            V_mon = np.array(raw_data["voltage_V"])
            meta = raw_data.get("metadata", {
                "R1": 0.90, "R2": 0.05, "L_um": 300.0, "T0": 298.0, "w_um": 2.8, "d_um": 0.342,
                "true_alpha_i": 12.5, "true_Gamma": 0.048, "true_C_mult": 1.35, "true_R_series": 0.85, "true_R_shunt": 150.0
            })
        else:
            # Fallback to CSV parsing (assuming headers)
            csv_data = np.genfromtxt(data_path, delimiter=",", skip_header=1)
            currents = csv_data[:, 0]
            V_mon = csv_data[:, 1]
            P_mon = csv_data[:, 2]
            meta = {
                "R1": 0.90, "R2": 0.05, "L_um": 300.0, "T0": 298.0, "w_um": 2.8, "d_um": 0.342,
                "true_alpha_i": 12.5, "true_Gamma": 0.048, "true_C_mult": 1.35, "true_R_series": 0.85, "true_R_shunt": 150.0
            }
    else:
        print("No monitoring dataset supplied. Generating mock monitoring dataset with noise...")
        currents, P_mon, V_mon, meta = generate_mock_monitoring_data()
        
    # Outlier/Invalid Data Filtering
    valid_mask = (currents > 0) & (P_mon >= 0) & (V_mon > 0)
    dropped_count = len(currents) - np.sum(valid_mask)
    if dropped_count > 0:
        print(f"  [WARNING] Dropped {dropped_count} invalid measurement points (non-positive current/voltage or negative power).")
        currents = currents[valid_mask]
        P_mon = P_mon[valid_mask]
        V_mon = V_mon[valid_mask]
        
    print(f"  Monitored points (after filtering): {len(currents)}")
    print(f"  Laser geometry:  L={meta['L_um']}um, w={meta['w_um']}um, d={meta['d_um']}um")
    
    # Parameters to calibrate: [alpha_i, Gamma, C_mult, R_series, R_shunt]
    initial_guess = [10.0, 0.05, 1.0, 1.0, 200.0]
    bounds = [
        (5.0, 20.0),      # alpha_i limits
        (0.03, 0.08),     # Gamma limits
        (0.5, 3.0),       # C_mult limits
        (0.1, 3.0),       # R_series limits
        (50.0, 1000.0)    # R_shunt limits
    ]
    
    # Loss objective
    def objective(params):
        alpha_i, Gamma, C_mult, R_series, R_shunt = params
        P_sim, V_sim, _ = simulate_liv(
            currents, meta["R1"], meta["R2"], meta["L_um"], meta["T0"], meta["w_um"], meta["d_um"],
            alpha_i, Gamma, C_mult, R_series, R_shunt
        )
        
        # Calculate loss normalized by average scales
        loss_P = np.mean((P_sim - P_mon)**2) / max(np.mean(P_mon**2), 1e-6)
        loss_V = np.mean((V_sim - V_mon)**2) / np.mean(V_mon**2)
        
        total_loss = loss_P + loss_V
        return total_loss
    
    print("\nRunning digital twin parameter calibration optimization...")
    max_iter = 2 if args.smoke_test else 20
    res = minimize(
        objective,
        initial_guess,
        method='L-BFGS-B',
        bounds=bounds,
        options={'maxiter': max_iter, 'iprint': 1}
    )
    
    cal_alpha_i, cal_Gamma, cal_C_mult, cal_R_series, cal_R_shunt = res.x
    
    # Save calibrated parameters
    calibrated_data = {
        "alpha_i": float(cal_alpha_i),
        "Gamma": float(cal_Gamma),
        "C_mult": float(cal_C_mult),
        "R_series": float(cal_R_series),
        "R_shunt": float(cal_R_shunt),
        "success": bool(res.success),
        "mse": float(res.fun),
        "iterations": int(res.nit),
        "timestamp": datetime.now().isoformat()
    }
    
    with open(output_dir / "calibrated_params.json", "w") as f:
        json.dump(calibrated_data, f, indent=4)
        
    print(f"\nCalibrated parameters saved to {output_dir}/calibrated_params.json")
    
    # Append to calibration history log
    history_path = output_dir / "calibration_history.json"
    history_list = []
    if history_path.exists():
        try:
            with open(history_path, "r") as f:
                history_list = json.load(f)
                if not isinstance(history_list, list):
                    history_list = []
        except Exception:
            history_list = []
            
    history_list.append(calibrated_data)
    # Limit history list to last 50 entries to keep it token efficient
    history_list = history_list[-50:]
    try:
        with open(history_path, "w") as f:
            json.dump(history_list, f, indent=4)
        print(f"Calibration history updated in {history_path}")
    except Exception as ex:
        print(f"Warning: Failed to write to calibration history log: {ex}")
    
    # Diagnostic Output
    print("\n=== CALIBRATION RESULTS ===")
    print(f"  Optimizer Status: {'SUCCESS' if res.success else 'FAILED/MAX_ITER'}")
    print(f"  Fitted MSE Loss:  {res.fun:.6e}")
    print(f"  Parameter             | Initial Guess | Calibrated Value")
    print(f"  --------------------------------------------------------")
    print(f"  Internal Loss alpha_i | {initial_guess[0]:13.3f} | {cal_alpha_i:16.3f}")
    print(f"  Confinement Gamma     | {initial_guess[1]:13.3f} | {cal_Gamma:16.3f}")
    print(f"  Auger Multiplier C    | {initial_guess[2]:13.3f} | {cal_C_mult:16.3f}")
    print(f"  Series Resistance Rs  | {initial_guess[3]:13.3f} | {cal_R_series:16.3f}")
    print(f"  Shunt Resistance Rsh  | {initial_guess[4]:13.3f} | {cal_R_shunt:16.3f}")
    
    # Generate Before vs After fit comparison
    print("\nGenerating calibration fit comparison plot...")
    P_initial, V_initial, _ = simulate_liv(
        currents, meta["R1"], meta["R2"], meta["L_um"], meta["T0"], meta["w_um"], meta["d_um"],
        *initial_guess
    )
    P_calibrated, V_calibrated, _ = simulate_liv(
        currents, meta["R1"], meta["R2"], meta["L_um"], meta["T0"], meta["w_um"], meta["d_um"],
        cal_alpha_i, cal_Gamma, cal_C_mult, cal_R_series, cal_R_shunt
    )
    
    # Plot L-I and V-I curves
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5), facecolor="#121212")
    
    # Light-Current (L-I) plot
    ax1.scatter(currents, P_mon * 1000.0, color="#ff7b72", marker="o", label="Monitored Data")
    ax1.plot(currents, P_initial * 1000.0, color="#8b949e", linestyle="--", linewidth=1.8, label="Initial Guess")
    ax1.plot(currents, P_calibrated * 1000.0, color="#64ffda", linewidth=2.5, label="Digital Twin Fit")
    ax1.set_title("L-I Characteristics (Output Power)", color="white", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Monitored Active Current (A)", color="#8b949e")
    ax1.set_ylabel("Optical Power (mW)", color="#8b949e")
    ax1.grid(True, linestyle="--", alpha=0.3, color="#555555")
    ax1.set_facecolor("#1e1e1e")
    ax1.tick_params(colors="white")
    ax1.legend(loc="upper left")
    for spine in ax1.spines.values():
        spine.set_color("#555555")
        
    # Voltage-Current (V-I) plot
    ax2.scatter(currents, V_mon, color="#ff7b72", marker="o", label="Monitored Data")
    ax2.plot(currents, V_initial, color="#8b949e", linestyle="--", linewidth=1.8, label="Initial Guess")
    ax2.plot(currents, V_calibrated, color="#64ffda", linewidth=2.5, label="Digital Twin Fit")
    ax2.set_title("V-I Characteristics (Terminal Voltage)", color="white", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Monitored Active Current (A)", color="#8b949e")
    ax2.set_ylabel("Terminal Voltage (V)", color="#8b949e")
    ax2.grid(True, linestyle="--", alpha=0.3, color="#555555")
    ax2.set_facecolor("#1e1e1e")
    ax2.tick_params(colors="white")
    ax2.legend(loc="upper left")
    for spine in ax2.spines.values():
        spine.set_color("#555555")
        
    plt.tight_layout()
    plot_path = output_dir / "calibration_fit.svg"
    plt.savefig(plot_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plot_path_png = output_dir / "calibration_fit.png"
    plt.savefig(plot_path_png, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close()
    print(f"Calibration fit comparison plot successfully saved to {plot_path} and {plot_path_png}")

if __name__ == "__main__":
    main()
