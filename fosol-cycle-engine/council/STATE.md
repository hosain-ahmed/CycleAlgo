# Council State

Last updated: 2026-11-06 (E5 complete; testing policy amended)

## RESUME HERE
1. Read this file, `council/CHECKLIST.md`, and `council/TESTING_POLICY.md`.
2. Run: `cd fosol-cycle-engine` then `python -X utf8 -m unittest discover -s tests -v`
   (expect 116 tests, OK).
3. Next layer: **E6 timeline, preparation, waiting, 3-crop expansion** (spec §10, §11).
4. Evidence gaps: no local soil measurements; preparation times blank; max waiting limit
   unset. Keep timing/prep `unknown`/conditional and never zero-fill.
4. E5 tests per the amended policy: boundaries, one normal case, all missing shapes,
   one failure, unknown-never-pass; budget 15–25; test docstrings `Spec §X | Bug: ...`.
5. SMAP token: `Q:\CycleAlgo\appeears_token.txt` expires 2026-11-07T03:13:49Z.
   Rerun `python tools/appeears_login.py` when it expires; never commit it.

## Current
- E1, E2, E3 PASS; commits `4711b3e`, `fc92802`, `68220d1`.
- E3 live-verified both providers:
  - POWER official daily point API, v2.10.3, fill `-999`.
  - SMAP via AppEEARS `SPL4SMGP.008`, layers `Geophysical_Data_sm_surface` /
    `..._sm_rootzone`, 3-hourly, 9 km, fill `-9999`; live task done, CSV fixture saved.
- E4 calendar evaluator PASS: 30 new tests (116 total); compact gate 5/5 mutations killed.
  Reports: `E4-fault-log.md`, `E4-review-round2.md`, `E4-spec-integrity.md`. Commit `a528c26`.
- E5 soil/land + water checks PASS: 20 new tests (136 total); 5/5 mutations killed.
  Reports: `E5-builder.md`, `E5-review.md`, `E5-spec-integrity.md`; docs `SOIL_WATER.md`.
  Real crops: all soil properties unknown (no local evidence); water is caution/unknown,
  never pass; no demand-minus-rainfall. Residual low: non-string salinity `unit` details
  may not JSON-serialize; FAO min>max returns caution.
- Policy: `council/TESTING_POLICY.md` (budgets, fault log, mutation check, <30-line reports,
  demo_check at E8–E9).

## Done
- Step 0 setup: dirs, checklist, state.
- E1 crop-profile loader: 14 tests. Reports `council/reports/E1-*.md`. Commit `4711b3e`.
- E2 request validation + error contract: 18 new tests. Reports `council/reports/E2-*.md`.
  Commit `fc92802`.
- E3 environmental loader: 54 new tests (86 total). Reports `council/reports/E3-*.md`.
  Docs `docs/ENVIRONMENTAL_DATA.md`, fixtures under `tests/fixtures/`. Commit `68220d1`.
- E4 calendar evaluator: 30 new tests (116 total). Compact gate PASS (5/5 mutations).
  Reports `E4-fault-log.md`, `E4-review-round2.md`, `E4-spec-integrity.md`.
- E4 calendar evaluator: 30 new tests (116 total). Reports `council/reports/E4-*.md`.
  Round-2 fixes: optional late bound, late order/year, precision/source guards, edge tests.
- Entry points:
  - `src/crop_profiles.py` -> `load_crop_profiles(path)`
  - `src/request_validation.py` -> `validate_explore_request(payload, known_crop_ids)`
  - `src/error_contract.py` -> `build_error_response(exc)`, `http_status_for_error(exc)`
  - `src/power_api.py` -> `fetch_power_daily`, `normalize_power_response`
  - `src/smap_api.py` -> `fetch_smap_point`, `parse_appeears_csv`
  - `src/environment.py` -> `load_environment`, `load_power_environment`, `load_smap_environment`
  - `src/environment_cache.py` -> `EnvironmentCache`, `build_cache_key`

## Blocked / must ask user
- Preparation times: `turnaround_days_*` is blank for all 8 crops -> timing must stay
  conditional/unknown (spec §10.2). Do not use zero.
- Max waiting limit, local soil evidence, sequence restrictions, costs/yields/prices:
  remain `unknown`/`null`/"Economic estimate unavailable" unless the user supplies evidence.
- Duration reference point (sowing vs transplanting) is preserved but unconfirmed.
- AppEEARS token expiry is a recurring operational dependency (48h); the code raises a
  clear error telling the user to rerun the login helper.

## Standing notes
- `v1.md` in the parent repo is modified/uncommitted user work. It is the source of truth
  used so far; do NOT commit or revert it without the user's approval.
- Never touch `Data/DataNEVERBEUSED/`; `Data/` files are read-only.
- Python 3.13.2, stdlib only; one shared evaluator; no crop-specific branches.
- Secrets: `token.txt` (Earthdata JWT) and `appeears_token.txt` (AppEEARS) are gitignored,
  never committed, never printed. `tools/appeears_login.py` creates the AppEEARS token.
- Low-severity review findings are accepted as non-blocking; see the reports.

## Gate log

| Item | Builder | Code Review | Spec Audit | Integrity | Verdict | Commit |
|---|---|---|---|---|---|---|
| E1 | PASS | PASS | PASS | PASS | PASS | 4711b3e |
| E2 | PASS | PASS | PASS | PASS | PASS | fc92802 |
| E3 | PASS | PASS | PASS | PASS | PASS | 68220d1 |
| E4 | PASS | PASS | PASS | PASS | PASS | a528c26 |
| E5 | PASS | PASS | PASS | PASS | PASS | e91cb1b |
