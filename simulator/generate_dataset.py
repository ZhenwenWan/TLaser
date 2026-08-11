import sys
import math
import json
import argparse
from datetime import datetime
from pathlib import Path
import numpy as np

# Add simulator folder to python path to import Quasi3DSimulator
sys.path.append(str(Path(__file__).resolve().parent))
from quasi_3d_synthesizer import Quasi3DSimulator

def main():
    parser = argparse.ArgumentParser(description="Dataset generator for TLaser digital twin.")
    parser.add_argument("--num-samples", type=int, default=1500, help="Number of samples to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for generation")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save generated files")
    parser.add_argument("--smoke-test", action="store_true", help="Run in lightweight test mode (10 samples)")
    args = parser.parse_args()
    
    num_samples = 10 if args.smoke_test else args.num_samples
    seed = args.seed
    np.random.seed(seed)
    
    # Establish paths
    current_dir = Path(__file__).resolve().parent
    output_dir = Path(args.output_dir) if args.output_dir else current_dir.parent / "data"
    output_dir.mkdir(exist_ok=True)
    
    inputs = []
    targets = []
    count = 0
    attempts = 0
    failures = 0
    failure_log = {}

    print(f"Starting TLaser dataset generation...")
    print(f"  Target Samples: {num_samples}")
    print(f"  Random Seed:    {seed}")
    print(f"  Output Dir:     {output_dir}")
    if args.smoke_test:
        print("  [SMOKE TEST MODE ENABLED]")
        
    # Range bounds definitions (in micro-units for easy reporting)
    ranges = {
        "R1": [0.1, 0.95],
        "R2": [0.05, 0.5],
        "L_um": [100.0, 1000.0],
        "T0": [250.0, 360.0],
        "I_active": [0.01, 0.5],
        "w_active_um": [1.5, 4.0],
        "d_active_um": [0.1, 0.5]
    }
    
    while count < num_samples:
        attempts += 1
        R1 = np.random.uniform(*ranges["R1"])
        R2 = np.random.uniform(*ranges["R2"])
        L_um = np.random.uniform(*ranges["L_um"])
        L = L_um * 1e-4  # cm
        T0 = np.random.uniform(*ranges["T0"])
        I_active = np.random.uniform(*ranges["I_active"])
        w_active_um = np.random.uniform(*ranges["w_active_um"])
        w_active = w_active_um * 1e-4  # cm
        d_active_um = np.random.uniform(*ranges["d_active_um"])
        d_active = d_active_um * 1e-4  # cm
        
        I_2d_unit = I_active / L
        
        # Initialize simulator with dynamic parameters
        sim = Quasi3DSimulator(
            L_cavity=L,
            R1=R1,
            R2=R2,
            M=51,
            T0=T0,
            w_active=w_active,
            d_active=d_active
        )
        
        try:
            res = sim.solve_longitudinal(I_2d_unit, verbose=False)
            P_opt = res["P_opt"]
            wpe = res["WPE"]
            I_total = res["I_total"]
            N_profile = res["N"]
            P_profile = res["P_plus"] + res["P_minus"]
            
            in_vec = [R1, R2, L, T0, I_active, w_active, d_active]
            out_vec = [P_opt, wpe, I_total] + list(N_profile) + list(P_profile)
            
            inputs.append(in_vec)
            targets.append(out_vec)
            count += 1
            
            if count % 300 == 0 or (args.smoke_test and count % 2 == 0):
                print(f"  Generated {count}/{num_samples}...")
        except Exception as e:
            failures += 1
            err_msg = str(e)
            failure_log[err_msg] = failure_log.get(err_msg, 0) + 1
            continue

    # Convert to array
    inputs_arr = np.array(inputs, dtype=np.float32)
    targets_arr = np.array(targets, dtype=np.float32)
    
    # Save files
    np.save(str(output_dir / "pinn_inputs.npy"), inputs_arr)
    np.save(str(output_dir / "pinn_targets.npy"), targets_arr)
    
    # Output metadata
    metadata = {
        "generator": "TLaser/generate_dataset.py",
        "device_family": "edge_emitter",
        "timestamp": datetime.now().isoformat(),
        "seed": seed,
        "smoke_test": args.smoke_test,
        "sample_count": count,
        "total_attempts": attempts,
        "failed_solves": failures,
        "failure_modes": failure_log,
        "parameter_ranges": ranges,
        "shapes": {
            "inputs": list(inputs_arr.shape),
            "targets": list(targets_arr.shape)
        }
    }
    
    with open(output_dir / "pinn_dataset_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)
        
    print(f"Dataset generation completed! Saved metadata to pinn_dataset_metadata.json")
    print(f"  Successful samples: {count}/{attempts} (Failures: {failures})")
    if failures > 0:
        print("  Failure modes logged:")
        for mode, f_count in failure_log.items():
            print(f"    - {mode}: {f_count} times")

if __name__ == "__main__":
    main()
