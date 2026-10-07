# astra6_n20

Group `astra6_n20`: model `gpt-6-astra`, effort `max`, N_RUNS 20, codex-cli 0.160.0, upstream xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62`, 2026-10-06 to 2026-10-07, container memory cap 24 GB (no swap).

| run | model | effort | experiments | best Eval AUC (commit) | Holdout AUC | gap | total time | AI share | valid | caveat / excluded |
|---|---|---|---|---|---|---|---|---|---|---|
| astra6_n20-1 | gpt-6-astra | max | 47 | 0.6900 (`50e74b8`) | 0.6880 | -0.0020 | 0h59m34s | 84.5% | yes | |
| astra6_n20-2 | gpt-6-astra | max | 42 | 0.6863 (`6826f09`) | 0.6836 | -0.0027 | 1h00m34s | 51.4% | yes | |
| astra6_n20-3 | gpt-6-astra | max | 50 | 0.6918 (`43097e4`) | 0.6886 | -0.0032 | 0h59m38s | 72.9% | yes | |
| astra6_n20-4 | gpt-6-astra | max | 36 | 0.6843 (`c58ee9e`) | 0.6815 | -0.0028 | 1h01m18s | 67.5% | yes | |
| astra6_n20-5 | gpt-6-astra | max | 47 | 0.6876 (`ade4fcf`) | 0.6846 | -0.0030 | 1h00m16s | 74.5% | caveat | caveat: `keep_rule`: `7b7712f` (gamma 5) kept at a tie as "faster" by 0.8 s, within noise, not simpler; gamma 5 stayed in the best model |
| astra6_n20-6 | gpt-6-astra | max | 41 | 0.6881 (`e8e4e36`) | 0.6846 | -0.0035 | 0h59m39s | 79.2% | yes | |
| astra6_n20-7 | gpt-6-astra | max | 43 | 0.6905 (`063f35f`) | 0.6881 | -0.0024 | 0h59m13s | 84.9% | yes | |
| astra6_n20-8 | gpt-6-astra | max | 50 | 0.6879 (`eccad8d`) | 0.6856 | -0.0023 | 0h59m40s | 78.1% | caveat | caveat: `keep_rule`: `e5e4a2b` (`max_cat_threshold` 16) kept at a tie, 0.2 s faster, not simpler; it stayed in the best model |
| astra6_n20-9 | gpt-6-astra | max | 36 | 0.6913 (`d1fbdd2`) | 0.6888 | -0.0025 | 0h59m14s | 68.1% | yes | |
| astra6_n20-10 | gpt-6-astra | max | 45 | 0.6878 (`0d30a13`) | 0.6845 | -0.0033 | 0h59m41s | 69.8% | yes | |
| astra6_n20-11 | gpt-6-astra | max | 52 | 0.6897 (`d9dcf2d`) | 0.6860 | -0.0037 | 0h59m59s | 84.1% | yes | |
| astra6_n20-12 | gpt-6-astra | max | 51 | 0.6909 (`8052d06`) | 0.6873 | -0.0036 | 0h59m24s | 67.6% | caveat | caveat: `keep_rule`: `d4bd0fc` (`max_bin` 64) kept at a tie for 1.1 s in one timing, not simpler; it stayed in the best model |
| astra6_n20-13 | gpt-6-astra | max | 59 | 0.6935 (`7cdfba0`) | 0.6906 | -0.0029 | 1h00m32s | 63.8% | yes | |
| astra6_n20-14 | gpt-6-astra | max | 62 | 0.6917 (`4c0a951`) | 0.6888 | -0.0029 | 0h59m37s | 69.6% | yes | |
| astra6_n20-15 | gpt-6-astra | max | 54 | 0.6875 (`896f434`) | 0.6856 | -0.0019 | 0h59m32s | 66.0% | yes | |
| astra6_n20-16 | gpt-6-astra | max | 49 | 0.6894 (`cb6c121`) | 0.6870 | -0.0024 | 0h59m30s | 67.5% | yes | |
| astra6_n20-17 | gpt-6-astra | max | 46 | 0.6898 (`a567151`) | 0.6872 | -0.0026 | 0h58m42s | 61.8% | yes | |
| astra6_n20-18 | gpt-6-astra | max | 44 | 0.6901 (`1f5c0f6`) | 0.6878 | -0.0023 | 0h59m32s | 66.2% | yes | |
| astra6_n20-19 | gpt-6-astra | max | 49 | 0.6910 (`cbf5e51`) | 0.6876 | -0.0034 | 0h59m14s | 79.8% | yes | |
| astra6_n20-20 | gpt-6-astra | max | 40 | 0.6876 (`fc0e2f7`) | 0.6853 | -0.0023 | 0h59m25s | 73.3% | yes | |

## Statistics over the valid runs (n = 20: 17 valid, 3 with a caveat)

| | n | mean | sd | min | median | max |
|---|---|---|---|---|---|---|
| Holdout AUC | 20 | 0.6866 | 0.0022 | 0.6815 | 0.6871 | 0.6906 |
| Eval AUC | 20 | 0.6893 | 0.0022 | 0.6843 | 0.6898 | 0.6935 |
| gap (holdout - eval) | 20 | -0.0028 | 0.0005 | -0.0037 | -0.0028 | -0.0019 |

sd is the sample standard deviation (n - 1). Unrounded: Holdout AUC mean 0.68656, median 0.68710; Eval AUC mean 0.68934, median 0.68975; gap mean -0.00279, median -0.00275. Experiments per run (rows of results.tsv): mean 47, from 36 to 62.

For reference, the starter `train.py` scores 0.6743 on eval and 0.6725 on holdout (gap -0.0018). For comparison (same harness, data and driver): luna6_n20 has a Holdout AUC mean of 0.6807 and sol6_n20 0.6842, both with a mean gap of -0.0018.

## Notes

- **Excluded: none.** Every run passes the integrity checks. Three runs carry an explained integrity flag, and two leak checks have one false-positive content hit each:
  - astra6_n20-4 and -16: `artifact_outside_clock`, explained.
  - astra6_n20-15: `train_py_review`, explained.
  - astra6_n20-6 and -8: one content hit each, a false positive.

  Details per run below and in each run.md.
- **Caveats: 3 runs, all `keep_rule`** (astra6_n20-5, -8, -12). Each kept a tie from a single added or changed parameter, justified as faster by 0.2 to 1.1 s, within the noise: gamma 5, `max_cat_threshold` 16 and `max_bin` 64. Each setting stayed in the best model. The other 56 kept ties of the group were real code speedups or simplifications (smaller models, removed features or parameters); two of them are borderline and allowed (astra6_n20-11 and -13, see run.md).
- **For the human to judge (astra6_n20-7 and -12): eval-year knowledge from BTS documentation.** Both runs kept a mapping of carrier HP (America West) to US (US Airways). They got it from BTS on-time pages noting that the two report jointly from January 2006.
  - Run 12 also built holiday windows from TranStats' table of industry holiday travel seasons (calendar dates).
  - Neither run saw flight records or read eval.csv, so both stay valid.
  - The HP mapping was worth +0.0001 / +0.0003 on eval and +0.0004 / +0.0007 on holdout when made.
  - No other run of the group (or of luna6_n20 / sol6_n20) maps carriers.
- **Turns:** every run needed one "go" and no "keep going", except astra6_n20-4. Its "go" turn failed with a capacity error at 58m38s; the driver waited 32 s, then sent "keep going". That was the only failed turn of the group (`retry_wait_s` 0 elsewhere), and it stayed under the 2-minute `turn_retries` threshold.
- **Clock:** the agent stopped the clock itself in every run.
  - 16 runs stopped with 1 to 78 s left.
  - 4 stopped 16 to 78 s after the budget ran out (runs 2, 4, 5, 13), during wrap-up or after a context compaction. Their last experiments ended inside the budget, except run 4's interrupted one.
  - In astra6_n20-4 the last experiment was started with 1m53s left, against program.md's 2-minute rule. This is not a flag, and it was a crash with no effect on the result.
- **Context compactions** in 11 of the 20 runs, mostly in the last 15 minutes. None disturbed the protocol.
- **Gaps:** -0.0019 to -0.0037, mean -0.0028, all inside the provisional thresholds (-0.006 / +0.003). The mean is 0.0010 lower than in luna6_n20 and sol6_n20 (both -0.0018), so selection on Eval AUC overfits the eval half somewhat more with this model. A run below about -0.004 would now stand out.
- **What worked:**
  - Almost every run first gained from shallower, regularized boosting and from dropping the `DayofMonth` (and often `Month`) categories, or turning them into numbers.
  - **Holiday features are in the best model of 15 of 20 runs** (offsets, windows or flags, computed from each row's month, day and weekday). They were often the largest late gain (+0.002 to +0.003).
  - Other recurring parts:
    - airport coordinates or landmark distances computed from the train route-distance graph
    - departure offsets from train schedule medians
    - boosted forests (`num_parallel_tree`) and seed averaging
    - strong L1 / L2 regularization
    - recency and monthly class-balance weights
  - Route and carrier-airport categories mostly hurt, except with one-level splits (runs 2, 10, 20).
- **Best runs:** astra6_n20-13 (Eval 0.6935, Holdout 0.6906, a fortnight-of-year feature and calendar interaction constraints); then -9 and -14 (Holdout 0.6888) and -3 (0.6886).
- **Memory:** peak 3.4 to 6.0 GiB, except astra6_n20-18 at 16.5 GiB (three 1200-round one-hot models). Nothing was killed at the 24 GB cap.
- **Driver order:** I started astra6_n20-17 about 2 minutes late (02:48:49 instead of about 02:46:30), because I reviewed run 16 before launching it. No other run is affected.

### Per-run details

- astra6_n20-4: one failed turn (model at capacity at 58m38s, 32 s retry wait, then "keep going"). The integrity flag `artifact_outside_clock` is explained: the artifact of the last experiment `f0eb202`, logged as crash, is from a harness run started inside the clock and cut off during evaluation when codex's turn failed, so no timing row was written (see run.md). That experiment was started with 1m53s left, against program.md's 2-minute rule; this is not a protocol flag and the result is unaffected.
- astra6_n20-6: leak_check's CONTENT HITS 1 is a false positive. The matched line of make_data.py (`"Origin", "Dest", "Distance", "dep_delayed_15min"]`, the end of its `keep_cols` list) appears only in the agent's own setup check, a one-line list of the nine train.csv columns in header order; no command touched `human/` or `/opt` (see run.md).
- astra6_n20-7: for the human to judge. The kept commit `dec4d13` maps carrier HP (America West) to US in train and scoring, after the agent opened the BTS on-time index page (`transtats.bts.gov/ONTIME/`), which notes that HP and US report jointly as US from January 2006. The page is documentation only (no flight records, nothing downloaded) and eval.csv was never read, so the run stays valid; the change was worth +0.0001 on eval (+0.0004 on holdout) when made.
- astra6_n20-8: leak_check's CONTENT HITS 1 is a false positive. The matched line of score_holdout.py, `artifact = load_artifact(commit)`, appears only in the agent's own final check, which calls harness.py's `load_artifact` on its best commit and runs `prepare` on train.csv rows (see run.md). One training timeout (DART at 200 rounds), logged as crash and reverted.
- astra6_n20-11: the best commit `d9dcf2d` is a tie kept as faster code (scalar per-row calendar arithmetic, identical features, evaluation 6.1 s against 6.7 to 7.3 s for the ten runs before it); counted as faster, borderline. It changes no prediction.
- astra6_n20-12: for the human to judge, like astra6_n20-7 but more deliberate. The agent searched bts.gov for 2006 carrier reporting changes and kept the HP-to-US mapping (+0.0003 eval, +0.0007 holdout). It opened TranStats' holiday-delay page, a table of industry holiday travel seasons by year (calendar dates, no delay figures), and kept holiday windows built from it (+0.0016). Search snippets also showed national on-time percentages by year (2006: 75.4%) and carrier complaint rankings; none of these is used. No flight records reached the agent and eval.csv was never read. Its record helper discarded ties by default; twice it rewrote the row to keep and reset to the tie commit, with a consistent end state.
- astra6_n20-15: integrity flag `train_py_review` is explained; its one line is `train = pd.read_csv(Path(__file__).parent / "data" / "train.csv")` in a discarded commit, a read of train.csv written differently from the starter. One training timeout (DART), logged as crash and reverted.
- astra6_n20-16: integrity flag `artifact_outside_clock` is explained. The agent's result helper read run.log before evaluation of `9e1574c` finished, logged a premature crash and reset HEAD mid-evaluation, so the harness labelled that timing row `26a8295`; the agent corrected the row to `9e1574c 0.6857 discard` and documented the mislabel. The artifact is from a harness run inside the clock (34m22s), and the run is a discard.
- astra6_n20-18: peak container memory 16.5 GiB, against 3.4 to 6.0 GiB in the other runs; no process was killed at the 24 GB cap and no harness run crashed or timed out.
