# Council State

Last updated: 2026-11-06 (E7 W2 PASS; W3 next)

## RESUME HERE
1. Read this file, `council/CHECKLIST.md`, and `council/TESTING_POLICY.md`.
2. Run: `cd fosol-cycle-engine` then `python -X utf8 -m unittest discover -s tests -v`
   (expect 216 tests, OK).
3. E7 W1–W2 PASS. Next: **W3 output assembler** (`build_outlook`) — schema, exact
   em-dash label, status ok/partial/unavailable, sources/fill/missing from data,
   union-span notes, all warning flags default OFF.
4. W1/W2 code: `src/seasonal_replay.py`, `src/outlook_config.py`,
   `src/outlook_indicators.py`; reports `E7-W1-*`, `E7-W2-*`, `E7-mustard-audit.md`.
5. Local 1990 CSV `PRECTOTCORR` is 24× the API/2000 file; never use raw. See
   `docs/ENVIRONMENTAL_DATA.md` and `E7-mustard-audit.md`.
5. §6.2 climate exposure is still pending; do not claim complete crop checks.
6. SMAP token: `Q:\CycleAlgo\appeears_token.txt` expires 2026-11-07T03:13:49Z.
   Rerun `python tools/appeears_login.py` when it expires; never commit it.
4. Evidence gaps: no local soil measurements; preparation blank; max waiting unset;
   duration reference stage unconfirmed. Keep timing/prep `unknown`/conditional, never zero.
   §6.2 climate exposure is still pending; do not claim complete checks.
5. SMAP token: `Q:\CycleAlgo\appeears_token.txt` expires 2026-11-07T03:13:49Z.
   Rerun `python tools/appeears_login.py` when it expires; never commit it.

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
