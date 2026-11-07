# E8 W1 revision review - corner-extreme completion
Verdict: PASS. Bugs: none.
Full suite: `python -X utf8 -m unittest discover -s tests -v`
```text
Ran 270 tests in 1.391s
OK
```
Focused metrics: `Ran 45 tests`, OK.

Verified: `min = H3.earliest - P1.latest`, `max = H3.latest - P1.earliest`; both realizations returned; `range_basis="corner_extremes"`. All 420 real branches are `ok` with `min <= max`; the 57 old-A inversions are valid; `b_82899e8d6941` is 655..682. Property test covers 300 fixed-seed realizations with no fallback. `enumerate_completion_range` matches the corner range and reports `enumeration_used=true`. Reversed ISO ranges are unavailable via `third_harvest_range`; the new synthetic negative-corner case returns `COMPLETION_RANGE_INVALID`. Fastest completion ranks 420 conditional / 0 candidate / 0 unranked, with the overlap note.

Mutation gate (5/5 killed):
| mutation | failing test | hash OK |
|---|---|---|
| min latest -> earliest | `test_known_ranges_use_earliest_and_latest_pairing` | yes |
| max earliest -> latest | `test_known_ranges_use_earliest_and_latest_pairing` | yes |
| property upper bound collapsed | `test_completion_property_300_random_realizations` | yes |
| enumeration fallback bypassed | `test_enumerate_completion_range_matches_corner_extremes` | yes |
| `COMPLETION_RANGE_INVALID` guard removed | `test_negative_corner_min_is_unavailable` | yes |

Restored SHA-256 `B7EC9F7E...`; no mutation remains.
E6 smoke (`2026-11-06`, max 365): 420 branches, 0 candidate / 420 conditional, 15 exclusions.
No E6/E7 source changed; no permanent edits; no commits.
