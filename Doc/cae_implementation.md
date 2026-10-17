# TLaser CAE implementation

## Implemented work packages

1. Persistent, isolated jobs with settings snapshots, progress, cancellation,
   solver logs, artifacts, and explicit failure/candidate/completed states.
2. Lasers coupled Elmer adapter: copied reference mesh and SIF, configurable
   p-contact potential, heat-sink temperature, optical frequency, cavity mirrors,
   coupling iterations and tolerance. External compatible Elmer/custom DLL
   installation is required; source cases are never executed in place.
3. Spatial results: mesh contours and 3D inspection, carriers, potential,
   temperature, complex EM fields and photon population; electrostatic field
   derived from the solved potential gradient; phase and logarithmic display.
4. Reproducible seven-dimensional sampling with iterative longitudinal solves,
   failure accounting, independent train/validation/test splits, seed and provenance.
5. Physics-informed training in a background job, loss history, validation and
   independent test metrics, safe model export, explicit model activation, and
   rejection of predictions outside the trained sampling envelope.
6. Maintain the five-section workspace, existing calibration acceptance checks,
   shared configuration, bilingual UI, and reproducible reports.

## Fidelity boundaries and remaining engineering validation

The Lasers reference mesh is a 2D transverse mesh (1663 nodes / 3218 triangles),
not a volumetric mesh of the 15-part CAD visualization. Effective solver width
and thickness do not remesh this transverse domain. Longitudinal PINN datasets
use the reduced quasi-3D engine, with a documented fixed set of physical
constants. Neither output provenance is relabeled as a full 3D solve.

Before production qualification: measured-device benchmark suites, mesh and
domain convergence studies, independently verified material/doping libraries,
configurable geometry meshing, 3D vector Maxwell analysis, and coupled
transverse-to-longitudinal parameter extraction remain distinct work packages.
Training/test errors are against a simulator, not experimental accuracy.

## Operating guide

1. Start `run_tlaser.ps1`, configure the device and choose **Simulator core**.
   The current-sweep tool uses the built-in longitudinal model.
2. For spatial fields, the default runtime is discovered from the sibling Lasers
   checkout or `TLASER_LASERS_ROOT`. On this workstation it is
   `C:\Users\aw4wz\Documents\Codex\Lasers\Lasers`. It requires the compatible
   `../tools/elmer-9.0-ucrt` installation and the custom DLLs in `ExeLibs`.
   Configure temperature, contact potential, frequency and iterations, then submit.
3. Refresh results, select a saved run and inspect the solver log. Select the
   iteration and field, rotate the mesh or view contours, then export CSV/VTU.
   A zero carrier-generated EM response is possible. A positive prescribed
   EM current source runs a driven response, not a self-consistent lasing mode.
   Raw EM amplitudes retain solver units pending independent unit qualification.
4. In **PINN surrogate**, configure ranges, sample count, epochs and error gate.
   Submit once. The background worker generates simulations and trains a new
   model without changing bundled weights. The default is 500 samples / 1000 epochs.
5. Review validation and independent test results. Each of power, WPE, current,
   carrier profile and power profile must pass on both splits. Normalization uses
   the training-target range per output (with a small floor), not relative error
   at each operating point. A small normalized error can hide large relative
   errors near threshold; inspect physical-unit RMSE too.
6. Activate the selected model explicitly. Predictions reject inputs outside its
   training domain or mismatched physical constants. Export the model package,
   dataset and validation report for reproducibility. Model activation is local
   to the browser session; saved jobs remain available after restart.

Job states: `queued`, `running`, `cancelled`, `failed`, `candidate`, `completed`.
Field jobs remain candidates until engineering convergence review; a successful
process exit does not prove convergence. Cancellation stops the owned solver
process or interrupts sampling/training at a safe boundary. Jobs have isolated
case directories and never overwrite the Lasers source case.

## Validation evidence (2026-10-17)

- Real coupled Elmer solve: 1663 nodes / 3218 triangles, saved mesh results.
- Simulator-driven training: 500 successful simulations, split 300/100/100,
  seed 42, 1000 epochs. Validation aggregate normalized RMSE 0.04982;
  independent test 0.04929. Worst test output group WPE: 0.08579.
  All groups passed the configured 0.15 gate. This is simulator-relative evidence.
- A deliberately short training run failed its gate and could not be activated.
- Regression checks cover the five-section workflow, calibration, geometry,
  exact potential gradients, complex EM phase, Windows progress-write retry,
  cancellation, checksum rejection and out-of-domain rejection.

Source basis: local Lasers/App/Run/laser_coupled.sif, Lasers/App/Mesh/mesh01,
Lasers/Tools/visualize_carriers_vtu.py, and the existing PLaser-derived
TLaser/surrogate/train.py and quasi_3d_synthesizer.py.
