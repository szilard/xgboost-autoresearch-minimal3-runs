# astra6_n20-9

**Valid** (no flags). Best Eval AUC **0.6913** (`d1fbdd2`), Holdout AUC **0.6888**, gap **-0.0025**.

The highest Holdout AUC of the group so far (astra6_n20-3 has 0.6886); the second-highest Eval AUC (after 0.6918 in astra6_n20-3).

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct6`
- Date: 2026-10-06. Driver ran 17:49:21 to 18:58:14 UTC, clock 17:52:55 to 18:52:08 UTC.
- Container `astra6_n20-9`: memory cap 24 GiB (25769803776 bytes), no swap; peak 3715276800 bytes (3.5 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as astra6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for astra6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 172 s: branch `oct6` created, files read, both data files checked, train.csv inspected, `output/results.tsv` and the research log started; ends "Say “go” to begin" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0.

**No question glossed over.** In turn 1 the agent called codex's question tool with the single option `oct6`. The tool returned `{"accepted":true}` and the agent went on with `oct6`. Its final message only asked for the go-ahead.

## Results

- 36 rows in results.tsv (baseline + 35 experiments): 18 keep, 18 discard, 0 crash; 36 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6786 → 0.6794 → 0.6794 → 0.6799 → 0.6803 → 0.6807 → 0.6817 → 0.6833 → 0.6845 → 0.6846 → 0.6871 → 0.6874 → 0.6893 → 0.6908 → 0.6910 → 0.6911 → 0.6913
- Best: `d1fbdd2` "Increase operational L2 leaf regularization from 10 to 50", Eval 0.6913, Holdout 0.6888 (gap -0.0025; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6777, 0.6787, 0.6787, 0.6781, 0.6789, 0.6787, 0.6804, 0.6813, 0.6827, 0.6831, 0.6854, 0.6855, 0.6867, 0.6881, 0.6886, 0.6888, 0.6888
- Best model: two XGBoost models stacked through the margin:
  - a **calendar model**: 200 depth-2 trees at learning rate 0.05, `min_child_weight` 200, `reg_lambda` 50, one-hot categories. Its inputs are `Month`, the offset to the nearest holiday within ±7 days, and which holiday it is (New Year, Memorial Day, July 4, Labor Day, Thanksgiving, Christmas), all computed from the row's month, day and weekday. Half its log-odds is the base margin of the second model.
  - an **operational model**: 600 rounds of 4 parallel lossguide trees with 32 leaves at learning rate 0.05, `min_child_weight` 20, `reg_lambda` 50, `subsample` 0.85, `colsample_bynode` 0.85, `max_cat_threshold` 8. Its inputs:
    - `DayOfWeek`, `UniqueCarrier`, `Origin` and `Dest` as categories; `CRSDepTime`, `Distance` and the departure minute
    - two airport coordinates for each end: classical MDS of shortest-path distances over the train route-distance graph
    - the flight's direction between them, divided by its distance

  No `DayofMonth` category. Both models are fitted on train only.
- Gains, adding up to +0.0170:
  - 600 depth-4 trees at learning rate 0.05: +0.0043
  - without `DayofMonth`: +0.0008
  - `max_cat_threshold` 8: +0.0005
  - depth 6: +0.0004
  - departure minute: +0.0004
  - month kept additive with interaction constraints: +0.0010
  - one-hot categorical splits: +0.0016
  - airport coordinates: +0.0012
  - 4 parallel trees: +0.0001
  - holiday type and offset: +0.0025
  - flight direction: +0.0003
  - a separate calendar model with the operational forest boosted on top: +0.0019
  - the calendar log-odds at half strength: +0.0015
  - lossguide with 32 leaves: +0.0002
  - without the weakest coordinate axis: +0.0001
  - `reg_lambda` 50: +0.0002
- One kept tie, faster code, as program.md allows: `a50cfe7` "simplify categorical conversion with identical features", evaluation 27.1 s → 16.7 s. Results equal to the best that added complexity were discarded (`c253c99`, `2083555`, `7589ee3`, `d4f8c6d`).
- Like runs 1, 3, 4, 5, 7 and 8, holiday features gave one of the largest gains (+0.0025).
- Timing (report.txt): total 0h59m14s; XGBoost runs 0h18m54s (31.9%); AI 0h40m19s (68.1%)
- Clock stopped by the agent after 3554 s, 46 s of the 3600 s budget left (not an early stop). The last run (`d1fbdd2`) ended at 3508 s. Final summary written in the research log.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 35 agent commits (branch and reflog) touch only train.py. 36 artifacts for 36 completed runs, all inside the clock. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed each of the 14 commands leak_check lists:
  - setup: `rg --files` limited to docs and config, `cat` of program.md, README.md, .gitignore, train.py and harness.py, `ls -la`, `ls -lh data/train.csv data/eval.csv`, the branch and the results header
  - web calls (below) run together with status polls
  - result loggings with its stored record helper
  - a final re-read of program.md and parts of harness.py
- Data reads: only `data/train.csv` (a profile, samples for its artifact checks). eval.csv was only listed with `ls -lh`. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `head` of train.csv.
- Web: 25 `web__run` calls with 9 searches, 12 opens and 4 finds (some calls combine them). Pages opened:
  - XGBoost docs: parameter tuning, parameters, categorical data, interaction constraints, random forests, learning to rank, intercept, monotonic constraints, tree methods
  - AWS SageMaker XGBoost tuning
  - scikit-learn cyclical features and TargetEncoder; SciPy `shortest_path`
  - papers: arXiv 2408.02802 and 2006.10858, the CatBoost NeurIPS paper, Microsoft's KDD 2012 paper on intelligible models
  - **one BTS page**, `bts.gov/topics/airlines-and-airports/increase-regional-air-travel-during-thanksgiving`: a 2019 newsroom item on estimated passengers during the 2018 Thanksgiving period (2.03 million per day; ATL and ORD the busiest). No flight records and nothing about 2005 or 2006.
  - The search before it (`site.bts.gov Thanksgiving holiday air travel delays`, plus one on faa.gov) returned snippets of the TranStats holiday-delay pages with empty filters, FAA and AP news items, and BTS reports. They carried the line "America West (merged into US Airways starting January 2006)". This run did not use it: no train.py version touches carrier codes.
  - "Holdout TS" was a `find` pattern in the CatBoost paper (its name for a target statistic), not a reference to the holdout set.

  No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+107 -13).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct6` = the 18 kept commits in results.tsv order; HEAD = `d1fbdd2` = last keep.
  - No discarded commit on the branch, nothing of output/ committed, no stray files, and every harness run is logged in results.tsv.
- Kept tie: one, faster code (see Results), so no `keep_rule`.
- Clock stopped by the agent (`clock_stopped_by` = agent), 46 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- **One context compaction** in the session log at 18:50:27, during the wrap-up, after the last experiment.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- turns/1.err holds only codex's "Reading additional input from stdin..."; turns/2.err is empty.
