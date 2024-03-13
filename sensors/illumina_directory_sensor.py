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


class DirectoryState:
    COPYCOMPLETE = "CopyComplete.txt"
    UNDEFINED = "undefined"


class DirectoryType:
    RUN = "run"
    ANALYSIS = "analysis"


class IlluminaDirectorySensor(PollingSensor):
    _DATASTORE_KEY = "illumina_directories"
    _dispatched_directories: List[Dict[str, str]]

    def __init__(self, sensor_service, config=None, poll_interval=60):
        super(IlluminaDirectorySensor, self).__init__(sensor_service, config, poll_interval)
        self._logger = self.sensor_service.get_logger(__name__)
        self._watched_directories = self.config.get(self._DATASTORE_KEY, [])
        self._directories = {}

        self._logger.debug("watched directories:")
        for wd in self._watched_directories:
            self._logger.debug(f"  - {wd}")

        directories = self.sensor_service.get_value(self._DATASTORE_KEY)
        if directories is not None:
            for rd in json.loads(directories):
                self._directories[f"{rd['host']}:{rd['path']}"] = rd

    def setup(self):
        pass

    def poll(self):
        self._check_for_run()
        self._check_for_analysis()
        self._update_datastore()

    def _check_for_run(self):
        existing_directories = set()

        # TODO: group watched directories by host and process each as a unit

        for wd in self._watched_directories:
            self._logger.debug(f"checking watch directory: {wd['path']}")

            host = wd.get("host", "localhost") or "localhost"
            client = self._client(host)

            _, stdout, stderr = client.exec_command(
                f"find {wd['path']} -maxdepth 1 -mindepth 1 -type d"
            )

            # Add new directories or update state of existing directories
            for line in stdout:
                directory_path = Path(line.strip())
                directory_state = self.directory_state(directory_path, client)

                payload = {
                    "path": str(directory_path),
                    "host": host,
                    "type": DirectoryType.RUN,
                }

                existing_directories.add(f"{host}:{directory_path}")
                existing_directory = self._find_directory(directory_path, host)
                state_changed = False

                if existing_directory is None:
                    state_changed = True
                    self._add_directory(directory_path, host, directory_state, DirectoryType.RUN)
                    self.sensor_service.dispatch(
                        trigger="gmc_norr_seqdata.new_directory",
                        payload=payload
                    )
                else:
                    state_changed = existing_directory["state"] != directory_state
                    existing_directory["state"] = directory_state

                if state_changed:
                    if directory_state == DirectoryState.COPYCOMPLETE:
                        self.sensor_service.dispatch(
                            trigger="gmc_norr_seqdata.copy_complete",
                            payload=payload,
                        )

            for line in stderr:
                self._logger.warning(f"stderr: {line}")

            client.close()

        # Remove directories that no longer exist
        for k in set(self._directories.keys()) - existing_directories:
            self._logger.debug(f"removing directory: {self._directories[k]}")
            self._directories.pop(k)

    def _check_for_analysis(self):
        """
        Check for an analysis directory inside run directories that are COPYCOMPLETE.
        """
        existing_directories = set()
        run_directories = [rd for rd in self._directories.values() if rd["type"] == DirectoryType.RUN and rd["state"] == DirectoryState.COPYCOMPLETE]

        for rd in run_directories:
            if rd["type"] != DirectoryType.RUN or rd["state"] != DirectoryState.COPYCOMPLETE:
                continue
            self._logger.debug(f"checking for analysis directory in {rd['host']}{rd['path']}")

            host = rd.get("host", "localhost") or "localhost"
            client = self._client(host)

            _, stdout, stderr = client.exec_command(
                f"find {rd['path']} -maxdepth 1 -mindepth 1 -type d -name Analysis"
            )

            analysis_dir = stdout.read().strip()
            if not analysis_dir:
                continue

            _, stdout, stderr = client.exec_command(
                f"find {analysis_dir} -maxdepth 1 -mindepth 1 -type f -name CopyComplete.txt"
            )

            directory_state = self.directory_state(str(analysis_dir), client)

            existing_directories.add(f"{host}:{analysis_dir}")
            existing_directory = self._find_directory(str(analysis_dir), host)
            state_changed = False

            payload = {
                "path": analysis_dir,
                "host": host,
                "type": DirectoryType.ANALYSIS,
            }

            if existing_directory is None:
                state_changed = True
                self._add_directory(analysis_dir, host, directory_state, DirectoryType.ANALYSIS)
                self.sensor_service.dispatch(
                    trigger="gmc_norr_seqdata.new_directory",
                    payload=payload
                )
            else:
                state_changed = existing_directory["state"] != directory_state
                existing_directory["state"] = directory_state

            if state_changed:
                for line in stderr:
                    self._logger.warning(f"stderr: {line}")

                if directory_state == DirectoryState.COPYCOMPLETE:
                    self.sensor_service.dispatch(
                        trigger="gmc_norr_seqdata.copy_complete",
                        payload=payload,
                    )

            client.close()

    def cleanup(self):
        pass

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass

    def directory_state(self, path: Union[Path, str], client: Union[SSHClient, LocalHostClient]):
        states = [
            DirectoryState.COPYCOMPLETE,
        ]

        for state in states:
            _, stdout, _ = client.exec_command(
                f"find {str(path)} -name {state}"
            )

            if len(stdout.read()) > 0:
                return state

        return DirectoryState.UNDEFINED

    def _client(self, hostname: str):
        user = self.config.get("user")
        keyfile = self.config.get("ssh_key")

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

    def _add_directory(self, directory: Path, host: str, state: str, type: str):
        self._logger.debug(f"adding directory: {host}:{directory}")
        self._directories[f"{host}:{str(directory)}"] = {
            "path": str(directory),
            "host": host,
            "state": state,
            "type": type,
        }

    def _find_directory(self, directory: Union[Path, str], host: str):
        return self._directories.get(f"{host}:{str(directory)}", None)

    def _update_datastore(self):
        self._logger.debug("updating datastore with directories")
        self.sensor_service.set_value(
            self._DATASTORE_KEY,
            json.dumps(list(self._directories.values()))
        )
