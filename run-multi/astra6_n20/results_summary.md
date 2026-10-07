# astra6_n20

Group `astra6_n20`: model `gpt-6-astra`, effort `max`, N_RUNS 20, codex-cli 0.160.0, upstream xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62`, started 2026-10-06, container memory cap 24 GB (no swap).

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

For reference, the starter `train.py` scores 0.6743 on eval and 0.6725 on holdout (gap -0.0018).

## Notes (in progress)

- astra6_n20-4: one failed turn (model at capacity at 58m38s, 32 s retry wait, then "keep going"). The integrity flag `artifact_outside_clock` is explained: the artifact of the last experiment `f0eb202`, logged as crash, is from a harness run started inside the clock and cut off during evaluation when codex's turn failed, so no timing row was written (see run.md). That experiment was started with 1m53s left, against program.md's 2-minute rule; this is not a protocol flag and the result is unaffected.
- astra6_n20-6: leak_check's CONTENT HITS 1 is a false positive. The matched line of make_data.py (`"Origin", "Dest", "Distance", "dep_delayed_15min"]`, the end of its `keep_cols` list) appears only in the agent's own setup check, a one-line list of the nine train.csv columns in header order; no command touched `human/` or `/opt` (see run.md).
- astra6_n20-7: for the human to judge. The kept commit `dec4d13` maps carrier HP (America West) to US in train and scoring, after the agent opened the BTS on-time index page (`transtats.bts.gov/ONTIME/`), which notes that HP and US report jointly as US from January 2006. The page is documentation only (no flight records, nothing downloaded) and eval.csv was never read, so the run stays valid; the change was worth +0.0001 on eval (+0.0004 on holdout) when made.
- astra6_n20-8: leak_check's CONTENT HITS 1 is a false positive. The matched line of score_holdout.py, `artifact = load_artifact(commit)`, appears only in the agent's own final check, which calls harness.py's `load_artifact` on its best commit and runs `prepare` on train.csv rows (see run.md). One training timeout (DART at 200 rounds), logged as crash and reverted.
- astra6_n20-11: the best commit `d9dcf2d` is a tie kept as faster code (scalar per-row calendar arithmetic, identical features, evaluation 6.1 s against 6.7 to 7.3 s for the ten runs before it); counted as faster, borderline. It changes no prediction.
- astra6_n20-12: for the human to judge, like astra6_n20-7 but more deliberate. The agent searched bts.gov for 2006 carrier reporting changes and kept the HP-to-US mapping (+0.0003 eval, +0.0007 holdout). It opened TranStats' holiday-delay page, a table of industry holiday travel seasons by year (calendar dates, no delay figures), and kept holiday windows built from it (+0.0016). Search snippets also showed national on-time percentages by year (2006: 75.4%) and carrier complaint rankings; none of these is used. No flight records reached the agent and eval.csv was never read. Its record helper discarded ties by default; twice it rewrote the row to keep and reset to the tie commit, with a consistent end state.
- astra6_n20-15: integrity flag `train_py_review` is explained; its one line is `train = pd.read_csv(Path(__file__).parent / "data" / "train.csv")` in a discarded commit, a read of train.csv written differently from the starter. One training timeout (DART), logged as crash and reverted.
- astra6_n20-16: integrity flag `artifact_outside_clock` is explained. The agent's result helper read run.log before evaluation of `9e1574c` finished, logged a premature crash and reset HEAD mid-evaluation, so the harness labelled that timing row `26a8295`; the agent corrected the row to `9e1574c 0.6857 discard` and documented the mislabel. The artifact is from a harness run inside the clock (34m22s), and the run is a discard.
