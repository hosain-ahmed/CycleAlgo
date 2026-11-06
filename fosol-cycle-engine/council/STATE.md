# Council State

Last updated: 2026-11-06 (E6 fix 1 PASS; fixes 2–3 pending; testing policy amended)

## RESUME HERE
1. Read this file, `council/CHECKLIST.md`, and `council/TESTING_POLICY.md`.
2. Run: `cd fosol-cycle-engine` then `python -X utf8 -m unittest discover -s tests -v`
   (expect 177 tests, OK).
3. E6 fix 1 (next-season roll) is PASS and committed. Next: **fix 2 rotation family**,
   then **fix 3 sequence uniqueness**, then re-run the E6 gate.
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
  Reports `E6-fix1-builder.md`, `E6-fix1-review.md`.
- E6 fixes 2 (rotation repeats) and 3 (sequence uniqueness) still pending; E6 gate not final.
- Policy: `council/TESTING_POLICY.md` (budgets, fault log, mutation check, <30-line reports,
  demo_check at E8–E9).

## Done
- Step 0 setup: dirs, checklist, state.
- E1 crop-profile loader: 14 tests. Commit `4711b3e`.
- E2 request validation + error contract: 18 new tests. Commit `fc92802`.
- E3 environmental loader: 54 new tests. Commit `68220d1`.
- E4 calendar evaluator: 30 new tests; compact gate 5/5 mutations. Commit `a528c26`.
- E5 soil/land + water: 20 new tests; 5/5 mutations. Commit `8fdbd5d`.
- E6 baseline: timeline/prep/waiting/rotation/3-crop expansion; 40 new tests.
  Fix 1: next-season roll; 177 tests total.
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
| E6 fix 1 | PASS | PASS | pending | pending | PASS | e4811bb |
| E6 fixes 2–3 | pending | pending | pending | pending | pending | pending |
