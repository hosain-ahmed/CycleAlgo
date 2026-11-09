# Explore contract (frozen)

Entry point: `src.explore.explore(payload, *, profiles, config=None, environment=None,
smap_context=None, now=None) -> dict`. HTTP wrapper: `src.api.handle_explore(payload, ...)
-> (status_code, body)`; server `POST /api/explore`, `GET /health`.

## Request

```json
{
  "district_id": "rajshahi",
  "start_date": "2026-11-06",
  "first_crop_id": null,
  "water_access": "unknown",
  "preference": "fastest_completion",
  "max_initial_wait_days": 180,
  "max_waiting_days": null
}
```

`request` echoes the effective request, including the caller/engine
`max_initial_wait_days` and `max_waiting_days` policy values (null when unset).

`district_id` required stable ID (only `rajshahi` supported). `start_date` required
`YYYY-MM-DD`. `first_crop_id` null or a crop-profile ID. `water_access` in
`rainfed|irrigation_available|unknown` (default unknown). `preference` in
`fastest_completion|lowest_total_cost|least_irrigation_dependence|highest_net_return|
more_crop_diversity` (default fastest_completion; `lowest_upfront_cash` rejected until
cash-flow evidence exists).

## Success envelope

```json
{
  "schema_version": "1",
  "generated_at": "UTC ISO",
  "request": {"district_id": "...", "start_date": "...", "first_crop_id": null,
              "water_access": "...", "preference": "..."},
  "status": "ok|partial|no_supported_options|unsupported_district|data_unavailable",
  "district": {"district_id": "rajshahi", "display_name": "Rajshahi",
               "supported": true, "geographic_scope": "representative point/grid"},
  "assumptions": [{"code": "...", "message": "..."}],
  "data_sources": [{"source_id": "...", "provider": "...", "product": "...",
                    "version": "...", "coverage": "...", "retrieved_at": null}],
  "crop_options": [{"crop_id": "...", "name_en": "...", "name_bn": "...",
                    "reference_variety": "...", "status": "candidate|conditional|unsupported",
                    "initial_wait_days": 0, "shown": true,
                    "checks": {"calendar": {...}, "climate": {...}, "soil": {...},
                               "water": {...}, "rotation": null},
                    "reasons": [], "missing_evidence": [], "source_ids": []}],
  "branches": [{"branch_id": "b_...", "status": "candidate|conditional",
                "initial_wait_days": 0, "crops": [3 nodes], "transitions": [2],
                "metrics": {"completion": {...}, "resources": {...},
                            "economics": {...}, "diversity": {...}},
                "outlook": {"status": "ok|partial|unavailable", "label": "...",
                            "indicators": []},
                "reasons": [], "cautions": [], "missing_evidence": [], "source_ids": []}],
  "branch_summary": {"candidate_count": 0, "conditional_count": 0,
                     "no_candidate_branches": true,
                     "message": "No candidate branches - N conditional branches shown"},
  "ranking": {"preference": "...", "metric": "...", "direction": "asc|desc",
              "groups": {"candidate": {"count": 0, "ranked": [], "unranked": []},
                         "conditional": {"count": 0, "ranked": [], "unranked": []}},
              "method": "...", "notes": [], "no_winner": true},
  "environment_context": {"status": "available|unavailable",
                          "product": "SPL4SMGP.008", "provider": "NASA SMAP via AppEEARS",
                          "resolution": "9 km EASE-Grid 2.0",
                          "temporal_resolution": "3-hourly",
                          "observations": [], "observation_start": null,
                          "observation_end": null, "retrieved_at": null,
                          "label": "Context only - no effect on status or ranking",
                          "warnings": []},
  "missing_evidence": [],
  "warnings": [{"code": "...", "message": "..."}]
}
```

- Date ranges `{"earliest","latest"}`; numeric ranges `{"min","max"}`.
- Unknown quantities `null`; never 0/NaN/empty string.
- `ranking` references branch IDs only; candidate and conditional groups separate.
- `environment_context` never changes status, checks, or ranking.
- Errors: HTTP 400 `{"schema_version":"1","error":{"code":"INVALID_REQUEST",
  "message":"...","field":"..."}}`; HTTP 500 generic
  `{"schema_version":"1","error":{"code":"INTERNAL_ERROR",
  "message":"Internal server error.","field":null}}`; no stack/credentials.
