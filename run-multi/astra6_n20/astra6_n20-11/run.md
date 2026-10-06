# astra6_n20-11

**Valid** (no flags). Best Eval AUC **0.6897** (`d9dcf2d`), Holdout AUC **0.6860**, gap **-0.0037**.

The gap is the largest of the group so far, but it is inside the -0.006 threshold.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct6`
- Date: 2026-10-06. Driver ran 20:05:13 to 21:11:28 UTC, clock 20:08:07 to 21:08:06 UTC.
- Container `astra6_n20-11`: memory cap 24 GiB (25769803776 bytes), no swap; peak 3721220096 bytes (3.5 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as astra6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for astra6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 126 s: branch `oct6` created, files read, both data files and the packages checked, `output/results.tsv` and the research log started; asks for "go" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0.

**No question glossed over.** The agent picked the tag `oct6` itself (no question tool call). Its final message only asked for the go-ahead.

## Results

- 52 rows in results.tsv (baseline + 51 experiments): 20 keep, 32 discard, 0 crash; 52 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6743 → 0.6759 → 0.6800 → 0.6830 → 0.6838 → 0.6838 → 0.6841 → 0.6843 → 0.6850 → 0.6851 → 0.6865 → 0.6872 → 0.6890 → 0.6891 → 0.6893 → 0.6894 → 0.6895 → 0.6897 → 0.6897
- Best: `d9dcf2d` "faster scalar calendar preparation with identical features", Eval 0.6897, Holdout 0.6860 (gap -0.0037; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6725, 0.6762, 0.6790, 0.6815, 0.6816, 0.6816, 0.6815, 0.6820, 0.6827, 0.6825, 0.6839, 0.6846, 0.6858, 0.6858, 0.6858, 0.6860, 0.6860, 0.6860, 0.6860
- Best model: a 1:2:1 average of three XGBoost regressors with a logistic objective, fitted to soft targets 0.05 / 0.95:
  - lossguide trees with 4, 8 and 16 leaves, for 500, 300 and 200 rounds
  - learning rate 0.05, `min_child_weight` 20, `reg_lambda` 10, `reg_alpha` 10
  - training weights balance the classes within each training month, times a recency weight that halves every six months back from December

  Inputs:
  - `DayOfWeek`, `UniqueCarrier`, `Origin` and `Dest` as categories, with codes fixed from train; `CRSDepTime` and `Distance`
  - no `Month` and no `DayofMonth`
  - departure minutes minus the train median for the carrier-origin pair
  - four calendar flags, computed from the row's month, day and weekday: summer (June to August), holiday, the 3 days before, and the 3 days after (New Year, July 4, Thanksgiving, Christmas)
- Gains, adding up to +0.0154:
  - without `DayofMonth`: +0.0016
  - 300 depth-4 trees at learning rate 0.05: +0.0041
  - without `Month`: +0.0030
  - depth 3: +0.0008
  - monthly class balance: +0.0003
  - recency weights: +0.0002
  - the depth 2/3/4 blend: +0.0007
  - schedule medians: +0.0001
  - holiday flags: +0.0014
  - winter and summer flags: +0.0007
  - `reg_alpha` 5: +0.0018
  - without the route median: +0.0001
  - without the winter flag: +0.0002
  - lossguide leaf limits: +0.0001
  - `reg_alpha` 10: +0.0001
  - soft targets: +0.0002
- Three kept ties, each faster code, as program.md allows:
  - `9b015b0` "faster prepare": evaluation 31.1 s → 8.1 s
  - `4f14bdb` explicit category codes: evaluation 6.2 s → 4.4 s
  - `d9dcf2d` (the best commit) scalar calendar arithmetic per row instead of small NumPy operations; the agent checked the features are identical on all 200,000 train rows.
    - Evaluation took 6.1 s against 6.8 s for `0d44d86` before it. The 10 runs before it with equally costly code took 6.7 to 7.3 s.
    - **Counted as faster, borderline:** a code change aimed at the per-row `prepare`, and below that whole range, but measured once and only by about 0.6 s.
    - Either way it changes no feature and no prediction: Eval and Holdout AUC are the same as `0d44d86` (0.6897 / 0.6860).

  Equal results that added complexity or no speed were discarded (`15312a1`, `e3e224e`, `0835e2b`, `5b6625e`, `7739099`, `8d5d93c`, `bb6c56e`, `8dc2c14`).
- Timing (report.txt): total 0h59m59s; XGBoost runs 0h09m31s (15.9%); AI 0h50m28s (84.1%)
- Clock stopped by the agent after 3599 s, 1 s of the 3600 s budget left (not an early stop). The last run (`d9dcf2d`) started at 3467 s, with 2m13s left, and ended at 3477 s. The agent then logged it, verified the artifact, wrote the final summary and stopped the clock.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 51 agent commits (branch and reflog) touch only train.py. 52 artifacts for 52 completed runs, all inside the clock. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed the 51 commands leak_check lists:
  - 31 are status polls with `rg '^(Training time:|Eval time:|Eval AUC:|Run time:)' output/run.log`, `harness.py status` and `git log`, which leak_check counts as broad reads
  - two `sed -n` reads of train.py
  - two web finds
  - setup: `rg --files` limited to docs and config, `ls -l data/train.csv data/eval.csv` and `is_file()` checks of both data files
  - result loggings and the final verification. Its "Any additional model claims should be checked through the human's separate holdout process" is text written to the research log.
- Data reads: only `data/train.csv` (a profile, a 500-row sample, delay rates, the feature-equality check). eval.csv was only listed and checked for existence. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `head` of train.csv in its profile.
- Web: 22 `web__run` calls with 12 searches, 7 opens and 3 finds (some calls combine them). Pages opened:
  - XGBoost docs: parameter tuning, categorical data, interaction constraints, random forests, learning to rank, DART, tree methods
  - the scikit-learn cyclical-features example
  - arXiv 1208.0645, 1505.01866 (DART), 1906.02629 (label smoothing)
  - the UC Berkeley iSchool flight-delay page, which failed to load ("Internal Error")

  One search was "2005 2006 Thanksgiving Day Christmas Day holidays". It returned OPM holiday pages (calendar dates) and scikit-learn voting docs. The agent did not hardcode any year: its holidays are computed from the row's weekday and day. No result or page from BTS, Kaggle or S3 appears in the web outputs. No flight data from elsewhere.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+96 -16).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct6` = the 20 kept commits in results.tsv order; HEAD = `d9dcf2d` = last keep.
  - No discarded commit on the branch, nothing of output/ committed, no stray files, and every harness run is logged in results.tsv.
- Kept ties: three, all faster code, one of them borderline (see Results). No `keep_rule`: each is a code change for speed, not a parameter change, and the borderline one changes no prediction.
- Clock stopped by the agent (`clock_stopped_by` = agent), 1 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- No context compaction in the session log.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- turns/1.err holds only codex's "Reading additional input from stdin..."; turns/2.err is empty.
