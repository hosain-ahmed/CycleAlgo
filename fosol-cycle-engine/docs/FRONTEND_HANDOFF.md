# Frontend handoff — Fosol-Cycle explore API

This is the practical contract for a web developer. The frozen schema is in
`docs/CONTRACT.md`; this page explains how to run it and how to render every state.

## 1. Start the development server

Run from `Q:\CycleAlgo\fosol-cycle-engine`:

```powershell
python -X utf8 -m src.server --host 127.0.0.1 --port 8000
```

The server loads `..\Data\fosol_cycle_rajshahi_crop_dataset.csv` by default. Override
with `--data-dir Q:\CycleAlgo\Data` if needed.

Health check:

```powershell
curl.exe -s http://127.0.0.1:8000/health
# {"status": "ok"}
```

Working explore call (initial screen, no first crop selected):

```powershell
curl.exe -s -X POST http://127.0.0.1:8000/api/explore `
  -H "Content-Type: application/json" `
  --data-binary "@examples/example_request_initial.json"
```

Selected-first-crop call:

```powershell
curl.exe -s -X POST http://127.0.0.1:8000/api/explore `
  -H "Content-Type: application/json" `
  --data-binary "@examples/example_request.json"
```

The bare development server has **no live POWER or SMAP calls**. It uses the local
crop profiles, so `outlook.status` is `unavailable`, `environment_context` is
`unavailable` (with a warning), and responses are `partial`. A host application can
supply `environment` and `smap_context` to `src.explore.explore`; the server wrapper
does not. `examples/example_response_smap_context.json` is the synthetic-context
example for that integration.

CORS: the server allows only `http://localhost:<port>` and
`http://127.0.0.1:<port>` for its own port. Serve the frontend from the same origin
or use a dev proxy; a separate frontend port will be blocked.

Request body limit is 64 KiB. `Content-Type` must be `application/json`.
Errors: invalid input → HTTP 400; oversized body → 413; wrong type → 415; internal
failure → HTTP 500 with a generic body and no stack or credentials.

## 2. Request fields

| Field | Required | Allowed values / default | Meaning |
|---|---|---|---|
| `district_id` | yes | `"rajshahi"` today; any non-empty string is shape-valid | Stable district ID. Only Rajshahi is evaluated; `dhaka` returns `unsupported_district`, not fabricated results. |
| `start_date` | yes | `YYYY-MM-DD` | Local agricultural start date. |
| `first_crop_id` | yes (key must exist) | `null` or an existing crop ID | `null` = initial screen; selected ID = return only branches rooted at that crop. |
| `water_access` | no | `rainfed`, `irrigation_available`, `unknown`; default `unknown` | User scenario, not a measurement. Unknown means “not confirmed”, not irrigation. |
| `preference` | no | `fastest_completion`, `lowest_total_cost`, `least_irrigation_dependence`, `highest_net_return`, `more_crop_diversity`; default `fastest_completion` | Ranking preference. `lowest_upfront_cash` is rejected until a sourced cash-flow schedule exists. |

Unknown extra keys are ignored. Invalid enums, missing required keys, or a bad date
return the E2 error shape with an HTTP status.

## 3. Response fields (top level)

| Field | Meaning | Null / absence |
|---|---|---|
| `schema_version` | Contract version string, currently `"1"`. | Never null. |
| `generated_at` | UTC ISO timestamp for this response. | Never null. |
| `request` | Effective request after defaults, including `max_initial_wait_days` and `max_waiting_days`. | Never null. |
| `status` | `ok`, `partial`, `no_supported_options`, `unsupported_district`, `data_unavailable`. | Never null. Invalid input is HTTP 400, not a success status. |
| `district` | `district_id`, `display_name`, `supported`, `geographic_scope`. | Unsupported district has `supported=false`, display name = ID, scope `not evaluated`. |
| `assumptions` | Array of `{code, message}` product assumptions. | May be empty for unsupported/data-unavailable. |
| `data_sources` | Array of `{source_id, provider, product, version, coverage, retrieved_at}`. | `retrieved_at` may be null; missing provider metadata uses a documented fallback. |
| `crop_options` | One option per profile with `crop_id`, names, variety, `status`, `shown`, `initial_wait_days`, `checks`, reasons/missing/sources. | Empty for unsupported district/data unavailable. Unsupported options have `shown=false`. |
| `branches` | Selected-crop branches (3 crops, 2 transitions) with metrics and outlook. | Empty on the initial screen, no options, unsupported district, and data unavailable. |
| `branch_summary` | `candidate_count`, `conditional_count`, `excluded_count`, `no_candidate_branches`, `message`. | Counts are never null; message is never null. |
| `ranking` | `preference`, `metric`, `direction`, `groups`, `excluded`, `method`, `notes`, `no_winner`. | Groups always present; ranked/unranked arrays may be empty. |
| `environment_context` | SMAP context: product/provider/resolution/temporal resolution/observations/start/end/retrieved/label/status/warnings. | `observations=[]`, dates/retrieved null, status `unavailable` + warning when not supplied. |
| `missing_evidence` | Sorted IDs such as `preparation_time`, `crop_water_demand_evidence`, `current_season_climate_exposure`. | May be empty. |
| `warnings` | Array of `{code, message}`. | May be empty. |

## 4. Crop options and checks

Each option:

- `crop_id`, `name_en`, `name_bn`, `reference_variety`.
- `status`: `candidate`, `conditional`, or `unsupported`.
- `shown`: false for unsupported options; hide or show disabled with the reason.
- `initial_wait_days`: days from `start_date` to the first documented planting
  window; **null** if no dated window is available, **0** only when already open.
- `checks.calendar`, `checks.climate`, `checks.soil`, `checks.water`,
  `checks.rotation`: each `{status, code, reason, source_ids}` with calendar/check
  details. `rotation` is null for the first crop because rotation starts at crop 2.
- `reasons`, `missing_evidence`, `source_ids`: human reasons, machine IDs, and
  evidence references.

`checks.climate` is `unknown` with `CLIMATE_EXPOSURE_DEFERRED`; §6.2 is not applied.
Soil is `unknown` without local evidence; water is caution/unknown and may say
“Irrigation confirmation required.” Do not turn a missing/unknown check into a pass.

## 5. Branches, crop nodes, and transitions

Branch: `branch_id`, `status` (`candidate|conditional`), `initial_wait_days`,
`crops` (exactly 3), `transitions` (exactly 2), `reasons`, `cautions`,
`missing_evidence`, `source_ids`, `metrics`, `outlook`.

Crop node: `position` 1–3, `crop_id`, names, `family`, `establishment_method`,
`status`, `checks`, `rotation` (null at position 1), `planting_range`,
`harvest_range`, `preparation_range`, `ready_range`, `duration`,
`timing_status`/`timing_code`/`timing_codes`, `nursery_age_days`,
`nursery_age_added`, reasons/cautions/missing/sources, and per-crop `outlook`.

Transition:

- `from_position`/`to_position`, `from_crop_id`/`to_crop_id`.
- `reference_date`, `reference_basis` (earliest ready or earliest harvest when prep
  unknown), `window` (preferred start/end, supported late end, window start,
  reference date, source IDs).
- `preparation_range` (null when unknown), `preparation_known`.
- `next_planting_range`, `next_planting` `{status, code, reason, timing_basis,
  timing_status, latest_clipped}`.
- `waiting_range` (null when prep/readiness unknown), `total_interval_range_days`
  (null when prep/readiness unknown).
- `harvest_to_next_window_days` `{min,max}`: calendar gap from harvest to the next
  planting window. This is **not** field-ready waiting.
- `window_only_gap`: true when the gap is only a window gap because preparation is
  unknown.
- `waiting_limit_status`: `within`, `partial`, `exceeds`, `not_configured`, or
  `unknown`; corresponding `waiting_limit` object has limit/basis/reason.
- `latest_invalid`: true when the latest realization was clipped below latest
  readiness/harvest; then waiting/total `max` are null.
- `calendar_check`, `window_reference_check`, reasons/cautions/missing/sources.

## 6. Metrics and outlook

`metrics.completion`: `status`, `completion_days` `{min,max}`,
`earliest_completion_date`, `latest_completion_date`, `ranking_value_days` (max),
`basis`, `range_basis`, `min_realization`/`max_realization` with P1/H1/P2/H2/P3/H3,
source ranges, overlap note, reasons/missing, `enumeration_used`.

`metrics.resources`:

- `cash_cost`: unavailable, `value_bdt_per_ha:null`.
- `irrigation`: `context_only`, `ranking_status:"unranked"`, per-crop guidance/FAO/
  phase/readiness, `total:null`, missing/reason.
- `labor`, `equipment`: unavailable, `value:null`, missing/reason.

`metrics.economics`: `status:"unavailable"`, `reason:"Economic estimate unavailable."`,
`scenarios:[]`, four monetary metrics with `value_bdt_per_ha:null`, reference-yield
context (`static_reference_not_used`), price evidence with `price_value:null`, and
missing IDs. Never invent a price, yield, cost, or revenue.

`metrics.diversity`: status, `distinct_family_count`, `families`,
`family_repeat_count`, `legume_present`/`legume_crop_ids`, legume note, basis, and
“not a measured soil-health ranking” note. Missing family/legume evidence is unknown,
not zero/false.

`outlook`: `status` (`ok|partial|unavailable`), `label` exactly
`Seasonal outlook — based on historical conditions, not a weather forecast.`,
`indicators`, and reason when unavailable; when environment is supplied it also has
`per_crop`. Each indicator has `indicator`, `status`, `definition` (variable,
statistic, coverage rule, unit, statistics), `period`, `sample`, `coverage`, `stats`
(null when unavailable), `notes`, and `source_ids`. It is historical context, not a
forecast. With the bare server/POWER absent it is `unavailable` and `indicators=[]`.

## 7. Ranking, summary, and warnings

`ranking.groups.candidate` and `.conditional` each have `count`, `ranked`, and
`unranked`. Ranked entries contain `branch_id`, `status`, `metric_value`, relevant
metric fields, reasons/cautions. Unranked entries have `metric_value:null`, a reason,
and missing evidence. `ranking.excluded` lists blocked branch IDs; `no_winner`,
`method`, and `notes` explain the outcome. Candidate and conditional groups must never
be merged. Economic/irrigation preferences are unranked with `no_winner=true`.

`branch_summary.message` already says when there are no candidate branches. Show it;
do not infer a candidate from a conditional branch.

`environment_context` is a separate SMAP context block. `status` is available or
unavailable; the label is always “Context only - no effect on status or ranking”.
Show observations if available; show the warning if unavailable. It never changes
checks, status, or ranking.

## 8. UI states

| State | Detection | Render |
|---|---|---|
| `ok` | `status:"ok"` | Show candidate ranking; current data is not this state. |
| `partial` | `status:"partial"` | Show results plus warnings and missing evidence. Current data is 0 candidate / conditional only. |
| No candidates | `branch_summary.no_candidate_branches=true`, candidate 0, conditional > 0 | Show “No candidate branches — N conditional branches shown”; conditional is not recommended. |
| No options | `status:"no_supported_options"`, no branches, counts 0 | Show no supported options; do not invent a crop/path. |
| Unsupported district | `status:"unsupported_district"` | Show that only Rajshahi is supported; no crop results. |
| Invalid input | HTTP 400 `{schema_version,error:{code,message,field}}` | Show the field/message; do not render a success envelope. |
| Data unavailable | `status:"data_unavailable"` | Show that crop data/profiles are unavailable; no results. |
| SMAP context | `environment_context.status` | Show separately; unavailable warning is not zero moisture and does not change the decision. |

If `outlook.status` is unavailable, show the reason; never label it a forecast.

## 9. Comparison table and timeline fields

- **Initial wait:** `branches[].initial_wait_days` (and `crop_options[]`). Ranking
  entries include `initial_wait_days`; use it directly. Always show it next to
  completion so a fast finish cannot hide a long start delay.
- **Completion:** `metrics.completion.completion_days` and
  `ranking_value_days` (max). Show the range, not only the max; use
  `earliest/latest_completion_date` and the overlap note.
- **Preparation:** `crops[].preparation_range`; null = unknown, never zero.
- **Waiting:** `transitions[].waiting_range`; null when readiness is unknown.
- **Window-only gap:** `transitions[].harvest_to_next_window_days` with
  `window_only_gap:true`; label it “window gap”, not “waiting”.
- **Total interval:** `transitions[].total_interval_range_days`; null when
  preparation/readiness is unknown.
- **Next planting:** `next_planting_range` and `next_planting` status/basis; do not
  claim the crop follows on time when prep is unknown.
- **Limits:** `waiting_limit_status` and `waiting_limit`; `partial`/`exceeds` are not
  complete approvals.
- **Metrics:** completion, resources, economics, diversity; render unavailable
  metrics as unavailable, not zero.
- **Ranking:** separate candidate/conditional groups; unranked entries stay
  unranked; no weighted score exists.

## 10. Must-nots

1. Never render an unknown/null value as zero, “none”, or a favorable default.
   `initial_wait_days=0` is valid only when the window is already open.
2. Never describe a conditional branch as a candidate or recommended option.
3. Never hide the initial wait, preparation gap, waiting interval, or window-only
   gap; do not call a window-only gap a field-ready waiting interval.
4. Never imply SMAP context changed a check, status, or ranking.
5. Never imply the seasonal outlook is a forecast; it is historical replay.
   Also do not invent economic values or rank an unranked metric.

## 11. Examples and checking

Run:

```powershell
python scripts/contract_check.py examples/example_response.json
python scripts/contract_check.py examples/example_error_invalid_input.json --error
```

Small-state examples: `example_response_unsupported_district.json` (dhaka),
`example_response_no_options.json` (Aman selected at the 180-day initial limit),
`example_response_data_unavailable.json` (empty profiles),
`example_error_invalid_input.json` (bad start date), and
`example_response_smap_context.json` (synthetic context, one-branch cap). Status and
ranking in the SMAP file are identical to the unavailable-context response; only the
context block and source metadata differ.

The shipped `example_response.json` and `example_response_smap_context.json` are
trimmed to one branch with `config.max_branches=1` for handoff size; a live Boro
selection returns 42 branches. The fuller handoff sample is
`example_response_first_crop_selected.json` (selected Boro, `config.max_branches=10`,
10 conditional branches); `examples/example_request_first_crop_selected.json`
documents that request.

The SMAP examples use the cached real AppEEARS task result
`tests/fixtures/appeears_spl4smgp_rajshahi_20250101_20250103.csv` (24 observations,
2025-01-01..03 UTC); no live token is needed.
