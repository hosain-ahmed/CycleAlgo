# Council State

Last updated: 2026-11-06 (E1 complete)

## Current
- E1 PASS and committed. Next: E2 request validation + error contract.

## Done
- Step 0 setup: dirs, checklist, state.
- E1 crop-profile loader: 14 tests pass; Builder/Review/Spec/Integrity all PASS.
  Reports: `council/reports/E1-*.md`.
- Noted for downstream: `turnaround_days_*` empty for all 8 crops -> prep unknown;
  duration reference point preserved but unresolved; evidence flags live in `raw`.

## Blocked
- Nothing blocks E2.

## Upcoming questions for the user (do not guess)
1. SMAP product and documented access route (spec §19) — needed for the SMAP part of E3;
   POWER work can proceed without it.
2. Sourced preparation times, max waiting limit, local soil evidence, sequence restrictions,
   costs, yields, farm-gate prices — remain `unknown`/`null`/unavailable unless supplied.
3. Confirm whether POWER is the only production environmental provider for v1 if SMAP is deferred.

## Gate log

| Item | Builder | Code Review | Spec Audit | Integrity | Verdict | Commit |
|---|---|---|---|---|---|---|
| E1 | PASS | PASS | PASS | PASS | PASS | pending |
