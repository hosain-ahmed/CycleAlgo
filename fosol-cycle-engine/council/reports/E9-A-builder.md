# E9 Stream A - explore envelope

Delivered `src/explore.py`, `tests/test_explore.py` (24 tests), both main example pairs, and regenerated the unsupported-district, no-options, data-unavailable, and SMAP-context examples. Request now echoes effective `max_initial_wait_days`/`max_waiting_days`; assumptions state the 180-day product-relevance limit; ranking entries include `initial_wait_days`; `FRONTEND_HANDOFF.md` now says so.

Handoff size: `example_response.json` and `example_response_smap_context.json` are selected-boro runs with `max_branches=1` and the cached real AppEEARS SMAP context (24 observations, 2025-01-01..03 UTC), exactly one 3-crop/2-transition branch. `example_response_first_crop_selected.json` is the fuller 10-branch handoff sample; a live Boro run returns 42 branches.

Climate: every crop option and branch crop node now has `status="unknown"`, `code="CLIMATE_EXPOSURE_DEFERRED"`, `missing_evidence=["current_season_climate_exposure"]`, empty `source_ids`; missing-evidence IDs/docs/questions aligned.

Boundary: synthetic 180-day window gives 179 -> `no_supported_options`/`FUTURE_WINDOW_EXCEEDS_LIMIT`; 180/181 -> conditional branches. Kills the off-by-one and `<` versus `<=` mutations.
Economics: all five monetary values null, scenarios `[]`; contract checker rejects a zeroed unavailable value.

Examples/checker: all `examples/*.json` contract checks PASS; `demo_check.py` PASS with cached real SMAP observations. Full suite: `Ran 310 tests in 7.168s`, `OK`.
E6 smoke 365/365: 420 branches, 0 candidate / 420 conditional, 15 exclusions; unchanged.
No E6/E7/W1-W5 changes; no Data changes; no commits.
