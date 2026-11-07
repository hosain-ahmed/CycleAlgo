"""Tests for branch completion-time and diversity metrics (v1.md §12.1, §13, §14.4)."""

import json
import unittest
from pathlib import Path

from src.branch_expander import expand_branches
from src.branch_metrics import (
    build_economics_metrics,
    build_resource_metrics,
    calculate_completion_time,
    calculate_diversity_metrics,
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


if __name__ == "__main__":
    unittest.main()
