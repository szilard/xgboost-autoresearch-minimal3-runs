# sol6_n20-7

**Valid** (no flags). Best Eval AUC **0.6866** (`eb1987a`), Holdout AUC **0.6837**, gap **-0.0029**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-sol`, effort `max` (levels it has: low medium high xhigh max ultra; `max` is not the highest)
- turn_context as confirmed from the session log: `[('gpt-6-sol', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `8d9c760`)
- Run tag / branch: `oct5`
- Date: 2026-10-05, driver 21:34:30 to 22:47:30 UTC; clock 21:37:23 to 22:36:24 UTC
- Container `sol6_n20-7`: memory cap 24 GiB (25769803776 bytes), no swap; peak 6329700352 bytes (5.9 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as run 1
- Driver: `run_one.sh` of commit `1030646`

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup in 2m02s: read program.md, README, `.gitignore`, `train.py`, `harness.py`, looked for AGENTS.md (none), listed `data/`, checked the packages, `output/results.tsv` with header; did not create the branch; ends "**Please confirm `oct5` or give me another tag** so I can create the branch and finish setup." |
| 2 | `go` | created `oct5`, started the clock and ran the whole hour; stopped the clock itself with 59 s left |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0, turns/2.err empty.

**The run-tag question was glossed over by "go" (benign).** As in runs 1-6, the agent asked through `request_user_input_async` ("`oct5` is available as a fresh branch tag. Should I use it?"). It first tried to call it from inside its JavaScript tool, which failed ("tools.request_user_input_async is not a function"), then called it directly; nobody sees it in `codex exec`. It waited with two 30 s `sleep` calls, asked again in its final message, and took "go" as approval of `oct5` and of the start. The waits were before the clock started.

## Results

- 58 rows in results.tsv (baseline + 57 experiments): 19 keep, 39 discard, 0 crash; 58 harness runs, all ok. The most experiments of the group so far.
- Kept Eval AUC: 0.6743 → 0.6747 → 0.6789 → 0.6797 → 0.6800 → 0.6800 (tie) → 0.6801 → 0.6805 → 0.6810 → 0.6812 → 0.6820 → 0.6834 → 0.6857 → 0.6857 (tie) → 0.6860 → 0.6862 → 0.6864 → 0.6865 → 0.6866 (ties: see protocol checks)
- Best: `eb1987a` "160-round categorical alternate model", Eval 0.6866, Holdout 0.6837 (gap -0.0029; starter: 0.6743 / 0.6725, gap -0.0018). The highest Eval AUC of the group so far; the gap is the largest so far, but within the provisional threshold (-0.006).
- Holdout AUC of the kept commits: 0.6725, 0.6735, 0.6773, 0.6784, 0.6785, 0.6785, 0.6790, 0.6785, 0.6787, 0.6786, 0.6789, 0.6798, 0.6823, 0.6825, 0.6830, 0.6835, 0.6835, 0.6837, 0.6837. Where the gap opened: the four schedule-reference keeps (`9258a81` to `0734220`) gained +0.0012 on eval and +0.0001 on holdout; the week-of-month keeps gained on both (+0.0037 eval, +0.0034 holdout).
- Best model: a weighted soft vote (scikit-learn `VotingClassifier`, weights 3:1:1) of three XGBoost models at learning rate 0.1 with native categoricals: 130 depth-3 trees; 130 depth-4 trees; 160 depth-3 trees with `max_cat_to_onehot` 20 (one-hot splits for the smaller categoricals); different seeds. Features: the starter's columns without day of month, plus
  - week of month (days 1-7, 8-14, 15-21, 22-31 as 0-3), from the day string
  - the scheduled departure minute minus the median scheduled departure minute of the flight's carrier at its origin, a lookup fitted on train (no target involved)
- Gains, adding up to +0.0123:
  - shallower trees (depth 4, then 3): +0.0050
  - day of month replaced by week of month: +0.0040 (dropping day of month +0.0003; a week-of-month category +0.0014; merging days 29-31 into the fourth week +0.0023)
  - departure time relative to the carrier-origin median schedule: +0.0012 (four steps, from an origin median to the carrier-origin median in true minutes)
  - the three-model soft vote and its tuning: +0.0009
  - 130 rounds at depth 3: +0.0008
  - a categorical departure hour: +0.0004 (removed again later at a tie)
- Timing (report.txt): total 0h59m01s; XGBoost runs 0h33m36s (56.9%); AI 0h25m25s (43.1%)
- Clock stopped by the agent after 3541 s, 59 s of the 3600 s budget left (not an early stop: under 2 minutes remained). The agent's last status check (22:35:07) showed 2m16s remaining, so by program.md's loop it could start one more experiment: `9fe0f27` started 118 s before the budget ran out and ended 81 s before it.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 57 agent commits (branch and reflog) touch only train.py; 58 artifacts for 58 runs, all inside the clock; every harness run is in results.tsv; the train.py of all 57 commits has no read of another file or the network. The carrier-origin median is computed from `train` at module level and used in `prepare` as a lookup, which program.md allows.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script, no row of eval.csv or holdout.csv in the log.
- The 62 commands leak_check lists, all reviewed: the setup reads (`cat program.md`, README, `.gitignore`, a check for AGENTS.md, `rg --files data`, `train.py`, `harness.py`, `ls -l data/train.csv data/eval.csv`, an existence check), 58 `rg '^(Eval AUC:|Run time:)' output/run.log && git rev-parse && python3 harness.py status` checks after the runs (listed because of `rg`), and two commands that append to results.tsv and the research log (one also loads the agent's own artifact `cee3500` for gain importances).
- Data reads: only `data/train.csv`, in two scratch commands (21:38 shape, dtypes, unique counts, nulls; 21:46 carrier-origin, route and carrier-route counts). eval.csv was never opened. No curl, wget, pip or git clone. All 205 shell commands looked through.
- Web: 11 `web__run` calls, all searches (no page opened). Searches: XGBoost and scikit-learn docs, arXiv, MDPI, flight-delay papers on schedule, route and holiday features, one "flight delay Kaggle competition winning solution ... feature engineering xgboost" and one query ending "... airline 2005 2006" (papers). No search for this dataset's target column; no flight rows in any result. No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call mentions `human/`, `/opt` or `holdout`: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+36 -4).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct5` = the 19 kept commits in results.tsv order; HEAD = `eb1987a` = last keep; no discarded commit on the branch; nothing of output/ committed; no stray files.
- **Two kept ties, both simpler and faster:**
  - `8b3e575` "remove departure hour category with equal AUC and faster evaluation", 0.6800 as `cee3500` before it: one feature fewer. Same holdout (0.6785).
  - `c28639f` "use numeric four-bin month phase with equal AUC and faster scoring", 0.6857 as `e21a1c8` before it: the week-of-month category replaced by a number (0-3). Holdout 0.6825 against 0.6823.
- Clock stopped by the agent (`clock_stopped_by` = agent), 59 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- No context compaction in the session log. run.log has no pandas warnings (`prepare` masks unseen categories with `.where(isin)` as the starter does; an unseen carrier-origin pair gets a missing reference time, which XGBoost handles).
- The week-of-month feature is new in this group: runs 1-6 tried day of month as a category or a number and week of year, but no coarse within-month position. It gained about as much on holdout as on eval.
