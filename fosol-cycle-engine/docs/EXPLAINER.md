# Fosol-Cycle in one page

## What it is

A Rajshahi crop-rotation explorer. It evaluates three-crop paths against calendar,
soil/water, timeline, rotation, diversity, economics, and a historical seasonal
outlook. It is decision support for a prototype, not a recommendation engine, a
weather forecast, or a yield/practice guarantee.

## Real counts (not marketing numbers)

- **Initial screen**, start `2026-11-06`, server initial-wait policy **180 days**,
  transition limit `None`: **0 candidate / 295 conditional / 56 exclusions**.
  `branches` is deliberately empty on the initial screen; the full summary is in
  `branch_summary`, and the message says to select a first crop.
- **Engine smoke**, `max_initial_wait_days=365` and `max_waiting_days=365`:
  **420 branches, 0 candidate / 420 conditional / 15 exclusions**.
- Selected first crop `boro_brri_dhan28` at the same start with the 180-day policy
  returns **42 conditional branches / 8 exclusions** and no candidates.

The difference between 295 and 420 is the initial-wait/transition configuration,
not a change in crop data. A 180-day initial limit excludes the Aman root (246-day
wait); transitions configured at `None` also do not roll future windows. The
420/365/365 smoke is an explicit test configuration, not a scientific maximum.

## The 655..682 example

Branch `b_82899e8d6941` has completion **655..682 days** from the actual fastest and
slowest realized schedules:

- fastest: first planting **2027-07-24**, third harvest **2029-05-09** (655 days);
- slowest: first planting **2027-07-10**, third harvest **2029-05-22** (682 days).

The range is a range because planting and harvest are ranges and the middle crop
has preparation/window timing. The engine ranks completion by the latest (682), and
keeps the earliest date and both realization records visible. It does not average the
endpoints.

## Deliberately unavailable, and why

- **Preparation time:** the crop CSV turnaround cells are blank; no sourced local
  preparation evidence exists. Unknown, never zero. This makes readiness and true
  waiting unknown; the engine shows the next window and a window-only gap instead.
- **Soil/land:** no local district BARC/SRDI pH, texture, drainage, or salinity
  evidence exists. Soil checks stay unknown; the crop CSV text is guidance, not a
  field measurement.
- **Economics:** no sourced farm-gate prices, production costs, cash-flow schedule, or
  validated typical yields. All monetary values are `null`/unavailable, scenarios are
  empty, and cost/return/upfront-cash preferences are unranked with no winner.
  Reference yields are context only and are never multiplied into revenue.
- **§6.2 current-season climate exposure:** deferred. The `climate` check is
  `unknown` with `CLIMATE_EXPOSURE_DEFERRED`; `current_season_climate_exposure` is listed in missing evidence.
- **SMAP:** context display only. It never changes status, checks, or ranking; it is
  unavailable when the token/fetch is missing, and an unavailable context is not zero
  moisture.
- **Warnings:** config-only and all OFF. Wheat is hidden; the audited mustard
  heavy-rain condition is held at the corrected 1/35 rather than enabled.
- **Duration reference:** the CSV does not confirm whether duration starts at sowing
  or transplanting; timing remains conditional.

These gaps are why current data has **0 candidate** branches. Conditional branches
are not recommendations; they are paths that remain inspectable while evidence is
missing.

## Five hardest reviewer questions

1. **“Why are there zero candidates?”** Because local preparation, soil, water
   confirmation, and duration-reference evidence are missing. Unknown evidence never
   becomes an automatic pass; the result is `partial` and conditional only.
2. **“Are these 295/420 branches recommendations?”** No. They are conditional paths,
   ranked only within the conditional group. The candidate group is empty and is not
   invented for display.
3. **“Why can’t I compare costs, returns, or irrigation dependence?”** No sourced
   price, cost, cash-flow, or comparable dependence evidence exists. Reference yields
   are context; the ranking deliberately says `Economic estimate unavailable` or
   `unranked` and `no_winner=true`.
4. **“Does wet SMAP soil mean the crop passes?”** No. SMAP is a separate context block
   and has no effect on checks, status, or ranking; no moisture threshold is validated.
5. **“Is the seasonal outlook a forecast?”** No. It is historical replay labelled
   “based on historical conditions, not a weather forecast”; §6.2 current-season
   climate is deferred, so do not present it as prediction.

## What is safe to claim

- The engine computes deterministic, inspectable branch ranges and rankings from the
  supplied evidence.
- Missing evidence is visible as `null`, `unknown`, `unavailable`, or `unranked`.
- The current output is a **partial evidence** result for Rajshahi, useful for demo
  and review, not a farmer-facing recommendation.
