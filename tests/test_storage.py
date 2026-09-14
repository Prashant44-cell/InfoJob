"""
Unit tests for ProfileStorage SQLite persistence and export formats.
"""

import os
import tempfile
import unittest
from signalpost.core.models import CompanyProfile, Fact, FactCategory
from signalpost.db.storage import ProfileStorage


class TestProfileStorage(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_profiles.db")
        self.storage = ProfileStorage(db_path=self.db_path)

    def test_save_and_retrieve_profile(self):
        fact = Fact(
            key="legal_name",
            label="Legal Name",
            value="TEST BEDRIFT AS",
            category=FactCategory.IDENTIFICATION.value,
            source_name="Enhetsregisteret",
            source_url="https://data.brreg.no/enhetsregisteret/api/enheter/999999999",
            source_date="2024-01-01",
            retrieved_at="2024-01-01T00:00:00Z",
            confidence=1.0,
            verified=True,
            validation_notes="Valid test entity",
        )

        profile = CompanyProfile(
            orgnr="999999999",
            name="TEST BEDRIFT AS",
            org_form="AS",
            status="Active",
            freshness_status="CURRENT",
            last_verified_at="2024-01-01T00:00:00Z",
            facts=[fact],
        )

        self.storage.save_profile(profile)
        self.assertEqual(self.storage.count_profiles(), 1)

        retrieved = self.storage.get_profile("999999999")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "TEST BEDRIFT AS")
        self.assertEqual(len(retrieved.facts), 1)
        self.assertEqual(retrieved.facts[0].value, "TEST BEDRIFT AS")

    def test_exports(self):
        # Save sample profile
        fact = Fact(
            key="legal_name",
            label="Legal Name",
            value="TEST AS",
            category=FactCategory.IDENTIFICATION.value,
            source_name="Enhetsregisteret",
            source_url="https://data.brreg.no/test",
            retrieved_at="2024-01-01T00:00:00Z",
            verified=True,
            confidence=1.0,
            validation_notes="Valid",
        )
        p = CompanyProfile(
            orgnr="111111111",
            name="TEST AS",
            org_form="AS",
            status="Active",
            freshness_status="CURRENT",
            last_verified_at="2024-01-01T00:00:00Z",
            facts=[fact],
        )
        self.storage.save_profile(p)

        json_file = os.path.join(self.temp_dir, "export.json")
        jsonl_file = os.path.join(self.temp_dir, "export.jsonl")
        csv_file = os.path.join(self.temp_dir, "export.csv")

        self.assertEqual(self.storage.export_to_json(json_file), 1)
        self.assertEqual(self.storage.export_to_jsonl(jsonl_file), 1)
        self.assertEqual(self.storage.export_to_csv(csv_file), 1)

        self.assertTrue(os.path.exists(json_file))
        self.assertTrue(os.path.exists(jsonl_file))
        self.assertTrue(os.path.exists(csv_file))


if __name__ == "__main__":
    unittest.main()
