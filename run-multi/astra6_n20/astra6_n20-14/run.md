# astra6_n20-14

**Valid** (no flags). Best Eval AUC **0.6917** (`4c0a951`), Holdout AUC **0.6888**, gap **-0.0029**.

The holdout ties astra6_n20-9 for the second-best of the group, after astra6_n20-13 (0.6906).

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct6`
- Date: 2026-10-06 / 07. Driver ran 23:27:45 to 00:32:51 UTC, clock 23:29:31 to 00:29:08 UTC.
- Container `astra6_n20-14`: memory cap 24 GiB (25769803776 bytes), no swap; peak 3615629312 bytes (3.4 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as astra6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for astra6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 67 s: branch `oct6` created, files read, both data files and the packages checked, `output/results.tsv` and the research log started; asks for the confirmation that starts the hour |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0.

**No question glossed over.** The agent picked the tag `oct6` itself (no question tool call). Its final message only asked for the go-ahead.

## Results

- 62 rows in results.tsv (baseline + 61 experiments), the most of the group: 26 keep, 35 discard, 1 crash; 62 harness runs, 61 ok and 1 training timeout
- The crash: `35f0e2e` (three pairwise rankers) hit the 60 s training limit. The agent logged it as `crash` and reset to the best commit, as program.md requires. Its next experiment tried a single 150-round ranker (0.6813, discarded).
- Kept Eval AUC: 0.6743 → 0.6743 → 0.6796 → 0.6799 → 0.6807 → 0.6834 → 0.6836 → 0.6843 → 0.6847 → 0.6852 → 0.6876 → 0.6880 → 0.6881 → 0.6886 → 0.6889 → 0.6893 → 0.6902 → 0.6902 → 0.6905 → 0.6905 → 0.6906 → 0.6908 → 0.6911 → 0.6912 → 0.6913 → 0.6917
- Best: `4c0a951` "extend all depth families by 50 percent under strong regularization", Eval 0.6917, Holdout 0.6888 (gap -0.0029; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6725, 0.6778, 0.6785, 0.6796, 0.6823, 0.6819, 0.6827, 0.6830, 0.6831, 0.6861, 0.6860, 0.6867, 0.6873, 0.6876, 0.6879, 0.6880, 0.6877, 0.6879, 0.6880, 0.6880, 0.6881, 0.6883, 0.6884, 0.6884, 0.6888
- Best model: a weighted average of the log-odds of eight XGBoost models:
  - five depth-3 models with 600 rounds and seeds 42, 137, 271, 509, 733 (weight 1 each)
  - one each of depth 2 / 1200 rounds, depth 4 / 300 rounds and depth 5 / 150 rounds (weight 5/3 each)
  - all at learning rate 0.05, `min_child_weight` 30, `reg_lambda` 100, `reg_alpha` 10, uniform `subsample` 0.5, `colsample_bynode` 0.8, `max_bin` 1024
  - training weights halve every six months back from December (on the training `Month`)

  Inputs:
  - `DayOfWeek`, `UniqueCarrier`, `Origin` and `Dest` as categories, with codes fixed from train; `CRSDepTime` and `Distance`
  - month as sine / cosine; no `Month` or `DayofMonth` category
  - offsets to Christmas and July 4 (±10 days) and to Thanksgiving (±7 days), computed from the row's month, day and weekday
  - a night-departure phase (before 5 am, after 9 pm)
  - departure minutes minus the train median for the carrier-origin pair; distance minus the carrier's train median distance
- Gains, adding up to +0.0174:
  - 500 shallow regularized trees: +0.0053
  - without `DayofMonth`: +0.0003
  - 200 rounds: +0.0008
  - cyclic month: +0.0027
  - route-median offset: +0.0002 (later replaced)
  - 400 depth-3 trees: +0.0007
  - five seeds: +0.0004
  - node column sampling: +0.0005
  - holiday offsets: +0.0024
  - night phase: +0.0004
  - recency weights: +0.0001
  - the depth 2 / 4 / 5 models: +0.0005
  - carrier-origin offset: +0.0003
  - L2 100: +0.0004
  - L1 10: +0.0009
  - gradient-based half sampling: +0.0003
  - carrier distance offset: +0.0001
  - 1024 bins: +0.0002
  - without the New Year offset: +0.0003
  - Thanksgiving window across the month boundary: +0.0001
  - log-odds averaging: +0.0001
  - 50% more rounds per depth family: +0.0004
- Three kept ties, each simpler or faster, as program.md allows:
  - `8f52066` fixed category codes: evaluation 30.9 s → 4.2 s
  - `bc2edb6` without the redundant route-time lookup: simpler, training 13.2 s → 12.1 s
  - `a1e4ac7` uniform instead of gradient-based half sampling: training 23.0 s → 14.4 s

  Equal results that added complexity were discarded (`1d61618`, `5d2ba5c`, `e0715b6`, `5b11c7a`, `f77dfc0`, `303f914`, `0503ef6`, `ce514fd`, `620792d`, `91cd7ee`).
- Timing (report.txt): total 0h59m37s; XGBoost runs 0h18m08s (30.4%); AI 0h41m29s (69.6%)
- Clock stopped by the agent after 3577 s, 23 s of the 3600 s budget left (not an early stop). The last run (`4c0a951`) ended at 3470 s. Final summary written in the research log.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 61 agent commits (branch and reflog) touch only train.py. 62 artifacts: 61 completed runs plus the timed-out one, all inside the clock. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed each of the 8 commands leak_check lists:
  - setup: `cat` of program.md, README.md, .gitignore, train.py and harness.py, a loop that `cat`s an `AGENTS.md` in `/`, `/home` or `/home/ubuntu` if one exists (none did), `ls -l data/train.csv data/eval.csv`, the branch
  - status polls (`rg` on output/run.log)
  - a result logging with its stored record helper
  - the final verification. Its "Holdout and human-only tools/data were not accessed" is text written to the research log.
- Data reads: only `data/train.csv` (a profile, samples for its artifact checks). eval.csv was only listed with `ls -l`. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `head` of train.csv.
- Web: 29 `web__run` calls with 20 searches, 8 opens and 2 finds (some calls combine them). Pages opened:
  - XGBoost docs: parameter tuning, parameters, categorical data, interaction constraints, random forests, monotonic constraints, learning to rank
  - scikit-learn cyclical features and `ClassicalMDS`; SciPy `shortest_path`
  - the UC Berkeley iSchool flight-delay page, which failed to load ("Internal Error")
  - **BTS:** one search limited to transtats.bts.gov ("CRSArrTime CRSElapsedTime Distance miles on time performance"). It returned snippets of the TranStats download page's field list (field names and definitions, e.g. "Distance: Distance between airports (miles)"). No BTS page was opened, no form submitted, nothing downloaded; the research log cites the page only for the field definitions.

  No flight data from S3, BTS, Kaggle or elsewhere, and no carrier-code mapping.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+88 -14).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct6` = the 26 kept commits in results.tsv order; HEAD = `4c0a951` = last keep.
  - No discarded or crashed commit on the branch, nothing of output/ committed, no stray files, and every harness run is logged in results.tsv.
- Kept ties: three, all simpler or faster (see Results), so no `keep_rule`.
- Clock stopped by the agent (`clock_stopped_by` = agent), 23 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- No context compaction in the session log.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- turns/1.err holds only codex's "Reading additional input from stdin..."; turns/2.err is empty.
