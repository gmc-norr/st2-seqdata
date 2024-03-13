import getpass
import json
from pathlib import Path
from st2tests.base import BaseSensorTestCase
import subprocess
import tempfile

from illumina_directory_sensor import IlluminaDirectorySensor, DirectoryState, DirectoryType

class IlluminaDirectorySensorTestCase(BaseSensorTestCase):
    sensor_cls = IlluminaDirectorySensor

    def setUp(self):
        super(IlluminaDirectorySensorTestCase, self).setUp()

        self.watch_directories = [
            ("localhost", tempfile.TemporaryDirectory()),
            ("127.0.0.1", tempfile.TemporaryDirectory()),
        ]
        self.sensor = self.get_sensor_instance(config={
            "illumina_directories": [
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
            self.sensor_service.get_value(self.sensor._DATASTORE_KEY)
        )
        assert len(datastore_directories) == 1

        (run_dirs[0] / DirectoryState.COPYCOMPLETE).touch()
        run_dirs[1].mkdir()

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 3)
        datastore_directories = json.loads(
            self.sensor_service.get_value(self.sensor._DATASTORE_KEY)
        )
        assert len(datastore_directories) == 2

    def test_new_copycomplete(self):
        self.sensor.poll()

        run_directory = Path(self.watch_directories[0][1].name) / "run1"
        run_directory.mkdir()

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.new_directory",
            payload={
                "path": str(run_directory),
                "host": "localhost",
                "type": DirectoryType.RUN,
            }
        )

        copycomplete = run_directory / DirectoryState.COPYCOMPLETE
        copycomplete.touch()

        assert copycomplete.exists()

        self.sensor.poll()

        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.copy_complete",
            payload={
                "path": str(run_directory),
                "host": "localhost",
                "type": DirectoryType.RUN,
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
        assert len(self.sensor._directories) == 1
        datastore_directories = json.loads(
            self.sensor_service.get_value(self.sensor._DATASTORE_KEY)
        )
        assert len(datastore_directories) == 1
        assert datastore_directories[0]["path"] == str(run_directory)
        assert datastore_directories[0]["host"] == "localhost"
        assert datastore_directories[0]["state"] == DirectoryState.UNDEFINED

        self.sensor.poll()
        assert len(self.sensor._directories) == 1
        run_directory.rmdir()

        self.sensor.poll()
        assert len(self.sensor._directories) == 0
        datastore_directories = json.loads(
            self.sensor_service.get_value(self.sensor._DATASTORE_KEY)
        )
        assert len(datastore_directories) == 0

    def test_analysis_directory(self):
        run_directory = Path(self.watch_directories[0][1].name) / "run1"
        run_directory.mkdir()
        (run_directory / "CopyComplete.txt").touch()

        analysis_directory = run_directory / "Analysis"
        analysis_directory.mkdir()
        (analysis_directory / "CopyComplete.txt").touch()

        self.sensor.poll()

        self.assertTriggerDispatched(
            trigger="gmc_norr_seqdata.copy_complete",
            payload={
                "path": str(analysis_directory),
                "host": "localhost",
                "type": DirectoryType.ANALYSIS,
            }
        )
        self.assertEqual(len(self.get_dispatched_triggers()), 4)
        self.assertEqual(len(self.sensor._directories), 2)

        datastore_directories = json.loads(
            self.sensor_service.get_value(self.sensor._DATASTORE_KEY)
        )
        self.assertEqual(len(datastore_directories), 2)

        (analysis_directory / "CopyComplete.txt").unlink()
        analysis_directory.rmdir()

        self.sensor.poll()

        self.assertEqual(len(self.get_dispatched_triggers()), 4)
        self.assertEqual(len(self.sensor._directories), 1)

    def test_deep_run_directory(self):
        run_directory = Path(self.watch_directories[0][1].name) / "run1"
        run_directory.mkdir()
        data_directory = run_directory / "Data"
        data_directory.mkdir(700)

        raised_exception = False
        try:
            self.sensor.poll()
        except subprocess.CalledProcessError:
            raised_exception = True

        self.assertFalse(raised_exception, "Exception when polling sensor")
