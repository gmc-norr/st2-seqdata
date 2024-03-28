from pathlib import Path
from st2tests.base import BaseSensorTestCase
import tempfile
import time

from illumina_directory_sensor import IlluminaDirectorySensor, DirectoryState, DirectoryType, PLATFORMS
from cleve_service import CleveMock

class IlluminaDirectorySensorTestCase(BaseSensorTestCase):
    sensor_cls = IlluminaDirectorySensor

    def setUp(self):
        super(IlluminaDirectorySensorTestCase, self).setUp()

        self.watch_directories = [
            tempfile.TemporaryDirectory(),
            tempfile.TemporaryDirectory(),
        ]
        self.cleve = CleveMock()
        self.sensor = self.get_sensor_instance(config={
            "illumina_directories": [Path(d.name) for d in self.watch_directories],
            "cleve_service": self.cleve,
        })

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
                "run_id": None,
                "path": str(run_dirs[0]),
                "state": DirectoryState.INCOMPLETE,
                "type": DirectoryType.RUN,
            }
        )

        (run_dirs[0] / "RunParameters.xml").touch()
        # Should trigger an incomplete directory
        self.sensor.poll()
        # Empty RunParameters.xml should be treated as an error
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.incomplete_directory",
            payload={
                "run_id": None,
                "path": str(run_dirs[0]),
                "state": DirectoryState.ERROR,
                "type": DirectoryType.RUN,
            }
        )

        self._write_basic_runparams(run_dirs[0], "NovaSeq", "run1")

        # Should trigger a new directory with pending state since
        # CopyComplete.txt does not yet exist
        self.sensor.poll()
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_directory",
            payload={
                "run_id": "run1",
                "path": str(run_dirs[0]),
                "state": DirectoryState.PENDING,
                "type": DirectoryType.RUN,
            }
        )

        # Add the run to the database
        self.cleve.add_run({
            "run_id": "run1",
            "platform": "NovaSeq",
            "state_history": [{"state": "new", "time": time.localtime()}],
            "path": str(run_dirs[0]),
        })

        (run_dirs[0] / PLATFORMS["NovaSeq"]["ready_marker"]).touch()

        # Should trigger a state change
        self.sensor.poll()
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.state_change",
            payload={
                "run_id": "run1",
                "path": str(run_dirs[0]),
                "state": DirectoryState.READY,
                "type": DirectoryType.RUN,
            }
        )

        self.assertEqual(len(self.get_dispatched_triggers()), 4)

    def test_moved_run_directory(self):
        self.cleve.add_run({
            "run_id": "run1",
            "platform": "NovaSeq",
            "state_history": [{"state": "new", "time": time.localtime()}],
            "path": str(Path(self.watch_directories[0].name) / "run1"),
        })

        # The directory does not exist, so it has been (re)moved
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.state_change",
            payload={
                "run_id": "run1",
                "path": str(Path(self.watch_directories[0].name) / "run1"),
                "state": DirectoryState.MOVED,
                "type": DirectoryType.RUN,
            }
        )

    def test_moved_run_directory_within_watched_directory(self):
        run_directory = Path(self.watch_directories[0].name) / "run1_moved"
        run_directory.mkdir()
        self._write_basic_runparams(run_directory, "NovaSeq", "run1")
        (run_directory / "CopyComplete.txt").touch()

        self.cleve.add_run({
            "run_id": "run1",
            "platform": "NovaSeq",
            "state_history": [{"state": "ready", "time": time.localtime()}],
            "path": str(Path(self.watch_directories[0].name) / "run1"),
        })

        # The directory does not exist, so it has been (re)moved
        self.sensor.poll()
        # Ensure only a single state change trigger is emitted
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.state_change",
            payload={
                "run_id": "run1",
                "path": str(Path(self.watch_directories[0].name) / "run1_moved"),
                "state": DirectoryState.MOVED,
                "type": DirectoryType.RUN,
            }
        )

    def test_moved_run_directory_with_state_change(self):
        run_directory = Path(self.watch_directories[0].name) / "run1_moved"
        run_directory.mkdir()
        self._write_basic_runparams(run_directory, "NovaSeq", "run1")
        (run_directory / "CopyComplete.txt").touch()

        self.cleve.add_run({
            "run_id": "run1",
            "platform": "NovaSeq",
            "state_history": [{"state": "new", "time": time.localtime()}],
            "path": str(Path(self.watch_directories[0].name) / "run1"),
        })

        # Should emit two triggers since it has been moved, and at the same
        # time the state has changed.
        self.sensor.poll()
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.state_change",
            payload={
                "run_id": "run1",
                "path": str(Path(self.watch_directories[0].name) / "run1_moved"),
                "state": DirectoryState.MOVED,
                "type": DirectoryType.RUN,
            }
        )
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.state_change",
            payload={
                "run_id": "run1",
                "path": str(Path(self.watch_directories[0].name) / "run1_moved"),
                "state": DirectoryState.READY,
                "type": DirectoryType.RUN,
            }
        )

    def test_analysis_directory(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run_directory.mkdir()
        (run_directory / "CopyComplete.txt").touch()
        self._write_basic_runparams(run_directory, "NovaSeq", "run1")

        analysis_directory = run_directory / "Analysis" / "1"
        analysis_directory.mkdir(parents=True)

        # Should find a new run directory and a new analysis directory
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 2)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_directory",
            payload={
                "run_id": "run1",
                "path": str(run_directory),
                "state": DirectoryState.READY,
                "type": DirectoryType.RUN,
            }
        )
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_directory",
            payload={
                "run_id": "run1",
                "path": str(analysis_directory),
                "state": DirectoryState.PENDING,
                "type": DirectoryType.ANALYSIS,
            }
        )

        # Add the run to the database
        self.cleve.add_run({
            "run_id": "run1",
            "platform": "NovaSeq",
            "state_history": [{
                "state": DirectoryState.READY,
                "time": time.localtime(),
            }],
            "path": str(run_directory),
            "analysis": [],
        })

        # Add analysis directory to database
        self.cleve.update_run(
            run_id="run1",
            analysis={
                "path": str(analysis_directory),
                "state": DirectoryState.PENDING,
            },
        )

        (analysis_directory / "CopyComplete.txt").touch()

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 3)
        # Should find a state change of the analysis directory
        self.sensor.poll()
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.state_change",
            payload={
                "run_id": "run1",
                "path": str(analysis_directory),
                "state": DirectoryState.READY,
                "type": DirectoryType.ANALYSIS,
            }
        )

    def test_analysis_directory_at_the_same_time_as_run_ready(self):
        run_directory = Path(self.watch_directories[0].name) / "run1"
        run_directory.mkdir()
        (run_directory / "CopyComplete.txt").touch()
        self._write_basic_runparams(run_directory, "NovaSeq", "run1")

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
                "type": DirectoryType.RUN,
            }
        )

        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_directory",
            payload={
                "run_id": "run1",
                "path": str(analysis_directory),
                "state": DirectoryState.PENDING,
                "type": DirectoryType.ANALYSIS,
            }
        )
