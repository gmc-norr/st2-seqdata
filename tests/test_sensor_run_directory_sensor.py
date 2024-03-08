import getpass
import json
from pathlib import Path
from st2tests.base import BaseSensorTestCase
import tempfile

from run_directory_sensor import RunDirectorySensor, RunDirectoryState

class RunDirectorySensorTestCase(BaseSensorTestCase):
    sensor_cls = RunDirectorySensor

    def setUp(self):
        super(RunDirectorySensorTestCase, self).setUp()

        self.watch_directories = [
            ("localhost", tempfile.TemporaryDirectory()),
            ("127.0.0.1", tempfile.TemporaryDirectory()),
        ]
        self.sensor = self.get_sensor_instance(config={
            "run_directories": [
                {"path": d[1].name, "host": d[0]} for d in self.watch_directories
            ],
            **self._get_user_credentials(),
        })

    def _get_user_credentials(self):
        ssh_dir = Path.home() / ".ssh"
        keyfile = None

        for f in ssh_dir.iterdir():
            if f.name in ("authorized_keys", "config", "known_hosts") or f.suffix == ".pub":
                continue
            keyfile = f
            break

        return {
            "user": getpass.getuser(),
            "keyfile": keyfile,
        }

    def test_new_directory(self):
        run_dirs = [
            Path(self.watch_directories[0][1].name) / "run1",
            Path(self.watch_directories[1][1].name) / "run2",
        ]

        run_dirs[0].mkdir()

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        datastore_directories = json.loads(
            self.sensor_service.get_value("run_directories")
        )
        assert len(datastore_directories) == 1

        (run_dirs[0] / RunDirectoryState.COPYCOMPLETE).touch()
        run_dirs[1].mkdir()

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 3)
        datastore_directories = json.loads(
            self.sensor_service.get_value("run_directories")
        )
        assert len(datastore_directories) == 2

    def test_new_copycomplete(self):
        self.sensor.poll()

        run_directory = Path(self.watch_directories[0][1].name) / "run1"
        run_directory.mkdir()

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_run_directory",
            payload={
                "run_directory": str(run_directory),
                "host": "localhost"
            }
        )

        copycomplete = run_directory / RunDirectoryState.COPYCOMPLETE
        copycomplete.touch()

        assert copycomplete.exists()

        self.sensor.poll()

        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.copy_complete",
            payload={
                "run_directory": str(run_directory),
                "host": "localhost"
            }
        )
        self.assertEqual(len(self.get_dispatched_triggers()), 2)

        # No more triggers should be emitted for the same directory
        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 2)

    def test_moved_run_directory(self):
        run_directory = Path(self.watch_directories[0][1].name) / "run1"
        run_directory.mkdir()

        self.sensor.poll()
        assert len(self.sensor._run_directories) == 1
        datastore_directories = json.loads(
            self.sensor_service.get_value("run_directories")
        )
        assert len(datastore_directories) == 1
        assert datastore_directories[0]["path"] == str(run_directory)
        assert datastore_directories[0]["host"] == "localhost"
        assert datastore_directories[0]["state"] == RunDirectoryState.UNDEFINED

        self.sensor.poll()
        assert len(self.sensor._run_directories) == 1
        run_directory.rmdir()

        self.sensor.poll()
        assert len(self.sensor._run_directories) == 0
        datastore_directories = json.loads(
            self.sensor_service.get_value("run_directories")
        )
        assert len(datastore_directories) == 0

    def test_rtacomplete(self):
        run_directory = Path(self.watch_directories[0][1].name) / "run1"
        run_directory.mkdir()

        rtacomplete = run_directory / RunDirectoryState.RTACOMPLETE
        rtacomplete.touch()

        payload = {
            "run_directory": str(run_directory),
            "host": "localhost"
        }

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 2)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_run_directory",
            payload=payload,
        )
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.rta_complete",
            payload=payload,
        )
        datastore_directories = json.loads(
            self.sensor_service.get_value("run_directories")
        )
        self.assertEqual(len(datastore_directories), 1)
        self.assertEqual(datastore_directories[0]["path"], str(run_directory))
        self.assertEqual(datastore_directories[0]["host"], "localhost")
        self.assertEqual(datastore_directories[0]["state"], RunDirectoryState.RTACOMPLETE)

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 2)

    def test_analysis_complete(self):
        run_directory = Path(self.watch_directories[0][1].name) / "run1"
        run_directory.mkdir()

        analysiscomplete = run_directory / RunDirectoryState.ANALYSISCOMPLETE
        analysiscomplete.touch()

        payload = {
            "run_directory": str(run_directory),
            "host": "localhost"
        }

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 2)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_run_directory",
            payload=payload,
        )
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.analysis_complete",
            payload=payload,
        )
