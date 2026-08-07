# TLaser Inspection Report

Inspector: Codex
Implementation developer: Antigravity
Date: 2026-08-07

## Inspection Scope

This inspection compares the current TLaser workspace against the implementation plan in `Doc/implementation_plan.md`.

The inspection covers:

- Current implementation status by planned phase.
- Plan deviations and technical comments.
- Recommended next tasks for the Antigravity implementation cycle.
- Suggested iteration protocol between Codex and Antigravity.

## Repository State Summary

The TLaser workspace currently contains the planned top-level structure:

- `simulator/`
- `surrogate/`
- `calibration/`
- `data/`
- `Doc/`

Generated artifacts are present in `data/`, including the simulation dataset, trained model file, scaling parameters, training loss plot, and calibrated parameter output.

The whole `TLaser` folder currently appears untracked from the parent Git repository context. If version control is desired, the next development cycle should decide whether TLaser should be initialized as its own repository or added intentionally to the parent repository.

## Phase 1 Inspection: High-Fidelity Dataset Generation

Status: Mostly implemented.

Implemented files:

- `simulator/quasi_3d_synthesizer.py`
- `simulator/generate_dataset.py`

Implemented behavior:

- The quasi-3D simulator exposes a `Quasi3DSimulator` class.
- The simulator supports cavity length, reflectivities, active-region width/depth, ambient temperature, internal loss, and other physical constants.
- The solver computes longitudinal carrier density, gain, forward/backward optical power, total optical power, electrical power, total current, and WPE.
- The dataset generation script samples the planned 7D parameter space:
  - `R1`
  - `R2`
  - `L`
  - `T0`
  - `I_active`
  - `w_active`
  - `d_active`
- The generated dataset artifacts exist:
  - `data/pinn_inputs.npy`
  - `data/pinn_targets.npy`

Verified artifact shapes:

- `pinn_inputs.npy`: `(1500, 7)`
- `pinn_targets.npy`: `(1500, 105)`

Inspector comments:

- The implementation uses uniform random sampling, which is allowed by the plan.
- The simulator is currently a synthetic quasi-3D implementation rather than a direct coupled Elmer FEM + FVM solver port from the `Lasers` project. This may be acceptable for a reduced prototype, but it should be named explicitly in documentation.
- `generate_dataset.py` has fixed sample count and random seed. For iterative testing, Antigravity should add CLI arguments such as `--num-samples`, `--seed`, and `--output-dir`.
- Failed simulator samples are silently skipped with `except Exception: continue`. Antigravity should log skipped samples and failure counts so data quality can be inspected.

Recommended next actions for Phase 1:

- Add a small dataset smoke-test mode.
- Add metadata output beside the `.npy` files, including parameter ranges, sample count, seed, simulator version, and generation timestamp.
- Decide whether to keep the synthetic simulator as the canonical high-fidelity source or later replace it with the actual Lasers/Elmer workflow.

## Phase 2 Inspection: PINN Surrogate

Status: Partially implemented.

Implemented files:

- `surrogate/model.py`
- `surrogate/train.py`

Implemented behavior:

- `PINNLaser` maps 7 inputs to 105 outputs.
- `train.py` loads generated dataset files.
- Input/output scaling is implemented.
- Scaling parameters are saved to `data/pinn_scale_params.npz`.
- The training loop includes:
  - data MSE loss,
  - carrier continuity residual at selected grid nodes,
  - first- and second-difference smoothness regularization.
- Trained weights are saved to `data/pinn_laser_model.pt`.
- A training loss plot is saved to `data/pinn_training_loss.svg`.

Inspector comments:

- The plan calls for total loss:
  - data loss,
  - carrier residual loss,
  - photon residual loss.
- The current implementation includes carrier residual and smoothness regularization, but it does not implement the planned photon propagation residual.
- The plan mentions `scipy.signal.savgol_filter`; the current training script does not use Savitzky-Golay filtering.
- The network output uses a final `Sigmoid`, which assumes all scaled targets lie in `[0, 1]`. Antigravity should verify target scaling bounds are never exceeded. If scaled targets exceed this range, the final sigmoid may cap valid physical outputs.
- The carrier residual is evaluated only at nodes `[0, 12, 25, 37, 50]`, while the plan describes enforcement along the 51 grid points. This is a pragmatic approximation, but it should be documented or extended.
- The current artifact `pinn_laser_model.pt` exists, but the available inspection runtime does not have PyTorch installed, so Codex could not load and verify the model weights.

Recommended next actions for Phase 2:

1. Implement photon propagation residual in `surrogate/train.py`.
2. Add a lightweight training smoke-test mode, for example `--epochs 5 --limit-samples 50`.
3. Add validation metrics after training:
   - scalar prediction error for `P_opt`, `WPE`, and `I_total`,
   - profile error for `N(z)` and `P(z)`,
   - carrier residual summary,
   - photon residual summary.
4. Revisit final activation and scaling strategy.
5. Decide whether Savitzky-Golay smoothing should be applied during post-processing, loss computation, or omitted in favor of differentiable smoothness penalties.

## Phase 3 Inspection: Calibration Loop

Status: Partially implemented.

Implemented file:

- `calibration/calibrate.py`

Implemented behavior:

- Calibration uses `scipy.optimize.minimize`.
- A mock monitoring dataset is generated internally.
- The optimizer fits:
  - `alpha_i`
  - `Gamma`
  - `I_shunt_unit`
  - `R_series`
- Calibrated parameters are saved to `data/calibrated_params.json`.

Current calibrated output:

```json
{
  "alpha_i": 10.003268382167423,
  "Gamma": 0.045960094395270795,
  "I_shunt_unit": 485.9995778257842,
  "R_series": 0.792333342765451,
  "success": true,
  "mse": 0.0007802920192957552
}
```

Inspector comments:

- The plan calls for real-time monitored L-I-V inputs at different heatsink temperatures. The current implementation uses mock data only.
- The plan calls for fitting Auger recombination coefficient `C` and shunt resistance `R_sh`. The current implementation fits a shunt current scale, but not `C` or explicit `R_sh`.
- The calibration currently calls the quasi-3D simulator directly for every optimizer evaluation. This is acceptable for the prototype, but the digital twin plan implies using the trained surrogate for reduced-order real-time calibration.
- The voltage model is a simplified diode-plus-series-resistance expression. If terminal voltage accuracy matters, Antigravity should document the model assumptions and add an explicit shunt resistance model.

Recommended next actions for Phase 3:

1. Add a real monitoring data input interface, such as CSV/JSON with columns:
   - `temperature_K`
   - `current_A`
   - `voltage_V`
   - `optical_power_W`
2. Extend calibration parameters to include:
   - Auger coefficient multiplier or absolute `C_recomb`,
   - explicit `R_sh`,
   - optionally `B_recomb` or gain scale if monitoring data supports identifiability.
3. Add calibration result diagnostics:
   - before/after L-I-V fit errors,
   - per-temperature residuals,
   - fitted parameter bounds status,
   - optimizer success message.
4. Decide whether calibration should use:
   - direct simulator calls for accuracy,
   - PINN surrogate calls for speed,
   - a hybrid strategy.

## Verification Plan Inspection

Status: Not yet formalized as automated tests.

The implementation plan asks for:

- Data generation test.
- Model training test.
- Calibration test.

Current state:

- Dataset artifacts exist and have expected shapes.
- Simulator smoke run succeeded during inspection.
- Calibration output exists and reports success.
- No dedicated automated test files or smoke-test commands are present.
- The inspection runtime lacks PyTorch and SciPy, so full training/calibration verification could not be rerun in this environment.

Recommended next actions for verification:

- Add `requirements.txt` or `pyproject.toml`.
- Add `scripts/verify_pipeline.py` or equivalent.
- Add quick CLI modes to long-running scripts.
- Record exact commands used to regenerate all artifacts.
- Include dependency checks with clear error messages.

## Inspector Priority List for Antigravity

Priority 1:

- Add project dependency specification.
- Add CLI smoke-test modes for dataset generation, training, and calibration.
- Implement the missing photon residual loss in `surrogate/train.py`.
- Review the concepts and methods already established in PLaser and identify which patterns should be reused for TLaser.

Priority 2:

- Add real monitoring data ingestion to `calibration/calibrate.py`.
- Extend calibration to fit `C_recomb` and explicit `R_sh`.
- Add validation diagnostics and plots for surrogate and calibration quality.
- Sync the TLaser application experience with the PLaser approach, including model loading, prediction workflow, calibration controls, and result visualization.
- Sync the TLaser webpage with the PLaser presentation pattern, while keeping TLaser-specific positioning focused on telecom diode-laser digital twins.

Priority 3:

- Improve dataset metadata and failure logging.
- Clarify whether the current quasi-3D simulator is the intended high-fidelity engine or a synthetic stand-in.
- Add documentation for artifact regeneration and expected runtime.
- Sync the TLaser manual with the PLaser documentation style, including installation, artifact regeneration, simulator usage, surrogate training, calibration workflow, and troubleshooting.
- Prepare a TLaser demo video plan following the PLaser demo method, showing the end-to-end workflow from simulation data to surrogate prediction and calibration.

## PLaser Alignment Tasks

Status: Not yet inspected or implemented in TLaser.

The next Antigravity implementation cycle should compare TLaser against PLaser and reuse compatible concepts, methods, and presentation patterns. Codex should then inspect whether the reuse is technically appropriate rather than only visually similar.

Required alignment tasks:

1. PLaser concept and method review
   - Identify reusable PLaser architecture decisions, model workflow conventions, UI structure, documentation format, and demo sequencing.
   - Record which PLaser concepts are adopted, adapted, or rejected for TLaser.
   - Avoid copying PLaser details that are specific to a different physical device or modeling assumption.

2. TLaser app sync
   - Create or update the TLaser app so it exposes the expected digital-twin workflow:
     - choose or load laser parameters,
     - run surrogate prediction,
     - visualize `P_opt`, `WPE`, `I_total`, `N(z)`, and `P(z)`,
     - load monitoring L-I-V data,
     - run calibration,
     - compare before/after calibration results.
   - Follow PLaser interaction patterns where they improve consistency.
   - Keep TLaser-specific controls for telecom diode-laser geometry, reflectivity, temperature, and current.

3. TLaser webpage sync
   - Create or update the TLaser webpage using the PLaser webpage as the reference pattern.
   - Present TLaser as a telecom diode-laser digital twin, not just a generic PINN example.
   - Include clear sections for simulator, surrogate, calibration, outputs, and verification artifacts.
   - Link or embed relevant generated outputs such as training loss and calibration diagnostics when available.

4. TLaser manual sync
   - Create or update the TLaser manual following the PLaser manual structure.
   - Minimum manual sections:
     - project purpose,
     - environment setup,
     - dataset generation,
     - surrogate training,
     - calibration with mock data,
     - calibration with real monitoring data,
     - app usage,
     - webpage/demo usage,
     - artifact regeneration,
     - troubleshooting.
   - Include exact commands once dependency management and CLI smoke modes are implemented.

5. TLaser demo video sync
   - Prepare a demo script and shot list following the PLaser demo method.
   - Minimum demo flow:
     - introduce TLaser and the telecom diode-laser digital-twin goal,
     - show the implementation plan,
     - run or explain data generation,
     - show surrogate prediction and profile visualization,
     - load mock or real L-I-V monitoring data,
     - run calibration,
     - compare pre- and post-calibration predictions,
     - point to the manual and webpage.
   - After app and webpage sync are complete, generate or record the actual demo video artifact.

Inspector comments:

- PLaser should be treated as a methodological reference, not as a blind template.
- TLaser documentation and UI should clearly state where the current simulator is synthetic quasi-3D versus a full high-fidelity Lasers/Elmer workflow.
- App, webpage, manual, and video work should not hide the remaining technical gaps in the PINN loss or calibration model.
- Codex should inspect these deliverables for consistency with the physical model, reproducibility, and clarity for future users.

## Codex and Antigravity Iteration Protocol

The intended workflow is:

1. Codex inspects the repository against `Doc/implementation_plan.md`.
2. Codex writes inspection comments and prioritizes next actions in this report.
3. Antigravity implements the next batch of changes.
4. Codex re-inspects the changed files and generated artifacts.
5. Codex updates this report with:
   - newly implemented items,
   - remaining deviations,
   - verification results,
   - next recommended tasks.

For each Antigravity implementation pass, Codex should focus review on:

- Whether the change matches the implementation plan.
- Whether physical equations are represented consistently.
- Whether outputs are reproducible.
- Whether generated artifacts can be verified from a clean environment.
- Whether new approximations are documented.

## Current Inspector Verdict

TLaser has a functional prototype skeleton for all three planned phases. Phase 1 is mostly complete for a synthetic quasi-3D workflow. Phase 2 and Phase 3 are present but incomplete relative to the implementation plan.

The next most important implementation task is to complete the PINN training objective by adding the photon propagation residual, then add smoke-test controls so future Codex inspections can verify the full pipeline quickly and repeatably.

---

## Further Inspection Update: 2026-08-07

This section records the next inspection pass after Antigravity implemented additional TLaser artifacts.

### Newly Observed Implementation Progress

Antigravity has added or updated the following items since the first inspection:

- `requirements.txt`
- `verify_pipeline.py`
- `app.py`
- `surrogate/pinn_surrogate.py`
- updated `surrogate/train.py`
- updated `simulator/generate_dataset.py`
- updated `calibration/calibrate.py`
- `Doc/TLaser_User_Manual.md`
- `Doc/TLaser_User_Manual_CN.md`
- `data/pinn_dataset_metadata.json`
- `data/calibration_fit.svg`

### Updated Status Against Previous Inspector Priorities

Status: meaningful progress.

Completed or partially completed items:

- Project dependency file has been added.
- Dataset generation now has CLI options and smoke-test mode.
- Dataset metadata is now generated and includes sample count, seed, parameter ranges, output shapes, failure count, and failure modes.
- Training now has CLI options and smoke-test mode.
- Training now includes a photon residual term.
- Training now reports final data, carrier, photon, and smoothness losses.
- Calibration now has CLI options and smoke-test mode.
- Calibration now supports external JSON/CSV monitoring data input.
- Calibration now fits `C_mult` and explicit `R_shunt`.
- Calibration now generates `calibration_fit.svg`.
- A Streamlit TLaser app has been added.
- English and Chinese manuals have been added.
- A verification pipeline script has been added.
- A surrogate wrapper has been added for model loading and prediction.

### Verification Performed

Codex ran Python syntax compilation on the updated Python files:

- `app.py`
- `simulator/generate_dataset.py`
- `surrogate/model.py`
- `surrogate/train.py`
- `surrogate/pinn_surrogate.py`
- `calibration/calibrate.py`
- `verify_pipeline.py`

Result: syntax compilation passed.

Codex also attempted to run `verify_pipeline.py` with the available inspection runtime.

Result: verification stopped at dependency import checks because the inspection runtime does not include `matplotlib`.

Observed verifier output:

```text
[FAILED] Dependency import check failed: No module named 'matplotlib'
Please run: pip install -r requirements.txt
```

Inspector comment:

- This is an environment limitation of the current inspection runtime, not proof that the TLaser project environment is invalid.
- The next implementation cycle should include an environment creation step or documented virtual environment path so Codex can run full verification reproducibly.

### Phase 1 Updated Inspection

Status: improved and mostly complete for the current synthetic simulator workflow.

Positive updates:

- `generate_dataset.py` now supports `--num-samples`, `--seed`, `--output-dir`, and `--smoke-test`.
- Failures are now counted and summarized.
- `pinn_dataset_metadata.json` exists and records a clean full run:
  - sample count: `1500`
  - total attempts: `1500`
  - failed solves: `0`
  - input shape: `[1500, 7]`
  - target shape: `[1500, 105]`

Remaining comments:

- The simulator is still a synthetic quasi-3D solver, not a verified direct Elmer/FVM high-fidelity workflow.
- Antigravity should add a short note in the manual and app saying whether this simulator is the canonical TLaser physics engine or a prototype stand-in.

### Phase 2 Updated Inspection

Status: improved but still needs technical review.

Positive updates:

- `train.py` now includes a photon residual term.
- `train.py` now supports smoke-test training.
- `train.py` now prints final loss components.
- `surrogate/pinn_surrogate.py` now applies Savitzky-Golay smoothing during prediction post-processing.

Inspector comments:

- The implementation plan describes the photon propagation constraint as first-order forward/backward equations for `P+` and `P-`.
- The current training implementation uses a second-order total-power approximation:
  - `d2P/dz2 - (Gamma*g(z) - alpha_i)^2 * P(z) = 0`
- This may be a useful approximation, but it is not the same as enforcing the planned first-order propagation residuals because the surrogate target only stores total `P(z)`, not separate `P_plus(z)` and `P_minus(z)`.
- Antigravity should either:
  - update the dataset target to include `P_plus` and `P_minus`, then implement the planned first-order residuals, or
  - document the second-order total-power residual as an intentional reduced approximation.
- The carrier residual still uses selected nodes rather than all 51 nodes. This is acceptable for speed, but should be documented.
- `surrogate/model.py` still uses a final `Sigmoid`; Antigravity should verify scaled targets are within `[0, 1]` or change the output strategy.

### Phase 3 Updated Inspection

Status: improved but one app integration bug is likely present.

Positive updates:

- `calibrate.py` now fits:
  - `alpha_i`
  - `Gamma`
  - `C_mult`
  - `R_series`
  - `R_shunt`
- `calibrate.py` now supports `--data-file`.
- `calibrate.py` now supports JSON and CSV input.
- `calibration_fit.svg` exists.
- Current `calibrated_params.json` includes the expanded parameter set and reports success.

Current calibrated output:

```json
{
  "alpha_i": 10.003136420656741,
  "Gamma": 0.04467014470513994,
  "C_mult": 1.01341418725773,
  "R_series": 0.998938782160668,
  "R_shunt": 200.000000155274,
  "success": true,
  "mse": 0.0010972974511966826,
  "iterations": 4,
  "timestamp": "2026-08-07T16:23:46.155910"
}
```

Blocking inspector finding:

- `calibration/calibrate.py` uses `datetime.now()` inside `main()`, but imports `datetime` only inside the `if __name__ == "__main__":` block.
- Running `python calibration/calibrate.py` directly works because that import executes before `main()`.
- Calling `calibrate.main()` from `app.py` likely fails with `NameError: name 'datetime' is not defined`.
- Antigravity should move `from datetime import datetime` to the top-level imports in `calibration/calibrate.py`.

Additional calibration comments:

- The JSON input path expects arrays named `current_A`, `optical_power_W`, and `voltage_V`, with optional metadata.
- The CSV input path assumes columns in the order current, voltage, optical power after one header row. This format should be documented in the manual.
- The app temporarily writes uploaded files under `data/`. This is functional, but Antigravity should ensure failed calibration cannot leave temporary files behind in future error paths.

### App Sync Inspection

Status: implemented but needs repair before acceptance.

Positive updates:

- `app.py` exists and uses Streamlit.
- The app exposes:
  - live surrogate prediction,
  - geometry and operating controls,
  - scalar metrics,
  - `N(z)` and `P(z)` plots,
  - monitoring file upload,
  - calibration trigger,
  - calibrated parameter display,
  - calibration fit plot display.

Blocking inspector findings:

- The app readback shows mojibake text in both English and Chinese UI strings, for example `âš¡`, `ðŸŒ`, `Î¼m`, and corrupted Chinese text.
- Antigravity should repair the file encoding and verify the rendered Streamlit UI displays proper symbols and Chinese text.
- Because of the `datetime` import issue in `calibrate.py`, the app's calibration button likely fails when it calls `calibrate.main()`.

Recommended app fixes:

- Save `app.py` explicitly as UTF-8.
- Replace corrupted UI strings with valid text.
- Prefer plain ASCII labels where symbols are not essential.
- Move calibration execution into a callable function that accepts arguments directly instead of mutating `sys.argv`.
- Add app startup guidance when dependencies, model weights, or scale parameters are missing.

### PLaser Alignment Inspection

Status: partial.

PLaser reference artifacts observed locally:

- `README.md`
- `app.py`
- `pinn_surrogate.py`
- `generate_animation.py`
- `PLaser_Demonstration.mp4`
- `PLaser_User_Manual.md`
- `PLaser_User_Manual_CN.md`
- `PLaser_User_Manual.pdf`
- `PLaser_User_Manual_CN.pdf`
- `docs/manual_assets/*`
- `docs/pinn_application_report.pdf`

TLaser alignment progress:

- TLaser now has a Streamlit app.
- TLaser now has a surrogate wrapper.
- TLaser now has English and Chinese manuals.
- TLaser now has generated plot artifacts.

Remaining PLaser alignment gaps:

- No TLaser `README.md` was observed.
- No TLaser static webpage or hosted webpage artifact was observed.
- No TLaser demo video artifact was observed.
- No TLaser demo generation script equivalent to PLaser `generate_animation.py` was observed.
- No TLaser PDF manual was observed.
- No TLaser manual asset folder equivalent to PLaser `docs/manual_assets/` was observed.

Recommended PLaser-alignment next tasks:

1. Add `README.md` for TLaser using PLaser's README structure, but with TLaser-specific digital-twin calibration content.
2. Add a TLaser webpage artifact or clearly define the Streamlit app as the intended web interface.
3. Add a TLaser demo script and then generate a demo video artifact.
4. Generate PDF versions of the English and Chinese manuals.
5. Add manual assets:
   - workflow diagram,
   - training loss figure,
   - calibration fit figure,
   - app screenshot,
   - surrogate prediction profile example.

### Manual Inspection

Status: partial.

Positive updates:

- English and Chinese manuals exist.
- The English manual covers setup, data generation, training, calibration, and app launch.

Remaining comments:

- The manual should document the exact external monitoring JSON and CSV schemas.
- The manual should include the verification command `python verify_pipeline.py`.
- The manual should explain the current photon residual approximation.
- The manual should state that the current simulator is quasi-3D synthetic/reduced unless Antigravity confirms it is fully aligned with the Lasers/Elmer source.
- The manual should include troubleshooting for dependency installation, PyTorch CPU wheel installation, and Streamlit model-load failures.

### Demo Video Inspection

Status: not implemented.

No TLaser demo video or demo-generation script was observed.

Recommended next action:

- Implement `generate_demo_video.py` or an equivalent demo recording workflow following the PLaser `generate_animation.py` concept.
- The demo should show:
  - app launch,
  - live surrogate prediction,
  - profile visualization,
  - monitoring data upload,
  - calibration run,
  - before/after fit plot,
  - manual and webpage references.

### Updated Inspector Verdict

Antigravity has completed a strong second implementation pass. The most important previous gaps are now either addressed or partially addressed: dependency specification, smoke modes, metadata, expanded calibration, app, manuals, surrogate wrapper, and verification script.

The next acceptance blockers are:

1. Fix the `datetime` import bug in `calibration/calibrate.py`.
2. Repair text encoding/mojibake in `app.py`.
3. Decide and document whether the current photon residual is an accepted reduced approximation or whether the dataset should be expanded to train on `P_plus` and `P_minus`.
4. Make the full verification pipeline runnable in a documented Python environment.
5. Complete PLaser alignment artifacts: README, webpage decision/artifact, PDF manuals, demo script, and demo video.

---

## Further Inspection Update 2: 2026-08-07

This section records the next inspection pass after another Antigravity implementation cycle.

### Newly Observed Implementation Progress

Antigravity has added or updated the following artifacts:

- `README.md`
- `generate_animation.py`
- `TLaser_Demonstration.mp4`
- `generate_user_manual_pdf.py`
- `generate_user_manual_pdf_cn.py`
- `Doc/TLaser_User_Manual.pdf`
- `Doc/TLaser_User_Manual_CN.pdf`
- `docs/manual_assets/pinn_training_loss.svg`
- `docs/manual_assets/pinn_training_loss.png`
- `docs/manual_assets/calibration_fit.svg`
- `docs/manual_assets/calibration_fit.png`
- `.gitignore`

The TLaser workspace is now a Git repository and the inspected worktree is clean.

### Acceptance Blocker Status Update

Previous blocker 1: `datetime` import bug.

Status: fixed.

- `calibration/calibrate.py` now imports `datetime` at top level.
- Calling `calibrate.main()` from another module should no longer fail for missing `datetime`.

Previous blocker 2: app encoding/mojibake.

Status: partially fixed.

- English app strings now appear clean and use ASCII-safe units such as `um` and `Ohm`.
- Chinese app strings still appear mojibake-corrupted in file readback.
- `Doc/TLaser_User_Manual_CN.md` also appears mojibake-corrupted in file readback.
- Because the Chinese PDF is generated from the Chinese markdown source, Antigravity should visually inspect or regenerate it after fixing the source encoding.

Previous blocker 3: photon residual approximation.

Status: documented.

- `README.md` and `Doc/TLaser_User_Manual.md` now explicitly document the second-order total-power photon residual as an accepted reduced-order approximation.
- This resolves the documentation gap, assuming Antigravity accepts the approximation scientifically.
- Codex still notes that this is not the same as the implementation plan's first-order `P+`/`P-` residual.

Previous blocker 4: verification pipeline runnable in documented environment.

Status: still not fully verified by Codex.

- `README.md` and the manual now document `python verify_pipeline.py`.
- Codex syntax-compiled all Python files successfully using the available inspection runtime.
- Codex could not run the full verification pipeline in the inspection runtime because required dependencies such as `matplotlib`, `torch`, `scipy`, `streamlit`, and `opencv-python` are not installed there.
- Antigravity should run `python verify_pipeline.py` inside the documented virtual environment and record the result in the report or README.

Previous blocker 5: PLaser alignment artifacts.

Status: mostly fixed.

Completed:

- README exists.
- PDF manuals exist.
- Manual assets exist.
- Demo generation script exists.
- Demo MP4 exists.

Remaining:

- No standalone static webpage artifact was observed.
- The Streamlit app may be the intended webpage/web interface, but this should be stated explicitly in README/manual or a static project page should be added.

### Current Artifact Inventory

Key user-facing artifacts now present:

- `README.md`
- `app.py`
- `Doc/TLaser_User_Manual.md`
- `Doc/TLaser_User_Manual.pdf`
- `Doc/TLaser_User_Manual_CN.md`
- `Doc/TLaser_User_Manual_CN.pdf`
- `TLaser_Demonstration.mp4`
- `generate_animation.py`
- `verify_pipeline.py`
- `docs/manual_assets/`

Data and model artifacts now present:

- `data/pinn_inputs.npy`
- `data/pinn_targets.npy`
- `data/pinn_scale_params.npz`
- `data/pinn_laser_model.pt`
- `data/pinn_dataset_metadata.json`
- `data/pinn_training_loss.svg`
- `data/pinn_training_loss.png`
- `data/calibrated_params.json`
- `data/calibration_fit.svg`
- `data/calibration_fit.png`

Current dataset metadata:

- sample count: `1500`
- total attempts: `1500`
- failed solves: `0`
- input shape: `[1500, 7]`
- target shape: `[1500, 105]`

Current calibration output:

```json
{
  "alpha_i": 10.003136420656741,
  "Gamma": 0.04467014470513994,
  "C_mult": 1.01341418725773,
  "R_series": 0.998938782160668,
  "R_shunt": 200.000000155274,
  "success": true,
  "mse": 0.0010972974511966826,
  "iterations": 4,
  "timestamp": "2026-08-07T17:40:08.346610"
}
```

### Code Verification

Codex ran syntax compilation on:

- `app.py`
- `generate_animation.py`
- `generate_user_manual_pdf.py`
- `generate_user_manual_pdf_cn.py`
- `verify_pipeline.py`
- `simulator/generate_dataset.py`
- `surrogate/model.py`
- `surrogate/train.py`
- `surrogate/pinn_surrogate.py`
- `calibration/calibrate.py`

Result: passed.

### Requirements Inspection

Current `requirements.txt`:

```text
numpy
matplotlib
streamlit
torch --index-url https://download.pytorch.org/whl/cpu
scipy
opencv-python
```

Inspector comments:

- The PyTorch CPU installation intent is clear.
- Antigravity should verify that `pip install -r requirements.txt` accepts the inline `torch --index-url ...` syntax on a clean environment.
- Safer alternatives are:
  - place `--index-url https://download.pytorch.org/whl/cpu` on its own line if the whole environment should use that index, or
  - document `pip install torch --index-url https://download.pytorch.org/whl/cpu` as a separate setup step, then keep `torch` plain in `requirements.txt`.

### App Inspection

Status: usable structure, but bilingual presentation still needs repair.

Positive updates:

- English strings are repaired and readable.
- Calibration display labels now use ASCII-safe text, such as `alpha_i`, `Gamma`, and `Ohm`.
- Temporary uploaded calibration files are removed in a guarded cleanup block.

Remaining app comments:

- Chinese strings remain mojibake-corrupted in `app.py`.
- The app still mutates `sys.argv` to call `calibrate.main()`. This is functional but brittle.
- Antigravity should eventually expose calibration as a direct function, for example `run_calibration(data_file=None, output_dir=...)`, so the CLI and app can share logic safely.

### Manual and PDF Inspection

Status: English manual improved; Chinese source needs encoding repair.

Positive updates:

- English manual documents:
  - environment setup,
  - troubleshooting,
  - simulator nature,
  - dataset generation,
  - photon residual approximation,
  - JSON and CSV monitoring data schemas,
  - verification command,
  - Streamlit app launch.
- English PDF manual exists.
- Chinese markdown and PDF manual exist.

Remaining comments:

- Chinese markdown appears mojibake-corrupted.
- Chinese PDF should be visually inspected after the source encoding is corrected.
- The manual says the quasi-3D solver is the canonical high-fidelity simulator for the prototype, which is clear and acceptable for this iteration.

### Demo Video Inspection

Status: implemented, basic artifact present.

Positive updates:

- `generate_animation.py` exists.
- `TLaser_Demonstration.mp4` exists and is about 16 MB.
- The demo script follows the PLaser-style approach: it uses the surrogate wrapper, sweeps parameters, renders dashboard-like plots, and writes an MP4.

Remaining comments:

- Codex did not visually inspect the MP4 in this pass.
- The demo currently focuses on live surrogate sweeps and longitudinal profiles.
- It does not show monitoring data upload, calibration execution, or before/after calibration fit comparison. If the demo is intended to cover the full TLaser digital-twin loop, Antigravity should extend it or create a second calibration-focused demo.

### Webpage Inspection

Status: unresolved.

- No standalone HTML/static webpage artifact was observed.
- If `app.py` is intended to satisfy the webpage requirement, Antigravity should explicitly state: "The TLaser webpage is the Streamlit dashboard launched by `python -m streamlit run app.py`."
- If a PLaser-style static webpage is required for publication or GitHub Pages, Antigravity should add a separate webpage artifact.

### Updated Inspector Verdict

Antigravity has closed most PLaser-alignment artifact gaps. TLaser now has a README, app, manuals, PDF manuals, manual assets, demo-generation script, and demo MP4.

The remaining acceptance blockers are now narrower:

1. Fix Chinese text encoding in `app.py` and `Doc/TLaser_User_Manual_CN.md`.
2. Verify `pip install -r requirements.txt` in a clean virtual environment, especially the PyTorch CPU wheel line.
3. Run `python verify_pipeline.py` inside the documented virtual environment and record the result.
4. Decide whether the Streamlit app is the official TLaser webpage, or add a standalone static webpage.
5. Optionally extend the demo video to include calibration upload/execution and before/after calibration fit comparison.

---

## Product-Standard Requirements Raise: 2026-08-07

Codex inspector recommendation: TLaser should now move from prototype acceptance toward standard product readiness. The next Antigravity cycles should treat TLaser as a versioned, reproducible, user-facing engineering product rather than a collection of successful scripts.

### Product Definition Requirements

Required:

- Define the product scope in `README.md`:
  - TLaser is a telecom diode-laser digital twin.
  - The current physics core is a quasi-3D reduced simulator.
  - The surrogate is a reduced-order PINN approximation.
  - Calibration currently supports L-I-V curve fitting.
- Define target users:
  - laser device engineers,
  - photonics researchers,
  - digital-twin workflow evaluators,
  - internal demo/review users.
- Define product modes:
  - CLI research workflow,
  - Streamlit dashboard,
  - documentation/manual package,
  - demonstration video.
- Add a clear limitations section:
  - not a replacement for full FEM/TCAD signoff,
  - not validated against real measured production wafers unless such data is added,
  - current photon residual uses the accepted second-order total-power approximation.

Acceptance criteria:

- A new user can understand what TLaser does and does not claim within five minutes of reading the README.
- The README and manual make the same product claims consistently.

### Environment and Packaging Requirements

Required:

- Replace ambiguous dependency management with a reproducible setup:
  - preferably `pyproject.toml` plus pinned dependencies, or
  - `requirements.txt` plus `requirements-lock.txt`.
- Fix PyTorch CPU installation instructions so `pip install -r requirements.txt` works in a clean environment.
- Add a documented Python version target, for example Python 3.11 or 3.12.
- Add a `Makefile`, PowerShell task script, or `scripts/` command wrapper for common workflows:
  - install,
  - verify,
  - generate dataset smoke test,
  - train smoke test,
  - calibrate smoke test,
  - run app,
  - generate manuals,
  - generate demo.
- Separate source code, generated artifacts, and release artifacts clearly.
- Decide whether large generated files should be tracked in Git or moved to release assets.

Acceptance criteria:

- Fresh clone plus documented install command succeeds.
- `python verify_pipeline.py` succeeds in the documented environment.
- Dependency installation does not require manual guessing.

### Code Quality Requirements

Required:

- Add a real package layout or clear module boundaries:
  - simulator,
  - surrogate,
  - calibration,
  - app,
  - scripts.
- Replace `sys.path.append` patterns with package imports or a documented local package install.
- Refactor calibration so CLI and Streamlit app call shared functions directly instead of mutating `sys.argv`.
- Add structured configuration for constants and parameter bounds.
- Add type hints to public functions and model wrappers.
- Add docstrings for all public classes and entry points.
- Add logging instead of print-only diagnostics for long-running workflows.
- Remove or ignore generated `__pycache__` files.

Acceptance criteria:

- Code can be imported without side effects.
- App code does not depend on CLI argument mutation.
- Main workflows can be called from both CLI and Python APIs.

### Testing and Verification Requirements

Required:

- Add automated tests under `tests/`.
- Minimum test groups:
  - simulator smoke test,
  - dataset shape and metadata test,
  - surrogate scale parameter test,
  - surrogate prediction API test,
  - calibration mock-data convergence test,
  - monitoring JSON/CSV parsing tests,
  - app import test,
  - documentation artifact existence test.
- Keep `verify_pipeline.py` as an end-to-end smoke test, but do not rely on it as the only test.
- Add numerical acceptance thresholds:
  - calibration MSE maximum,
  - allowed output shape mismatch count,
  - no NaN/Inf in generated datasets,
  - prediction latency target,
  - basic surrogate error metrics on a validation split.
- Save verification results to a machine-readable file, for example `data/verification_report.json`.

Acceptance criteria:

- `pytest` or equivalent test command passes.
- `verify_pipeline.py` produces a clear pass/fail summary.
- Validation metrics are documented and reproducible.

### Model and Physics Validation Requirements

Required:

- Add a validation split to training.
- Report scalar prediction error for:
  - `P_opt`,
  - `WPE`,
  - `I_total`.
- Report profile error for:
  - `N(z)`,
  - `P(z)`.
- Report physics residual metrics separately:
  - carrier residual,
  - photon residual,
  - smoothness penalty.
- Verify scaled targets stay within model output assumptions. If not, replace final `Sigmoid` or adjust scaling.
- Add plots:
  - predicted vs target scatter,
  - residual histogram,
  - representative profile overlay,
  - calibration before/after L-I-V plot.
- State whether validation is against:
  - synthetic quasi-3D simulator only,
  - PLaser-derived data,
  - real measurement data.

Acceptance criteria:

- Product claims include measured validation numbers.
- Validation figures are regenerated by documented commands.
- The model file is traceable to dataset metadata and training settings.

### App and UX Requirements

Required:

- Fix all encoding issues in bilingual UI.
- Decide whether Chinese support is required for product release. If yes, verify all Chinese text renders correctly in:
  - Streamlit app,
  - markdown manual,
  - PDF manual.
- Add app states:
  - missing model,
  - missing dependencies,
  - loading,
  - prediction success,
  - calibration running,
  - calibration failure,
  - invalid uploaded file,
  - empty dataset.
- Add input validation for all controls and uploaded data.
- Add downloadable outputs:
  - prediction CSV,
  - calibration JSON,
  - calibration fit figure.
- Add product-level UI polish:
  - consistent units,
  - consistent axis labels,
  - no corrupted text,
  - no unexplained abbreviations,
  - clear distinction between active current and terminal current.

Acceptance criteria:

- A non-developer can run the app, upload valid data, calibrate, and export results.
- Invalid files produce clear errors without stack traces.
- App screenshots pass visual review.

### Documentation Requirements

Required:

- Promote docs from script notes to product documentation:
  - README for quickstart,
  - user manual for workflows,
  - technical reference for equations,
  - developer guide for modifying/extending code,
  - release notes/changelog.
- Add exact JSON and CSV schemas for monitoring data.
- Add artifact regeneration commands.
- Add troubleshooting for:
  - PyTorch install,
  - Streamlit launch,
  - missing model weights,
  - failed calibration,
  - corrupt or invalid monitoring data.
- Add a traceability table:
  - implementation plan item,
  - implemented artifact,
  - verification method,
  - status.

Acceptance criteria:

- Documentation supports both user operation and developer maintenance.
- English docs are release-ready.
- Chinese docs are either fixed and release-ready or explicitly marked experimental.

### Demo and Web Requirements

Required:

- Decide product web surface:
  - Streamlit dashboard only, or
  - separate static webpage plus Streamlit dashboard.
- If Streamlit is the official webpage, document that clearly.
- If static webpage is required, add a product landing page with:
  - product overview,
  - workflow,
  - screenshots,
  - demo video link,
  - manual links,
  - limitations.
- Extend demo coverage or add a second demo:
  - live prediction,
  - monitoring data upload,
  - calibration run,
  - before/after fit comparison,
  - export/report output.

Acceptance criteria:

- Demo video matches the product claims.
- Web entry point points users to app, manual, and verification artifacts.

### Release and Versioning Requirements

Required:

- Add semantic versioning, starting with something like `v0.1.0-prototype`.
- Add `CHANGELOG.md`.
- Add release checklist:
  - clean Git state,
  - dependencies verified,
  - tests passed,
  - pipeline verified,
  - manuals regenerated,
  - demo regenerated or checked,
  - artifacts listed.
- Record artifact provenance:
  - dataset generation timestamp,
  - training timestamp,
  - training command,
  - calibration command,
  - model file checksum if possible.

Acceptance criteria:

- A release can be reproduced from source and documented commands.
- Release artifacts can be distinguished from development artifacts.

### Security, Robustness, and Data Handling Requirements

Required:

- Treat uploaded calibration files as untrusted input.
- Validate file size, extension, schema, numeric ranges, NaN/Inf values, and array lengths.
- Avoid writing temporary uploaded files into permanent `data/` unless intentionally saved.
- Prefer temporary directories for upload handling.
- Add error handling around model loading, calibration, plotting, and file cleanup.
- Ensure no credentials or local private paths are embedded in release docs.

Acceptance criteria:

- Bad input cannot crash the app silently.
- Temporary files are cleaned up.
- Release docs do not expose machine-specific implementation details unless clearly marked local examples.

### Product-Readiness Priority List for Antigravity

Priority 1: Product Acceptance Blockers

- Fix Chinese encoding or disable Chinese release mode until fixed.
- Fix dependency installation so clean setup works.
- Run and record `verify_pipeline.py` in the documented environment.
- Refactor calibration app integration away from `sys.argv` mutation.
- Decide and document official webpage strategy.

Priority 2: Product Quality

- Add tests under `tests/`.
- Add validation metrics and plots.
- Add product limitations and validation status to README/manual.
- Add downloadable app outputs and stronger uploaded-data validation.
- Add changelog and version label.

Priority 3: Release Polish

- Generate release-ready manuals.
- Extend demo to include calibration.
- Add static webpage if required.
- Add artifact provenance and checksums.
- Clean generated cache files and clarify tracked artifacts.

### Product-Standard Inspector Verdict

TLaser is no longer merely a prototype scaffold. It now has the shape of a product: app, CLI workflows, model artifacts, manuals, demo, and verification script. However, it is not yet product-standard because reproducible installation, automated tests, validation metrics, bilingual text integrity, app robustness, and release/version discipline are not yet complete.

Codex recommends treating the next Antigravity cycle as a product-hardening sprint, not a feature sprint.

---

## High-Fidelity Simulation and Data Quality Inspection: 2026-08-07

User focus for this inspection pass: improve the high-fidelity simulation model and training-data quality.

### Executive Finding

The current simulator is useful as a reduced quasi-3D synthetic generator, but it should not yet be treated as a high-fidelity product-grade data source. The largest issue found in this pass is a concrete data-quality mismatch: the generated dataset contains `I_total` values up to about `49 A`, while `surrogate/train.py` scales `I_total` with an assumed maximum of `20 A`. Because `surrogate/model.py` uses a final `Sigmoid`, any scaled target above `1.0` cannot be represented faithfully by the model.

This is an immediate product-blocking data-quality issue for the surrogate.

### Dataset Quality Check Results

Codex inspected the current generated dataset:

```text
inputs shape:  (1500, 7), float32
targets shape: (1500, 105), float32
inputs finite: true
targets finite: true
```

Input ranges observed:

```text
R1:       min 0.100026, mean 0.523075, max 0.949069
R2:       min 0.050185, mean 0.276415, max 0.499777
L_cm:     min 0.010022, mean 0.054589, max 0.099960
T0:       min 250.006, mean 303.471, max 359.913
I_active: min 0.010006, mean 0.254286, max 0.499322
w_cm:     min 1.5006e-4, mean 2.7189e-4, max 3.9987e-4
d_cm:     min 1.0044e-5, mean 2.9732e-5, max 4.9989e-5
```

Output ranges observed:

```text
P_opt:  min 4.80e-7 W, mean 4.91e-3 W, max 1.73e-2 W
WPE:    min 9.76e-9,   mean 2.48e-4,   max 2.72e-3
I_total min 4.90 A,    mean 26.82 A,   max 49.00 A
N(z):   min 4.48e17,   max 1.13e19
P(z):   min 1.88e-6 W, max 2.47e-2 W
```

Scaler compatibility check:

```text
scaled target max: 2.4498
scaled target values above 1.0: 1132
negative scaled target values: 0
```

Inspector comments:

- `I_total` values are the main cause of scaled target overflow.
- `train.py` assumes `out_max[2] = 20.0` for `I_total`.
- Current `I_total` reaches about `49.0`.
- `model.py` uses a final `Sigmoid`, so scaled targets above `1.0` are outside the model output range.
- This will bias the surrogate, especially current prediction and any coupled WPE/electrical interpretation.

Immediate required action:

- Fix scaling/model compatibility before further training is accepted.

Options:

1. Adjust `out_max[2]` based on dataset statistics plus margin, then retrain.
2. Compute all output scaling from the generated dataset and save it in `pinn_scale_params.npz`.
3. Remove the final `Sigmoid` and use a model/output transform that can represent values outside `[0, 1]`.
4. Fix the simulator current model so `I_total` is physically realistic before regenerating the dataset.

Codex recommends option 4 first, then option 2.

### High-Fidelity Simulation Model Inspection

Status: reduced synthetic model, not yet high-fidelity.

Current implementation characteristics:

- The simulator solves a longitudinal cavity problem with `P_plus`, `P_minus`, `N`, and gain arrays.
- It uses a shooting method for mirror boundary conditions.
- It solves the local carrier equation with a log-Newton method.
- It integrates photon propagation with explicit Euler integration.
- It uses simple temperature scaling laws for gain, transparency carrier density, and Auger recombination.
- It uses fixed or globally assigned values for important device parameters such as `Gamma`, `alpha_i`, `I_shunt_unit`, `A`, `B`, `C`, `N_tr`, and gain coefficient.

Main high-fidelity gaps:

1. Transverse physics is not actually solved in TLaser.
   - The file header says the model is coupled with baseline 2D transverse parameters from Elmer.
   - No Elmer/FEM mesh, material solution, optical confinement calculation, thermal solution, or drift-diffusion import is present in TLaser.
   - `Gamma` is fixed at `0.05` unless overwritten.

2. Thermal model is only parametric.
   - Temperature affects gain, transparency density, and Auger coefficient through simple scaling laws.
   - There is no self-heating model coupled to current, voltage, thermal resistance, heat source distribution, or heatsink boundary condition.
   - The simulator cannot yet capture spatial thermal gradients or thermal rollover mechanistically.

3. Electrical model is too coarse.
   - `I_total = (I_2d_unit + I_shunt_unit) * L_cavity`.
   - With `I_shunt_unit = 486.678 A/cm`, cavity lengths up to `0.1 cm` create tens of amps of shunt current.
   - This dominates the electrical metrics and pushes WPE to very small values.
   - The simulator uses fixed `V_bias = 1.0499` for electrical power.

4. Optical propagation uses explicit Euler.
   - Euler integration is simple but low order and can introduce numerical bias in gain/loss propagation.
   - A product-grade simulator should use a more stable and higher-order integration method, or at least verify grid convergence.

5. Boundary-condition convergence is not reported in the dataset.
   - The bisection shooting residual is used internally.
   - The returned result does not include convergence flag, iteration count, final residual, or whether the bracket was valid.
   - `generate_dataset.py` accepts all successful function returns without quality filtering.

6. Dataset targets omit `P_plus` and `P_minus`.
   - The simulator computes both fields.
   - The dataset stores only total `P_profile = P_plus + P_minus`.
   - This prevents training the planned first-order photon residual directly.

7. Spontaneous emission and gain modeling are simplified.
   - `beta_sp` is fixed.
   - Gain is logarithmic and clamped nonnegative.
   - Gain compression, spectral detuning, carrier-dependent refractive index, and linewidth-related effects are absent.

### Data Generation Inspection

Status: operational but not yet product-grade.

Positive items:

- CLI controls exist for sample count, seed, output directory, and smoke test.
- Metadata records sample count, attempts, failures, parameter ranges, and array shapes.
- Current full dataset has no NaN/Inf values.
- Current generation run reports zero failed solves.

Data-quality gaps:

1. Sampling is uniform random only.
   - Uniform random sampling is acceptable for a first pass.
   - Product-grade surrogate training should use Latin Hypercube, Sobol, Halton, or stratified sampling for better coverage.

2. No train/validation/test split metadata.
   - The dataset file does not record split indices.
   - There is no holdout set tied to a specific seed and dataset version.

3. No output distribution summary in metadata.
   - Metadata does not include min/mean/max/quantiles for inputs and outputs.
   - The scaler mismatch would have been caught earlier if output statistics were saved automatically.

4. No physical plausibility filters.
   - Samples are accepted if the solver does not throw an exception.
   - There are no acceptance checks for:
     - positive finite values,
     - plausible terminal current,
     - plausible WPE,
     - mirror-boundary residual,
     - Newton convergence quality,
     - monotonic or bounded power behavior,
     - carrier-density range.

5. No units schema.
   - Inputs are stored in mixed units: `L`, `w`, and `d` are stored in cm, while metadata ranges are reported in microns.
   - This is workable but should be explicitly encoded in metadata to avoid future misuse.

6. Dataset is regenerated destructively.
   - Current scripts overwrite `pinn_inputs.npy`, `pinn_targets.npy`, and metadata.
   - Product-grade data generation should write versioned dataset directories or include dataset IDs.

### Required Simulator Upgrades

Priority 1: Fix physical/electrical realism and scaling.

- Revisit `I_shunt_unit = 486.678 A/cm`.
- Decide whether shunt current should be:
  - removed from simulator dataset generation,
  - modeled as a calibration-only parasitic,
  - reduced to a physically justified scale,
  - replaced with explicit `R_shunt` voltage-dependent leakage.
- Replace fixed `V_bias` with a documented voltage model or move voltage/electrical parasitics into calibration.
- Regenerate the dataset after fixing current model behavior.
- Recompute output scaling from the regenerated dataset.

Priority 2: Add solver quality outputs.

- Return from `solve_longitudinal()`:
  - `converged`,
  - `shooting_iterations`,
  - `shooting_residual`,
  - `max_newton_iterations`,
  - `newton_failure_count`,
  - `min/max` sanity values,
  - optional grid spacing and method version.
- Store quality summaries in dataset metadata.
- Reject or quarantine samples that fail quality checks.

Priority 3: Improve numerical method.

- Replace explicit Euler propagation with at least RK4 or a stable exponential segment update.
- Add grid-convergence testing with `M = 51`, `101`, and `201`.
- Record convergence error for representative operating points.
- Add regression tests for solver stability.

Priority 4: Improve physical model hierarchy.

- Add parameterized 2D transverse lookup tables or imports:
  - optical confinement factor `Gamma(w, d, T)`,
  - effective index `n_eff(w, d, T)`,
  - active-region overlap,
  - thermal resistance or local temperature rise,
  - series/shunt parasitic estimates.
- If real Elmer/Lasers outputs are available, add an adapter that imports them into TLaser data generation.
- Make the simulator state whether each sample used:
  - analytic defaults,
  - lookup-table transverse data,
  - imported FEM data.

Priority 5: Expand targets if first-order photon residual remains a goal.

- Save `P_plus(z)` and `P_minus(z)` separately in `pinn_targets.npy`, or create a new target file schema.
- Update model output dimensions accordingly.
- Train direct first-order photon residuals:
  - `dP_plus/dz - (Gamma*g - alpha_i)P_plus = source`,
  - `dP_minus/dz + (Gamma*g - alpha_i)P_minus = source`.
- Keep total `P(z)` as a derived output for app display.

### Required Data Quality Upgrades

Priority 1: Add dataset QA report.

Create `data/dataset_quality_report.json` containing:

- dataset ID,
- generator git commit if available,
- generation command,
- timestamp,
- random seed,
- sample count,
- parameter ranges and units,
- input min/mean/max/quantiles,
- output min/mean/max/quantiles,
- NaN/Inf counts,
- scaling overflow counts,
- physical rejection counts,
- solver convergence statistics.

Priority 2: Add quality gates.

Generation should fail or warn loudly if:

- any NaN/Inf appears,
- scaled target values exceed model range,
- solver convergence fails,
- `I_total` exceeds a chosen physical maximum,
- WPE is outside a plausible range,
- too many samples are below threshold or otherwise low-information,
- output distribution is badly imbalanced.

Priority 3: Improve sampling.

- Add `--sampling uniform|lhs|sobol`.
- Add edge/corner cases intentionally.
- Add threshold-focused sampling around lasing transition.
- Add calibration-focused sampling over parasitic and thermal drift parameters.
- Add stratified current/temperature sampling so high-temperature and near-threshold behavior is not underrepresented.

Priority 4: Version datasets.

- Write datasets to `data/datasets/<dataset_id>/`.
- Save `inputs.npy`, `targets.npy`, `metadata.json`, `quality_report.json`, and `scale_params.npz` together.
- Store the active model's training dataset ID in model metadata.

Priority 5: Add data visualizations.

- Generate:
  - input coverage plots,
  - output histograms,
  - P-I curves for selected geometries,
  - WPE vs current/temperature,
  - `N(z)` and `P(z)` envelopes,
  - solver residual distributions.

### Immediate Antigravity Task List

1. Fix the simulator electrical current model so generated `I_total` is physically plausible.
2. Regenerate dataset after that fix.
3. Recompute scale parameters from dataset statistics.
4. Add dataset quality report generation.
5. Add quality gates for NaN/Inf, scaled overflow, solver convergence, and physical plausibility.
6. Add solver convergence outputs to `Quasi3DSimulator.solve_longitudinal()`.
7. Upgrade propagation integration from Euler to a higher-quality method or document grid-convergence evidence.
8. Add `P_plus` and `P_minus` targets if first-order photon residual training is desired.
9. Add sampling strategy control, starting with Latin Hypercube or Sobol.
10. Document the simulator fidelity level honestly: reduced quasi-3D analytic/parametric, not full FEM/TCAD.

### High-Fidelity/Data-Quality Inspector Verdict

TLaser's current dataset is clean in the narrow sense that it is finite and generated without reported solver failures. But it is not yet high-quality product training data. The terminal-current scaling mismatch and physically questionable shunt-current model must be fixed before the surrogate can be considered reliable.

Codex recommends that the next Antigravity cycle focus first on simulator current realism, dataset QA reporting, and scale/model compatibility before adding more UI or documentation features.
