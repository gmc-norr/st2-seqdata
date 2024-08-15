from pathlib import Path
import tempfile
from unittest.mock import Mock, ANY

import cleve_service
from st2tests.base import BaseActionTestCase

from actions.update_analysis import UpdateAnalysisAction


def mock_response(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    return MockResponse({"message": "run added"}, 200)


class UpdateAnalyisTestCase(BaseActionTestCase):
    action_cls = UpdateAnalysisAction

    def setUp(self):
        super(UpdateAnalyisTestCase, self).setUp()

        self.cleve = cleve_service.Cleve(key="secret")
        self.action = self.get_action_instance(config={
            "cleve_service": self.cleve
        })

    def test_update_analysis_wo_summary_file(self):
        cleve_service.requests.patch = Mock(side_effect=mock_response)
        self.action.run(
            run_id="run1",
            analysis_id="1",
            state="ready",
            summary_file=None,
        )

        cleve_service.requests.patch.assert_called_with(
            "http://localhost:8080/api/runs/run1/analysis/1",
            files={
                "state": "ready",
            },
            headers={
                "Authorization": "secret",
            },
        )

    def test_update_analysis_w_summary_file(self):
        cleve_service.requests.patch = Mock(side_effect=mock_response)

        tmpdir = tempfile.mkdtemp()
        summary_file = Path(tmpdir, "detailed_summary.json")
        with open(summary_file, 'w') as f:
            f.write('{"hello": "world"}')

        self.action.run(
            run_id="run1",
            analysis_id="1",
            state="ready",
            summary_file=summary_file,
        )

        cleve_service.requests.patch.assert_called_with(
            "http://localhost:8080/api/runs/run1/analysis/1",
            files={
                "state": "ready",
                "analysis_summary": (
                    "detailed_summary.json",
                    ANY,
                    'application/json',
                ),
            },
            headers={
                "Authorization": "secret",
            },
        )
