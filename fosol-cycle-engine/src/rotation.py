"""Rotation compatibility for second and third crops (v1.md §11).

The crop CSV carries advisory rotation text but no structured, sourced
crop-to-crop restriction. Same-family repetition is therefore a transparent
diversity caution, never a rejection. A family change is not evidence of
disease control, soil-carbon improvement, or nitrogen balance, and legume
presence is a potential biological-nitrogen-fixation indicator rather than a
guaranteed nitrogen credit.
"""

from __future__ import annotations


def evaluate_rotation(
    profile: dict,
    previous_profile: dict | None,
    path_profiles: list[dict] | tuple[dict, ...] | None,
) -> dict:
    """Compare the current crop family with the previous crop in the path.

    ``path_profiles`` is used only for diversity and legume indicators. No
    machine-readable blocking rule exists in the current data, so ``status`` is
    never ``unsupported`` and ``blocking`` is always false.
    """
    current_family = _profile_text(profile, "family")
    previous_family = (
        _profile_text(previous_profile, "family")
        if isinstance(previous_profile, dict)
        else None
    )
    path = _path_profiles(path_profiles, profile)
    legume_profiles = [
        item
        for item in path
        if _is_true(item.get("is_legume_n_fixing"))
    ]
    legume_ids = [
        crop_id
        for crop_id in (_profile_text(item, "crop_id") for item in legume_profiles)
        if crop_id is not None
    ]

    if current_family is None or previous_family is None:
        status = "unknown"
        code = "ROTATION_FAMILY_EVIDENCE_MISSING"
        reason = (
            "The current or previous crop family is missing; rotation "
            "compatibility is unknown rather than an automatic pass."
        )
        missing = ["crop_family"]
    elif _same_family(current_family, previous_family):
        status = "caution"
        code = "SAME_FAMILY_REPEAT"
        reason = (
            f"Both the previous crop and this crop are in {current_family}. "
            "Same-family repetition is a diversity caution only; it is not "
            "rejected because no structured, sourced restriction exists."
        )
        missing = []
    else:
        status = "pass"
        code = "FAMILY_DIVERSIFIED"
        reason = (
            f"The family changes from {previous_family} to {current_family}. "
            "Family diversification alone does not establish disease control, "
            "soil-carbon improvement, or nitrogen balance."
        )
        missing = []

    return {
        "status": status,
        "code": code,
        "reason": reason,
        "source_ids": ["rotation_family_rule"],
        "family": current_family,
        "previous_family": previous_family,
        "diversity_indicator": True,
        "blocking": False,
        "rule_machine_readable": False,
        "machine_readable_rule_source_ids": [],
        "rotation_family_rule": _advisory_text(profile, "rotation_family_rule"),
        "rotation_note": _advisory_text(profile, "rotation_note"),
        "legume_present_in_path": bool(legume_profiles),
        "legume_crop_ids": legume_ids,
        "legume_note": (
            "A legume is present in the path; this is potential biological "
            "nitrogen fixation under suitable conditions, not a guaranteed "
            "nitrogen credit or fertilizer saving."
            if legume_profiles
            else "No legume is present in the path."
        ),
        "path_length": len(path),
        "path_crop_ids": [
            crop_id
            for crop_id in (_profile_text(item, "crop_id") for item in path)
            if crop_id is not None
        ],
        "missing_evidence": missing,
    }


def _path_profiles(
    path_profiles: list[dict] | tuple[dict, ...] | None,
    profile: dict,
) -> list[dict]:
    if isinstance(path_profiles, dict):
        path = [path_profiles]
    elif isinstance(path_profiles, (list, tuple)):
        path = [item for item in path_profiles if isinstance(item, dict)]
    else:
        path = []

    current_id = _profile_text(profile, "crop_id")
    if current_id is None or not any(
        _profile_text(item, "crop_id") == current_id for item in path
    ):
        path.append(profile)
    return path


def _same_family(left: str, right: str) -> bool:
    return left.strip().casefold() == right.strip().casefold()


def _is_true(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().upper() == "TRUE"
    return False


def _profile_text(profile: dict, field: str) -> str | None:
    value = profile.get(field)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _advisory_text(profile: dict, field: str) -> str | None:
    value = profile.get(field)
    if value is None:
        raw = profile.get("raw")
        if isinstance(raw, dict):
            value = raw.get(field)
    if value is None:
        return None
    text = str(value).strip()
    return text or None
