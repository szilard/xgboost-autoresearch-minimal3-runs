# sol6_n20

Group `sol6_n20`: model `gpt-6-sol`, effort `max`, N_RUNS 20, codex-cli 0.160.0, upstream xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62`, started 2026-10-05, container memory cap 24 GB (no swap).

| run | model | effort | experiments | best Eval AUC (commit) | Holdout AUC | gap | total time | AI share | valid | caveat / excluded |
|---|---|---|---|---|---|---|---|---|---|---|
| sol6_n20-1 | gpt-6-sol | max | 34 | 0.6865 (`fa052d9`) | 0.6850 | -0.0015 | 1h00m59s | 68.4% | yes | |
| sol6_n20-2 | gpt-6-sol | max | 34 | 0.6858 (`b602c3f`) | 0.6836 | -0.0022 | 1h00m28s | 64.0% | yes | |
| sol6_n20-3 | gpt-6-sol | max | 35 | 0.6857 (`72d7e0a`) | 0.6841 | -0.0016 | 0h58m34s | 60.4% | yes | |
| sol6_n20-4 | gpt-6-sol | max | 29 | 0.6831 (`07f5782`) | 0.6821 | -0.0010 | 0h58m55s | 71.0% | yes | |
| sol6_n20-5 | gpt-6-sol | max | 47 | 0.6839 (`8202360`) | 0.6826 | -0.0013 | 0h58m46s | 40.2% | yes | |
| sol6_n20-6 | gpt-6-sol | max | 43 | 0.6818 (`44473d1`) | 0.6803 | -0.0015 | 0h59m02s | 47.6% | yes | |
| sol6_n20-7 | gpt-6-sol | max | 58 | 0.6866 (`eb1987a`) | 0.6837 | -0.0029 | 0h59m01s | 43.1% | yes | |
| sol6_n20-8 | gpt-6-sol | max | 48 | 0.6877 (`83775c5`) | 0.6871 | -0.0006 | 0h59m22s | 44.8% | yes | |
| sol6_n20-9 | gpt-6-sol | max | 51 | 0.6846 (`348d81c`) | 0.6834 | -0.0012 | 0h58m28s | 41.4% | yes | |
| sol6_n20-10 | gpt-6-sol | max | 51 | 0.6885 (`c3b3a92`) | 0.6864 | -0.0021 | 0h59m06s | 49.0% | yes | |
| sol6_n20-11 | gpt-6-sol | max | 55 | 0.6893 (`cd0df4b`) | 0.6857 | -0.0036 | 0h59m15s | 47.3% | yes | |
| sol6_n20-12 | gpt-6-sol | max | 70 | 0.6870 (`43d5c46`) | 0.6846 | -0.0024 | 0h58m52s | 43.1% | yes | |
| sol6_n20-13 | gpt-6-sol | max | 51 | 0.6869 (`5ed0a2f`) | 0.6854 | -0.0015 | 0h59m23s | 55.4% | yes | |

In progress: 13 of 20 runs done. The statistics follow once all runs are done.

For reference, the starter `train.py` scores 0.6743 on eval and 0.6725 on holdout (gap -0.0018).
