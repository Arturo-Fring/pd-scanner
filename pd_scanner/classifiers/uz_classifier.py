"""File protection level classification."""

from __future__ import annotations

from pd_scanner.core.models import GroupFlags


def classify_uz(group_flags: GroupFlags, estimated_volume: str) -> str:
    """Classify file into UZ-1..UZ-4 or NO_PD."""
    if group_flags.has_special or group_flags.has_biometric:
        return "UZ-1"
    if group_flags.has_payment or (group_flags.has_state_ids and estimated_volume == "large"):
        return "UZ-2"
    if group_flags.has_state_ids or (
        group_flags.has_common_pd and estimated_volume in {"medium", "large"}
    ):
        return "UZ-3"
    if group_flags.has_common_pd:
        return "UZ-4"
    return "NO_PD"

