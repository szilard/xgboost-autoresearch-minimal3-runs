# astra6_n20-17

**Valid** (no flags). Best Eval AUC **0.6898** (`a567151`), Holdout AUC **0.6872**, gap **-0.0026**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct7`
- Date: 2026-10-07. Driver ran 02:48:49 to 03:53:24 UTC, clock 02:50:44 to 03:49:26 UTC.
- Container `astra6_n20-17`: memory cap 24 GiB (25769803776 bytes), no swap; peak 3646160896 bytes (3.4 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as astra6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for astra6_n20-1
- I launched this run about 2 minutes late. I reviewed astra6_n20-16 before starting it, which the skill's order doesn't allow, and started it at 02:48:49 after run 16's container was deleted at 02:46:30. The run itself is driven the same way as all others.

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 71 s: branch `oct7` created, files read, both data files and the imports checked, `output/results.tsv` and the research log started; ends "say **go** to begin" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0.

**No question glossed over.** The agent picked the tag `oct7` itself (no question tool call). Its final message only asked for the go-ahead.

## Results

- 46 rows in results.tsv (baseline + 45 experiments): 17 keep, 28 discard, 1 crash; 46 harness runs, 45 ok and 1 training timeout
- The crash: `82d8241` (DART tree dropout) hit the 60 s training limit. The agent logged it as `crash` and reset to the best commit. Its next experiment ran DART within budget (250 rounds at rate 0.1: 0.6833, discarded).
- Kept Eval AUC: 0.6743 → 0.6793 → 0.6825 → 0.6825 → 0.6830 → 0.6834 → 0.6841 → 0.6844 → 0.6849 → 0.6851 → 0.6867 → 0.6868 → 0.6873 → 0.6877 → 0.6895 → 0.6898 → 0.6898
- Best: `a567151` "simplify ensemble from three seeds to two", Eval 0.6898, Holdout 0.6872 (gap -0.0026; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6782, 0.6821, 0.6821, 0.6812, 0.6821, 0.6818, 0.6822, 0.6824, 0.6828, 0.6843, 0.6845, 0.6856, 0.6855, 0.6870, 0.6873, 0.6872
- Best model: the average of two XGBoost models (seeds 42 and 137) that boost small forests. Each runs 500 rounds of 4 parallel depth-4 trees at learning rate 0.05, with `min_child_weight` 20, `reg_lambda` 200, gamma 5, `subsample` 0.8, `colsample_bynode` 0.8 and `max_cat_threshold` 16. Interaction constraints keep the day of month and day of year apart from all other features. Inputs:
  - `DayOfWeek`, `UniqueCarrier`, `Origin` and `Dest` as categories, with codes fixed from train; `CRSDepTime`, `Distance`, departure hour and minute
  - month as a number and as sine / cosine; day of month and day of year as numbers (no categorical `Month` or `DayofMonth`)
  - three airport coordinates per end: classical MDS of shortest-path distances over the train route-distance graph
  - three "peer" delay rates from train labels, smoothed toward 0.5 (prior 100 / 200):
    - the origin airport's rate without this carrier
    - the destination's rate without this carrier
    - the carrier's rate at other origins

    They are fitted on train only, with defaults for unseen pairs, and nothing is read at scoring.

  No holiday features: they were tried (`3419e9d`) and discarded at a tie.
- Gains, adding up to +0.0155:
  - 500 shallow regularized trees: +0.0050
  - calendar and departure-time numbers: +0.0032
  - `max_cat_threshold` 16: +0.0005
  - 4 parallel trees: +0.0004
  - fine date kept apart by interaction constraints: +0.0007
  - airport coordinates: +0.0003
  - gamma 5: +0.0005
  - peer delay rates: +0.0002
  - without the categorical `DayofMonth`: +0.0016
  - three seeds: +0.0001
  - month without its categorical duplicate: +0.0005
  - circular month: +0.0004
  - `reg_lambda` 50, then 200: +0.0018, +0.0003
- Two kept ties, each simpler or faster, as program.md allows:
  - `a252681` fixed category codes: evaluation 21.0 s → 7.0 s
  - `a567151` (the best commit): two seeds instead of three, training 33.4 s → 23.6 s (Holdout 0.6873 → 0.6872)

  Equal results that added complexity were discarded (`5bda441`, `3419e9d`, `42f7564`, `ceccc1d`, `1947e00`).
- Timing (report.txt): total 0h58m42s; XGBoost runs 0h22m25s (38.2%); AI 0h36m17s (61.8%)
- Clock stopped by the agent after 3522 s, 78 s of the 3600 s budget left. That is not an early stop: under 2 minutes remained. The last run (`a567151`) ended at 3483 s.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 45 agent commits (branch and reflog) touch only train.py. 45 artifacts for the 45 completed runs (the timed-out run saved none), all inside the clock. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed each of the 9 commands leak_check lists:
  - setup: `rg --files` limited to docs and config, `cat` of train.py, harness.py and .gitignore, `ls -l data/train.csv data/eval.csv`, the branch and results header
  - status polls with `rg` on output/run.log
  - a final re-read of program.md and train.py
  - the final verification
- Data reads: only `data/train.csv` (a profile, samples for its artifact checks). eval.csv was only listed with `ls -l`. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `head` of train.csv in its profile.
- Web: 20 `web__run` calls with 13 searches, 10 opens and 2 finds (some calls combine them). Pages opened:
  - XGBoost docs: parameter tuning, parameters, categorical data, interaction constraints, monotonic constraints, DART, learning to rank, the feature-weights example
  - scikit-learn target-encoder cross-fitting and bias-variance examples
  - arXiv 2105.08969
  - a pandas page, which failed to load

  No result or page from BTS, Kaggle or S3 appears in the web outputs; no carrier-code mapping. No flight data from elsewhere.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt. "holdout" appears only in the final verification's text.
- diff-stat.txt (first commit to best): train.py only (+95 -9).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct7` = the 17 kept commits in results.tsv order; HEAD = `a567151` = last keep.
  - No discarded or crashed commit on the branch, nothing of output/ committed, no stray files, and every harness run is logged in results.tsv.
- Kept ties: two, both simpler or faster (see Results), so no `keep_rule`.
- Clock stopped by the agent (`clock_stopped_by` = agent), 78 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- **One context compaction** in the session log at 03:46:43, 56 minutes into the clock, just before the wrap-up.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- turns/1.err holds only codex's "Reading additional input from stdin..."; turns/2.err is empty.
