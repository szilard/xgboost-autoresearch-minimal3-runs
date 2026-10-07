# astra6_n20-18

**Valid** (no flags). Best Eval AUC **0.6901** (`1f5c0f6`), Holdout AUC **0.6878**, gap **-0.0023**.

Peak memory was 16.5 GiB, the highest of the group by far: the others ranged from 3.4 to 6.0 GiB. It stayed under the 24 GiB cap with nothing killed (see Other notes).

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct7`
- Date: 2026-10-07. Driver ran 03:53:34 to 04:59:55 UTC, clock 03:56:13 to 04:55:45 UTC.
- Container `astra6_n20-18`: memory cap 24 GiB (25769803776 bytes), no swap; **peak 17769504768 bytes (16.5 GiB)**; 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as astra6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for astra6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 117 s: branch `oct7` created, files read, both data files and the packages checked, `output/results.tsv` with header; ends "Say “go” to begin" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0.

**No question glossed over.** In turn 1 the agent called codex's question tool to propose `oct7` (options `oct7`, `oct7-a`). The tool returned `{"accepted":true}` and the agent went on with `oct7`. Its final message only asked for the go-ahead.

## Results

- 44 rows in results.tsv (baseline + 43 experiments): 16 keep, 28 discard, 0 crash; 44 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6758 → 0.6761 → 0.6761 → 0.6807 → 0.6818 → 0.6840 → 0.6840 → 0.6844 → 0.6850 → 0.6854 → 0.6855 → 0.6857 → 0.6859 → 0.6900 → 0.6901
- Best: `1f5c0f6` "retain 37.5 percent of the learned additive month effect", Eval 0.6901, Holdout 0.6878 (gap -0.0023; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6751, 0.6755, 0.6755, 0.6783, 0.6790, 0.6826, 0.6826, 0.6827, 0.6838, 0.6843, 0.6844, 0.6845, 0.6845, 0.6878, 0.6878
- Best model: a soft-voting average of three XGBoost models (seeds 42, 137, 2026). Each runs 1200 rounds of lossguide trees with 16 leaves at learning rate 0.05, with `min_child_weight` 20, `reg_lambda` 10, `subsample` 0.8, `colsample_bynode` 0.8, one-level categorical splits (`max_cat_to_onehot` 1024), and a logistic objective with smoothed targets 0.05 / 0.95.
  - Interaction constraints make `Month` and a holiday phase each an additive effect, separate from the operational features.
  - After fitting, each model measures its learned month effect on two training rows and shrinks it at prediction time: it subtracts 62.5% of the month's centred log-odds, keeping 37.5%.
  - Inputs:
    - `Month`, `DayOfWeek`, `UniqueCarrier`, `Origin` and `Dest` as categories; `CRSDepTime` and `Distance`; no `DayofMonth`
    - two airport coordinates per end: classical MDS of shortest-path distances over the train route-distance graph
    - a holiday phase: before, on or after a holiday within 3 days (New Year, July 4, Memorial Day, Labor Day, Thanksgiving, Christmas), computed from the row's month, day and weekday on a 365-day calendar
- Gains, adding up to +0.0158:
  - 400 regularized trees: +0.0015
  - without `DayofMonth`: +0.0003
  - one-level categorical splits: +0.0046
  - 1200 trees: +0.0011
  - month as an additive effect: +0.0022
  - 4 parallel trees with column sampling: +0.0004 (later back to 1 per round)
  - airport coordinates: +0.0006
  - holiday phase: +0.0004
  - lossguide with 16 leaves: +0.0001
  - smoothed targets: +0.0002
  - three seeds: +0.0002
  - **the month effect at half strength: +0.0041**, then at 37.5%: +0.0001
- The month shrinkage is a model choice tuned on Eval AUC, like the calendar-margin scaling of astra6_n20-9. The holdout followed (0.6845 → 0.6878).
- Two kept ties, both faster code, as program.md allows:
  - `160e851` reused category dtypes: evaluation 27.1 s → 9.3 s
  - `6f0afce` explicit category codes: evaluation 9.6 s → 5.9 s

  Equal results that added complexity were discarded (`062fe44`, `6ad5f15`, `aba3067`).
- Timing (report.txt): total 0h59m32s; XGBoost runs 0h20m08s (33.8%); AI 0h39m24s (66.2%)
- Clock stopped by the agent after 3572 s, 28 s of the 3600 s budget left (not an early stop). The last run (`aba3067`) ended at 3481 s. Final summary written in the research log.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 43 agent commits (branch and reflog) touch only train.py. 44 artifacts (352 MB) for 44 completed runs, all inside the clock. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed each of the 4 commands leak_check lists:
  - setup: a loop that `cat`s an `AGENTS.md` in `/`, `/home`, `/home/ubuntu` or the repo if one exists (none did), `cat train.py harness.py`, `ls -l data/train.csv data/eval.csv`, the branch with an `rg` in program.md for the confirmation rule
  - the final summary. Its mention of the holdout is text written to the research log.
- Data reads: only `data/train.csv` (a profile, delay rates, samples for its artifact checks). eval.csv was only listed with `ls -l`. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `head` of train.csv.
- Web: 28 `web__run` calls with 13 searches, 10 opens and 11 finds (some calls combine them). Pages opened:
  - XGBoost docs: parameter tuning, categorical data, interaction constraints, monotonic constraints, random forests, learning to rank
  - scikit-learn cyclical-features and boosting-regularization examples and Isomap; pandas categorical guide; SciPy `shortest_path`
  - arXiv 1906.02629 (label smoothing) and 2310.05067
  - two Friedman papers on jerryfriedman.su.domains, which failed to load

  No result or page from BTS, Kaggle or S3 appears in the web outputs; no carrier-code mapping. No flight data from elsewhere.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+108 -14).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct7` = the 16 kept commits in results.tsv order; HEAD = `1f5c0f6` = last keep.
  - No discarded commit on the branch, nothing of output/ committed, no stray files, and every harness run is logged in results.tsv.
- Kept ties: two, both faster code (see Results), so no `keep_rule`.
- Clock stopped by the agent (`clock_stopped_by` = agent), 28 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- **Peak memory 16.5 GiB** (container cgroup peak), against 3.4 to 6.0 GiB in the other runs of the group; 0 processes killed at the cap.
  - The driver records only the run's peak, not which step reached it.
  - This run's models are the largest of the group: three 1200-round, 16-leaf models with one-level splits over hundreds of airport levels, and in some experiments 2400 rounds or five members. The harness scores eval.csv in 8 worker processes, each holding the model.
  - No harness run crashed or timed out, so the cap had no effect on the results.
- No context compaction in the session log.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- turns/1.err holds only codex's "Reading additional input from stdin..."; turns/2.err is empty.
