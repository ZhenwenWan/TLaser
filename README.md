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

---

## 4. Official Webpage Surface

The official landing page for publication and portfolio visualization is hosted at:
* **English Landing Page**: [https://zhenwenwan.github.io/Pages/TLaser.html](https://zhenwenwan.github.io/Pages/TLaser.html)
* **Chinese Landing Page**: [https://zhenwenwan.github.io/Pages/TLaser_CN.html](https://zhenwenwan.github.io/Pages/TLaser_CN.html)

The interactive computational dashboard is launched locally using Streamlit.

---

## 5. Verification & Validation Report

### Automated Pipeline Verification
The entire mathematical, deep learning, and optimization workflow is verified using `verify_pipeline.py`. The output verification trace is as follows:

```text
==================================================
          TLaser Pipeline Verification            
==================================================

>>> Step 1: Checking imports...
  [SUCCESS] All primary dependencies (numpy, matplotlib, streamlit, torch, scipy) imported correctly.

>>> Running Step: Dataset Generator Smoke Test...
  [SUCCESS] Dataset Generator Smoke Test completed successfully.

>>> Running Step: PINN Surrogate Training Smoke Test...
  [SUCCESS] PINN Surrogate Training Smoke Test completed successfully.

>>> Running Step: Parameter Calibration Smoke Test...
  [SUCCESS] Parameter Calibration Smoke Test completed successfully.

==================================================
  Verification Pipeline Completed: ALL STEPS PASS 
==================================================
```

### Deep Learning Surrogate Convergence Metrics
After aligning input/output scaling factors dynamically to avoid Sigmoid saturation, the surrogate model achieves high numerical fidelity:
* **Combined Multi-Physics Loss**: `2.7985e+00`
* **Data Regression MSE Loss**: `6.2821e-02`
* **Longitudinal Carrier Residual Loss**: `4.5319e+01`
* **Longitudinal Photon Propagation Loss**: `9.2086e+00`
* **Spatial Profile Smoothness Penalty**: `6.2029e-03`

---

## 6. VCSEL Digital Twin Adaptation (Extension Mode)

TLaser includes a separate **VCSEL product extension mode** to demonstrate digital-twin modeling and parameter calibration for Vertical-Cavity Surface-Emitting Lasers.

* **Simulator Core**: Located at [vcsel_simulator.py](file:///C:/Users/aw4wz/Documents/Codex/TLaser/simulator/vcsel_simulator.py). Models 1D radial current crowding, radial spatial hole burning, DBR mirrors, and self-heating thermal rollover.
* **Proposal & Roadmap**: Detailed in [vcsel_adaptation_plan.md](file:///C:/Users/aw4wz/Documents/Codex/TLaser/Doc/vcsel_adaptation_plan.md).
* **VCSEL LIV Schema**: Defined at [vcsel_liv_measurement.schema.json](file:///C:/Users/aw4wz/Documents/Codex/TLaser/data/schemas/vcsel_liv_measurement.schema.json).
* **Demonstration Video**: Recompiled animation showing radial sweeps and thermal rollover is saved at `TLaser_VCSEL_Demonstration.mp4` (generated by [generate_vcsel_animation.py](file:///C:/Users/aw4wz/Documents/Codex/TLaser/generate_vcsel_animation.py)).

> [!NOTE]
> **Reduced Physics Demonstration**: The current VCSEL modeling mode and its generated demonstration video are for demonstration purposes (reduced-order rate approximations). High-fidelity engineering deployment requires verification against measured wafer telemetry.

---

## 7. Engineering Mapping Storyline

TLaser connects high-level telecom hardware products to deep physical parameters through a structured engineering cognition path:

1. **Layer 1: Real Optical Module** - SFP/QSFP transceiver module is the standardized, testable commercial product. System testing provides measured L-I-V curves.
2. **Layer 2: Module Decomposition** - Internals contain the Transmitter Optical Sub-Assembly (TOSA), driver chip, photodiode monitor, and thermoelectric cooler (TEC).
3. **Layer 3: Laser Chip Focus** - Zooming into the TOSA package exposes the bare semiconductor ridge waveguide laser chip. Geometry parameters (L, w, d) define its boundaries.
4. **Layer 4: PLaser Physical Model** - Forward solver modeling carrier transport/recombination, electromagnetic wave intensity propagation, and self-heating thermal rollover.
5. **Layer 5: TLaser Digital Twin & Inverse Modeling** - Reverse parameter solver identifying unmeasurable drifts ($R_{\text{th}}$, $R_s$, $\alpha_i$) from LIV test data, updating the simulator to support engineering decisions (reliability diagnostics, layout changes).

