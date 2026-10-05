# sol6_n20-1

**Valid** (no flags). Best Eval AUC **0.6865** (`fa052d9`), Holdout AUC **0.6850**, gap **-0.0015**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-sol`, effort `max` (levels it has: low medium high xhigh max ultra; `max` is not the highest)
- turn_context as confirmed from the session log: `[('gpt-6-sol', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `8d9c760`)
- Run tag / branch: `oct5`
- Date: 2026-10-05, driver 14:29:13 to 15:38:53 UTC; clock 14:32:36 to 15:33:35 UTC
- Container `sol6_n20-1`: memory cap 24 GiB (25769803776 bytes), no swap; peak 12032356352 bytes (11.2 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; packages cloudpickle 3.1.2, numpy 2.5.3, pandas 3.0.6, scikit-learn 1.9.1, xgboost 3.4.1
- Driver: `run_one.sh` of commit `1030646`

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 2m30s: read program.md, README, `train.py`, `harness.py`, checked the two data files, created the branch `oct5` and `output/results.tsv` with header; ends "please confirm **go** to start the one-hour run, or tell me if you want a different tag" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself, 59 s after the budget ran out |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0. turns/2.err has one codex error at 14:32:23, "failed to refresh available models: request timed out": a background refresh of the model list, with no effect on the turn.

**A question about the run tag went unanswered (benign).** In turn 1 the agent called codex's `request_user_input_async` tool ("may I use `oct5` as the branch tag?", options "Use oct5" / "Choose another tag"). In `codex exec` nobody sees it: the tool only returned `{"accepted":true}`. The agent then called `sleep` for 30 s, got no answer, picked `oct5` itself and asked again in its final message, which "go" answered by implication. The 30 s were before the clock started, and the tag is only the branch name.

## Results

- 34 rows in results.tsv (baseline + 33 experiments): 9 keep, 25 discard, 0 crash; 34 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6774 → 0.6838 → 0.6848 → 0.6851 → 0.6857 → 0.6862 → 0.6864 → 0.6865
- Best: `fa052d9` "drop numeric month with day of year retained", Eval 0.6865, Holdout 0.6850 (gap -0.0015; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6776, 0.6837, 0.6844, 0.6846, 0.6842, 0.6844, 0.6849, 0.6850. Holdout stops gaining after `76e69bc` (depth 3, 0.6844): the last five keeps add +0.0017 on eval and +0.0006 on holdout.
- Best model: a fixed 70/30 average of two XGBoost models (150 depth-3 trees and 100 depth-4 trees, learning rate 0.1, native categoricals), on:
  - `CRSDepTime`, `Distance`, and `DayOfWeek`, `UniqueCarrier`, `Origin`, `Dest` as categories
  - numeric day of month and day of year (from the month and day strings, with a fixed non-leap-year table); month itself dropped
  - a weekday × 3-hour departure block category (levels fitted on train)
- Gains, adding up to +0.0122:
  - shallower trees: +0.0074 (depth 4: +0.0064; depth 3: +0.0010)
  - ordered (numeric) month and day of month: +0.0031
  - day of year: +0.0006
  - weekday × 3-hour block: +0.0005
  - 150 rounds at depth 3: +0.0003
  - the 70/30 depth-3/depth-4 average: +0.0002
  - dropping numeric month: +0.0001
- Timing (report.txt): total 1h00m59s; XGBoost runs 0h19m15s (31.6%); AI 0h41m44s (68.4%)
- Clock stopped by the agent after 3659 s, 59 s **past** the 3600 s budget (`clock_remaining_s` -59): the driver's "TIME IS UP" came at 15:33:07 and the agent stopped the clock at 15:33:35, inside the 10-minute grace. The agent's last status check (15:30:30) showed 2m06s remaining, so by program.md's loop it could start one more experiment: `fa052d9` (the best commit) started 41 s before the budget ran out and ended 5 s before it; the 59 s were spent logging the result, committing the research log entry and writing the final summary. No harness run after the budget.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 33 agent commits (branch and reflog) touch only train.py; 34 artifacts for 34 runs, all inside the clock; every harness run is in results.tsv; the train.py of all 33 commits has no read of another file or the network.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script, no row of eval.csv or holdout.csv in the log.
- The 3 commands leak_check lists, all reviewed: the setup reads (`cat program.md`, `cat README.md train.py .gitignore`, `find data -maxdepth ...`), `cat harness.py` with `ls -l data/train.csv data/eval.csv` (an existence check), and the last patch to the research log (it cites a URL).
- Data reads: only `data/train.csv`, in four scratch commands (14:33-14:52: shape, dtypes, `head(3)`, delay rates by month / hour / weekday / carrier, route counts, day-level delay rates). eval.csv was never opened. No curl, wget, pip or git clone. All 177 shell commands looked through: harness runs, polling them (`write_stdin`), logging to results.tsv and the research log, git commit / reset of train.py.
- Web: 11 `web__run` calls, 10 searches and 1 open of two XGBoost docs pages (categorical data, parameter tuning). Searches: XGBoost and scikit-learn docs, arXiv, NeurIPS and ScienceDirect papers on flight-delay features, CatBoost, ensembling. One query ends "... route season 2005 2006 paper": a search for papers, nothing downloaded. No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call mentions `human/`, `/opt` or `holdout`: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+29 -9).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct5` = the 9 kept commits in results.tsv order; HEAD = `fa052d9` = last keep; no discarded commit on the branch; nothing of output/ committed; no stray files.
- No kept ties. Four experiments tied the current best and were discarded (min child weight 5, subsample 0.8, categorical month, gamma 1), each with the reason "no gain, more code or more time".
- Clock stopped by the agent (`clock_stopped_by` = agent), 59 s late (see Results); not an early stop.
- No retry waits (`retry_wait_s` 0).

## Other notes

- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- No context compaction in the session log.
- Most of the hour's gain came from regularizing toward simpler trees (100 depth-6 trees → 150 depth-3), the opposite of luna6_n20-1, which gained most from subsampling with deep trees.
