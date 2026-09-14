"""
Unit tests for Norwegian Organization Number validator and Modulo 11 checksum.
"""

import unittest
from signalpost.core.validator import (
    calculate_control_digit,
    clean_orgnr,
    normalize_company_name,
    validate_norwegian_orgnr,
)


class TestOrgnrValidator(unittest.TestCase):

    def test_clean_orgnr(self):
        self.assertEqual(clean_orgnr("923 609 016"), "923609016")
        self.assertEqual(clean_orgnr("NO 923 609 016 MVA"), "923609016")
        self.assertEqual(clean_orgnr("923-609-016"), "923609016")
        self.assertEqual(clean_orgnr(""), "")

    def test_valid_org_numbers(self):
        # Known real Norwegian company organization numbers
        valid_numbers = [
            "923609016",  # Equinor ASA
            "984851006",  # DNB Bank ASA
            "990888213",  # Telenor ASA
            "943753784",  # Kongsberg Gruppen ASA
            "914778271",  # Norsk Hydro ASA
            "976389387",  # Ernst & Young AS
        ]
        for orgnr in valid_numbers:
            is_valid, reason = validate_norwegian_orgnr(orgnr)
            self.assertTrue(is_valid, f"Expected {orgnr} to be valid, got: {reason}")

    def test_invalid_checksum(self):
        # Alter last digit of Equinor (control digit is 6, alter to 7)
        is_valid, reason = validate_norwegian_orgnr("923609017")
        self.assertFalse(is_valid)
        self.assertIn("Checksum failure", reason)

    def test_invalid_lengths_and_formats(self):
        self.assertFalse(validate_norwegian_orgnr("12345678")[0])  # 8 digits
        self.assertFalse(validate_norwegian_orgnr("1234567890")[0])  # 10 digits
        self.assertFalse(validate_norwegian_orgnr("ABCDEFGHI")[0])  # letters
        self.assertFalse(validate_norwegian_orgnr("")[0])  # empty

    def test_calculate_control_digit(self):
        # Equinor first 8 digits: 92360901
        self.assertEqual(calculate_control_digit("92360901"), 6)
        # DNB first 8 digits: 98485100
        self.assertEqual(calculate_control_digit("98485100"), 6)

    def test_normalize_company_name(self):
        self.assertEqual(normalize_company_name("EQUINOR ASA"), "EQUINOR")
        self.assertEqual(normalize_company_name("DNB Bank ASA"), "DNB BANK")
        self.assertEqual(normalize_company_name("Acme AS"), "ACME")


if __name__ == "__main__":
    unittest.main()
