import os
from pathlib import Path
import requests
from st2reactor.sensor.base import PollingSensor
from typing import Dict
import xml.etree.ElementTree as ET

from cleve_service import Cleve


PLATFORMS = {
    "NovaSeq": {
        "serial_tag": "InstrumentSerialNumber",
        "serial_pattern": "LH",
        "ready_marker": "CopyComplete.txt",
    },
    "NextSeq": {
        "serial_tag": "InstrumentId",
        "serial_pattern": "NB",
        "ready_marker": "CopyComplete.txt",
    },
    "MiSeq": {
        "serial_tag": "ScannerID",
        "serial_pattern": "M",
        "ready_marker": "RTAComplete.txt",
    },
}


class DirectoryState:
    NEW = "new"
    READY = "ready"
    PENDING = "pending"
    UNDEFINED = "undefined"
    INCOMPLETE = "incomplete"


class DirectoryType:
    RUN = "run"
    ANALYSIS = "analysis"


class IlluminaDirectorySensor(PollingSensor):

    def __init__(self, sensor_service, config=None, poll_interval=60):
        super(IlluminaDirectorySensor, self).__init__(sensor_service, config, poll_interval)
        self._logger = self.sensor_service.get_logger(__name__)
        self._watched_directories = self.config.get("illumina_directories", [])
        self._directories = {}

        if "cleve_service" in self.config:
            # This is for testing purposes. In production, host
            # and port should be used
            self.cleve = self.config.get("cleve_service")
        else:
            self.cleve = Cleve(
                self.config.get("cleve", {}).get("host"),
                self.config.get("cleve", {}).get("port"),
            )

        self._logger.debug("watched directories:")
        for wd in self._watched_directories:
            self._logger.debug(f"  - {wd}")

    def setup(self):
        pass

    def poll(self):
        """
        Poll the file system for new run and analysis directories
        as well as state changes of existing directories.
        """
        registered_rundirs = self.cleve.get_runs()
        self._check_for_run(registered_rundirs)
        self._check_for_analysis()

    def _check_for_run(self, registered_rundirs: Dict[str, Dict]) -> None:
        """
        Check for new run directories, or state changes of existing run
        directories.

        Emits triggers for new run directories, state changes of existing run
        directories, and also incomplete run directories where essential
        information is missing.

        :param registered_rundirs: Existing run directories
        :type registered_rundirs: dict
        """
        for wd in self._watched_directories:
            self._logger.debug(f"checking watch directory: {wd}")

            root, dirnames, _ = next(os.walk(wd))

            for dirname in dirnames:
                dirpath = Path(root) / str(dirname)
                self._logger.debug(f"looking at {dirpath}")
                try:
                    run_id = self.get_run_id(dirpath)
                except IOError as e:
                    self._logger.debug(f"incomplete run directory: {str(e)}")
                    self._emit_trigger(
                        "incomplete_directory",
                        dirpath,
                        DirectoryState.INCOMPLETE,
                        DirectoryType.RUN,
                        message=str(e),
                    )
                    continue
                self._logger.debug(f"identified run as {run_id}")
                if run_id in registered_rundirs:
                    registered_state = registered_rundirs[run_id]["state_history"][0]["state"]
                    current_state = self.directory_state(dirpath)

                    print(registered_state, current_state)

                    if registered_state != current_state:
                        self._logger.debug(f"{dirpath} changed state from {registered_state} to {current_state}")
                        self._emit_trigger("state_change", dirpath, current_state, DirectoryType.RUN)
                else:
                    self._logger.debug(f"new directory found: {dirpath}")
                    self._emit_trigger("new_directory", dirpath, DirectoryState.NEW, DirectoryType.RUN)

    def _check_for_analysis(self):
        """
        Check for an analysis directory inside NovaSeq run directories that
        are ready.
        """
        runs = self.cleve.get_runs(platform="NovaSeq", state="ready")

        self._logger.debug(f"found {len(runs)} ready NovaSeq runs")

        for run in runs.values():
            print(run["path"])
            analysis_path = Path(run["path"]) / "Analysis"
            if not analysis_path.is_dir():
                # There are no analysis directories to check
                continue
            existing_analyses = {}
            for analysis in run.get("analysis", []):
                existing_analyses[analysis["path"]] = analysis

            root, analysis_dirs, _ = next(os.walk(analysis_path))

            for analysis_dir in analysis_dirs:
                dirpath = Path(root) / str(analysis_dir)
                self._logger.debug(f"looking at analysis at {dirpath}")
                if dirpath in existing_analyses:
                    self._logger.debug(f"analysis dir has been registered for run, checking state")
                    registered_state = existing_analyses[dirpath]["state"]
                    current_state = self.directory_state(dirpath)
                    if registered_state != current_state:
                        self._logger.debug(f"{dirpath} changed state from {registered_state} to {current_state}")
                        self._emit_trigger("state_change", dirpath, current_state, DirectoryType.ANALYSIS)
                else:
                    self._logger.debug(f"new analysis found: {dirpath}")
                    self._emit_trigger("new_directory", dirpath, self.directory_state(dirpath), DirectoryType.ANALYSIS)

    def _emit_trigger(self, trigger: str, path: Path, state: str, type: str, message: str = ""):
        """
        Emit a stackstorm trigger.

        :param trigger: The trigger name
        :type trigger: str
        :param path: The path to the directory
        :type path: pathlib.Path
        :param state: The directory state
        :type state: str
        :param type: The directory type
        :type type: str
        :param message: An optional message
        :type message: str
        """
        payload = {
            "path": str(path),
            "state": state,
            "type": type,
            "message": message,
        }
        self.sensor_service.dispatch(trigger=f"gmc_norr_seqdata.{trigger}", payload=payload)

    def get_run_id(self, path: Path) -> str:
        """
        Get the sequencing run ID from RunParameters.xml.

        :param path: The path to the sequencing run directory
        :type path: pathlib.Path
        :raises ValueError: If the sequencing platform or run ID cannot be identified
        :return: The run ID.
        :rtype: str
        """
        self._logger.debug(f"looking for run id in {path}")
        runparamsfile = path / "RunParameters.xml"
        if not runparamsfile.is_file():
            raise IOError(f"{runparamsfile} does not exist")
        tree = ET.parse(runparamsfile)
        root = tree.getroot()

        for p, d in PLATFORMS.items():
            serialelem = root.find(d["serial_tag"])
            if serialelem is None:
                continue
            serial = str(serialelem.text)
            platform = p
            if not serial.startswith(d["serial_pattern"]):
                raise ValueError(f"Serial number {serial} does not belong to {platform}")
            break
        else:
            raise ValueError("Could not identify platform")

        self._logger.debug(f"platform is {platform}")

        run_id = root.find("RunId")
        if run_id is None:
            raise ValueError(f"RunId not found in {runparamsfile}")
        return str(run_id.text)

    def cleanup(self):
        pass

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass

    def directory_state(self, path: Path) -> str:
        """
        Get the state of a directory

        If a directory contains a RunParameters.xml file and a CopyComplete.txt
        file, then the directory is ready for analysis.

        If the directory only contains a RunParameters.xml file, processing on
        the machine is not yet complete, so the directory is pending.

        If the directory contains neither a RunParameters.xml file nor a
        CopyComplete.txt file, then the directory is incomplete and will not
        be added to the database.

        :param path: The path to the run directory
        :type path: pathlib.Path
        :return: The state of the directory
        :rtype: str
        """
        runparams = path / "RunParameters.xml"
        copycomplete = path / "CopyComplete.txt"

        if runparams.is_file() and copycomplete.is_file():
            return DirectoryState.READY
        elif runparams.is_file() and not copycomplete.exists():
            return DirectoryState.PENDING
        elif not runparams.is_file():
            return DirectoryState.INCOMPLETE
        else:
            return DirectoryState.UNDEFINED
