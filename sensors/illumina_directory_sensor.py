from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from st2reactor.sensor.base import PollingSensor
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

from cleve_service import Cleve


PLATFORMS = {
    "NovaSeq": {
        "serial_tag": "InstrumentSerialNumber",
        "serial_pattern": "LH",
        "ready_marker": "CopyComplete.txt",
    },
    "NextSeq": {
        "serial_tag": "InstrumentID",
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
    ERROR = "error"
    MOVED = "moved"
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
        registered_rundirs = self.cleve.get_runs(brief=True)
        self._check_for_run(registered_rundirs)

        runs = self.cleve.get_runs(brief=False, platform="NovaSeq", state="ready")
        self._logger.debug(f"found {len(runs)} ready NovaSeq runs")
        for run_id, run in runs.items():
            self._check_for_analysis(
                run_id,
                Path(run["path"]),
                run.get("analysis", [])
            )

    def _find_incomplete_directory_trigger(self,
                                           payload: Dict) -> Optional[str]:
        """
        Find an incomplete_directory trigger instance with the same
        payload that is less than one week old.
        """
        timeformat = "%Y-%m-%dT%H:%M:%S.%fZ"
        one_week_old = (datetime.now(timezone.utc) - timedelta(days=7))

        try:
            client = self.sensor_service.datastore_service.get_api_client()
        except NotImplementedError:
            # API client not available in tests, return no matches
            return None
        instances = client.triggerinstances.query(
            trigger="gmc_norr_seqdata.incomplete_directory",
            timestamp_gt=one_week_old.strftime(timeformat),
        )
        for instance in instances:
            if instance.payload == payload:
                return instance.id

        return None

    def _run_info_ok(self, rundir: Path) -> None:
        """
        Check that RunInfo.xml exists and is not empty.

        :param rundir: path to the run directory
        """
        runinfofile = rundir / "RunInfo.xml"
        if not runinfofile.is_file():
            raise IOError(f"{runinfofile} does not exist")
        if runinfofile.stat().st_size == 0:
            raise ValueError(f"{runinfofile} is empty")

    def _handle_incomplete_directory(self,
                                     rundir: Path,
                                     state: str = DirectoryState.INCOMPLETE,
                                     message: str = "") -> None:
        self._logger.debug(f"incomplete run directory: {rundir}")
        self._logger.debug(f"reason: {message}")
        email = self.config.get("notification_email", [])
        if not email:
            self._logger.info("no email addresses provided, "
                              "no trigger dispatched")
            return
        payload = dict(
            path=str(rundir),
            state=state,
            directory_type=DirectoryType.RUN,
            message=message,
            email=self.config.get("notification_email", []),
        )
        t = self._find_incomplete_directory_trigger(payload)
        if t is None:
            self._emit_trigger(
                "incomplete_directory",
                **payload,
            )
        else:
            self._logger.debug("trigger instance with the same "
                               "payload found within the last week, "
                               "won't emit new trigger")

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
        moved_dirs = set()
        for wd in self._watched_directories:
            self._logger.debug(f"checking watch directory: {wd}")

            root, dirnames, _ = next(os.walk(wd))

            for dirname in dirnames:
                dirpath = Path(root) / str(dirname)
                self._logger.debug(f"looking at {dirpath}")
                try:
                    run_id = self.get_run_id(dirpath)
                except IOError as e:
                    self._handle_incomplete_directory(
                        dirpath,
                        DirectoryState.INCOMPLETE,
                        str(e),
                    )
                    continue
                except ET.ParseError as e:
                    self._handle_incomplete_directory(
                        dirpath,
                        DirectoryState.ERROR,
                        str(e),
                    )
                    continue
                except ValueError as e:
                    self._handle_incomplete_directory(
                        dirpath,
                        DirectoryState.ERROR,
                        str(e),
                    )
                    continue
                try:
                    self._run_info_ok(dirpath)
                except IOError as e:
                    self._handle_incomplete_directory(
                        dirpath,
                        DirectoryState.INCOMPLETE,
                        str(e),
                    )
                    continue
                except ValueError as e:
                    self._handle_incomplete_directory(
                        dirpath,
                        DirectoryState.ERROR,
                        str(e),
                    )
                    continue
                self._logger.debug(f"identified run as {run_id}")
                if run_id in registered_rundirs:
                    registered_path = registered_rundirs[run_id]["path"]
                    if registered_path != str(dirpath):
                        moved_dirs.add(run_id)
                        self._logger.debug(f"{dirpath} moved from {registered_path}")
                        self._emit_trigger(
                            "state_change",
                            run_id=run_id,
                            path=str(dirpath),
                            state=DirectoryState.MOVED,
                            directory_type=DirectoryType.RUN)

                    state_history = registered_rundirs[run_id].get("state_history", [])
                    registered_state = None
                    if state_history:
                        registered_state = state_history[0]["state"]
                    current_state = self.run_directory_state(dirpath)

                    if registered_state != current_state:
                        self._logger.debug(
                            f"{dirpath} changed state from "
                            f"{registered_state} to {current_state}"
                        )
                        self._emit_trigger(
                            "state_change",
                            run_id=run_id,
                            path=str(dirpath),
                            state=current_state,
                            directory_type=DirectoryType.RUN)
                else:
                    self._logger.debug(f"new directory found: {dirpath}")
                    self._emit_trigger(
                        "new_directory",
                        run_id=run_id,
                        runparameters=str(dirpath / "RunParameters.xml"),
                        runinfo=str(dirpath / "RunInfo.xml"),
                        path=str(dirpath),
                        state=self.run_directory_state(dirpath),
                        directory_type=DirectoryType.RUN)
                    self._check_for_analysis(run_id, dirpath)

        # Check if existing runs have been moved out of the watched directories
        for run in registered_rundirs.values():
            # Don't emit a trigger if the state already is moved
            state_history = run.get("state_history", [])
            if state_history and state_history[0]["state"] == DirectoryState.MOVED:
                continue
            dirpath = Path(run["path"])
            if run["run_id"] not in moved_dirs and not dirpath.is_dir():
                self._logger.debug(f"run {run['run_id']} is missing")
                self._emit_trigger(
                    "state_change",
                    run_id=run["run_id"],
                    path=str(run["path"]),
                    state=DirectoryState.MOVED,
                    directory_type=DirectoryType.RUN
                )

    def _check_for_analysis(
            self,
            run_id: str,
            path: Path,
            existing_analyses: Optional[List[Dict]] = None) -> None:
        """
        Check for an analysis directory inside NovaSeq run directories that
        are ready.
        """
        analysis_path = Path(path) / "Analysis"
        if not analysis_path.is_dir():
            # There are no analysis directories to check
            return

        analyses = {}
        for a in existing_analyses or []:
            analyses[a["path"]] = a

        root, analysis_dirs, _ = next(os.walk(analysis_path))

        for analysis_dir in analysis_dirs:
            dirpath = Path(root) / str(analysis_dir)
            self._logger.debug(f"looking at analysis at {dirpath}")
            detailed_summary = list((dirpath / "Data" / "summary")
                                    .glob("*/detailed_summary.json"))

            if len(detailed_summary) == 0:
                detailed_summary = None
            else:
                detailed_summary = str(detailed_summary[0])
                self._logger.debug(
                    f"found detailed summary at {detailed_summary}"
                )

            analysis_id = dirpath.name

            if str(dirpath) in analyses:
                self._logger.debug(
                    "analysis dir has been registered for run, checking state"
                )
                registered_state = analyses[str(dirpath)]["state"]
                current_state = self.analysis_directory_state(dirpath)
                if registered_state != current_state:
                    self._logger.debug(f"{dirpath} changed state "
                                       f"from {registered_state} "
                                       f"to {current_state}")
                    self._emit_trigger(
                        "state_change",
                        run_id=run_id,
                        analysis_id=analysis_id,
                        summary_file=detailed_summary,
                        state=current_state,
                        directory_type=DirectoryType.ANALYSIS)
            else:
                self._logger.debug(f"new analysis found: {dirpath}")
                self._emit_trigger(
                    "new_directory",
                    run_id=run_id,
                    summary_file=detailed_summary,
                    path=str(dirpath),
                    state=self.analysis_directory_state(dirpath),
                    directory_type=DirectoryType.ANALYSIS)

    def _emit_trigger(self, trigger: str, **kwargs) -> None:
        """
        Emit a stackstorm trigger.

        :param trigger: The trigger name
        :type trigger: str
        :param run_id: The sequencing run ID
        :type run_id: str
        :param path: The path to the directory
        :type path: pathlib.Path
        :param state: The directory state
        :type state: str
        :param type: The directory type
        :type type: str
        :param message: An optional message
        :type message: str
        """
        self.sensor_service.dispatch(
            trigger=f"gmc_norr_seqdata.{trigger}",
            payload=kwargs,
        )

    def get_run_id(self, path: Path) -> str:
        """
        Get the sequencing run ID from RunParameters.xml.

        :param path: The path to the sequencing run directory
        :type path: pathlib.Path
        :raises IOError: If the RunParameters.xml file cannot be found
        :raises ET.ParseError: If the RunParameters.xml file cannot be parsed
        :raises ValueError: If the sequencing platform or run ID cannot be identified
        :return: The run ID.
        :rtype: str
        """
        self._logger.debug(f"looking for run id in {path}")
        runparamsfile = path / "RunParameters.xml"
        if not runparamsfile.is_file():
            raise IOError(f"{runparamsfile} does not exist")
        try:
            tree = ET.parse(runparamsfile)
        except ET.ParseError:
            raise
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

        for x in ("RunID", "RunId"):
            run_id = root.find(x)
            if run_id is not None:
                break
        else:
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

    def run_directory_state(self, path: Path) -> str:
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
        runinfo = path / "RunInfo.xml"
        copycomplete = path / "CopyComplete.txt"

        if not runparams.is_file() or not runinfo.is_file():
            return DirectoryState.INCOMPLETE
        elif runparams.is_file() and runinfo.is_file() and copycomplete.is_file():
            return DirectoryState.READY
        elif runparams.is_file() and runinfo.is_file() and not copycomplete.exists():
            return DirectoryState.PENDING
        else:
            return DirectoryState.UNDEFINED

    def analysis_directory_state(self, path: Path) -> str:
        copycomplete = path / "CopyComplete.txt"
        if copycomplete.is_file():
            return DirectoryState.READY
        else:
            return DirectoryState.PENDING
