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
        self.uri = f"{host}:{port}/api"
        self.key = key

    def _get(self, uri: str, params=None) -> Dict[str, Any]:
        r = requests.get(uri, params=params)
        if r.status_code != 200:
            raise CleveError(
                f"failed to fetch {uri}: HTTP {r.status_code}"
            )
        return r.json()

    def get_runs(self,
                 brief=True,
                 platform: Optional[str] = None,
                 state: Optional[str] = None) -> Dict[str, Dict]:
        uri = f"{self.uri}/runs"
        payload = {
            "platform": platform,
            "state": state,
            "page_size": 0,  # Get all runs
        }

        # Must exclude brief if false since the response
        # would otherwise always be brief if the key is
        # present in the url.
        if brief:
            payload["brief"] = "yes"

        res = self._get(uri, payload)

        runs = {}
        for run in res.get("runs", []):
            runs[run["run_id"]] = run
        return runs

    def add_run(self,
                path: str,
                state: str) -> Dict[str, Any]:
        if self.key is None:
            raise CleveError("no API key provided")

        uri = f"{self.uri}/runs"
        headers = {"Authorization": self.key}
        payload = {
            "path": path,
            "state": state,
        }

        r = requests.post(
            uri,
            json=payload,
            headers=headers
        )

        if r.status_code != 200:
            raise CleveError(
                f"failed to add run to {uri}: "
                f"HTTP {r.status_code} {r.json()}"
            )

        return r.json()

    def update_run_path(self,
                        run_id: str,
                        path: str) -> Dict[str, Any]:
        if self.key is None:
            raise CleveError("no API key provided")

        uri = f"{self.uri}/runs/{run_id}/path"
        headers = {
            "Authorization": self.key,
        }
        payload = {
            "path": path,
        }

        r = requests.patch(uri, json=payload, headers=headers)

        if r.status_code != 200:
            raise CleveError(
                f"failed to update run {run_id} in {uri}: "
                f"HTTP {r.status_code} {r.json()}"
            )

        return r.json()

    def update_run_state(self,
                         run_id: str,
                         state: str) -> Dict[str, Any]:
        if self.key is None:
            raise CleveError("no API key provided")

        uri = f"{self.uri}/runs/{run_id}/state"
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

    def update_samplesheet(self,
                           run_id: str,
                           samplesheet: str) -> Dict[str, Any]:
        if self.key is None:
            raise CleveError("no API key provided")

        uri = f"{self.uri}/runs/{run_id}/samplesheet"
        headers = {
            "Authorization": self.key,
        }
        payload = {
            "samplesheet": samplesheet,
        }

        r = requests.post(uri, json=payload, headers=headers)

        if r.status_code != 200:
            raise CleveError(
                f"failed to update samplesheet for run {run_id} in {uri}: "
                f"HTTP {r.status_code} {r.json()}"
            )

        return r.json()

    def add_run_qc(self, run_id: str) -> Dict[str, Any]:
        if self.key is None:
            raise CleveError("no API key provided")

        uri = f"{self.uri}/runs/{run_id}/qc"
        headers = {
            "Authorization": self.key,
        }

        r = requests.post(uri, headers=headers)

        if r.status_code != 200:
            raise CleveError(
                f"failed to add QC for run {run_id}: "
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
