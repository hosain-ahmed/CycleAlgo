# Council State

Last updated: 2026-11-07 (E8 PASS with real-realization completion; next E9)

## RESUME HERE
1. Read this file, `council/CHECKLIST.md`, `council/TESTING_POLICY.md`, and
   `council/reports/E8-preflight.md`.
2. Run: `cd fosol-cycle-engine` then `python -X utf8 -m unittest discover -s tests -v`
   (expect 274 tests, OK). E6 smoke must stay 420 branches / 0 candidate / 420
   conditional / 15 exclusions.
3. E8 PASS. Next: **E9 response envelope, status precedence, warnings, branch
   attachment, `scripts/demo_check.py`, API**. Completion uses actual fastest/slowest
   realizations (example b_82899e8d6941: 655..682; P1 2027-07-24/H3 2029-05-09 fast,
   P1 2027-07-10/H3 2029-05-22 slow). Tightness + 300-sample exact min/max tests.
   fastest 420/420; candidate 0 because prep/soil/water/duration evidence is missing
   on all 1260 crop nodes. §17.16 N/A (no financial values).
4. **E9 hard gate:** build and run `scripts/demo_check.py` before any E9 commit;
   golden Rajshahi scenarios, invariants, offline/stale-cache behavior. Do not defer again.
4. E8 defaults in use (user can override): economics A (completion+diversity only;
   all economic/resource metrics unavailable), completion endpoints A
   (earliest−earliest / latest−latest, rank by latest), irrigation display-only.
   Labor/equipment/upfront cash unavailable; no annualization; diversity = family
   count with legume presence separate. See `reports/E8-preflight.md`.
5. After decisions: W1 completion -> W2 diversity -> W3 resources -> W4 economics
   unavailable -> W5 ranking. One function per worker, different reviewer; tests,
   mutation, code+spec, E6 smoke, commit/push after each.
6. E7 warnings all OFF: wheat 35/35 hidden; mustard held at corrected 1/35.
7. Local 1990 CSV `PRECTOTCORR` is 24× the API/2000 file; never use raw. The guard
   `tests/test_local_power_data.py` locks this and the 2026-09 stale-B drift.
8. §6.2 current-season climate exposure is still unimplemented; do not claim it.
9. SMAP token expiry is operational; rerun `tools/appeears_login.py` when needed.

## Current
- E1–E5 PASS. Commits: `4711b3e`, `fc92802`, `68220d1`, `a528c26`, `8fdbd5d`.
- E3 live-verified POWER (v2.10.3, fill -999) and AppEEARS SMAP
  (`SPL4SMGP.008`, 3-hourly, 9 km, fill -9999).
- E6 fix 1 PASS: next-season windows roll forward within `max_waiting_days`.
  Smoke (`2026-11-06`, max 365): 295 -> 420 branches, 0 candidate / 420 conditional,
  exclusions 56 -> 15 (all `WINDOW_GEOGRAPHY_UNKNOWN`), Aman 0 -> 62.
  Reports `E6-fix1-builder.md`, `E6-fix1-review.md`. Commit `5f6cef0`.
- E6 fix 2 PASS: rotation compares all prior positions; 150 position-1/3 family-repeat
  branches now caution (was 81 pass / 69 caution), 0 `FAMILY_DIVERSIFIED`; total branches
  still 420, exclusions still 15. Reports `E6-fix2-builder.md`, `E6-fix2-review.md`.
- E6 fix 3 PASS: sequence/branch-ID uniqueness check added; 420 branches, 420 unique
  sequences/IDs, 0 duplicates; branches not collapsed. Reports `E6-fix3-builder.md`,
  `E6-fix3-review.md`.
- E6 fixes 4–5 PASS: Option A null-latest (waiting/total latest null, `latest_invalid`,
  earliest retained, `total >= prep` invariant) and `_transition_ok` requires
  `next_planting.status=="pass"`. 187 tests; reports `E6-fix4-*.md`, `E6-fix5-*.md`.
- E6 final gate PASS: 7/7 mutations killed; no-prep 420 branches / 15 exclusions /
  0 candidate / 420 conditional; boro 55; 150 position-1/3 repeats all caution;
  uniqueness 420/420. Prep 7–10: 419/16, total<prep 30 -> 0, 30 `latest_invalid`,
  78 caution / 0 pass. Reports `E6-final-review-round2.md`,
  `E6-final-spec-integrity-round2.md`.
- E6 wording fix PASS: `_limit_error` now states product relevance cutoff, not a
  scientifically safe maximum / biological impossibility; 188 tests; smoke 420/15.
- E7 W1 PASS: `map_schedule_to_seasons` maps E6 union spans to 1991–2025, 90%/100%
  coverage, cross-year/leap handling, `last_complete_data_date` parameter. 201 tests;
  6/6 mutations; E6 smoke 420/0/420/15.
- E7 mustard audit: raw 29/35 was a local CSV unit bug; 1990 file `PRECTOTCORR`
  is 24× the live API/2000 file. Corrected 1/35 (2023 season, 2024-01-21 70.23 mm/day).
  Wheat warnings 35/35 (weak), mustard 1/35 (weak). All warning flags default OFF;
  statistics only until stage-specific windows/evidence. Report `E7-mustard-audit.md`.
- E7 W2 PASS: temperature pooled stats (≥90%, linear IQR), precipitation per-season
  totals (100% days, mm), generic warning engine with per-indicator text, flags default
  OFF. 216 tests; 7/7 mutations; E6 smoke 420/0/420/15. Reports `E7-W2-*`.
- E7 W3 PASS: `build_outlook` schema, exact em-dash label, status ok/partial/unavailable,
  data-sourced version/fill/missing, indicator `source_ids`, union-span notes. 224 tests;
  8 W3; 2/2 contract mutations. E7 total 36 tests vs 20–30; extra cases cover schema,
  status, source refs, unavailable nulls (documented reason). Reports `E7-W3-*`.
- E7 final gate PASS: spec/integrity, 224 tests, E6 smoke 420/0/420/15. Warnings OFF
  (wheat 35/35 hidden; mustard corrected 1/35 held); no SMAP/soil/water/prep/duration
  added; E7 historical-only. Report `E7-final-spec-integrity.md`.
- E8 preflight guard PASS: `tests/test_local_power_data.py` locks the 24× 1990
  PRECTOTCORR and the 2026-09 stale-B drift; live fixture proves A/24 = API.
  225 tests; E6 smoke 420/0/420/15. Reports `E8-preflight-guard*.md`. Commit `2e01a65`.
- E8 preflight delivered (`council/reports/E8-preflight.md`): all economic inputs
  missing; defaults in use: completion+diversity only, economics unavailable,
  completion endpoints A, irrigation display-only.
- E8 W1 PASS: `calculate_completion_time` decision A, unavailable/null on missing,
  malformed, or reversed ranges; 232 tests; 5/5 mutations; E6 smoke 420/0/420/15.
  Reports `E8-W1-builder.md`, `E8-W1-review.md`.
- E8 W2 PASS: `calculate_diversity_metrics` family count/repeat proxy, legume
  presence with profile fallback; missing -> unknown/null; 240 tests; 5/5 mutations.
  Reports `E8-W2-builder.md`, `E8-W2-review.md`.
- E8 W3 PASS: `build_resource_metrics` keeps cash/irrigation/labor/equipment separate;
  cash/labor/equipment unavailable/null; irrigation context-only/unranked; no combined
  score or summed volume; 246 tests; 5/5 mutations. Reports `E8-W3-*`.
- E8 W4 PASS: `build_economics_metrics` all monetary metrics unavailable/null;
  reference yields context-only; no price/cost/cash-flow values; 253 tests; 5/5
  mutations. Reports `E8-W4-*`.
- E8 W5 PASS: `rank_branches` candidate/conditional groups separate, blocked excluded,
  fastest/diversity ranked, economics/irrigation unranked/no winner, missing metric
  unranked, deterministic ties; 264 tests; 5/5 mutations. Reports `E8-W5-*`.
- E8 completion revision PASS: corner form, both realizations, 300-seed property test,
  enumeration fallback with negative guard, min<=max all 420, no
  `COMPLETION_RANGE_INVALID` unranked, fastest 420/420 conditional. 271 tests; E6 smoke
  420/0/420/15. Reports `E8-W1-revision-*.md`.
- E8 final PASS: real fastest/slowest realization range (example 655..682 with dates),
  independent tightness all 420, 300-sample exact min/max, prep-known distinction
  (60..99 vs B 60..129), enumeration fallback, fastest 420/420; 274 tests; 49 E8
  (+9 for user-requested realization/tightness tests); §17.16 N/A.
  Report `E8-final-spec-integrity-realization.md`.
- Policy: `council/TESTING_POLICY.md` (budgets, fault log, mutation check, <30-line reports,
  demo_check at E8–E9).

## Done
- Step 0 setup: dirs, checklist, state.
- E1 crop-profile loader: 14 tests. Commit `4711b3e`.
- E2 request validation + error contract: 18 new tests. Commit `fc92802`.
- E3 environmental loader: 54 new tests. Commit `68220d1`.
- E4 calendar evaluator: 30 new tests; compact gate 5/5 mutations. Commit `a528c26`.
- E5 soil/land + water: 20 new tests; 5/5 mutations. Commit `8fdbd5d`.
- E6 timeline/prep/waiting/rotation/3-crop expansion PASS: 187 tests total.
  Fixes: next-season roll, all-path rotation repeats, sequence uniqueness,
  Option A null-latest, candidate `next_planting` pass guard.
- E7 W1 season mapping PASS: 13 focused tests, 201 total; 6/6 mutations; E6 smoke
  unchanged. Reports `E7-W1-builder.md`, `E7-W1-review.md`.
- E7 W2 indicators PASS: 15 focused tests, 216 total; 7/7 mutations; E6 smoke unchanged.
  Reports `E7-W2-builder.md`, `E7-W2-review.md`.
- E7 W3 outlook assembler PASS: 8 focused tests, 224 total; contract mutations killed.
  Reports `E7-W3-builder.md`, `E7-W3-review.md`.
- E7 final PASS: 224 tests; E6 smoke unchanged; warnings OFF; E7 36 tests (+6 budget,
  documented). Next E8.
- Entry points:
  - `src/crop_profiles.py` -> `load_crop_profiles(path)`
  - `src/request_validation.py` -> `validate_explore_request(payload, known_crop_ids)`
  - `src/error_contract.py` -> `build_error_response(exc)`, `http_status_for_error(exc)`
  - `src/power_api.py` -> `fetch_power_daily`, `normalize_power_response`
  - `src/smap_api.py` -> `fetch_smap_point`, `parse_appeears_csv`
  - `src/environment.py` -> `load_environment`, `load_power_environment`, `load_smap_environment`
  - `src/environment_cache.py` -> `EnvironmentCache`, `build_cache_key`
  - `src/calendar_evaluator.py` -> `evaluate_calendar_fit`
  - `src/soil_water.py` -> `evaluate_soil_fit`, `evaluate_water_fit`, `evaluate_soil_water`
  - `src/timeline.py` -> `build_crop_timeline`, `calculate_next_planting`, `calculate_waiting`
  - `src/rotation.py` -> `evaluate_rotation`
  - `src/branch_expander.py` -> `expand_branches`

## Blocked / must ask user
- Preparation times: `turnaround_days_*` blank for all 8 crops -> timing unknown; no zero.
- Max waiting limit, local soil evidence, sequence restrictions, costs/yields/prices:
  remain `unknown`/`null`/"Economic estimate unavailable" unless supplied.
- Duration reference point preserved but unconfirmed.
- AppEEARS token expiry is operational (48h); code raises a clear rerun hint.
- E9 must build/run `scripts/demo_check.py` before any commit (hard gate).
- Candidate group is empty (0/420); present conditional branches with evidence reasons
  and an explicit “no candidate branches” state. Cause: prep unknown, soil unknown,
  water caution/unknown, duration reference unresolved on all 1260 crop nodes.
- §17.16 N/A until sourced economics; all monetary metrics unavailable by design.

## Standing notes
- `v1.md` is modified/uncommitted user work; source of truth, do not commit/revert.
- Never touch `Data/DataNEVERBEUSED/`; `Data/` read-only.
- Python 3.13.2, stdlib only; one shared evaluator; no crop-specific branches.
- `token.txt` and `appeears_token.txt` are gitignored, never printed.

## Gate log

| Item | Builder | Code Review | Spec Audit | Integrity | Verdict | Commit |
|---|---|---|---|---|---|---|
| E1 | PASS | PASS | PASS | PASS | PASS | 4711b3e |
| E2 | PASS | PASS | PASS | PASS | PASS | fc92802 |
| E3 | PASS | PASS | PASS | PASS | PASS | 68220d1 |
| E4 | PASS | PASS | PASS | PASS | PASS | a528c26 |
| E5 | PASS | PASS | PASS | PASS | PASS | 8fdbd5d |
| E6 fix 1 | PASS | PASS | PASS | PASS | PASS | 5f6cef0 |
| E6 fix 2 | PASS | PASS | PASS | PASS | PASS | f867dd5 |
| E6 fix 3 | PASS | PASS | PASS | PASS | PASS | 9b99cc1 |
| E6 final | PASS | PASS | PASS | PASS | PASS | 609cdf0 |
| E7 W1 | PASS | PASS | PASS | PASS | PASS | 8e2f0d3 |
| E7 W2 | PASS | PASS | PASS | PASS | PASS | 1fafb61 |
| E7 W3 | PASS | PASS | PASS | PASS | PASS | cff97bc |
| E7 final | PASS | PASS | PASS | PASS | PASS | d454b96 |
| E8 guard | PASS | PASS | PASS | PASS | PASS | 2e01a65 |
| E8 W1 | PASS | PASS | PASS | PASS | PASS | 7c45cbb |
| E8 W2 | PASS | PASS | PASS | PASS | PASS | 6495a4d |
| E8 W3 | PASS | PASS | PASS | PASS | PASS | 4b11246 |
| E8 W4 | PASS | PASS | PASS | PASS | PASS | cae196a |
| E8 W5 | PASS | PASS | PASS | PASS | PASS | 30927f7 |
| E8 W1 rev | PASS | PASS | PASS | PASS | PASS | d0a7e8d |
| E8 final | PASS | PASS | PASS | PASS | PASS | 3934114 |
