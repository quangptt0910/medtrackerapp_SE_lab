from unittest.mock import patch, Mock
from django.test import TestCase
from medtrackerapp.services import DrugInfoService


class DrugInfoServiceTest(TestCase):
    def test_get_drug_info_missing_drug_name(self):
        with self.assertRaises(ValueError) as context:
            DrugInfoService.get_drug_info("")
        self.assertIn("drug_name is required", str(context.exception))

    @patch("medtrackerapp.services.requests.get")
    def test_get_drug_info_api_error(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 500  # simulate API error
        mock_get.return_value = mock_resp

        with self.assertRaises(ValueError) as context:
            DrugInfoService.get_drug_info("aspirin")
        self.assertIn("OpenFDA API error", str(context.exception))

    @patch("medtrackerapp.services.requests.get")
    def test_get_drug_info_no_results(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": []}  # empty results
        mock_get.return_value = mock_resp

        with self.assertRaises(ValueError) as context:
            DrugInfoService.get_drug_info("aspirin")
        self.assertIn("No results found", str(context.exception))
