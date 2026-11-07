"""Tests for branch completion-time and diversity metrics (v1.md §12.1, §13, §14.4)."""

import datetime as dt
import json
import random
import unittest
from pathlib import Path

from src.branch_expander import expand_branches
from src.branch_metrics import (
    build_economics_metrics,
    build_resource_metrics,
    calculate_completion_time,
    calculate_diversity_metrics,
    enumerate_completion_range,
    rank_branches,
)
from src.crop_profiles import load_crop_profiles

SRC = Path(__file__).resolve().parents[1] / "src" / "branch_metrics.py"
DATA_CSV = (
    Path(__file__).resolve().parents[2]
    / "Data"
    / "fosol_cycle_rajshahi_crop_dataset.csv"
)
_MISSING = object()
_CROP_IDS = (
    "aman_br11",
    "boro_brri_dhan28",
    "lentil_binamasur9",
    "maize_rabi_bari_hybrid13",
    "mung_bari_mung6_kharif1",
    "mustard_binasarisha9",
    "potato_bari_alu41",
    "wheat_bari_gom33",
)


def _diversity_branch(
    families=("Poaceae", "Fabaceae", "Brassicaceae"),
    legume_flags=(False, True, False),
    crop_ids=("crop_a", "crop_b", "crop_c"),
) -> dict:
    return {
        "crops": [
            {
                "crop_id": crop_id,
                "family": family,
                "is_legume_n_fixing": flag,
            }
            for crop_id, family, flag in zip(crop_ids, families, legume_flags)
        ],
        "transitions": [{}, {}],
    }


def _real_branches():
    profiles = load_crop_profiles(DATA_CSV)
    branches = expand_branches(
        profiles, "2026-11-06", max_waiting_days=365
    )["branches"]
    return profiles, branches


def _random_date(rng: random.Random, start: dt.date, end: dt.date) -> dt.date:
    return start + dt.timedelta(days=rng.randint(0, (end - start).days))


def _economics_profiles() -> dict:
    return {
        crop_id: {
            "yield_reference_low_t_ha": 4.0,
            "yield_reference_high_t_ha": 5.0,
            "yield_basis": "synthetic test reference",
            "market_price_mode": "DYNAMIC_EXTERNAL",
            "source_barc_zoning": "https://example.test/barc",
        }
        for crop_id in ("crop_a", "crop_b", "crop_c")
    }


def _resource_branch(
    contexts: tuple[dict, ...] | None = None,
    crop_count: int = 3,
    transition_count: int = 2,
) -> dict:
    crops = []
    for index, suffix in enumerate(("a", "b", "c")):
        crop = {"crop_id": f"crop_{suffix}"}
        if contexts is not None:
            crop.update(contexts[index])
        crops.append(crop)
    return {
        "crops": crops[:crop_count],
        "transitions": [{} for _ in range(transition_count)],
    }


def _ranking_branch(
    branch_id: str,
    status: str = "conditional",
    first_planting: object = _MISSING,
    third_harvest: object = _MISSING,
    families: tuple = ("Poaceae", "Fabaceae", "Brassicaceae"),
    legume_flags: tuple = (False, True, False),
    reasons: list | None = None,
    cautions: list | None = None,
) -> dict:
    first = (
        {"earliest": "2026-01-01", "latest": "2026-01-02"}
        if first_planting is _MISSING
        else first_planting
    )
    third = (
        {"earliest": "2026-04-01", "latest": "2026-04-12"}
        if third_harvest is _MISSING
        else third_harvest
    )
    crops = []
    for index, (family, flag) in enumerate(zip(families, legume_flags)):
        crops.append(
            {
                "crop_id": f"{branch_id}_crop_{index}",
                "family": family,
                "is_legume_n_fixing": flag,
                "planting_range": (
                    first
                    if index == 0
                    else {"earliest": "2026-01-03", "latest": "2026-01-04"}
                ),
                "harvest_range": (
                    third
                    if index == 2
                    else {"earliest": "2026-02-01", "latest": "2026-02-02"}
                ),
            }
        )
    return {
        "branch_id": branch_id,
        "status": status,
        "crops": crops,
        "transitions": [{}, {}],
        "reasons": reasons or [],
        "cautions": cautions or [],
    }


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
        self.assertEqual(result["completion_days"], {"min": 81, "max": 109})
        self.assertEqual(result["earliest_completion_date"], "2026-04-01")
        self.assertEqual(result["latest_completion_date"], "2026-04-20")
        self.assertEqual(result["ranking_value_days"], 109)
        self.assertEqual(
            result["basis"], "third_harvest_minus_first_planting"
        )
        self.assertEqual(result["range_basis"], "corner_extremes")
        self.assertEqual(
            result["min_realization"],
            {"first_planting": "2026-01-10", "third_harvest": "2026-04-01"},
        )
        self.assertEqual(
            result["max_realization"],
            {"first_planting": "2026-01-01", "third_harvest": "2026-04-20"},
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

    def test_previous_max_below_min_case_uses_corner_extremes(self) -> None:
        """Spec §12.1 | Bug it catches: corner extremes are not used for an inverted A range."""
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
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["completion_days"], {"min": 10, "max": 24})
        self.assertEqual(result["range_basis"], "corner_extremes")
        self.assertEqual(
            result["min_realization"],
            {"first_planting": "2026-01-10", "third_harvest": "2026-01-20"},
        )
        self.assertEqual(
            result["max_realization"],
            {"first_planting": "2026-01-01", "third_harvest": "2026-01-25"},
        )

    def test_negative_corner_min_is_unavailable(self) -> None:
        """Spec §12.1 | Bug it catches: a negative fastest completion is returned as valid."""
        result = calculate_completion_time(
            _branch(
                first_planting={
                    "earliest": "2027-01-01",
                    "latest": "2027-12-31",
                },
                third_harvest={
                    "earliest": "2027-06-01",
                    "latest": "2027-07-01",
                },
            )
        )
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["completion_days"])
        self.assertIsNone(result["ranking_value_days"])
        self.assertEqual(result["reason"], "COMPLETION_RANGE_INVALID")

    def test_negative_corner_enumeration_is_unavailable(self) -> None:
        """Spec §12.1 | Bug it catches: enumeration returns a negative range as ok."""
        branch = _branch(
            first_planting={
                "earliest": "2027-01-01",
                "latest": "2027-12-31",
            },
            third_harvest={
                "earliest": "2027-06-01",
                "latest": "2027-07-01",
            },
        )
        result = enumerate_completion_range(branch)
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["completion_days"])
        self.assertIsNone(result["ranking_value_days"])
        self.assertTrue(result["enumeration_used"])
        self.assertEqual(result["reason"], "COMPLETION_RANGE_INVALID")

    def test_reversed_date_range_is_unavailable(self) -> None:
        """Spec §12.1 | Bug it catches: reversed ISO endpoints are silently accepted."""
        result = calculate_completion_time(
            _branch(
                third_harvest={
                    "earliest": "2026-04-20",
                    "latest": "2026-04-01",
                }
            )
        )
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["completion_days"])
        self.assertIn("third_harvest_range", result["missing_evidence"])

    def test_corner_extremes_min_le_max_for_all_real_branches(self) -> None:
        """Spec §12.1 | Bug it catches: a valid branch still gets an inverted completion range."""
        _, branches = _real_branches()
        self.assertEqual(len(branches), 420)
        for branch in branches:
            result = calculate_completion_time(branch)
            self.assertEqual(result["status"], "ok", branch["branch_id"])
            self.assertLessEqual(
                result["completion_days"]["min"],
                result["completion_days"]["max"],
            )
            self.assertEqual(result["range_basis"], "corner_extremes")

    def test_previously_inverted_branches_are_now_valid(self) -> None:
        """Spec §12.1 | Bug it catches: the 57 decision-A inversions remain unranked."""
        _, branches = _real_branches()
        inverted = []
        for branch in branches:
            planting = branch["crops"][0]["planting_range"]
            harvest = branch["crops"][2]["harvest_range"]
            planting_earliest = dt.date.fromisoformat(planting["earliest"])
            planting_latest = dt.date.fromisoformat(planting["latest"])
            harvest_earliest = dt.date.fromisoformat(harvest["earliest"])
            harvest_latest = dt.date.fromisoformat(harvest["latest"])
            if (harvest_latest - planting_latest).days < (
                harvest_earliest - planting_earliest
            ).days:
                inverted.append(branch)
        self.assertEqual(len(inverted), 57)
        for branch in inverted:
            result = calculate_completion_time(branch)
            self.assertEqual(result["status"], "ok")
            self.assertLessEqual(
                result["completion_days"]["min"],
                result["completion_days"]["max"],
            )

        example = next(
            branch
            for branch in branches
            if branch["branch_id"] == "b_82899e8d6941"
        )
        result = calculate_completion_time(example)
        self.assertEqual(result["completion_days"], {"min": 655, "max": 682})

    def test_completion_property_300_random_realizations(self) -> None:
        """Spec §12.1 | Bug it catches: a realizable date pair falls outside the corner range."""
        _, branches = _real_branches()
        rng = random.Random(20261107)
        cache = {}
        fallback_used = False
        for _ in range(300):
            branch = rng.choice(branches)
            planting_range = branch["crops"][0]["planting_range"]
            harvest_range = branch["crops"][2]["harvest_range"]
            planting = _random_date(
                rng,
                dt.date.fromisoformat(planting_range["earliest"]),
                dt.date.fromisoformat(planting_range["latest"]),
            )
            harvest = _random_date(
                rng,
                dt.date.fromisoformat(harvest_range["earliest"]),
                dt.date.fromisoformat(harvest_range["latest"]),
            )
            result = cache.get(branch["branch_id"])
            if result is None:
                result = calculate_completion_time(branch)
                cache[branch["branch_id"]] = result
            days = (harvest - planting).days
            if not (
                result["completion_days"]["min"]
                <= days
                <= result["completion_days"]["max"]
            ):
                fallback_used = True
                enumerated = enumerate_completion_range(branch)
                self.assertTrue(enumerated["enumeration_used"])
                self.assertLessEqual(
                    enumerated["completion_days"]["min"], days
                )
                self.assertGreaterEqual(
                    enumerated["completion_days"]["max"], days
                )
        self.assertFalse(fallback_used)

    def test_enumerate_completion_range_matches_corner_extremes(self) -> None:
        """Spec §12.1 | Bug it catches: the enumeration fallback returns a different range."""
        branch = _branch(
            first_planting={
                "earliest": "2026-01-01",
                "latest": "2026-01-10",
            },
            third_harvest={
                "earliest": "2026-04-01",
                "latest": "2026-04-20",
            },
        )
        corner = calculate_completion_time(branch)
        enumerated = enumerate_completion_range(branch)
        self.assertTrue(enumerated["enumeration_used"])
        self.assertEqual(enumerated["range_basis"], "enumerated_realizations")
        self.assertEqual(
            enumerated["completion_days"], corner["completion_days"]
        )
        self.assertEqual(
            enumerated["min_realization"], corner["min_realization"]
        )
        self.assertEqual(
            enumerated["max_realization"], corner["max_realization"]
        )

    def test_result_is_json_serializable(self) -> None:
        """Spec §14.4 | Bug it catches: dates or non-finite values leak into JSON."""
        result = calculate_completion_time(_branch())
        encoded = json.dumps(result, allow_nan=False)
        self.assertNotIn("NaN", encoded)
        self.assertIsInstance(json.loads(encoded)["completion_days"]["min"], int)

    def test_three_families_counts_all_distinct(self) -> None:
        """Spec §13 | Bug it catches: distinct family count is wrong or a soil-health claim appears."""
        result = calculate_diversity_metrics(_diversity_branch())
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["distinct_family_count"], 3)
        self.assertEqual(
            result["families"], ["Poaceae", "Fabaceae", "Brassicaceae"]
        )
        self.assertEqual(result["family_repeat_count"], 0)
        self.assertEqual(result["legume_present"], True)
        self.assertEqual(result["legume_crop_ids"], ["crop_b"])
        self.assertEqual(
            result["basis"], "crop_family_count_product_convention"
        )
        self.assertIn("not a measured soil-health", result["diversity_note"])
        self.assertIn("not a guaranteed", result["legume_note"])

    def test_two_families_reports_repeat_proxy(self) -> None:
        """Spec §13 | Bug it catches: repeated family values are counted as distinct."""
        result = calculate_diversity_metrics(
            _diversity_branch(families=(" Poaceae ", "poaceae", "Fabaceae"))
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["distinct_family_count"], 2)
        self.assertEqual(result["families"], ["Poaceae", "Fabaceae"])
        self.assertEqual(result["family_repeat_count"], 1)

    def test_legume_presence_true_and_false(self) -> None:
        """Spec §13 | Bug it catches: legume presence is inverted or overclaimed as N credit."""
        with_legume = calculate_diversity_metrics(
            _diversity_branch(legume_flags=(False, True, False))
        )
        without = calculate_diversity_metrics(
            _diversity_branch(legume_flags=(False, False, False))
        )
        self.assertTrue(with_legume["legume_present"])
        self.assertEqual(with_legume["legume_crop_ids"], ["crop_b"])
        self.assertIn("not a guaranteed", with_legume["legume_note"])
        self.assertFalse(without["legume_present"])
        self.assertEqual(without["legume_crop_ids"], [])
        self.assertIn("No legume", without["legume_note"])

    def test_missing_family_or_legume_flag_is_unknown(self) -> None:
        """Spec §13 | Bug it catches: missing family or legume evidence becomes zero/false."""
        missing_family = calculate_diversity_metrics(
            _diversity_branch(families=(None, "Fabaceae", "Poaceae"))
        )
        self.assertEqual(missing_family["status"], "unknown")
        self.assertIsNone(missing_family["distinct_family_count"])
        self.assertIsNone(missing_family["families"])
        self.assertIsNone(missing_family["family_repeat_count"])
        self.assertIn("crop_family", missing_family["missing_evidence"])

        missing_legume = calculate_diversity_metrics(
            _diversity_branch(legume_flags=(False, None, False))
        )
        self.assertEqual(missing_legume["status"], "unknown")
        self.assertEqual(missing_legume["distinct_family_count"], 3)
        self.assertIsNone(missing_legume["legume_present"])
        self.assertEqual(missing_legume["legume_crop_ids"], [])
        self.assertIn("is_legume_n_fixing", missing_legume["missing_evidence"])

    def test_malformed_branch_shape_is_unavailable(self) -> None:
        """Spec §14.4 | Bug it catches: malformed branches crash or return metrics."""
        base = _diversity_branch()
        cases = (
            None,
            {},
            {"crops": base["crops"][:2], "transitions": base["transitions"]},
            {"crops": base["crops"], "transitions": base["transitions"][:1]},
        )
        for branch in cases:
            with self.subTest(branch=branch):
                result = calculate_diversity_metrics(branch)
                self.assertEqual(result["status"], "unavailable")
                self.assertIsNone(result["distinct_family_count"])
                self.assertIsNone(result["families"])
                self.assertIsNone(result["family_repeat_count"])
                self.assertIsNone(result["legume_present"])
                self.assertEqual(result["reason"], "INVALID_BRANCH_SHAPE")

    def test_diversity_result_is_json_serializable(self) -> None:
        """Spec §14.4 | Bug it catches: non-JSON values leak from diversity metrics."""
        result = calculate_diversity_metrics(_diversity_branch())
        encoded = json.dumps(result, allow_nan=False)
        self.assertNotIn("NaN", encoded)
        self.assertEqual(json.loads(encoded)["distinct_family_count"], 3)

    def test_real_branch_uses_profile_legume_fallback(self) -> None:
        """Spec §13 | Bug it catches: real E6 branches lose legume presence without profile lookup."""
        profiles = load_crop_profiles(DATA_CSV)
        expanded = expand_branches(
            profiles, "2026-11-06", max_waiting_days=365
        )
        legume_ids = {"lentil_binamasur9", "mung_bari_mung6_kharif1"}
        branch = next(
            branch
            for branch in expanded["branches"]
            if any(crop["crop_id"] in legume_ids for crop in branch["crops"])
        )
        with_profiles = calculate_diversity_metrics(branch, profiles)
        self.assertEqual(with_profiles["status"], "ok")
        self.assertTrue(with_profiles["legume_present"])
        self.assertTrue(
            set(with_profiles["legume_crop_ids"]) & legume_ids
        )
        without_profiles = calculate_diversity_metrics(branch)
        self.assertEqual(without_profiles["status"], "unknown")
        self.assertIsNone(without_profiles["legume_present"])
        self.assertIn(
            "is_legume_n_fixing", without_profiles["missing_evidence"]
        )

    def test_profile_family_and_legume_fallback_with_node_precedence(self) -> None:
        """Spec §13 | Bug it catches: profile fallback is ignored or overrides crop-node values."""
        profiles = {
            "crop_a": {"family": "Poaceae", "is_legume_n_fixing": False},
            "crop_b": {"family": "Fabaceae", "is_legume_n_fixing": True},
            "crop_c": {"family": "Poaceae", "is_legume_n_fixing": False},
        }
        fallback = calculate_diversity_metrics(
            _diversity_branch(
                families=(None, None, None),
                legume_flags=(None, None, None),
            ),
            profiles,
        )
        self.assertEqual(fallback["status"], "ok")
        self.assertEqual(fallback["distinct_family_count"], 2)
        self.assertEqual(fallback["families"], ["Poaceae", "Fabaceae"])
        self.assertTrue(fallback["legume_present"])
        self.assertEqual(fallback["legume_crop_ids"], ["crop_b"])

        node = _diversity_branch(
            families=("Brassicaceae", "Fabaceae", "Poaceae"),
            legume_flags=(False, False, False),
        )
        precedence = calculate_diversity_metrics(node, profiles)
        self.assertIn("Brassicaceae", precedence["families"])
        self.assertFalse(precedence["legume_present"])

    def test_economics_metrics_are_unavailable_and_scenarios_empty(self) -> None:
        """Spec §12.3/§17.15 | Bug it catches: missing economics becomes zero or estimated."""
        result = build_economics_metrics(_diversity_branch(), _economics_profiles())
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "Economic estimate unavailable.")
        self.assertEqual(result["scenarios"], [])
        for key in (
            "gross_revenue_bdt_per_ha",
            "production_cost_bdt_per_ha",
            "net_return_bdt_per_ha",
            "upfront_cash_bdt_per_ha",
        ):
            with self.subTest(metric=key):
                metric = result[key]
                self.assertEqual(metric["status"], "unavailable")
                self.assertIsNone(metric["value_bdt_per_ha"])
                self.assertEqual(metric["unit"], "BDT/ha")

    def test_yield_reference_context_is_not_used_for_revenue(self) -> None:
        """Spec §12.3 | Bug it catches: static reference yields are converted into revenue."""
        result = build_economics_metrics(_diversity_branch(), _economics_profiles())
        context = result["yield_reference_context"]
        self.assertEqual(len(context), 3)
        for item in context:
            self.assertEqual(item["status"], "static_reference_not_used")
            self.assertEqual(item["yield_reference_low_t_ha"], 4.0)
            self.assertEqual(item["yield_reference_high_t_ha"], 5.0)
            self.assertEqual(item["yield_basis"], "synthetic test reference")
        self.assertIsNone(
            result["gross_revenue_bdt_per_ha"]["value_bdt_per_ha"]
        )

        without_profiles = build_economics_metrics(_diversity_branch())
        self.assertTrue(
            all(
                item["yield_reference_low_t_ha"] is None
                for item in without_profiles["yield_reference_context"]
            )
        )
        self.assertIsNone(
            without_profiles["price_evidence"]["market_price_mode"]
        )

    def test_price_evidence_is_dynamic_external_without_value(self) -> None:
        """Spec §12.3 | Bug it catches: a price value or static price is invented."""
        result = build_economics_metrics(_diversity_branch(), _economics_profiles())
        price = result["price_evidence"]
        self.assertEqual(price["status"], "unavailable")
        self.assertEqual(price["market_price_mode"], "DYNAMIC_EXTERNAL")
        self.assertEqual(price["source_barc_zoning"], "https://example.test/barc")
        self.assertIsNone(price["price_value"])
        self.assertEqual(len(price["per_crop"]), 3)
        self.assertNotIn("price_value", price["per_crop"][0])

    def test_economics_missing_evidence_ids_are_exact(self) -> None:
        """Spec §12.3/§12.4 | Bug it catches: missing economic evidence IDs are omitted."""
        result = build_economics_metrics(_diversity_branch(), _economics_profiles())
        self.assertEqual(
            result["missing_evidence"],
            [
                "production_cost_evidence",
                "farm_gate_price_evidence",
                "validated_typical_yield_or_attainable_basis",
                "cash_flow_schedule",
            ],
        )

    def test_economics_malformed_branch_is_unavailable(self) -> None:
        """Spec §14.4 | Bug it catches: malformed branches crash or return economics."""
        base = _diversity_branch()
        cases = (
            None,
            {},
            {"crops": base["crops"][:2], "transitions": base["transitions"]},
            {"crops": base["crops"], "transitions": base["transitions"][:1]},
        )
        for branch in cases:
            with self.subTest(branch=branch):
                result = build_economics_metrics(branch)
                self.assertEqual(result["status"], "unavailable")
                self.assertEqual(result["reason"], "INVALID_BRANCH_SHAPE")
                self.assertEqual(result["scenarios"], [])
                self.assertEqual(result["yield_reference_context"], [])
                self.assertIsNone(
                    result["gross_revenue_bdt_per_ha"]["value_bdt_per_ha"]
                )

    def test_economics_result_is_json_serializable(self) -> None:
        """Spec §14.4 | Bug it catches: non-JSON values leak from economics metrics."""
        result = build_economics_metrics(_diversity_branch(), _economics_profiles())
        encoded = json.dumps(result, allow_nan=False)
        self.assertNotIn("NaN", encoded)
        self.assertIsNone(
            json.loads(encoded)["net_return_bdt_per_ha"]["value_bdt_per_ha"]
        )

    def test_economics_module_has_no_crop_id_branches(self) -> None:
        """Spec §14.4 | Bug it catches: a crop-specific branch is added to economics."""
        source = SRC.read_text(encoding="utf-8")
        for crop_id in _CROP_IDS:
            self.assertNotIn(crop_id, source)

    def test_module_has_no_crop_id_branches(self) -> None:
        """Spec §14.4 | Bug it catches: a crop-specific branch is added to branch metrics."""
        source = SRC.read_text(encoding="utf-8")
        for crop_id in _CROP_IDS:
            self.assertNotIn(crop_id, source)


class ResourceMetricsTests(unittest.TestCase):
    def test_resources_remain_four_separate_metrics(self) -> None:
        """Spec §12.2 | Bug it catches: unlike resource units collapsed into one score."""
        result = build_resource_metrics(_resource_branch())
        self.assertEqual(
            set(result), {"cash_cost", "irrigation", "labor", "equipment"}
        )
        self.assertFalse(any("score" in key for key in result))
        self.assertFalse(any(key.startswith("total") for key in result))

    def test_cash_labor_and_equipment_are_unavailable(self) -> None:
        """Spec §12.2 | Bug it catches: missing cost/labor/equipment evidence becomes zero."""
        result = build_resource_metrics(_resource_branch())
        cash = result["cash_cost"]
        self.assertEqual(cash["status"], "unavailable")
        self.assertIsNone(cash["value_bdt_per_ha"])
        self.assertEqual(cash["missing_evidence"], ["production_cost_evidence"])
        for name, evidence in (("labor", "labor_evidence"), ("equipment", "equipment_evidence")):
            with self.subTest(name=name):
                metric = result[name]
                self.assertEqual(metric["status"], "unavailable")
                self.assertIsNone(metric["value"])
                self.assertEqual(metric["missing_evidence"], [evidence])
                self.assertTrue(metric["reason"])

    def test_irrigation_is_context_only_without_numeric_total(self) -> None:
        """Spec §12.2 | Bug it catches: qualitative irrigation guidance summed or ranked."""
        result = build_resource_metrics(_resource_branch())
        irrigation = result["irrigation"]
        self.assertEqual(irrigation["status"], "context_only")
        self.assertEqual(irrigation["ranking_status"], "unranked")
        self.assertIsNone(irrigation["total"])
        self.assertNotIn("dependence_score", irrigation)
        self.assertEqual(len(irrigation["per_crop"]), 3)
        self.assertIn("not comparable", irrigation["reason"])

    def test_irrigation_per_crop_uses_node_then_profile_fallback(self) -> None:
        """Spec §12.2 | Bug it catches: per-crop irrigation context lost or node value overridden."""
        contexts = (
            {
                "crop_id": "crop_a",
                "irrigation_guidance": "node guidance",
                "fao_crop_water_need_min_mm": 100.0,
                "fao_crop_water_need_max_mm": 200.0,
                "local_phase_water_total_mm": 150.0,
                "water_ranking_readiness": "HIGH",
            },
            {"crop_id": "crop_b"},
            {"crop_id": "crop_c"},
        )
        profiles = {
            "crop_a": {
                "irrigation_guidance": "profile A",
                "fao_crop_water_need_min_mm": 999.0,
                "fao_crop_water_need_max_mm": 999.0,
                "local_phase_water_total_mm": 999.0,
                "water_ranking_readiness": "LOW",
            },
            "crop_b": {
                "irrigation_guidance": "profile B",
                "fao_crop_water_need_min_mm": 10.0,
                "fao_crop_water_need_max_mm": 20.0,
                "local_phase_water_total_mm": 15.0,
                "water_ranking_readiness": "PARTIAL",
            },
            "crop_c": {},
        }
        result = build_resource_metrics(_resource_branch(contexts), profiles)
        per_crop = result["irrigation"]["per_crop"]
        self.assertEqual(
            [item["crop_id"] for item in per_crop],
            ["crop_a", "crop_b", "crop_c"],
        )
        self.assertEqual(per_crop[0]["irrigation_guidance"], "node guidance")
        self.assertEqual(per_crop[0]["fao_crop_water_need_min_mm"], 100.0)
        self.assertEqual(per_crop[0]["local_phase_water_total_mm"], 150.0)
        self.assertEqual(per_crop[0]["water_ranking_readiness"], "HIGH")
        self.assertEqual(per_crop[1]["irrigation_guidance"], "profile B")
        self.assertEqual(per_crop[1]["fao_crop_water_need_max_mm"], 20.0)
        self.assertEqual(per_crop[1]["water_ranking_readiness"], "PARTIAL")
        self.assertIsNone(per_crop[2]["irrigation_guidance"])
        self.assertIsNone(per_crop[2]["fao_crop_water_need_min_mm"])

    def test_malformed_branch_makes_all_resources_unavailable(self) -> None:
        """Spec §14.4 | Bug it catches: malformed branches return context or numeric resources."""
        base = _resource_branch()
        cases = (
            None,
            {},
            _resource_branch(crop_count=2),
            _resource_branch(transition_count=1),
            {"crops": base["crops"], "transitions": [None, None]},
        )
        for branch in cases:
            with self.subTest(branch=branch):
                result = build_resource_metrics(branch)
                for name in ("cash_cost", "irrigation", "labor", "equipment"):
                    self.assertEqual(result[name]["status"], "unavailable")
                    self.assertEqual(
                        result[name]["reason"], "INVALID_BRANCH_SHAPE"
                    )
                self.assertIsNone(result["cash_cost"]["value_bdt_per_ha"])
                self.assertIsNone(result["labor"]["value"])
                self.assertIsNone(result["equipment"]["value"])
                self.assertEqual(result["irrigation"]["per_crop"], [])
                self.assertIsNone(result["irrigation"]["total"])

    def test_resource_metrics_are_json_serializable(self) -> None:
        """Spec §14.4 | Bug it catches: non-JSON values leak from resource metrics."""
        result = build_resource_metrics(_resource_branch())
        encoded = json.dumps(result, allow_nan=False)
        self.assertNotIn("NaN", encoded)
        self.assertEqual(
            json.loads(encoded)["irrigation"]["ranking_status"], "unranked"
        )


class RankingTests(unittest.TestCase):
    def test_fastest_completion_ranks_conditional_and_notes_empty_candidate(self) -> None:
        """Spec §12.1/§13 | Bug it catches: fastest ranking crosses groups or claims a winner."""
        slow = _ranking_branch(
            "b_slow",
            third_harvest={"earliest": "2026-04-01", "latest": "2026-05-01"},
        )
        fast = _ranking_branch("b_fast")
        result = rank_branches([slow, fast], "fastest_completion")
        self.assertEqual(result["preference"], "fastest_completion")
        self.assertEqual(result["metric"], "completion_days.max")
        self.assertEqual(result["direction"], "ascending")
        self.assertEqual(result["groups"]["candidate"]["count"], 0)
        self.assertEqual(result["groups"]["candidate"]["ranked"], [])
        conditional = result["groups"]["conditional"]
        self.assertEqual(conditional["count"], 2)
        self.assertEqual(
            [entry["branch_id"] for entry in conditional["ranked"]],
            ["b_fast", "b_slow"],
        )
        self.assertEqual(conditional["ranked"][0]["metric_value"], 101)
        self.assertEqual(
            conditional["ranked"][0]["completion_days"],
            {"min": 89, "max": 101},
        )
        self.assertFalse(result["no_winner"])
        self.assertTrue(
            any("Candidate group is empty" in note for note in result["notes"])
        )

    def test_fastest_completion_overlap_note_is_visible(self) -> None:
        """Spec §12.1/§13 | Bug it catches: overlapping completion ranges claim a definitive winner."""
        result = rank_branches(
            [
                _ranking_branch("b_early"),
                _ranking_branch(
                    "b_late",
                    third_harvest={
                        "earliest": "2026-04-06",
                        "latest": "2026-04-17",
                    },
                ),
            ],
            "fastest_completion",
        )
        self.assertEqual(
            [entry["branch_id"] for entry in result["groups"]["conditional"]["ranked"]],
            ["b_early", "b_late"],
        )
        self.assertTrue(any("overlap" in note.lower() for note in result["notes"]))
        self.assertFalse(result["no_winner"])

    def test_diversity_ranks_descending_and_shows_legume_separately(self) -> None:
        """Spec §13 | Bug it catches: diversity order is ascending or legume is folded into family count."""
        result = rank_branches(
            [
                _ranking_branch(
                    "b_two",
                    families=("Poaceae", "Poaceae", "Fabaceae"),
                    legume_flags=(False, False, False),
                ),
                _ranking_branch("b_three"),
            ],
            "more_crop_diversity",
        )
        ranked = result["groups"]["conditional"]["ranked"]
        self.assertEqual([entry["branch_id"] for entry in ranked], ["b_three", "b_two"])
        self.assertEqual(ranked[0]["metric_value"], 3)
        self.assertEqual(ranked[0]["family_repeat_count"], 0)
        self.assertTrue(ranked[0]["legume_present"])
        self.assertEqual(ranked[0]["legume_crop_ids"], ["b_three_crop_1"])
        self.assertEqual(ranked[1]["metric_value"], 2)
        self.assertEqual(ranked[1]["family_repeat_count"], 1)
        self.assertEqual(
            ranked[0]["basis"], "crop_family_count_product_convention"
        )
        self.assertIn("product convention", ranked[0]["diversity_note"])

    def test_economic_and_irrigation_preferences_are_unranked_no_winner(self) -> None:
        """Spec §13/§17.15 | Bug it catches: unavailable cost/return/irrigation becomes zero and ranks."""
        branches = [_ranking_branch("b_one"), _ranking_branch("b_two")]
        expected = {
            "lowest_total_cost": "production_cost_bdt_per_ha",
            "highest_net_return": "net_return_bdt_per_ha",
            "lowest_upfront_cash": "upfront_cash_bdt_per_ha",
            "least_irrigation_dependence": "irrigation_dependence",
        }
        for preference, metric in expected.items():
            with self.subTest(preference=preference):
                result = rank_branches(branches, preference)
                self.assertEqual(result["metric"], metric)
                self.assertEqual(result["direction"], "unavailable")
                self.assertTrue(result["no_winner"])
                for name in ("candidate", "conditional"):
                    group = result["groups"][name]
                    self.assertEqual(group["ranked"], [])
                    self.assertEqual(group["count"], 2 if name == "conditional" else 0)
                    for entry in group["unranked"]:
                        self.assertIsNone(entry["metric_value"])
                        self.assertTrue(entry["reason"])
                        self.assertTrue(entry["missing_evidence"])

    def test_missing_completion_is_unranked_not_favorable(self) -> None:
        """Spec §13/§14.4 | Bug it catches: missing completion gets a zero or favorable rank."""
        result = rank_branches(
            [_ranking_branch("b_missing", third_harvest=None)],
            "fastest_completion",
        )
        conditional = result["groups"]["conditional"]
        self.assertEqual(conditional["count"], 1)
        self.assertEqual(conditional["ranked"], [])
        self.assertEqual(len(conditional["unranked"]), 1)
        self.assertTrue(result["no_winner"])
        self.assertIsNone(conditional["unranked"][0]["metric_value"])
        self.assertIn("third_harvest_range", conditional["unranked"][0]["missing_evidence"])

    def test_blocked_branch_is_excluded_not_revived(self) -> None:
        """Spec §13/§17.14 | Bug it catches: a preference revives an unsupported branch."""
        result = rank_branches(
            [
                _ranking_branch("b_blocked", status="unsupported"),
                _ranking_branch("b_ok"),
            ],
            "fastest_completion",
        )
        self.assertEqual(result["excluded"], ["b_blocked"])
        self.assertEqual(
            [entry["branch_id"] for entry in result["groups"]["conditional"]["ranked"]],
            ["b_ok"],
        )
        self.assertFalse(result["no_winner"])

    def test_candidate_and_conditional_groups_stay_separate(self) -> None:
        """Spec §13 | Bug it catches: candidate and conditional branches share one ranking."""
        result = rank_branches(
            [
                _ranking_branch("b_candidate", status="candidate"),
                _ranking_branch("b_conditional", status="conditional"),
            ],
            "fastest_completion",
        )
        self.assertEqual(result["groups"]["candidate"]["count"], 1)
        self.assertEqual(result["groups"]["conditional"]["count"], 1)
        self.assertEqual(
            [entry["branch_id"] for entry in result["groups"]["candidate"]["ranked"]],
            ["b_candidate"],
        )
        self.assertEqual(
            [entry["branch_id"] for entry in result["groups"]["conditional"]["ranked"]],
            ["b_conditional"],
        )

    def test_ties_break_deterministically_by_branch_id(self) -> None:
        """Spec §13/§14.4 | Bug it catches: equal metrics order nondeterministically."""
        result = rank_branches(
            [_ranking_branch("b_b"), _ranking_branch("b_a")],
            "fastest_completion",
        )
        self.assertEqual(
            [entry["branch_id"] for entry in result["groups"]["conditional"]["ranked"]],
            ["b_a", "b_b"],
        )
        self.assertIn("branch_id", result["method"])

    def test_invalid_preference_raises(self) -> None:
        """Spec §13 | Bug it catches: an unknown preference silently falls back."""
        with self.assertRaises(ValueError):
            rank_branches([], "unknown_preference")

    def test_real_420_branches_rank_fastest_and_diversity(self) -> None:
        """Spec §13/§17.14-17 | Bug it catches: real conditional branches are not ranked or groups mix."""
        profiles = load_crop_profiles(DATA_CSV)
        expanded = expand_branches(
            profiles, "2026-11-06", max_waiting_days=365
        )
        branches = expanded["branches"]
        self.assertEqual(len(branches), 420)
        fastest = rank_branches(branches, "fastest_completion", profiles)
        self.assertEqual(fastest["groups"]["candidate"]["count"], 0)
        self.assertEqual(fastest["groups"]["conditional"]["count"], 420)
        self.assertEqual(len(fastest["groups"]["conditional"]["ranked"]), 420)
        self.assertEqual(fastest["groups"]["conditional"]["unranked"], [])
        self.assertTrue(any("overlap" in note.lower() for note in fastest["notes"]))
        diversity = rank_branches(branches, "more_crop_diversity", profiles)
        self.assertEqual(diversity["groups"]["candidate"]["count"], 0)
        self.assertGreater(len(diversity["groups"]["conditional"]["ranked"]), 0)
        economics = rank_branches(branches, "lowest_total_cost", profiles)
        self.assertTrue(economics["no_winner"])
        self.assertEqual(economics["groups"]["conditional"]["ranked"], [])
        self.assertEqual(len(economics["groups"]["conditional"]["unranked"]), 420)

    def test_ranking_is_json_serializable(self) -> None:
        """Spec §14.4 | Bug it catches: non-JSON values leak from ranking output."""
        result = rank_branches([_ranking_branch("b_one")], "fastest_completion")
        encoded = json.dumps(result, allow_nan=False)
        self.assertNotIn("NaN", encoded)
        self.assertFalse(json.loads(encoded)["no_winner"])


if __name__ == "__main__":
    unittest.main()
