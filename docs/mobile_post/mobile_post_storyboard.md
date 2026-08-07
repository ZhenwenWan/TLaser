# TLaser Mobile Storyboard & Presentation Plan

This storyboard structures the mobile-screen slide presentations (9:16 aspect ratio) for sharing TLaser's capabilities on social networks, video stories, or mobile viewports.

---

## Storyboard Slides Sequence

### Slide 1: Cover Screen
* **File Name**: `docs/mobile_post/cover.png`
* **Order**: 1
* **Headline**: TLaser
* **Body Text**: Real-time semiconductor laser diode digital twin platform. Predict and calibrate L-I-V parameters instantly.
* **Visual Asset**: Hero rendering of butterfly-packaged telecom laser chip with glowing ridge waveguide core.
* **Regeneration Command**: `python -m streamlit run app.py`

### Slide 2: The Core Problem
* **File Name**: `docs/mobile_post/problem.png`
* **Order**: 2
* **Headline**: Physics is Precise but Slow
* **Body Text**: 2D finite-element CAE simulations take tens of seconds per sweep. Live monitoring demands millisecond responses.
* **Visual Asset**: Simplified flow tracing 2D Elmer mesh solver to 1D cavity spatial hole burning (SHB) discretization.
* **Regeneration Command**: `python simulator/generate_dataset.py`

### Slide 3: TLaser Workflow
* **File Name**: `docs/mobile_post/workflow.png`
* **Order**: 3
* **Headline**: High-Fidelity to PINN
* **Body Text**: 1. High-Fidelity Simulation Sweeps -> 2. Physics-Informed NN Training -> 3. Instant Predictions -> 4. Real-time L-I-V Parameter Calibration.
* **Visual Asset**: Flow chart linking the 7D parametric workspace inputs to the output metrics.
* **Regeneration Command**: `python verify_pipeline.py`

### Slide 4: Instant Predictions
* **File Name**: `docs/mobile_post/dashboard_mobile.png`
* **Order**: 4
* **Headline**: Millisecond Predictions
* **Body Text**: Real-time sweeps of cavity length, widths, temperature, and mirror coatings under 5 milliseconds latency.
* **Visual Asset**: Mobile crop of Streamlit dashboard showing longitudinal carrier density $N(z)$ and optical power $P(z)$ profile plots.
* **Regeneration Command**: `python -m streamlit run app.py`

### Slide 5: Active Calibration
* **File Name**: `docs/mobile_post/calibration_mobile.png`
* **Order**: 5
* **Headline**: Fit Drifting Physics
* **Body Text**: Automatically calibrate internal loss, confinement factor, Auger scaling, series resistance, and junction shunt leakage.
* **Visual Asset**: Noisy monitored telemetry points overlaid with the optimized model fit curve.
* **Regeneration Command**: `python calibration/calibrate.py`

### Slide 6: Hardened Data Quality
* **File Name**: `docs/mobile_post/data_quality_mobile.png`
* **Order**: 6
* **Headline**: Zero Scaling Clipping
* **Body Text**: Aligned physical current ranges and adaptive dataset-driven scaling boundaries yield 100,000x lower training loss.
* **Visual Asset**: Train loss history plot converging cleanly below 2.5 combined MSE.
* **Regeneration Command**: `python surrogate/train.py`

### Slide 7: Clear Limitations
* **File Name**: `docs/mobile_post/limitations.png`
* **Order**: 7
* **Headline**: Engineering Integrity
* **Body Text**: Built as a fast quasi-3D mathematical surrogate, not a replacement for full multi-mesh TCAD/FEM waveguide signoff.
* **Visual Asset**: Visual warnings with clear validation boundaries.
* **Regeneration Command**: N/A

### Slide 8: Run Locally
* **File Name**: `docs/mobile_post/cta.png`
* **Order**: 8
* **Headline**: Download & Test
* **Body Text**: Clone from GitHub. Set up venv and run dashboard: `python -m streamlit run app.py`.
* **Visual Asset**: GitHub repository URL and contact information (aw4wzw@gmail.com).
* **Regeneration Command**: N/A
