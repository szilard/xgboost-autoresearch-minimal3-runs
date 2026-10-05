# sol6_n20-3

**Valid** (no flags). Best Eval AUC **0.6857** (`72d7e0a`), Holdout AUC **0.6841**, gap **-0.0016**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-sol`, effort `max` (levels it has: low medium high xhigh max ultra; `max` is not the highest)
- turn_context as confirmed from the session log: `[('gpt-6-sol', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `8d9c760`)
- Run tag / branch: `oct5`
- Date: 2026-10-05, driver 16:49:26 to 17:56:57 UTC; clock 16:53:06 to 17:51:39 UTC
- Container `sol6_n20-3`: memory cap 24 GiB (25769803776 bytes), no swap; peak 6396968960 bytes (6.0 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as run 1
- Driver: `run_one.sh` of commit `1030646`

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup in 2m36s: read `train.py` and `harness.py`, checked the two data files and the packages, `output/results.tsv` with header; did not create the branch; ends "`program.md` calls for agreeing on the run tag before creating the branch. Is `oct5` good, or would you prefer another tag?" |
| 2 | `go` | created `oct5`, started the clock and ran the hour; stopped the clock itself with 86 s left |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0. turns/2.err: one failed `apply_patch` at 16:56:19 (the context lines of an edit to the research log didn't match); harmless, the agent redid it.

**The run-tag question was glossed over by "go" (benign).** As in runs 1 and 2, the agent first asked through codex's `request_user_input_async` ("Is `oct5` okay as the new experiment's branch and run tag?"), which nobody sees in `codex exec`, waited 30 s with `sleep`, then asked again in its final message. It took "go" as approval of `oct5`. The wait was before the clock started.

## Results

- 35 rows in results.tsv (baseline + 34 experiments): 8 keep, 27 discard, 0 crash; 35 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6752 → 0.6789 → 0.6822 → 0.6843 → 0.6843 (tie, see protocol checks) → 0.6856 → 0.6857
- Best: `72d7e0a` "remove scheduled departure hour", Eval 0.6857, Holdout 0.6841 (gap -0.0016; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6731, 0.6777, 0.6817, 0.6833, 0.6833, 0.6840, 0.6841
- Best model: one XGBoost model, 300 depth-3 trees at learning rate 0.05, native categoricals, on the starter's columns with day of month as a number instead of a category, plus a numeric day of year (from the month and day strings, with a fixed non-leap-year table). The departure hour and minute added in the first keep were removed again by the end.
- Gains, adding up to +0.0114:
  - smaller and shallower trees: +0.0058 (300 depth-4 trees at 0.05: +0.0037; depth 3: +0.0021)
  - day of year: +0.0033
  - day of month as a number instead of a category: +0.0013
  - departure hour and minute: +0.0009 (both later removed: the minute as unused at +0, the hour at +0.0001)
- Timing (report.txt): total 0h58m34s; XGBoost runs 0h23m10s (39.6%); AI 0h35m24s (60.4%)
- Clock stopped by the agent after 3514 s, 86 s of the 3600 s budget left (not an early stop: under 2 minutes remained). The last run (`938c50c`) ended 127 s before the budget ran out.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 34 agent commits (branch and reflog) touch only train.py; 35 artifacts for 35 runs, all inside the clock; every harness run is in results.tsv; the train.py of all 34 commits has no read of another file or the network.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script, no row of eval.csv or holdout.csv in the log.
- The 7 commands leak_check lists, all reviewed: a `git show-ref` for the branch name, the setup reads (`cat harness.py`, `ls -l data/train.csv data/eval.csv`, an existence check), four scripts that load the agent's own artifacts (`7044598`, `dab5518`, `a2c056e`) to print gain importances or the tree config, and the last patch to results.tsv and the research log.
- Data reads: only `data/train.csv`, in four scratch commands (16:53 shape, dtypes, missing values, unique counts, target balance, time range; 16:55 delay rates by hour and month; 17:02 route and carrier-airport counts; 17:18 weekday of 1 January and 24 November, for a holiday feature). eval.csv was never opened. No curl, wget, pip or git clone. All 130 shell commands looked through: harness runs, polling them (`write_stdin`), logging, git commit / reset of train.py.
- Web: 16 `web__run` calls, 10 searches, 4 opens and 2 `find`s. Pages read: XGBoost docs (categorical data, parameter tuning, parameters, DART) and a Promet – Traffic&Transportation paper on flight-delay prediction (PDF). Three opens failed (two MDPI papers: 429, an ACM DOI: 403). Searches: XGBoost and scikit-learn docs, arXiv, flight-delay papers on calendar, holiday and route features, ensembling, target encoding. No search for this dataset's solutions or for flight data; no flight rows in any web result. No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call mentions `human/`, `/opt` or `holdout`: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+9 -4).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct5` = the 8 kept commits in results.tsv order; HEAD = `72d7e0a` = last keep; no discarded commit on the branch; nothing of output/ committed; no stray files.
- **One kept tie, simpler code:** `59226f3` "remove unused departure minute feature" kept at 0.6843, equal to `a2c056e` before it. The research log: `DepMinute` had zero splits in the model, and removing it shortened evaluation. Allowed. Its holdout AUC is 0.6833, the same as the commit before.
- Clock stopped by the agent (`clock_stopped_by` = agent), 86 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- No context compaction in the session log. run.log has no pandas warnings (`prepare` masks unseen categories with `.where(isin)` as the starter does).
- The simplest best model of the group so far: a single model, and the final features are the starter's columns plus day of year.
- Peak memory 6.0 GiB, about half of runs 1 and 2 (11.2 and 11.7 GiB).
