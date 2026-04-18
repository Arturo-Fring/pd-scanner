"""Validation and normalization helpers."""

from __future__ import annotations

import re


def digits_only(value: str) -> str:
    """Return only digits from an input string."""
    return re.sub(r"\D", "", value or "")


def normalize_phone(value: str) -> str | None:
    """Normalize Russian phone numbers to +7XXXXXXXXXX."""
    digits = digits_only(value)
    if len(digits) == 11 and digits[0] in {"7", "8"}:
        digits = f"7{digits[1:]}"
    elif len(digits) == 10:
        digits = f"7{digits}"
    else:
        return None
    if len(digits) != 11:
        return None
    return f"+{digits}"


def luhn_check(value: str) -> bool:
    """Validate a PAN using the Luhn algorithm."""
    digits = digits_only(value)
    if not digits.isdigit() or not 13 <= len(digits) <= 19:
        return False
    total = 0
    reverse_digits = digits[::-1]
    for index, char in enumerate(reverse_digits):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def validate_snils(value: str) -> bool:
    """Validate SNILS checksum."""
    digits = digits_only(value)
    if len(digits) != 11 or digits == "00000000000":
        return False
    number = digits[:9]
    checksum = int(digits[9:])
    total = sum(int(digit) * (9 - index) for index, digit in enumerate(number))
    if total < 100:
        expected = total
    elif total in {100, 101}:
        expected = 0
    else:
        expected = total % 101
        if expected == 100:
            expected = 0
    return checksum == expected


def validate_inn(value: str) -> bool:
    """Validate INN for legal entities or individuals."""
    digits = digits_only(value)
    if len(digits) == 10:
        coefficients = (2, 4, 10, 3, 5, 9, 4, 6, 8)
        checksum = sum(int(d) * c for d, c in zip(digits[:9], coefficients, strict=True))
        return int(digits[9]) == checksum % 11 % 10
    if len(digits) == 12:
        coeff11 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
        coeff12 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
        checksum11 = sum(int(d) * c for d, c in zip(digits[:10], coeff11, strict=True))
        checksum12 = sum(int(d) * c for d, c in zip(digits[:11], coeff12, strict=True))
        return (
            int(digits[10]) == checksum11 % 11 % 10
            and int(digits[11]) == checksum12 % 11 % 10
        )
    return False


def maybe_validate_bik(value: str) -> bool:
    """Basic BIK sanity check."""
    digits = digits_only(value)
    return len(digits) == 9 and digits.isdigit() and digits != "000000000"


def mask_value(value: str, entity_type: str) -> str:
    """Mask a detected value for reports."""
    raw = value.strip()
    digits = digits_only(raw)

    if entity_type == "phone":
        normalized = normalize_phone(raw)
        if not normalized:
            return "***"
        return f"+7*** ***-**-{normalized[-2:]}"

    if entity_type == "email":
        local, _, domain = raw.partition("@")
        if not local or not domain:
            return "***@***"
        visible = local[:2]
        return f"{visible}***@{domain}"

    if entity_type == "bank_card":
        if len(digits) < 4:
            return "****"
        groups = ["****", "****", "****", digits[-4:]]
        return " ".join(groups)

    if entity_type in {"snils", "passport_rf", "inn", "bank_account", "driver_license"}:
        if len(digits) <= 4:
            return "*" * len(digits)
        hidden = "*" * max(0, len(digits) - 4)
        return f"{hidden}{digits[-4:]}"

    if entity_type == "bik":
        return f"***{digits[-3:]}" if len(digits) >= 3 else "***"

    if entity_type == "cvv":
        return "***"

    if len(raw) <= 4:
        return "*" * len(raw)
    return f"{raw[:2]}***{raw[-2:]}"

