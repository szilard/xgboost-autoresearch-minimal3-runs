# sol6_n20

Group `sol6_n20`: model `gpt-6-sol`, effort `max`, N_RUNS 20, codex-cli 0.160.0, upstream xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62`, 2026-10-05 to 2026-10-06, container memory cap 24 GB (no swap).

| run | model | effort | experiments | best Eval AUC (commit) | Holdout AUC | gap | total time | AI share | valid | caveat / excluded |
|---|---|---|---|---|---|---|---|---|---|---|
| sol6_n20-1 | gpt-6-sol | max | 34 | 0.6865 (`fa052d9`) | 0.6850 | -0.0015 | 1h00m59s | 68.4% | yes | |
| sol6_n20-2 | gpt-6-sol | max | 34 | 0.6858 (`b602c3f`) | 0.6836 | -0.0022 | 1h00m28s | 64.0% | yes | |
| sol6_n20-3 | gpt-6-sol | max | 35 | 0.6857 (`72d7e0a`) | 0.6841 | -0.0016 | 0h58m34s | 60.4% | yes | |
| sol6_n20-4 | gpt-6-sol | max | 29 | 0.6831 (`07f5782`) | 0.6821 | -0.0010 | 0h58m55s | 71.0% | yes | |
| sol6_n20-5 | gpt-6-sol | max | 47 | 0.6839 (`8202360`) | 0.6826 | -0.0013 | 0h58m46s | 40.2% | yes | |
| sol6_n20-6 | gpt-6-sol | max | 43 | 0.6818 (`44473d1`) | 0.6803 | -0.0015 | 0h59m02s | 47.6% | yes | |
| sol6_n20-7 | gpt-6-sol | max | 58 | 0.6866 (`eb1987a`) | 0.6837 | -0.0029 | 0h59m01s | 43.1% | yes | |
| sol6_n20-8 | gpt-6-sol | max | 48 | 0.6877 (`83775c5`) | 0.6871 | -0.0006 | 0h59m22s | 44.8% | caveat | caveat: keep_rule (tie kept as "faster" by 1.0 s, not simpler) |
| sol6_n20-9 | gpt-6-sol | max | 51 | 0.6846 (`348d81c`) | 0.6834 | -0.0012 | 0h58m28s | 41.4% | yes | |
| sol6_n20-10 | gpt-6-sol | max | 51 | 0.6885 (`c3b3a92`) | 0.6864 | -0.0021 | 0h59m06s | 49.0% | yes | |
| sol6_n20-11 | gpt-6-sol | max | 55 | 0.6893 (`cd0df4b`) | 0.6857 | -0.0036 | 0h59m15s | 47.3% | yes | |
| sol6_n20-12 | gpt-6-sol | max | 70 | 0.6870 (`43d5c46`) | 0.6846 | -0.0024 | 0h58m52s | 43.1% | yes | |
| sol6_n20-13 | gpt-6-sol | max | 51 | 0.6869 (`5ed0a2f`) | 0.6854 | -0.0015 | 0h59m23s | 55.4% | yes | |
| sol6_n20-14 | gpt-6-sol | max | 43 | 0.6858 (`b27ca12`) | 0.6846 | -0.0012 | 0h59m12s | 56.5% | yes | |
| sol6_n20-15 | gpt-6-sol | max | 39 | 0.6878 (`c7c19c0`) | 0.6856 | -0.0022 | 0h59m39s | 64.0% | yes | |
| sol6_n20-16 | gpt-6-sol | max | 31 | 0.6817 (`519d0ef`) | 0.6804 | -0.0013 | 0h59m42s | 70.0% | caveat | caveat: turn_retries (7 failed turns, model at capacity; retry waits 216 s) |
| sol6_n20-17 | gpt-6-sol | max | 35 | 0.6853 (`6321ab4`) | 0.6839 | -0.0014 | 0h58m26s | 54.7% | yes | |
| sol6_n20-18 | gpt-6-sol | max | 60 | 0.6864 (`08500bb`) | 0.6847 | -0.0017 | 0h59m08s | 39.8% | yes | |
| sol6_n20-19 | gpt-6-sol | max | 58 | 0.6889 (`c4b427d`) | 0.6866 | -0.0023 | 0h59m02s | 41.1% | caveat | caveat: keep_rule (tie kept as "faster" by 1.0 s, not simpler) |
| sol6_n20-20 | gpt-6-sol | max | 30 | 0.6860 (`ac85c11`) | 0.6838 | -0.0022 | 0h59m09s | 70.5% | yes | |

## Statistics over the valid runs (n = 20: 17 valid, 3 with a caveat)

| | n | mean | sd | min | median | max |
|---|---|---|---|---|---|---|
| Holdout AUC | 20 | 0.6842 | 0.0018 | 0.6803 | 0.6844 | 0.6871 |
| Eval AUC | 20 | 0.6860 | 0.0021 | 0.6817 | 0.6862 | 0.6893 |
| gap (holdout - eval) | 20 | -0.0018 | 0.0007 | -0.0036 | -0.0016 | -0.0006 |

sd is the sample standard deviation (n - 1); values formatted as the summary script does (`:.4f`). Unrounded: Holdout AUC mean 0.68418, median 0.68435; Eval AUC mean 0.68597, median 0.68620; gap mean -0.00179, median -0.00155. Experiments per run (rows of results.tsv): mean 45, from 29 to 70.

## Notes

- **Excluded: none.** All 20 runs pass the integrity checks, with 0 content hits in every leak check. Every run used codex-cli 0.160.0, `gpt-6-sol` at `max` (confirmed in each session's turn_context), the same upstream commit, a 3600 s budget and the 24 GB cap; no process was killed at the cap (peak memory 3.6 to 11.7 GiB).
- **Caveats: 3 runs.**
  - sol6_n20-16, `turn_retries`: 7 failed turns in a row, all "model at capacity"; the driver's retry waits took 216 s of the hour (limit 120 s), and one harness run was cut off and re-run.
  - sol6_n20-8 and sol6_n20-19, `keep_rule`: each kept a tie that is a single parameter change (DART `rate_drop` 0.1 → 0.2; `grow_policy` lossguide at the same depth) and was "faster" by 1.0 s in total, within run-to-run noise. Both were first counted as faster and reclassified at the end of the group, so that ties are judged as in luna6_n20 (where 0.3-1.1 s "faster" ties got `keep_rule` and only real simplifications or speed-ups were allowed). The reported AUCs are unaffected (in run 8 the tied commit is the best one and scores the same as the one before it; in run 19 the best is a later strict improvement, though one later gain, +0.0007, was built on the tied setting).
  - 16 other ties were kept for a real simplification (a feature or input removed, fewer or shallower trees, simpler code) or a real speed-up (20-30% faster scoring in runs 12 and 18); each is explained in its run.md.
- **`train_py_review` flag** on sol6_n20-12 is a false match: the check's pattern `glob` matches `global_delay_rate`, the train mean of a cross-fitted delay rate (fitted on train only) in a discarded commit.
- **Web research about this dataset** (allowed: reading for ideas; no data downloaded, no flight rows of eval or holdout seen):
  - sol6_n20-2 and -12 searched by the target column's name (`"dep_delayed_15min"`) and found the mlcourse.ai Kaggle competition built on this benchmark. Run 2 opened the assignment page, which prints 10 rows of the mlcourse.ai data; checked against train, eval and holdout, none of them is in any of the three files. Run 12 opened a solution gist (code only) and took one idea from it (a minute-not-a-multiple-of-5 flag, +0.0001).
  - sol6_n20-19 found an R Consortium talk on this dataset through a general search and took one idea from its snippet (half-hour departure slots, +0.0002, later an hourly category).
  - sol6_n20-8, -9, -12 and -20 also searched for "2005 2006" Kaggle or GitHub solutions; nothing about this dataset came back.
- **BTS pages:** runs 2, 8, 9, 10, 11, 15, 18 and 20 met BTS / TranStats pages in searches; runs 9, 11 and 15 opened the TranStats "Holiday Delay" page. What reached the log is the page's navigation and its table of holiday travel-season dates by year, plus headers and notes of other on-time pages (run 18's search results included the on-time data download page, not opened); no flight records and no 2005 or 2006 delay figures. sol6_n20-11's best model uses holiday windows built from that date table for 2005 and 2006 (calendar information, including the eval year, which program.md names); runs 5 and 17 likewise used the 2006 Thanksgiving date, computed or looked up.
- **Deprecated library behaviour in two best models:** sol6_n20-12 and -18 kept a faster `prepare` that builds `pd.Categorical` without masking unseen airports first; pandas 3.0.6 warns for every such evaluation row (2,421 warnings in run.log) but still yields NaN, so the AUCs are unaffected; with a later pandas these artifacts would fail to score. sol6_n20-8 and -14 use the DART booster, which xgboost 3.4.1 marks as deprecated.
- **Turns:** every run's agent asked about the run tag through codex's `request_user_input_async`, which nobody sees in `codex exec`, and waited 30 to 90 s with `sleep` before the clock started; one "go" answered it in every run (sol6_n20-20 needed a second "go" only because its first two turns failed before the clock started). Failed turns, all "model at capacity" and none of another kind: run 4 (1, 31 s of waits), run 16 (7, 216 s), run 17 (1, 31 s), run 20 (4, of which 2 before the clock; 62 s). Runs 4 and 16 each had one harness run cut off and re-run.
- **Clock:** every run's agent stopped the clock itself. 18 runs stopped with 18 to 94 s left; runs 1 and 2 stopped 59 s and 28 s after the budget ran out, because their last status check showed just over 2 minutes and the wrap-up came after one more experiment (no harness run after the budget). Context compaction happened once each in runs 9 and 12, near the end.
- **Gaps:** -0.0006 to -0.0036, mean -0.0018, the same as the starter's -0.0018; all inside the provisional thresholds (-0.006 / +0.003). The largest, run 11 (-0.0036), opened in its last three keeps (L1 and sampling tweaks: +0.0013 on eval, -0.0005 on holdout).
- **What worked:** most runs gained most from shallower trees at a lower learning rate (depth 3 or 4, about +0.005 to +0.008); runs 5 and 6 kept deeper trees and regularized through fewer rounds, sampling and leaf limits instead. 19 of 20 added a numeric calendar feature (day of year, or day of month or week of month as a number instead of a category), worth +0.001 to +0.005; the one run without it (16) has the lowest Eval AUC and the second-lowest Holdout AUC of the group. Route (origin-destination) categories always lowered Eval AUC. The best holdout, sol6_n20-8 (0.6871), averaged five models (two of them DART) with numeric calendar fields and a year-end travel flag.

For reference, the starter `train.py` scores 0.6743 on eval and 0.6725 on holdout (gap -0.0018).
