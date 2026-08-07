# TLaser User Manual

Welcome to **TLaser**, the Digital Twin Control Center for telecom diode lasers. This manual provides installation instructions, mathematical formulations, execution steps for the simulation and training pipelines, and details on online parameter calibration.

---

## 1. Project Overview

TLaser creates a high-fidelity reduced-order digital twin of a telecom semiconductor laser. It bridges the gap between slow, multi-physics numerical solvers and real-time operational needs by combining:
1. **Quasi-3D Simulator Core**: Solves longitudinal carrier density and wave propagation.
2. **Physics-Informed Neural Network (PINN)**: Maps 7D design parameters to 105D space arrays in under 5 milliseconds.
3. **Monitored L-I-V Parameter Calibration**: Fits internal parameter drift against real-time measured Light-Current-Voltage curves.

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

---

## 3. High-Fidelity Dataset Generation

The dataset generator runs random parameter sweeps over the 7D design domain.

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
3. **Photon Propagation Wave Residual**:
   $$\frac{d^2P}{dz^2} - (\Gamma g(z) - \alpha_i)^2 P(z) = 0$$
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

### Calibration Parameters
* **$\alpha_i$ (Internal Loss)** & **$\Gamma$ (Confinement)**: Adjusts the laser threshold and optical slope efficiency.
* **$C_{\text{multiplier}}$**: Adjusts the Auger non-radiative recombination thermal droop.
* **$R_{\text{series}}$** & **$R_{\text{shunt}}$**: Adjusts the terminal voltage drop and current leakage channels.

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

## 6. Interactive App Dashboard

To launch the real-time digital twin and online calibration dashboard, execute:
```powershell
python -m streamlit run app.py
```
This runs the web interface locally on `http://localhost:8501`, supporting bilingual English and Chinese views.
