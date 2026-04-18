"""UZ classifier tests."""

from pd_scanner.classifiers.uz_classifier import classify_uz
from pd_scanner.core.models import GroupFlags


def test_uz1_for_special_categories() -> None:
    flags = GroupFlags(has_special=True)
    assert classify_uz(flags, "small") == "UZ-1"


def test_uz2_for_payment() -> None:
    flags = GroupFlags(has_payment=True)
    assert classify_uz(flags, "small") == "UZ-2"


def test_uz3_for_state_ids_small() -> None:
    flags = GroupFlags(has_state_ids=True)
    assert classify_uz(flags, "small") == "UZ-3"


def test_uz4_for_small_common_pd() -> None:
    flags = GroupFlags(has_common_pd=True)
    assert classify_uz(flags, "small") == "UZ-4"


def test_no_pd_classification() -> None:
    flags = GroupFlags()
    assert classify_uz(flags, "none") == "NO_PD"
