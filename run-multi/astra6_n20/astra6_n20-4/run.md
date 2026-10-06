# astra6_n20-4

**Valid** (no protocol flags). Best Eval AUC **0.6843** (`c58ee9e`), Holdout AUC **0.6815**, gap **-0.0028**.

The integrity flag `artifact_outside_clock` is explained below. The artifact is from the agent's last harness run, started inside the clock and cut off during evaluation, so the harness never wrote its timing row. The run had one failed turn (model at capacity, 32 s retry wait), so a "keep going" was needed.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct6`
- Date: 2026-10-06. Driver ran 12:11:12 to 13:19:29 UTC, clock 12:13:26 to 13:14:43 UTC.
- Container `astra6_n20-4`: memory cap 24 GiB (25769803776 bytes), no swap; peak 3735453696 bytes (3.5 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as astra6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for astra6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 91 s: branch `oct6` created, files read, both data files checked, train.csv profiled, `output/results.tsv` and the research log started; ends "Reply **go** to confirm the tag and begin" |
| 2 | `go` | started the clock and worked until 58m38s on the clock (13:12:04). The turn then **failed**: "Selected model is at capacity". No final message (no turns/2.txt). |
| 3 | `keep going` | sent after the driver's 30 s capacity wait, with 48 s left. The agent logged its interrupted last experiment as a crash, reset to the best commit, wrote the final summary and stopped the clock. |

- **Failed turns: 1** (`failed_turns` 1), a capacity error. The driver waited 30 s; `retry_wait_s` = 32 s came out of the agent's hour, under the 2-minute threshold, so no `turn_retries` flag.
- turns/2.err also holds a codex error at the same moment: "failed to record rollout items: thread … not found". The session log is still complete: every turn's start and end and every tool call are in it.
- In turn 3, codex's "write_stdin failed: Unknown process id 20093" is the agent polling the exec session of turn 2's codex process, which no longer existed.
- **No question glossed over.** "go" confirms both the proposed tag `oct6` and the start.

## Results

- 36 rows in results.tsv (baseline + 35 experiments): 13 keep, 22 discard, 1 crash; 35 completed harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6781 → 0.6781 → 0.6786 → 0.6790 → 0.6806 → 0.6808 → 0.6819 → 0.6823 → 0.6834 → 0.6841 → 0.6842 → 0.6843
- Best: `c58ee9e` "Increase L2 leaf regularization from 10 to 100", Eval 0.6843, Holdout 0.6815 (gap -0.0028; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6763, 0.6763, 0.6779, 0.6779, 0.6786, 0.6778, 0.6793, 0.6796, 0.6805, 0.6814, 0.6812, 0.6815
- Best model: one XGBoost model that boosts a small forest. It runs 1000 rounds of 4 parallel depth-5 trees at learning rate 0.02, with `min_child_weight` 100, `reg_lambda` 100, `subsample` 0.8, `colsample_bynode` 0.8 and `max_cat_threshold` 8. Inputs:
  - `Month`, `DayOfWeek`, `UniqueCarrier`, `Origin` and `Dest` as categories; no `DayofMonth`
  - `CRSDepTime`, `Distance`, departure hour, minute and sine / cosine
  - the offset to the nearest holiday, capped at ±14 days. It is computed from month, day and weekday on a fixed 365-day calendar.
  - three airport coordinates for each end: classical MDS of shortest-path distances over the train route-distance graph
  - five smoothed target encodings: origin, destination, carrier-origin, carrier-destination and route
    - Each is a table of five out-of-fold delay rates, fitted on train labels only.
    - A row picks its fold from a hash of its feature columns, without the label.
    - Levels not seen in train get 0.5. Nothing is read at scoring time.
- Gains, adding up to +0.0100:
  - 400 depth-5 trees at learning rate 0.05 with regularization: +0.0038
  - without `DayofMonth`: +0.0005
  - departure-time features: +0.0004
  - `max_cat_threshold` 8: +0.0016
  - holiday offset: +0.0002
  - `min_child_weight` 100: +0.0011
  - target encodings: +0.0004
  - airport coordinates: +0.0011
  - 4 parallel trees with node sampling: +0.0007
  - 1000 rounds at learning rate 0.02: +0.0001
  - `reg_lambda` 100: +0.0001
- One kept tie, faster code, as program.md allows: `25542f4` "Simplify categorical dataframe construction", evaluation 31.0 s → 18.8 s.
- Timing (report.txt): total 1h01m18s; XGBoost runs 0h19m54s (32.5%); AI 0h41m24s (67.5%)
- Clock stopped by the agent after 3678 s, **78 s after the 3600 s budget ran out** (`clock_remaining_s` -78). This is not an early stop. The overrun includes the 32 s retry wait and turn 3's wrap-up.
- **The last experiment started with under 2 minutes left.** The agent's last status check (13:10:58) showed 2m28s remaining. It then logged experiment 34 and started experiment 35 (`f0eb202`, `max_bin` 64) at 13:11:33, when 1m53s remained, without checking again. program.md says not to start new experiments once less than 2 minutes remain. The check is not among the protocol flags, and the experiment was discarded without a score, so it changes nothing in the result.

## Integrity checks: pass (one flag, explained)

- checks.txt: `INTEGRITY FLAGS: artifact_outside_clock`, from the line `f0eb202162cf0ef4910135eed4c52771aa3dd271.pkl: no harness run of that commit`. It comes from a harness run started inside the clock:
  - 13:11:33: the agent committed `f0eb202` and ran `python3 harness.py run > output/run.log 2>&1`, 58m07s into the clock.
  - run.log, copied out by the driver: "Training time: 24.7s", "Training done, evaluating...", "Artifact: artifacts/f0eb202…pkl (23.0 MB)", and nothing after. So the harness saved the artifact at about 13:12:00, inside the budget, which ended at 13:13:26.
  - 13:12:04: codex's turn ended on the capacity error. At 13:12:12 the eval workers of `train.py` were still running in the container. By 13:13:08 they were gone (the agent's `ps` found none), without an Eval AUC and without the harness's timing row. The driver kills nothing between turns. The run most likely died with the exited codex process that had started it.
  - The agent then logged `f0eb202` as `crash` (0.0000, "interrupted during evaluation without a score") and reset to `c58ee9e`.

  So the artifact did come from a harness run inside the clock. The flag fires only because an interrupted run leaves no timing row. It is not an experiment run before the start or after the stop. Nothing kept depends on it: the commit is a crash and is not on the branch.
- Otherwise: 35 agent commits (branch and reflog) touch only train.py. 36 artifacts: 35 from completed runs plus `f0eb202`. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed each of the 6 commands leak_check lists:
  - setup: `rg --files` limited to docs and config, `cat` of program.md, README.md, .gitignore, train.py and harness.py, `rg --files` excluding data, `ls -la`, `ls -l data/train.csv data/eval.csv`, `git checkout -b oct6` and the results header
  - 13:13:08: `tail` of run.log and `ps` for the harness
  - 13:14:42: the crash logging, reset and final verification. "The holdout and archived results were never accessed" is text the agent wrote to the research log.
- Data reads: only `data/train.csv` (a profile, plus 32-row samples for its artifact checks). eval.csv was only listed with `ls -l`. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `head(8)` of train.csv.
- Web: 28 `web__run` calls with 14 searches, 19 opens and 2 finds (some calls combine them). Pages opened:
  - XGBoost docs: parameter tuning, parameters, categorical data, random forests, interaction constraints, learning to rank, DART, custom objectives, tree methods
  - scikit-learn docs: cyclical features, TargetEncoder, target-encoder cross-fitting, Isomap, common pitfalls, voting ensembles, feature selection
  - category_encoders, SciPy `shortest_path`, AWS SageMaker XGBoost tuning, LightGBM features
  - arXiv: 2304.13761, 2104.00629, 1208.0645, 1906.02629
  - the UC Berkeley iSchool flight-delay page and the MDPI Aerospace paper, both of which failed to load ("Internal Error")

  No result or page from BTS, Kaggle or S3 appears in the web outputs. No flight data from elsewhere.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+101 -9).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct6` = the 13 kept commits in results.tsv order; HEAD = `c58ee9e` = last keep.
  - No discarded or crashed commit on the branch, nothing of output/ committed, no stray files, and every completed harness run is logged in results.tsv.
- Kept tie: one, for faster code (see Results), so no `keep_rule`.
- Clock stopped by the agent (`clock_stopped_by` = agent), `clock_remaining_s` -78.
- Retry waits: 32 s (`retry_wait_s`), under 120 s, so no `turn_retries`.

## Other notes

- **One context compaction** in the session log at 13:10:44, 57 minutes into the clock, just before the last experiment.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind at the end, the best commit is HEAD, branch not detached.
- turns/1.err holds only codex's "Reading additional input from stdin...".
