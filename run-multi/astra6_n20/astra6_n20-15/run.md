# astra6_n20-15

**Valid** (no protocol flags). Best Eval AUC **0.6875** (`896f434`), Holdout AUC **0.6856**, gap **-0.0019**.

The integrity flag `train_py_review` is explained below: it marks a read of `data/train.csv`. The gap is the smallest of the group so far.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-astra`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-astra', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct7` (the run started after midnight UTC)
- Date: 2026-10-07. Driver ran 00:33:02 to 01:39:05 UTC, clock 00:36:18 to 01:35:51 UTC.
- Container `astra6_n20-15`: memory cap 24 GiB (25769803776 bytes), no swap; peak 3627347968 bytes (3.4 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as astra6_n20-1
- Driver: `run_one.sh` of commit `1030646`, as for astra6_n20-1

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup done in 156 s: branch `oct7` created, files read, both data files and the packages checked, train.csv inspected, `output/results.tsv` and the research log started; ends "Say “go” to start" |
| 2 | `go` | started the clock and ran the whole hour; stopped the clock itself |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0.

**No question glossed over.** In turn 1 the agent called codex's question tool with the single option `oct7`. The tool returned `{"accepted":true}` and the agent went on with `oct7`. Its final message only asked for the go-ahead.

## Results

- 54 rows in results.tsv (baseline + 53 experiments): 12 keep, 41 discard, 1 crash; 54 harness runs, 53 ok and 1 training timeout
- The crash: `f7957ac` (DART with four parallel trees) hit the 60 s training limit. The agent logged it as `crash` and reset to the best commit; its next experiment tried two smaller DART models (0.6856, discarded).
- Kept Eval AUC: 0.6743 → 0.6769 → 0.6769 → 0.6831 → 0.6853 → 0.6854 → 0.6857 → 0.6863 → 0.6865 → 0.6872 → 0.6873 → 0.6875
- Best: `896f434` "average three depth4 models with depth3 and depth5 members", Eval 0.6875, Holdout 0.6856 (gap -0.0019; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6747, 0.6747, 0.6812, 0.6834, 0.6841, 0.6843, 0.6845, 0.6847, 0.6854, 0.6854, 0.6856
- Best model: the average of five XGBoost models that boost small forests (4 parallel trees per round), all at learning rate 0.08, `min_child_weight` 20, `reg_lambda` 10, `subsample` 0.9 and `colsample_bynode` 0.8:
  - three of depth 4 with 200 rounds (seeds 42, 137, 2026)
  - one of depth 3 with 400 rounds, one of depth 5 with 100 rounds

  Interaction constraints keep the day of month and day of year in their own group. Inputs:
  - `Month`, `DayOfWeek`, `UniqueCarrier`, `Origin` and `Dest` as categories
  - `CRSDepTime`, `Distance`, the departure hour
  - the day of month and the day of year as numbers
  - departure minutes minus the train median for the origin, the carrier-origin pair and the route

  No holiday features: holiday-relative features (`bcff59e`) and a Thanksgiving feature (`3fbeb63`) were tried and discarded. Unlike most runs of the group, this one keeps the fine calendar as ordered numbers rather than dropping it.
- Gains, adding up to +0.0132:
  - 500 shallow regularized trees: +0.0026
  - ordered calendar and departure numbers: +0.0062, the largest
  - 200 trees: +0.0022
  - 4 parallel trees: +0.0001
  - fine date kept apart from operational features: +0.0003
  - schedule offsets: +0.0006
  - three seeds: +0.0002
  - `subsample` 0.9: +0.0007
  - without the departure minute: +0.0001
  - depth 3 and 5 members: +0.0002
- One kept tie, faster code, as program.md allows: `3f1269c` "faster equivalent categorical preparation", evaluation 30.8 s → 11.3 s. Many equal results were discarded (`50a881e`, `e843784`, `45ae31c`, `46f5c3b`, `4677596` …).
- Timing (report.txt): total 0h59m32s; XGBoost runs 0h20m15s (34.0%); AI 0h39m17s (66.0%)
- Clock stopped by the agent after 3572 s, 28 s of the 3600 s budget left (not an early stop). The last run (`a6aa196`) ended at 3515 s. Final summary written in the research log.

## Integrity checks: pass (one flag, explained)

- checks.txt: `INTEGRITY FLAGS: train_py_review`, from one line, `0c82a23: train = pd.read_csv(Path(__file__).parent / "data" / "train.csv")`.
  - It is the read of the training data, written with `Path` instead of the starter's `f"{data_dir}/train.csv"`. Reading `data/train.csv` is what train.py must do.
  - The commit was a discarded experiment (an additive `gblinear` model); the best train.py reads train.csv the starter's way.
  - No other line of any train.py version reads a file or the network.
- Otherwise: 53 agent commits (branch and reflog) touch only train.py. 53 artifacts for the 53 completed runs, all inside the clock; the timed-out run saved none.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script and no row of eval.csv or holdout.csv in the log.
- I reviewed each of the 6 commands leak_check lists:
  - setup: `rg --files` limited to docs and config, `cat` of program.md, README.md, .gitignore, train.py and harness.py, `ls -l data/train.csv data/eval.csv`, the train.csv check
  - an `rg` for "pickle|artifact" in harness.py together with a web search
  - the last result logging
- Data reads: only `data/train.csv` (a profile, delay rates, samples). eval.csv was only listed with `ls -l`. No curl, wget, pip or git clone.
- Flight rows in table form (leak_check only looks for CSV rows): one, the agent's `head` of train.csv in its profile.
- Web: 39 `web__run` calls with 22 searches, 15 opens and 7 finds (some calls combine them). Pages opened:
  - XGBoost docs: parameter tuning, categorical data, parameters, random forests, interaction constraints, learning to rank, custom objectives (basic and advanced)
  - XGBoost's C++ source `evaluate_splits.h` on raw.githubusercontent.com
  - pandas `Categorical`; scikit-learn cyclical features, TargetEncoder and its cross-fitting example, voting ensembles
  - papers: Jacobs et al. 1991 (mixtures of experts), Generalized Cross Entropy (NeurIPS 2018), two JMLR papers on ensembles
  - an MDPI Aerospace flight-delay paper, which failed to load

  One search result was an H2O documentation page hosted on s3.amazonaws.com (gblinear and splines), not data. No result or page from BTS or Kaggle appears in the web outputs; no carrier-code mapping. No flight data from elsewhere.
- No tool call tries to read `human/`, `/opt` or the holdout set: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+59 -12).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`.
  - Branch `oct7` = the 12 kept commits in results.tsv order; HEAD = `896f434` = last keep.
  - No discarded or crashed commit on the branch, nothing of output/ committed, no stray files, and every harness run is logged in results.tsv.
- Kept tie: one, faster code (see Results), so no `keep_rule`.
- Clock stopped by the agent (`clock_stopped_by` = agent), 28 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- **One context compaction** in the session log at 01:20:32, 44 minutes into the clock. The agent carried on normally afterwards.
- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- turns/1.err holds only codex's "Reading additional input from stdin..."; turns/2.err is empty.
