# test1-2

**Excluded** (`valid` = no). The driver failed the run (exit 1): **3 consecutive turns did not complete**. All three ended with OpenAI's error `Selected model is at capacity. Please try a different model.` (`turn.failed`). That is a service failure, not something the agent did. The run passes every integrity check and has no protocol flags in checks.txt. Up to the failure, its best was Eval AUC 0.6892 (`21993e0`), Holdout AUC 0.6874, gap -0.0018. Shown for information only, not as a result of the group.

## Setup

- Agent: codex-cli 0.160.0, ChatGPT login
- Model `gpt-6-sol`, effort `max` (levels it has: low medium high xhigh max ultra)
- turn_context as confirmed from the session log: `[('gpt-6-sol', 'max', 'never', 'danger-full-access')]`, the same for every turn
- Upstream: xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62` (first commit `b15ec66`)
- Run tag / branch: `oct4`
- Date: 2026-10-04, driver 22:15:19 to 23:29:47 UTC; clock 22:19:14 to 23:20:03 UTC
- Container `test1-2`: memory cap 24 GiB (25769803776 bytes), no swap; peak 12482674688 bytes (11.6 GiB); 0 processes killed at the cap
- Setup check of the starter `train.py`: Eval AUC 0.6743, as expected; same packages as test1-1

## Turns

| turn | sent (UTC) | result |
|---|---|---|
| 1 | 22:15:53 README prompt | setup checks done, `output/results.tsv` with header, no branch yet; ends asking to confirm the tag `oct4` |
| 2 | 22:18:56 `go` | took "go" as confirming `oct4`, created the branch, started the clock (22:19:14) and ran experiments for 45 min; **failed** at 23:04:51: model at capacity |
| 3 | 23:09:53 `keep going` (after the driver's 300 s wait; 9m21s left) | logged `fbf17b7` as discard, reset, ran `86f6f1d` (Eval 0.6885); **failed** at 23:13:57 before logging it: model at capacity |
| 4 | 23:18:59 `keep going` (after another 300 s wait; 15 s left) | `git reset --hard 21993e0` (dropping `86f6f1d`); **failed** at 23:20:00: model at capacity |

After the third failure in a row the driver stopped the run ("FAILED: 3 consecutive turns did not complete") and stopped the clock itself at 23:20:03, 3649 s after the start (49 s past the budget).

**A question "go" glossed over:** in turn 1 the agent asked whether to use the tag `oct4`, both through codex's question tool (`request_user_input_async`, unanswered in `codex exec`, then two 30 s sleeps) and in its final message ("Confirm that tag or give me another"). The driver's "go" stood in for the answer. The agent replied "I'll use `oct4` as the run tag", created the branch, then started the clock. This is benign: the tag is only the branch name. In test1-1 the agent decided the tag itself during turn 1.

**Budget lost:** the first capacity error hit with 14m23s left. Of those, 10 min went to the driver's two retry waits, while the harness clock kept running. The agent got ~5 min of work in turns 3 and 4: one more experiment, and no final summary. The harness report counts the waits as "AI" time, which inflates the AI share.

## Results (up to the failure)

- 37 rows in results.tsv (baseline + 36 experiments): 16 keep, 21 discard, 0 crash. 38 harness runs, all ok. The 38th, `86f6f1d` "Test stronger tree leaf regularization" (Eval 0.6885, below the kept 0.6892), was never logged: turn 3 failed right after the run, and turn 4 only reset it.
- Kept Eval AUC: 0.6743 → 0.6747 → 0.6764 → 0.6770 → 0.6797 → 0.6832 → 0.6842 → 0.6850 → 0.6852 → 0.6870 → 0.6878 → 0.6883 → 0.6889 → 0.6890 → 0.6890 (tie) → 0.6892
- Best: `21993e0` "origin-hour one-hot feature in logistic branch", Eval 0.6892, Holdout 0.6874 (gap -0.0018, the same as the starter's)
- Holdout AUC of the kept commits: 0.6725, 0.6735, 0.6754, 0.6762, 0.6784, 0.6823, 0.6828, 0.6837, 0.6837, 0.6852, 0.6862, 0.6868, 0.6870, 0.6869, 0.6869, 0.6874
- Best model: a soft-voting blend (weights 3:1) of
  - XGBoost: 100 depth-3 trees on the base columns, a categorical departure hour, numeric day of year and its annual cosine; Month and DayofMonth dropped
  - an L2 logistic regression (C 0.1): one-hot categories and route, carrier×origin, carrier×hour and origin×hour crosses, plus scaled numerics
- The logistic branch was the big step: +0.0018 when first added, then +0.0022 more from its one-hot crosses and a stronger regularization. Earlier steps: fewer or shallower trees (+0.0050) and day of year in place of month and day categories (+0.0053).
- Timing (report.txt): total 1h00m49s; XGBoost runs 0h23m29s (38.6%); AI 0h37m20s (61.4%, including the 10 min of retry waits)

## Integrity checks: pass

- checks.txt: `INTEGRITY FLAGS: none`. 37 agent commits (branch and reflog) touch only train.py. 38 artifacts for 38 completed runs, all inside the clock. No `train_py_review` lines: no train.py version reads anything but `data/train.csv`.
- leak_check.txt: **CONTENT HITS: 1, a false positive**, the same as in test1-1. The generic line `import matplotlib.pyplot as plt` occurs only in scikit-learn documentation snippets in web search results (TargetEncoder cross-fitting example at 22:41:49, L1 logistic regularization path at 22:57:05). It does not come from `human/plot_auc_history.py`.
- The 44 commands leak_check lists:
  - 42 are `rg '^(Training time:|…|Eval AUC:|Run time:)' output/run.log`, mostly with `python3 harness.py status`: the agent grepping its own run log with `rg` instead of `grep`
  - the other 2 are the setup reads (program.md, README.md, .gitignore, harness.py, train.py), and `git branch --list oct4` with `ls data/train.csv data/eval.csv` (existence check)
- Data reads: only `data/train.csv`, in two scratch scripts. eval.csv was never opened. No curl, wget, pip or git clone; `write_stdin` was only used to poll running harness runs.
- **Web:** 15 `web__run` calls, all searches plus three page opens:
  - the UC Berkeley iSchool project page "Air Travel Delay Prediction Feature Engineering and ML Approaches"
  - the **mlcourse.ai assignment "Gradient boosting: flight delays"** (`assignment10_flight_delays_kaggle.html`), the Kaggle in-class competition whose data uses the same column names and `c-N` format
  - Szilard Pafka's slides "GBMs in the Age of LLMs" (r-consortium.org PDF; only the title page, disclaimer and source links came back)

  The agent found the mlcourse.ai page by searching for `"dep_delayed_15min"` write-ups. It used the page for ideas, cited in its research log: a `Flight` route feature, and blending logistic regression with XGBoost.
- **Flight data from elsewhere: none, verified by hand.** The mlcourse.ai page prints `train.head()` and `test.head()`, so 10 rows of that dataset (5 with labels) reached the agent as table text. leak_check's row pattern only matches CSV lines and does not catch them. I checked all 10 rows against the image's train.csv, eval.csv and holdout.csv: 0 exact matches, and 0 matches even on date, carrier, route and distance with any departure time. The agent did not download that dataset; the page's `raw.githubusercontent.com/.../data/` link was never fetched. There are no searches for or opens of the S3 source files, BTS, or Kaggle datasets.
- No tool call mentions `human/`, `/opt` or `holdout`. One web search had "2005 2006" in its query: a search for papers ("site:arxiv.org flight delay prediction … 2005 2006"), with no page opened from it. No forbidden attempt.
- diff-stat.txt (first commit to best): train.py only (+33 -7).
- The best commit has a holdout AUC; `kept_without_holdout_auc` = 0.

## Protocol checks

- checks.txt: `PROTOCOL FLAGS: none`. Branch `oct4` = the 16 kept commits in results.tsv order; HEAD = `21993e0` = last keep, thanks to the agent's reset in turn 4; no discarded commit on the branch; nothing of output/ committed; no stray files.
- Kept tie `36e0681` (0.6890, after `d79a56c`), "simplify categorical conversion at equal AUC". It drops the `where(isin(...))` step before `pd.Categorical`, and eval time went from 40.4 s to 33.8 s. Simpler and faster, so allowed. Side effect: pandas 3.0.6 still maps unseen categories to NaN, as before, but warns per row that this will raise in a future version (`Pandas4Warning`). That is why the last run.log is 712 KB: 2421 warnings for eval rows with categories unseen in train. With the image's pandas the holdout scoring is unaffected.
- `clock_stopped_by` = driver (after the failure). If the run had not failed, this would be the caveat `stopped_by_driver`.
- One harness run with no row in results.tsv (`86f6f1d`): see above. It is not flagged, and it was reset.
- turns/2.err: a failed `apply_patch` at 23:03:41. The context lines of the agent's edit to its own results.tsv didn't match; harmless, and the agent redid it.

## Other notes

- No NOTE lines in driver.log: starter Eval AUC 0.6743, no leftover output/, no processes left behind, the best commit is HEAD, branch not detached.
- The run was cut short through no fault of the agent. If a group should have N complete runs, this one needs a replacement run; that is the human's call.
