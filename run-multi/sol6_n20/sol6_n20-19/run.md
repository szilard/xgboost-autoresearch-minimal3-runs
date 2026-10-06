# sol6_n20-19

**Valid** (no flags). Best Eval AUC **0.6889** (`c4b427d`), Holdout AUC **0.6866**, gap **-0.0023**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-sol`, effort `max` (levels it has: low medium high xhigh max ultra; `max` is not the highest)
- turn_context as confirmed from the session log: `[('gpt-6-sol', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `8d9c760`)
- Run tag / branch: `oct6`
- Date: 2026-10-06, driver 11:37:10 to 12:49:56 UTC; clock 11:39:16 to 12:38:17 UTC
- Container `sol6_n20-19`: memory cap 24 GiB (25769803776 bytes), no swap; peak 3848638464 bytes (3.6 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as run 1
- Driver: `run_one.sh` of commit `1030646`

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup in 1m21s: read program.md, README, `train.py`, `harness.py`, checked the data files and packages, created the branch `oct6` and `output/results.tsv` with header; ends "I used the proposed tag after allowing time for a preference ... Reply **go** to start the one-hour run, or give me a different tag before we begin." |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself with 58 s left |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0. turns/2.err has codex's "failed to refresh available models: request timed out" (11:39:15), a background refresh with no effect.

**The run-tag question went unanswered (benign).** As in runs 1-18, the agent asked through `request_user_input_async` ("I propose `oct6` as the new run tag ..."), which nobody sees in `codex exec`, waited 30 s with `sleep` ("after allowing time for a preference"), then created `oct6` itself and offered a different tag in its final message. The wait was before the clock started.

## Results

- 58 rows in results.tsv (baseline + 57 experiments): 22 keep, 36 discard, 0 crash; 58 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6789 → 0.6813 → 0.6842 → 0.6846 → 0.6847 → 0.6852 → 0.6856 → 0.6857 → 0.6861 → 0.6863 → 0.6865 → 0.6867 → 0.6869 → 0.6870 → 0.6875 → 0.6875 (tie, see protocol checks) → 0.6882 → 0.6886 → 0.6887 → 0.6888 → 0.6889
- Best: `c4b427d` "500 rounds in 2:1 blended models", Eval 0.6889, Holdout 0.6866 (gap -0.0023; starter: 0.6743 / 0.6725, gap -0.0018). The second-highest Eval AUC of the group (run 11: 0.6893) and the second-highest Holdout AUC (run 8: 0.6871).
- Holdout AUC of the kept commits: 0.6725, 0.6775, 0.6792, 0.6831, 0.6832, 0.6832, 0.6838, 0.6844, 0.6841, 0.6845, 0.6847, 0.6847, 0.6853, 0.6854, 0.6853, 0.6846, 0.6846, 0.6851, 0.6864, 0.6861, 0.6865, 0.6866. One step went against holdout: `reg_alpha` 10 (`7d3cd17`) gained +0.0005 on eval and lost 0.0007 on holdout; the blend with a lighter model (`8203f15`) then gained on both (+0.0004 eval, +0.0013 holdout).
- Best model: a 2:1 soft vote (scikit-learn `VotingClassifier`) of two XGBoost models, each 500 rounds of 3 parallel loss-guided trees (`num_parallel_tree` 3, at most 8 or 12 leaves, no depth cap) at learning rate 0.05, `subsample` 0.8, `colsample_bytree` 0.8, `min_child_weight` 10, native categoricals: a strongly regularized one (`reg_lambda` 200, `reg_alpha` 10, `gamma` 5, 8 leaves) and a lighter one (`reg_lambda` 50, no L1 or gamma, 12 leaves, another seed). Features: `CRSDepTime`, `Distance`, `DayOfWeek`, `UniqueCarrier`, `Origin`, `Dest`, departure hour as a 24-level category, and a numeric day of year (fixed non-leap-year table; the month and day-of-month categories dropped).
- Gains, adding up to +0.0146:
  - smaller learning rate, more and shallower trees (400 depth-4 trees at 0.05, then depth 3): +0.0070
  - day of year, replacing the month and day-of-month categories: +0.0033
  - regularization (`min_child_weight` 10; `reg_lambda` 10, 50, 200; `gamma` 5; `reg_alpha` 10): +0.0015
  - row and column sampling 0.8: +0.0009
  - loss-guided trees with 8 leaves and no depth cap: +0.0007
  - the 2:1 blend with a lighter loss-guided model, its 12 leaves and 500 rounds: +0.0007
  - departure time slots (half-hour, then hourly category): +0.0003
  - three parallel trees per round: +0.0002
- Timing (report.txt): total 0h59m02s; XGBoost runs 0h34m47s (58.9%); AI 0h24m15s (41.1%)
- Clock stopped by the agent after 3542 s, 58 s of the 3600 s budget left (not an early stop: under 2 minutes remained). The last run (`c4b427d`, the best commit) ended 89 s before the budget ran out.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 57 agent commits (branch and reflog) touch only train.py; 58 artifacts for 58 runs, all inside the clock; every harness run is in results.tsv; the train.py of all 57 commits has no read of another file or the network. A discarded version (`d1cd332`) used a cross-fitted smoothed origin delay rate fitted on train, a lookup that program.md allows.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script, no row of eval.csv or holdout.csv in the log.
- The 3 commands leak_check lists, all reviewed: the setup reads (`cat program.md`, README, `train.py`, `harness.py`, `ls -l data/train.csv data/eval.csv`, `git show-ref`) and a script loading the agent's own artifact `95b92f3` for feature importances.
- Data reads: only `data/train.csv`, in three scratch commands. eval.csv was never opened. No curl, wget, pip or git clone. All 198 shell commands looked through.
- Web: 11 `web__run` calls, all searches (no page opened): XGBoost and scikit-learn docs, arXiv, the CatBoost paper, flight-delay papers. No search for this dataset, its target column or its solutions, and no BTS site.
  - One search (12:06, `site:arxiv.org scheduled flight delay prediction calendar holiday day of week airport airline feature interactions`) returned, among others, three pages about this benchmark dataset: a 2016 random-forest article (its table of features), the R Consortium talk "GBM in the age of LLMs" (szilard) and a DAML 2024 paper whose snippet shows two DepTime values of the mlcourse.ai rows already checked in run 2 (not in train, eval or holdout). No flight rows in the log (no `c-N` rows).
  - The agent took one idea from the talk's snippet ("some feature engineering (e.g., cutting the original DepTime into 48 categories)"): its research log cites "A R Consortium talk on this airline dataset ... reports feature engineering with half-hour departure slots", and it tried a 48-level half-hour slot (`101f75b`, +0.0002, kept), later replaced by an hourly category (`a1f3820`, +0.0001). Reading for ideas is allowed; noted because the source is about this dataset.
  - No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call mentions `human/`, `/opt` or `holdout`: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+34 -5).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct6` = the 22 kept commits in results.tsv order; HEAD = `c4b427d` = last keep; no discarded commit on the branch; nothing of output/ committed; no stray files.
- **One kept tie, faster:** `f833740` "lossguide tree growth; same AUC and faster total run", 0.6875 as `7d3cd17`: training 6.5 s → 5.4 s (-17%), evaluation unchanged (31.1 / 31.2 s); same holdout (0.6846). Allowed. The next commit (`5b71d1b`, 8 leaves without a depth cap) built on it and gained +0.0007.
- Clock stopped by the agent (`clock_stopped_by` = agent), 58 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- No context compaction in the session log. run.log has no pandas warnings (`prepare` masks unseen categories with `.where(isin)`; the hour categories 0-23 cover every `CRSDepTime`).
- The lowest peak memory of the group (3.6 GiB).
