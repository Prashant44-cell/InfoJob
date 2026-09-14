"""
Validation and normalization for Norwegian Organization Numbers (organisasjonsnummer).
Implements the official Modulo 11 checksum algorithm defined by Brønnøysundregistrene.
"""

import re
from typing import Optional, Tuple

WEIGHTS = [3, 2, 7, 6, 5, 4, 3, 2]


def clean_orgnr(raw_input: str) -> str:
    """
    Cleans raw input string by stripping whitespace, punctuation,
    and common prefixes like 'NO' or 'MVA'.
    Example: 'NO 923 609 016 MVA' -> '923609016'
    """
    if not raw_input:
        return ""
    # Extract digits only
    digits = re.sub(r"\D", "", str(raw_input))
    return digits


def calculate_control_digit(first_8_digits: str) -> Optional[int]:
    """
    Calculates the 9th digit (control digit) using Modulo 11 weights.
    Returns integer 0-9, or None if remainder is 1 (illegal number).
    """
    if len(first_8_digits) != 8 or not first_8_digits.isdigit():
        return None

    weighted_sum = sum(int(digit) * weight for digit, weight in zip(first_8_digits, WEIGHTS))
    remainder = weighted_sum % 11

    if remainder == 0:
        return 0
    elif remainder == 1:
        # A remainder of 1 cannot yield a single-digit control number (11-1 = 10)
        return None
    else:
        return 11 - remainder


def validate_norwegian_orgnr(raw_orgnr: str) -> Tuple[bool, str]:
    """
    Validates a Norwegian organization number.
    Returns: (is_valid: bool, reason: str)
    """
    cleaned = clean_orgnr(raw_orgnr)

    if not cleaned:
        return False, "Organization number cannot be empty."

    if len(cleaned) != 9:
        return False, f"Invalid length ({len(cleaned)} digits). Norwegian org numbers must be exactly 9 digits."

    if not cleaned.isdigit():
        return False, "Organization number must contain only numeric digits."

    first_8 = cleaned[:8]
    expected_control = calculate_control_digit(first_8)

    if expected_control is None:
        return False, "Invalid organization number: Modulo 11 remainder produces illegal control digit 10."

    actual_control = int(cleaned[8])
    if actual_control != expected_control:
        return False, f"Checksum failure: control digit is {actual_control}, expected {expected_control} (MOD 11)."

    return True, "Valid Norwegian organization number."


def normalize_company_name(name: str) -> str:
    """
    Normalizes company name for fuzzy matching and comparisons.
    Strips legal form suffixes (AS, ASA, ENK, DA, ANS, NUF) and punctuation.
    """
    if not name:
        return ""
    cleaned = name.upper().strip()
    # Normalize common business suffixes
    suffixes = [
        r"\bALLMENNAKSJESELSKAP\b",
        r"\bAKSJESELSKAP\b",
        r"\bENKELTPERSONFORETAK\b",
        r"\bANSVARLIG SELSKAP\b",
        r"\bSELSKAP MED DELT ANSVAR\b",
        r"\bASA\b",
        r"\bA\.S\.A\b",
        r"\bAS\b",
        r"\bA\.S\b",
        r"\bENK\b",
        r"\bDA\b",
        r"\bANS\b",
        r"\bNUF\b",
    ]
    for suffix in suffixes:
        cleaned = re.sub(suffix, "", cleaned)
    # Remove extra whitespace and special characters
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned
