# Changelog

All notable changes to the **TLaser** digital twin platform will be documented in this file.

---

## 2026-10-25 — CAD sections and graded meshes

* Configure 2D cuts by a point and plane-normal direction through the current CAD.
* Mesh intersected parts separately with shared interface connectivity and original
  IDs; replace the reduced geometry that caused the ridge-width discrepancy.
* Add true-scale section views, part inspection and world-coordinate navigation.
* Use continuous size fields in 2D and graded tetrahedral intervals in 3D,
  preserving every CAD part plane and thin layer.
* Keep arbitrary CAD sections out of the legacy solver's incompatible material map.
* Add geometry, grading, invalid-plane and UI regression checks and reproducible
  transverse, oblique and volume acceptance runs. All 17 tests passed; the default
  graded volume contains 1,162,992 tetrahedra with adjacent spacing ratios < 1.38.

## 2026-10-24 — Tetrahedral volume mesh

* Add 3D meshing of all 15 current CAD parts using conforming six-tetrahedra
  subdivision of a shared grid, with matching triangular material interfaces.
* Add part filtering, cavity cutaway and edge display; export Gmsh tetrahedra
  and Elmer 504 volume elements with 303 boundary triangles.
* Validate 28,170 tetrahedra, 5,820 nodes and 5,920 shared-interface triangles.
  Thirteen regression tests pass; the browser generation/cutaway workflow passes.
* Keep volume meshes out of the existing transverse 2D solver selection.
  This completes volume meshing; a full 3D physics solver remains future work.

## 2026-10-24 — Explicit mesh sizes and shared interfaces

* Put Configure & run first and remove its configuration load/save controls.
* Replace scale inputs with target/minimum/maximum size in µm, checked before
  launch and applied to the Gmsh size field. Preserve legacy worker settings.
* Require boundary elements for every material region and identical node/edge
  connectivity with correct parents across shared interfaces.
* Passed nine tests and two real Gmsh runs; checked reports and meshes are saved
  under validation/mesh_sizes. Full 3D CAD volume meshing remains pending.

## 2026-10-24 — Focused Mesh workflow

* Simplified Mesh results to view, details and download; removed redundant
  headings, examples, job selector/status controls and prominent node counts.
* Added generation preflight, cross-section size preview, automatic background
  progress/completion, cancellation and failure diagnostics in Configure & run.
* Passed 11 targeted tests and a real browser-triggered Gmsh generation with
  automatic display of its completed mesh.
* Keep the latest successful mesh visible after failures and provide a reference
  mesh download when no generated mesh exists. Preserve solver job controls.

## 2026-10-24 — Independent part dimensions

* Replace Geometry controls with a bilingual Dimensions table containing 16
  independent part dimensions, with shared dimensions owned by the first part.
* Rebuild layer positions, symmetric shoulders/isolation, metal widths and facet
  sizes using the inspected Lasers generator's dependency rules.
* Remove Parts and dimensions and Physical model parameters panels. Move
  operating/effective prediction inputs to Prediction → Operating conditions.
* Passed 20 targeted geometry, UI and downstream regression tests.
* Preserve CAD edits in device JSON while accepting older configurations.
  Mesh scales remain separate until individual CAD-to-mesh mapping is implemented.

## 2026-10-23 — Geometry-driven transverse meshing

* Added physical lateral/layer scaling to Gmsh jobs and an explicit transfer from
  Geometry controls; old configurations retain unit scales.
* Validate material areas, physical bounds and contact tags/locations/lengths
  before accepting meshes and before loading new meshes into the field solver.
* Export geometry and acceptance reports with mesh packages; retain the solver's
  selected geometry snapshot for provenance.
* Added three reproducible Gmsh examples (reference, scaled, refined), saved mesh
  files, reports and comparison plot visible in Mesh results.
* Passed 21 targeted regression tests; documented the remaining staged CAE plan.

## 2026-10-23 — Six CAE workspaces

* Reorganized edge-emitter navigation into Geometry, Mesh, Simulator, PINN,
  Prediction and Calibration, with matching Chinese navigation.
* Separated meshing from solver selection; preserved job configuration, load/save,
  results, validation examples, training, prediction and calibration workflows.
* Added explicit geometry part visibility and topology-preserving CAD scaling;
  defaulted to true proportions. Added reference mesh preview and planar 3D
  inspection with optional element edges.
* Simplified titles and moved method notes into expandable details. Documented
  the existing limits of CAD-to-mesh mapping and ML inverse calibration.

## 2026-10-22 — Saved solver validation results

* Added independent carrier, mirror, gain, integrated photon-transport, field
  finiteness, transverse steady-state and outer-feedback validation checks.
  New longitudinal and coupled jobs save downloadable `validation.json` reports.
* Added shipped **Included validation example** results for workspaces 3 and 4,
  including input snapshots, check tables, PNG/CSV curves, reference comparisons,
  grid refinement, actual VTU fields and solver logs. They are available without
  local jobs or an installed solver runtime.
* Added `validate_solvers.py` to reproduce and package the examples from the
  actual Lasers reference source and a completed coupled job.
* Verified 30 software tests, including example rendering without local jobs,
  rejection of corrupted carrier/mirror data, and preservation of a failed
  transverse diagnostic despite converged outer feedback. Updated the main-tab
  test to account for the nested visualization/configuration tabs.
* Longitudinal numerical checks passed. The stricter coupled example converged
  in three outer iterations with its final transverse solve converged after 11
  iterations, but **full acceptance remains incomplete**: the Elmer log contains
  a NaN Poynting-vector diagnostic. The report preserves this failed check.
* See [the validation report](Doc/solver_validation.md) for measured numerical
  values, acceptance thresholds, plots, reproduction instructions and limitations.

## 2026-10-22 — CAE workspaces, Lasers methodology, and visualization

### Implemented

* Bilingual five-section workflow: Device model, Simulator core, PINN surrogate,
  Instant Performance Prediction, and Instant Parameter Calibration.
* Interactive Lasers reference geometry, saved device configurations, and design
  parameters shared across prediction and calibration workflows.
* Four Simulator core workspaces: Lasers/Gmsh mesher, transverse 2D solver,
  longitudinal 1D solver, and iterative 1D–2D coupled solver. Each has configuration
  import/export, saved-run selection, and result visualization.
* Isolated background jobs with progress, cancellation, logs, saved settings,
  result artifacts, and explicit candidate/failure states.
* Transverse Lasers/Elmer Poisson and electron/hole transport, lattice heat,
  vector electromagnetic fields, and photon-population coupling.
* Active longitudinal carrier balance and bidirectional optical transport based
  on Lasers Task 1.6: temperature-dependent gain, spontaneous/stimulated emission,
  facet reflection, and spatial hole burning. Adaptive boundary-value integration
  checks carrier, mirror, and transport residuals.
* Two-way averaged optothermal feedback: measured mesh MQW area and computed MQW
  temperature feed the longitudinal model; cavity optical absorption heating
  returns to the transverse model. Inner longitudinal convergence is required
  before the outer loop can report convergence.
* Simulation-driven surrogate datasets, model training, held-out validation/test
  evaluation, model export, and explicit activation of models passing configured
  gates. The reduced training backend remains separate from the field solver.
* Visible **Visualization & results** and **Configure & run** tabs. Solver
  workspaces appear at the top of Simulator core; **Current sweep · L-I-V curves**
  has its own panel. Empty and unfinished runs explain how to obtain plots.
* Field contours, rotatable mesh inspection, EM phase controls, expanded
  cross-section curves, longitudinal carrier/gain/photon/power curves, coupling
  histories, and CSV/VTU/JSON downloads.

### Methodology correction

The temporary passive longitudinal probe model introduced in `1983de9` was
replaced by the Lasers active-laser formulation in `01f3ba3`. New runs reject
passive-probe configurations; historical results retain their original labels.
Lasers partitions the physics between transverse full-field equations and
longitudinal carrier/optical transport. TLaser does not claim an independent
longitudinal Poisson/heat/vector-Maxwell solve or a full volumetric 3D solve.

### Validation recorded

* 27 tests passed across CAE infrastructure, workspaces, active longitudinal
  physics, device workflows, section rendering, and reference geometry.
* Separate Streamlit checks passed for saved active-laser result rendering and
  the visible visualization tabs with empty-result guidance. After the navigation
  change, all four workspace tests and three device-section tests passed again.
* A matched 401-node comparison gave 0.002506211066 W from the Lasers reference
  and 0.002505684998 W from TLaser: a 0.021% difference. This is a numerical
  comparison, not experimental validation.
* The installed Lasers runtime completed a two-iteration coupled smoke run.
  Final heat mismatch was approximately 1.79e-4 and relative temperature change
  1.92e-5; both longitudinal solves converged. The short transverse run still
  requires inner-convergence review, so results remain candidates.

### Access and remaining scope

Restart `./run_tlaser.ps1`. Open **Simulator core**, choose a workspace, then
**Visualization & results** and a finished saved run. If none exists, use
**Configure & run**, start a task, then return and refresh. Saved jobs are local
to `runs/`; Git updates do not transfer simulation results or external runtimes.

Automatic transverse active-current/confinement extraction, pointwise 3D
feedback, independently calibrated material libraries, mesh-convergence studies,
and measured-device qualification remain outstanding. Current and confinement
are explicit inputs. WPE uses TLaser's series/shunt electrical estimate.

Implementation milestones: `b5758ca` (four workspaces), `01f3ba3` (Lasers active
methodology), and `b8a0a9a` (visualization navigation). See the
[CAE implementation and operating guide](Doc/cae_implementation.md) for equations,
source references, runtime requirements, and model limitations.

## [v0.1.0-prototype] - 2026-08-10

### Added
* **VCSEL Digital Twin Extension Mode**:
  * Implemented radial physical simulation prototype in [`simulator/vcsel_simulator.py`](file:///C:/Users/aw4wz/Documents/Codex/TLaser/simulator/vcsel_simulator.py) modeling current crowding, self-heating, thermal rollover, and radial spatial hole burning.
  * Added validation JSON schema at [`data/schemas/vcsel_liv_measurement.schema.json`](file:///C:/Users/aw4wz/Documents/Codex/TLaser/data/schemas/vcsel_liv_measurement.schema.json).
  * Added VCSEL adaptation plan and roadmap in [`Doc/vcsel_adaptation_plan.md`](file:///C:/Users/aw4wz/Documents/Codex/TLaser/Doc/vcsel_adaptation_plan.md).
  * Created [`generate_vcsel_animation.py`](file:///C:/Users/aw4wz/Documents/Codex/TLaser/generate_vcsel_animation.py) and generated the compiled H.264 demonstration video `TLaser_VCSEL_Demonstration.mp4`.
* **Automated Test Coverage**:
  * Introduced [`tests/test_tlaser.py`](file:///C:/Users/aw4wz/Documents/Codex/TLaser/tests/test_tlaser.py) containing 9 unit tests covering simulators, datasets, scaling boundaries, calibration, app imports, and documents.
  * Integrated unit test suite as Step 5 in the automated pipeline verification.
* **Sandbox Verification**:
  * Configured [`verify_pipeline.py`](file:///C:/Users/aw4wz/Documents/Codex/TLaser/verify_pipeline.py) to run temporary checks in `data/smoke_test/` to preserve production weights and datasets.

### Changed
* **App Architecture Hardening**:
  * Refactored Streamlit [`app.py`](file:///C:/Users/aw4wz/Documents/Codex/TLaser/app.py) to invoke `run_calibration()` cleanly instead of using `sys.argv` mutation.
  * Standardized UTF-8 encoding across all text file IO operations.
  * Rebuilt documentation and solved Matplotlib font and CJK glyph compile warnings in PDF manual scripts.
* **Deprecation Fixes**:
  * Removed the deprecated `'iprint'` option from `scipy.optimize.minimize` in `calibrate.py` to prevent `OptimizeWarning` pollution.
  * Replaced `np.trapz` references in `vcsel_simulator.py` with custom trapezoidal integration for NumPy 2.0 compatibility.
