## Setup

- `Dockerfile` - the `agents3` image: Ubuntu 26.04, codex installed as the
  unprivileged user `ubuntu` (nothing AI as root), the Python packages, and a
  copy of [xgboost-autoresearch-minimal3](https://github.com/szilard/xgboost-autoresearch-minimal3)
  at a pinned commit (`MINIMAL3_REF` in the Dockerfile), with fresh git
  history (no upstream `.git`, no `results/`) and the data already prepared.
  The human-only files - the `human/` scripts and `data/holdout.csv` - are
  not in that copy: they sit in `/opt/human-only`, readable by root only.

Runs are driven by the Claude Code skill `/xgb-multi` (see [Running
experiments](#running-experiments-xgb-multi)), after the one-time build and
login below.

### Build

From the repo root:

```bash
docker build -t agents3 setup/
```

To move to another upstream commit, change `MINIMAL3_REF` in the Dockerfile
(or pass `--build-arg MINIMAL3_REF=<full hash>`) and rebuild; all runs that
are to be compared should come from the same image.

### Log in (once)

The ChatGPT login goes into the docker volume `codex-auth`:

```bash
docker run -it --rm -e CODEX_HOME=/home/ubuntu/.codex-auth \
  -v codex-auth:/home/ubuntu/.codex-auth agents3 bash -c \
  'codex login --device-auth && find "$CODEX_HOME" -mindepth 1 ! -name auth.json -exec rm -rf {} +'
```

`CODEX_HOME` is needed because `codex login` first deletes
`~/.codex/auth.json`, which in the image is a symlink into the volume. The
`find` leaves only `auth.json` in the volume. Check it with:

```bash
docker run --rm -v codex-auth:/v agents3 ls -la /v
```

### Running experiments: `/xgb-multi`

The project skill `.claude/skills/xgb-multi/SKILL.md` runs the experiment N
times in a row, e.g. to see how much the result varies between runs
(N = 1 is a single run). Start `claude` in this repo (inside tmux: a run
takes ~1.5 hours) and type:

```
/xgb-multi <run-group> <model> <n-runs> [effort]
```

e.g. `/xgb-multi luna6_n20 gpt-6-luna 20` (effort defaults to `max`). It
only runs when invoked like this, never on its own. For each run, one after
another:

- the script `.claude/skills/xgb-multi/run_one.sh` drives the run, so every
  run gets exactly the same messages under the same rules:
  - starts a new `agents3` container named `<run-group>-<i>`, with the
    `codex-auth` volume mounted, and checks that the human-only files are
    out of the agent's reach
  - runs codex with `codex exec` / `codex exec resume`, one command per
    turn: the README prompt, then "go" until the harness clock starts, and
    "keep going" if the agent stops early; the harness enforces the 1-hour
    budget
  - checks from the codex session log that the model and effort took effect
  - once the agent has exited: runs the harness report and `run_checks.py`
    (rule checks on `results.tsv`, the harness timing and git: only
    `train.py` changed, the keep rule, resets, results only from harness
    runs inside the clock, no early stop), copies the human-only files back
    into the repo, runs the holdout scoring and the plot, and
    `leak_check.py`, which lists the agent's downloads and broad reads and
    searches the session log for the content of the holdout and eval data
    and the human-only scripts, not just their names
  - copies the results into `run-multi/<run-group>/<run-group>-<i>/` (the
    session log slimmed by `slim_session.py`: gzipped, encrypted reasoning
    dropped, account ids redacted) and deletes the container, to save disk
- Claude reviews each finished run while the next one runs: the integrity
  checks (a failed one excludes the run), the protocol checks (the run stays
  valid, with a caveat), the eval/holdout gap, `run.md`, and the group's
  `results_summary.md` (with mean/sd/min/median/max over the valid runs) and
  `holdout_auc.tsv` (one line per run, for plots)
- nothing is committed - review and commit the results yourself

`.claude/settings.json` pre-approves the docker commands and file writes a
run needs, so it can run unattended (also in auto mode), and denies
`docker volume rm` to protect the login.

### Summary over all groups: `/xgb-summary`

The project skill `.claude/skills/xgb-summary/SKILL.md` brings the summary
up to date, e.g. after a group has finished. Type `/xgb-summary` (no
arguments) in `claude` in this repo. It

- runs `tools/summary_table.py`, which checks the group files (each
  `holdout_auc.tsv` against the runs' `driver-summary.json`, the same codex
  version, effort and upstream commit everywhere, test groups left in
  `run-multi/`) and prints the results table per model
- runs `tools/plot_holdout_auc.py` and `tools/pairwise_win_prob.py`, which
  write the plots to `run-multi/SUMMARY/`, and looks at each plot
- rewrites the results block of the main README (table, caveats and
  exclusions, the beeswarm plot)
- commits nothing

The three scripts can also be run by hand, from the repo root and without
arguments; they need matplotlib, numpy and scipy on the host.

### The container

This is what the driver starts:

```bash
docker run -dit --name <run> --memory=24g --memory-swap=24g -v codex-auth:/home/ubuntu/.codex-auth agents3
```

The memory cap (24 GB, no swap, on the 30 GB host) keeps a runaway experiment
from starving the host: the kernel kills the largest process in the container
instead, which the harness records as a crash or eval timeout. The agent sees
the host's memory in `free`, not the cap. The driver logs the peak memory and
the number of processes killed at the cap in driver.log and driver-summary.json.

Only `auth.json` is shared, through the symlink; sessions, history and config
stay in the container. Codex rewrites `auth.json` in place when it refreshes
the token, so the refreshed token lands in the volume.

Don't run `codex logout` in a container. To remove the login, run
`docker volume rm codex-auth`.
