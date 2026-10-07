# astra6_n20-16

**Valid** (no protocol flags). Best Eval AUC **0.6894** (`cb6c121`), Holdout AUC **0.6870**, gap **-0.0024**.

The integrity flag `artifact_outside_clock` is explained below: a timing row labelled with the wrong commit after a bookkeeping slip by the agent. The artifact itself is from a harness run inside the clock.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct7`
- Date: 2026-10-07. Driver ran 01:39:18 to 02:46:30 UTC, clock 01:42:38 to 02:42:08 UTC.
- Container `astra6_n20-16`: memory cap 24 GiB (25769803776 bytes), no swap; peak 3690369024 bytes (3.4 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as astra6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for astra6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 159 s: branch `oct7` created, files read, both data files checked, train.csv inspected, `output/results.tsv` and the research log started; ends "Say **go** to begin" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0.

**No question glossed over.** In turn 1 the agent called codex's question tool to propose `oct7` (options `oct7`, `oct7-run1`). The tool returned `{"accepted":true}` and the agent went on with `oct7`. Its final message only asked for the go-ahead.

## Results

- 49 rows in results.tsv (baseline + 48 experiments): 21 keep, 28 discard, 0 crash; 49 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6743 → 0.6759 → 0.6800 → 0.6815 → 0.6817 → 0.6818 → 0.6820 → 0.6824 → 0.6854 → 0.6854 → 0.6854 → 0.6856 → 0.6858 → 0.6862 → 0.6863 → 0.6868 → 0.6885 → 0.6888 → 0.6894 → 0.6894
- Best: `cb6c121` "remove redundant deprecated dart booster alias and one-tree default", Eval 0.6894, Holdout 0.6870 (gap -0.0024; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6725, 0.6762, 0.6790, 0.6796, 0.6801, 0.6802, 0.6806, 0.6810, 0.6838, 0.6838, 0.6837, 0.6842, 0.6844, 0.6847, 0.6841, 0.6852, 0.6867, 0.6866, 0.6870, 0.6870
- Best model: the average of two XGBoost models with tree dropout (seeds 42 and 137). Each runs 180 rounds of depth-4 trees at learning rate 0.1, with `rate_drop` 0.05, `skip_drop` 0.5, forest normalization, `min_child_weight` 20, `reg_lambda` 300, `max_bin` 64, `subsample` 0.75, `colsample_bynode` 0.8 and `max_cat_threshold` 16. Training weights halve every 12 months back from December. Inputs:
  - `DayOfWeek`, `UniqueCarrier`, `Origin` and `Dest` as categories; `CRSDepTime`, `Distance` and the departure hour
  - month as a number and as sine / cosine; no `DayofMonth`
  - the distance in days to the nearest of New Year, July 4, Christmas and Thanksgiving, capped at 21, computed from the row's month, day and weekday
  - departure minutes minus the train median for the route and for the carrier-origin pair
- Gains, adding up to +0.0151:
  - without `DayofMonth`: +0.0016
  - depth 4, 300 trees at learning rate 0.05: +0.0041
  - `max_cat_threshold` 16: +0.0015
  - numeric and cyclic month: +0.0002
  - departure hour and minute: +0.0001
  - 3 parallel trees with 75% rows: +0.0002
  - node column sampling: +0.0004
  - holiday distance: +0.0030, the largest
  - route-median offset: +0.0002
  - recency weights: +0.0002
  - DART: +0.0004
  - 64 bins: +0.0001
  - two seeds: +0.0005
  - `reg_lambda` 100, then 300: +0.0017, +0.0003
  - carrier-origin offset: +0.0006
- Four kept ties, each simpler or faster, as program.md allows:
  - `b12cec4` cached category dtypes: evaluation 31.3 s → 10.3 s
  - `40b0506` direct calendar lookups and explicit category codes: evaluation 14.2 s → 7.9 s
  - `efe0916` without the minute-of-hour feature: one feature fewer (Holdout 0.6838 → 0.6837)
  - `cb6c121` (the best commit): without the deprecated `booster="dart"` alias and the default one-tree setting. The dropout parameters are unchanged; Eval and Holdout AUC are the same as `fd9ab43` before it.

  Equal results that added complexity were discarded (`437d862`, `34cf7f7`).
- Timing (report.txt): total 0h59m30s; XGBoost runs 0h19m19s (32.5%); AI 0h40m11s (67.5%)
- Clock stopped by the agent after 3570 s, 30 s of the 3600 s budget left (not an early stop). The last run (`767e2b6`) ended at 3499 s. Final summary written in the research log.

## Integrity checks: pass (one flag, explained)

- checks.txt: `INTEGRITY FLAGS: artifact_outside_clock`, from `9e1574c8c739b43cce36ee14e014e9c3a5420d48.pkl: no harness run of that commit`. checks.txt also notes "9e1574c is logged as discard but has no completed harness run". From the session log:
  - **02:17:03** (34m22s on the clock): the agent commits `9e1574c` (lossguide trees with 12 leaves) and starts `python3 harness.py run > output/run.log`.
  - **02:17:15:** its stored result helper reads run.log too early, after "Training done, evaluating... Artifact: artifacts/9e1574c….pkl" but before the Eval AUC. It logs `9e1574c 0.0000 crash` and runs `git reset --hard 26a8295` while the harness is still evaluating. Evaluation scores the already-saved artifact, so the reset does not change the result. The harness labels its timing row with the commit at the end of the run, which is now `26a8295`.
  - **02:17:56:** the agent sees the completed run ("Eval AUC: 0.6857 … ok"), resets to `9e1574c`, removes the premature crash row and adds a guard to the helper that refuses unfinished logs.
  - **02:18:17:** it records `9e1574c 0.6857 discard` and resets to the best commit `26a8295`.
  - It then documents the mislabelled timing row in the research log and leaves the protected timing file untouched.

  The timing data agrees. timing/runs.tsv has two `26a8295` rows. The second (start 1791339421.2) trained for 18.8 s, against 14.1 s for the real `26a8295` run before it, which fits the 12-leaf lossguide model. So the artifact and the Eval AUC 0.6857 come from a harness run inside the clock. Nothing kept depends on it: it is a discard.
- Otherwise: 48 agent commits (branch and reflog) touch only train.py. 49 artifacts for 49 completed runs. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed each of the 7 commands leak_check lists:
  - setup: `rg --files` limited to docs and config, `cat` of program.md, README.md, train.py and harness.py, `ls -l data/train.csv data/eval.csv`, the research-log start
  - the DART docs with an `rg` for `load_artifact` in harness.py
  - an `rg` of its own research log for the bookkeeping note
  - the final verification
- Data reads: only `data/train.csv` (a profile, samples for its artifact checks). eval.csv was only listed with `ls -l`. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `train.head(3)`.
- Web: 30 `web__run` calls with 13 searches, 15 opens and 4 finds (some calls combine them). Pages opened:
  - XGBoost docs: parameter tuning, parameters, interaction constraints, random forests, learning to rank, DART, tree methods, custom objectives, categorical data
  - scikit-learn cyclical features, Isomap and ensembles; SciPy `shortest_path`; pandas groupby
  - the XGBoost paper (arXiv 1603.02754)
  - a 2008 Stanford CS229 project report, "Airline Departure Delay Prediction" (Naul). It describes BTS data and features in prose, with a few 2008 national figures (e.g. American Airlines on time 66.9% through September 2008). No flight records and nothing about 2005 or 2006.
  - the UC Berkeley iSchool flight-delay page and a pandas page, both of which failed to load

  No result or page from BTS (other than the CS229 report's citation of transtats.bts.gov), Kaggle or S3 appears in the web outputs; no carrier-code mapping. No flight data from elsewhere.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt. "holdout" appears only in the final verification's text.
- diff-stat.txt (first commit to best): train.py only (+78 -10).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct7` = the 21 kept commits in results.tsv order; HEAD = `cb6c121` = last keep.
  - No discarded commit on the branch, nothing of output/ committed, no stray files, and every harness run is logged in results.tsv (one under a wrong commit label, see above).
- Kept ties: four, all simpler or faster (see Results), so no `keep_rule`.
- Clock stopped by the agent (`clock_stopped_by` = agent), 30 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- **One context compaction** in the session log at 02:34:53, 52 minutes into the clock. The agent carried on normally afterwards.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- turns/1.err holds only codex's "Reading additional input from stdin..."; turns/2.err is empty.
