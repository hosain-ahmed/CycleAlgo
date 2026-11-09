# E9 Stream A - explore envelope

Delivered `src/explore.py`, `tests/test_explore.py` (24 tests), both main example pairs, and regenerated the unsupported-district, no-options, data-unavailable, and SMAP-context examples. Request now echoes effective `max_initial_wait_days`/`max_waiting_days`; assumptions state the 180-day product-relevance limit; ranking entries include `initial_wait_days`; `FRONTEND_HANDOFF.md` now says so.

Climate: every crop option and branch crop node now has `status="unknown"`, `code="CLIMATE_EXPOSURE_DEFERRED"`, `missing_evidence=["current_season_climate_exposure"]`, empty `source_ids`; missing-evidence IDs/docs/questions aligned.

Boundary: synthetic 180-day window gives 179 -> `no_supported_options`/`FUTURE_WINDOW_EXCEEDS_LIMIT`; 180/181 -> conditional branches. Kills the off-by-one and `<` versus `<=` mutations.
Economics: all five monetary values null, scenarios `[]`; contract checker rejects a zeroed unavailable value.

Examples/checker: all `examples/*.json` contract checks PASS; `demo_check.py` PASS. Full suite: `Ran 310 tests in 8.538s`, `OK`.
E6 smoke 365/365: 420 branches, 0 candidate / 420 conditional, 15 exclusions; unchanged.
No E6/E7/W1-W5 changes; no Data changes; no commits.
