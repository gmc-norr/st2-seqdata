from io import StringIO
import json
import os
from pathlib import Path
import paramiko
from paramiko.client import SSHClient, AutoAddPolicy
import pwd
from st2reactor.sensor.base import PollingSensor
import subprocess
from typing import Dict, List, Union


class LocalHostClient:

    def __init__(self, username):
        self.hostname = "localhost"

        if username is None:
            self.user_uid = os.getuid()
            self.user_gid = os.getgid()
        else:
            pw_record = pwd.getpwnam(username)
            self.user_uid = pw_record.pw_uid
            self.user_gid = pw_record.pw_gid

    def exec_command(self, cmd):
        if isinstance(cmd, str):
            cmd = cmd.split()
        p = subprocess.run(cmd, preexec_fn=self._preexec, encoding="utf-8",
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           check=True)
        return "", StringIO(p.stdout), StringIO(p.stderr)

    def _preexec(self):
        os.setgid(self.user_gid)
        os.setuid(self.user_uid)

    def close(self):
        pass


class RunDirectoryState:
    ANALYSISCOMPLETE = "AnalysisComplete.txt"
    COPYCOMPLETE = "CopyComplete.txt"
    RTACOMPLETE = "RTAComplete.txt"
    UNDEFINED = "undefined"


class RunDirectorySensor(PollingSensor):
    _DATASTORE_KEY = "run_directories"
    _dispatched_run_directories: List[Dict[str, str]]

    def __init__(self, sensor_service, config=None, poll_interval=60):
        super(RunDirectorySensor, self).__init__(sensor_service, config, poll_interval)
        self._logger = self.sensor_service.get_logger(__name__)
        self._watched_directories = self.config.get("run_directories", [])
        self._run_directories = {}

        self._logger.debug("watched directories:")
        for wd in self._watched_directories:
            self._logger.debug(f"  - {wd}")

        run_directories = self.sensor_service.get_value(self._DATASTORE_KEY)
        if run_directories is not None:
            for rd in json.loads(run_directories):
                self._run_directories[f"{rd['host']}:{rd['path']}"] = rd

    def setup(self):
        pass

    def poll(self):
        for wd in self._watched_directories:
            self._logger.debug(f"checking watch directory: {wd['path']}")

            host = wd.get("host", "localhost") or "localhost"
            client = self._client(host)

            _, stdout, stderr = client.exec_command(
                f"find {wd['path']} -maxdepth 1 -mindepth 1 -type d"
            )

            existing_run_directories = set()

            # Add new run directories or update state of existing run directories
            for line in stdout:
                run_directory_path = Path(line.strip())
                run_directory_state = self.run_directory_state(run_directory_path, client)

                payload = {
                    "run_directory": str(run_directory_path),
                    "host": host
                }

                existing_run_directories.add(f"{host}:{run_directory_path}")
                existing_run_directory = self._find_run_directory(run_directory_path, host)
                state_changed = False

                if existing_run_directory is None:
                    state_changed = True
                    self._add_run_directory(run_directory_path, host, run_directory_state)
                    self.sensor_service.dispatch(
                        trigger="gmc_norr_seqdata.new_run_directory",
                        payload=payload
                    )
                else:
                    state_changed = existing_run_directory["state"] != run_directory_state
                    existing_run_directory["state"] = run_directory_state

                if state_changed:
                    if run_directory_state == RunDirectoryState.COPYCOMPLETE:
                        self.sensor_service.dispatch(
                            trigger="gmc_norr_seqdata.copy_complete",
                            payload=payload,
                        )
                    elif run_directory_state == RunDirectoryState.RTACOMPLETE:
                        self.sensor_service.dispatch(
                            trigger="gmc_norr_seqdata.rta_complete",
                            payload=payload,
                        )
                    elif run_directory_state == RunDirectoryState.ANALYSISCOMPLETE:
                        self.sensor_service.dispatch(
                            trigger="gmc_norr_seqdata.analysis_complete",
                            payload=payload,
                        )

            # Remove run directories that no longer exist
            for k in set(self._run_directories.keys()) - existing_run_directories:
                self._logger.debug(f"removing run directory: {self._run_directories[k]}")
                self._run_directories.pop(k)

            for line in stderr:
                self._logger.warning(f"stderr: {line}")

            client.close()

        self._update_datastore()

    def cleanup(self):
        pass

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass

    def run_directory_state(self, path: Union[Path, str], client: Union[SSHClient, LocalHostClient]):
        states = [
            RunDirectoryState.ANALYSISCOMPLETE,
            RunDirectoryState.COPYCOMPLETE,
            RunDirectoryState.RTACOMPLETE,
        ]

        for state in states:
            _, stdout, _ = client.exec_command(
                f"find {str(path)} -name {state}"
            )

            if len(stdout.read()) > 0:
                return state

        return RunDirectoryState.UNDEFINED

    def _client(self, hostname: str):
        user = self.sensor_service.get_value("service_user", local=False)
        keyfile = self.sensor_service.get_value("service_keyfile", local=False)

        self._logger.debug(f"connecting to {hostname} as {user}")

        if hostname == "localhost":
            client = LocalHostClient(user)
        else:
            client = SSHClient()
            client.set_missing_host_key_policy(AutoAddPolicy)

            try:
                client.connect(
                    hostname=hostname,
                    username=user,
                    key_filename=keyfile,
                )
            except paramiko.ssh_exception.AuthenticationException as e:
                self._logger.error(f"Authentication failed for {user}@{hostname}: {e}")
                raise RuntimeError

        return client

    def _add_run_directory(self, run_directory: Path, host: str, state: str):
        self._logger.debug(f"adding run directory: {host}:{run_directory}")
        self._run_directories[f"{host}:{str(run_directory)}"] = {
            "path": str(run_directory),
            "host": host,
            "state": state
        }

    def _find_run_directory(self, run_directory: Union[Path, str], host: str):
        return self._run_directories.get(f"{host}:{str(run_directory)}", None)

    def _update_datastore(self):
        self.sensor_service.set_value(
            self._DATASTORE_KEY,
            json.dumps(list(self._run_directories.values()))
        )
