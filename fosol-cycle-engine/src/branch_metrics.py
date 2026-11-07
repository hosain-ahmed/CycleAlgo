"""Branch metrics: completion time and diversity (v1.md §12.1, §13, §14.4)."""

from __future__ import annotations

import datetime as dt

_BASIS = "third_harvest_minus_first_planting"
_DIVERSITY_BASIS = "crop_family_count_product_convention"
_DIVERSITY_NOTE = (
    "Family count is a product convention, not a measured soil-health ranking."
)


def calculate_completion_time(branch: dict) -> dict:
    """Return the completion range from third harvest minus first planting.

    The latest-completion convention is ``max = third harvest latest - first
    planting latest``; the returned range is never silently swapped.
    """
    if not isinstance(branch, dict):
        return _unavailable("INVALID_BRANCH_SHAPE", ["branch_shape"])

    crops = branch.get("crops")
    transitions = branch.get("transitions")
    if (
        not isinstance(crops, (list, tuple))
        or len(crops) != 3
        or not isinstance(transitions, (list, tuple))
        or len(transitions) != 2
        or not all(isinstance(crop, dict) for crop in crops)
    ):
        return _unavailable("INVALID_BRANCH_SHAPE", ["branch_shape"])

    first_planting, first_missing = _range(
        crops[0].get("planting_range"), "first_planting_range"
    )
    third_harvest, third_missing = _range(
        crops[2].get("harvest_range"), "third_harvest_range"
    )
    missing = first_missing + third_missing
    result = _unavailable("COMPLETION_EVIDENCE_MISSING", missing)
    if first_planting is not None:
        result["first_planting_range"] = _iso_range(*first_planting)
    if third_harvest is not None:
        result["third_harvest_range"] = _iso_range(*third_harvest)
    if missing:
        return result

    planting_earliest, planting_latest = first_planting
    harvest_earliest, harvest_latest = third_harvest
    completion_min = (harvest_earliest - planting_earliest).days
    completion_max = (harvest_latest - planting_latest).days
    if (
        completion_min < 0
        or completion_max < 0
        or completion_max < completion_min
    ):
        result = _unavailable("COMPLETION_RANGE_INVALID", ["completion_range"])
        result["first_planting_range"] = _iso_range(*first_planting)
        result["third_harvest_range"] = _iso_range(*third_harvest)
        return result

    return {
        "status": "ok",
        "completion_days": {"min": completion_min, "max": completion_max},
        "earliest_completion_date": harvest_earliest.isoformat(),
        "latest_completion_date": harvest_latest.isoformat(),
        "ranking_value_days": completion_max,
        "basis": _BASIS,
        "first_planting_range": _iso_range(*first_planting),
        "third_harvest_range": _iso_range(*third_harvest),
        "range_overlap_note": (
            "Completion is a range; ranking uses the latest completion value, "
            "and overlapping branch ranges are not a definitive timing winner."
        ),
        "reason": None,
        "reasons": [],
        "missing_evidence": [],
    }


def calculate_diversity_metrics(
    branch: dict, profiles: dict | None = None
) -> dict:
    """Return transparent family-count and legume-presence diversity metrics.

    Crop-node values win; ``profiles`` is an optional ``{crop_id: profile}``
    fallback for normalized family and legume fields.
    """
    if not _valid_branch_shape(branch):
        return _diversity_unavailable()
    if profiles is not None and not isinstance(profiles, dict):
        raise TypeError("profiles must be a dict keyed by crop_id or None")

    crops = branch["crops"]
    families: list[str] = []
    seen_families: set[str] = set()
    family_missing = False
    legume_flags: list[bool | None] = []
    missing: list[str] = []
    for crop in crops:
        crop_id = _diversity_text(crop.get("crop_id"))
        profile = profiles.get(crop_id) if profiles and crop_id else None
        if not isinstance(profile, dict):
            profile = None
        family = _diversity_text(crop.get("family"))
        if family is None and profile is not None:
            family = _diversity_text(profile.get("family"))
        if family is None:
            family_missing = True
            missing.append("crop_family")
        else:
            key = family.casefold()
            if key not in seen_families:
                seen_families.add(key)
                families.append(family)
        legume_flag = _legume_flag(crop.get("is_legume_n_fixing"))
        if legume_flag is None and profile is not None:
            legume_flag = _legume_flag(profile.get("is_legume_n_fixing"))
        legume_flags.append(legume_flag)

    if any(flag is None for flag in legume_flags):
        missing.append("is_legume_n_fixing")
        legume_present = None
        legume_crop_ids: list[str] = []
    else:
        legume_present = any(legume_flags)
        legume_crop_ids = [
            crop_id
            for crop, flag in zip(crops, legume_flags)
            if flag and (crop_id := _diversity_text(crop.get("crop_id"))) is not None
        ]

    if family_missing:
        distinct_family_count = None
        family_repeat_count = None
        family_list = None
    else:
        distinct_family_count = len(families)
        family_repeat_count = 3 - distinct_family_count
        family_list = families

    missing = _dedupe(missing)
    status = "unknown" if missing else "ok"
    reason = "DIVERSITY_EVIDENCE_MISSING" if missing else None
    return {
        "status": status,
        "distinct_family_count": distinct_family_count,
        "families": family_list,
        "family_repeat_count": family_repeat_count,
        "legume_present": legume_present,
        "legume_crop_ids": legume_crop_ids,
        "legume_note": _legume_note(legume_present),
        "basis": _DIVERSITY_BASIS,
        "diversity_note": _DIVERSITY_NOTE,
        "reason": reason,
        "reasons": [reason] if reason else [],
        "missing_evidence": missing,
    }


def _valid_branch_shape(branch: object) -> bool:
    if not isinstance(branch, dict):
        return False
    crops = branch.get("crops")
    transitions = branch.get("transitions")
    return (
        isinstance(crops, (list, tuple))
        and len(crops) == 3
        and all(isinstance(crop, dict) for crop in crops)
        and isinstance(transitions, (list, tuple))
        and len(transitions) == 2
        and all(isinstance(transition, dict) for transition in transitions)
    )


def _diversity_unavailable() -> dict:
    return {
        "status": "unavailable",
        "distinct_family_count": None,
        "families": None,
        "family_repeat_count": None,
        "legume_present": None,
        "legume_crop_ids": [],
        "legume_note": None,
        "basis": _DIVERSITY_BASIS,
        "diversity_note": _DIVERSITY_NOTE,
        "reason": "INVALID_BRANCH_SHAPE",
        "reasons": ["INVALID_BRANCH_SHAPE"],
        "missing_evidence": ["branch_shape"],
    }


def _diversity_text(value: object) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _legume_flag(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        upper = value.strip().upper()
        if upper == "TRUE":
            return True
        if upper == "FALSE":
            return False
    return None


def _legume_note(legume_present: bool | None) -> str | None:
    if legume_present is True:
        return (
            "A legume is present in the evaluated crops; this is potential "
            "biological nitrogen fixation under suitable conditions, not a "
            "guaranteed nitrogen credit or fertilizer saving."
        )
    if legume_present is False:
        return "No legume is present in the evaluated crops."
    return (
        "Legume presence is unknown because at least one crop lacks a legume flag."
    )


def _dedupe(values) -> list:
    return list(dict.fromkeys(values))


def _unavailable(code: str, missing: list[str]) -> dict:
    return {
        "status": "unavailable",
        "completion_days": None,
        "earliest_completion_date": None,
        "latest_completion_date": None,
        "ranking_value_days": None,
        "basis": _BASIS,
        "first_planting_range": None,
        "third_harvest_range": None,
        "range_overlap_note": None,
        "reason": code,
        "reasons": [code],
        "missing_evidence": list(missing),
    }


def _range(value: object, field: str) -> tuple[tuple[dt.date, dt.date] | None, list[str]]:
    if not isinstance(value, dict):
        return None, [field]
    earliest = value.get("earliest")
    latest = value.get("latest")
    if earliest is None or latest is None:
        return None, [field]
    try:
        start = _coerce_date(earliest, f"{field}.earliest")
        end = _coerce_date(latest, f"{field}.latest")
    except (TypeError, ValueError):
        return None, [field]
    if start > end:
        return None, [field]
    return (start, end), []


def _coerce_date(value: object, field: str) -> dt.date:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value.strip())
        except ValueError as exc:
            raise ValueError(
                f"{field} must be an ISO date (YYYY-MM-DD): {value!r}"
            ) from exc
    raise TypeError(f"{field} must be an ISO date string or date")


def _iso_range(earliest: dt.date, latest: dt.date) -> dict:
    return {"earliest": earliest.isoformat(), "latest": latest.isoformat()}
