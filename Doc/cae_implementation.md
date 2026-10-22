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

### Four solver workspaces (2026-10-22)

Simulator core now separates **Mesher · Lasers / Gmsh**, **Transverse 2D
solver**, **Longitudinal 1D solver**, and **1D-2D two-way coupled solver**.
Each has editable settings, versioned JSON configuration import/export,
restoration from a saved run, independent persistent jobs, and result visualization.
Solver configurations snapshot the device rather than silently following later
edits. Use **Use current Device model** to explicitly refresh that snapshot.

The 2D workspace runs Elmer's coupled Poisson/electron/hole, heat and vector
EM equations without an implicit longitudinal solve. The 1D workspace now solves
the following three coupled equation sets, rather than the reduced carrier-rate
model used for PINN training:

* Poisson plus separate electron/hole drift-diffusion continuity, using
  Scharfetter–Gummel fluxes, SRH/radiative/Auger recombination, uniform transverse
  pair injection and unity-yield photogeneration from absorbed probe light.
  Axial potential endpoints are prescribed; carrier facets have zero flux.
* Axial heat conduction, nonradiative recombination heating and axial Joule heat,
  with insulated thermal facets and a configurable distributed transverse heat
  sink. Absorbed photon energy enters through photogeneration/nonradiative
  recombination, rather than adding the same energy twice.
* Complex scalar Helmholtz waves with partially reflecting facets and a
  prescribed incident optical probe. Drude carrier dispersion and temperature
  modify refractive index; wave absorption modifies the continuity equations.
  A separate optical grid resolves each wavelength with at least 24 nodes;
  exponentially fitted differences preserve uniform-medium phase propagation.

This longitudinal wave model is a **passive driven cavity**, not a self-lasing
eigenmode or stimulated-emission laser-power prediction. Its transmitted probe
power is labeled accordingly. Optical amplitudes have units sqrt(W); they are
power-normalized, not electric field in V/cm. The electrostatic field is V/cm.
Default mobility, permittivity, effective masses and thermo-optic coefficient
are explicit assumptions saved with the result, not a calibrated material library.
The configured series/shunt resistance and confinement factor belong to the
separate reduced laser predictor; this axial field model does not use them.

Configuration includes axial bias, probe power, thermal conductivity, effective
transverse heat conductance, refractive index, iteration limit and residual
tolerance. Each run saves separate carrier, potential, temperature, photon and
complex wave arrays, plus residuals for all equation sets. Convergence requires
both PDE residuals and the unrelaxed optical-source mismatch to pass. Reaching
an iteration limit is never reported as convergence. Older configuration files
receive the new options' defaults. Cancellation is checked between outer solves.

The fourth workspace uses this complete 1D member and the complete 2D member
in an **optothermal feedback** closure:

1. Run the transverse carrier/thermal/EM solvers with the currently applied
   optical-absorption heat source.
2. Area-average the computed MQW temperature and use it as the effective heat-sink
   reference for the longitudinal multiphysics solve. This averaged closure is
   not a pointwise 3D heat-flux match; its effective thermal conductance requires
   calibration and it must not be interpreted as a validated absolute temperature.
3. Integrate forward plus backward cavity power along the longitudinal grid.
   Return `fraction × alpha_i × mean_power / actual_mesh_MQW_area` in W/cm³
   as uniform MQW optical heating, replacing the transverse photon-heating term
   to avoid double counting it. Other transverse thermal sources remain active.
4. Relax the returned heat source and repeat. Stop only when both the unrelaxed
   heat mismatch and relative MQW-temperature change pass the specified tolerance,
   and the longitudinal multiphysics solve itself has converged.

Every feedback iterate saves its generated SIF, mesh fields, longitudinal profiles,
and diagnostics. The UI exposes the residual history and lets you inspect each
iterate. An exhausted iteration budget is explicitly **not converged**. Even when
outer residuals pass, results remain candidates pending inner-solver/engineering
review. Cancellation reaches the active Elmer subprocess.

This is cavity-averaged optical-loss/thermal two-way coupling, not spatially
resolved 3D feedback or an electrical current-matching loop. Active current remains
a user-configured input; no transverse current extraction is implied. The loss
deposition fraction is an explicit modeling assumption requiring calibration.

Validation: an analytical lossy Fabry–Perot transmission check, integrated
electron/hole generation/recombination balance, default-device coupled residuals,
zero-drive Maxwell response, cancellation, iteration-limit reporting and
Streamlit workspace/configuration tests. These are numerical checks, not
measured-device qualification. The reduced current sweep, PINN dataset generator,
prediction and calibration backend remain unchanged; new field results must not
be confused with training targets from that reduced backend.

Earlier release notes below describe the preceding implementation.

### Lasers Simulator core update (2026-10-18)

The Simulator core now provides three stages: **Mesher**, **Quasi-3D coupled
solver**, and **Visualization and postprocessing**. The mesher is copied from
Lasers/Tools/generate_gmsh_mesh01.py and uses its App/Geometry model, preserves
11 material regions and boundary IDs, and exports Gmsh/Elmer files. Select a
completed mesh job in the solver form. Element-size scale controls refinement;
physical geometry dimensions remain those of the Lasers reference model.

After Elmer finishes, TLaser computes the area-weighted MQW temperature on body 4,
matches mesh nodes to solved field coordinates, and passes that temperature to
the longitudinal carrier/forward/backward optical solver. Active current and
effective active dimensions remain explicit design inputs. This extends the
Lasers run_quasi_3d.py architecture, whose transverse baseline current is
hard-coded, with an automatic thermal handoff. It is one-way coupling, not an
iterated transverse/longitudinal feedback loop or a full volumetric solve.

Postprocessing includes all solved field components, EM phase, mesh inspection,
cross-section probes with CSV export, iteration extrema, longitudinal forward
and backward power, spatial hole burning, and downloadable raw results.
Gmsh defaults to C:/gmsh/gmsh.exe and can be selected in the app.

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
