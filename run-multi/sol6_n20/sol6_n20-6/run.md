# sol6_n20-6

**Valid** (no flags). Best Eval AUC **0.6818** (`44473d1`), Holdout AUC **0.6803**, gap **-0.0015**.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-sol`, effort `max` (levels it has: low medium high xhigh max ultra; `max` is not the highest)
- turn_context as confirmed from the session log: `[('gpt-6-sol', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `8d9c760`)
- Run tag / branch: `oct5`
- Date: 2026-10-05, driver 20:21:01 to 21:34:19 UTC; clock 20:24:26 to 21:23:27 UTC
- Container `sol6_n20-6`: memory cap 24 GiB (25769803776 bytes), no swap; peak 12523597824 bytes (11.7 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as run 1
- Driver: `run_one.sh` of commit `1030646`

## Turns

| turn | sent | result |
|---|---|---|
| 1 | README prompt | setup in 2m32s: read program.md, README, `train.py`, `harness.py`, listed the repo's files, looked for AGENTS.md under `/home/ubuntu` (none), checked the data files, packages and clock; did not create the branch; ends "I propose **`oct5`** ... Confirm that tag (or give me another), and I'll create the branch and header-only `output/results.tsv`, then stop for your go-ahead before starting the clock." |
| 2 | `go` | created `oct5` and results.tsv, started the clock and ran the whole hour; stopped the clock itself with 58 s left |

No "keep going". **No failed turns:** `failed_turns` 0, `retry_wait_s` 0, turns/2.err empty.

**The run-tag question was glossed over by "go" (benign).** As in runs 1-5, the agent first asked through `request_user_input_async` ("should I use the branch tag `oct5`?", options "Use oct5" / "Use oct5a"), which nobody sees in `codex exec`, waited with three 30 s `sleep` calls, then asked again in its final message. It took the single "go" as approval of `oct5` and of the start (no second "go" was needed). The waits were before the clock started.

## Results

- 43 rows in results.tsv (baseline + 42 experiments): 15 keep, 28 discard, 0 crash; 43 harness runs, all ok
- Kept Eval AUC: 0.6743 → 0.6751 → 0.6766 → 0.6770 → 0.6784 → 0.6786 → 0.6786 (tie, see protocol checks) → 0.6790 → 0.6791 → 0.6798 → 0.6801 → 0.6803 → 0.6808 → 0.6812 → 0.6818
- Best: `44473d1` "remove holiday category feature", Eval 0.6818, Holdout 0.6803 (gap -0.0015; starter: 0.6743 / 0.6725, gap -0.0018)
- Holdout AUC of the kept commits: 0.6725, 0.6728, 0.6748, 0.6755, 0.6774, 0.6783, 0.6783, 0.6777, 0.6777, 0.6785, 0.6800, 0.6785, 0.6785, 0.6806, 0.6803. The two depth keeps (`2797a98` depth 8, `a9586ee` depth 10: eval +0.0007) took holdout from 0.6800 down to 0.6785; the highest holdout is `1a5836d` (0.6806), the keep before the best.
- Best model: one XGBoost model, 120 loss-guided trees (`max_leaves` 31, `max_depth` 10) at learning rate 0.05, `subsample` 0.8, native categoricals. Features: the starter's columns with `CRSDepTime` replaced by departure minute of day and hour, plus a numeric day of year (fixed non-leap-year table).
- Gains, adding up to +0.0075:
  - the learning schedule: +0.0033 (fewer rounds: 50 then 25 at 0.1, +0.0019; with loss-guided trees, 40 and 60 rounds, +0.0010; 120 at 0.05, +0.0004)
  - day of year: +0.0014
  - loss-guided growth with 31 leaves, then depth caps 8 and 10: +0.0011 (+0.0004, +0.0002, +0.0005)
  - departure minute of day and hour: +0.0008
  - a holiday-period category: +0.0001, and removing it again in the 120-round model: +0.0006
  - `subsample` 0.8: +0.0002
- Timing (report.txt): total 0h59m02s; XGBoost runs 0h30m56s (52.4%); AI 0h28m05s (47.6%)
- Clock stopped by the agent after 3542 s, 58 s of the 3600 s budget left (not an early stop: under 2 minutes remained). The last run (`a157264`) ended 102 s before the budget ran out.

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 42 agent commits (branch and reflog) touch only train.py; 43 artifacts for 43 runs, all inside the clock; every harness run is in results.tsv; the train.py of all 42 commits has no read of another file or the network.
- leak_check.txt: **CONTENT HITS: 0.** No line of a human-only script, no row of eval.csv or holdout.csv in the log.
- The 3 commands leak_check lists, all reviewed: the setup reads (`cat program.md`, `cat README.md`, `rg --files` of the repo without CSV and JSON files, `find .. -name AGENTS.md`, which found nothing), `cat train.py` / `cat harness.py` / `ls data/train.csv data/eval.csv` (an existence check), and the last patch to the research log.
- Data reads: only `data/train.csv`, in four scratch commands (20:25 shape, dtypes, unique counts, time range; 20:32 route and carrier-origin counts; 20:33 the first 10 rows of the three date columns; 20:48 airport connectivity of the hubs, for a hub-distance feature fitted on train and later discarded). eval.csv was never opened. No curl, wget, pip or git clone. All 233 shell commands looked through. Three scripts loaded the agent's own artifacts (`e9521f1`, `e09605c`) to print the tree config and gain importances.
- Web: 11 `web__run` calls, 9 searches and 2 opens. Pages read: XGBoost docs (parameter tuning, parameters) and a Chinese Journal of Aeronautics article on flight delays (sciopen.com); the UC Berkeley iSchool page failed (403). Searches: XGBoost, scikit-learn and CatBoost docs, the CatBoost paper, flight-delay papers on routes, hubs, holidays and departure times. No search for this dataset; no flight rows in any web result. No flight data from S3, BTS, Kaggle or elsewhere.
- No tool call mentions `human/`, `/opt` or `holdout`: no forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+13 -3).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks: pass

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct5` = the 15 kept commits in results.tsv order; HEAD = `44473d1` = last keep; no discarded commit on the branch; nothing of output/ committed; no stray files.
- **One kept tie, simpler code:** `e9521f1` "remove redundant raw HHMM model feature" kept at 0.6786, equal to `ed6e6d6` before it (the minute of day and hour carry the same information). Allowed. Same holdout AUC (0.6783).
- Clock stopped by the agent (`clock_stopped_by` = agent), 58 s remaining.
- No retry waits (`retry_wait_s` 0).

## Other notes

- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- No context compaction in the session log. run.log has no pandas warnings (`prepare` masks unseen categories with `.where(isin)` as the starter does).
- Six of its first eight experiments are run 5's, in nearly the same order (departure minute and hour, 300 rounds, 50 rounds, 25 rounds, depth 4, route category), with identical Eval AUCs (0.6751, 0.6674, 0.6766, 0.6770, 0.6747, 0.6710): training is deterministic (`random_state` 42), so the same change gives the same score. The two runs part ways after that.
- The lowest best Eval and Holdout AUC of the group so far.
