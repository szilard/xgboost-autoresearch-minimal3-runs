# test1

Group `test1`: model `gpt-6-sol`, effort `max`, N_RUNS 3, codex-cli 0.160.0, upstream xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62`, 2026-10-04/05, container memory cap 24 GB (no swap).

| run | model | effort | experiments | best Eval AUC (commit) | Holdout AUC | gap | total time | AI share | valid | caveat / excluded |
|---|---|---|---|---|---|---|---|---|---|---|
| test1-1 | gpt-6-sol | max | 41 | 0.6856 (`8619c6e`) | 0.6847 | -0.0009 | 0h58m30s | 55.0% | yes | |
| test1-2 | gpt-6-sol | max | 37 | (0.6892 (`21993e0`)) | (0.6874) | (-0.0018) | 1h00m49s | 61.4% | no | excluded: driver failed the run, 3 consecutive turns did not complete. All three ended with OpenAI's "Selected model is at capacity" (from 23:04 UTC, 14 min left; 10 of them lost to retry waits). Integrity checks pass; AUCs in parentheses for information only |
| test1-3 | gpt-6-sol | max | 44 | 0.6861 (`28ed4b1`) | 0.6847 | -0.0014 | 0h59m34s | 60.3% | yes | |

## Statistics over the valid runs (n = 2: test1-1, test1-3)

| | n | mean | sd | min | median | max |
|---|---|---|---|---|---|---|
| Holdout AUC | 2 | 0.6847 | 0.0000 | 0.6847 | 0.6847 | 0.6847 |
| Eval AUC | 2 | 0.6859 | 0.0004 | 0.6856 | 0.6859 | 0.6861 |
| gap (holdout - eval) | 2 | -0.0012 | 0.0004 | -0.0014 | -0.0012 | -0.0009 |

sd is the sample standard deviation (n - 1). With n = 2 the median equals the mean. Unrounded: Eval AUC mean and median 0.68585, gap mean and median -0.00115, both sd 0.00035.

For reference, the starter `train.py` scores 0.6743 on eval and 0.6725 on holdout (gap -0.0018).

## Notes

- Excluded: 1 run (test1-2), for a service failure, not the agent's behaviour. With 14 min left on its clock, three turns in a row ended with OpenAI's `Selected model is at capacity`, and the driver's two 300 s retry waits ran on the agent's clock. Up to then it had the best result of the group (Eval 0.6892, Holdout 0.6874), and all its integrity checks pass.
- Caveats: none. Both valid runs stopped the clock themselves (90 s and 26 s left) and have no protocol flags.
- Turns: each run needed exactly one "go"; only test1-2 got "keep going" (twice, both after failed turns).
- Run tag: in test1-2 and test1-3 the agent ended the setup turn asking to confirm the tag `oct4`, and the driver's "go" served as the answer. In test1-1 it chose the tag itself after its question went unanswered.
- leak_check reports CONTENT HITS: 1 in every run. In all three it is a false positive: the generic `import matplotlib.pyplot as plt` (also in `human/plot_auc_history.py`) inside scikit-learn documentation pages from web searches.
- test1-2 opened the mlcourse.ai Kaggle "flight delays" assignment, which uses the same data format. 10 public rows shown on that page (table form, which leak_check does not match) reached the agent. None of them is in train, eval or holdout (checked by hand). It used the page only for ideas (route feature, logistic + XGBoost blend).
- Gaps (-0.0009, -0.0014, and -0.0018 for the excluded run) are all well inside the provisional thresholds (-0.006 / +0.003).
