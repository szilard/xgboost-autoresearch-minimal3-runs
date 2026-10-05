# luna6_n20

Group `luna6_n20`: model `gpt-6-luna`, effort `max`, N_RUNS 20, codex-cli 0.160.0, upstream xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62`, started 2026-10-05, container memory cap 24 GB (no swap).

| run | model | effort | experiments | best Eval AUC (commit) | Holdout AUC | gap | total time | AI share | valid | caveat / excluded |
|---|---|---|---|---|---|---|---|---|---|---|
| luna6_n20-1 | gpt-6-luna | max | 36 | 0.6844 (`de6a11d`) | 0.6822 | -0.0022 | 0h58m51s | 58.8% | yes | |
| luna6_n20-2 | gpt-6-luna | max | 25 | 0.6813 (`9cb236b`) | 0.6789 | -0.0024 | 0h59m07s | 74.5% | yes | |

In progress: 2 of 20 runs done. The statistics follow once all runs are done.

For reference, the starter `train.py` scores 0.6743 on eval and 0.6725 on holdout (gap -0.0018).
