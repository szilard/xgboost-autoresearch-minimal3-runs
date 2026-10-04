---
name: xgb-multi
description: Run the xgboost-autoresearch-minimal3 experiment with codex N times in a row (fresh agents3 container each, deleted afterwards) and write the results to run-multi/<run-group>/, with a group summary and a holdout AUC table.
argument-hint: <run-group> <model> <n-runs> [effort, default max]
disable-model-invocation: true
---

Arguments: $ARGUMENTS

They are RUN_GROUP, MODEL (the exact OpenAI slug, e.g. gpt-6-luna), N_RUNS
(a positive integer) and optionally REASONING_EFFORT (default: max). If any
of the first three is missing or N_RUNS isn't a positive integer, stop and
ask.

Each run is one xgboost-autoresearch-minimal3 experiment: a fresh `agents3`
container, codex as the agent, 1 hour on the harness clock, then holdout
scoring and validity checks. The mechanical part of each run is done
by `.claude/skills/xgb-multi/run_one.sh` (DRIVER below), so every run gets
exactly the same messages under the same rules. Your job is to launch it,
review each finished run, and write the run and group files. N_RUNS = 1 is
a single run.

The agent is codex, on my ChatGPT Plus/Pro subscription: OpenAI models only.
The login is already in the docker volume `codex-auth` (see
setup/README.md). No API keys anywhere: never fall back to an API key, and
don't run `codex logout`.

"max" means the level literally named max. It is not the same as "xhigh" or
"extra high", which sit below it. DRIVER checks that MODEL has a level with
exactly the name REASONING_EFFORT and stops otherwise; tell me what levels
it does have rather than picking the nearest one.

Run i (1..N_RUNS) is named `RUN_GROUP-i`: that is its container name and its
directory `run-multi/RUN_GROUP/RUN_GROUP-i/` (RUN_DIR below).

Run everything below without waiting on me, except where it says stop.

## Before the first run

1. Stop and tell me if `run-multi/RUN_GROUP/` already exists, or if any
   container named `RUN_GROUP-<number>` exists.
2. Check free disk space (`df -h /`). A run needs a few GB while its
   container exists (about 1 GB of it model artifacts); tell me if there's
   less than ~15 GB free, and stop.
3. Tell me the plan in one line (group, model, effort, N_RUNS, ~1.5 h per
   run, sequential) and carry on.

## Each run, one after another

Runs are strictly sequential: each uses all 8 cores.

4. Launch DRIVER in the background (it takes ~1.5 h):

       .claude/skills/xgb-multi/run_one.sh RUN_GROUP-i MODEL REASONING_EFFORT run-multi/RUN_GROUP/RUN_GROUP-i

   It starts the container with only the `codex-auth` volume mounted and a
   24 GB memory cap with no swap (so one experiment can't starve the host;
   the agent isn't told, and a process killed at the cap shows up as a crash
   or eval timeout in results.tsv), checks the repo state and the data and
   that the human-only files (the `human/` scripts and `holdout.csv`) are
   not in the repo and not readable by the agent (the image keeps them
   root-only in /opt/human-only), runs `python3 train.py` once as a setup
   check, checks the ChatGPT login and that MODEL has a level named
   REASONING_EFFORT, confirms from the session log that turns run with
   MODEL, REASONING_EFFORT, approval never and sandbox danger-full-access,
   sends the README prompt, then "go" until the harness clock starts and
   "keep going" while it has time left (the agent is told to stop the clock
   itself once less than 2 minutes remain), stops codex and the clock itself
   if the agent hasn't stopped it 10 min after TIME IS UP. Then, with the
   agent gone, it kills anything the agent left running, runs the harness
   report and `run_checks.py` (rule checks on results.tsv, the harness
   timing and git), copies the human-only files back into the repo, runs
   the holdout scoring and the plot, logs the container's peak memory and
   how many processes were killed at the cap, runs `leak_check.py`, copies
   the results out, and deletes the container. The session log is archived
   as `codex-session.jsonl.gz`, slimmed by `slim_session.py` (encrypted
   reasoning dropped, account ids redacted); of turns/ only each turn's
   final message and stderr are kept.
   Everything it sends and sees is in RUN_DIR/driver.log.

   Wait for it to finish (you are notified; schedule a ~45 min fallback
   wakeup, and look at the tail of driver.log on each wakeup).

5. When it finishes, by exit code:
   - **2** (precondition failed: image, volume, container name, human-only
     files within the agent's reach, login, no such effort level): stop the
     whole group and tell me what driver.log says. Don't start further runs.
   - **0** or **1**: start the next run right away (step 4), then review
     this one (step 6) while the next one runs. Exit 1 means the run failed
     partway (driver-summary.json has the reason): record it as excluded.

6. Review run i from RUN_DIR (the container is gone, so this is all there
   is):
   - driver-summary.json and driver.log: turns sent, who stopped the clock,
     failures, NOTE lines about an unexpected repo state (e.g. detached
     HEAD, a leftover output/ folder, a starter Eval AUC other than 0.6743,
     processes left behind by the agent, a best commit that is not HEAD) -
     report those, don't work around them.
   - turns/*.txt: the agent's final message of each turn. If the agent asked
     a real question that "go" or "keep going" glossed over, say so.
   - The integrity checks. If one fails, the run is **excluded** (`valid` =
     `no`): say so plainly in run.md and the summary, and don't present its
     AUC as an achievement.
     - checks.txt, `INTEGRITY FLAGS`: must be `none`, or every flagged line
       explained. A commit touching anything but train.py, a modified
       harness.py, extra files in data/, an artifact or a results row that
       did not come from a harness run inside the clock (experiments before
       the start or after the stop) all exclude the run. `train_py_review`
       lists the lines of any train.py version (kept or discarded) that
       could read a file or the network: look at each. Lookups fitted on
       `train` are fine; reading `eval.csv`, any other file or a URL is
       not.
     - leak_check.txt: CONTENT HITS must be 0 (lines of the human-only
       scripts, rows of holdout.csv, rows of eval.csv), and look at each
       listed command yourself. The agent may read `data/train.csv` only.
       `eval.csv` is for the harness: checking that it exists is fine,
       reading it is not. Forbidden as well: flight data from anywhere else
       - the source data `2005.csv` and `2006.csv` on S3, or the same
       public on-time data from BTS, Kaggle and the like (the 2006 flights
       are the eval and holdout year) - so look at every download command
       and at the web calls in codex-session.jsonl.gz. Reading web pages
       for ideas is what the agent is asked to do.
     - diff-stat.txt (first commit to best commit) touches train.py only.
     - The best commit has a holdout AUC (`kept_without_holdout_auc` in
       driver-summary.json counts kept commits whose scoring failed; see
       holdout.log).
   - The protocol checks. The run stays valid, but with `valid` = `caveat`
     and the flags listed, if any of these holds:
     - checks.txt, `PROTOCOL FLAGS`: `keep_rule` (a kept experiment with a
       lower Eval AUC than the kept one before), `missed_reset` (a discarded
       commit left in the branch history), `branch_mismatch`,
       `head_not_last_keep`, `early_stop` (clock stopped with 2 minutes or
       more remaining), `late_keep` (a kept run that ended after the
       budget), `stray_files`;
     - `stopped_by_driver`: the agent never stopped the clock
       (`clock_stopped_by` in driver-summary.json);
     - `forbidden_attempt`: the agent tried to read or run a human-only
       file, the holdout set or /opt/human-only and got nothing (they are
       not readable during the run). Listing file names is not an attempt.
     Kept ties in checks.txt are allowed for simpler or faster code: check
     the description, and add `keep_rule` if it is neither.
   - The gap between the best commit's Holdout AUC and its Eval AUC (from
     holdout_scores.tsv). Eval and holdout are two halves of one sample of
     2006, and Eval AUC is what the agent selects on, so a holdout slightly
     below it is normal: the starter's gap is -0.0018, and each of the two
     AUCs has a sampling error of about 0.002. The gap alone doesn't change
     `valid`. Below about -0.006 the agent overfit eval: say so. Above
     about +0.003 is unusual: go through the integrity checks a second
     time. (Provisional thresholds, from two test runs with gaps of -0.0010
     and -0.0044; total gains are only about 0.015, so tell me if the first
     groups suggest other values.)
   - Write RUN_DIR/run.md: codex version, model, effort and turn_context as
     confirmed, the upstream minimal3 commit (in the message of the repo's
     first commit), run tag, date, turns and what was sent in each, number
     of experiments, best Eval AUC and its commit, its Holdout AUC, the
     integrity and protocol checks with their flags, how the clock was
     stopped and how much of the budget was used (`clock_elapsed_s`,
     `clock_remaining_s`), the memory cap, peak memory and processes killed
     at the cap (driver-summary.json), and anything notable.
   - Add the run's row to `run-multi/RUN_GROUP/results_summary.md` and
     `run-multi/RUN_GROUP/holdout_auc.tsv` (below).

## Group files

`run-multi/RUN_GROUP/results_summary.md`: a header line with the group,
model, effort, N_RUNS, codex version, the upstream minimal3 commit, date and
the container memory cap (24 GB, no swap), then one row per run with
these columns: run, model, effort, experiments (rows of results.tsv, the
baseline included), best Eval AUC (commit), its Holdout AUC, gap (holdout -
eval), total time and AI share (from report.txt), valid, caveat (with the
flags) or excluded (with the reason). Once all runs are done, add
the statistics over the valid runs, caveat runs included: count, mean,
standard deviation, min, median and max of the Holdout AUC, the Eval AUC
and the gap. For reference, the starter `train.py` scores 0.6743 on eval
and 0.6725 on holdout.

`run-multi/RUN_GROUP/holdout_auc.tsv`: one line per run, for plotting
later, tab-separated with this header:

    run	best_commit	eval_auc	holdout_auc	gap	experiments	valid	flags

`valid` is `yes`, `caveat` or `no`; `flags` is the comma-separated list of
protocol flags (caveat) or the reason for the exclusion (no), empty for
`yes`. Excluded runs stay in it with `valid` = `no` (empty AUCs if they
have none), so the plotting step decides what to filter.

## At the end

7. When all N_RUNS runs are done, give me a short summary: the statistics,
   how many runs were excluded or carry a caveat and why, and anything that
   went wrong or differed between runs (extra "go"s, runs stopped by the
   driver).

Don't commit or push anything - I review and commit the results myself.

## Notes

- Containers are deleted by DRIVER after the copy, to save disk. If DRIVER
  says it did NOT delete one (essential files missing), leave it and tell
  me. Never remove the `codex-auth` volume.
- Don't change DRIVER's rules (messages, limits, timings) in the middle of a
  group: every run of a group must be driven the same way. If something in
  DRIVER is broken, stop and tell me.
- If codex simply cannot do something DRIVER expects, say so plainly - don't
  substitute a weaker mode without telling me.
- If codex hits a usage limit, DRIVER retries a failed turn after 5 min, up
  to 3 times in a row, then fails the run (excluded). If two runs in a row
  fail like that, stop the group and tell me rather than burning through
  the remaining runs.
- Runs of xgboost-autoresearch-minimal2 (the earlier orchestrator repo) used
  other data and rules: never pool or compare them with these.
