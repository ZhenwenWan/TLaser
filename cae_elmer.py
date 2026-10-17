"""Run the Lasers transverse coupled case in an isolated TLaser job directory."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import numpy as np
from cae_jobs import ROOT, write_json, check_cancel
from cae_fields import read_vtu
from device_model import validate_config


def detect_lasers():
    candidates = [os.environ.get("TLASER_LASERS_ROOT", ""), str(ROOT.parent / "Lasers" / "Lasers"),
                  str(Path.home() / "Documents/Codex/Lasers/Lasers")]
    return next((str(Path(p)) for p in candidates if p and (Path(p)/"ExeLibs").is_dir()), "")


def runtime(lasers_root):
    root = Path(lasers_root).expanduser().resolve()
    home = root.parent / "tools/elmer-9.0-ucrt"
    exe = home / "bin/ElmerSolver.exe"
    libs = root / "ExeLibs"
    required = [exe] + [libs / name for name in ("CarriersFVMSolve_e12e17.dll", "ThermoSolve.dll", "EMWaveSolve.dll")]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise ValueError("Missing compatible Lasers runtime: " + ", ".join(missing))
    return root, home, exe, libs


def run_fields(folder, settings):
    root, home, exe, libs = runtime(settings["lasers_root"])
    bounds = {"temperature": (250, 450), "p_potential": (-1, 2), "frequency": (1e13, 1e15),
              "iterations": (3, 100), "tolerance": (1e-8, 1e-2)}
    for key, (low, high) in bounds.items():
        value = settings[key]
        if not isinstance(value, (int, float)) or not np.isfinite(value) or not low <= value <= high:
            raise ValueError(f"Invalid {key}")
    case = folder / "case"
    case.mkdir()
    shutil.copytree(ROOT / "assets/elmer/mesh", case / "mesh")
    source = (ROOT / "assets/elmer/coupled.sif").read_text(encoding="utf-8")
    text = source.replace('Mesh DB "../Mesh" "mesh01"', 'Mesh DB "." "mesh"')
    text = text.replace("../../ExeLibs/", libs.as_posix() + "/")
    text = re.sub(r"\$T0\s*=\s*300.0", f"$T0 = {settings['temperature']:.12g}", text)
    text = re.sub(r"\$tm\s*=\s*300", f"$tm = {settings['temperature']:.12g}", text)
    text = text.replace("Temperature = Real 300.0", f"Temperature = Real {settings['temperature']:.12g}")
    text = text.replace("Psi = Real 0.57724", f"Psi = Real {settings['p_potential']:.12g}")
    text = text.replace("1.934e14", f"{settings['frequency']:.12g}")
    drive = float(settings.get("em_drive", 0.))
    if not np.isfinite(drive) or not 0 <= drive <= 1:
        raise ValueError("Invalid EM current-source amplitude")
    if drive > 0:
        text = text.replace('Current Density 1 = Variable Carriers\n    Real Procedure "' + libs.as_posix()
                            + '/EMWaveSolve" "GetCurrentSourceReal1"',
                            f'Current Density 1 = Real {drive:.12g}')
    text = text.replace("Steady State Max Iterations = Integer 15", f"Steady State Max Iterations = Integer {int(settings['iterations'])}")
    text = text.replace("Steady State Convergence Tolerance = Real 1.0e-4", f"Steady State Convergence Tolerance = Real {settings['tolerance']:.12g}")
    c = validate_config(settings["configuration"])
    text = text.replace("Cavity Length = Real 300.0e-4", f"Cavity Length = Real {c['geometry']['L_um']*1e-4:.12g}")
    for index in (1, 2):
        text = text.replace(f"Mirror {index} Reflectivity = Real 0.3", f"Mirror {index} Reflectivity = Real {c['optical'][f'R{index}']:.12g}")
    (case / "case.sif").write_text(text, encoding="utf-8")
    write_json(folder / "provenance.json", {"backend": "Lasers Elmer coupled transverse FEM/FVM",
        "template_sha256": hashlib.sha256(source.encode()).hexdigest(), "runtime": str(exe),
        "custom_libraries": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                             (libs/"CarriersFVMSolve_e12e17.dll", libs/"ThermoSolve.dll", libs/"EMWaveSolve.dll")},
        "mesh": "Lasers reference mesh01; unchanged transverse geometry", "coordinate_unit": "cm"})
    env = os.environ.copy()
    env["ELMER_HOME"], env["ELMER_LIB"] = str(home), str(libs)
    env["PATH"] = os.pathsep.join([str(home/"bin"), str(home/"share/elmersolver/lib"),
                                  str(root.parent/"tools/msys64/ucrt64/bin"), str(libs), env.get("PATH", "")])
    with (folder / "solver.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([str(exe), "case.sif"], cwd=case, env=env, stdout=log,
            stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        started = time.monotonic()
        try:
            while process.poll() is None:
                check_cancel(folder)
                if time.monotonic()-started > 1800:
                    raise TimeoutError("Solver exceeded the 30-minute job limit")
                time.sleep(.3)
        except BaseException:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise
    log = (folder / "solver.log").read_text(encoding="utf-8", errors="replace")
    if process.returncode or re.search(r"ERROR::|MATC ERROR|Solver input file error", log):
        raise RuntimeError("Elmer failed; inspect solver.log for diagnostics")
    outputs = sorted(case.rglob("*.vtu"))
    if not outputs:
        raise RuntimeError("Solver produced no VTU fields")
    points, triangles, fields = read_vtu(outputs[-1])
    if not all(np.isfinite(a).all() for a in fields.values()):
        raise RuntimeError("Solver produced nonfinite fields")
    # A completed process is not proof of nonlinear/coupled convergence.
    warnings = list(dict.fromkeys(line.strip() for line in log.splitlines()
        if re.search(r"WARNING::|Deltamin|maximum.*iteration|\bNaN\b", line, re.I)
        and not re.search(r"any NaN.*:\s*F\s*$", line)))
    em = [v for k,v in fields.items() if k.startswith("electric field")]
    if em and all(np.max(np.abs(v)) == 0 for v in em):
        warnings.append("EM solution is zero for this excitation. No optical-wave amplitude is resolved.")
    write_json(folder / "fields.json", {"files": [str(p.relative_to(folder)) for p in outputs],
        "nodes": len(points), "triangles": len(triangles), "fields": list(fields),
        "elapsed_s": time.monotonic()-started, "warnings": warnings[-40:],
        "convergence": "Review nonlinear and coupled convergence in solver.log; exit code alone is insufficient"})
    return "candidate", "Field solve finished; inspect convergence and physical ranges"
