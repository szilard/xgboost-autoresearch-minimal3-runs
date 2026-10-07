# astra6_n20-19

**Valid** (no flags). Best Eval AUC **0.6910** (`cbf5e51`), Holdout AUC **0.6876**, gap **-0.0034**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct7`
- Date: 2026-10-07. Driver ran 05:00:07 to 06:07:41 UTC, clock 05:03:32 to 06:02:46 UTC.
- Container `astra6_n20-19`: memory cap 24 GiB (25769803776 bytes), no swap; peak 3636187136 bytes (3.4 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as astra6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for astra6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 161 s: branch `oct7` created, files read, both data files and the packages checked, `output/results.tsv` and the research log started; ends "Say **go** to begin" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0.

**No question glossed over.** In turn 1 the agent called codex's question tool to propose `oct7` (options `oct7`, `oct7-flight-delay`). The tool returned `{"accepted":true}` and the agent went on with `oct7`. Its final message only asked for the go-ahead.

## Results

- 49 rows in results.tsv (baseline + 48 experiments): 23 keep, 26 discard, 0 crash; 49 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6800 → 0.6809 → 0.6809 → 0.6809 → 0.6832 → 0.6833 → 0.6834 → 0.6841 → 0.6845 → 0.6846 → 0.6848 → 0.6848 → 0.6850 → 0.6851 → 0.6862 → 0.6874 → 0.6880 → 0.6881 → 0.6891 → 0.6898 → 0.6906 → 0.6910
- Best: `cbf5e51` "Increase minimum child weight from 100 to 300 for stronger leaf support", Eval 0.6910, Holdout 0.6876 (gap -0.0034; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6787, 0.6790, 0.6790, 0.6790, 0.6812, 0.6809, 0.6813, 0.6812, 0.6816, 0.6818, 0.6820, 0.6820, 0.6823, 0.6824, 0.6831, 0.6847, 0.6848, 0.6850, 0.6857, 0.6864, 0.6871, 0.6876
- Best model: a soft-voting average of three XGBoost models (seeds 42, 43, 44). Each has 300 depth-4 trees at learning rate 0.05, with `min_child_weight` 300, `reg_lambda` 50, `subsample` 0.9 and `max_cat_threshold` 32. Training weights balance the classes within each training month, times a recency weight that halves every six months back from December. Inputs:
  - `Month`, `DayOfWeek`, `UniqueCarrier`, `Origin` and `Dest` as categories; `CRSDepTime`, `Distance` and departure sine / cosine; no `DayofMonth`
  - departure minutes minus the train median for the route and the carrier-origin pair
  - the nearest holiday within 7 days (New Year, Memorial Day, July 4, Labor Day, Thanksgiving, Christmas) as a category, and the days before and after it, computed from the row's month, day and weekday
- Gains, adding up to +0.0167:
  - 600 depth-4 trees with regularization: +0.0057
  - without `DayofMonth`: +0.0009
  - without `Month`: +0.0023, then re-added under monthly class balancing: +0.0011
  - departure-time features: +0.0001
  - airport coordinates: +0.0001, then removed: +0.0001
  - depth 3: +0.0007
  - recency weights: +0.0004
  - schedule offsets: +0.0002
  - monthly class balance: +0.0002
  - three seeds: +0.0001
  - holiday proximity: +0.0012, then the holiday's identity: +0.0010
  - `min_child_weight` 100: +0.0006
  - without the standalone hour and minute: +0.0001
  - L2 50: +0.0007
  - depth 4 with larger leaves and stronger L2: +0.0008
  - `min_child_weight` 300: +0.0004
- Three kept ties, each simpler or faster, as program.md allows:
  - `d950e9a` cached category dtypes, frame built once: evaluation 27.1 s → 8.3 s
  - `94fd4f8` explicit codes for unseen categories (removes pandas deprecation warnings): evaluation 8.3 s → 7.1 s, and 6.2 to 7.7 s in the runs after it
  - `41c1f04` 300 rounds instead of 600: a smaller model, training 2.6 s → 1.9 s

  Equal results that added complexity were discarded (`6f692c0`, `94fb42f`, `20f898c`, `cba049c`).
- Timing (report.txt): total 0h59m14s; XGBoost runs 0h11m59s (20.2%); AI 0h47m16s (79.8%)
- Clock stopped by the agent after 3554 s, 46 s of the 3600 s budget left (not an early stop). The last run (`a47f9f9`) ended at 3474 s. Final summary written in the research log.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 48 agent commits (branch and reflog) touch only train.py. 49 artifacts for 49 completed runs, all inside the clock. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed each of the 7 commands leak_check lists:
  - setup: `rg --files` limited to docs and config, `cat` of program.md, README.md, .gitignore and train.py, `sed` of part of harness.py, `ls -l data/train.csv data/eval.csv`, the results header
  - a web call together with a status poll
  - an `rg` for function names in harness.py
  - the final verification
- Data reads: only `data/train.csv` (a profile, a 128-row sample for its artifact check). eval.csv was only listed with `ls -l`. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `head` of train.csv in its profile.
- Web: 21 `web__run` calls with 12 searches, 7 opens and 4 finds (some calls combine them). Pages opened:
  - XGBoost docs: parameter tuning, categorical data, parameters, interaction constraints, random forests, DART, monotonic constraints, learning to rank
  - pandas `Categorical`; scikit-learn target-encoder cross-fitting; AWS SageMaker XGBoost tuning; arXiv 2304.01512
  - the UC Berkeley iSchool flight-delay page, which failed to load

  One search included "site.transportation.gov thanksgiving christmas flight delays holiday travel". Its snippets were DOT / BTS reporting rules and links, with no flight records and no 2005 or 2006 figures. No BTS page was opened. No flight data from S3, BTS, Kaggle or elsewhere, and no carrier-code mapping.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt. "holdout" appears only in the final verification's text.
- diff-stat.txt (first commit to best): train.py only (+68 -10).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct7` = the 23 kept commits in results.tsv order; HEAD = `cbf5e51` = last keep.
  - No discarded commit on the branch, nothing of output/ committed, no stray files, and every harness run is logged in results.tsv.
- Kept ties: three, all simpler or faster (see Results), so no `keep_rule`.
- Clock stopped by the agent (`clock_stopped_by` = agent), 46 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- **One context compaction** in the session log at 05:59:12, 56 minutes into the clock, before the wrap-up.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- turns/1.err holds only codex's "Reading additional input from stdin..."; turns/2.err is empty.
