from unittest.mock import patch

from django.test import TestCase
from medtrackerapp.models import Medication, DoseLog
from django.utils import timezone
from datetime import timedelta, date, datetime


class MedicationModelTests(TestCase):
    def setUp(self):
        self.med = Medication.objects.create(
            name="Aspirin", dosage_mg=100, prescribed_per_day=2
        )

    def test_str_returns_name_and_dosage(self):
        med = Medication.objects.create(
            name="Aspirin", dosage_mg=100, prescribed_per_day=2
        )
        self.assertEqual(str(med), "Aspirin (100mg)")

    def test_adherence_rate_all_doses_taken(self):
        med = Medication.objects.create(
            name="Aspirin", dosage_mg=100, prescribed_per_day=2
        )

        now = timezone.now()
        DoseLog.objects.create(medication=med, taken_at=now - timedelta(hours=30))
        DoseLog.objects.create(medication=med, taken_at=now - timedelta(hours=1))

        adherence = med.adherence_rate()
        self.assertEqual(adherence, 100.0)

    def test_adherence_rate_all_doses_missed(self):
        med = Medication.objects.create(
            name="Aspirin", dosage_mg=100, prescribed_per_day=2
        )
        now = timezone.now()
        DoseLog.objects.create(
            medication=med, taken_at=now - timedelta(hours=2), was_taken=False
        )
        DoseLog.objects.create(medication=med, taken_at=now, was_taken=False)
        self.assertEqual(med.adherence_rate(), 0.0)

    def test_adherence_rate_no_logs(self):
        med = Medication.objects.create(
            name="Aspirin", dosage_mg=100, prescribed_per_day=2
        )
        self.assertEqual(med.adherence_rate(), 0.0)

    def test_expected_doses(self):
        med = Medication.objects.create(
            name="Enzym", dosage_mg=100, prescribed_per_day=3
        )
        days = 5
        self.assertEqual(med.expected_doses(days), 5 * 3)

    def test_expected_doses_negative_days(self):
        med = Medication.objects.create(
            name="Aspirin", dosage_mg=100, prescribed_per_day=2
        )
        with self.assertRaises(ValueError):
            med.expected_doses(-5)

    def test_expected_doses_zero_days(self):
        med = Medication.objects.create(
            name="Aspirin", dosage_mg=100, prescribed_per_day=2
        )
        self.assertEqual(med.expected_doses(0), 0)

    def test_invalid_date_medication(self):
        med = Medication.objects.create(
            name="Aspirin", dosage_mg=100, prescribed_per_day=0
        )

        with self.assertRaises(ValueError):
            med.expected_doses(10)

    def test_adherence_rate_period_some_dose_taken(self):
        start = date(2025, 10, 1)
        end = date(2025, 10, 3)
        DoseLog.objects.create(
            medication=self.med, taken_at=datetime(2025, 10, 1, 0, 0)
        )
        DoseLog.objects.create(
            medication=self.med, taken_at=datetime(2025, 10, 1, 20, 10)
        )
        DoseLog.objects.create(
            medication=self.med, taken_at=datetime(2025, 10, 2, 10, 10)
        )
        DoseLog.objects.create(
            medication=self.med, taken_at=datetime(2025, 10, 2, 20, 10)
        )
        DoseLog.objects.create(
            medication=self.med, taken_at=datetime(2025, 10, 3, 23, 59)
        )

        rate = self.med.adherence_rate_over_period(start, end)
        self.assertEqual(rate, round(100 * 5 / 6, 2))

    def test_adherence_rate_over_period_expected_zero(self):
        med = Medication.objects.create(
            name="TestMed", dosage_mg=50, prescribed_per_day=2
        )
        start = date(2025, 10, 1)
        end = date(2025, 10, 7)

        with patch.object(Medication, "expected_doses", return_value=0):
            rate = med.adherence_rate_over_period(start, end)
            self.assertEqual(rate, 0.0)

    def test_adherence_rate_over_period_all_dose_taken_wrong_period(self):
        med = Medication.objects.create(name="X", dosage_mg=100, prescribed_per_day=2)
        start = date(2025, 10, 2)
        end = date(2025, 10, 3)

        DoseLog.objects.create(medication=med, taken_at=datetime(2025, 10, 1, 10, 10))
        DoseLog.objects.create(medication=med, taken_at=datetime(2025, 10, 1, 20, 10))
        DoseLog.objects.create(medication=med, taken_at=datetime(2025, 10, 4, 0, 0))
        DoseLog.objects.create(medication=med, taken_at=datetime(2025, 10, 4, 20, 10))

        rate = self.med.adherence_rate_over_period(start, end)
        self.assertEqual(rate, 0.0)

    def test_adherence_rate_over_period_invalid_date_range(self):
        med = Medication.objects.create(
            name="Aspirin", dosage_mg=100, prescribed_per_day=2
        )
        start = date(2025, 10, 5)
        end = date(2025, 10, 1)
        with self.assertRaises(ValueError):
            med.adherence_rate_over_period(start, end)

    def test_fetch_external_info_success(self):
        from unittest.mock import patch

        med = Medication.objects.create(
            name="Aspirin", dosage_mg=100, prescribed_per_day=2
        )
        with patch("medtrackerapp.services.DrugInfoService.get_drug_info") as mock_get:
            mock_get.return_value = {"generic_name": "aspirin", "brand_name": "Bayer"}
            result = med.fetch_external_info()
            self.assertIn("generic_name", result)
            mock_get.assert_called_once_with("Aspirin")

    def test_fetch_external_info_error(self):
        from unittest.mock import patch

        med = Medication.objects.create(
            name="Aspirin", dosage_mg=100, prescribed_per_day=2
        )
        with patch("medtrackerapp.services.DrugInfoService.get_drug_info") as mock_get:
            mock_get.side_effect = Exception("API Error")
            result = med.fetch_external_info()
            self.assertIn("error", result)
            self.assertEqual(result["error"], "API Error")


class DoseLogModelTests(TestCase):
    def setUp(self):
        self.med = Medication.objects.create(
            name="Ibuprofen", dosage_mg=200, prescribed_per_day=3
        )

    def test_doselog_str_taken(self):
        dose_time = timezone.make_aware(datetime(2025, 10, 1, 10, 30))
        log = DoseLog.objects.create(
            medication=self.med, taken_at=dose_time, was_taken=True
        )
        self.assertIn("Ibuprofen", str(log))
        self.assertIn("Taken", str(log))

    def test_doselog_str_missed(self):
        dose_time = timezone.make_aware(datetime(2025, 10, 1, 10, 30))
        log = DoseLog.objects.create(
            medication=self.med, taken_at=dose_time, was_taken=False
        )
        self.assertIn("Ibuprofen", str(log))
        self.assertIn("Missed", str(log))

    def test_doselog_default_was_taken(self):
        dose_time = timezone.now()
        log = DoseLog.objects.create(medication=self.med, taken_at=dose_time)
        self.assertTrue(log.was_taken)

    def test_doselog_ordering(self):
        time1 = timezone.now() - timedelta(hours=2)
        time2 = timezone.now() - timedelta(hours=1)
        time3 = timezone.now()

        DoseLog.objects.create(medication=self.med, taken_at=time1)
        DoseLog.objects.create(medication=self.med, taken_at=time3)
        DoseLog.objects.create(medication=self.med, taken_at=time2)

        logs = DoseLog.objects.all()
        self.assertEqual(logs[0].taken_at, time3)
        self.assertEqual(logs[1].taken_at, time2)
        self.assertEqual(logs[2].taken_at, time1)

    def test_doselog_cascade_delete(self):
        dose_time = timezone.now()
        DoseLog.objects.create(medication=self.med, taken_at=dose_time)
        DoseLog.objects.create(
            medication=self.med, taken_at=dose_time - timedelta(hours=1)
        )

        log_count_before = DoseLog.objects.filter(medication=self.med).count()
        self.assertEqual(log_count_before, 2)

        med_id = self.med.id
        self.med.delete()

        log_count_after = DoseLog.objects.filter(medication_id=med_id).count()
        self.assertEqual(log_count_after, 0)
