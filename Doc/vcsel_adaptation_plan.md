# VCSEL Digital Twin Adaptation Plan

This document outlines the engineering proposal and implementation roadmap for extending **TLaser** from edge-emitting semiconductor lasers to **Vertical-Cavity Surface-Emitting Lasers (VCSELs)**.

---

## 1. Physical & Mathematical Models

VCSEL physics are dominated by transverse and radial profiles rather than longitudinal propagation. The core model adaptations will include:

### Radial Current Crowding
The contact geometry and oxide aperture profile squeeze current through the active region. The injected current density $J(r)$ exhibits crowding near the oxide boundary:
$$J(r) = J_0 \cdot \exp\left(-\frac{(r - R_{\text{ap}})^2}{w_{\text{crowd}}^2}\right)$$
Where $R_{\text{ap}}$ is the aperture radius and $w_{\text{crowd}}$ is the width of current crowding.

### Radial Carrier Diffusion & Spatial Hole Burning
The 1D radial carrier rate equation is solved along $r \in [0, R_{\text{contact}}]$:
$$D_N \left( \frac{\partial^2 N}{\partial r^2} + \frac{1}{r} \frac{\partial N}{\partial r} \right) + \frac{\eta_i I(r)}{q V_{\text{act}}} - R_{\text{rec}}(N(r)) - v_g g(N(r)) S(r) = 0$$

### Standing-Wave Cavity Loss
Instead of mirror reflectivity coatings $R_1/R_2$ representing sliced end-facets, the cavity loss is determined by DBR stacking:
$$\alpha_m = \frac{1}{2 L_{\text{eff}}} \ln\left(\frac{1}{R_{\text{top}} R_{\text{bottom}}}\right)$$

### Self-Heating & Thermal Rollover
The optical mode detuning and threshold shifts are solved using thermal feedback:
$$T_{\text{junction}} = T_{\text{ambient}} + (I \cdot V - P_{\text{opt}}) \cdot R_{\text{th}}$$
$$I_{\text{th}}(T) = I_{\text{th0}} + b \cdot (T - T_{\text{gain-cavity}})^2$$

---

## 2. Dataset Generation Strategy
* **Simulator**: [`simulator/vcsel_simulator.py`](file:///C:/Users/aw4wz/Documents/Codex/TLaser/simulator/vcsel_simulator.py).
* **Sampling Space (6D)**:
  * Aperture diameter $d_{\text{ap}} \in [4.0, 12.0]\,\mu\text{m}$
  * Top DBR reflectivity $R_{\text{top}} \in [0.990, 0.998]$
  * Thermal resistance $R_{\text{th}} \in [1000, 2500]\,\text{K/W}$
  * Operating current $I_{\text{inj}} \in [0, 15]\,\text{mA}$
  * Ambient temperature $T_{\text{ambient}} \in [250, 360]\,\text{K}$
  * Cavity length deviation $\Delta L_{\text{eff}} \in [-0.1, 0.1]\,\mu\text{m}$
* **Outputs**: Scalar metrics ($I_{\text{th}}$, $P_{\text{opt}}$, $V_{\text{term}}$, WPE, $T_{\text{junction}}$) and radial profiles ($N(r)$, $I(r)$, Mode shape).
* **Storage Location**: `data/datasets/vcsel/` directory, keeping it separate from EEL datasets.

---

## 3. PINN Surrogate Loss Architecture
1. **Data Loss (MSE)**: Regression target values.
2. **Radial Carrier Equation Residual**: Backpropagates numerical errors in the radial rate equations.
3. **Radial Wave Equation (Helmholtz) Constraint**: Enforces physical boundaries on the Gaussian mode profile.
4. **Smoothness Regularization**: Controls spatial gradients along the radial coordinate.

---

## 4. Calibration Parameters
The SciPy optimization loop in the VCSEL mode will solve for:
* **$d_{\text{ap}}$** (Oxide aperture diameter)
* **$R_{\text{th}}$** (Thermal resistance)
* **$R_{\text{top}}$** (Top DBR reflectivity)
* **$R_s$** (Series contact resistance)
* **$C_{\text{recomb}}$** (Auger coefficient multiplier)

Monitored telemetry will include a spectral wavelength red-shift channel ($\Delta \lambda$ vs $I$) to isolate temperature rise independently from electrical dissipation.

---

## 5. Verification & Validation Roadmap
1. Build `tests/test_vcsel_simulator.py` to check energy conservation.
2. Validate against digitized datasheet curves for common VCSELs (e.g. Lumentum/II-VI baselines).
3. Confirm calibration convergence of $R_{\text{th}}$ using simulated noisy datasets.
