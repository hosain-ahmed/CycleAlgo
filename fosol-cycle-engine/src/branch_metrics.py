"""Branch completion-time metric (v1.md §12.1, §14.4)."""

from __future__ import annotations

import datetime as dt

_BASIS = "third_harvest_minus_first_planting"


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
