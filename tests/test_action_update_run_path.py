from unittest.mock import Mock

import cleve_service
from st2tests.base import BaseActionTestCase

from actions.update_run_path import UpdateRunPathAction


def mock_patch(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    return MockResponse({"message": "path updated"}, 200)


class UpdateRunPathTestCase(BaseActionTestCase):
    action_cls = UpdateRunPathAction

    def setUp(self):
        super(UpdateRunPathTestCase, self).setUp()

        self.cleve = cleve_service.Cleve(key="secret")
        self.action = self.get_action_instance(config={
            "cleve_service": self.cleve
        })

    def test_add_run(self):
        cleve_service.requests.patch = Mock(side_effect=mock_patch)
        self.action.run(run_id="run1", path="/path/to/run1")

        cleve_service.requests.patch.assert_called_with(
            "http://localhost:8080/api/runs/run1/path",
            json={
                "path": "/path/to/run1",
            },
            headers={
                "Authorization": "secret",
            },
        )
