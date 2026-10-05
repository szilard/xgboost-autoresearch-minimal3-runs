# sol6_n20

Group `sol6_n20`: model `gpt-6-sol`, effort `max`, N_RUNS 20, codex-cli 0.160.0, upstream xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62`, started 2026-10-05, container memory cap 24 GB (no swap).

| run | model | effort | experiments | best Eval AUC (commit) | Holdout AUC | gap | total time | AI share | valid | caveat / excluded |
|---|---|---|---|---|---|---|---|---|---|---|
| sol6_n20-1 | gpt-6-sol | max | 34 | 0.6865 (`fa052d9`) | 0.6850 | -0.0015 | 1h00m59s | 68.4% | yes | |
| sol6_n20-2 | gpt-6-sol | max | 34 | 0.6858 (`b602c3f`) | 0.6836 | -0.0022 | 1h00m28s | 64.0% | yes | |

In progress: 2 of 20 runs done. The statistics follow once all runs are done.

For reference, the starter `train.py` scores 0.6743 on eval and 0.6725 on holdout (gap -0.0018).
