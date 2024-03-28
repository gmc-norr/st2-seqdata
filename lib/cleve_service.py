import requests
import time
from typing import Dict, Optional


class CleveError(Exception):
    pass


class Cleve:

    def __init__(self, host: str, port: int):
        self.uri = f"http://{host}:{port}/api"

    def get_runs(self, platform: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Dict]:
        uri = f"{self.uri}/runs?brief"
        if platform:
            uri += f"&platform={platform}"
        if state:
            uri += f"&state={state}"

        r = requests.get(uri)

        if r.status_code != 200:
            raise CleveError(f"failed to fetch runs from {self.uri}: HTTP {r.status_code}")

        runs = {}
        for run in r.json():
            runs[run["run_id"]] = run
        return runs


class CleveMock(Cleve):

    def __init__(self, runs: Optional[Dict[str, Dict]] = None):
        self.runs = {}
        if runs is not None:
            self.runs = runs

    def get_runs(self, platform: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Dict]:
        runs = {}
        for run_id, run in self.runs.items():
            last_state = sorted(run["state_history"], key=lambda x: x["time"], reverse=True)[0]["state"]
            if platform and run["platform"] != platform:
                continue
            if state and last_state != state:
                continue
            runs[run_id] = run
        return runs

    def add_run(self, run: Dict):
        if "run_id" not in run:
            raise CleveError("run must have a run_id")
        if "state_history" not in run:
            raise CleveError("run must have a state_history")
        if "platform" not in run:
            raise CleveError("run must have a platform")
        self.runs[run["run_id"]] = run

    def update_run(self, run_id: str, state: Optional[str] = None, analysis: Optional[Dict] = None):
        if run_id not in self.runs:
            raise CleveError(f"run {run_id} not found")

        if state is not None:
            self.runs[run_id]["state_history"].append({"state": state, "time": time.time()})
        if analysis is not None:
            self.runs[run_id]["analysis"].append(analysis)
