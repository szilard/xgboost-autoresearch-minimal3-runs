# astra6_n20-3

**Valid** (no flags). Best Eval AUC **0.6918** (`43097e4`), Holdout AUC **0.6886**, gap **-0.0032**.

The highest Eval and Holdout AUC of the group so far.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct6`
- Date: 2026-10-06. Driver ran 11:03:46 to 12:10:59 UTC, clock 11:05:55 to 12:05:33 UTC.
- Container `astra6_n20-3`: memory cap 24 GiB (25769803776 bytes), no swap; peak 3626672128 bytes (3.4 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as astra6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for astra6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 88 s: branch `oct6` created, files read, both data files checked, `output/results.tsv` with header; ends "say **go** when ready" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0.

**No question glossed over.** The agent picked the tag `oct6` itself (no question tool call). Its final message only asked for the go-ahead.

## Results

- 50 rows in results.tsv (baseline + 49 experiments): 24 keep, 26 discard, 0 crash; 50 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6759 → 0.6759 → 0.6793 → 0.6822 → 0.6826 → 0.6831 → 0.6833 → 0.6848 → 0.6874 → 0.6880 → 0.6882 → 0.6888 → 0.6889 → 0.6898 → 0.6901 → 0.6904 → 0.6905 → 0.6907 → 0.6913 → 0.6915 → 0.6915 → 0.6915 → 0.6918
- Best: `43097e4` "Require stronger gain for approximate logistic tree splits", Eval 0.6918, Holdout 0.6886 (gap -0.0032; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6762, 0.6762, 0.6788, 0.6803, 0.6807, 0.6801, 0.6802, 0.6819, 0.6838, 0.6843, 0.6843, 0.6849, 0.6853, 0.6860, 0.6866, 0.6874, 0.6877, 0.6880, 0.6880, 0.6879, 0.6881, 0.6881, 0.6886
- Best model: the average of two XGBoost models trained on the same features and weights:
  - a classifier: 600 rounds at learning rate 0.04, `approx` tree method, lossguide with 32 leaves, `min_child_weight` 100, `reg_lambda` 50, gamma 5, `subsample` 0.8, `colsample_bytree` 0.7, `max_cat_threshold` 8
  - a squared-error regressor with the same settings except `hist`, `min_child_weight` 400, `reg_lambda` 200 and gamma 0; its prediction is clipped to [0, 1]

  Training weights: a recency weight with a six-month half-life on the training `Month`, times class balancing within each training month. Inputs:
  - `DayOfWeek` and `UniqueCarrier` as categories; `Distance`
  - no `Origin` or `Dest` category. Instead, each airport gets its shortest-path network distance to six landmark airports (ATL, ORD, DFW, DEN, LAX, JFK), plus its typical route mileage and the flight's distance relative to it. All are computed from the train route-distance graph only.
  - departure time as minutes after 5 am and as sine / cosine
  - month as sine / cosine; no `Month` or `DayofMonth` category
  - days since and until the nearest holiday (New Year, Memorial Day, July 4, Labor Day, Thanksgiving, Christmas), capped at 7. They are computed from the row's month, day and weekday on a fixed 365-day calendar.
- Gains, adding up to +0.0175:
  - without `DayofMonth`: +0.0016; without `Month`: +0.0029
  - shallow, regularized 600-round boosting: +0.0034
  - departure-time features, partition limit, without the minute: +0.0004, +0.0005, +0.0002
  - airport geography: +0.0015, then in place of the airport categories: +0.0026
  - recency weights: +0.0006; monthly class balance: +0.0002
  - holiday proximity: +0.0006
  - stronger regularization: +0.0001
  - month sine / cosine: +0.0009
  - lossguide, feature sampling, more leaves: +0.0003, +0.0003, +0.0001
  - logistic + squared-error blend: +0.0002
  - typical route mileage: +0.0006
  - `approx`: +0.0002
  - gamma 5: +0.0003
- Three kept ties, each simpler or faster, as program.md allows:
  - `8652e1e` simplified category preparation: evaluation 26.9 s → 10.5 s
  - `8fe9d77` removed the redundant raw and hourly departure-time columns
  - `c47dcbd` fitted category code maps: evaluation 11.2 s → 9.0 s, features checked identical by the agent

  Results equal to the best that added complexity were discarded (`782b2b3`, `67d85fe`).
- Like astra6_n20-1, and unlike astra6_n20-2, holiday features helped here.
- Timing (report.txt): total 0h59m38s; XGBoost runs 0h16m09s (27.1%); AI 0h43m28s (72.9%)
- Clock stopped by the agent after 3578 s, 22 s of the 3600 s budget left (not an early stop). The last run (`43097e4`) ended 83 s before the budget ran out. Final summary written in the research log.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 49 agent commits (branch and reflog) touch only train.py. 50 artifacts for 50 completed runs, all inside the clock. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed each of the 6 commands leak_check lists:
  - setup: `cat` of program.md, README.md, .gitignore, train.py and harness.py, `rg --files --hidden` excluding .git and data, and `ls -l data/train.csv data/eval.csv`
  - three inspections of its own artifacts, found with a `glob` in `artifacts/` (split gains, trees)
  - the final verification. It mentions "the unseen holdout remains the human's independent check" in text written to the research log.
- Data reads: only `data/train.csv` (a profile with delay rates by month, day, weekday and carrier; samples for its artifact checks). eval.csv was only listed with `ls -l`. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `train.head(8)` of train.csv.
- Web: 28 `web__run` calls with 11 searches, 14 opens and 4 finds (some calls combine them). Pages opened:
  - XGBoost docs: parameter tuning, parameters, interaction constraints, random forests, learning to rank, DART, custom objectives, tree methods
  - pandas `Categorical` and scikit-learn docs: cyclical features, TargetEncoder, voting ensembles
  - SciPy `least_squares`
  - papers: CatBoost (arXiv 1706.09516), Friedman's stochastic gradient boosting, label smoothing (PMLR), arXiv 1811.12803
  - a Google Research blog post on concept drift
  - the UC Berkeley iSchool flight-delay project page, which failed to load ("Internal Error")

  Searches included OPM's federal holiday rules and two general flight-delay-feature searches. No result or page from BTS, Kaggle or S3 appears in the web outputs. No flight data from elsewhere.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+94 -12).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct6` = the 24 kept commits in results.tsv order; HEAD = `43097e4` = last keep.
  - No discarded commit on the branch, nothing of output/ committed, no stray files, and every harness run is logged in results.tsv.
- Kept ties: three, all simpler or faster (see Results), so no `keep_rule`.
- Clock stopped by the agent (`clock_stopped_by` = agent), 22 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- **One context compaction** in the session log at 11:57:04, 51 minutes into the clock. The agent carried on normally afterwards: 8 more experiments, the logs consistent, and the wrap-up done.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- turns/1.err holds only codex's "Reading additional input from stdin..."; turns/2.err is empty.
- The gap of -0.0032 is the largest of the group so far, but it is well inside the -0.006 threshold.
