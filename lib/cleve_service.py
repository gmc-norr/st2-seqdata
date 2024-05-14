import requests
from typing import Any, Dict, Optional


class CleveError(Exception):
    pass


class Cleve:

    def __init__(
            self,
            host: str = "localhost",
            port: int = 8080,
            key: Optional[str] = None):
        self.uri = f"http://{host}:{port}/api"
        self.key = key

    def get_runs(self,
                 brief=True,
                 platform: Optional[str] = None,
                 state: Optional[str] = None) -> Dict[str, Dict]:
        uri = f"{self.uri}/runs"
        payload = {
            "platform": platform,
            "state": state,
        }

        # Must exclude brief if false since the response
        # would otherwise always be brief if the key is
        # present in the url.
        if brief:
            payload["brief"] = "yes"

        r = requests.get(uri, params=payload)

        if r.status_code != 200:
            raise CleveError(
                f"failed to fetch runs from {uri}: HTTP {r.status_code}")

        runs = {}
        for run in r.json():
            runs[run["run_id"]] = run
        return runs

    def add_run(self,
                runparameters: str,
                runinfo: str,
                path: str,
                state: str) -> Dict[str, Any]:
        if self.key is None:
            raise CleveError("no API key provided")

        uri = f"{self.uri}/runs"
        headers = {"Authorization": self.key}
        files = [(
            "runparameters", (
                "RunParameters.xml",
                open(runparameters, "rb"),
                "application/xml",
            ),
        ), (
            "runinfo", (
                "RunInfo.xml",
                open(runinfo, "rb"),
                "application/xml",
            ),
        )]
        payload = {
            "path": path,
            "state": state,
        }

        r = requests.post(
            uri,
            files=files,
            data=payload,
            headers=headers
        )

        if r.status_code != 200:
            raise CleveError(
                f"failed to add run to {uri}: "
                f"HTTP {r.status_code} {r.json()}"
            )

        return r.json()

    def update_run(self,
                   run_id: str,
                   state: str) -> Dict[str, Any]:
        if self.key is None:
            raise CleveError("no API key provided")

        uri = f"{self.uri}/runs/{run_id}"
        headers = {
            "Authorization": self.key,
        }
        payload = {
            "state": state,
        }

        r = requests.patch(uri, json=payload, headers=headers)

        if r.status_code != 200:
            raise CleveError(
                f"failed to update run {run_id} in {uri}: "
                f"HTTP {r.status_code} {r.json()}"
            )

        return r.json()

    def add_analysis(self,
                     run_id: str,
                     path: str,
                     state: str,
                     summary_file: Optional[str]) -> Dict[str, Any]:
        if self.key is None:
            raise CleveError("no API key provided")

        uri = f"{self.uri}/runs/{run_id}/analysis"
        headers = {
            "Authorization": self.key,
        }

        files: Dict[str, Any] = {
            "state": (None, state),
            "path": (None, path),
        }

        if summary_file is not None:
            files["summary_file"] = (
                "detailed_summary.json",
                open(summary_file, "rb"),
                "application/json",
            )

        r = requests.post(uri, files=files, headers=headers)

        if r.status_code != 200:
            raise CleveError(
                f"failed to add analysis for run {run_id}: "
                f"HTTP {r.status_code} {r.json()}"
            )

        return r.json()

    def update_analysis(self,
                        run_id: str,
                        analysis_id: str,
                        state: Optional[str],
                        summary_file: Optional[str]) -> Dict[str, Any]:
        if self.key is None:
            raise CleveError("no API key provided")

        uri = f"{self.uri}/runs/{run_id}/analysis/{analysis_id}"
        headers = {"Authorization": self.key}

        payload = None
        files = None

        if state is not None:
            payload = {
                "state": state,
            }

        if summary_file is not None:
            files = [(
                "analysis_summary", (
                    "detailed_summary.json",
                    open(summary_file, "rb"),
                    "application/json",
                ),
            )]

        r = requests.patch(uri, data=payload, files=files, headers=headers)

        if r.status_code != 200:
            raise CleveError(
                f"failed to update analysis for run {run_id} in {uri}: "
                f"HTTP {r.status_code} {r.json()}"
            )

        return r.json()
