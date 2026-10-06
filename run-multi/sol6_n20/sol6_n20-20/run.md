# sol6_n20-20

**Valid** (no flags). Best Eval AUC **0.6860** (`ac85c11`), Holdout AUC **0.6838**, gap **-0.0022**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-sol`, effort `max` (levels it has: low medium high xhigh max ultra; `max` is not the highest)
- turn_context as confirmed from the session log: `[('gpt-6-sol', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `8d9c760`)
- Run tag / branch: `oct6`
- Date: 2026-10-06, driver 12:50:09 to 13:57:19 UTC; clock 12:53:44 to 13:52:53 UTC
- Container `sol6_n20-20`: memory cap 24 GiB (25769803776 bytes), no swap; peak 12366548992 bytes (11.5 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as run 1
- Driver: `run_one.sh` of commit `1030646`

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | read program.md, README, `train.py`, `harness.py`, checked git state; asked about the run tag; **failed** at 12:51:59 ("model at capacity") before finishing setup |
| 2 | `go` (clock not started) | created the branch `oct6`; **failed** at 12:52:53 (capacity) |
| 3 | `go` (clock not started) | finished setup, started the clock (12:53:44), ran the baseline and 4 experiments (the last a crash); **failed** at 13:02:27 (capacity) |
| 4 | `keep going` (after 31 s) | fixed the crash and ran 22 experiments; **failed** at 13:46:08 (capacity) |
| 5 | `keep going` (after 31 s) | 3 more experiments; stopped the clock itself with 51 s left |

**Four failed turns**, all "Selected model is at capacity". `failed_turns` 4, `retry_wait_s` 62: the driver counts only waits while the clock runs, so the two failures before the clock started cost the hour nothing; the two during it cost 31 s each, under the 2-minute limit (no `turn_retries` flag). None cut off a harness run: the crash of `fbf65e3` (13:02:09) was a code error that came before the abort, and the run of `9c49e76` ended at 13:46:07, a second before the next abort, and was logged in turn 5. The second "go" (turn 3) was needed only because turn 2 failed, not because the agent misread the first one. turns/3.err and turns/5.err have codex's "failed to refresh available models: request timed out", background refreshes with no effect.

**The run-tag question went unanswered (benign).** As in runs 1-19, the agent asked through `request_user_input_async` ("Use `oct6` as the run tag? ... then pause before starting the one-hour clock."), which nobody sees in `codex exec`; turn 1 then failed, and the agent took the next "go" as approval of `oct6` and of the start. All before the clock started.

## Results

- 30 rows in results.tsv (baseline + 29 experiments): 7 keep, 22 discard, 1 crash; 30 harness runs (29 ok, 1 crash)
- Kept Eval AUC: 0.6743 → 0.6795 → 0.6812 → 0.6856 → 0.6857 → 0.6858 → 0.6860
- Best: `ac85c11` "add cyclic departure time sine and cosine", Eval 0.6860, Holdout 0.6838 (gap -0.0022; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6779, 0.6794, 0.6830, 0.6841, 0.6842, 0.6838. The last keep gained +0.0002 on eval and lost 0.0004 on holdout; the highest holdout is `9667470` (0.6842).
- Best model: one XGBoost model, 300 depth-3 trees at learning rate 0.05, `min_child_weight` 10, native categoricals. Features: the starter's columns with day of month as a number (instead of a category), plus a numeric day of year (fixed non-leap-year table) and the sine and cosine of the scheduled departure time on a 24-hour circle.
- Gains, adding up to +0.0117:
  - smaller learning rate with more and shallower trees (300 depth-4 trees at 0.05, then depth 3): +0.0069
  - day of month as a number: +0.0044; day of year added: +0.0001
  - cyclic departure time (sine, cosine): +0.0002
  - `min_child_weight` 10: +0.0001
- Timing (report.txt): total 0h59m09s; XGBoost runs 0h17m28s (29.5%); AI 0h41m41s (70.5%, including the two retry waits)
- Clock stopped by the agent after 3549 s, 51 s of the 3600 s budget left (not an early stop: under 2 minutes remained). The last run (`8cd9a08`) ended 99 s before the budget ran out.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 29 agent commits (branch and reflog) touch only train.py; 29 artifacts for the 29 completed runs (the crash has none), all inside the clock; every harness run is in results.tsv; the train.py of all 29 commits has no read of another file or the network.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script, no row of eval.csv or holdout.csv in the log.
- The 2 commands leak_check lists, both reviewed: the setup reads (`cat program.md`, README, ...) and the git-state check.
- Data reads: only `data/train.csv`, in three scratch commands. eval.csv was never opened. No curl, wget, pip or git clone. All 159 shell commands looked through.
- Web: 11 `web__run` calls, 8 searches and 3 opens. Pages read: XGBoost docs (parameters, categorical data), an IET Intelligent Transport Systems article and a PMC article on flight-delay prediction; the UC Berkeley iSchool page (403) and an MDPI article (429) failed.
  - Two searches looked for solutions on data like this one: "flight delay prediction 2005 2006 airline data feature engineering origin destination route Kaggle solution" and `site:github.com airline delay prediction xgboost 2005 2006 Month DayofMonth CRSDepTime feature engineering` (the dataset's column names). The results were other flight-delay projects; nothing about this dataset or its target column, no flight rows, and nothing from them was opened.
  - One search result was BTS's Transtats "Holiday Delay" page (not opened). No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call mentions `human/`, `/opt` or `holdout`: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+15 -5).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct6` = the 7 kept commits in results.tsv order, plus the crashed `fbf65e3` (see below); HEAD = `ac85c11` = last keep; nothing of output/ committed; no stray files.
- No kept ties. Two experiments tied the best and were discarded (`min_child_weight` 30, `gamma` 5).
- One crash fixed by the next commit (allowed): `fbf65e3` "numeric day conversion omitted c- prefix" crashed and stayed in the branch history; in the next turn the agent read the error and `1fefbc3` fixed the parsing and was kept. checks.txt notes it as "fine if the next commit fixes it".
- Clock stopped by the agent (`clock_stopped_by` = agent), 51 s remaining.
- Retry waits 62 s (`retry_wait_s`), under the 2-minute limit: no `turn_retries` flag.

## Other notes

- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- No context compaction in the session log. run.log has no pandas warnings (`prepare` masks unseen categories with `.where(isin)` as the starter does).
