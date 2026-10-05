# test1-1

**Valid** (no flags). Best Eval AUC **0.6856** (`8619c6e`), Holdout AUC **0.6847**, gap **-0.0009**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-sol`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-sol', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct4`
- Date: 2026-10-04, driver 21:07:15 to 22:15:10 UTC; clock 21:09:59 to 22:08:29 UTC
- Container `test1-1`: memory cap 24 GiB (25769803776 bytes), no swap; peak 12510085120 bytes (11.7 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected. Packages: xgboost 3.4.1, pandas 3.0.6, numpy 2.5.3, scikit-learn 1.9.1, cloudpickle 3.1.2

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt ("Hi have a look at program.md and let's kick off a new experiment! let's do the setup first.") | setup done on branch `oct4`, `output/results.tsv` with header, clock not started; asks for "go" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going" was needed. In turn 1 the agent asked whether it could use the tag `oct4` through codex's question tool (`request_user_input_async`). In `codex exec` nobody answers that question. The agent waited 30 s, wrote "I haven't heard back on the optional tag choice, so I'll use `oct4`", and finished the setup. "go" did not gloss over a real question.

## Results

- 41 rows in results.tsv (baseline + 40 experiments): 10 keep, 30 discard, 1 crash; 41 harness runs (40 ok, 1 crash), no timeouts
- Kept Eval AUC: 0.6743 → 0.6747 → 0.6789 → 0.6797 → 0.6832 → 0.6841 → 0.6843 → 0.6851 → 0.6852 → 0.6856, strictly increasing (no ties)
- Best: `8619c6e` "remove day of year after numeric month and day", Eval 0.6856, Holdout 0.6847 (gap -0.0009; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits follows Eval AUC closely: 0.6725, 0.6735, 0.6773, 0.6784, 0.6823, 0.6831, 0.6834, 0.6838, 0.6845, 0.6847
- Best model: a 75/25 blend of 150 depth-3 and 100 depth-4 XGBoost trees (learning rate 0.1), Month and DayofMonth as ordered numbers, a categorical departure hour, the other columns as in the starter
- The biggest gains came from shallower trees (depth 6 → 3: +0.0050), an ordered day-of-year feature (+0.0035), and then numeric month/day replacing it (+0.0013 in three steps). Feature crosses (route, carrier × hour), target-rate seasonality, cyclic encodings, regularization, DART, row subsampling and `max_cat_threshold` changes were all discarded.
- Timing (report.txt): total 0h58m30s; XGBoost runs 0h26m18s (45.0%, nearly all of it row-by-row eval at ~27-50 s per run); AI 0h32m12s (**55.0%**)
- Clock stopped by the agent after 3510 s, 90 s of the 3600 s budget left (not an early stop: under 2 minutes remained). The last run (`629fd07`) ended 151 s before the budget ran out.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 40 agent commits (branch and reflog) touch only train.py. No artifact or kept row from outside the clock, 40 artifacts for 40 completed runs. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 1, a false positive**. The hit is the generic line `import matplotlib.pyplot as plt`, which also occurs in `human/plot_auc_history.py`. In the session log it appears twice, both times in scikit-learn documentation pages returned by the agent's web searches (the TargetEncoder cross-fitting example at 21:36:55, the permutation-importance example at 21:49:36). It does not come from the human-only file. No rows of eval.csv or holdout.csv, and no lines of the other human-only scripts, are in the log.
- The 6 commands leak_check lists, each reviewed:
  - reading program.md, README.md, harness.py and train.py at setup
  - `ls -l data/train.csv data/eval.csv` (existence check, as program.md asks)
  - two `python3 -c` one-liners loading the agent's own artifact `artifacts/a4d724a*.pkl` (via glob) to print feature importances and `max_cat_threshold`. That is reading its own model, not data.
  - two web `find`/`open` calls on the XGBoost docs
- Data reads: only `data/train.csv`, in five `python3 -c` scratch commands. eval.csv was never opened.
- Web: 13 `web__run` calls. Ten are searches, three open or search within XGBoost docs pages (parameter, categorical and DART tutorials). Results came from XGBoost and scikit-learn docs, arXiv and other papers. There were no downloads and no flight data from S3, BTS, Kaggle or elsewhere.
- No tool call mentions `human/`, `/opt`, `holdout`, `2005.csv` or `2006`: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+22 -10).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. The branch `oct4` holds exactly the 10 kept commits in results.tsv order; HEAD = `8619c6e` = last keep; no discarded commit on the branch; nothing of output/ committed; no stray files.
- Clock stopped by the agent (`clock_stopped_by` = agent), 90 s remaining.
- Allowed by program.md, so no caveat: one crash, `1a0fa55` ("day of year initial parser did not handle c- prefix": the calendar columns are strings like `c-11`). It was fixed by the next commit `97717bc` and is not on the branch.

## Other notes

- turns/2.err: one failed `apply_patch` at 21:23:36. The context lines of the agent's edit to its own `output/research-log.md` didn't match; the agent redid the edit. No effect on the run.
- Two discarded experiments used more elaborate lookups, both fitted on `train` only, which is allowed. `c9471c1` added shortest-path distances from each origin to JFK/LAX/ATL over train's route graph (scipy dijkstra). `3ec537b` added the delay rate per day of year from train, smoothed over 21 days.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
