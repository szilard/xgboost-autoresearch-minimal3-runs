# sol6_n20-15

**Valid** (no flags). Best Eval AUC **0.6878** (`c7c19c0`), Holdout AUC **0.6856**, gap **-0.0022**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-sol`, effort `max` (levels it has: low medium high xhigh max ultra; `max` is not the highest)
- turn_context as confirmed from the session log: `[('gpt-6-sol', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `8d9c760`)
- Run tag / branch: `oct6`
- Date: 2026-10-06, driver 07:01:23 to 08:11:26 UTC; clock 07:05:01 to 08:04:40 UTC
- Container `sol6_n20-15`: memory cap 24 GiB (25769803776 bytes), no swap; peak 12440420352 bytes (11.6 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as run 1
- Driver: `run_one.sh` of commit `1030646`

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup in 2m42s: read program.md, README, `harness.py`, `train.py`, checked the branch name, the data files and the output/ state; did not create the branch or results.tsv; ends "`program.md` requires us to agree on the run tag before I create the branch. **Can we use `oct6`?**" |
| 2 | `go` | created `oct6` and results.tsv, started the clock and ran the whole hour; stopped the clock itself with 21 s left |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0, turns/2.err empty.

**The run-tag question was glossed over by "go" (benign).** As in runs 1-14, the agent asked through `request_user_input_async` ("Can we use `oct6` as this experiment's run tag?"), which nobody sees in `codex exec`, waited with three 30 s `sleep` calls, then asked again in its final message. It took "go" as approval of `oct6` and of the start. The waits were before the clock started.

## Results

- 39 rows in results.tsv (baseline + 38 experiments): 12 keep, 27 discard, 0 crash; 39 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6808 → 0.6833 → 0.6841 → 0.6852 → 0.6854 → 0.6857 → 0.6864 → 0.6867 → 0.6869 → 0.6874 → 0.6878
- Best: `c7c19c0` "reg_lambda 30", Eval 0.6878, Holdout 0.6856 (gap -0.0022; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6787, 0.6826, 0.6830, 0.6842, 0.6842, 0.6847, 0.6849, 0.6854, 0.6852, 0.6852, 0.6856
- Best model: one XGBoost model, 200 loss-guided trees with at most 16 leaves at learning rate 0.05, `min_child_weight` 5, `reg_lambda` 30, `subsample` 0.8, `colsample_bytree` 0.4, native categoricals. Features: `CRSDepTime`, `Distance`, `DayOfWeek`, `UniqueCarrier`, `Origin`, `Dest`, departure hour as a category, and a numeric day of year (fixed non-leap-year table; the month and day-of-month categories dropped).
- Gains, adding up to +0.0135:
  - a regularized regime in one step (400 depth-4 trees at 0.05, `min_child_weight` 5, row and column sampling 0.8), later 200 rounds: +0.0067
  - day of year, replacing the month and day-of-month categories: +0.0044
  - column sampling 0.6, then 0.4: +0.0010
  - `reg_lambda` 10, then 30: +0.0009
  - departure hour as a category: +0.0003
  - loss-guided growth with 16 leaves: +0.0002
- Timing (report.txt): total 0h59m39s; XGBoost runs 0h21m27s (36.0%); AI 0h38m12s (64.0%). While its harness runs went, the agent waited with `sleep` calls of 20-25 s (34 in the hour) instead of polling the run.
- Clock stopped by the agent after 3579 s, 21 s of the 3600 s budget left (not an early stop: under 2 minutes remained). The agent's last status check before its last run (08:02:22) showed 2m39s remaining; `0d1de46` started 114 s before the budget ran out and ended 82 s before it.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 38 agent commits (branch and reflog) touch only train.py; 39 artifacts for 39 runs, all inside the clock; every harness run is in results.tsv; the train.py of all 38 commits has no read of another file or the network.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script, no row of eval.csv or holdout.csv in the log.
- The 7 commands leak_check lists, all reviewed: the setup reads (`cat program.md`, README, `harness.py`, `train.py`, `git show-ref`, a `git status --ignored` check of output/ and artifacts/), the web open of the Transtats page (below) and three patches to the research log that cite web pages.
- Data reads: only `data/train.csv`, in seven scratch commands (shape and dtypes; delay rate by hour; route and carrier-origin counts; hour ranges; the weekday of 1 January; delay rates around Thanksgiving in train). eval.csv was never opened. No curl, wget, pip or git clone. All 318 shell commands looked through.
- Web: 19 `web__run` calls, 15 searches, 3 opens and 1 `find`. Pages read: XGBoost docs (categorical data, parameters) and the Transtats "Holiday Delay" page; an MDPI article failed to load.
  - **BTS:** the Transtats page's text in the log is its navigation and the holiday travel-season date table, no delay counts (the words "On Time" / "Delayed" do not occur in it). One search ("... flight delays holidays thanksgiving research airport delays 2005 2006") listed BTS's "Table 3-1-3 Airline Delays by Cause: 2003-2007"; its snippet shows only the national 2003 totals (flights, delayed flights, cause shares). Nothing from it was opened, and no 2005 or 2006 figure appears in the log. The Thanksgiving feature built afterwards (`d4e2f30`, relative day to Thanksgiving, computed from each row's date) was discarded.
  - Other searches: XGBoost and scikit-learn docs, arXiv, MDPI, flight-delay papers, target encoding, Friedman's stochastic gradient boosting. No search for this dataset or for its solutions; no flight rows in any result. No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call mentions `human/`, `/opt` or `holdout`: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+20 -4).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct6` = the 12 kept commits in results.tsv order; HEAD = `c7c19c0` = last keep; no discarded commit on the branch; nothing of output/ committed; no stray files.
- No kept ties.
- Clock stopped by the agent (`clock_stopped_by` = agent), 21 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- No context compaction in the session log. run.log has no pandas warnings (`prepare` masks unseen categories with `.where(isin)`; the hour categories 0-23 cover every `CRSDepTime`).
