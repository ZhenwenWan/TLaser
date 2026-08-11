# TLaser User Manual

Welcome to **TLaser**, the Digital Twin Control Center for telecom diode lasers. This manual provides installation instructions, mathematical formulations, execution steps for the simulation and training pipelines, and details on online parameter calibration.

---

## 1. Project Overview

TLaser creates a high-fidelity reduced-order digital twin of a telecom semiconductor laser. It bridges the gap between slow, multi-physics numerical solvers and real-time operational needs by combining:
1. **Quasi-3D Simulator Core**: Solves longitudinal carrier density and wave propagation.
2. **Physics-Informed Neural Network (PINN)**: Maps 7D design parameters to 105D space arrays in under 5 milliseconds.
3. **Monitored L-I-V Parameter Calibration**: Fits internal parameter drift against real-time measured Light-Current-Voltage curves.

### 1.1 Engineering Mapping Storyline

To clearly articulate TLaser's position in the industrial telecom photonics value chain, the platform maps a complete engineering path from products down to digital twin parameters:

1. **Optical Module Level**: Standard SFP/QSFP transceivers plugged into network switches. System testing provides measured L-I-V (Light-Current-Voltage) curves.
2. **Assembly Internal Subsystems**: Subsystems like the Transmitter Optical Sub-Assembly (TOSA), laser driver, and thermoelectric coolers (TEC) dictate operational states.
3. **Laser Chip Level**: The bare semiconductor laser chip inside the TOSA. Waveguide dimensions ($L$, $w$, $d$) define its boundaries.
4. **PLaser Physics (Forward)**: Models carrier transport, quantum well recombination, photon field intensity propagation, and self-heating.
5. **TLaser Digital Twin (Inverse)**: Uses measured LIV curves to identify unmeasurable drifts ($R_{\text{th}}$, $R_s$, $\alpha_i$), calibrating the twin to support engineering diagnostics and design updates.

---

## 2. Environment Setup

Configure a local Python virtual environment to manage dependencies safely:
```powershell
# Clone the repository
git clone https://github.com/ZhenwenWan/TLaser.git
cd TLaser

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # On Windows PowerShell

# Install required libraries
pip install -r requirements.txt
```

### Troubleshooting Environment Setup
* **PyTorch CPU Wheel issues**: On systems without a CUDA GPU, pip might attempt to install CUDA-enabled PyTorch which can be large or fail. Use:
  ```powershell
  pip install torch --extra-index-url https://download.pytorch.org/whl/cpu
  ```
* **Missing matplotlib or OpenCV**: Verify that your path points to the virtual environment interpreter (`.venv\Scripts\python.exe`) rather than the global system Python.

---

## 3. High-Fidelity Dataset Generation

The dataset generator runs random parameter sweeps over the 7D design domain.

> [!NOTE]
> **Simulator Nature**: The current simulator core is a synthetic quasi-3D solver that couples axial wave propagation and multi-quantum well carrier rates. It acts as the canonical high-fidelity simulator for the TLaser digital twin prototype.

### Sweep Boundaries
* Mirror reflectivities: $R_1 \in [0.1, 0.95]$, $R_2 \in [0.05, 0.5]$
* Cavity dimensions: Length $L \in [100, 1000]\,\mu\text{m}$, Ridge Width $w \in [1.5, 4.0]\,\mu\text{m}$, Thickness $d \in [0.1, 0.5]\,\mu\text{m}$
* Environmental inputs: Temperature $T_0 \in [250, 360]\,\text{K}$, Injection Current $I_{\text{active}} \in [0.01, 0.5]\,\text{A}$

### Execution Commands
* **Run full sweeps (1500 samples)**:
  ```powershell
  python simulator/generate_dataset.py --num-samples 1500
  ```
* **Run quick smoke test**:
  ```powershell
  python simulator/generate_dataset.py --smoke-test
  ```
Outputs are saved in `data/` as `pinn_inputs.npy` and `pinn_targets.npy`, alongside `pinn_dataset_metadata.json`.

---

## 4. Physics-Informed Neural Network Training

The PINN model trains a surrogate to reproduce the laser behavior under physical boundary penalties.

### Optimization Penalties
1. **Data Loss**: Matches predicted output power, WPE, current, and profile points against simulator targets.
2. **Carrier Rate Equation Residual**:
   $$G_{\text{inj}} - R_{\text{rec}}(N(z)) - R_{\text{stim}}(N(z), P(z)) = 0$$
3. **Photon Propagation Wave Residual (Second-Order Approximation)**:
   $$\frac{d^2P}{dz^2} - (\Gamma g(z) - \alpha_i)^2 P(z) = 0$$
   *Note: Using a second-order wave equation on total power is an accepted reduced-order physical approximation, avoiding the separate prediction of forward/backward field components.*
4. **Laplacian Smoothness Regularization**: Smooths predicted carrier and power curves.

### Execution Commands
* **Run full training (600 epochs)**:
  ```powershell
  python surrogate/train.py --epochs 600
  ```
* **Run quick smoke test**:
  ```powershell
  python surrogate/train.py --smoke-test
  ```
Saves weights to `data/pinn_laser_model.pt` and training convergence history to `data/pinn_training_loss.svg`.

---

## 5. Parameter Calibration Loop

The calibration engine matches the digital twin with a real physical device by fitting drifted or unknown physical properties.

### Input Data Schemas
* **JSON File**: Must contain arrays for `current_A`, `voltage_V`, and `optical_power_W`.
  ```json
  {
    "current_A": [0.05, 0.1, 0.15],
    "voltage_V": [1.02, 1.05, 1.08],
    "optical_power_W": [0.005, 0.02, 0.04]
  }
  ```
* **CSV File**: Must have a single header row followed by columns in the order: `Current (A)`, `Voltage (V)`, `Power (W)`.

### Execution Commands
* **Run calibration on mock monitoring data**:
  ```powershell
  python calibration/calibrate.py
  ```
* **Run calibration on external monitored file**:
  ```powershell
  python calibration/calibrate.py --data-file data/monitored_liv.json
  ```
Saves fitted constants to `data/calibrated_params.json` and generates the L-I-V fit comparison chart in `data/calibration_fit.svg`.

---

## 6. Automated Pipeline Verification

To verify the end-to-end environment, code syntax, and data workflows in a single click, run:
```powershell
python verify_pipeline.py
```

---

## 7. Interactive App Dashboard

To launch the real-time digital twin and online calibration dashboard, execute:
```powershell
python -m streamlit run app.py
```
This runs the web interface locally on `http://localhost:8501`, supporting bilingual English and Chinese views.
