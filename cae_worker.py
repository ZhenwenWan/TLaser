"""Background entry point; does not import Streamlit."""
import json
import sys
import traceback
from cae_jobs import job_path, write_json, check_cancel


def main(job_id):
    folder = job_path(job_id)
    request = json.loads((folder / "request.json").read_text(encoding="utf-8"))
    try:
        check_cancel(folder)
        write_json(folder / "status.json", {"state": "running", "stage": request["kind"]})
        if request["kind"] == "fields":
            from cae_elmer import run_fields
            state, stage = run_fields(folder, request["settings"])
        else:
            from cae_training import run_training
            state, stage = run_training(folder, request["settings"])
        check_cancel(folder)
        write_json(folder / "status.json", {"state": state, "stage": stage})
    except InterruptedError:
        write_json(folder / "status.json", {"state": "cancelled", "stage": "Cancelled by user"})
    except Exception as ex:
        traceback.print_exc()
        write_json(folder / "status.json", {"state": "failed", "stage": str(ex)})


if __name__ == "__main__":
    main(sys.argv[1])
