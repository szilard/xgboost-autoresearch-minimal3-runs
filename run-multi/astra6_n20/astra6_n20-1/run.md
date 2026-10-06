# astra6_n20-1

**Valid** (no flags). Best Eval AUC **0.6900** (`50e74b8`), Holdout AUC **0.6880**, gap **-0.0020**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max`. Its levels are `low medium high xhigh max ultra`, so `ultra` sits above `max`.
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct6`
- Date: 2026-10-06. Driver ran 08:44:42 to 09:51:51 UTC, clock 08:48:31 to 09:48:05 UTC.
- Container `astra6_n20-1`: memory cap 24 GiB (25769803776 bytes), no swap; peak 3619983360 bytes (3.4 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected. Packages: cloudpickle 3.1.2, numpy 2.5.3, pandas 3.0.6, scikit-learn 1.9.1, xgboost 3.4.1.
- Driver: `run_one.sh` of commit `1030646`

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 189 s: branch `oct6` created, files read, both data files checked, train.csv inspected, `output/results.tsv` and the research log started; ends "Say **go** to begin" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0.

**No question glossed over.** In turn 1 the agent called codex's question tool to propose the tag `oct6`. The tool returned `{"accepted":true}` and the agent went on with `oct6`. Its final message only asked for the go-ahead, which "go" gives. turns/1.err holds only codex's "Reading additional input from stdin..."; turns/2.err is empty.

## Results

- 47 rows in results.tsv (baseline + 46 experiments): 19 keep, 28 discard, 0 crash; 47 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6743 → 0.6800 → 0.6812 → 0.6837 → 0.6837 → 0.6837 → 0.6841 → 0.6842 → 0.6843 → 0.6845 → 0.6845 → 0.6846 → 0.6848 → 0.6871 → 0.6876 → 0.6880 → 0.6881 → 0.6900
- Best: `50e74b8` "remove monthly weighting after adding holiday features", Eval 0.6900, Holdout 0.6880 (gap -0.0020; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6725, 0.6784, 0.6797, 0.6810, 0.6810, 0.6814, 0.6824, 0.6822, 0.6823, 0.6823, 0.6823, 0.6825, 0.6828, 0.6855, 0.6857, 0.6857, 0.6857, 0.6880
- Best model: the average of three XGBoost classifiers (seeds 42, 137, 2026). Each has 400 rounds at learning rate 0.025, lossguide growth with 16 leaves, `min_child_weight` 40, `reg_lambda` 10, `subsample` 0.85 and `max_cat_threshold` 32. Their inputs:
  - `DayOfWeek`, `UniqueCarrier`, `Origin` and `Dest` as native categories, with codes fixed from train; `CRSDepTime` and `Distance`
  - no `Month` and no `DayofMonth`
  - two schedule offsets: departure minutes minus the train median for the origin, and for the carrier-origin pair
  - six holiday-relative day offsets: Thanksgiving, Christmas / New Year, July 4, Memorial Day, Labor Day, MLK / Presidents' Day. They are calendar arithmetic on `Month`, `DayofMonth` and `DayOfWeek` alone: the weekday of the 1st of the month is derived from the row, so no year and no file is needed.
- Gains, adding up to +0.0157:
  - depth 4, 400 trees, stronger regularization: +0.0057
  - without `DayofMonth`: +0.0012; then without `Month`: +0.0025
  - schedule offsets from train medians: +0.0004
  - class weights balanced within each training month: +0.0001
  - a blend with a geography model, then three seeds: +0.0001, +0.0002
  - 400 rounds at learning rate 0.025: +0.0001; lossguide with 16 leaves: +0.0002
  - holiday offsets: Thanksgiving / winter / July 4 +0.0023, Memorial / Labor Day +0.0005, MLK / Presidents' Day +0.0004
  - without the route offset: +0.0001; without the monthly weights: +0.0019
- Four kept ties, each simpler or faster, as program.md allows:
  - `73d6659` "simplify prepare": same features, evaluation 31.5 s → 17.5 s
  - `7f1baf3` "fixed category codes": evaluation 13.3 s → 3.9 s, predictions checked identical by the agent
  - `4399805` 200 rounds instead of 400: a smaller model (Holdout 0.6810 → 0.6814)
  - `092ca0c` "remove geography": half the ensemble, training 6.0 s → 3.2 s

  Results equal to the best were discarded when they added complexity (`9091038`, `765ea8a`, `221ff7e`) or changed nothing (`026b1dd`, gamma 5).
- Above every run pushed so far: the luna6_n20 maxima are 0.6859 eval and 0.6844 holdout, and the sol6_n20 maxima (runs 1-15) are 0.6893 and 0.6871. Most of the late gain came from the holiday features (+0.0032) and from dropping the monthly weights after adding them (+0.0019).
- Timing (report.txt): total 0h59m34s; XGBoost runs 0h09m13s (15.5%); AI 0h50m21s (84.5%)
- Clock stopped by the agent after 3574 s, 26 s of the 3600 s budget left (not an early stop). The last run (`e4832c1`) ended 146 s before the budget ran out. Final summary written in the research log.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 46 agent commits (branch and reflog) touch only train.py. 47 artifacts for 47 completed runs, all inside the clock. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed each of the 47 commands leak_check lists:
  - setup: `rg --files` limited to the repo's docs and code, `cat` of program.md, README.md, train.py and harness.py, and `ls -l data/train.csv data/eval.csv`
  - status polls with `harness.py status`, `git log` and `tail` of results.tsv and run.log
  - appends to results.tsv and the research log
  - checks of its own artifacts with `load_artifact` on samples of train.csv: batch vs single-row features, label flips, unseen categories, holiday dates against Python's `datetime` for 2005 and 2006
  - web calls (below)
- Data reads: only `data/train.csv`. eval.csv was only listed with `ls -l`, never opened. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `train.head(3)` of train.csv.
- Web: 23 `web__run` calls, made up of 9 searches, 10 page opens and 4 finds. Pages opened:
  - XGBoost docs: parameter tuning, categorical data, parameters, interaction constraints, random forests, learning to rank, monotonic constraints
  - scikit-learn docs: RobustScaler, manifold (Isomap), voting ensembles, target encoder cross-fitting
  - the CatBoost NeurIPS paper

  Two searches were aimed at BTS: `site.transtats.bts.gov airline on time performance ...` and `site.bts.gov airline delays time of day ...`. They returned only result snippets. I read them in full: they hold field lists of the TranStats departure and download forms, BTS reporting directives and national delay-cause shares, but no flight records. No BTS page was opened and nothing was downloaded. The other searches covered XGBoost and scikit-learn docs, CatBoost, the MVS sampling paper on arXiv, and OPM's federal holiday dates. No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt. "holdout" appears only in the agent's research-log text ("the unseen holdout remains the check").
- diff-stat.txt (first commit to best): train.py only (+69 -14).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct6` = the 19 kept commits in results.tsv order; HEAD = `50e74b8` = last keep.
  - No discarded commit on the branch, nothing of output/ committed, no stray files, and every harness run is logged in results.tsv.
- Kept ties: four, all for simpler or faster code (see Results), so no `keep_rule`.
- Clock stopped by the agent (`clock_stopped_by` = agent), 26 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- No context compaction in the session log.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- The agent stated the 2005-to-2006 shift as the reason for its regularization and ablations, from program.md. Its holiday features compute each holiday from the row's own weekday and day, so they work for any year.
