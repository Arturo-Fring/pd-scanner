"""Masking unit tests."""

from pd_scanner.detectors.maskers import sanitize_snippet
from pd_scanner.detectors.validators import mask_value


def test_mask_phone() -> None:
    assert mask_value("+7 999 123-45-67", "phone").endswith("67")


def test_mask_email() -> None:
    assert mask_value("ivan.petrov@mail.ru", "email") == "iv***@mail.ru"


def test_mask_card() -> None:
    assert mask_value("4111111111111111", "bank_card") == "**** **** **** 1111"


def test_sanitize_snippet() -> None:
    masked = sanitize_snippet("Контакт ivan.petrov@mail.ru, карта 4111111111111111")
    assert "mail.ru" in masked
    assert "4111111111111111" not in masked
