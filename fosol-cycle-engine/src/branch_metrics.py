"""Branch metrics: completion time and diversity (v1.md §12.1, §13, §14.4)."""

from __future__ import annotations

import datetime as dt

_BASIS = "third_harvest_minus_first_planting"
_DIVERSITY_BASIS = "crop_family_count_product_convention"
_DIVERSITY_NOTE = (
    "Family count is a product convention, not a measured soil-health ranking."
)
_PREFERENCE_CONFIG = {
    "fastest_completion": ("completion_days.max", "ascending"),
    "lowest_total_cost": ("production_cost_bdt_per_ha", "unavailable"),
    "least_irrigation_dependence": ("irrigation_dependence", "unavailable"),
    "highest_net_return": ("net_return_bdt_per_ha", "unavailable"),
    "more_crop_diversity": ("distinct_family_count", "descending"),
    "lowest_upfront_cash": ("upfront_cash_bdt_per_ha", "unavailable"),
}
_ECONOMIC_REASON = "Economic estimate unavailable."
_ECONOMIC_MISSING = [
    "production_cost_evidence",
    "farm_gate_price_evidence",
    "validated_typical_yield_or_attainable_basis",
    "cash_flow_schedule",
]


def calculate_completion_time(branch: dict) -> dict:
    """Return the corner-extreme completion range from third harvest minus planting.

    ``min`` is the fastest realization (third harvest earliest minus first
    planting latest); ``max`` is the slowest realization (third harvest latest
    minus first planting earliest). The range is never silently swapped.
    """
    first_planting, third_harvest, error = _completion_ranges(branch)
    if error is not None:
        return error

    planting_earliest, planting_latest = first_planting
    harvest_earliest, harvest_latest = third_harvest
    completion_min = (harvest_earliest - planting_latest).days
    completion_max = (harvest_latest - planting_earliest).days
    if (
        completion_min < 0
        or completion_max < 0
        or completion_min > completion_max
    ):
        result = _unavailable("COMPLETION_RANGE_INVALID", ["completion_range"])
        result["first_planting_range"] = _iso_range(*first_planting)
        result["third_harvest_range"] = _iso_range(*third_harvest)
        return result

    return _completion_result(
        first_planting,
        third_harvest,
        completion_min,
        completion_max,
        (planting_latest, harvest_earliest),
        (planting_earliest, harvest_latest),
        range_basis="corner_extremes",
    )


def enumerate_completion_range(branch: dict) -> dict:
    """Enumerate every first-planting/third-harvest date pair in the ranges."""
    first_planting, third_harvest, error = _completion_ranges(branch)
    if error is not None:
        error["enumeration_used"] = False
        return error

    planting_earliest, planting_latest = first_planting
    harvest_earliest, harvest_latest = third_harvest
    minimum = None
    maximum = None
    min_realization = None
    max_realization = None
    planting = planting_earliest
    while planting <= planting_latest:
        harvest = harvest_earliest
        while harvest <= harvest_latest:
            days = (harvest - planting).days
            if minimum is None or days < minimum:
                minimum = days
                min_realization = (planting, harvest)
            if maximum is None or days > maximum:
                maximum = days
                max_realization = (planting, harvest)
            harvest += dt.timedelta(days=1)
        planting += dt.timedelta(days=1)

    if (
        minimum is None
        or maximum is None
        or minimum < 0
        or maximum < 0
        or minimum > maximum
    ):
        result = _unavailable("COMPLETION_RANGE_INVALID", ["completion_range"])
        result["enumeration_used"] = True
        return result

    result = _completion_result(
        first_planting,
        third_harvest,
        minimum,
        maximum,
        min_realization,
        max_realization,
        range_basis="enumerated_realizations",
    )
    result["enumeration_used"] = True
    return result


def _completion_ranges(
    branch: object,
) -> tuple[
    tuple[dt.date, dt.date] | None,
    tuple[dt.date, dt.date] | None,
    dict | None,
]:
    if not isinstance(branch, dict):
        return None, None, _unavailable("INVALID_BRANCH_SHAPE", ["branch_shape"])
    crops = branch.get("crops")
    transitions = branch.get("transitions")
    if (
        not isinstance(crops, (list, tuple))
        or len(crops) != 3
        or not isinstance(transitions, (list, tuple))
        or len(transitions) != 2
        or not all(isinstance(crop, dict) for crop in crops)
    ):
        return None, None, _unavailable("INVALID_BRANCH_SHAPE", ["branch_shape"])

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
        return None, None, result
    return first_planting, third_harvest, None


def _completion_result(
    first_planting: tuple[dt.date, dt.date],
    third_harvest: tuple[dt.date, dt.date],
    completion_min: int,
    completion_max: int,
    min_realization: tuple[dt.date, dt.date],
    max_realization: tuple[dt.date, dt.date],
    *,
    range_basis: str,
) -> dict:
    return {
        "status": "ok",
        "completion_days": {"min": completion_min, "max": completion_max},
        "earliest_completion_date": third_harvest[0].isoformat(),
        "latest_completion_date": third_harvest[1].isoformat(),
        "ranking_value_days": completion_max,
        "basis": _BASIS,
        "range_basis": range_basis,
        "min_realization": {
            "first_planting": min_realization[0].isoformat(),
            "third_harvest": min_realization[1].isoformat(),
        },
        "max_realization": {
            "first_planting": max_realization[0].isoformat(),
            "third_harvest": max_realization[1].isoformat(),
        },
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


def build_resource_metrics(
    branch: dict, profiles: dict | None = None
) -> dict:
    """Return cash, irrigation, labor, and equipment context separately.

    No combined resource score is produced. Cash, labor, and equipment have no
    sourced evidence; irrigation is qualitative context only and is not summed
    or converted into a dependence score.
    """
    if not _valid_branch_shape(branch):
        return _invalid_resource_metrics()
    if profiles is not None and not isinstance(profiles, dict):
        raise TypeError("profiles must be a dict keyed by crop_id or None")

    per_crop = []
    for crop in branch["crops"]:
        crop_id = _resource_text(crop.get("crop_id"))
        profile = profiles.get(crop_id) if profiles and crop_id else None
        if not isinstance(profile, dict):
            profile = None
        per_crop.append(
            {
                "crop_id": crop_id,
                "irrigation_guidance": _context_text(
                    crop, profile, "irrigation_guidance"
                ),
                "fao_crop_water_need_min_mm": _context_number(
                    crop, profile, "fao_crop_water_need_min_mm"
                ),
                "fao_crop_water_need_max_mm": _context_number(
                    crop, profile, "fao_crop_water_need_max_mm"
                ),
                "local_phase_water_total_mm": _context_number(
                    crop, profile, "local_phase_water_total_mm"
                ),
                "water_ranking_readiness": _context_text(
                    crop, profile, "water_ranking_readiness"
                ),
            }
        )

    return {
        "cash_cost": _cash_unavailable(),
        "irrigation": {
            "status": "context_only",
            "ranking_status": "unranked",
            "per_crop": per_crop,
            "total": None,
            "missing_evidence": ["comparable_irrigation_evidence"],
            "reason": (
                "Irrigation guidance and FAO/phase values are qualitative "
                "context only; they are not comparable across crops or "
                "scenarios, so no total or dependence score is calculated."
            ),
        },
        "labor": _resource_unavailable(
            "labor_evidence",
            "No sourced labor evidence; labor requirements and peak periods "
            "are unavailable.",
        ),
        "equipment": _resource_unavailable(
            "equipment_evidence",
            "No sourced equipment evidence; equipment and special-management "
            "prerequisites are unavailable.",
        ),
    }


def build_economics_metrics(
    branch: dict, profiles: dict | None = None
) -> dict:
    """Return economics metrics as explicitly unavailable, never zero-filled.

    Yield references and price modes are context only; no revenue, cost, net
    return, upfront cash, or price value is estimated without sourced evidence.
    """
    if not _valid_branch_shape(branch):
        return _invalid_economics_metrics()
    if profiles is not None and not isinstance(profiles, dict):
        raise TypeError("profiles must be a dict keyed by crop_id or None")

    yield_context = []
    price_context = []
    for crop in branch["crops"]:
        crop_id = _resource_text(crop.get("crop_id"))
        profile = profiles.get(crop_id) if profiles and crop_id else None
        if not isinstance(profile, dict):
            profile = None
        yield_context.append(
            {
                "crop_id": crop_id,
                "yield_reference_low_t_ha": _context_number(
                    crop, profile, "yield_reference_low_t_ha"
                ),
                "yield_reference_high_t_ha": _context_number(
                    crop, profile, "yield_reference_high_t_ha"
                ),
                "yield_basis": _context_text(crop, profile, "yield_basis"),
                "status": "static_reference_not_used",
            }
        )
        price_context.append(
            {
                "crop_id": crop_id,
                "market_price_mode": _context_text(
                    crop, profile, "market_price_mode"
                ),
                "source_barc_zoning": _context_text(
                    crop, profile, "source_barc_zoning"
                ),
            }
        )

    modes = {
        item["market_price_mode"]
        for item in price_context
        if item["market_price_mode"] is not None
    }
    sources = {
        item["source_barc_zoning"]
        for item in price_context
        if item["source_barc_zoning"] is not None
    }
    mode = next(iter(modes)) if len(modes) == 1 else None
    source = next(iter(sources)) if len(sources) == 1 else None

    return {
        "status": "unavailable",
        "reason": _ECONOMIC_REASON,
        "scenarios": [],
        "gross_revenue_bdt_per_ha": _economics_metric(
            ["validated_typical_yield_or_attainable_basis", "farm_gate_price_evidence"]
        ),
        "production_cost_bdt_per_ha": _economics_metric(
            ["production_cost_evidence"]
        ),
        "net_return_bdt_per_ha": _economics_metric(
            [
                "production_cost_evidence",
                "farm_gate_price_evidence",
                "validated_typical_yield_or_attainable_basis",
            ]
        ),
        "upfront_cash_bdt_per_ha": _economics_metric(
            ["cash_flow_schedule", "production_cost_evidence"]
        ),
        "yield_reference_context": yield_context,
        "price_evidence": {
            "status": "unavailable",
            "market_price_mode": mode,
            "source_barc_zoning": source,
            "price_value": None,
            "unit": "BDT/t",
            "per_crop": price_context,
            "missing_evidence": ["farm_gate_price_evidence"],
            "reason": (
                "No sourced farm-gate price value; market price mode is "
                "dynamic external."
            ),
        },
        "missing_evidence": list(_ECONOMIC_MISSING),
    }


def rank_branches(
    branches: list[dict] | tuple[dict, ...],
    preference: str,
    profiles: dict | None = None,
) -> dict:
    """Rank candidate and conditional branches by one explicit preference metric."""
    if preference not in _PREFERENCE_CONFIG:
        raise ValueError(
            "preference must be one of " + ", ".join(_PREFERENCE_CONFIG)
        )
    if not isinstance(branches, (list, tuple)):
        raise TypeError("branches must be a list or tuple")
    if profiles is not None and not isinstance(profiles, dict):
        raise TypeError("profiles must be a dict keyed by crop_id or None")

    metric, direction = _PREFERENCE_CONFIG[preference]
    group_items = {
        "candidate": {"items": [], "ranked": [], "unranked": []},
        "conditional": {"items": [], "ranked": [], "unranked": []},
    }
    excluded: list = []
    prepared: list[dict] = []
    for branch in branches:
        branch_id = _ranking_branch_id(branch)
        if not isinstance(branch, dict):
            excluded.append(branch_id)
            continue
        status = branch.get("status")
        if status not in group_items:
            excluded.append(branch_id)
            continue
        item = {
            "branch": branch,
            "branch_id": branch_id,
            "status": status,
            "completion": calculate_completion_time(branch),
            "diversity": calculate_diversity_metrics(branch, profiles),
            "resources": build_resource_metrics(branch, profiles),
            "economics": build_economics_metrics(branch, profiles),
        }
        group_items[status]["items"].append(item)
        prepared.append(item)

    if preference == "fastest_completion":
        for item in prepared:
            completion = item["completion"]
            if (
                completion["status"] != "ok"
                or completion["completion_days"] is None
            ):
                _append_unranked(
                    group_items[item["status"]],
                    item,
                    completion.get("reason") or "COMPLETION_EVIDENCE_MISSING",
                    completion.get("missing_evidence", []),
                )
                continue
            reasons, cautions = _ranking_reasons(item)
            reasons = _dedupe(reasons + list(completion.get("reasons", [])))
            group_items[item["status"]]["ranked"].append(
                {
                    **_ranking_base(item),
                    "metric_value": completion["completion_days"]["max"],
                    "completion_days": completion["completion_days"],
                    "earliest_completion_date": completion[
                        "earliest_completion_date"
                    ],
                    "latest_completion_date": completion[
                        "latest_completion_date"
                    ],
                    "reasons": reasons,
                    "cautions": cautions,
                }
            )
        for name in group_items:
            group_items[name]["ranked"].sort(
                key=lambda entry: (
                    entry["metric_value"],
                    entry["branch_id"] or "",
                )
            )
    elif preference == "more_crop_diversity":
        for item in prepared:
            diversity = item["diversity"]
            if diversity["distinct_family_count"] is None:
                _append_unranked(
                    group_items[item["status"]],
                    item,
                    diversity.get("reason") or "DIVERSITY_EVIDENCE_MISSING",
                    diversity.get("missing_evidence", []),
                )
                continue
            reasons, cautions = _ranking_reasons(item)
            reasons = _dedupe(reasons + list(diversity.get("reasons", [])))
            group_items[item["status"]]["ranked"].append(
                {
                    **_ranking_base(item),
                    "metric_value": diversity["distinct_family_count"],
                    "families": diversity["families"],
                    "family_repeat_count": diversity["family_repeat_count"],
                    "legume_present": diversity["legume_present"],
                    "legume_crop_ids": diversity["legume_crop_ids"],
                    "basis": diversity["basis"],
                    "diversity_note": diversity["diversity_note"],
                    "reasons": reasons,
                    "cautions": cautions,
                }
            )
        for name in group_items:
            group_items[name]["ranked"].sort(
                key=lambda entry: (
                    -entry["metric_value"],
                    entry["branch_id"] or "",
                )
            )
    else:
        for item in prepared:
            if preference == "least_irrigation_dependence":
                evidence = item["resources"]["irrigation"]
            else:
                evidence = item["economics"][metric]
            _append_unranked(
                group_items[item["status"]],
                item,
                evidence.get("reason") or "METRIC_EVIDENCE_MISSING",
                evidence.get("missing_evidence", []),
            )

    groups = {}
    for name in ("candidate", "conditional"):
        ranked = group_items[name]["ranked"]
        unranked = group_items[name]["unranked"]
        groups[name] = {
            "count": len(ranked) + len(unranked),
            "ranked": ranked,
            "unranked": unranked,
        }

    ranked_any = any(groups[name]["ranked"] for name in groups)
    no_winner = not ranked_any
    notes: list[str] = []
    for name in ("candidate", "conditional"):
        if groups[name]["count"] == 0:
            notes.append(
                f"{name.capitalize()} group is empty; no {name} branches were ranked."
            )
        elif not groups[name]["ranked"]:
            notes.append(
                f"{name.capitalize()} group has no branch with a comparable metric."
            )
    if no_winner:
        notes.append("No branch has a comparable metric; no winner is forced.")
    if preference == "fastest_completion":
        for name in ("candidate", "conditional"):
            ranked = groups[name]["ranked"]
            if len(ranked) >= 2 and _completion_overlap(ranked[0], ranked[1]):
                notes.append(
                    "Top two completion ranges overlap in the "
                    f"{name} group ({ranked[0]['branch_id']}, "
                    f"{ranked[1]['branch_id']}); the order is not a "
                    "definitive timing winner."
                )
    elif preference == "more_crop_diversity":
        notes.append(
            "Family-count ordering is a product convention, not a "
            "soil-health ranking; legume presence is reported separately."
        )
    else:
        notes.append(
            f"No comparable {metric} evidence; all branches are unranked."
        )

    if preference == "fastest_completion":
        method = (
            "Rank candidate and conditional groups separately by "
            "completion_days.max ascending; ties by branch_id ascending; "
            "no weighted score."
        )
    elif preference == "more_crop_diversity":
        method = (
            "Rank candidate and conditional groups separately by "
            "distinct_family_count descending; ties by branch_id ascending; "
            "family count is a product convention, not a soil-health ranking."
        )
    else:
        method = (
            f"No comparable {metric} evidence; all candidate and conditional "
            "branches are unranked; no winner is forced."
        )

    return {
        "preference": preference,
        "metric": metric,
        "direction": direction,
        "groups": groups,
        "excluded": excluded,
        "method": method,
        "notes": notes,
        "no_winner": no_winner,
    }


def _ranking_branch_id(branch: object):
    if isinstance(branch, dict):
        value = branch.get("branch_id")
        if value is not None:
            return str(value)
    return None


def _ranking_base(item: dict) -> dict:
    return {"branch_id": item["branch_id"], "status": item["status"]}


def _ranking_reasons(item: dict) -> tuple[list, list]:
    branch = item["branch"]
    reasons = list(branch.get("reasons") or [])
    cautions = list(branch.get("cautions") or [])
    return _dedupe(reasons), _dedupe(cautions)


def _append_unranked(group: dict, item: dict, reason: str, missing: list) -> None:
    reasons, cautions = _ranking_reasons(item)
    if reason and reason not in reasons:
        reasons.append(reason)
    group["unranked"].append(
        {
            **_ranking_base(item),
            "metric_value": None,
            "reason": reason,
            "missing_evidence": list(missing),
            "reasons": _dedupe(reasons),
            "cautions": cautions,
        }
    )


def _completion_overlap(left: dict, right: dict) -> bool:
    a = left["completion_days"]
    b = right["completion_days"]
    return a["min"] <= b["max"] and b["min"] <= a["max"]


def _economics_metric(missing: list[str]) -> dict:
    return {
        "status": "unavailable",
        "value_bdt_per_ha": None,
        "unit": "BDT/ha",
        "missing_evidence": missing,
        "reason": _ECONOMIC_REASON,
    }


def _invalid_economics_metrics() -> dict:
    missing = ["branch_shape"] + list(_ECONOMIC_MISSING)
    metric_missing = ["branch_shape"]
    return {
        "status": "unavailable",
        "reason": "INVALID_BRANCH_SHAPE",
        "scenarios": [],
        "gross_revenue_bdt_per_ha": _economics_metric(metric_missing),
        "production_cost_bdt_per_ha": _economics_metric(metric_missing),
        "net_return_bdt_per_ha": _economics_metric(metric_missing),
        "upfront_cash_bdt_per_ha": _economics_metric(metric_missing),
        "yield_reference_context": [],
        "price_evidence": {
            "status": "unavailable",
            "market_price_mode": None,
            "source_barc_zoning": None,
            "price_value": None,
            "unit": "BDT/t",
            "per_crop": [],
            "missing_evidence": ["branch_shape"],
            "reason": "INVALID_BRANCH_SHAPE",
        },
        "missing_evidence": missing,
    }


def _cash_unavailable() -> dict:
    return {
        "status": "unavailable",
        "value_bdt_per_ha": None,
        "unit": "BDT/ha",
        "missing_evidence": ["production_cost_evidence"],
        "reason": (
            "No sourced production-cost evidence; reference yields are not "
            "used to estimate cash cost."
        ),
    }


def _resource_unavailable(evidence: str, reason: str) -> dict:
    return {
        "status": "unavailable",
        "value": None,
        "unit": None,
        "missing_evidence": [evidence],
        "reason": reason,
    }


def _invalid_resource_metrics() -> dict:
    return {
        "cash_cost": {
            **_cash_unavailable(),
            "missing_evidence": ["branch_shape"],
            "reason": "INVALID_BRANCH_SHAPE",
        },
        "irrigation": {
            "status": "unavailable",
            "ranking_status": "unranked",
            "per_crop": [],
            "total": None,
            "missing_evidence": ["branch_shape"],
            "reason": "INVALID_BRANCH_SHAPE",
        },
        "labor": {
            **_resource_unavailable(
                "labor_evidence",
                "No sourced labor evidence.",
            ),
            "missing_evidence": ["branch_shape"],
            "reason": "INVALID_BRANCH_SHAPE",
        },
        "equipment": {
            **_resource_unavailable(
                "equipment_evidence",
                "No sourced equipment evidence.",
            ),
            "missing_evidence": ["branch_shape"],
            "reason": "INVALID_BRANCH_SHAPE",
        },
    }


def _context_text(crop: dict, profile: dict | None, field: str) -> str | None:
    value = _resource_text(crop.get(field))
    if value is None and profile is not None:
        value = _resource_text(profile.get(field))
    return value


def _context_number(crop: dict, profile: dict | None, field: str) -> float | None:
    value = _resource_number(crop.get(field))
    if value is None and profile is not None:
        value = _resource_number(profile.get(field))
    return value


def _resource_text(value: object) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _resource_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if number == number and abs(number) != float("inf") else None


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
        "range_basis": None,
        "min_realization": None,
        "max_realization": None,
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
