# sol6_n20-11

**Valid** (no flags). Best Eval AUC **0.6893** (`cd0df4b`), Holdout AUC **0.6857**, gap **-0.0036**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-sol`, effort `max` (levels it has: low medium high xhigh max ultra; `max` is not the highest)
- turn_context as confirmed from the session log: `[('gpt-6-sol', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `8d9c760`)
- Run tag / branch: `oct6`
- Date: 2026-10-06, driver 02:18:35 to 03:29:27 UTC; clock 02:21:27 to 03:20:42 UTC
- Container `sol6_n20-11`: memory cap 24 GiB (25769803776 bytes), no swap; peak 6261608448 bytes (5.8 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as run 1
- Driver: `run_one.sh` of commit `1030646`

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup in 1m57s: read program.md, README, `train.py`, `harness.py`, looked for AGENTS.md under `/home/ubuntu` (none), listed `data/`, checked git state and packages; did not create the branch; ends "I propose **`oct6`** ... Confirm that tag (or give me another), and I'll create the branch and initialize `output/results.tsv`. The one-hour clock will stay off until setup is complete and you say go." |
| 2 | `go` | created `oct6` and results.tsv, started the clock and ran the whole hour; stopped the clock itself with 45 s left |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0, turns/2.err empty.

**The run-tag question was glossed over by "go" (benign).** As in runs 1-10, the agent asked through `request_user_input_async` ("I propose `oct6` based on today's date."), which nobody sees in `codex exec`, waited with two 30 s `sleep` calls, then asked again in its final message. It took the single "go" as approval of `oct6`, of the setup and of the start. The waits were before the clock started.

## Results

- 55 rows in results.tsv (baseline + 54 experiments): 16 keep, 38 discard, 1 crash; 55 harness runs (54 ok, 1 training timeout)
- Kept Eval AUC: 0.6743 → 0.6795 → 0.6812 → 0.6840 → 0.6844 → 0.6850 → 0.6851 → 0.6852 → 0.6854 → 0.6867 → 0.6870 → 0.6879 → 0.6880 → 0.6889 → 0.6892 → 0.6893
- Best: `cd0df4b` "subsample 0.7 with colsample 0.6", Eval 0.6893, Holdout 0.6857 (gap -0.0036; starter: 0.6743 / 0.6725, gap -0.0018). The highest Eval AUC of the group so far, and its largest gap so far, within the provisional threshold (-0.006).
- Holdout AUC of the kept commits: 0.6725, 0.6779, 0.6794, 0.6832, 0.6831, 0.6839, 0.6840, 0.6840, 0.6841, 0.6853, 0.6855, 0.6862, 0.6862, 0.6861, 0.6859, 0.6857. **Where the gap opened:** holdout peaked at 0.6862 (`a29b296`, `46d159f`); the last three keeps (`reg_alpha` 10, `colsample_bytree` 0.6, `subsample` 0.7) added +0.0013 on eval and lost 0.0005 on holdout.
- Best model: one XGBoost model, 500 depth-3 trees at learning rate 0.05, `subsample` 0.7, `colsample_bytree` 0.6, `reg_lambda` 50, `reg_alpha` 10, native categoricals. Features: `CRSDepTime`, `Distance`, `DayOfWeek`, `UniqueCarrier`, `Origin`, `Dest`, a numeric day of year (fixed non-leap-year table; month and day of month dropped), and a seven-level holiday-window category: none, or one of six fixed day-of-year ranges around Presidents' Day, Memorial Day, Independence Day, Labor Day, Thanksgiving and the winter holidays.
- Gains, adding up to +0.0150:
  - smaller learning rate, more and shallower trees (300 depth-4 trees at 0.05, then depth 3, then 500 trees): +0.0070
  - day of year, replacing the month and day-of-month categories: +0.0038
  - L2 and L1 regularization (`reg_lambda` 5, 20, 50; `reg_alpha` 10): +0.0023
  - the holiday-window category: +0.0013 (holdout +0.0012 for that step)
  - row and column sampling: +0.0006
- Timing (report.txt): total 0h59m15s; XGBoost runs 0h31m14s (52.7%); AI 0h28m01s (47.3%)
- Clock stopped by the agent after 3555 s, 45 s of the 3600 s budget left (not an early stop: under 2 minutes remained). The agent's last status check (03:19:18) showed 2m09s remaining, so by program.md's loop it could start one more experiment: `c5a84d0` started 111 s before the budget ran out and ended 77 s before it.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 54 agent commits (branch and reflog) touch only train.py; 54 artifacts for the 54 completed runs (the timed-out run has none), all inside the clock; every harness run is in results.tsv; the train.py of all 54 commits has no read of another file or the network.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script, no row of eval.csv or holdout.csv in the log.
- The 7 commands leak_check lists, all reviewed: the setup reads (`cat program.md`, README, `train.py`, `harness.py`, `find .. -name AGENTS.md` (nothing found) and `find data -maxdepth 2`, `git branch`, `ls data/train.csv data/eval.csv`), the branch creation, and four appends to results.tsv and the research log (two cite the BTS page).
- Data reads: only `data/train.csv`, in five scratch commands (02:21 shape, dtypes, missing values; 02:22 delay rates by hour and other fields; 02:25 delay rate by departure minute; 02:29 route and carrier-origin counts; 02:37 weekdays of 1 January and other dates in train). eval.csv was never opened. No curl, wget, pip or git clone. All 290 shell commands looked through.
- Web: 15 `web__run` calls, 10 searches and 5 opens. Pages read: XGBoost docs (categorical data, parameters, parameter tuning, DART), the scikit-learn cyclical-feature example, the Stanford CS229 2008 airline departure-delay report, and the Transtats "Holiday Delay" page (opened three times, at different lines); the UC Berkeley iSchool page failed (403).
  - **Transtats:** what the agent read from the page is its table of holiday travel-season dates by year (holiday, date, start and end of the travel period, 1999-2026); no delay counts or rates appear in the log (the words "On Time" / "Delayed" do not occur in those outputs). The six windows of the best model's holiday feature are the union of the page's 2005 and 2006 travel periods (e.g. Thanksgiving 17-29 November = 2005's 18-29 and 2006's 17-28). This is public calendar information, also for the eval year (which program.md names), not flight data.
  - One search ended "... flight delay holiday proximity feature 2005 2006" (`site:cs229.stanford.edu`): papers. No search for this dataset's target column or for its solutions; no flight rows in any result. No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call mentions `human/`, `/opt` or `holdout`: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+25 -4).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct6` = the 16 kept commits in results.tsv order; HEAD = `cd0df4b` = last keep; no discarded commit on the branch; nothing of output/ committed; no stray files.
- No kept ties. Two experiments tied the current best and were discarded "without simplification" (`reg_lambda` 100, `min_child_weight` 0.1).
- One crash, handled as program.md asks: `6bcb46d` "DART 500 trees" hit the 1-minute training limit; logged as `crash`, discarded and reverted. The next experiment (`7988bb0`, DART with 300 trees) ran fine and was discarded.
- Clock stopped by the agent (`clock_stopped_by` = agent), 45 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- No context compaction in the session log. run.log has no pandas warnings (`prepare` masks unseen categories with `.where(isin)`; the holiday category's levels 0-6 cover every day).
