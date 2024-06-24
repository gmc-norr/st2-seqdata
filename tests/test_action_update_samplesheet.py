from unittest.mock import Mock

import cleve_service
from st2tests.base import BaseActionTestCase

from actions.update_samplesheet import UpdateSampleSheet


def mock_post(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    return MockResponse({"message": "samplesheet updated"}, 200)


class UpdateSampleSheetTestCase(BaseActionTestCase):
    action_cls = UpdateSampleSheet

    def setUp(self):
        super(UpdateSampleSheetTestCase, self).setUp()

        self.cleve = cleve_service.Cleve(key="secret")
        self.action = self.get_action_instance(config={
            "cleve_service": self.cleve
        })

    def test_update_samplesheet(self):
        cleve_service.requests.post = Mock(side_effect=mock_post)
        self.action.run(run_id="run1", samplesheet="/path/to/samplesheet")

        cleve_service.requests.post.assert_called_with(
            "http://localhost:8080/api/runs/run1/samplesheet",
            json={
                "samplesheet": "/path/to/samplesheet",
            },
            headers={
                "Authorization": "secret",
            },
        )
