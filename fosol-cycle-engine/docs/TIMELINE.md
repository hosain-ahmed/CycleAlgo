# Timeline, Preparation, Waiting, and Branches (E6)

Source: `v1.md` §10, §11, §17.6-8, §17.12. Code: `src/timeline.py`,
`src/rotation.py`, `src/branch_expander.py`. Tests: `tests/test_timeline.py`,
`tests/test_rotation.py`, `tests/test_branch_expander.py`.

## Duration stage is an assumption

The crop CSV records variety duration min/max but not whether the clock starts
at sowing or transplanting. `duration_reference_verified` defaults to `False`,
so known durations stay `conditional` / `DURATION_REFERENCE_UNRESOLVED`.
Aman and Boro are transplanted; their `seedling_age_*` values are reported but
never added to variety duration (`NURSERY_AGE_NOT_ADDED`, `nursery_age_added=false`).

## Preparation is unknown until supplied

All eight `turnaround_days_min/max` cells are blank and
`turnaround_rule_status=VALIDATION_REQUIRED`. The engine never reads those
fields. `preparation` / `preparation_lookup` is the only source:
`{"min_days", "max_days", "source_ids"}`. `None` leaves preparation and
readiness `None` with `PREPARATION_EVIDENCE_MISSING`; it is never zero.
An explicit `0` is a valid immediate-readiness assumption.

## Formulas

```text
harvest earliest = planting earliest + duration_min
harvest latest   = planting latest   + duration_max
ready earliest   = harvest earliest  + prep_min
ready latest     = harvest latest    + prep_max
next earliest    = max(ready earliest, window start)
next latest      = max(ready latest,   window start)
waiting          = next planting - ready
total interval   = next planting - harvest
```

The next range is clipped at the documented supported-late end and the clip is
reported (`NEXT_PLANTING_LATEST_CLIPPED`). A clipped latest cannot create a
negative waiting interval. When preparation is unknown, the next planting range
is the crop window only (`timing_basis=window_only_preparation_unknown`); the
engine does not claim the crop follows on time.

## Waiting limit is product policy

`max_waiting_days` has no default numeric value. `None` gives
`waiting_limit_status=not_configured`; `within` is inclusive, `partial` means
only part of the range exceeds it, and `exceeds` excludes the path. The limit is
a product relevance cutoff, not a sourced agronomic maximum or a claim that
longer fallow is unsafe.

## Rotation scope

Same-family repetition is `caution` / `SAME_FAMILY_REPEAT`; a family change is
`pass` / `FAMILY_DIVERSIFIED`. Neither is proof of disease control, soil-carbon
improvement, or nitrogen balance. Legume presence is potential BNF, not a
guaranteed nitrogen credit. The CSV text is advisory (`rule_machine_readable=false`)
and never blocks a branch. Only the two transitions inside the three-crop path
are evaluated: the third-to-first transition is outside v1 scope and is not
claimed as a validated repeatable rotation.

## Branch uniqueness

`expand_branches` adds `uniqueness`: `branch_count`, `branch_ids_unique`,
`duplicate_branch_ids`, `sequence_count`, `duplicate_sequences` (each with
`crop_ids`, `branch_ids`, `window_keys`) and the §14.4 rule. The same crop
sequence with different ordered windows is two branches; duplicate branch IDs
are a hard failure. Duplicate sequences are reported, never collapsed.
