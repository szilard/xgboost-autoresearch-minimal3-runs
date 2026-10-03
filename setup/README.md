## Setup

- `Dockerfile` - the `agents2` image: Ubuntu 26.04, codex installed as the
  unprivileged user `ubuntu` (nothing AI as root), the Python packages, and a
  copy of [xgboost-autoresearch-minimal2](https://github.com/szilard/xgboost-autoresearch-minimal2)
  with fresh git history (no upstream `.git`, no `results/`) and the data
  already prepared.

Runs are driven by the Claude Code skill `/xgb-multi` (see [Running
experiments](#running-experiments-xgb-multi)), after the one-time build and
login below.

### Build

From the repo root:

```bash
docker build -t agents2 setup/
```

### Log in (once)

The ChatGPT login goes into the docker volume `codex-auth`:

```bash
docker run -it --rm -e CODEX_HOME=/home/ubuntu/.codex-auth \
  -v codex-auth:/home/ubuntu/.codex-auth agents2 bash -c \
  'codex login --device-auth && find "$CODEX_HOME" -mindepth 1 ! -name auth.json -exec rm -rf {} +'
```

`CODEX_HOME` is needed because `codex login` first deletes
`~/.codex/auth.json`, which in the image is a symlink into the volume. The
`find` leaves only `auth.json` in the volume. Check it with:

```bash
docker run --rm -v codex-auth:/v agents2 ls -la /v
```

### Running experiments: `/xgb-multi`

The project skill `.claude/skills/xgb-multi/SKILL.md` runs the experiment N
times in a row, e.g. to see how much the result varies between runs
(N = 1 is a single run). Start `claude` in this repo (inside tmux: a run
takes ~2.5-3 hours) and type:

```
/xgb-multi <run-group> <model> <n-runs> [effort]
```

e.g. `/xgb-multi luna-max gpt-5.6-luna 10` (effort defaults to `max`). It
only runs when invoked like this, never on its own. For each run, one after
another:

- the script `.claude/skills/xgb-multi/run_one.sh` drives the run, so every
  run gets exactly the same messages under the same rules:
  - starts a new `agents2` container named `<run-group>-<i>`, with the
    `codex-auth` volume mounted
  - runs codex with `codex exec` / `codex exec resume`, one command per
    turn: the README prompt, then "go" until the harness clock starts, and
    "keep going" if the agent stops early; the harness enforces the 2-hour
    budget
  - checks from the codex session log that the model and effort took effect
  - runs the harness report, the ground truth scoring and the plot, and
    `leak_check.py`, which searches the session log for the content of the
    holdout data and the human-only scripts, not just their names
  - copies the results into `run-multi/<run-group>/<run-group>-<i>/` (the
    session log slimmed by `slim_session.py`: gzipped, encrypted reasoning
    dropped, account ids redacted) and deletes the container, to save disk
- Claude reviews each finished run while the next one runs: validity checks
  (eval/holdout gap, train.py-only diff, no access to the holdout data),
  `run.md`, and the group's `results_summary.md` (with mean/sd/min/median/max
  over the valid runs) and `holdout_auc.tsv` (one line per run, for plots)
- nothing is committed - review and commit the results yourself

The earlier single-run skill `/xgb-run` (Claude driving each turn live,
container left up) is retired; it is preserved at tags `v0.1`/`v0.2`, and
its run is in [archive/single-run](../archive/single-run/).

`.claude/settings.json` pre-approves the docker commands and file writes a
run needs, so it can run unattended (also in auto mode), and denies
`docker volume rm` to protect the login.

### The container

This is what the driver starts:

```bash
docker run -dit --name <run> --memory=24g --memory-swap=24g -v codex-auth:/home/ubuntu/.codex-auth agents2
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
