from dataclasses import dataclass
import datetime
import os
from pathlib import Path
from st2tests.base import BaseSensorTestCase
import tempfile
import time
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock

from illumina_directory_sensor import (
    IlluminaDirectorySensor,
    DirectoryState,
    DirectoryType,
    PLATFORMS
)
from cleve_service import Cleve


class IlluminaDirectorySensorTestCase(BaseSensorTestCase):
    sensor_cls = IlluminaDirectorySensor

    def setUp(self):
        super(IlluminaDirectorySensorTestCase, self).setUp()

        self.watch_directories = [
            tempfile.TemporaryDirectory(),
            tempfile.TemporaryDirectory(),
        ]

        self.target_directory = tempfile.TemporaryDirectory()
        # Mock the cleve service
        self.cleve = Cleve(key="supersecretapikey")
        self.cleve.runs = {}
        self.cleve.get_runs = Mock(
            side_effect=self._get_runs
        )
        self.cleve.add_run = Mock(
            side_effect=self._add_run
        )
        self.cleve.update_run_path = Mock(
            side_effect=self._update_run_path
        )
        self.cleve.update_run_state = Mock(
            side_effect=self._update_run_state
        )
        self.cleve.add_analysis = Mock(
            side_effect=self._add_analysis
        )
        self.cleve.update_analysis = Mock(
            side_effect=self._update_analysis
        )

        self.sensor = self.get_sensor_instance(config={
            "illumina_directories": [Path(d.name) for d in self.watch_directories],
            "cleve_service": self.cleve,
            "notification_email": ["me@mail.com"],
            "shared_drive": self.target_directory.name,
        })

    def _get_runs(
            self,
            brief: bool = False,
            platform: Optional[str] = None,
            state: Optional[str] = None) -> Dict[str, Dict]:
        filtered_runs = {}
        for run_id, r in self.cleve.runs.items():
            platform_match = not platform or r["platform"] == platform
            state_history = r.get("state_history", [])
            past_state = None
            if state_history:
                past_state = state_history[0]["state"]
            state_match = not state or past_state == state
            if platform_match and state_match:
                filtered_runs[run_id] = r.copy()
            if brief:
                if "runparameters" in filtered_runs[run_id]:
                    del filtered_runs[run_id]["runparameters"]
                if "analysis" in filtered_runs[run_id]:
                    del filtered_runs[run_id]["analysis"]
        return filtered_runs

    def _add_run(self, run_id: str, run: Dict[str, Any]):
        self.cleve.runs[run_id] = run

    def _update_run_path(self, run_id: str, path: Union[str, Path]):
        self.cleve.runs[run_id]["path"] = str(path)

    def _update_run_state(self, run_id: str, state: str):
        self.cleve.runs[run_id]["state_history"].insert(0, {
            "state": state,
            "time": time.time(),
        })

    def _add_analysis(self, run_id: str, analysis: Dict[str, Any]):
        self.cleve.runs[run_id]["analysis"].append(analysis)

    def _update_analysis(
            self,
            run_id: str,
            analysis_id: str,
            state: Optional[str] = None,
            summary: Optional[Dict[str, Any]] = None):
        for a in self.cleve.runs[run_id]["analysis"]:
            if a["analysis_id"] == analysis_id:
                if state is not None:
                    a["state"] = state
                if summary is not None:
                    a["summary"] = summary

    def assertTriggerDispatched(self, trigger, payload):
        """
        Assert that a a specific trigger has been dispatched with the given
        payload. This is an overload of the assertTriggerDispatched function in
        BaseSensorTestCase that allows for a subset of keys in the payload to
        be matched. If the payload passed to this function is a valid subset of
        the actual payload, and the values match, then it is considered a
        match and the assertion succeeds.
        """
        for t in self.get_dispatched_triggers():
            if t["trigger"] == trigger:
                subset_payload = {k: t["payload"].get(k) for k in payload.keys()}
                if subset_payload == payload:
                    break
        else:
            raise AssertionError(
                f"trigger '{trigger}' with payload {payload} not dispatched"
            )

    def _write_basic_runcompletionstatus(self,
                                         dir: Path,
                                         tag: str = "RunStatus",
                                         status: str = "RunCompleted"):
        runcompletionstatusfile = dir / "RunCompletionStatus.xml"
        with open(runcompletionstatusfile, "w") as f:
            content = f"""
                <RunCompletionStatus>
                    <{tag}>{status}</{tag}>
                </RunCompletionStatus>
            """
            f.write(content)

    def _write_basic_runparams(self, dir: Path, platform: str, run_id: str):
        runparamsfile = dir / "RunParameters.xml"
        with open(runparamsfile, "w") as f:
            p = PLATFORMS[platform]
            runparams = f"""
                <RunParameters>
                    <{p["serial_tag"]}>{p["serial_pattern"]}1234</{p["serial_tag"]}>
                    <RunId>{run_id}</RunId>
                </RunParameters>
            """
            f.write(runparams)

    def _write_basic_runinfo(self, dir: Path, platform: str, run_id: str):
        runinfofile = dir / "RunInfo.xml"
        with open(runinfofile, "w") as f:
            p = PLATFORMS[platform]
            runparams = f"""
                <RunInfo Version="6">
                    <Run Id="{run_id}" Number="123">
                        <Instrument>{p["serial_pattern"]}1234</Instrument>
                    </Run>
                </RunInfo>
            """
            f.write(runparams)

    def test_new_directory(self):
        run_dirs = [
            Path(self.watch_directories[0].name) / "run1",
            Path(self.watch_directories[1].name) / "run2",
        ]

        run_dirs[0].mkdir()

        # Should trigger an incomplete directory
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.incomplete_directory",
            payload={
                "path": str(run_dirs[0]),
                "state": DirectoryState.INCOMPLETE,
                "message": f"{run_dirs[0]}/RunParameters.xml does not exist",
                "directory_type": DirectoryType.RUN,
            }
        )

        (run_dirs[0] / "RunParameters.xml").touch()
        self.sensor.poll()
        # Empty RunParameters.xml should be treated as an error
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.incomplete_directory",
            payload={
                "path": str(run_dirs[0]),
                "state": DirectoryState.ERROR,
                "directory_type": DirectoryType.RUN,
            }
        )

        self._write_basic_runparams(run_dirs[0], "NovaSeq X Plus", "run1")

        # Should trigger an incomplete directory with incomplete state since
        # RunInfo.xml does not yet exist.
        self.sensor.poll()
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.incomplete_directory",
            payload={
                "path": str(run_dirs[0]),
                "state": DirectoryState.INCOMPLETE,
                "message": f"{run_dirs[0]}/RunInfo.xml does not exist",
                "directory_type": DirectoryType.RUN,
            }
        )

        (run_dirs[0] / "RunInfo.xml").touch()
        self.sensor.poll()
        # Empty RunInfo.xml should be treated as an error
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.incomplete_directory",
            payload={
                "path": str(run_dirs[0]),
                "state": DirectoryState.ERROR,
                "message": f"{run_dirs[0]}/RunInfo.xml is empty",
                "directory_type": DirectoryType.RUN,
            }
        )

        self._write_basic_runinfo(run_dirs[0], "NovaSeq X Plus", "run1")

        # Should trigger a new directory with pending state since
        # CopyComplete.txt does not yet exist
        self.sensor.poll()
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_directory",
            payload={
                "run_id": "run1",
                "path": str(run_dirs[0]),
                "state": DirectoryState.PENDING,
                "directory_type": DirectoryType.RUN,
            }
        )

        # Add the run to the database
        self.cleve.add_run("run1", {
            "run_id": "run1",
            "platform": "NovaSeq X Plus",
            "state_history": [{"state": "new", "time": time.localtime()}],
            "path": str(run_dirs[0]),
        })

        (run_dirs[0] / PLATFORMS["NovaSeq X Plus"]["ready_marker"]).touch()

        # Should trigger a state change
        self.sensor.poll()
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.state_change",
            payload={
                "run_id": "run1",
                "path": str(run_dirs[0]),
                "state": DirectoryState.READY,
                "directory_type": DirectoryType.RUN,
                "platform": "NovaSeq X Plus",
                "target_directory": self.target_directory.name,
            }
        )

        self.assertEqual(len(self.get_dispatched_triggers()), 6)

    def test_state_change_of_moved_directory(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run = {
            "run_id": "run1",
            "platform": "NovaSeq X Plus",
            "state_history": [
                {
                    "state": "moved",
                    "time": datetime.datetime.now(),
                },
                {
                    "state": "ready",
                    "time": datetime.datetime.now() - datetime.timedelta(days=1)
                },
            ],
            "path": str(run_directory),
        }

        self.cleve.add_run("run1", run)

        # The directory has been moved, and we don't know where,
        # so no state change should be emitted.
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 0)

    def test_moved_run_directory(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run = {
            "run_id": "run1",
            "platform": "NovaSeq X Plus",
            "state_history": [{"state": "new", "time": time.localtime()}],
            "path": str(run_directory),
        }

        self.cleve.add_run("run1", run)

        # The directory does not exist, so it has been (re)moved
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.state_change",
            payload={
                "run_id": "run1",
                "path": None,
                "state": DirectoryState.MOVED,
                "directory_type": DirectoryType.RUN,
            }
        )

        # Update the run state
        self.cleve.update_run_state("run1", state=DirectoryState.MOVED)

        # No more state changes should be emitted for this run
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)

    def test_moved_run_directory_within_watched_directory(self):
        run_directory = Path(self.watch_directories[0].name) / "run1_moved"
        run_directory.mkdir()
        self._write_basic_runparams(run_directory, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory, "NovaSeq X Plus", "run1")
        (run_directory / "CopyComplete.txt").touch()

        self.cleve.add_run("run1", {
            "run_id": "run1",
            "platform": "NovaSeq X Plus",
            "state_history": [{"state": "ready", "time": time.localtime()}],
            "path": str(Path(self.watch_directories[0].name) / "run1"),
        })

        # The directory does not exist, so it has been (re)moved
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.state_change",
            payload={
                "run_id": "run1",
                "path": str(Path(self.watch_directories[0].name) / "run1_moved"),
                "state": DirectoryState.MOVED,
                "directory_type": DirectoryType.RUN,
            }
        )

        # Update run state and path
        self.cleve.update_run_state("run1", state=DirectoryState.MOVED)
        self.cleve.update_run_path("run1", path=run_directory)

        # The next poll should emit a state change
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 2)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.state_change",
            payload={
                "run_id": "run1",
                "path": str(Path(self.watch_directories[0].name) / "run1_moved"),
                "state": DirectoryState.READY,
                "directory_type": DirectoryType.RUN,
            }
        )

    def test_moved_run_directory_with_state_change(self):
        run_directory = Path(self.watch_directories[0].name) / "run1_moved"
        run_directory.mkdir()
        self._write_basic_runparams(run_directory, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory, "NovaSeq X Plus", "run1")
        (run_directory / "CopyComplete.txt").touch()

        run = {
            "run_id": "run1",
            "platform": "NovaSeq X Plus",
            "state_history": [{"state": "new", "time": time.localtime()}],
            "path": str(Path(self.watch_directories[0].name) / "run1"),
        }

        self.cleve.add_run("run1", run)

        # Moved state should be emitted on first poll
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.state_change",
            payload={
                "run_id": "run1",
                "path": str(Path(self.watch_directories[0].name) / "run1_moved"),
                "state": DirectoryState.MOVED,
                "directory_type": DirectoryType.RUN,
            }
        )

        # Update run
        self.cleve.update_run_state("run1", state=DirectoryState.MOVED)
        self.cleve.update_run_path("run1", run_directory)

        # State change should be emitted on second poll
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 2)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.state_change",
            payload={
                "run_id": "run1",
                "path": str(Path(self.watch_directories[0].name) / "run1_moved"),
                "state": DirectoryState.READY,
                "directory_type": DirectoryType.RUN,
            }
        )

    def test_update_empty_state(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run_directory.mkdir()
        (run_directory / "CopyComplete.txt").touch()
        self._write_basic_runparams(run_directory, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory, "NovaSeq X Plus", "run1")

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_directory",
            payload={
                "run_id": "run1",
                "path": str(run_directory),
                "state": DirectoryState.READY,
                "directory_type": DirectoryType.RUN,
            }
        )

        self.cleve.add_run("run1", {
            "run_id": "run1",
            "platform": "NovaSeq X Plus",
            "state": DirectoryState.READY,
            "path": str(Path(self.watch_directories[0].name) / "run1"),
        })
        self.cleve.runs["run1"]["state_history"] = []

        self.sensor.poll()
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.state_change",
            payload={
                "run_id": "run1",
                "path": str(run_directory),
                "state": DirectoryState.READY,
                "directory_type": DirectoryType.RUN,
            }
        )

    def test_analysis_directory(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run_directory.mkdir()
        (run_directory / "CopyComplete.txt").touch()
        self._write_basic_runparams(run_directory, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory, "NovaSeq X Plus", "run1")

        analysis_directory = run_directory / "Analysis" / "1"
        analysis_directory.mkdir(parents=True)

        not_analysis_directory = run_directory / "Analysis" / "tmp"
        not_analysis_directory.mkdir(parents=True)

        # Should find a new run directory and a (1) new analysis directory
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 2)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_directory",
            payload={
                "run_id": "run1",
                "path": str(run_directory),
                "state": DirectoryState.READY,
                "directory_type": DirectoryType.RUN,
            }
        )
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_directory",
            payload={
                "run_id": "run1",
                "path": str(analysis_directory),
                "state": DirectoryState.PENDING,
                "directory_type": DirectoryType.ANALYSIS,
            }
        )

        # Add the run to the database
        self.cleve.add_run("run1", {
            "run_id": "run1",
            "platform": "NovaSeq X Plus",
            "state_history": [{
                "state": DirectoryState.READY,
                "time": time.localtime(),
            }],
            "path": str(run_directory),
            "analysis": [],
        })

        # Add analysis directory to database
        self.cleve.add_analysis(
            run_id="run1",
            analysis={
                "analysis_id": "1",
                "path": str(analysis_directory),
                "state": DirectoryState.PENDING,
            },
        )

        # Should not find anything to update
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 2)

        (analysis_directory / "CopyComplete.txt").touch()

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 3)
        # Should find a state change of the analysis directory
        self.sensor.poll()
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.state_change",
            payload={
                "run_id": "run1",
                "analysis_id": "1",
                "state": DirectoryState.READY,
                "directory_type": DirectoryType.ANALYSIS,
                "target_directory": self.target_directory.name,
            }
        )

    def test_analysis_directory_at_the_same_time_as_run_ready(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run_directory.mkdir()
        (run_directory / "CopyComplete.txt").touch()
        self._write_basic_runparams(run_directory, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory, "NovaSeq X Plus", "run1")

        analysis_directory = run_directory / "Analysis" / "1"
        analysis_directory.mkdir(parents=True)

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 2)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_directory",
            payload={
                "run_id": "run1",
                "path": str(run_directory),
                "state": DirectoryState.READY,
                "directory_type": DirectoryType.RUN,
            }
        )

        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_directory",
            payload={
                "run_id": "run1",
                "path": str(analysis_directory),
                "state": DirectoryState.PENDING,
                "directory_type": DirectoryType.ANALYSIS,
            }
        )

    def test_analysis_directory_ready_at_the_same_time_as_run_ready(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run_directory.mkdir()
        (run_directory / "CopyComplete.txt").touch()
        self._write_basic_runparams(run_directory, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory, "NovaSeq X Plus", "run1")

        analysis_directory = run_directory / "Analysis" / "1"
        analysis_directory.mkdir(parents=True)
        (analysis_directory / "CopyComplete.txt").touch()

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 2)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_directory",
            payload={
                "run_id": "run1",
                "path": str(run_directory),
                "state": DirectoryState.READY,
                "directory_type": DirectoryType.RUN,
            }
        )

        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_directory",
            payload={
                "run_id": "run1",
                "path": str(analysis_directory),
                "state": DirectoryState.READY,
                "directory_type": DirectoryType.ANALYSIS,
                "target_directory": self.target_directory.name,
            }
        )

    def test_new_samplesheet(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run_directory.mkdir()
        (run_directory / "CopyComplete.txt").touch()
        self._write_basic_runparams(run_directory, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory, "NovaSeq X Plus", "run1")
        original_samplesheet = (run_directory / "SampleSheet.csv")
        new_samplesheet = (run_directory / "SampleSheet_new.csv")

        original_samplesheet.touch()
        new_samplesheet.touch()

        modtime = datetime.datetime(
            2024, 6, 20, 13, 9, 3, 617000,
            tzinfo=datetime.timezone(datetime.timedelta(hours=2)),
        )
        os.utime(
            original_samplesheet,
            (modtime.timestamp(), modtime.timestamp())
        )

        # Same modification time, but different timezone.
        server_modtime = modtime.astimezone(datetime.timezone.utc)

        self.cleve.add_run("run1", {
            "run_id": "run1",
            "platform": "NovaSeq X Plus",
            "state_history": [{
                "state": DirectoryState.READY,
                "time": time.localtime(),
            }],
            "samplesheets": [{
                "path": str(run_directory / "SampleSheet.csv"),
                "modification_time":
                    server_modtime.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }],
            "path": str(run_directory),
            "analysis": [],
        })

        # Assuming that the test is not run in the past,
        # we expect the `new_samplesheet` to replacet the
        # original one.
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_samplesheet",
            payload={
                "run_id": "run1",
                "samplesheet": str(new_samplesheet),
            }
        )

    def test_new_samplesheet_with_none_registered(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run_directory.mkdir()
        (run_directory / "CopyComplete.txt").touch()
        self._write_basic_runparams(run_directory, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory, "NovaSeq X Plus", "run1")
        original_samplesheet = (run_directory / "SampleSheet.csv")

        original_samplesheet.touch()

        self.cleve.add_run("run1", {
            "run_id": "run1",
            "platform": "NovaSeq X Plus",
            "state_history": [{
                "state": DirectoryState.READY,
                "time": time.localtime(),
            }],
            "samplesheets": [],
            "path": str(run_directory),
            "analysis": [],
        })

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_samplesheet",
            payload={
                "run_id": "run1",
                "samplesheet": str(original_samplesheet),
            }
        )

    def test_new_samplesheet_with_different_timezone(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run_directory.mkdir()
        (run_directory / "CopyComplete.txt").touch()
        self._write_basic_runparams(run_directory, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory, "NovaSeq X Plus", "run1")
        original_samplesheet = (run_directory / "SampleSheet.csv")

        original_samplesheet.touch()

        # File modification time is local
        modtime = datetime.datetime.now(
            tz=datetime.timezone(datetime.timedelta(hours=2))
        )
        os.utime(
            original_samplesheet,
            (modtime.timestamp(), modtime.timestamp())
        )

        # Modification time in database is UTC
        self.cleve.add_run("run1", {
            "run_id": "run1",
            "platform": "NovaSeq X Plus",
            "state_history": [{
                "state": DirectoryState.READY,
                "time": time.localtime(),
            }],
            "samplesheets": [{
                "path": str(original_samplesheet),
                "modification_time": modtime.replace(
                    tzinfo=datetime.timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }],
            "path": str(run_directory),
            "analysis": [],
        })

        # No trigger should be emitted
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 0)

    def test_find_samplesheet(self):
        @dataclass
        class TestCase:
            samplesheets: List[Path]
            modtimes: List[datetime.datetime]
            expect: str

        run_directory = Path(self.watch_directories[0].name) / "run1"
        run_directory.mkdir()

        testcases = [
            TestCase(
                samplesheets=[
                    run_directory / "SampleSheet.csv",
                ],
                modtimes=[
                    datetime.datetime(2024, 9, 4, 15, 23),
                ],
                expect=str(run_directory / "SampleSheet.csv"),
            ),
            TestCase(
                samplesheets=[
                    run_directory / "SampleSheet.csv",
                    run_directory / "SampleSheet_final.csv",
                    run_directory / "SampleSheet_old.csv",
                ],
                modtimes=[
                    datetime.datetime(2024, 9, 4, 15, 23),
                    datetime.datetime(2024, 9, 4, 15, 50),
                    datetime.datetime(2024, 9, 4, 15, 0),
                ],
                expect=str(run_directory / "SampleSheet_final.csv"),
            ),
        ]

        for n, case in enumerate(testcases, start=1):
            for s, t in zip(case.samplesheets, case.modtimes):
                s.touch()
                os.utime(s, (t.timestamp(), t.timestamp()))

            self.sensor._find_samplesheet(run_id="run1", path=run_directory)
            self.assertEqual(len(self.get_dispatched_triggers()), n)
            self.assertTriggerDispatched(
                trigger="gmc_norr_seqdata.new_samplesheet",
                payload={
                    "run_id": "run1",
                    "samplesheet": case.expect,
                })

            for s in case.samplesheets:
                s.unlink()

    def test_update_samplesheet(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run_directory.mkdir()
        (run_directory / "CopyComplete.txt").touch()
        self._write_basic_runparams(run_directory, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory, "NovaSeq X Plus", "run1")
        original_samplesheet = (run_directory / "SampleSheet.csv")
        old_samplesheet = (run_directory / "SampleSheet_old.csv")

        original_samplesheet.touch()
        old_samplesheet.touch()

        # File modification time is local, i.e. CEST
        modtime = datetime.datetime(
            2024, 9, 3, 8, 40,
            tzinfo=datetime.timezone(datetime.timedelta(hours=2))
        )
        oldtime = datetime.datetime(
            2024, 9, 3, 8, 18,
            tzinfo=datetime.timezone(datetime.timedelta(hours=2))
        )

        os.utime(
            original_samplesheet,
            (modtime.timestamp(), modtime.timestamp())
        )
        os.utime(
            old_samplesheet,
            (oldtime.timestamp(), oldtime.timestamp())
        )

        # Server modification time is in UTC
        server_modtime = modtime.astimezone(datetime.timezone.utc)

        self.cleve.add_run("run1", {
            "run_id": "run1",
            "platform": "NovaSeq X Plus",
            "state_history": [{
                "state": DirectoryState.READY,
                "time": time.localtime(),
            }],
            "samplesheets": [{
                "path": str(original_samplesheet),
                "modification_time":
                    server_modtime.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }],
            "path": str(run_directory),
            "analysis": [],
        })

        # No trigger should be dispatched since the modification time of the
        # most recent sample sheet on disk is the same as the one in the
        # database, just different time zones.
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 0)

    def test_update_deleted_samplesheet(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run_directory.mkdir()
        (run_directory / "CopyComplete.txt").touch()
        self._write_basic_runparams(run_directory, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory, "NovaSeq X Plus", "run1")
        samplesheet = (run_directory / "SampleSheet.csv")

        # Sample sheet modification time is older than what is
        # registered in the database.
        modtime = datetime.datetime(
            2024, 7, 5, 9, 0,
            tzinfo=datetime.timezone(datetime.timedelta(hours=2)),
        )
        server_modtime = datetime.datetime(
            2024, 9, 1, 10, 0,
            tzinfo=datetime.timezone.utc,
        )
        samplesheet.touch()
        os.utime(
            samplesheet,
            (modtime.timestamp(), modtime.timestamp()),
        )

        # Registered sample sheet does not exist on disk.
        self.cleve.add_run("run1", {
            "run_id": "run1",
            "platform": "NovaSeq X Plus",
            "state_history": [{
                "state": DirectoryState.READY,
                "time": time.localtime(),
            }],
            "samplesheets": [{
                "path": str(run_directory / "SampleSheet_test.csv"),
                "modification_time":
                    server_modtime.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }],
            "path": str(run_directory),
            "analysis": [],
        })

        # The missing sample sheet should be replaced with the one
        # that actually exists.
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_samplesheet",
            payload={
                "run_id": "run1",
                "samplesheet": str(samplesheet),
            },
        )

    def test_new_samplesheet_with_microsecond_difference(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run_directory.mkdir()
        (run_directory / "CopyComplete.txt").touch()
        self._write_basic_runparams(run_directory, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory, "NovaSeq X Plus", "run1")
        samplesheet = (run_directory / "SampleSheet.csv")

        samplesheet.touch()

        original_modtime = datetime.datetime(
            2024, 6, 20, 13, 9, 3, 617123,
            tzinfo=datetime.timezone(datetime.timedelta(hours=2)),
        )
        os.utime(
            samplesheet,
            (original_modtime.timestamp(), original_modtime.timestamp()),
        )

        server_modtime = original_modtime.astimezone(datetime.timezone.utc)

        # The new samplesheet is technically newer than what is in the
        # database, but this could be due to the modification time being
        # saved as milliseconds in the database instead of microseconds.
        # In these cases no trigger should be emitted.

        self.cleve.add_run("run1", {
            "run_id": "run1",
            "platform": "NovaSeq X Plus",
            "state_history": [{
                "state": DirectoryState.READY,
                "time": time.localtime(),
            }],
            "samplesheets": [{
                "path": str(run_directory / "SampleSheet.csv"),
                "modification_time":
                    server_modtime.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }],
            "path": str(run_directory),
            "analysis": [],
        })

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 0)

    def test_duplicated_run(self):
        run_directory1 = Path(self.watch_directories[0].name) / "run1"
        run_directory2 = Path(self.watch_directories[0].name) / "run2"

        run_directory1.mkdir()
        run_directory2.mkdir()
        (run_directory1 / "CopyComplete.txt").touch()
        (run_directory2 / "CopyComplete.txt").touch()
        self._write_basic_runparams(run_directory1, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory1, "NovaSeq X Plus", "run1")
        self._write_basic_runparams(run_directory2, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory2, "NovaSeq X Plus", "run1")

        self.cleve.add_run("run1", {
            "run_id": "run1",
            "platform": "NovaSeq X Plus",
            "state_history": [{
                "state": DirectoryState.READY,
                "time": time.localtime(),
            }],
            "samplesheets": [],
            "path": str(run_directory1),
            "analysis": [],
        })

        # run1 exists in the database with the directory being run_directory1.
        # run_directory2 contains the same run, and should be ignored by the
        # sensor. It should instead emit a trigger sending a notification that
        # there is a run that has been duplicated within the watch directory.
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.duplicate_run",
            payload={
                "run_id": "run1",
                "path": str(run_directory1),
                "duplicate_path": str(run_directory2),
                "email": ["me@mail.com"],
            }
        )

        # Mock a trigger instance in the database
        self.sensor._find_duplicate_run_trigger = Mock(
            return_value="mock_trigger_instance"
        )

        # No new triggers should be emitted since a recent trigger instance
        # already exists.
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)

    def test_run_directory_state(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run_directory.mkdir()
        (run_directory / "CopyComplete.txt").touch()
        self._write_basic_runparams(run_directory, "NovaSeq X Plus", "run1")
        self._write_basic_runinfo(run_directory, "NovaSeq X Plus", "run1")

        # No RunCompletionStatus.xml should yield READY
        self.assertEqual(
            self.sensor.run_directory_state(run_directory),
            DirectoryState.READY,
        )

        self._write_basic_runcompletionstatus(
            run_directory,
            status="RunCompleted"
        )
        # RunCompletionStatus.xml for a successful run
        self.assertEqual(
            self.sensor.run_directory_state(run_directory),
            DirectoryState.READY,
        )

        self._write_basic_runcompletionstatus(
            run_directory,
            status="RunErrored",
        )
        # RunCompletionStatus.xml for a failed run
        self.assertEqual(
            self.sensor.run_directory_state(run_directory),
            DirectoryState.ERROR,
        )

        self._write_basic_runcompletionstatus(
            run_directory,
            tag="CompletionStatus",
            status="CompletedAsPlanned",
        )
        # RunCompletionStatus.xml for a successful NextSeq run
        self.assertEqual(
            self.sensor.run_directory_state(run_directory),
            DirectoryState.READY,
        )

        self._write_basic_runcompletionstatus(
            run_directory,
            tag="CompletionStatus",
            status="ExceptionEndedEarly",
        )
        # RunCompletionStatus.xml for a failed NextSeq run
        self.assertEqual(
            self.sensor.run_directory_state(run_directory),
            DirectoryState.ERROR,
        )
