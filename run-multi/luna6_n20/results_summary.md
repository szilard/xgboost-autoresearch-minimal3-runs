# luna6_n20

Group `luna6_n20`: model `gpt-6-luna`, effort `max`, N_RUNS 20, codex-cli 0.160.0, upstream xgboost-autoresearch-minimal3 @ `5fb023a70fbee73d0d2ee7a3b5875726981c8c62`, started 2026-10-05, container memory cap 24 GB (no swap).

| run | model | effort | experiments | best Eval AUC (commit) | Holdout AUC | gap | total time | AI share | valid | caveat / excluded |
|---|---|---|---|---|---|---|---|---|---|---|
| luna6_n20-1 | gpt-6-luna | max | 36 | 0.6844 (`de6a11d`) | 0.6822 | -0.0022 | 0h58m51s | 58.8% | yes | |
| luna6_n20-2 | gpt-6-luna | max | 25 | 0.6813 (`9cb236b`) | 0.6789 | -0.0024 | 0h59m07s | 74.5% | yes | |
| luna6_n20-3 | gpt-6-luna | max | 29 | 0.6820 (`9c46a06`) | 0.6803 | -0.0017 | 0h58m37s | 67.9% | yes | |
| luna6_n20-4 | gpt-6-luna | max | 37 | 0.6824 (`d72b8ff`) | 0.6797 | -0.0027 | 0h58m44s | 61.9% | yes | |
| luna6_n20-5 | gpt-6-luna | max | 25 | 0.6803 (`8bfaefd`) | 0.6789 | -0.0014 | 0h58m31s | 73.1% | yes | |
| luna6_n20-6 | gpt-6-luna | max | 30 | 0.6821 (`bd192f4`) | 0.6800 | -0.0021 | 0h58m54s | 58.7% | caveat | caveat: `keep_rule`: `bd192f4` (gamma 0.1) kept at a tie, for an evaluation 0.6 s faster, within noise; the commit before it has the same Eval and Holdout AUC |
| luna6_n20-7 | gpt-6-luna | max | 25 | 0.6813 (`e91e44a`) | 0.6795 | -0.0018 | 0h58m32s | 79.2% | yes | |
| luna6_n20-8 | gpt-6-luna | max | 28 | 0.6809 (`7a1cbf0`) | 0.6795 | -0.0014 | 0h58m51s | 73.2% | caveat | caveat: `keep_rule`: two ties kept for a faster run that is noise (`744ceef`, `7a1cbf0`, `min_child_weight` 5 and 10); each has the same Eval and Holdout AUC as the commit before it |
| luna6_n20-9 | gpt-6-luna | max | 24 | 0.6859 (`794421a`) | 0.6844 | -0.0015 | 0h58m35s | 69.6% | yes | |
| luna6_n20-10 | gpt-6-luna | max | 32 | 0.6828 (`b0110e3`) | 0.6820 | -0.0008 | 0h59m15s | 68.9% | yes | |

In progress: 10 of 20 runs done. The statistics follow once all runs are done.

For reference, the starter `train.py` scores 0.6743 on eval and 0.6725 on holdout (gap -0.0018).
