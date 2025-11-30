from rest_framework.test import APITestCase
from medtrackerapp.models import Medication, DoseLog
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from datetime import timedelta, date, datetime
from unittest.mock import patch


class MedicationViewTests(APITestCase):
    def setUp(self):
        self.med = Medication.objects.create(name="Aspirin", dosage_mg=100, prescribed_per_day=2)

    def test_list_medications_valid_data(self):
        url = reverse("medication-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Aspirin")
        self.assertEqual(response.data[0]["dosage_mg"], 100)

    def test_create_medication_valid(self):
        url = reverse("medication-list")
        data = {"name": "Ibuprofen", "dosage_mg": 200, "prescribed_per_day": 3}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Ibuprofen")

    def test_create_medication_invalid(self):
        url = reverse("medication-list")
        data = {"name": "", "dosage_mg": -10, "prescribed_per_day": 0}  # invalid data
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_medication_valid(self):
        url = reverse("medication-detail", args=[self.med.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Aspirin")

    def test_retrieve_medication_invalid(self):
        url = reverse("medication-detail", args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_medication_valid(self):
        url = reverse("medication-detail", args=[self.med.pk])
        data = {"name": "Aspirin Updated", "dosage_mg": 150, "prescribed_per_day": 2}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Aspirin Updated")

    def test_update_medication_invalid_data(self):
        url = reverse("medication-detail", args=[self.med.pk])
        data = {"name": "", "dosage_mg": -100, "prescribed_per_day": -1}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_medication_invalid_id(self):
        url = reverse("medication-detail", args=[9999])
        data = {"name": "Name", "dosage_mg": 100, "prescribed_per_day": 2}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_medication_valid(self):
        url = reverse("medication-detail", args=[self.med.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_medication_invalid(self):
        url = reverse("medication-detail", args=[9999])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_external_info_success(self):
        url = reverse("medication-get-external-info", args=[self.med.pk])
        response = self.client.get(url)
        # Accept 200 or 502 depending on external API availability, assert response structure
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_502_BAD_GATEWAY))

    def test_get_external_info_invalid_id(self):
        url = reverse("medication-get-external-info", args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DoseLogViewTests(APITestCase):
    def setUp(self):
        self.med = Medication.objects.create(name="Ibuprofen", dosage_mg=200, prescribed_per_day=3)
        self.log = DoseLog.objects.create(medication=self.med, taken_at=timezone.now(), was_taken=True)

    def test_list_dose_logs(self):
        url = reverse("doselog-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(d["id"] == self.log.id for d in response.data))

    def test_create_dose_log_valid(self):
        url = reverse("doselog-list")
        data = {
            "medication": self.med.pk,
            "taken_at": (timezone.now() - timedelta(days=1)).isoformat(),
            "was_taken": True
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_dose_log_invalid(self):
        url = reverse("doselog-list")
        data = {"medication": 9999, "taken_at": "", "was_taken": "invalid"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_dose_log_valid(self):
        url = reverse("doselog-detail", args=[self.log.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_dose_log_invalid(self):
        url = reverse("doselog-detail", args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_dose_log_valid(self):
        url = reverse("doselog-detail", args=[self.log.pk])
        data = {"medication": self.med.pk, "taken_at": timezone.now().isoformat(), "was_taken": False}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["was_taken"])

    def test_update_dose_log_invalid_data(self):
        url = reverse("doselog-detail", args=[self.log.pk])
        data = {"medication": "invalid", "taken_at": "bad date", "was_taken": "no"}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_dose_log_invalid_id(self):
        url = reverse("doselog-detail", args=[9999])
        data = {"medication": self.med.pk, "taken_at": timezone.now().isoformat(), "was_taken": True}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_dose_log_valid(self):
        url = reverse("doselog-detail", args=[self.log.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_dose_log_invalid(self):
        url = reverse("doselog-detail", args=[9999])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_dose_logs_valid_range(self):
        url = reverse("doselog-filter-by-date")
        start_date = (timezone.now() - timedelta(days=2)).date().isoformat()
        end_date = timezone.now().date().isoformat()
        response = self.client.get(f"{url}?start={start_date}&end={end_date}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_dose_logs_missing_params(self):
        url = reverse("doselog-filter-by-date")  # possibly different name
        response = self.client.get(f"{url}?start=&end=")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_dose_logs_invalid_params(self):
        url = reverse("doselog-filter-by-date")
        response = self.client.get(f"{url}?start=bad&end=invalid")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MedicationExternalInfoTest(APITestCase):
    def setUp(self):
        self.med = Medication.objects.create(name="Aspirin", dosage_mg=100, prescribed_per_day=2)

    @patch('medtrackerapp.services.DrugInfoService.get_drug_info')
    def test_external_info_success(self, mock_get_drug_info):
        # Mock successful API response
        mock_get_drug_info.return_value = {
            "generic_name": "aspirin",
            "brand_name": "Bayer",
            "purpose": "Pain relief"
        }

        url = reverse("medication-get-external-info", args=[self.med.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("generic_name", response.data)
        self.assertEqual(response.data["generic_name"], "aspirin")

    @patch('medtrackerapp.services.DrugInfoService.get_drug_info')
    def test_external_info_failure(self, mock_get_drug_info):
        # Mock an exception raised by the API call
        mock_get_drug_info.side_effect = Exception("API failure")

        url = reverse("medication-get-external-info", args=[self.med.pk])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("error", response.data)
        self.assertEqual(response.data["error"], "API failure")
