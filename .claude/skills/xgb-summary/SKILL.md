---
name: xgb-summary
description: Bring the summary over all run groups in run-multi/ up to date - check the group files, redraw the SUMMARY plots, print the head-to-head table and rewrite the results block of the README.
disable-model-invocation: true
---

No arguments. Everything comes from the group files that /xgb-multi wrote:
each `run-multi/<group>/holdout_auc.tsv` and the runs' `driver-summary.json`,
`holdout_scores.tsv` and harness timing (`timing/clock.json`,
`timing/runs.tsv`). Groups of the same model are pooled, runs with
`valid` = `no` are left out, runs with a caveat are included.

The mechanical part is done by three scripts, run from the repo root without
arguments:

- `tools/summary_table.py` - checks the group files and prints the results
  table per model. It changes nothing.
- `tools/plot_holdout_auc.py` - the beeswarm plot and the two path plots.
- `tools/pairwise_win_prob.py` - the head-to-head table and its plot.

Your job is to run them, act on what they report, look at the plots and
rewrite the results block of README.md. Don't compute any statistics
yourself: every number in the README comes from the scripts' output.

## Steps

1. Run `tools/summary_table.py`. If it says there are no groups, tell me and
   stop. Otherwise go through its WARNING lines before anything is written:
   - **a group looks like a test group**: stop and ask me whether to include
     it or to move it out of run-multi/ first (`git mv run-multi/<group>
     archive/<group>`; do that only if I say so). Its runs would be pooled
     with all other runs of that model.
   - **a row of holdout_auc.tsv disagrees with driver-summary.json**, a wrong
     gap, a `valid` that is not yes, caveat or no, `valid` = yes with
     flags, or `valid` = caveat without flags: stop and tell me which rows.
     Don't correct the files yourself.
   - **a valid run without a holdout AUC**, or valid although the driver's
     status is failed: stop and tell me.
   - **mixed effort, upstream or time_budget_s**: stop and ask me. Runs at a
     different effort, minimal3 commit or time budget are not the same
     experiment and should not be pooled.
   - **mixed codex_version or memory_limit_bytes**: carry on, and say so in
     the README intro and in your summary to me.
   - **a run folder that is not in holdout_auc.tsv**: that group is in
     progress (a run still going or not yet reviewed). Carry on, and say in
     the README notes that the group is in progress.
   - **more than one model in a group**, or a missing driver-summary.json:
     stop and tell me.
   - **a caveat that has no plotting rule**: a kind of caveat that turns up
     for the first time. Stop and ask me whether runs with it are to be
     marked in the plots (hollow dots, dashed lines) or drawn like any other
     run. Tell me what the caveat is and what it did to the result, from the
     runs' run.md. Then add the kind to `CAVEAT_MARKED` or `CAVEAT_PLAIN` in
     `tools/plot_holdout_auc.py` as I say, and run `summary_table.py` again.
     Never move a kind that is already in one of the two sets. The kinds are
     the flags of holdout_auc.tsv, except that `keep_rule` is split: it
     stays `keep_rule` when the driver's own checks flagged it (a kept
     commit with a lower Eval AUC) and is `keep_rule_tie` when it was added
     in the review (a tie kept without being simpler or faster).

2. Run `tools/plot_holdout_auc.py`, then `tools/pairwise_win_prob.py`. They
   write the PNGs to `run-multi/SUMMARY/`.
   - If the first one warns that a model has no fixed colour, add the model
     to `MODEL_SLOT` in `tools/plot_holdout_auc.py` with the lowest slot
     number not yet used, and run both again. Never change the slot of a
     model that is already there: the colour follows the model in all plots.
   - With fewer than two models there is no head-to-head plot. With fewer
     than 5 runs a model has no interval, percentile marks or median path.
     The legends have a "run with caveat" entry only when a run is marked.
     All are as intended.

3. Look at every PNG in `run-multi/SUMMARY/` that was just written. Each
   model with valid runs must be there, with as many dots or lines as the
   table has valid runs; the runs whose NOTE line says "marked" hollow
   (dashed in the path plots) and no others; nothing cut off, overlapping
   or unreadable; the range of the dots in the beeswarm plot must match the
   table's min and max. If a plot is wrong, tell me what is wrong. Don't restyle the plots
   yourself.

4. In README.md, replace everything between the lines
   `<!-- xgb-summary: start ... -->` and `<!-- xgb-summary: end -->` (keep
   both lines) with, in this order:
   - One intro sentence with the settings printed by `summary_table.py`: the
     number of runs per model if it is the same for all models (otherwise
     leave it to the table), the codex version, the effort, the container
     memory cap in GB and the upstream minimal3 commit (first 7 characters).
     Then: "Holdout AUC of each run's best model (by eval AUC; on a tie the
     last kept commit), over the valid runs, including those with a caveat;
     the starter `train.py` scores 0.6725:"
   - The markdown table exactly as printed.
   - One short paragraph of notes, from the NOTE lines: which caveats there
     are, how many runs carry each and whether the plots mark them; how
     many runs were excluded and why,
     in a few words each (or "No run was excluded."); which groups are in
     progress; anything mixed from step 1. A valid run with integrity flags
     must be explained in its run.md: read it, and tell me if it is not.
   - The beeswarm plot:
     `![Holdout AUC per run](run-multi/SUMMARY/holdout_auc_beeswarm.png)`

   Leave the rest of the README alone.

5. For every model with a single group whose `results_summary.md` already
   has the statistics over the valid runs: compare its holdout AUC mean, sd,
   min, median and max with the table row. They must agree to within 0.0001
   (rounding). Tell me if they don't.

6. Give me a short summary: the table, the head-to-head table as printed by
   `pairwise_win_prob.py`, every warning and what you did about it, and
   anything off in the plots.

Don't commit or push anything - I review and commit the results myself.
