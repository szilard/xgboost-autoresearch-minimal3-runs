# luna6_n20-3

**Valid** (no flags). Best Eval AUC **0.6820** (`9c46a06`), Holdout AUC **0.6803**, gap **-0.0017**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-luna`, effort `max` (levels it has: low medium high xhigh max)
- turn_context as confirmed from the session log: `[('gpt-6-luna', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct5`
- Date: 2026-10-05, driver 09:57:46 to 11:05:51 UTC; clock 09:59:57 to 10:58:35 UTC
- Container `luna6_n20-3`: memory cap 24 GiB (25769803776 bytes), no swap; peak 12520439808 bytes (11.7 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as luna6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for luna6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | preflight done in 59 s: files read, the two data files checked, no branch and no `output/` yet; ends asking to confirm the tag `oct5` |
| 2 | `go` | took "go" as confirming `oct5`, created the branch and `output/results.tsv`, started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0, no capacity error in the session log.

**A question "go" glossed over:** unlike luna6_n20-1 and -2, this agent asked to agree on the tag before creating the branch ("I've proposed `oct5`; once you confirm, I'll create the branch"). It first tried codex's question tool, whose call failed on a malformed argument (turns/1.err, 09:58:53), then asked in its final message. On "go" it replied "Confirmed. I'll use `oct5`", did the rest of the setup and started the clock. Benign: the tag is only the branch name.

## Results

- 29 rows in results.tsv (baseline + 28 experiments): 11 keep, 18 discard, 0 crash; 29 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6789 → 0.6800 → 0.6803 → 0.6804 → 0.6806 → 0.6808 → 0.6809 → 0.6810 → 0.6814 → 0.6820, strictly increasing (no kept ties). Five results equal to the last keep were discarded as not simpler or faster, as the keep rule requires: one at 0.6800, two at 0.6803, one at 0.6804 and one at 0.6809.
- Best: `9c46a06` "equal-weight ensemble, secondary row sample 0.8 and column sample 0.4", Eval 0.6820, Holdout 0.6803 (gap -0.0017; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6771, 0.6787, 0.6787, 0.6782, 0.6785, 0.6788, 0.6791, 0.6792, 0.6796, 0.6803
- Best model: an equal-weight soft vote (scikit-learn `VotingClassifier`) of two XGBoost models, each 200 depth-4 trees at learning rate 0.05:
  - one on all rows and columns
  - one with `subsample` 0.8, `colsample_bytree` 0.4 and another seed

  Features: the starter's eight columns, sine and cosine of the departure time, and a smoothed delay rate of the origin airport (smoothing 500, fitted on train).
- Gains, adding up to +0.0077:
  - depth 4: +0.0046
  - learning rate 0.05 with 200 trees: +0.0011
  - sine / cosine departure time: +0.0003
  - origin delay rate: +0.0001
  - the two-model vote, in three steps: +0.0005
  - sampling of the second model (rows 0.8, columns 0.8 → 0.6 → 0.4): +0.0011
- Timing (report.txt): total 0h58m37s; XGBoost runs 0h18m48s (32.1%); AI 0h39m49s (67.9%)
- Clock stopped by the agent after 3517 s, 83 s of the 3600 s budget left (not an early stop: under 2 minutes remained). The last run (`2b4a23e`) ended 157 s before the budget ran out. Final summary written in the research log.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 29 agent commits (branch and reflog) touch only train.py. 29 artifacts for 29 completed runs, all inside the clock. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script, no row of eval.csv or holdout.csv in the log.
- The 3 commands leak_check lists, each reviewed:
  - the setup read: `git branch --list oct5`, `sed` of train.py and harness.py, `ls data/train.csv data/eval.csv`
  - two `rg` greps of the agent's own `output/research-log.md` (one with the wrap-up status)
- Data reads: only `data/train.csv`, in six scratch commands (level and route counts, the range of `CRSDepTime`, month and weekday values, support of airports, carriers and carrier-hours). eval.csv was never opened. No curl, wget, pip or git clone; `write_stdin` was only used to poll running harness runs.
- Flight rows in table form (leak_check only looks for CSV rows): none.
- Web: 12 `web__run` calls: 7 searches, 4 page opens, 1 find. Pages opened:
  - XGBoost docs: parameter tuning, categorical data, parameters
  - scikit-learn `VotingClassifier` docs
  - the CatBoost paper (NeurIPS 2018) and a target-encoding paper (arXiv 2104.00629)
  - flight-delay studies: a ScienceDirect and a Wiley paper, a TRID record of an econometric study, the UC Berkeley iSchool project page

  Kaggle and BTS appear only as the data sources those papers cite (and in one search-result snippet); neither site was opened. No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call mentions `human/`, `/opt` or `holdout`: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+38 -7).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct5` = the 11 kept commits in results.tsv order; HEAD = `9c46a06` = last keep; no discarded commit on the branch; nothing of output/ committed; no stray files; every harness run is logged in results.tsv.
- Clock stopped by the agent (`clock_stopped_by` = agent), 83 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- One commit was never run: `90d695d` "Test 2-to-1 ensemble weighting", committed at 10:58:00 with about 95 s left. The agent did not start it (less than 2 minutes remained), reset to the best commit and wrapped up. It is in the reflog only: no harness run, no artifact, no row in results.tsv. That is why checks.txt counts 29 agent commits for 28 experiments.
- The origin delay rate here is a plain lookup fitted on all of train (not cross-fitted as in luna6_n20-1), so training rows see a rate that includes their own label. It gained +0.0001 on eval and lost 0.0005 on holdout at that step.
- The session log has one context compaction, at 10:54:40.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
