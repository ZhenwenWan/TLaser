# Shared device model — first local release

## Run and review

From the project directory, run `./run_tlaser.ps1`, then open http://localhost:8501.
The launcher supports the existing dependency installation even when its old
Windows Store Python launcher is unavailable. For a fresh environment, install
`requirements.txt` (or the direct versions in `requirements-local-tested.txt`)
and run `python -m streamlit run app.py`.

Select **Edge-emitting Diode Laser**. Edit dimensions and select **Update device**.
The top view and cross-section update from a shared schema-version-1 configuration.
Save/load configurations in the disclosure above the editor. Switch workflows in
the sidebar; the same device and original snapshot remain selected. English and
Chinese are supported.

In prediction, choose **Nominal PINN** or **Physical simulator**. The nominal PINN
always uses its seven design/operating inputs and ignores fitted constants.
The physical simulator uses all constants in the saved configuration, or accepted
fitted constants when explicitly applied in the calibration workflow.

In calibration, choose explicit **Synthetic demo** or upload measurement JSON.
Start with one parameter (series resistance by default). The result shows original
and estimated parameters, fixed geometry, measured/original/estimated LIV curves,
optimizer status, normalized losses, bound status and local sensitivities.
Only candidates passing convergence, loss-improvement, normalized loss below 0.01,
and local diagnostic checks
can be applied. Download candidate configuration or the full calibration report,
including original/estimated snapshots, measurements, timestamp and content hash.

## Data contract and geometry

Current must be known **active-region current**, in amperes. Ordinary measured
terminal current includes leakage and is not accepted as active current silently.
JSON requires `current_semantics: "active_region"`, `current_A`, `voltage_V`,
`optical_power_W`, and metadata matching the chosen `L_um`, `w_um`, `d_um`, `R1`,
`R2`, `T0`. There must be 5–200 finite points and at least five distinct currents.
The app offers a template with clearly marked example values. The new shared
workflow intentionally uses JSON; legacy CSV handling is not reused because it
silently supplies fixed geometry and lacks current semantics.

Geometry contains named effective active, substrate-context and cladding-context
regions and rear/front facet boundaries. Only the effective active region and
cavity dimensions are physical model inputs. Substrate/cladding are fixed
illustrations. Display scales differ by axis and vertical thickness is exaggerated.
Active width is not asserted to equal a verified etched ridge width; active
thickness is not a resolved epitaxial stack. This is a fixed template, not CAD.

Configuration validation uses the documented seven-input sampling bounds, not
the padded normalization ranges. Membership is not an accuracy guarantee.
Edge calibration estimates only selected supported physical constants; dimensions,
facets, temperature and operating preset remain fixed. Local sensitivity and
Jacobian conditioning do not establish globally unique identification or device
accuracy. Five-parameter fits may be ambiguous or fail to converge.

## Integration boundaries

The new edge workflow uses in-memory, session-specific uploads and results. It
does not overwrite historical shared calibration files. A configuration edit/load
invalidates the current fit and applied-state flag. The app can display geometry
and run the simulator when the nominal weights cannot load.

The legacy VCSEL demonstration remains separately available. It has not been
converted to the shared schema and retains its legacy persistence behavior.
Its C multiplier is not identifiable from the current LIV output calculation.
This release does not qualify that path for production use.

DFB grating physics, EML absorber/modulation physics, inverse geometry estimation,
thermal feedback in the edge solver, and real FEM integration are future work.
CW is an operating preset, not a separate architecture. No public deployment was
performed. Authentication, customer-data retention, persistent multiuser storage,
background calibration execution and hosting costs remain undecided. Static
presentation pages cannot execute the Python application.

The existing model was trained on synthetic data without a held-out split.
Smoke execution or synthetic fit recovery does not prove measured-device accuracy.
The reduced solver does not expose a trustworthy convergence certificate; that
physics/QA upgrade and a held-out surrogate benchmark remain required before
product-grade accuracy claims. No sub-5-ms UI latency claim is made.

## Verification

`python -m unittest discover -s tests -p test_device_workflow.py -v` checks schema
round trips and rejection cases, dimension-to-backend/schematic agreement,
measurement validation, a known series-resistance recovery, fixed geometry,
failed-fit rejection and shared design state across workflow/language switches.
Unlike the legacy verification pipeline, these tests do not overwrite training
artifacts or calibration history.

On 2026-10-09, all seven focused tests passed using Python 3.12 and the locally
installed dependencies recorded in `requirements-local-tested.txt`. They include
the complete synthetic-demo → fit → apply → simulator-prediction interaction and
fit invalidation after editing geometry. This checks behavior, not telecom-device
measurement accuracy. The restricted execution sandbox blocks Python's local
socket initialization; a live browser preview needs permission to start the server
outside that sandbox. After approval, the server was started at
http://127.0.0.1:8502 and its controls, geometry image and nominal prediction
outputs were checked in the browser. The ordinary local launcher remains
`./run_tlaser.ps1` (port 8501 by default).
