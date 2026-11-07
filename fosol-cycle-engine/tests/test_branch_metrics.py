"""Tests for branch completion-time metric (v1.md §12.1, §14.4)."""

import json
import unittest
from pathlib import Path

from src.branch_metrics import calculate_completion_time

SRC = Path(__file__).resolve().parents[1] / "src" / "branch_metrics.py"
_MISSING = object()


def _branch(
    first_planting: object = _MISSING,
    third_harvest: object = _MISSING,
    crop_count: int = 3,
    transition_count: int = 2,
) -> dict:
    default_planting = {"earliest": "2026-01-01", "latest": "2026-01-02"}
    default_harvest = {"earliest": "2026-01-03", "latest": "2026-01-04"}
    first_p = default_planting if first_planting is _MISSING else first_planting
    third_h = default_harvest if third_harvest is _MISSING else third_harvest
    crops = [
        {"planting_range": first_p, "harvest_range": default_harvest},
        {"planting_range": default_planting, "harvest_range": default_harvest},
        {"planting_range": default_planting, "harvest_range": third_h},
    ]
    return {
        "crops": crops[:crop_count],
        "transitions": [{} for _ in range(transition_count)],
    }


class CompletionTimeTests(unittest.TestCase):
    def test_known_ranges_use_earliest_and_latest_pairing(self) -> None:
        """Spec §12.1 | Bug it catches: completion endpoints are averaged or mis-paired."""
        result = calculate_completion_time(
            _branch(
                first_planting={
                    "earliest": "2026-01-01",
                    "latest": "2026-01-10",
                },
                third_harvest={
                    "earliest": "2026-04-01",
                    "latest": "2026-04-20",
                },
            )
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["completion_days"], {"min": 90, "max": 100})
        self.assertEqual(result["earliest_completion_date"], "2026-04-01")
        self.assertEqual(result["latest_completion_date"], "2026-04-20")
        self.assertEqual(result["ranking_value_days"], 100)
        self.assertEqual(
            result["basis"], "third_harvest_minus_first_planting"
        )
        self.assertEqual(
            result["first_planting_range"],
            {"earliest": "2026-01-01", "latest": "2026-01-10"},
        )
        self.assertEqual(
            result["third_harvest_range"],
            {"earliest": "2026-04-01", "latest": "2026-04-20"},
        )
        self.assertIn("overlapping", result["range_overlap_note"])

    def test_single_date_ranges_give_single_completion_value(self) -> None:
        """Spec §12.1 | Bug it catches: a single-date range invents a wider completion."""
        result = calculate_completion_time(
            _branch(
                first_planting={
                    "earliest": "2026-01-01",
                    "latest": "2026-01-01",
                },
                third_harvest={
                    "earliest": "2026-02-01",
                    "latest": "2026-02-01",
                },
            )
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["completion_days"], {"min": 31, "max": 31})
        self.assertEqual(result["ranking_value_days"], 31)

    def test_missing_or_invalid_ranges_are_unavailable(self) -> None:
        """Spec §12.1 | Bug it catches: missing/invalid timing becomes a zero or invented range."""
        cases = (
            ("missing_third_harvest", _branch(third_harvest=None), "third_harvest_range"),
            ("missing_first_planting", _branch(first_planting=None), "first_planting_range"),
            (
                "invalid_iso",
                _branch(
                    third_harvest={
                        "earliest": "not-a-date",
                        "latest": "2026-04-20",
                    }
                ),
                "third_harvest_range",
            ),
            (
                "reversed_harvest",
                _branch(
                    third_harvest={
                        "earliest": "2026-04-20",
                        "latest": "2026-04-01",
                    }
                ),
                "third_harvest_range",
            ),
        )
        for name, branch, missing in cases:
            with self.subTest(name=name):
                result = calculate_completion_time(branch)
                self.assertEqual(result["status"], "unavailable")
                self.assertIsNone(result["completion_days"])
                self.assertIsNone(result["ranking_value_days"])
                self.assertIn(missing, result["missing_evidence"])

    def test_malformed_branch_shape_is_unavailable_without_crash(self) -> None:
        """Spec §12.1 | Bug it catches: malformed branches crash or look complete."""
        cases = (
            None,
            {},
            _branch(crop_count=2),
            _branch(transition_count=1),
        )
        for branch in cases:
            with self.subTest(branch=branch):
                result = calculate_completion_time(branch)
                self.assertEqual(result["status"], "unavailable")
                self.assertIsNone(result["completion_days"])
                self.assertEqual(result["reason"], "INVALID_BRANCH_SHAPE")

    def test_max_below_min_is_unavailable_not_swapped(self) -> None:
        """Spec §12.1 | Bug it catches: reversed completion endpoints are silently swapped."""
        result = calculate_completion_time(
            _branch(
                first_planting={
                    "earliest": "2026-01-01",
                    "latest": "2026-01-10",
                },
                third_harvest={
                    "earliest": "2026-01-20",
                    "latest": "2026-01-25",
                },
            )
        )
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["completion_days"])
        self.assertIsNone(result["ranking_value_days"])
        self.assertEqual(result["reason"], "COMPLETION_RANGE_INVALID")
        self.assertIn("completion_range", result["missing_evidence"])

    def test_result_is_json_serializable(self) -> None:
        """Spec §14.4 | Bug it catches: dates or non-finite values leak into JSON."""
        result = calculate_completion_time(_branch())
        encoded = json.dumps(result, allow_nan=False)
        self.assertNotIn("NaN", encoded)
        self.assertIsInstance(json.loads(encoded)["completion_days"]["min"], int)

    def test_module_has_no_crop_id_branches(self) -> None:
        """Spec §14.4 | Bug it catches: a crop-specific branch is added to completion logic."""
        source = SRC.read_text(encoding="utf-8")
        self.assertNotIn("crop_id", source)


if __name__ == "__main__":
    unittest.main()
