# astra6_n20-10

**Valid** (no flags). Best Eval AUC **0.6878** (`0d30a13`), Holdout AUC **0.6845**, gap **-0.0033**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct6`
- Date: 2026-10-06. Driver ran 18:58:27 to 20:05:01 UTC, clock 19:00:30 to 20:00:11 UTC.
- Container `astra6_n20-10`: memory cap 24 GiB (25769803776 bytes), no swap; peak 3714228224 bytes (3.5 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as astra6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for astra6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 81 s: branch `oct6` created, files read, both data files checked, `output/results.tsv` with header; ends "say **go** to start" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0.

**No question glossed over.** The agent picked the tag `oct6` itself (no question tool call). Its final message only asked for the go-ahead.

## Results

- 45 rows in results.tsv (baseline + 44 experiments): 20 keep, 25 discard, 0 crash; 45 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6743 → 0.6759 → 0.6771 → 0.6796 → 0.6800 → 0.6801 → 0.6810 → 0.6815 → 0.6824 → 0.6827 → 0.6858 → 0.6863 → 0.6866 → 0.6866 → 0.6868 → 0.6873 → 0.6874 → 0.6875 → 0.6878
- Best: `0d30a13` "extend Christmas lead-up from 7 to 14 days", Eval 0.6878, Holdout 0.6845 (gap -0.0033; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6725, 0.6762, 0.6752, 0.6772, 0.6776, 0.6778, 0.6783, 0.6782, 0.6799, 0.6802, 0.6828, 0.6835, 0.6839, 0.6839, 0.6838, 0.6839, 0.6840, 0.6844, 0.6845
- Best model: one XGBoost model that boosts a small forest. It runs 400 rounds of 3 parallel depth-8 trees at learning rate 0.05, with `min_child_weight` 30, `reg_lambda` 20, `reg_alpha` 5, `subsample` 0.8 and `colsample_bytree` 0.85. Categorical splits are one level at a time (`max_cat_to_onehot` 20000). Inputs:
  - categories: `Month`, `DayOfWeek`, `UniqueCarrier`, `Origin`, `Dest`, plus the route, carrier-origin and carrier-destination pairs, with levels fixed from train; no `DayofMonth`
  - `CRSDepTime` and `Distance`; departure minutes after 4 am and their sine / cosine; an arrival-clock proxy (departure + 30 min + distance / 8) with its sine / cosine
  - holiday offsets for Thanksgiving, Christmas (from 14 days before), New Year and July 4, each within a window around the day and missing outside it. They are computed from the row's month, day and weekday.
  - three airport coordinates per end and the direction between them (classical MDS of shortest-path distances over the train route-distance graph)
  - each airport's shortest-path distance to five landmark airports (ATL, ORD, DFW, LAX, JFK), from the same train graph
- Gains, adding up to +0.0135:
  - without `DayofMonth`: +0.0016
  - one-level categorical splits: +0.0012
  - 400 trees at learning rate 0.05: +0.0025
  - `min_child_weight` 30: +0.0004
  - route category: +0.0001
  - carrier-airport categories: +0.0009
  - depth 8: +0.0005
  - airport coordinates and direction: +0.0009
  - L2 20: +0.0003
  - holiday offsets: +0.0031, the largest
  - row and column sampling: +0.0005
  - 3 parallel trees: +0.0003
  - clock features: +0.0002
  - landmark distances: +0.0005
  - L1 5: +0.0001
  - arrival-clock proxy: +0.0001
  - longer Christmas lead-up: +0.0003
- Two kept ties, both faster code, as program.md allows:
  - `e130f87` simpler category preparation: evaluation 30.8 s → 10.2 s
  - `8af0d94` direct fitted category codes: evaluation 15.2 s → 9.1 s, and 8.9 to 9.2 s in the runs after it

  Equal results that added complexity or time were discarded (`940a0b7`, `c1cda88`, `29377e1`, `9c795e7`, `8bb5af6`, `94196b7`, `583572a`).
- Unlike most runs of the group, this one kept high-cardinality crosses (route, carrier-origin and carrier-destination) with one-level splits and depth-8 trees.
- Timing (report.txt): total 0h59m41s; XGBoost runs 0h18m02s (30.2%); AI 0h41m39s (69.8%)
- Clock stopped by the agent after 3581 s, 19 s of the 3600 s budget left (not an early stop). The last run (`292bb6a`) ended at 3506 s. The agent saw 1m28s left, started nothing new and wrapped up.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 44 agent commits (branch and reflog) touch only train.py. 45 artifacts for 45 completed runs, all inside the clock. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed each of the 4 commands leak_check lists:
  - setup: `rg --files` limited to docs and config, `cat` of train.py and harness.py, `ls -l data/train.csv data/eval.csv`
  - two result loggings
  - the final one includes "No additional evaluation metric or holdout access was used", text written to the research log
- Data reads: only `data/train.csv` (a profile, a 64-row sample for its artifact checks). eval.csv was only listed with `ls -l`. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `head` of train.csv in its profile.
- Web: 19 `web__run` calls with 11 searches, 7 opens and 3 finds (some calls combine them). Pages opened:
  - XGBoost docs: parameter tuning, categorical data, parameters (twice), monotonic constraints, interaction constraints, custom objectives, tree methods
  - the scikit-learn cyclical-features example
  - the UC Berkeley iSchool flight-delay page, which failed to load ("Internal Error")

  Searches covered XGBoost and scikit-learn docs, arXiv (wide & deep, label smoothing, MVS), concept drift, and OPM's federal holidays. No result or page from BTS, Kaggle or S3 appears in the web outputs. No flight data from elsewhere.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+93 -10).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct6` = the 20 kept commits in results.tsv order; HEAD = `0d30a13` = last keep.
  - No discarded commit on the branch, nothing of output/ committed, no stray files, and every harness run is logged in results.tsv.
- Kept ties: two, both faster code (see Results), so no `keep_rule`.
- Clock stopped by the agent (`clock_stopped_by` = agent), 19 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- No context compaction in the session log.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- turns/1.err holds only codex's "Reading additional input from stdin..."; turns/2.err is empty.
