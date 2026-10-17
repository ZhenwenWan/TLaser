"""Persistent isolated CAE jobs. Workers own their output directories."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs"


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    # Windows readers/virus scanners can briefly deny atomic replacement.
    for attempt in range(40):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 39:
                raise
            time.sleep(.05)


def job_path(job_id):
    if not isinstance(job_id, str) or not job_id or any(c not in "0123456789abcdef" for c in job_id):
        raise ValueError("Invalid job identifier")
    return RUNS / job_id


def start_job(kind, settings):
    if kind not in {"fields", "training"}:
        raise ValueError("Unknown job kind")
    job_id = uuid.uuid4().hex
    folder = job_path(job_id)
    folder.mkdir(parents=True)
    write_json(folder / "request.json", {"kind": kind, "settings": settings,
               "created_at": datetime.now(timezone.utc).isoformat(), "schema_version": 1})
    write_json(folder / "status.json", {"state": "queued", "stage": "Starting worker"})
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    with (folder / "worker.log").open("w", encoding="utf-8") as log:
        try:
            process = subprocess.Popen([sys.executable, str(ROOT / "cae_worker.py"), job_id],
                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as ex:
            write_json(folder / "status.json", {"state": "failed", "stage": str(ex)})
            raise
    write_json(folder / "process.json", {"pid": process.pid})
    return job_id


def read_jobs(kind):
    jobs = []
    if RUNS.exists():
        for folder in sorted(RUNS.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not folder.is_dir():
                continue
            try:
                request = json.loads((folder / "request.json").read_text(encoding="utf-8"))
                if request["kind"] == kind:
                    status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
                    jobs.append((folder.name, request, status))
            except (OSError, ValueError, KeyError):
                continue
    return jobs


def cancel_job(job_id):
    (job_path(job_id) / "cancel").touch()


def check_cancel(folder):
    if (folder / "cancel").exists():
        raise InterruptedError("Cancelled by user")
