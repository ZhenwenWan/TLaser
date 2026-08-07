# TLaser - Real-Time Digital Twin & Parameter Calibration Diode Laser Platform

TLaser is an advanced Physics-Informed Neural Network (PINN) surrogate modeling and online parameter calibration platform for edge-emitting telecom semiconductor diode lasers. By combining a high-fidelity simulator core with a deep learning surrogate and an active optimization loop, TLaser maps and aligns physical laser performance to real-world characteristics in under 5 milliseconds.

---

## 1. Physical & Mathematical Formulation

### Coupled Carrier Rate Equation
The carrier density distribution $N(z)$ along the cavity length $z \in [0, L]$ is governed by:
$$G_{\text{inj}} - R_{\text{rec}}(N(z)) - R_{\text{stim}}(N(z), P_{\text{tot}}(z)) = 0$$

Where:
* **Injection rate**: $G_{\text{inj}} = \frac{I_{\text{active}}}{q_0 \cdot L \cdot w_{\text{active}} \cdot d_{\text{active}}}$
* **Recombination rate**: $R_{\text{rec}} = A \cdot N + B \cdot N^2 + C \cdot N^3$
* **Stimulated emission rate**: $R_{\text{stim}} = \frac{g(N) \cdot P_{\text{tot}}(z)}{w_{\text{active}} \cdot d_{\text{active}} \cdot E_{\text{phot}}}$

### Photon Propagation Wave Equation
The optical wave propagation is modeled using the second-order total-power intensity wave equation:
$$\frac{d^2P}{dz^2} - (\Gamma g(z) - \alpha_i)^2 P(z) = 0$$

> [!NOTE]
> **Total Power Approximation**: Enforcing a second-order wave intensity derivative for the total power profile $P(z) = P^+(z) + P^-(z)$ is an intentional, accepted reduced-order physical approximation. This formulation allows the neural network to avoid predicting separate forward and backward wave components, reducing target dimensions while preserving the physical wave intensity curvature along the longitudinal cavity axis.

---

## 2. Installation & Quickstart

Initialize the virtual environment and install dependencies in a PowerShell window:
```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### Run Automated Pipeline Verification
Confirm the entire setup is operational by running the unified test script:
```powershell
python verify_pipeline.py
```

---

## 3. Execution Commands

### Step 1: High-Fidelity Dataset Generation
Compile simulation sweeps over the 7D parameter space:
```powershell
python simulator/generate_dataset.py --num-samples 1500
```
*(For rapid checks, run: `python simulator/generate_dataset.py --smoke-test`)*

### Step 2: PINN Surrogate Training
Train the surrogate neural network with data and physics constraints:
```powershell
python surrogate/train.py --epochs 600
```
*(For rapid checks, run: `python surrogate/train.py --smoke-test`)*

### Step 3: Parameter Calibration Loop
Fit physical laser parameter drifts against real-time measured L-I-V curves:
```powershell
python calibration/calibrate.py
```

### Step 4: Streamlit Dashboard App
Launch the interactive bilingual control dashboard:
```powershell
python -m streamlit run app.py
```
Open your browser at `http://localhost:8501`.
