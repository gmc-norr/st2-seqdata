from unittest import TestCase
from unittest.mock import Mock

from cleve_service import Cleve


class TestCleveService(TestCase):

    def test_cleve_service_init(self):
        cleve = Cleve(key="supersecretapikey")
        self.assertEqual(cleve.key, "supersecretapikey")
        self.assertEqual(cleve.uri, "http://localhost:8080/api")

    def test_cleve_service_get_runs(self):
        """This test has to be kept in sync with the cleve API"""
        cleve = Cleve(key="supersecretapikey")
        cleve._get = Mock(return_value={
            "metadata": {
                "total_count": 2,
                "page": 1,
                "page_size": 2
            },
            "runs": [
                {
                    "run_id": "run1",
                },
                {
                    "run_id": "run2",
                }
            ]
        })
        runs = cleve.get_runs()
        self.assertEqual(len(runs), 2)
