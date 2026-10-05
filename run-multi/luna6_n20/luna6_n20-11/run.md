# luna6_n20-11

**Valid** (no flags). Best Eval AUC **0.6805** (`0ea9a71`), Holdout AUC **0.6773**, gap **-0.0032**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-luna`, effort `max` (levels it has: low medium high xhigh max)
- turn_context as confirmed from the session log: `[('gpt-6-luna', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct5`
- Date: 2026-10-05, driver 18:56:22 to 19:58:46 UTC; clock 18:57:57 to 19:56:37 UTC
- Container `luna6_n20-11`: memory cap 24 GiB (25769803776 bytes), no swap; peak 4402081792 bytes (4.1 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as luna6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for luna6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 47 s: branch `oct5` created, files read, the two data files checked, `output/results.tsv` with header; ends "Confirm when you're ready, and I'll start the clock and run the baseline" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0, no capacity error in the session log.

**No question glossed over.** The agent picked the tag `oct5` and created the branch without asking to agree on it; its only question was the confirmation to start, which "go" answers.

## Results

- 34 rows in results.tsv (baseline + 33 experiments): 3 keep, 31 discard, 0 crash; 34 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6777 → 0.6805, strictly increasing (no kept ties). Two results equal to the last keep were discarded, as the keep rule requires (`colsample_bytree` 0.6; `max_cat_to_onehot` 1, slower).
- Best: `0ea9a71` "use colsample_bytree=0.8 without row subsampling", Eval 0.6805, Holdout 0.6773 (gap -0.0032; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6766, 0.6773
- Best model: the starter (100 depth-6 trees at learning rate 0.1, the starter's features) with `colsample_bytree` 0.8: one line added to train.py
- Gains, adding up to +0.0062:
  - row and column subsampling 0.8: +0.0034
  - without the row subsampling: +0.0028
- None of the other 31 experiments beat that:
  - features: departure time as minutes and sine / cosine, route category, delay rates, carrier × departure block, departure hour, day of year
  - tree shape: depth 4, 5 and 7, `min_child_weight`, gamma, loss-guided growth
  - other settings: DART, a random forest, `scale_pos_weight`, `max_bin`, other sampling settings
- Timing (report.txt): total 0h58m40s; XGBoost runs 0h18m54s (32.2%); AI 0h39m46s (67.8%)
- Clock stopped by the agent after 3520 s, 80 s of the 3600 s budget left (not an early stop: under 2 minutes remained). The last run (`ad5e9a9`) ended 119 s before the budget ran out. Final summary written in the research log.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: train_py_review`, **explained: a false match of the pattern,** as in luna6_n20-1 and -7. Both flagged lines are from the discarded `ba0eb2d` (delay rates) and contain the variable `global_delay_rate`; the check's pattern `glob` matches the word "global":
  - `global_delay_rate = target_binary.mean()`: the share of delayed flights in train
  - `return (stats["sum"] + global_delay_rate * prior_weight) / (stats["count"] + prior_weight)`: the smoothed rate per category, from train

  Lookups fitted on `train`, which program.md allows. No version of train.py reads anything but `data/train.csv`.
- The other lines of checks.txt: 33 agent commits (branch and reflog) touch only train.py. 34 artifacts for 34 completed runs, all inside the clock.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script, no row of eval.csv or holdout.csv in the log.
- The 3 commands leak_check lists, each reviewed:
  - the setup reads: `git status`, `git branch --list oct5`, `cat` of train.py and harness.py, `ls data/train.csv data/eval.csv`
  - `git show HEAD:train.py` and `git show --stat HEAD` (twice, with `tail` of train.py and of its own `output/run.log`): the agent checking its own last commit. Not a results file, which program.md forbids to look up in git.
- Data reads: only `data/train.csv`, in two scratch commands (types, `head(8)`, range of `CRSDepTime`, level counts; route counts). eval.csv was never opened. No curl, wget, pip or git clone; `write_stdin` was only used to poll running harness runs.
- Flight rows in table form (leak_check only looks for CSV rows): 8, the `head(8)` of train.csv printed by the agent's own scratch command. All eight are the first rows of train.csv and in neither eval.csv nor holdout.csv (checked in a throwaway container).
- Web: 23 `web__run` calls: 15 searches, 8 page opens. Pages opened:
  - XGBoost docs: parameter tuning, categorical data, parameters, DART; the XGBoost paper (arXiv 1603.02754) and the DART paper (PMLR v38)
  - flight-delay studies: two MDPI papers, a Springer, a ScienceDirect and a Wiley paper, arXiv 2105.08969, a ResearchGate page ("Probabilistic Flight Delay Predictions"), a TRID record, the UC Berkeley iSchool project page

  Two Kaggle pages (a flight-delay notebook and a write-up) came up in search results, one snippet with a table of column names, but neither was opened. No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call mentions `human/`, `/opt` or `holdout`: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+1).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct5` = the 3 kept commits in results.tsv order; HEAD = `0ea9a71` = last keep; no discarded commit on the branch; nothing of output/ committed; no stray files; every harness run is logged in results.tsv.
- Clock stopped by the agent (`clock_stopped_by` = agent), 80 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- The weakest run of the group: the lowest Holdout AUC (0.6773, against 0.6789 to 0.6844 for the others), the fewest keeps (3) and the largest gap (-0.0032). The gap is still inside the provisional threshold of -0.006. The one kept change after the subsampling (dropping the row subsampling) gained 0.0028 on eval but only 0.0007 on holdout.
- Unlike most runs of the group, depth 4 did not help here on top of `colsample_bytree` 0.8 (0.6799).
- The session log has one context compaction, at 19:41:54.
- turns/2.err: three failed `apply_patch` calls (19:05:06, 19:26:59, 19:30:21). The context lines of edits to train.py didn't match; harmless, and the agent redid them.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
