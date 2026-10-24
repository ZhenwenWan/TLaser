# TLaser CAE implementation

## Workspace navigation (2026-10-23)

The bilingual edge-emitter interface uses six concise workspaces:

| Workspace | Workflow |
| --- | --- |
| Geometry / 几何 | Shared design configuration, rotatable material assembly, part visibility, topology-preserving lateral/layer scaling and exploded inspection. True proportions are the initial view. |
| Mesh / 网格 | Gmsh configuration, save/load, jobs, mesh export and 2D or navigable 3D inspection. The bundled reference mesh is visible before the first job. |
| Simulator / 仿真 | Transverse 2D, longitudinal 1D and coupled 1D–2D solver selection; independent configuration, saved results, fields, curves and validation examples. L-I-V sweep remains available. |
| PINN | Training jobs and model review/activation in separate tabs. |
| Prediction / 预测 | Active surrogate predictions and existing physical-simulator comparison. |
| Calibration / 标定 | Existing measurement import, parameter fitting, acceptance and application workflow. |

This is a UI reorganization, preserving existing numerical engines and saved job/configuration formats. Geometry now uses independent part dimensions (see the 2026-10-24 update below); Mesh retains separate scale settings. Visibility remains an inspection setting; the full 15-part CAD assembly is not meshed. The 3D mesh view navigates planar 2D triangles, not volume elements. Calibration still fits the physical simulator; a verified ML inverse model is not yet connected. The separate VCSEL workflow is retained.

## Focused Mesh workspace (2026-10-24)

Mesh results now contain only the 2D/3D mesh view, edge visibility, expandable
Mesh details and Download mesh. The duplicate heading, model/example panels,
manual refresh, run selector, completed-status banner and prominent counts are
removed from Mesh. Simulator job interfaces are unchanged.

Configure & run retains portable configuration load/save and exposes refinement,
lateral/layer scale and the Gmsh path. It previews the physical cross-section
size and validates settings and executable availability before starting a job.
Generate mesh starts an isolated background job; controls prevent duplicate
launches while it runs. Progress refreshes automatically every two seconds with
a cancel action. Completion reloads the latest successful mesh automatically.
Failure/cancellation diagnostics stay in Configure & run, and the previous usable
mesh remains visible. A reference mesh and its ZIP download are available before
any local generation. Mesh details identifies the generated mesh for selection
in Simulator. Old jobs and validation evidence remain on disk.

Validation: 11 targeted tests passed, including configuration preflight, missing
Gmsh rejection, failure fallback, clean reference presentation and solver
workspace regression checks. A browser-triggered real Gmsh run
`230ffdc0acf946f7bd73220ab5b093b0` completed with 1663 nodes / 3218 triangles;
its identity and accepted mesh report appeared automatically in Mesh details.

This remains the reduced 2D transverse mesher; full CAD-to-domain mapping and
volume meshing are not added by this workflow simplification.

## Geometry dimension editor (2026-10-24)

Geometry now shows **Dimensions / 尺寸**: a table of 16 independent part
measurements (part, length/width/height, value in µm). Shared dimensions are
listed only at the first owning part. The previous Parts and dimensions and
Physical model parameters panels are removed. Part visibility uses the 3D legend.

The dependency rules were inspected in the local Lasers source
`Lasers/App/Geometry/telecom_laser_geometry.py`:

* Substrate length drives the first 13 body parts; chip width drives the six
  full-width layers, backside metal and both facet coatings.
* Each of the first six layer heights is independent. Equal numerical values
  (such as upper/lower SCH thickness) do not create a constraint.
* Ridge width and combined ridge/cladding height are independent. Shoulder
  width is `(chip width - ridge width)/2`; the first shoulder owns their shared
  height. Both shoulder centers follow the ridge and chip edges.
* The first SiN part owns isolation width and height for both sides. Width is
  equivalent to choosing the source generator's window clearance, and must fit
  inside the derived shoulder width.
* P-metal width is `1.6 * ridge width`. P-metal and backside metal heights remain
  independent, even though both start at 0.25 µm.
* The rear facet owns coating length (thickness along the cavity axis), shared
  with the front facet. Facet width follows chip width; height follows the full
  layer stack including both metal thicknesses. Source facet placement is retained.

Update device validates positive finite dimensions and topology constraints,
rebuilds stack coordinates, and synchronizes cavity length. The existing device
JSON save/load persists optional `cad_dimensions`; old configurations still load
with reference dimensions. Current, temperature, reflectivities and effective
1D/PINN dimensions are under Prediction → Operating conditions.

These individual CAD dimensions are **not yet mapped into the reduced 11-region
mesh**. The earlier Geometry scale-transfer button is removed with its source
controls to avoid copying invisible/stale settings; Mesh retains its own editable
physical scale settings and saved configurations. Earlier descriptions of that
button below describe the previous increment. Implementing a full explicit
CAD-to-reduced-domain mapping remains the next meshing task.

Tests cover reconstruction of all reference part coordinates, shared dimension
propagation, independent equal-valued layer thicknesses, layer adjacency, JSON
round-trip, invalid topology rejection and bilingual UI editing.

## Increment 1: geometry-driven transverse meshing (2026-10-23)

Geometry's lateral and layer scale controls now have an explicit downstream path:

1. Set **Parts and dimensions** in Geometry.
2. Open **Mesh → Configure & run → Use Geometry scales**. This copies the two
   scale values into an independent mesh configuration snapshot; later Geometry
   edits do not silently change that snapshot. Alternatively edit them in Mesh.
3. Choose element-size scale, save the configuration if desired, and run the job.
4. Inspect the mesh and its region-area/contact acceptance report. Downloads
   include the generated geometry JSON, Gmsh geometry, Elmer mesh and report.
5. In Simulator configuration, select the completed job as **Solver mesh**.
   New geometry-bearing meshes are checked again before the field solver runs;
   the solver job saves `mesh_geometry.json` for provenance.

Both geometry scales accept finite values from 0.5 to 2. The reduced cross-section
is transformed in physical coordinates, preserving the eleven material regions,
left/right symmetry and contact IDs. At lateral 1.4 / layer 0.8, width is 16.8 µm,
height 3.384 µm, ridge width 4.2 µm and MQW thickness 0.064 µm. Hidden parts are
not removed. Effective 1D width/thickness and trained model domains stay separate.
Legacy mesh configurations default to unit geometry scales.

Validation: `python validate_mesh_geometry.py --gmsh C:/gmsh/gmsh.exe` reproduces
three real Gmsh cases under `validation/mesh_geometry`. Reports check finite
nonzero triangles, all eleven material areas, domain bounds, required exterior
tags, contact locations and lengths. The refinement case must increase element
count. The saved plot/report are available in **Mesh → Visualization & results →
Validated mesh examples**, independently of local simulation jobs.

| Case | Lateral / layer scale | Element-size scale | Nodes | Triangles |
| --- | --- | --- | --- | --- |
| Reference | 1 / 1 | 1 | 1663 | 3218 |
| Scaled | 1.4 / 0.8 | 1 | 755 | 1412 |
| Scaled, refined | 1.4 / 0.8 | 0.5 | 2691 | 5206 |

All geometric checks passed. Software tests also reject invalid scales,
corrupted coordinates and missing contacts, and check configuration migration
and UI scale transfer. This is mesh validation, not a mesh-convergence study of
physical outputs or a new validation of Elmer on changed geometries.

## Ordered development plan

Each increment must ship with reproducible evidence, documentation and a commit.

1. **Complete:** physical transverse scaling, independent mesh snapshots and
   geometry/contact acceptance checks.
2. **Next:** explicit region-level geometry editing and geometry save/load,
   followed by mesh/solver convergence comparisons on modified cross-sections.
3. Volume meshing of the CAD assembly with material/interface tags and mesh
   quality checks; enable solver consumption only after the formulation supports it.
4. Simulator scenario management and robust field/postprocessing acceptance,
   including resolving the outstanding coupled Poynting diagnostic and extracting
   transverse current/confinement for longitudinal feedback.
5. Connect selectable validated simulator scenarios to PINN datasets/training;
   retain independent held-out validation and precise physics provenance.
6. Verified-model prediction with domain/uncertainty checks, then ML-driven
   inverse calibration with identifiability and synthetic-recovery tests.
7. Measured-device benchmarks and engineering qualification across all workflows.

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
6. Maintain the six-section workspace, existing calibration acceptance checks,
   shared configuration, bilingual UI, and reproducible reports.

## Fidelity boundaries and remaining engineering validation

The Lasers reference mesh is a 2D transverse mesh (1663 nodes / 3218 triangles),
not a volumetric mesh of the 15-part CAD visualization. Explicit lateral/layer scaling now generates new transverse meshes with preserved material/contact tags. Effective solver width
and thickness do not remesh this transverse domain. Longitudinal PINN datasets
use the reduced quasi-3D engine, with a documented fixed set of physical
constants. Neither output provenance is relabeled as a full 3D solve.

Before production qualification: measured-device benchmark suites, mesh and
domain convergence studies, independently verified material/doping libraries,
general geometry meshing beyond uniform transverse scaling, 3D vector Maxwell analysis, and coupled
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
