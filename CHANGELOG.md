# Changelog

All notable changes to the **TLaser** digital twin platform will be documented in this file.

---

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
