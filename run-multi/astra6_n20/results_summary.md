# astra6_n20

Group `astra6_n20`: model `gpt-6-astra`, effort `max`, N_RUNS 20, codex-cli 0.160.0, upstream xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62`, started 2026-10-06, container memory cap 24 GB (no swap).

| run | model | effort | experiments | best Eval AUC (commit) | Holdout AUC | gap | total time | AI share | valid | caveat / excluded |
|---|---|---|---|---|---|---|---|---|---|---|
| astra6_n20-1 | gpt-6-astra | max | 47 | 0.6900 (`50e74b8`) | 0.6880 | -0.0020 | 0h59m34s | 84.5% | yes | |

For reference, the starter `train.py` scores 0.6743 on eval and 0.6725 on holdout (gap -0.0018).
