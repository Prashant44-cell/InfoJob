"""
Unit tests for EntityResolver: ensures each fact belongs to the right company.
"""

import unittest
from signalpost.agent.entity_resolver import EntityResolver
from signalpost.core.models import FactCategory


class TestEntityResolver(unittest.TestCase):

    def setUp(self):
        self.resolver = EntityResolver()

    def test_financial_statement_matching(self):
        target_orgnr = "923609016"
        target_name = "EQUINOR ASA"

        # Correct matching statement
        stmt_valid = {
            "virksomhet": {
                "organisasjonsnummer": "923609016",
                "organisasjonsform": "ASA",
            }
        }
        ok, conf, reason = self.resolver.verify_financial_statement(stmt_valid, target_orgnr, target_name)
        self.assertTrue(ok)
        self.assertEqual(conf, 1.0)

        # Mismatched statement from another company
        stmt_invalid = {
            "virksomhet": {
                "organisasjonsnummer": "984851006",  # DNB Bank orgnr
                "organisasjonsform": "ASA",
            }
        }
        ok, conf, reason = self.resolver.verify_financial_statement(stmt_invalid, target_orgnr, target_name)
        self.assertFalse(ok)
        self.assertIn("Cross-entity mismatch", reason)

    def test_name_similarity_and_aliases(self):
        # Exact match after suffix stripping
        self.assertEqual(self.resolver.calculate_name_similarity("EQUINOR ASA", "Equinor"), 1.0)
        # Historical name vs modern
        self.assertGreater(self.resolver.calculate_name_similarity("STATOIL ASA", "StatoilHydro ASA"), 0.7)
        # Completely different companies
        self.assertLess(self.resolver.calculate_name_similarity("EQUINOR ASA", "DNB BANK ASA"), 0.3)

    def test_build_verified_fact(self):
        fact = self.resolver.build_verified_fact(
            key="ceo",
            label="Chief Executive Officer",
            value="Anders Opedal",
            category=FactCategory.GOVERNANCE,
            source_name="Brønnøysundregistrene (Roller)",
            source_url="https://data.brreg.no/enhetsregisteret/api/enheter/923609016/roller",
            source_date="2020-11-02",
        )
        self.assertEqual(fact.key, "ceo")
        self.assertEqual(fact.value, "Anders Opedal")
        self.assertEqual(fact.source_date, "2020-11-02")
        self.assertTrue(fact.verified)
        self.assertEqual(fact.confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
