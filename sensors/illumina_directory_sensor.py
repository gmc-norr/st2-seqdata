from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from st2common import log as logging
from st2reactor.sensor.base import PollingSensor
from typing import Dict, List, Optional, Union
import xml.etree.ElementTree as ET

from cleve_service import Cleve

LOG = logging.getLogger(__name__)


PLATFORMS = {
    "NovaSeq X Plus": {
        "serial_tag": "InstrumentSerialNumber",
        "serial_pattern": "LH",
        "ready_marker": "CopyComplete.txt",
    },
    "NextSeq 5x0": {
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

        LOG.debug("watched directories:")
        for wd in self._watched_directories:
            LOG.debug(f"  - {wd}")

    def setup(self):
        pass

    def poll(self):
        """
        Poll the file system for new run and analysis directories
        as well as state changes of existing directories.
        """
        registered_rundirs = self.cleve.get_runs(brief=True)
        moved_runs = self._check_new_runs(registered_rundirs)
        self._check_existing_runs(registered_rundirs, moved_runs)

        runs = self.cleve.get_runs(brief=False, platform="NovaSeq X Plus", state="ready")
        LOG.debug(f"found {len(runs)} ready NovaSeq X Plus runs")
        for run_id, run in runs.items():
            self._check_for_analysis(
                run_id,
                Path(run["path"]),
                run.get("analysis", [])
            )

    def _find_emitted_trigger(self,
                              trigger: str,
                              payload: Dict,
                              newer_than: datetime) -> Optional[str]:
        """
        Find a specific trigger instance with a certain
        payload that is newer than the given timestamp.
        """
        timeformat = "%Y-%m-%dT%H:%M:%S.%fZ"
        try:
            client = self.sensor_service.datastore_service.get_api_client()
        except NotImplementedError:
            # API client not available in tests, return no matches
            return None
        instances = client.triggerinstances.query(
            trigger=f"gmc_norr_seqdata.{trigger}",
            timestamp_gt=newer_than.strftime(timeformat),
        )
        for instance in instances:
            if instance.payload == payload:
                return instance.id

        return None

    def _find_incomplete_directory_trigger(self,
                                           payload: Dict) -> Optional[str]:
        """
        Find an incomplete_directory trigger instance with a particular
        payload that is less than one week old.
        """
        one_week_old = (datetime.now(timezone.utc) - timedelta(days=7))
        return self._find_emitted_trigger(
            "incomplete_directory",
            payload,
            one_week_old
        )

    def _find_duplicate_run_trigger(self,
                                    payload: Dict) -> Optional[str]:
        """
        Find a duplicate run trigger instance with a particular
        payload that is less than one week old.
        """
        one_week_old = (datetime.now(timezone.utc) - timedelta(days=7))
        return self._find_emitted_trigger(
            "duplicate_run",
            payload,
            one_week_old
        )

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

    def _handle_duplicate_run(self,
                              run_id: str,
                              path: Union[Path, str],
                              duplicate_path: Union[Path, str]) -> None:
        LOG.warning(f"run {run_id} with path "
                             f"{path} was also "
                             f"found at {duplicate_path}")
        payload = dict(
            run_id=run_id,
            path=str(path),
            duplicate_path=str(duplicate_path),
            email=self.config.get("notification_email"),
        )
        t = self._find_duplicate_run_trigger(payload)
        if t is None:
            self._emit_trigger(
                "duplicate_run",
                **payload,
            )
        else:
            LOG.debug("trigger instance with the same "
                               "payload found within the last week, "
                               "won't emit new trigger")

    def _handle_incomplete_directory(self,
                                     rundir: Path,
                                     state: str = DirectoryState.INCOMPLETE,
                                     message: str = "") -> None:
        LOG.debug(f"incomplete run directory: {rundir}")
        LOG.debug(f"reason: {message}")
        email = self.config.get("notification_email", [])
        if not email:
            LOG.info("no email addresses provided, "
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
            LOG.debug("trigger instance with the same "
                               "payload found within the last week, "
                               "won't emit new trigger")

    def _check_new_runs(self, registered_rundirs: Dict[str, Dict]) -> List[str]:
        """
        Check for new run directories within the watched directories.

        :param registered_rundirs: Existing run directories
        :type registered_rundirs: dict
        """
        moved_runs = []
        for wd in self._watched_directories:
            LOG.debug(f"checking watch directory: {wd}")
            if not os.path.exists(wd):
                LOG.error(f"directory {wd} does not exist")
                continue

            root, dirnames, _ = next(os.walk(wd))

            for dirname in dirnames:
                dirpath = Path(root) / str(dirname)
                LOG.debug(f"looking at {dirpath}")
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
                LOG.debug(f"identified run as {run_id}")

                if run_id in registered_rundirs:
                    registered_path = Path(registered_rundirs[run_id]["path"])
                    state_history = registered_rundirs[run_id].get("state_history", [])
                    registered_state = None
                    if state_history:
                        registered_state = state_history[0]["state"]

                    if not registered_path.exists() and \
                        str(registered_path) != str(dirpath) and \
                            registered_state != DirectoryState.MOVED:
                        # directory has been moved within the watched directories
                        LOG.debug(f"{dirpath} moved from {registered_path}")
                        self._emit_trigger(
                            "state_change",
                            run_id=run_id,
                            path=str(dirpath),
                            state=DirectoryState.MOVED,
                            directory_type=DirectoryType.RUN)
                        moved_runs.append(run_id)
                    if registered_path.exists() and registered_path != dirpath:
                        self._handle_duplicate_run(run_id, registered_path, dirpath)
                    continue

                LOG.debug(f"new directory found: {dirpath}")
                self._emit_trigger(
                    "new_directory",
                    run_id=run_id,
                    runparameters=str(dirpath / "RunParameters.xml"),
                    runinfo=str(dirpath / "RunInfo.xml"),
                    path=str(dirpath),
                    state=self.run_directory_state(dirpath),
                    directory_type=DirectoryType.RUN)
                self._check_for_analysis(run_id, dirpath)

        return moved_runs

    def _check_existing_runs(self,
                             registered_rundirs: Dict[str, Dict],
                             moved_runs: List[str]) -> None:
        """
        Check existing run directories for state changes and new samplesheets.

        :param registered_rundirs: Existing run directories
        :type registered_rundirs: dict
        :param moved_runs: List of run ids that are already known to have been moved
        :type moved_runs: list
        """
        for run_id, rundir in registered_rundirs.items():
            registered_path = Path(rundir["path"])
            LOG.debug(f"checking existing run directory: {registered_path}")
            platform = rundir['platform']
            state_history = registered_rundirs[run_id].get("state_history", [])
            registered_state = None
            if state_history:
                registered_state = state_history[0]["state"]

            if not registered_path.is_dir() and \
                run_id not in moved_runs and \
                    registered_state != DirectoryState.MOVED:
                # Run directory has been moved outside the watched directories
                # or deleted.
                self._emit_trigger(
                    "state_change",
                    run_id=run_id,
                    path=None,
                    state=DirectoryState.MOVED,
                    directory_type=DirectoryType.RUN)
                # Leave any additional state change for the next poll
                continue
            elif run_id in moved_runs:
                # It has already been handled, or the place to which it
                # has been moved is not known, so don't do any more
                # state changes in this round of polling.
                continue
            elif not registered_path.is_dir() and registered_state == DirectoryState.MOVED:
                # The directory has moved, and we don't know where,
                # don't try to update the state.
                continue

            current_state = self.run_directory_state(registered_path)

            if registered_state != current_state:
                LOG.debug(
                    f"{registered_path} changed state from "
                    f"{registered_state} to {current_state}"
                )
                self._emit_trigger(
                    "state_change",
                    run_id=run_id,
                    path=str(registered_path),
                    state=current_state,
                    directory_type=DirectoryType.RUN,
                    platform=platform,
                    target_directory=self.config.get("shared_drive")
                )

            # Find any new samplesheets
            samplesheet_info = rundir.get("samplesheets", [])
            if len(samplesheet_info) == 0 or not Path(samplesheet_info[-1].get("path")).exists():
                samplesheet_modtime = None
            else:
                mod_time_str = samplesheet_info[-1].get("modification_time")
                samplesheet_modtime = datetime.strptime(
                    mod_time_str,
                    "%Y-%m-%dT%H:%M:%S.%fZ",
                )
                samplesheet_modtime = samplesheet_modtime.replace(
                    microsecond=0,
                    tzinfo=timezone.utc
                )
            self._find_samplesheet(
                run_id=run_id,
                path=registered_path,
                newer_than=samplesheet_modtime
            )

    def _find_samplesheet(
            self,
            run_id: str,
            path: Path,
            newer_than: Optional[datetime] = None) -> None:
        """
        Find any new samplesheets in the given directory. If `newer_than` is
        not `None`, then a trigger will only be emitted if there is a
        samplesheet with a modification more recent than `newer_than`. If
        `newer_than` is `None`, then a trigger for the most recent samplesheet
        will be emitted, if one exists.
        """
        samplesheets = path.glob("[Ss]ample[Ss]heet*.csv")
        mod_times = []
        current_tz = datetime.now(timezone.utc).astimezone().tzinfo
        for ss in samplesheets:
            info = ss.stat()
            modification_time = datetime.fromtimestamp(
                info.st_mtime,
                tz=current_tz
            )
            modification_time = modification_time.replace(microsecond=0)
            mod_times.append((ss, modification_time))

        mod_times = sorted(mod_times, key=lambda x: x[1], reverse=True)

        if len(mod_times) == 0:
            return

        most_recent_samplesheet = mod_times[0]

        if newer_than is None:
            self._emit_trigger(
                "new_samplesheet",
                run_id=run_id,
                samplesheet=str(most_recent_samplesheet[0]),
            )
        elif most_recent_samplesheet[1] > newer_than:
            self._emit_trigger(
                "new_samplesheet",
                run_id=run_id,
                samplesheet=str(most_recent_samplesheet[0]),
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
            analyses[a["analysis_id"]] = a

        root, analysis_dirs, _ = next(os.walk(analysis_path))

        for analysis_dir in analysis_dirs:
            dirpath = Path(root) / str(analysis_dir)
            analysis_id = dirpath.name

            if not analysis_id.isdigit():
                # Most likely not a real analysis directory, ignore it
                continue

            LOG.debug(f"looking at analysis at {dirpath}")
            detailed_summary = list((dirpath / "Data" / "summary")
                                    .glob("*/detailed_summary.json"))

            if len(detailed_summary) == 0:
                detailed_summary = None
            else:
                detailed_summary = str(detailed_summary[0])
                LOG.debug(
                    f"found detailed summary at {detailed_summary}"
                )

            if analysis_id in analyses:
                LOG.debug(
                    "analysis dir has been registered for run, checking state"
                )
                registered_state = analyses[analysis_id]["state"]
                current_state = self.analysis_directory_state(dirpath)
                if registered_state != current_state:
                    LOG.debug(f"{dirpath} changed state "
                        f"from {registered_state} "
                        f"to {current_state}")
                    self._emit_trigger(
                        "state_change",
                        run_id=run_id,
                        analysis_id=analysis_id,
                        summary_file=detailed_summary,
                        state=current_state,
                        directory_type=DirectoryType.ANALYSIS,
                        path=str(dirpath),
                        target_directory=self.config.get("shared_drive"))
            else:
                LOG.debug(f"new analysis found: {dirpath}")
                self._emit_trigger(
                    "new_directory",
                    run_id=run_id,
                    summary_file=detailed_summary,
                    path=str(dirpath),
                    state=self.analysis_directory_state(dirpath),
                    directory_type=DirectoryType.ANALYSIS,
                    target_directory=self.config.get("shared_drive"))

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
        LOG.debug(f"looking for run id in {path}")
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

        LOG.debug(f"platform is {platform}")

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

        If a directory contains a RunParameters.xml file, a RunInfo.xml file
        and a CopyComplete.txt file, then the directory is ready for analysis,
        but only if the RunCompletionStatus.xml file also states that the run
        was successful.

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
        runcompletionstatus = path / "RunCompletionStatus.xml"

        if not runparams.is_file() or not runinfo.is_file():
            return DirectoryState.INCOMPLETE
        elif runparams.is_file() and runinfo.is_file() \
                and copycomplete.is_file():
            if runcompletionstatus.is_file():
                if self._run_completion_status(runcompletionstatus):
                    return DirectoryState.READY
                else:
                    return DirectoryState.ERROR
            else:
                return DirectoryState.READY
        elif runparams.is_file() and runinfo.is_file() and \
                not copycomplete.exists():
            return DirectoryState.PENDING
        else:
            return DirectoryState.UNDEFINED

    def _run_completion_status(self, path: Path) -> bool:
        """
        Read RunCompletionStatus.xml and return true if the run has
        successfully completed, and false otherwise.
        """
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            raise

        root = tree.getroot()
        # NovaSeq structure
        runstatus = root.find("RunStatus")
        if runstatus is not None and runstatus.text == "RunCompleted":
            return True

        if runstatus is None:
            # NextSeq structure
            runstatus = root.find("CompletionStatus")
            if runstatus is not None and \
                    runstatus.text == "CompletedAsPlanned":
                return True

        return False

    def analysis_directory_state(self, path: Path) -> str:
        copycomplete = path / "CopyComplete.txt"
        if copycomplete.is_file():
            return DirectoryState.READY
        else:
            return DirectoryState.PENDING
