# astra6_n20-13

**Valid** (no flags). Best Eval AUC **0.6935** (`7cdfba0`), Holdout AUC **0.6906**, gap **-0.0029**.

The highest Eval and Holdout AUC of any minimal3 run so far (before it: astra6_n20-3 with 0.6918 on eval, astra6_n20-9 with 0.6888 on holdout). The gap is ordinary, and every check is clean.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct6`
- Date: 2026-10-06. Driver ran 22:20:05 to 23:27:33 UTC, clock 22:22:04 to 23:22:37 UTC.
- Container `astra6_n20-13`: memory cap 24 GiB (25769803776 bytes), no swap; peak 3708370944 bytes (3.5 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as astra6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for astra6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 79 s: branch `oct6` created, files read, both data files checked, `output/results.tsv` with header; asks for "go" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself, 32 s after the budget ran out |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0.

**No question glossed over.** The agent picked the tag `oct6` itself (no question tool call). Its final message only asked for the go-ahead.

## Results

- 59 rows in results.tsv (baseline + 58 experiments), the most of the group: 27 keep, 32 discard, 0 crash; 59 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6743 → 0.6787 → 0.6792 → 0.6792 → 0.6804 → 0.6821 → 0.6823 → 0.6824 → 0.6825 → 0.6843 → 0.6843 → 0.6845 → 0.6866 → 0.6869 → 0.6869 → 0.6885 → 0.6886 → 0.6886 → 0.6889 → 0.6922 → 0.6924 → 0.6924 → 0.6925 → 0.6933 → 0.6935 → 0.6935
- Best: `7cdfba0` "simplify preparation and define interaction groups once; exact equivalence", Eval 0.6935, Holdout 0.6906 (gap -0.0029; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6725, 0.6772, 0.6776, 0.6776, 0.6792, 0.6800, 0.6804, 0.6809, 0.6808, 0.6830, 0.6831, 0.6832, 0.6849, 0.6850, 0.6848, 0.6864, 0.6869, 0.6869, 0.6872, 0.6900, 0.6900, 0.6901, 0.6901, 0.6906, 0.6906, 0.6906
- Best model: the average of two XGBoost models that boost small forests. Each runs 600 rounds of 4 parallel lossguide trees with 16 leaves at learning rate 0.05, with `colsample_bytree` 0.8 and `max_cat_threshold` 16.
  - One uses `subsample` 0.8 with `reg_lambda` 250 and `reg_alpha` 10; the other `subsample` 0.5 with `reg_lambda` 156.25 and `reg_alpha` 6.25.
  - Interaction constraints keep the calendar features in their own groups (Month with the fortnight; each holiday window alone), apart from the rest.
  - Training weights halve every 12 months back from December (on the training `Month`).

  Inputs:
  - `DayOfWeek`, `UniqueCarrier`, `Origin` and `Dest` as categories, with codes fixed from train; `Distance`
  - `Month` as a number; the fortnight of the year, (day of year − 1) // 14; no `DayofMonth`
  - departure minutes after 5 am (no raw `CRSDepTime`)
  - three holiday windows: Thanksgiving ±7 days, Christmas ±14 days, and the nearest of Memorial Day, July 4 and Labor Day ±4 days. All are computed from the row's month, day and weekday on a fixed 365-day calendar.
- Gains, adding up to +0.0192:
  - 600 depth-4 trees at learning rate 0.05 with regularization: +0.0044
  - without `DayofMonth`: +0.0005
  - month kept additive: +0.0012
  - `max_cat_threshold` 16: +0.0017
  - 4 parallel trees: +0.0002
  - schedule offsets: +0.0001; airport coordinates: +0.0001 (both later removed)
  - holiday windows: +0.0018
  - column sampling: +0.0002
  - `reg_lambda` 100, then 500: +0.0021, +0.0003
  - `Month` as an ordered number: +0.0016
  - lossguide with 16 leaves: +0.0001
  - recency weights: +0.0003
  - **the fortnight of the year: +0.0033, the largest**
  - minutes after 5 am: +0.0002
  - `reg_lambda` 250: +0.0001
  - `reg_alpha` 10: +0.0008
  - the 0.8 / 0.5 subsampling pair: +0.0002
- Seven kept ties, each simpler or faster, as program.md allows:
  - `38bc84b` without redundant category checks: evaluation 31.1 s → 21.1 s
  - `d0d5ebc` cached category codes: evaluation 18.8 s → 5.1 s
  - `5fde1d2` without the airport coordinates; `ca9067d` without the schedule offsets; `b799422` without the raw clock time: each a feature removal
  - `2a49482` without the explicit `min_child_weight` (back to the default). One parameter less in the code, so simpler, though borderline: with 16-leaf lossguide trees it changes little, and timing was unchanged (20.2 s → 20.5 s).
  - `7cdfba0` (the best commit): a refactor of `prepare` and of the interaction groups, checked by the agent to give exactly the same features. Eval and Holdout AUC are the same as `7073db1` before it.

  Equal results that added complexity were discarded (`a154928`, `933e0ed`, `f716fda`).
- Timing (report.txt): total 1h00m32s; XGBoost runs 0h21m54s (36.2%); AI 0h38m38s (63.8%)
- Clock stopped by the agent after 3632 s, **32 s after the 3600 s budget ran out** (not an early stop).
  - The last run (`7cdfba0`) started at 3464 s, with 2m16s left, and ended at 3501 s.
  - A context compaction at 23:21:55 then delayed the wrap-up.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 58 agent commits (branch and reflog) touch only train.py. 59 artifacts for 59 completed runs, all inside the clock. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed each of the 4 commands leak_check lists:
  - setup: `cat` of program.md, README.md, train.py and harness.py, a loop that `cat`s an `AGENTS.md` in `/`, `/home`, `/home/ubuntu` or the repo if one exists (none did), `rg --files --hidden` excluding .git, data and binary files, and `ls -l data/train.csv data/eval.csv`
  - the branch and results header
  - the final verification. Its "No holdout or human data was accessed" is text written to the research log.
- Data reads: only `data/train.csv` (a profile, a 16-row sample for its artifact check). eval.csv was only listed with `ls -l`. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `head` of train.csv in its profile.
- Web: 23 `web__run` calls with 12 searches, 14 opens and 3 finds (some calls combine them). Pages opened:
  - XGBoost docs: parameter tuning, categorical data, interaction constraints, random forests, learning to rank, custom objectives, DART, tree methods, parameters, monotonic constraints
  - scikit-learn cyclical features, Isomap and `VotingClassifier`; pandas `Categorical`; SciPy `shortest_path`
  - AWS SageMaker XGBoost tuning
  - Prophet's documentation on holiday effects (the source of its holiday windows idea)

  No result or page from BTS, Kaggle or S3 appears in the web outputs; no carrier-code mapping. No flight data from elsewhere.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+79 -12).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct6` = the 27 kept commits in results.tsv order; HEAD = `7cdfba0` = last keep.
  - No discarded commit on the branch, nothing of output/ committed, no stray files, and every harness run is logged in results.tsv.
- Kept ties: seven, all simpler or faster (see Results; one borderline), so no `keep_rule`.
- Clock stopped by the agent (`clock_stopped_by` = agent), `clock_remaining_s` -32.
- No retry waits (`retry_wait_s` 0).

## Other notes

- **One context compaction** in the session log at 23:21:55, after the last experiment, during the wrap-up.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- turns/1.err holds only codex's "Reading additional input from stdin..."; turns/2.err is empty.
