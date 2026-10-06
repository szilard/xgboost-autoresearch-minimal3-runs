# luna6_n20-19

**Valid** (no flags). Best Eval AUC **0.6826** (`03bbc84`), Holdout AUC **0.6811**, gap **-0.0015**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-luna`, effort `max` (levels it has: low medium high xhigh max)
- turn_context as confirmed from the session log: `[('gpt-6-luna', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct6`
- Date: 2026-10-06, driver 03:47:07 to 04:56:34 UTC; clock 03:50:20 to 04:49:04 UTC
- Container `luna6_n20-19`: memory cap 24 GiB (25769803776 bytes), no swap; peak 6196858880 bytes (5.8 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as luna6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for luna6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 147 s: branch `oct6` created, files read, the two data files checked, `output/results.tsv` with header; ends "Confirm the setup, and I'll start the experiment clock and run the baseline" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0, no capacity error in the session log.

**No question glossed over.** The agent's call of codex's question tool failed on a malformed argument (turns/1.err, 03:48:11). It then chose the tag `oct6` itself, and its final message only asked for the go-ahead, which "go" gives.

## Results

- 28 rows in results.tsv (baseline + 27 experiments): 11 keep, 16 discard, 1 crash; 30 harness runs: 27 ok, 2 crash, 1 training timeout
- Kept Eval AUC: 0.6743 → 0.6789 → 0.6791 → 0.6798 → 0.6800 → 0.6802 → 0.6802 (tie, a simpler model: see protocol checks) → 0.6806 → 0.6807 → 0.6810 → 0.6826. Eight other ties were discarded as "tied … with no simplification", as the keep rule requires.
- Best: `03bbc84` "add first day-of-year harmonic", Eval 0.6826, Holdout 0.6811 (gap -0.0015; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6771, 0.6777, 0.6783, 0.6787, 0.6785, 0.6784, 0.6790, 0.6791, 0.6795, 0.6811
- Best model: an equal soft vote (scikit-learn `VotingClassifier`) of two XGBoost models, depth 3 and depth 4, each 800 trees at learning rate 0.0125 with `min_child_weight` 25. Features: the starter's columns plus two sine / cosine pairs of the departure time (daily period and half-day) and one of the day of year.
- Gains, adding up to +0.0083:
  - depth 4: +0.0046
  - `min_child_weight` 25: +0.0002
  - the departure-time harmonics: +0.0007, +0.0002
  - learning rate 0.05 with 200 trees: +0.0002, then depth 3: equal
  - learning rate 0.025 with 400, then 0.0125 with 800 trees: +0.0004, +0.0001
  - the depth-3 / depth-4 vote: +0.0003
  - sine / cosine of the day of year: +0.0016
- A holiday window (New Year, Memorial Day, July 4, Labor Day, Thanksgiving, Christmas from calendar rules) tied and was discarded.
- Timing (report.txt): total 0h58m45s; XGBoost runs 0h20m22s (34.7%); AI 0h38m23s (65.3%)
- Clock stopped by the agent after 3525 s, 75 s of the 3600 s budget left (not an early stop: under 2 minutes remained). The last run (`7d831ef`) ended 150 s before the budget ran out. Final summary written in the research log.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 29 agent commits (branch and reflog) touch only train.py. 27 artifacts for the 27 completed runs, all inside the clock (the crashed and timed-out runs saved none). No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script, no row of eval.csv or holdout.csv in the log.
- The 4 commands leak_check lists, each reviewed:
  - the two setup checks: `cat` of train.py and harness.py, `ls data/train.csv data/eval.csv`, `git branch --list oct6`, tests for existing output files
  - the search for the BTS day-of-week coding
  - the research-log entry citing it
- **BTS pages, checked in detail.** For a holiday window, the agent opened two BTS pages (04:31:56, 04:32:28).
  - The first is BTS's "Technical Directive #39 – On-Time Performance" (2025), the reporting rules for airlines. From it the agent took the day-of-week coding (Monday = 1 … Sunday = 7). It is a regulatory text, with no flight data.
  - The second is again TranStats' "Thanksgiving Flight Delays Details", as in luna6_n20-16. The output is the same: the empty table header ("Flight Date, Day of Week, Total Flights, Departures On Time / Delayed / Cancelled, …"), the 15-minute definition and the list of reporting carriers. No data rows. Read in full.
  - The holiday flag uses calendar rules only and was discarded.

  No flight data from BTS, S3, Kaggle or elsewhere. This is the third run (after luna6_n20-13 and -16) to open a BTS holiday-delay page.
- Data reads: only `data/train.csv`, in five scratch commands:
  - shape, types, missing values, `head(5)`
  - the departure-time range
  - carrier delay rates, route counts
  - the `Month` and `DayofMonth` values

  eval.csv was never opened. No curl, wget, pip or git clone; `write_stdin` was only used to poll running harness runs.
- Flight rows in table form (leak_check only looks for CSV rows): 5, the `head(5)` of train.csv printed by the agent's own scratch command (in the same tool call as a web open). All five are among the first rows of train.csv, already checked against eval.csv and holdout.csv for luna6_n20-11: none of them is an eval or holdout row.
- Web: 15 `web__run` calls: 10 searches, 5 page opens. Pages opened:
  - XGBoost docs: parameter tuning, categorical data
  - a Stanford CS229 project on airline delays (2008), a Microsoft Learn flight-delay tutorial, the scikit-learn `VotingClassifier` docs
  - the two BTS pages above
- No tool call mentions `human/`, `/opt` or `holdout`: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+27 -7).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct6` = the 11 kept commits in results.tsv order; HEAD = `03bbc84` = last keep; no discarded commit on the branch; nothing of output/ committed; no stray files.
- **One kept tie, allowed:** `fc4aaca` (0.6802, after `32beb38`) lowered `max_depth` from 4 to 3, "tied AUC with simpler trees". A depth-3 tree has at most half the leaves of a depth-4 tree, so the model is smaller by construction. That is a simplification at no cost in AUC, which the rule allows; the holdout AUC is the same within 0.0001 (0.6784 against 0.6785). The agent applied the rule strictly otherwise: it discarded eight other ties as "no simplification", among them gamma 1, `min_child_weight` 50, the holiday window and vote weights.
- **A timeout and two crashes, all allowed:**
  - `ffc8d70` (a DART ensemble) hit the 60-second training limit and was logged as `crash` and reverted, as program.md asks.
  - `51a4122` and `ed98a49` were the day-of-year feature crashing twice (the `c-` prefixes of `Month` and `DayofMonth`). The agent fixed it with `git commit --amend` and reran it as `03bbc84` (kept). The two crashed versions are in the reflog and the harness timing only, without a row in results.tsv, which program.md allows for an easy fix.
- Clock stopped by the agent (`clock_stopped_by` = agent), 75 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- The session log has one context compaction, at 04:41:32; turns/2.err is empty.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
