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

See [longitudinal and two-way validation results](solver_validation.md) for the
included field/curve examples, numerical acceptance criteria, reproduction steps,
and the outstanding Poynting-vector diagnostic failure in the coupled run.

### Four solver workspaces (2026-10-22)

Simulator core now separates **Mesher · Lasers / Gmsh**, **Transverse 2D
solver**, **Longitudinal 1D solver**, and **1D-2D two-way coupled solver**.
Each has editable settings, versioned JSON configuration import/export,
restoration from a saved run, independent persistent jobs, and result visualization.
Solver configurations snapshot the device rather than silently following later
edits. Use **Use current Device model** to explicitly refresh that snapshot.

To inspect plots, open **Simulator core**, select one of the four workspaces,
and open its **Visualization & results** tab (shown first). Select a saved run
and refresh after completion. The transverse workspace provides field contours,
rotatable mesh inspection and cross-section curves; the longitudinal workspace
provides carrier, gain, photon and forward/backward power curves. Coupled runs
provide both, with an iteration selector. Use **Configure & run** to start a new
simulation. Results are stored in the checkout's local `runs/` folder and are not
downloaded by a Git update. Empty, running and failed selections show guidance
instead of silently hiding the visualization area.

### Alignment with the Lasers methodology

Source inspection: `Lasers/Doc/CarriersSolver_README.md`,
`ThermoSolver_README.md`, `EMSolver_README.md`, `App/Run/laser_coupled.sif`,
`Tools/quasi_3d_synthesizer.py`, `App/Run/run_quasi_3d.py`, and
`Pages/Projects/Lasers/index.html` Task 1.6 in the local Lasers project.

Lasers uses a dimensional decomposition, not three identical full field solves:

* **Transverse 2D:** Poisson plus electron/hole continuity, lattice heat transport,
  vector Helmholtz EM, and photon-population feedback in the coupled Elmer case.
* **Longitudinal 1D:** local carrier balance with A/B/C recombination, logarithmic
  temperature-dependent gain, spontaneous emission, stimulated recombination,
  and bidirectional optical power propagation. Both facet reflectivities are
  boundary conditions. This resolves spatial hole burning without a volumetric
  3D mesh or an externally driven passive probe.
* **Quasi-3D:** transverse parameters feed the longitudinal active laser.
  TLaser additionally iterates averaged optical heating back into the transverse
  solve; this outer iteration is a TLaser extension, not a claim that the Lasers
  example driver already implements it.

The previous passive Helmholtz probe implementation did not follow this
methodology and has been retired. Its saved results remain viewable and clearly
labeled; its configurations are rejected for new active-laser runs.

The implemented longitudinal equations follow the Lasers source:

    G = A N + B N^2 + C(T) N^3 + g(N,T)(P+ + P-)/(Aact h nu)
    dP+/dz = (Gamma g - alpha_i) P+ + beta B N^2 Aact h nu
    dP-/dz = -(Gamma g - alpha_i) P- - beta B N^2 Aact h nu
    P+(0) = R1 P-(0); P-(L) = R2 P+(L)

A log-density Newton solve enforces local carrier balance. Adaptive boundary-value
collocation in log optical powers replaces the reference's clipped forward-Euler
shooting, preserving its equations while checking both mirror conditions and
transport residuals. Output includes gain, carrier/photon profiles, both facet
powers, adaptive mesh count and convergence diagnostics. No complex longitudinal
EM field or independent axial Poisson/thermal solve is claimed: those fields are
provided by the transverse model.

For two-way runs:

1. Solve the transverse electrical, thermal and EM equations with the current
   optical heating source.
2. Extract area-weighted MQW temperature and actual body-4 area from the mesh.
   Use both in the longitudinal active-laser equations; configured width/thickness
   do not replace the actual area for this coupled calculation.
3. Return `fraction * alpha_i * mean(P+ + P-) / actual_MQW_area` as MQW heating,
   replacing the transverse optical absorption source to avoid double counting.
4. Relax and repeat. Outer convergence requires heat mismatch, temperature change,
   and the longitudinal carrier/transport/mirror convergence checks to pass.

Active current and confinement remain explicit configured inputs. The reference
Lasers driver hard-codes its extracted baseline current (0.127953 A at 300 um);
TLaser does not silently substitute that baseline for a newly configured device.
Automatic transverse current/confinement extraction and pointwise 3D feedback
remain unimplemented. Temperature is a transverse input to the 1D model, so no
second independently estimated heat rise is added to the MQW temperature.

Electrical power/WPE use TLaser's existing series/shunt estimate, not the Lasers
reference driver's fixed leakage-current and voltage baseline. Neither is relabeled
as a terminal-current extraction. The PINN training/prediction backend remains
unchanged. New adaptive field-workspace results do not silently retrain models.

Validation includes carrier balance, both mirror boundaries, symmetric-cavity
symmetry, current response, actual-area/temperature handoff, rejection of passive
configurations and cancellation. Saved results remain candidates: numerical
convergence does not establish measured-device accuracy or inner Elmer convergence.

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
