"""Validator unit tests."""

from pd_scanner.detectors.validators import luhn_check, validate_inn, validate_snils


def test_luhn_check_valid_card() -> None:
    assert luhn_check("4111 1111 1111 1111")


def test_luhn_check_invalid_card() -> None:
    assert not luhn_check("4111 1111 1111 1112")


def test_validate_snils_valid() -> None:
    assert validate_snils("112-233-445 95")


def test_validate_snils_invalid() -> None:
    assert not validate_snils("112-233-445 96")


def test_validate_inn_legal_entity_valid() -> None:
    assert validate_inn("7707083893")


def test_validate_inn_individual_valid() -> None:
    assert validate_inn("500100732259")
