# Optimizing XGBoost Machine Learning Models with AI Agents: Runs

**TL;DR:** Runs [xgboost-autoresearch-minimal2](https://github.com/szilard/xgboost-autoresearch-minimal2) (an AI coding agent autonomously tunes an XGBoost model, and its gains are then checked on a held-out test set it never sees) with various agents/LLMs, once or repeatedly, fully automated. Repeated runs show how much the result of the same agent/LLM varies from run to run.

This is the orchestrator for [xgboost-autoresearch-minimal2](https://github.com/szilard/xgboost-autoresearch-minimal2), itself a follow-up to [xgboost-autoresearch](https://github.com/szilard/xgboost-autoresearch).
Another follow-up project is [identical-runs-different-results](https://github.com/earino/identical-runs-different-results) and the corresponding [arXiv paper](https://arxiv.org/abs/2609.33812).

How a run works (the task, the agent's loop and the guardrails are described in the [xgboost-autoresearch-minimal2 README](https://github.com/szilard/xgboost-autoresearch-minimal2)):

- **Isolation:** each run gets a fresh Docker container (`agents2` image) with a clean copy of `xgboost-autoresearch-minimal2`: no history and no earlier results, so the agent cannot see previous runs. Only the agent's login is shared with the container.
- **Agent:** currently codex, on a ChatGPT subscription (OpenAI models, at a chosen reasoning effort, e.g. `max`). It gets the prompt from the `xgboost-autoresearch-minimal2` README and then works on its own for 2 hours, enforced by the harness clock; the orchestrator only sends "go" to start and "keep going" if it stops early.
- **Ground truth:** after the run, every kept model is scored on the holdout set (`groundtruth_all.tsv`, `auc_history.png`).
- **Validity checks:** the model and effort actually used (from the agent's session log), the eval/holdout gap, only `train.py` changed, and no access to the holdout data or the human-only scripts (also searched for their content in the agent's commands and outputs). Runs that fail a check are recorded as excluded; a run whose only issue is reading `prepare.py` during setup, with nothing further, is kept as valid with a caveat.
- **Orchestration:** by Claude Code, with the project skill `/xgb-multi <group> <model> <n-runs> [effort]`: N sequential runs of the same setup (N = 1 for a single run), each driven identically by a script, results in `run-multi/<group>/<group>-<i>/`, plus a group `results_summary.md` (with mean/sd/min/median/max over the valid runs) and `holdout_auc.tsv` (one line per run, for plots such as histograms). Claude reviews each run and writes up the results.

Each run's folder has the agent's `results.tsv`, `research-log.md` and final `train.py`, the ground truth scores and plot, the harness timing report, the git log, the agent's session log (gzipped, with the encrypted reasoning dropped and account ids redacted) and a `run.md` with the settings, the turns sent, the validity checks and anything notable.

## Results so far

10 runs per model, codex-cli 0.159.0, effort `max`, 24 GB container memory cap. Holdout AUC of each run's best model (by eval AUC), over the valid runs, including those with a caveat (see below); the baseline `train.py` scores 0.7155:

| group | model | valid runs | holdout AUC mean | sd | min | median | max |
|---|---|---|---|---|---|---|---|
| [astra6_n10](run-multi/astra6_n10/results_summary.md) | gpt-6-astra | 10 (3 with caveat) | 0.7616 | 0.0027 | 0.7589 | 0.7609 | 0.7663 |
| [sol6_n10](run-multi/sol6_n10/results_summary.md) | gpt-6-sol | 10 (4 with caveat) | 0.7585 | 0.0035 | 0.7510 | 0.7581 | 0.7626 |
| [luna6_n10](run-multi/luna6_n10/results_summary.md) | gpt-6-luna | 10 | 0.7504 | 0.0076 | 0.7348 | 0.7520 | 0.7598 |

"With caveat": the agent read the human-only `prepare.py` in its first batch of setup reads, before it had read the rule against it, disclosed it itself and went no further (no holdout or source-data access); such runs are kept, marked `caveat` in `holdout_auc.tsv`, and their results don't differ from the clean runs'. No run so far was excluded.

![Holdout AUC per run](run-multi/SUMMARY/holdout_auc_beeswarm.png)

Plots over all groups, in [run-multi/SUMMARY/](run-multi/SUMMARY/):

- `holdout_auc_beeswarm.png` (above): one dot per run (hollow: with caveat), the mean with its 90% interval and the 10th/90th percentiles per model;
- `holdout_auc_pairwise.png`: head to head - the probability that one run of a model beats one run of another, with a 90% bootstrap interval;
- `holdout_auc_path_panels.png`, `holdout_auc_path_bands.png`, `holdout_auc_path_median.png`: the holdout AUC of the kept model after each experiment - per run in one panel per model, as a median with a 10th-90th percentile band per model, and all runs faded with the medians in bold.

They are made by `tools/plot_holdout_auc.py` (beeswarm and paths) and `tools/pairwise_win_prob.py` (head to head; it also prints the table), which read every group's `holdout_auc.tsv` and pool groups of the same model.

Earlier runs - the first test group luna-test (3 runs of gpt-5.6-luna, before the memory cap) and a single run driven live by Claude with the retired `/xgb-run` skill - are in [archive/](archive/).

## Machine and setup

Recommended machine: m8i.2xlarge (8 cores, 32 GB RAM). The per-run time limits depend on the hardware, so compare results only across runs on the same machine type. Runs are sequential, since each uses all cores.

Setup and usage: [setup/README.md](setup/README.md).
