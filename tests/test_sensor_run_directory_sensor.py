import json
from pathlib import Path
from st2tests.base import BaseSensorTestCase
import tempfile

from run_directory_sensor import RunDirectorySensor, RunDirectoryState


class RunDirectorySensorTestCase(BaseSensorTestCase):
    sensor_cls = RunDirectorySensor

    def setUp(self):
        super(RunDirectorySensorTestCase, self).setUp()

        self.watch_directory = tempfile.TemporaryDirectory()
        self.sensor = self.get_sensor_instance(config={
            "run_directories": [
                {"path": self.watch_directory.name}
            ]
        })

    def test_new_copycomplete(self):
        self.sensor.poll()

        run_directory = Path(self.watch_directory.name) / "run1"
        run_directory.mkdir()

        self.sensor.poll()
        self.assertEqual(len(self.get_dispatched_triggers()), 1)
        self.assertTriggerDispatched(
            trigger="gmc_norr.new_run_directory",
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
            trigger="gmc_norr.copy_complete",
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
        run_directory = Path(self.watch_directory.name) / "run1"
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
        run_directory = Path(self.watch_directory.name) / "run1"
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
            trigger="gmc_norr.new_run_directory",
            payload=payload,
        )
        self.assertTriggerDispatched(
            trigger="gmc_norr.rta_complete",
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
        run_directory = Path(self.watch_directory.name) / "run1"
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
            trigger="gmc_norr.new_run_directory",
            payload=payload,
        )
        self.assertTriggerDispatched(
            trigger="gmc_norr.analysis_complete",
            payload=payload,
        )
