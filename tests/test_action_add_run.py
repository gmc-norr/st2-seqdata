from unittest.mock import Mock

import cleve_service
from st2tests.base import BaseActionTestCase

from actions.add_run import AddRunAction


def mock_post(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    return MockResponse({"message": "run added"}, 200)


class AddRunTestCase(BaseActionTestCase):
    action_cls = AddRunAction

    def setUp(self):
        super(AddRunTestCase, self).setUp()

        self.cleve = cleve_service.Cleve(key="secret")
        self.action = self.get_action_instance(config={
            "cleve_service": self.cleve
        })

    def test_add_run(self):
        cleve_service.requests.post = Mock(side_effect=mock_post)
        self.action.run(path="/path/to/run", state="ready")

        cleve_service.requests.post.assert_called_with(
            "http://localhost:8080/api/runs",
            json={
                "path": "/path/to/run",
                "state": "ready",
            },
            headers={
                "Authorization": "secret",
            },
        )
