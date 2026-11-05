# Council State

Last updated: 2026-11-06 (E2 complete; stopping for the night)

## RESUME HERE
1. Read this file and `council/CHECKLIST.md`.
2. Run: `cd fosol-cycle-engine` then `python -X utf8 -m unittest discover -s tests -v`
   (expect 32 tests, OK).
3. Next task: **E3 environmental loading + caching + missing-value handling** (spec §15).
   Spawn the Builder, then the three auditors, then commit.
4. Ask the user the SMAP question before writing any SMAP code (see Blocked).

## Current
- E1 and E2 PASS, committed and pushed to `origin/vv1`.
- Next: E3. POWER work may proceed; SMAP needs a user decision first.

## Done
- Step 0 setup: dirs, checklist, state.
- E1 crop-profile loader: 14 tests. Reports `council/reports/E1-*.md`. Commit `4711b3e`.
- E2 request validation + error contract: 32 tests total (18 new).
  Reports `council/reports/E2-*.md`.
- Entry points so far:
  - `src/crop_profiles.py` -> `load_crop_profiles(path)`
  - `src/request_validation.py` -> `validate_explore_request(payload, known_crop_ids)`
  - `src/error_contract.py` -> `build_error_response(exc)`, `http_status_for_error(exc)`

## Blocked / must ask user
- **SMAP (spec §19):** no product/access route chosen, and no SMAP file exists in `Data/`.
  Do not invent an endpoint. POWER can be built first; SMAP checks stay `unknown`/unavailable
  until the user picks a documented product.
- Preparation times: `turnaround_days_*` is blank for all 8 crops -> timing must stay
  conditional/unknown (spec §10.2). Do not use zero.
- Max waiting limit, local soil evidence, sequence restrictions, costs/yields/prices:
  remain `unknown`/`null`/"Economic estimate unavailable" unless the user supplies evidence.
- Duration reference point (sowing vs transplanting) is preserved but unconfirmed.

## Standing notes
- `v1.md` in the parent repo is modified/uncommitted user work. It is the source of truth
  used so far; do NOT commit or revert it without the user's approval.
- Never touch `Data/DataNEVERBEUSED/`; `Data/` files are read-only.
- Python 3.13.2, stdlib only; one shared evaluator; no crop-specific branches.
- Low-severity E1/E2 findings accepted as non-blocking; see the review reports if hardening
  is wanted later (Unicode digits in MM-DD, float-based integer parse, padded district_id).

## Gate log

| Item | Builder | Code Review | Spec Audit | Integrity | Verdict | Commit |
|---|---|---|---|---|---|---|
| E1 | PASS | PASS | PASS | PASS | PASS | 4711b3e |
| E2 | PASS | PASS | PASS | PASS | PASS | pending |
