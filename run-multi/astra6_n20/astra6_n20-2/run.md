# astra6_n20-2

**Valid** (no flags). Best Eval AUC **0.6863** (`6826f09`), Holdout AUC **0.6836**, gap **-0.0027**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct6`
- Date: 2026-10-06. Driver ran 09:52:01 to 11:03:34 UTC, clock 09:55:41 to 10:56:16 UTC.
- Container `astra6_n20-2`: memory cap 24 GiB (25769803776 bytes), no swap; peak 6421655552 bytes (6.0 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as astra6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for astra6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 180 s: branch `oct6` created, files read, both data files checked, train.csv inspected, `output/results.tsv` and the research log started; ends "say **go** to begin" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself, 34 s after the budget ran out |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0.

**No question glossed over.** In turn 1 the agent called codex's question tool with the single option `oct6`. The tool returned `{"accepted":true}` and the agent went on with `oct6`. Its final message only asked for the go-ahead.

## Results

- 42 rows in results.tsv (baseline + 41 experiments): 16 keep, 26 discard, 0 crash; 42 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6762 → 0.6834 → 0.6840 → 0.6844 → 0.6845 → 0.6846 → 0.6851 → 0.6852 → 0.6852 → 0.6854 → 0.6856 → 0.6856 → 0.6859 → 0.6861 → 0.6863
- Best: `6826f09` "Weight feature sampling toward departure time and away from fine calendar effects", Eval 0.6863, Holdout 0.6836 (gap -0.0027; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6724, 0.6812, 0.6817, 0.6822, 0.6829, 0.6827, 0.6831, 0.6833, 0.6832, 0.6829, 0.6831, 0.6832, 0.6835, 0.6837, 0.6836
- Best model: one XGBoost model that boosts a small forest. It runs 1600 rounds of 3 parallel depth-6 trees at learning rate 0.05, with `max_bin` 1024, `min_child_weight` 20, `reg_lambda` 100, `subsample` 0.85 and `colsample_bytree` 0.9. Its feature weights are 4 for `CRSDepTime`, 0.5 for `Month` and `DayofMonth`, and 1 for the rest. Categorical splits are one level at a time (`max_cat_to_onehot` 10000). Inputs:
  - the eight starter columns
  - a carrier-origin category
  - two origin-airport coordinates: classical MDS of shortest-path distances over the train route-distance graph, fitted on train only
- Gains, adding up to +0.0120:
  - 600 trees at learning rate 0.05 with stronger regularization: +0.0019
  - one-hot splits for all categories: +0.0072, the largest
  - 1200 rounds: +0.0006
  - carrier-origin and carrier-destination crosses: +0.0004
  - airport coordinates, then without the route-direction differences: +0.0001, +0.0001
  - 3 parallel trees per round: +0.0005
  - 1024 bins: +0.0001
  - without the carrier-destination cross: +0.0002
  - only two coordinate axes: +0.0002
  - `reg_lambda` 100: +0.0003
  - 1600 rounds: +0.0002
  - feature weights: +0.0002
- Two kept ties, both simpler, as program.md allows:
  - `dc9e866`: 800 rounds instead of 1200, training 21.2 s → 14.9 s
  - `c4328a2`: the destination coordinates removed

  Equal results that added complexity were discarded (`0109617`, `5a7f06c`, `0ad34f0`, `b7b05d3`).
- The agent logged results and applied the keep rule with a small script of its own, stored in codex's exec tool as `finishTemplate`. The script keeps a result above the last keep, or a tie when called with `ALLOW_EQUAL` True, and otherwise runs `git reset --hard` to the last keep.
- Unlike astra6_n20-1, holiday-proximity features were tried (`539607a`, 0.6832) and discarded here.
- Timing (report.txt): total 1h00m34s; XGBoost runs 0h29m26s (48.6%); AI 0h31m09s (51.4%)
- Clock stopped by the agent after 3634 s, **34 s after the 3600 s budget ran out**. This is not an early stop.
  - The last run (`6826f09`) started at 3489 s and ended at 3538 s, inside the budget.
  - The agent then spent the rest of the time on its final artifact check and the summary in the research log.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 41 agent commits (branch and reflog) touch only train.py. 42 artifacts for 42 completed runs, all inside the clock. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed each of the 5 commands leak_check lists:
  - setup: `cat program.md`, `rg --files` excluding data, a loop that `cat`s an `AGENTS.md` in `/`, `/home` or `/home/ubuntu` if one exists (none did), `cat` of train.py and harness.py, and `ls -l data/train.csv data/eval.csv`
  - the research-log patch
  - a status poll
  - the web search below that included a bts.gov query
- Data reads: only `data/train.csv` (a profile, delay rates by month, weekday, hour and carrier, and samples for the agent's checks of its own artifacts). eval.csv was only listed with `ls -l`. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `train.head(5)` of train.csv.
- Web: 24 `web__run` calls with 15 searches, 8 opens and 5 finds (some calls combine them). Pages opened:
  - XGBoost docs: parameter tuning, parameters, categorical data, tree methods, monotonic constraints, DART
  - scikit-learn Isomap and SciPy `shortest_path` docs
  - arXiv 2505.12460, on k-means binning in histogram GBDTs
  - an MDPI Aerospace flight-delay paper, which failed to load ("Internal Error")

  One search was limited to bts.gov ("Thanksgiving Christmas holiday air travel scheduled flights"). It returned no bts.gov result at all; the output holds only the OPM holiday page and the XGBoost random-forest page. No BTS page was opened. No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+45 -7).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct6` = the 16 kept commits in results.tsv order; HEAD = `6826f09` = last keep.
  - No discarded commit on the branch, nothing of output/ committed, no stray files, and every harness run is logged in results.tsv.
- Kept ties: two, both simplifications (see Results), so no `keep_rule`.
- Clock stopped by the agent (`clock_stopped_by` = agent), `clock_remaining_s` -34.
- No retry waits (`retry_wait_s` 0).

## Other notes

- No context compaction in the session log. turns/1.err holds only codex's "Reading additional input from stdin..."; turns/2.err is empty.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- train.py imports `scipy.sparse.csgraph`, which comes with scikit-learn in the image. It is a library import, not a file read.
