"""Map entities to high-level PII groups."""

from __future__ import annotations

from pd_scanner.core.models import GroupFlags


COMMON_PD = {
    "fio",
    "phone",
    "email",
    "birth_date",
    "birth_place",
    "address",
}
STATE_IDS = {"passport_rf", "snils", "inn", "driver_license", "mrz"}
PAYMENT = {"bank_card", "bank_account", "bik", "cvv"}
BIOMETRIC = {"biometric_keyword"}
SPECIAL = {
    "special_health",
    "special_religion",
    "special_politics",
    "special_race_nationality",
}


def entity_group(entity_type: str) -> str:
    """Return the top-level entity group."""
    if entity_type in COMMON_PD:
        return "common_pd"
    if entity_type in STATE_IDS:
        return "state_ids"
    if entity_type in PAYMENT:
        return "payment"
    if entity_type in BIOMETRIC:
        return "biometric"
    if entity_type in SPECIAL:
        return "special"
    return "unknown"


def build_group_flags(entity_types: set[str]) -> GroupFlags:
    """Build group flags for a file from detected entities."""
    return GroupFlags(
        has_common_pd=bool(entity_types & COMMON_PD),
        has_state_ids=bool(entity_types & STATE_IDS),
        has_payment=bool(entity_types & PAYMENT),
        has_biometric=bool(entity_types & BIOMETRIC),
        has_special=bool(entity_types & SPECIAL),
    )

