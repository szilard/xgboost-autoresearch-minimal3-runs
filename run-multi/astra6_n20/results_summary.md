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

For reference, the starter `train.py` scores 0.6743 on eval and 0.6725 on holdout (gap -0.0018).

## Notes (in progress)

- astra6_n20-4: one failed turn (model at capacity at 58m38s, 32 s retry wait, then "keep going"). The integrity flag `artifact_outside_clock` is explained: the artifact of the last experiment `f0eb202`, logged as crash, is from a harness run started inside the clock and cut off during evaluation when codex's turn failed, so no timing row was written (see run.md). That experiment was started with 1m53s left, against program.md's 2-minute rule; this is not a protocol flag and the result is unaffected.
- astra6_n20-6: leak_check's CONTENT HITS 1 is a false positive. The matched line of make_data.py (`"Origin", "Dest", "Distance", "dep_delayed_15min"]`, the end of its `keep_cols` list) appears only in the agent's own setup check, a one-line list of the nine train.csv columns in header order; no command touched `human/` or `/opt` (see run.md).
