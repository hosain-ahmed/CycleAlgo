"""Contract checker for explore responses (v1.md §14.4).

Usage:
    python scripts/contract_check.py examples/example_response.json
    python scripts/contract_check.py examples/example_error.json --error
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

VALID_STATUS = {
    "ok",
    "partial",
    "no_supported_options",
    "unsupported_district",
    "data_unavailable",
}
VALID_PREFERENCES = {
    "fastest_completion",
    "lowest_total_cost",
    "least_irrigation_dependence",
    "highest_net_return",
    "more_crop_diversity",
}
_ECONOMIC_VALUE_KEYS = (
    "gross_revenue_bdt_per_ha",
    "production_cost_bdt_per_ha",
    "net_return_bdt_per_ha",
    "upfront_cash_bdt_per_ha",
)


def _check_economics(value: object, field: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{field} must be an object")
        return
    if value.get("status") != "unavailable":
        return
    if value.get("scenarios") != []:
        errors.append(f"{field}.scenarios must be empty when unavailable")
    for key in _ECONOMIC_VALUE_KEYS:
        metric = value.get(key)
        if not isinstance(metric, dict):
            errors.append(f"{field}.{key} must be an object")
        elif metric.get("value_bdt_per_ha") is not None:
            errors.append(
                f"{field}.{key}.value_bdt_per_ha must be null when unavailable"
            )
    price = value.get("price_evidence")
    if not isinstance(price, dict):
        errors.append(f"{field}.price_evidence must be an object")
    elif price.get("price_value") is not None:
        errors.append(f"{field}.price_evidence.price_value must be null when unavailable")


def _check_outlook(
    value: object, field: str, catalog: set[str], errors: list[str]
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{field} must be an object")
        return
    if value.get("status") not in {"ok", "partial", "unavailable"}:
        errors.append(f"{field}.status invalid")
    if not isinstance(value.get("label"), str) or not value["label"]:
        errors.append(f"{field}.label must be non-empty")
    for source in value.get("sources", []):
        if isinstance(source, dict) and source.get("source_id") not in catalog:
            errors.append(f"{field}.sources references unknown source_id")
    ranges = value.get("seasonal_ranges")
    if ranges is None:
        return
    if not isinstance(ranges, dict):
        errors.append(f"{field}.seasonal_ranges must be an object")
        return
    if ranges.get("status") not in {"ok", "partial", "unavailable"}:
        errors.append(f"{field}.seasonal_ranges.status invalid")
    if not isinstance(ranges.get("label"), str) or not ranges["label"]:
        errors.append(f"{field}.seasonal_ranges.label must be non-empty")
    coverage = ranges.get("coverage")
    if not isinstance(coverage, dict):
        errors.append(f"{field}.seasonal_ranges.coverage must be an object")
    else:
        for key in ("start_year", "end_year", "seasons_total"):
            if not isinstance(coverage.get(key), int):
                errors.append(f"{field}.seasonal_ranges.coverage.{key} must be int")
    if ranges.get("thresholds_applied") is not False:
        errors.append(f"{field}.seasonal_ranges.thresholds_applied must be false")
    if ranges.get("warnings") != []:
        errors.append(f"{field}.seasonal_ranges.warnings must be empty")
    _source_ids(
        ranges.get("source_ids"),
        f"{field}.seasonal_ranges.source_ids",
        catalog,
        errors,
    )
    for indicator in ranges.get("indicators", []):
        if not isinstance(indicator, dict):
            errors.append(f"{field}.seasonal_ranges.indicators must contain objects")
            continue
        for key in ("min", "median", "max"):
            if not isinstance(indicator.get(key), (int, float)):
                errors.append(
                    f"{field}.seasonal_ranges indicator {key} must be numeric"
                )
        if all(
            isinstance(indicator.get(key), (int, float))
            for key in ("min", "median", "max")
        ) and not (
            indicator["min"] <= indicator["median"] <= indicator["max"]
        ):
            errors.append(
                f"{field}.seasonal_ranges indicator ordering invalid"
            )


def _strict_load(path: Path) -> dict:
    def reject(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")

    text = path.read_text(encoding="utf-8")
    if "NaN" in text or "Infinity" in text:
        raise ValueError("NaN/Infinity is not allowed in the contract")
    payload = json.loads(text, parse_constant=reject)
    if not isinstance(payload, dict):
        raise ValueError("response must be a JSON object")
    # unknown values must never be NaN/Inf; allow_nan=False proves serialization.
    json.dumps(payload, allow_nan=False)
    return payload


def _date(value: object, field: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append(f"{field} must be an ISO date string")
        return
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field} is not YYYY-MM-DD: {value!r}")


def _range(value: object, field: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{field} must be an object")
        return
    _date(value.get("earliest"), f"{field}.earliest", errors)
    _date(value.get("latest"), f"{field}.latest", errors)
    if (
        isinstance(value.get("earliest"), str)
        and isinstance(value.get("latest"), str)
        and value["earliest"] > value["latest"]
    ):
        errors.append(f"{field}.earliest > latest")


def _source_ids(value: object, field: str, catalog: set[str], errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{field} must be a list of source IDs")
        return
    for source_id in value:
        if source_id not in catalog:
            errors.append(f"{field} references unknown source_id {source_id!r}")


def validate_request(payload: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload.get("district_id"), str) or not payload["district_id"]:
        errors.append("district_id must be a non-empty string")
    _date(payload.get("start_date"), "start_date", errors)
    first = payload.get("first_crop_id")
    if first is not None and (not isinstance(first, str) or not first):
        errors.append("first_crop_id must be null or a non-empty string")
    if payload.get("water_access", "unknown") not in {
        "rainfed",
        "irrigation_available",
        "unknown",
    }:
        errors.append("water_access is invalid")
    if payload.get("preference", "fastest_completion") not in VALID_PREFERENCES:
        errors.append("preference is invalid")
    return errors


def validate_response(payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "1":
        errors.append("schema_version must be '1'")
    if "error" in payload:
        error = payload["error"]
        if not isinstance(error, dict):
            errors.append("error must be an object")
        else:
            for key in ("code", "message"):
                if not isinstance(error.get(key), str) or not error[key]:
                    errors.append(f"error.{key} must be a non-empty string")
            if "stack" in error or "traceback" in error:
                errors.append("error must not contain a stack trace")
        return errors

    required = (
        "generated_at",
        "request",
        "status",
        "district",
        "assumptions",
        "data_sources",
        "crop_options",
        "branches",
        "ranking",
        "warnings",
        "branch_summary",
        "environment_context",
        "missing_evidence",
    )
    for key in required:
        if key not in payload:
            errors.append(f"missing top-level key {key}")

    if not isinstance(payload.get("request"), dict):
        errors.append("request must be an object")
    else:
        request = payload["request"]
        for key in ("max_initial_wait_days", "max_waiting_days"):
            if key not in request:
                errors.append(f"request.{key} is required")
            else:
                value = request[key]
                if value is not None and (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < 0
                ):
                    errors.append(
                        f"request.{key} must be a non-negative integer or null"
                    )
    status = payload.get("status")
    if status not in VALID_STATUS:
        errors.append(f"invalid status {status!r}")
    generated = payload.get("generated_at")
    if not isinstance(generated, str) or not generated.endswith("+00:00"):
        errors.append("generated_at must be a UTC ISO timestamp")
    if not isinstance(payload.get("assumptions"), list):
        errors.append("assumptions must be a list")
    if not isinstance(payload.get("warnings"), list):
        errors.append("warnings must be a list")
    if not isinstance(payload.get("missing_evidence"), list):
        errors.append("missing_evidence must be a list")

    sources = payload.get("data_sources")
    source_ids: set[str] = set()
    if not isinstance(sources, list):
        errors.append("data_sources must be a list")
        sources = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict) or not isinstance(source.get("source_id"), str):
            errors.append(f"data_sources[{index}] missing source_id")
            continue
        source_ids.add(source["source_id"])

    crop_options = payload.get("crop_options")
    if not isinstance(crop_options, list):
        errors.append("crop_options must be a list")
        crop_options = []
    for index, option in enumerate(crop_options):
        if not isinstance(option, dict):
            errors.append(f"crop_options[{index}] must be an object")
            continue
        if not isinstance(option.get("crop_id"), str):
            errors.append(f"crop_options[{index}] missing crop_id")
        if option.get("status") not in {"candidate", "conditional", "unsupported"}:
            errors.append(f"crop_options[{index}] invalid status")
        _source_ids(option.get("source_ids"), f"crop_options[{index}].source_ids", source_ids, errors)

    branches = payload.get("branches")
    if not isinstance(branches, list):
        errors.append("branches must be a list")
        branches = []
    branch_ids: set[str] = set()
    status_counts = {"candidate": 0, "conditional": 0}
    for index, branch in enumerate(branches):
        label = f"branches[{index}]"
        if not isinstance(branch, dict):
            errors.append(f"{label} must be an object")
            continue
        branch_id = branch.get("branch_id")
        if not isinstance(branch_id, str) or not branch_id:
            errors.append(f"{label} missing branch_id")
        elif branch_id in branch_ids:
            errors.append(f"duplicate branch_id {branch_id!r}")
        else:
            branch_ids.add(branch_id)
        branch_status = branch.get("status")
        if branch_status not in {"candidate", "conditional"}:
            errors.append(f"{label} invalid status {branch_status!r}")
        else:
            status_counts[branch_status] += 1
        crops = branch.get("crops")
        transitions = branch.get("transitions")
        if not isinstance(crops, list) or len(crops) != 3:
            errors.append(f"{label} must have exactly 3 crops")
            crops = []
        if not isinstance(transitions, list) or len(transitions) != 2:
            errors.append(f"{label} must have exactly 2 transitions")
        for position, crop in enumerate(crops, 1):
            if not isinstance(crop, dict) or crop.get("position") != position:
                errors.append(f"{label}.crops[{position - 1}] position must be {position}")
                continue
            if not isinstance(crop.get("crop_id"), str):
                errors.append(f"{label}.crops[{position - 1}] missing crop_id")
            if "outlook" in crop:
                _check_outlook(
                    crop["outlook"],
                    f"{label}.crops[{position - 1}].outlook",
                    source_ids,
                    errors,
                )
            for key in ("planting_range", "harvest_range"):
                if crop.get(key) is not None:
                    _range(crop[key], f"{label}.crops[{position - 1}].{key}", errors)
            _source_ids(crop.get("source_ids"), f"{label}.crops[{position - 1}].source_ids", source_ids, errors)
        for index_t, transition in enumerate(transitions, 1):
            if not isinstance(transition, dict):
                errors.append(f"{label}.transitions[{index_t - 1}] must be an object")
                continue
            if transition.get("from_position") != index_t:
                errors.append(f"{label}.transitions[{index_t - 1}] from_position must be {index_t}")
            if transition.get("to_position") != index_t + 1:
                errors.append(f"{label}.transitions[{index_t - 1}] to_position must be {index_t + 1}")
            for key in ("preparation_range", "waiting_range", "next_planting_range"):
                if transition.get(key) is not None:
                    _range(transition[key], f"{label}.transitions[{index_t - 1}].{key}", errors)
            _source_ids(transition.get("source_ids"), f"{label}.transitions[{index_t - 1}].source_ids", source_ids, errors)
        _source_ids(branch.get("source_ids"), f"{label}.source_ids", source_ids, errors)
        metrics = branch.get("metrics")
        if not isinstance(metrics, dict):
            errors.append(f"{label}.metrics must be an object")
        else:
            _check_economics(metrics.get("economics"), f"{label}.metrics.economics", errors)
        if "outlook" in branch:
            _check_outlook(
                branch["outlook"], f"{label}.outlook", source_ids, errors
            )

    summary = payload.get("branch_summary")
    if not isinstance(summary, dict):
        errors.append("branch_summary must be an object")
    else:
        initial_null = (payload.get("request") or {}).get("first_crop_id") is None
        for key in ("candidate_count", "conditional_count"):
            if not isinstance(summary.get(key), int) or summary.get(key) < 0:
                errors.append(f"branch_summary.{key} must be a non-negative integer")
            elif not initial_null and summary.get(key) != status_counts[key[:-6]]:
                errors.append(f"branch_summary.{key} != branch status count")
        if initial_null and branches:
            errors.append("branches must be empty when first_crop_id is null")
        if not isinstance(summary.get("no_candidate_branches"), bool):
            errors.append("branch_summary.no_candidate_branches must be boolean")
        if not isinstance(summary.get("message"), str):
            errors.append("branch_summary.message must be a string")

    ranking = payload.get("ranking")
    if not isinstance(ranking, dict):
        errors.append("ranking must be an object")
    else:
        if ranking.get("preference") not in VALID_PREFERENCES:
            errors.append("ranking.preference is invalid")
        groups = ranking.get("groups")
        if not isinstance(groups, dict):
            errors.append("ranking.groups must be an object")
        else:
            for group_name in ("candidate", "conditional"):
                group = groups.get(group_name)
                if not isinstance(group, dict):
                    errors.append(f"ranking.groups.{group_name} must be an object")
                    continue
                for list_name in ("ranked", "unranked"):
                    entries = group.get(list_name)
                    if not isinstance(entries, list):
                        errors.append(f"ranking.groups.{group_name}.{list_name} must be a list")
                        continue
                    for entry in entries:
                        if not isinstance(entry, dict) or entry.get("branch_id") not in branch_ids:
                            errors.append(f"ranking references unknown branch in {group_name}.{list_name}")
                            continue
                        if "initial_wait_days" not in entry:
                            errors.append(
                                f"ranking entry in {group_name}.{list_name} missing initial_wait_days"
                            )
                        else:
                            wait = entry["initial_wait_days"]
                            if wait is not None and (
                                isinstance(wait, bool)
                                or not isinstance(wait, int)
                                or wait < 0
                            ):
                                errors.append(
                                    f"ranking entry in {group_name}.{list_name} has invalid initial_wait_days"
                                )
                if group.get("count") != len(group.get("ranked", [])) + len(group.get("unranked", [])):
                    errors.append(f"ranking.groups.{group_name}.count mismatch")

    context = payload.get("environment_context")
    if not isinstance(context, dict):
        errors.append("environment_context must be an object")
    else:
        if context.get("status") not in {"available", "unavailable"}:
            errors.append("environment_context.status invalid")
        if context.get("status") == "unavailable" and not context.get("warnings"):
            errors.append("unavailable environment_context needs a warning")
        if "context only" not in str(context.get("label", "")).lower():
            errors.append("environment_context label must say context only")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="examples/example_response.json")
    parser.add_argument("--error", action="store_true")
    args = parser.parse_args(argv)
    path = Path(args.path)
    try:
        payload = _strict_load(path)
    except Exception as exc:  # noqa: BLE001 - CLI reports, never hides
        print(f"FAIL {path}: {exc}")
        return 1
    is_request = "schema_version" not in payload and "district_id" in payload
    if is_request and not args.error:
        errors = validate_request(payload)
        kind = "request"
    else:
        errors = validate_response(payload)
        kind = "response"
        if args.error and "error" not in payload:
            errors.append("expected an error response")
    if errors:
        print(f"FAIL {path}")
        for error in errors[:20]:
            print(f"- {error}")
        return 1
    print(f"PASS {path} ({kind})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
