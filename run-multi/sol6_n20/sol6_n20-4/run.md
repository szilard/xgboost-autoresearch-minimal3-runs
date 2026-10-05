# sol6_n20-4

**Valid** (no flags). Best Eval AUC **0.6831** (`07f5782`), Holdout AUC **0.6821**, gap **-0.0010**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-sol`, effort `max` (levels it has: low medium high xhigh max ultra; `max` is not the highest)
- turn_context as confirmed from the session log: `[('gpt-6-sol', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `8d9c760`)
- Run tag / branch: `oct5`
- Date: 2026-10-05, driver 17:57:07 to 19:03:19 UTC; clock 18:01:07 to 19:00:02 UTC
- Container `sol6_n20-4`: memory cap 24 GiB (25769803776 bytes), no swap; peak 4366184448 bytes (4.1 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as run 1
- Driver: `run_one.sh` of commit `1030646`

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup in 2m44s: read program.md, README, `train.py`, `harness.py`, listed the repo's files, looked for AGENTS.md files (none), checked the data files and the packages; did not create the branch or results.tsv; ends "**Can I use `oct5`?** It's available. Once you confirm, I'll create the branch and initialize `output/results.tsv`." |
| 2 | `go` | created `oct5` and results.tsv, started the clock (18:01:07), ran the baseline and two experiments; **failed** at 18:06:04 with "Selected model is at capacity" while the harness was running `eb5671d` |
| 3 | `keep going` (after a 31 s wait) | re-ran `eb5671d` and ran the rest of the hour; stopped the clock itself with 65 s left |

**One failed turn:** `failed_turns` 1, `retry_wait_s` 31 (under the 2-minute limit, no flag). turns/2.err has only a follow-on error of the abort ("failed to record rollout items: thread ... not found").

- What the failure cost: the harness run of `eb5671d` (started 18:05:32) was cut off when codex exited, after saving its artifact and before printing an Eval AUC; it is not in timing/runs.tsv. In turn 3 the agent tried to poll the old process (turns/3.err: "write_stdin failed: Unknown process id 37052"), found no AUC in run.log and no process left (`pgrep`), and re-ran the same commit at 18:07:20 (0.6789). In all about 2 minutes of the hour: the 31 s wait, the 32 s of the cut-off run and about 45 s of recovery.
- turns/3.err also has one failed `apply_patch` at 18:23:04 (the context lines of an edit to the research log didn't match); harmless, the agent redid it.

**The run-tag question was glossed over by "go" (benign).** As in runs 1-3, the agent first asked through `request_user_input_async` ("Can I use `oct5` as the tag for this run?"), which nobody sees in `codex exec`, waited with two 30 s `sleep` calls, then asked again in its final message. It took "go" as approval of `oct5` and of the start. The waits were before the clock started.

## Results

- 29 rows in results.tsv (baseline + 28 experiments): 5 keep, 23 discard, 1 crash; 29 harness runs (28 ok, 1 crash), plus the cut-off run above
- Kept Eval AUC: 0.6743 → 0.6789 → 0.6798 → 0.6830 → 0.6831
- Best: `07f5782` "200 trees eta 0.05", Eval 0.6831, Holdout 0.6821 (gap -0.0010; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6771, 0.6786, 0.6815, 0.6821
- Best model: one XGBoost model, 200 depth-3 trees at learning rate 0.05, native categoricals, on the starter's columns plus a numeric day of year (from the month and day strings, with a fixed non-leap-year table)
- Gains, adding up to +0.0088:
  - shallower trees: +0.0055 (depth 4: +0.0046; depth 3: +0.0009)
  - day of year: +0.0032
  - 200 trees at learning rate 0.05 instead of the starter's 100 at 0.1: +0.0001
- Timing (report.txt): total 0h58m55s; XGBoost runs 0h17m06s (29.0%); AI 0h41m49s (71.0%)
- Clock stopped by the agent after 3535 s, 65 s of the 3600 s budget left (not an early stop: under 2 minutes remained). The last run (`50d1635`) ended 131 s before the budget ran out.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 28 agent commits (branch and reflog) touch only train.py; 28 artifacts for the 28 completed runs (the crash has none; the cut-off run's artifact was overwritten by its re-run of the same commit), all inside the clock; every harness run is in results.tsv; the train.py of all 28 commits has no read of another file or the network.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script, no row of eval.csv or holdout.csv in the log.
- The 32 commands leak_check lists, all reviewed: the setup reads (`cat program.md`, `cat README.md`, `rg --files` of the repo, a check for AGENTS.md in the home and repo folders), a `git branch` / status check, and 30 `rg '^(Eval AUC:|Run time:...)' output/run.log` reads of the harness output after each run (listed because of `rg`), plus the final patch to the research log.
- Data reads: only `data/train.csv`, in four scratch commands (18:02 shape, dtypes, missing values, unique counts, target balance, time and distance ranges; 18:15-18:16 checking the `c-` prefix of the date columns after the crash; 18:22 counts of carrier-month, carrier-origin, route and origin-month combinations). eval.csv was never opened. No curl, wget, pip or git clone. All 252 shell commands looked through.
- Web: 11 `web__run` calls, 8 searches and 3 opens. Pages read: XGBoost docs (parameter tuning, twice; categorical data), two Stanford CS229 project reports on flight delays (2016, 2008) and a paper in the Journal of Basic and Applied Research; the UC Berkeley iSchool page failed (403). Searches: XGBoost docs, CS229, arXiv, flight-delay papers. No search for this dataset or for flight data; no flight rows in any web result. No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call mentions `human/`, `/opt` or `holdout`: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+7 -3).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct5` = the 5 kept commits in results.tsv order; HEAD = `07f5782` = last keep; no discarded commit on the branch; nothing of output/ committed; no stray files.
- No kept ties. One experiment tied the current best and was discarded (`min_child_weight` 10).
- One crash, fixed by the next commit (allowed): `59c7f08` "day-of-year parse failed on prefixed dates" (the date columns are `c-N` strings); `7403a9e` parsed them and was kept.
- Clock stopped by the agent (`clock_stopped_by` = agent), 65 s remaining.
- Retry waits 31 s (`retry_wait_s`), under the 2-minute limit: no `turn_retries` flag.

## Other notes

- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- No context compaction in the session log. run.log has no pandas warnings (`prepare` masks unseen categories with `.where(isin)` as the starter does).
- The lowest best Eval AUC of the group so far (0.6831) and the fewest experiments (28), with the highest AI share (71.0%); the smallest eval-holdout gap so far (-0.0010).
