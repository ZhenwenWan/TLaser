# TLaser - Real-Time Digital Twin & Parameter Calibration Diode Laser Platform

The local dashboard now includes a shared, versioned ridge-device configuration,
interactive Lasers 15-part 3D geometry, configuration save/load, and fixed-geometry calibration
comparison. Start it with `./run_tlaser.ps1`; see
[the first-release guide](Doc/device_model_release.md) for supported workflows,
measurement semantics and limitations. Fitted prediction uses the physical
simulator; the existing seven-input PINN remains a nominal predictor.

The edge-emitter workspace has five shared-device sections in English and Chinese:

1. **Device model** — edit and save the device configuration; inspect the Lasers 15-part 3D geometry.
2. **Simulator core** — four configurable workspaces: Lasers/Gmsh mesher, transverse 2D solver, longitudinal 1D solver, and iterative 1D–2D optothermal coupling. Each supports configuration load/save, saved-run restoration and visualization. Field results include potential, carrier density, temperature and complex EM fields, with CSV/VTU export and feedback residual history.
3. **PINN surrogate** — generate a seven-input dataset by repeatedly calling the simulator, train a physics-informed network, inspect held-out validation/test errors, export the model and explicitly activate models that pass the configured gates.
4. **Instant Performance Prediction** — obtain operating-point metrics and longitudinal profiles using the nominal PINN or physical simulator, including accepted fitted constants.
5. **Instant Parameter Calibration** — upload L-I-V data or run a synthetic demo, inspect fit diagnostics, and apply accepted constants to simulator predictions.

Simulation and PINN comparison reports are flagged as stale after a device change.
Calibration remains an iterative solver; the section name does not promise a fixed
latency. The full 3D geometry is a reference visualization, while the connected
physics engines include the reduced longitudinal predictor, Lasers transverse coupled solver,
and a longitudinal Poisson/drift-diffusion, thermal and scalar-wave solver. The latter
uses driven passive optical-probe boundaries; it does not predict self-lasing output.
The two-way field workflow exchanges averaged optical heating and MQW temperature.
See the CAE guide for assumptions and convergence checks. VCSEL remains a separate
demonstration with its existing prediction and calibration modes.

TLaser is a reduced-model Physics-Informed Neural Network (PINN) prediction and
parameter calibration prototype for edge-emitting telecom semiconductor diode
lasers. It combines a synthetic longitudinal simulator, a nominal surrogate, and
bounded inverse fitting. Measured-device accuracy and end-to-end response latency
require separate validation; this release does not establish a sub-5-ms guarantee.

---

## 1. Physical & Mathematical Formulation

### Coupled Carrier Rate Equation
The carrier density distribution $N(z)$ along the cavity length $z \in [0, L]$ is governed by:
$$G_{\text{inj}} - R_{\text{rec}}(N(z)) - R_{\text{stim}}(N(z), P_{\text{tot}}(z)) = 0$$

Where:
* **Injection rate**: $G_{\text{inj}} = \frac{I_{\text{active}}}{q_0 \cdot L \cdot w_{\text{active}} \cdot d_{\text{active}}}$
* **Recombination rate**: $R_{\text{rec}} = A \cdot N + B \cdot N^2 + C \cdot N^3$
* **Stimulated emission rate**: $R_{\text{stim}} = \frac{g(N) \cdot P_{\text{tot}}(z)}{w_{\text{active}} \cdot d_{\text{active}} \cdot E_{\text{phot}}}$

### Longitudinal optical transport
The simulator propagates forward and backward powers. New training jobs enforce
their discrete transport equations using total power $S=P^++P^-$ and difference
$D=P^+-P^-$, with $k=\Gamma g-\alpha_i$ and spontaneous source $s$:
$$S'=kD,\qquad D'=kS+2s,\qquad D(0)=\frac{R_1-1}{R_1+1}S(0).$$
The carrier residual uses the configured Auger multiplier, and the optical
residual uses the configured confinement and internal loss. Existing bundled
weights are retained; these changes apply to newly trained models.

### Run the CAE workflows

See [the CAE guide](Doc/cae_implementation.md) for setup, validation evidence,
fidelity boundaries and remaining engineering work. Jobs persist under `runs/`
and continue across page refreshes. They are local artifacts, excluded from Git.
The compatible Lasers runtime and its custom libraries are required for spatial
field simulation; PINN dataset generation uses the built-in longitudinal solver.

---

## 2. Installation & Quickstart

### Open the latest 3D revision on Windows

Stop any older TLaser server with `Ctrl+C` in its PowerShell window. If you are
using an older checkout, update its launcher once:

```powershell
cd C:\Users\aw4wz\TLaser  # Or your own TLaser checkout directory
git pull --ff-only origin main
.\run_tlaser.ps1
```

The launcher now checks GitHub on each start, updates clean `main` checkouts
with fast-forward merges, installs Plotly if missing, validates the geometry,
and prints the folder and revision being launched. It preserves local edits;
offline starts use the local revision with a warning. `-SkipUpdate` runs the
local revision, `-CheckOnly` validates without starting a server, and
`-UpdateOnly` updates the checkout without launching or installing dependencies.
An occupied port produces a message instead of silently reusing an older app.
Use `-Port 8518` to run alongside an existing server.

Open `http://127.0.0.1:8501` and keep PowerShell running. The geometry view
includes **True proportions**, **Show substrate and facet coatings**, and
**Layer separation** controls, plus 15 material parts in the legend. Drag to
rotate, scroll to zoom, and click legend entries to inspect individual layers.
The imported reference stack is a geometric visualization; reduced solver
width/thickness do not redefine its epitaxial layer dimensions.

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

---

## 8. Strategic Industrial Autonomy & Closed-Loop Twins

TLaser is positioned to address key bottlenecks in the telecom optical chip supply chain:
* **The High-Speed Bottleneck**: In 2025, the global optical transceiver market reached 160 billion RMB. While China is a manufacturing giant for transceivers, core components like high-speed DFB and EML laser chips are still catching up with US/Japan counterparts.
* **Closed-loop Twin Paradigm**: Modern manufacturing suffers from material variations and process tolerances. General commercial tools like Crosslight PICS3D and Ansys Lumerical are forward solvers. True autonomy requires a closed-loop digital twin that unifies forward modeling and inverse data calibration (analogous to meteorological data assimilation).
* **Open Partnership**: TLaser's software core (Lasers) and surrogate compiler (PLaser) are fully built. The next phase targets industry partnerships with DFB/EML fabs and testing facilities to ingest real experimental data.


