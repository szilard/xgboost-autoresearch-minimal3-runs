# sol6_n20-2

**Valid** (no flags). Best Eval AUC **0.6858** (`b602c3f`), Holdout AUC **0.6836**, gap **-0.0022**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-sol`, effort `max` (levels it has: low medium high xhigh max ultra; `max` is not the highest)
- turn_context as confirmed from the session log: `[('gpt-6-sol', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `8d9c760`)
- Run tag / branch: `oct5`
- Date: 2026-10-05, driver 15:39:01 to 16:49:16 UTC; clock 15:42:55 to 16:43:23 UTC
- Container `sol6_n20-2`: memory cap 24 GiB (25769803776 bytes), no swap; peak 12543324160 bytes (11.7 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as run 1
- Driver: `run_one.sh` of commit `1030646`

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup in 2m52s: read program.md, README, `train.py`, `harness.py`, checked the two data files, `output/results.tsv` with header; did **not** create the branch; ends "**Please confirm that run tag** [`oct5`] so I can create the branch ... I'll wait for a separate "go" before starting the one-hour clock" |
| 2 | `go` | created `oct5`, started the clock and ran the whole hour; stopped the clock itself, 28 s after the budget ran out |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0, turns/2.err empty.

**The run-tag question was glossed over by "go" (benign).** As in run 1, the agent first asked through codex's `request_user_input_async` tool ("Can I use `oct5` as the new run tag?"), which nobody sees in `codex exec`; it waited with two 30 s `sleep` calls, then asked again in its final message. "go" answered it only by implication: the agent took it as approval of `oct5` and of the start. Both waits were before the clock started; the tag is only the branch name.

## Results

- 34 rows in results.tsv (baseline + 33 experiments): 9 keep, 25 discard, 0 crash; 34 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6793 → 0.6829 → 0.6835 → 0.6840 → 0.6841 → 0.6843 → 0.6852 → 0.6858
- Best: `b602c3f` "reg_alpha 6 in all ensemble members", Eval 0.6858, Holdout 0.6836 (gap -0.0022; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6783, 0.6819, 0.6823, 0.6829, 0.6831, 0.6833, 0.6837, 0.6836
- Best model: the equal average of three XGBoost models, 200 trees each at learning rate 0.05, `min_child_weight` 5, `reg_alpha` 6, native categoricals: depth 4; depth 3; depth 4 with `subsample` 0.8, `colsample_bytree` 0.8 and another seed. Features: the starter's eight columns plus a numeric day of year (from the month and day strings, with a fixed non-leap-year table).
- Gains, adding up to +0.0115:
  - smaller learning rate with shallower trees (300 depth-4 trees at 0.05, `min_child_weight` 5): +0.0050, then 200 trees instead of 300: +0.0006
  - day of year: +0.0036
  - L1 regularization (`reg_alpha` 1, 3, 6): +0.0017 (+0.0002, +0.0009, +0.0006); 10 was worse
  - averaging with a depth-3 model, then a third subsampled model: +0.0006 (+0.0005, +0.0001)
- Timing (report.txt): total 1h00m28s; XGBoost runs 0h21m44s (36.0%); AI 0h38m44s (64.0%)
- Clock stopped by the agent after 3628 s, 28 s **past** the 3600 s budget (`clock_remaining_s` -28). The agent's last status check (16:40:43) showed 2m12s remaining, so by program.md's loop it could start one more experiment: `cd7df53` started 88 s before the budget ran out and ended 50 s before it. The next status check showed 41 s left; the agent logged the discard, reset, wrote the final summary and stopped the clock at 16:43:23, 6 s after the driver's TIME IS UP. No harness run after the budget.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 33 agent commits (branch and reflog) touch only train.py; 34 artifacts for 34 runs, all inside the clock; every harness run is in results.tsv; the train.py of all 33 commits has no read of another file or the network.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script, no CSV row of eval.csv or holdout.csv in the log.
- The 8 commands leak_check lists, all reviewed: the setup reads (`cat program.md`, README, `.gitignore`, `train.py`, `harness.py`, `find data ...`, `ls data/train.csv data/eval.csv`, an existence check), a script that loads the agent's own artifact `artifacts/d19cef7*.pkl` to print two XGBoost config values (`max_cat_threshold`, `max_cat_to_onehot`), one web search (below), three patches to the research log that cite URLs, and the final check that the best artifact exists.
- Data reads: only `data/train.csv`, in three scratch commands (15:43 shape, dtypes, `head(3)`, category counts; 15:49 route and carrier-origin counts; 16:08 weekday of 24 November in train, for a Thanksgiving feature). eval.csv was never opened. No curl, wget, pip or git clone. All 184 shell commands looked through: harness runs, polling them (`write_stdin`), logging, git commit / reset of train.py.
- **Web: the agent looked for prior work on this exact dataset.** 17 `web__run` calls: 12 searches, 3 opens (UC Berkeley iSchool flight-delay project, XGBoost parameter, categorical, tree-method and DART pages) and 2 `find`s in a page. At 16:00 it searched for Kaggle solutions, then for `"dep_delayed_15min" XGBoost feature engineering Kaggle solution` and `"dep_delayed_15min" "AUC" xgboost Origin Dest` (the target column's name), plus `site:github.com flight delay prediction xgboost 2005 2006 departure delayed 15min kaggle`. The results were pages about the mlcourse.ai Kaggle in-class competition "Flight delays" (same columns, `c-N` coding and target), its write-ups, JuML and ModelFox benchmark pages. At 16:16 it ran `find` for "blend" and "Logistic" on the mlcourse.ai assignment page (how the competition's second benchmark blended logistic regression with XGBoost).
  - That page prints `train.head()` and `test.head()` of the mlcourse.ai data: **10 flight rows** ended up in the log (as a table, which leak_check does not look for). I checked all 10 in a throwaway `agents3` container against train.csv, eval.csv and holdout.csv on month, day, weekday, carrier, origin, destination and distance: **none of them is in any of the three files**. By their weekdays, 3 train rows fall on 2005 dates, 2 train rows on 2006 dates (or 2000; so the mlcourse.ai train data likely includes 2006 flights) and the 5 test rows on 2007 (or 2001) dates.
  - No data file was downloaded or opened (the page names `flight_delays_train.csv` on GitHub; it was not fetched). Reading pages for ideas is allowed, so this is not a flag. The searches by the target's column name show that the agent recognized the dataset and went looking for solutions to it.
  - One search was restricted to `site:transtats.bts.gov` (holiday travel delays); the result was BTS's "Holiday Delay" application page with its table of holiday travel-season dates, no flight records, and nothing was opened from BTS.
- No tool call mentions `human/`, `/opt` or `holdout`: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+44 -5).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct5` = the 9 kept commits in results.tsv order; HEAD = `b602c3f` = last keep; no discarded commit on the branch; nothing of output/ committed; no stray files.
- No kept ties. Three experiments tied the current best and were discarded for adding code or time (`min_child_weight` 10, holiday travel windows, gamma 1).
- Clock stopped by the agent (`clock_stopped_by` = agent), 28 s late (see Results); not an early stop.
- No retry waits (`retry_wait_s` 0).

## Other notes

- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- No context compaction in the session log. run.log has no pandas warnings (`prepare` masks unseen categories with `.where(isin)` as the starter does).
- Holdout stops gaining after `e4ed85d` (reg_alpha 3): the last keep adds +0.0006 on eval and -0.0001 on holdout.
