import requests
from typing import Dict


class CleveError(Exception):
    pass


class Cleve:

    def __init__(self, host: str, port: int):
        self.uri = f"http://{host}:{port}/api"

    def get_runs(self, platform: str = None, state: str = None) -> Dict[str, Dict]:
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
