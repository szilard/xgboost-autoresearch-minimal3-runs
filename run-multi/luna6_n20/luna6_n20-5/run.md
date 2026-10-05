# luna6_n20-5

**Valid** (no flags). Best Eval AUC **0.6803** (`8bfaefd`), Holdout AUC **0.6789**, gap **-0.0014**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-luna`, effort `max` (levels it has: low medium high xhigh max)
- turn_context as confirmed from the session log: `[('gpt-6-luna', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct5`
- Date: 2026-10-05, driver 12:12:44 to 13:19:21 UTC; clock 12:14:57 to 13:13:28 UTC
- Container `luna6_n20-5`: memory cap 24 GiB (25769803776 bytes), no swap; peak 12549005312 bytes (11.7 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as luna6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for luna6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 85 s: branch `oct5` created, files read, the two data files checked, `output/results.tsv` with header and an empty research log; ends "Confirm when you're ready for me to start the clock and launch it" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0, no capacity error in the session log.

**No question glossed over.** The agent picked the tag `oct5` and created the branch without asking to agree on it; its only question was the confirmation to start, which "go" answers.

## Results

- 25 rows in results.tsv (baseline + 24 experiments): 8 keep, 15 discard, 2 crash; 25 harness runs: 23 ok, 2 crash
- Kept Eval AUC: 0.6743 → 0.6745 → 0.6747 → 0.6789 → 0.6797 → 0.6799 → 0.6799 (tie, a simplification: see protocol checks) → 0.6803. Three other results equal to the last keep were discarded, as the keep rule requires: one at 0.6789 and two at 0.6797.
- Best: `8bfaefd` "remove carrier target rate; retain origin rate", Eval 0.6803, Holdout 0.6789 (gap -0.0014; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6734, 0.6735, 0.6773, 0.6783, 0.6790, 0.6791, 0.6789
- Best model: one XGBoost model, 200 depth-4 trees at learning rate 0.05, on the starter's eight columns plus:
  - the departure hour as a category
  - a smoothed delay rate of the origin airport (smoothing 100), cross-fitted on train
- Gains, adding up to +0.0060:
  - departure hour category (with a sine / cosine pair, then without it): +0.0004
  - depth 4: +0.0042
  - 200 trees at learning rate 0.05: +0.0008
  - delay rates of carrier, origin and destination: +0.0002; without the destination rate: equal; without the carrier rate: +0.0004
- The two crashes were one idea (sine / cosine of the month), fixed at the third attempt: `Month` is text of the form `c-11`, so first the arithmetic and then the integer cast failed. The fixed version tied at 0.6797 and was discarded.
- Timing (report.txt): total 0h58m31s; XGBoost runs 0h15m44s (26.9%); AI 0h42m47s (73.1%)
- Clock stopped by the agent after 3511 s, 89 s of the 3600 s budget left (not an early stop: under 2 minutes remained). The last run (`9ee21dd`) ended 121 s before the budget ran out. Final summary written in the research log.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 24 agent commits (branch and reflog) touch only train.py. 23 artifacts for the 23 completed runs, all inside the clock (the two crashed runs saved none). No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script, no row of eval.csv or holdout.csv in the log.
- The 3 commands leak_check lists, each reviewed:
  - the setup reads: `sed` of train.py and harness.py, `ls data/train.csv data/eval.csv`, and `rg --files -g 'AGENTS.md' -g '!human/**' -g '!results/**'`, a search for a file name that leaves `human/` and `results/` out
  - an `rg` of the agent's own train.py and `output/results.tsv`
  - the last reset to the best commit, with the logging of the last result
- Data reads: only `data/train.csv`, in six scratch commands (range of `CRSDepTime`, the `Month` values, counts of routes, carrier-hours and origin-hours). eval.csv was never opened. No curl, wget, pip or git clone; `write_stdin` was only used to poll running harness runs.
- Flight rows in table form (leak_check only looks for CSV rows): none.
- Web: 14 `web__run` calls: 8 searches (one came back empty and was repeated), 5 page opens, 1 find. Pages opened:
  - XGBoost docs: parameter tuning, parameters, categorical data, feature interaction constraints
  - scikit-learn `TargetEncoder` docs and its cross-fitting example
  - flight-delay studies: the UC Berkeley iSchool project page, a conference paper (SDSU), an IET paper, the TRID record of a 2006 econometric study

  A page of flyerintel.com (airline reliability by hour) failed to load, so nothing of it was read. BTS appears only as the title of a search result that was not opened. No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt. "holdout" occurs only in the agent's note "No holdout was used".
- diff-stat.txt (first commit to best): train.py only (+46 -3).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct5` = the 8 kept commits in results.tsv order; HEAD = `8bfaefd` = last keep; no discarded or crashed commit on the branch; nothing of output/ committed; no stray files; every harness run is logged in results.tsv.
- **One kept tie, allowed:** `6dd6c96` removed the destination delay rate from `11f9f8f` and scored the same 0.6799. Removing a feature at no cost in AUC is the simplification the keep rule asks for. The evaluation also got slightly faster (47.3 s → 46.0 s).
- Clock stopped by the agent (`clock_stopped_by` = agent), 89 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- The lowest result of the group so far, with luna6_n20-2 (both Holdout 0.6789), and again a slow run: 25 experiments, 73.1% of the hour outside the harness runs.
- The origin delay rate is cross-fitted in an unusual way. Each row's fold is a hash of its own eight feature values modulo 5, and the row gets the rate fitted on the train rows of the other four folds. Evaluation rows are treated the same way, so every row's feature depends only on that row and on lookups fitted on train. `prepare` reads no file.
- The session log has one context compaction, at 13:08:12.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
