# astra6_n20-20

**Valid** (no flags). Best Eval AUC **0.6876** (`fc0e2f7`), Holdout AUC **0.6853**, gap **-0.0023**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct7`
- Date: 2026-10-07. Driver ran 06:07:52 to 07:15:16 UTC, clock 06:11:47 to 07:11:12 UTC.
- Container `astra6_n20-20`: memory cap 24 GiB (25769803776 bytes), no swap; peak 3656929280 bytes (3.4 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as astra6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for astra6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 195 s: branch `oct7` created, files read, both data files checked, train.csv inspected, `output/results.tsv` and the research log started; ends "Say **go** to begin" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0.

**No question glossed over.** In turn 1 the agent called codex's question tool to propose `oct7` (options `oct7`, `oct7-run1`). The tool returned `{"accepted":true}` and the agent went on with `oct7`. Its final message only asked for the go-ahead.

## Results

- 40 rows in results.tsv (baseline + 39 experiments): 17 keep, 23 discard, 0 crash; 40 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6786 → 0.6786 → 0.6831 → 0.6838 → 0.6844 → 0.6851 → 0.6853 → 0.6861 → 0.6863 → 0.6864 → 0.6865 → 0.6865 → 0.6868 → 0.6869 → 0.6876 → 0.6876
- Best: `fc0e2f7` "Remove inactive categorical-partition threshold under all-one-hot splitting", Eval 0.6876, Holdout 0.6853 (gap -0.0023; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6769, 0.6769, 0.6812, 0.6816, 0.6832, 0.6828, 0.6836, 0.6846, 0.6849, 0.6844, 0.6845, 0.6845, 0.6847, 0.6848, 0.6853, 0.6853
- Best model: one XGBoost **ranker** (`rank:pairwise`, one sampled pair per row, mean pair method), trained on train split at random into 32 ranking groups. Its score goes through a sigmoid to give a probability.
  - It runs 600 rounds of 4 parallel lossguide trees with 32 leaves at learning rate 0.05, with `min_child_weight` 30, `reg_lambda` 10, `subsample` 0.8, `colsample_bynode` 0.8, and one-level categorical splits (`max_cat_to_onehot` 10000).
  - Inputs:
    - `DayOfWeek`, `UniqueCarrier`, `Origin` and `Dest` as categories; a carrier-origin category, with levels from train
    - `CRSDepTime` and `Distance`; `Month` and `DayofMonth` as numbers
    - each airport's shortest-path distance to LAX, ORD and ATL over the train route-distance graph
  - No holiday features: row-local holiday distances (`14b2b5a`) were tried and discarded.
  - The only run of the group whose best model uses a ranking objective rather than logistic loss.
- Gains, adding up to +0.0133:
  - 600 depth-4 trees with regularization: +0.0043
  - day of month as a number: +0.0045, the largest
  - `max_cat_threshold` 8: +0.0007
  - month as a number: +0.0006
  - depth 6: +0.0007
  - 4 parallel trees: +0.0002
  - landmark distances: +0.0008, filled through the route network: +0.0002
  - one-hot splits: +0.0001
  - the pairwise ranking objective: +0.0001, with 32 random groups: +0.0003
  - lossguide with 32 leaves: +0.0001
  - the carrier-origin category: +0.0007
- Three kept ties, each simpler or faster, as program.md allows:
  - `c633883` simpler category preparation: evaluation 30.9 s → 7.9 s
  - `66f3964` cached category codes: evaluation 9.4 s → 7.6 s
  - `fc0e2f7` (the best commit): without the `max_cat_threshold` parameter, which has no effect when every categorical split is one-hot. Same Eval and Holdout AUC as `45a8abb`.

  Equal results that added complexity were discarded (`aa90845`, `9bf2f2b`, `16362e5`, `fe68a1c`, `3d9f2c9`).
- Timing (report.txt): total 0h59m25s; XGBoost runs 0h15m53s (26.7%); AI 0h43m32s (73.3%)
- Clock stopped by the agent after 3565 s, 35 s of the 3600 s budget left (not an early stop). The last run (`fc0e2f7`) ended at 3477 s. Final summary written in the research log.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 39 agent commits (branch and reflog) touch only train.py. 40 artifacts for 40 completed runs, all inside the clock. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed each of the 7 commands leak_check lists:
  - setup: `rg --files` limited to docs and config, `cat` of program.md, README.md, .gitignore, train.py and harness.py, `ls -l data/train.csv data/eval.csv`, the branch and results header
  - the holiday search below
  - the plan for the holiday-distance experiment
  - the final verification
- Data reads: only `data/train.csv` (a profile, samples for its artifact checks). eval.csv was only listed with `ls -l`. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `head` of train.csv in its profile.
- Web: 21 `web__run` calls with 12 searches, 9 opens and 1 find (some calls combine them). Pages opened:
  - XGBoost docs: parameter tuning, parameters, categorical data, interaction constraints, tree methods
  - Google's ML crash course on feature crosses
  - SciPy `shortest_path`; scikit-learn voting ensembles and target-encoder cross-fitting
  - the UC Berkeley iSchool flight-delay page, which failed to load
  - **One search was limited to bts.gov** ("Thanksgiving Christmas July 4 holiday air travel busiest days"). It returned only snippets:
    - the TranStats holiday-delay detail page with empty filters (column header only)
    - BTS archive pages on holiday travel (the 2001 America on the Go survey, OmniStats)

    No BTS page was opened. The research log cites a BTS Thanksgiving-travel item as motivation for the holiday-distance experiment, which was discarded. No flight records and no 2005 or 2006 figures.
- No flight data from S3, BTS, Kaggle or elsewhere, and no carrier-code mapping.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt. "holdout" appears only in the final verification's text.
- diff-stat.txt (first commit to best): train.py only (+76 -12).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct7` = the 17 kept commits in results.tsv order; HEAD = `fc0e2f7` = last keep.
  - No discarded commit on the branch, nothing of output/ committed, no stray files, and every harness run is logged in results.tsv.
- Kept ties: three, all simpler or faster (see Results), so no `keep_rule`.
- Clock stopped by the agent (`clock_stopped_by` = agent), 35 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- No context compaction in the session log.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- turns/1.err holds only codex's "Reading additional input from stdin..."; turns/2.err is empty.
