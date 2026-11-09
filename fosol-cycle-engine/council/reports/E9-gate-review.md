# E9 gate review (final)

**Verdict: PASS.**
Full suite: `Ran 310 tests in 8.631s`, `OK`. Demo: PASS.
Examples: 9/9 PASS (2 requests, 6 responses, 1 error).
Source unchanged since the 5/5 mutation run: `explore.py F4DD...6036`, `branch_metrics.py 45DA...DD81`, `calendar_evaluator.py 44A9...8BEF`, `test_explore.py 5DAF...3CFC`, `test_branch_expander.py FDC5...6EB5`, `demo_check.py 7179...4DE6`, `contract_check.py D73A...07ED`.
Verified: request limits `180`/`None` on initial/selected/unsupported/data_unavailable; ranking `initial_wait_days` matches branch values; climate checks and `current_season_climate_exposure` present in applicable responses; examples include request limit fields and ranking waits.
Mutations: 5/5 killed (status, null->0, no-candidate message, SMAP isolation, initial-wait 179); hashes restored.
No source/test/example edits or commits; pre-existing `branch_metrics.py`/`v1.md` diffs remain.
