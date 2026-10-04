# Mechanical checks of a finished run: did the agent follow the rules of
# program.md that can be read off results.tsv, the harness timing and git?
# Runs inside the run's container, after codex has exited and the clock is
# stopped, and before the driver copies human/ and holdout.csv back.
#
# Integrity (a confirmed one excludes the run):
#   non_train_change      a commit touches a file other than train.py (and outside output/)
#   tracked_file_modified uncommitted change to a tracked file other than train.py
#   extra_data_files      data/ holds more than train.csv and eval.csv
#   artifact_outside_clock  an artifact not saved by a harness run inside the clock
#   result_without_run    a kept row with no completed harness run
#   train_py_review       a train.py version reads files or the network (lines listed)
# Protocol (the run stays valid, with a caveat):
#   keep_rule             a kept row has a lower Eval AUC than the kept row before it
#   missed_reset          a commit logged as discard is in the branch history
#   branch_mismatch       a kept commit is not in the branch history, or in another order
#   head_not_last_keep    HEAD is not the last kept commit
#   early_stop            the clock was stopped with 2 minutes or more remaining
#   output_committed      a commit includes files of output/ (they stay uncommitted)
#   stray_files           untracked files outside output/
# Also listed, without a flag, because program.md allows them: kept ties, crash
# or unlogged commits in the branch history (a crash fixed by a commit on top),
# discard rows without a completed run (a timeout logged as discard), and kept
# runs that started inside the budget and ended after it.
#
# Usage: python3 run_checks.py [--repo DIR] [--output DIR] [--budget SECONDS] [--no-git]
# (--no-git: only the checks on results.tsv and timing/, e.g. on an archived run:
#  run_checks.py --no-git --output results/test2 --budget 3600)
import argparse
import csv
import json
import re
import subprocess
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--repo", default="/home/ubuntu/xgboost-autoresearch-minimal3")
ap.add_argument("--output", help="default: REPO/output")
ap.add_argument("--budget", type=float, help="default: time_budget_s of harness.py")
ap.add_argument("--no-git", action="store_true")
args = ap.parse_args()
repo = Path(args.repo)
output = Path(args.output) if args.output else repo / "output"
MIN_REMAINING_S = 120  # program.md: do not stop the clock while 2 minutes or more remain

integrity, protocol = [], []


def git(*a):
    return subprocess.run(["git", *a], cwd=repo, text=True, capture_output=True).stdout.strip()


def same(a, b):
    """Two commit hashes, possibly abbreviated to different lengths."""
    return bool(a) and bool(b) and (a.startswith(b) or b.startswith(a))


def flag(group, name, detail):
    if name not in group:
        group.append(name)
    print(f"  FLAG {name}: {detail}")


def tsv(path):
    if not path.exists():
        print(f"  {path.name} missing")
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))


def auc(row):
    try:
        return float(row.get("Eval_AUC") or "")
    except ValueError:
        return None


# ---------- results.tsv ----------

print("== results.tsv")
rows = [r for r in tsv(output / "results.tsv") if (r.get("commit") or "").strip()]
for r in rows:
    r["commit"], r["status"] = r["commit"].strip(), (r.get("status") or "").strip()
counts = {s: sum(r["status"] == s for r in rows) for s in ("keep", "discard", "crash")}
other = [r for r in rows if r["status"] not in counts]
print(f"  {len(rows)} rows: " + ", ".join(f"{n} {s}" for s, n in counts.items())
      + (f", {len(other)} with another status ({', '.join(sorted({r['status'] for r in other}))})" if other else ""))

keeps = [r for r in rows if r["status"] == "keep"]
if any(auc(r) is None for r in keeps):
    flag(protocol, "keep_rule", "a kept row has no numeric Eval_AUC")
keeps_auc = [r for r in keeps if auc(r) is not None]
ties = []
for prev, r in zip(keeps_auc, keeps_auc[1:]):
    if auc(r) < auc(prev):
        flag(protocol, "keep_rule", f"{r['commit']} kept at {auc(r):.4f}, below {prev['commit']} at {auc(prev):.4f}")
    elif auc(r) == auc(prev):
        ties.append(f"{r['commit']} ({auc(r):.4f}, after {prev['commit']})")
print(f"  kept ties (allowed only for simpler or faster code; look at the description): {', '.join(ties) or 'none'}")
if keeps_auc:
    print(f"  kept Eval AUC: {auc(keeps_auc[0]):.4f} -> {auc(keeps_auc[-1]):.4f}, "
          f"max {max(map(auc, keeps_auc)):.4f}")

# ---------- clock and harness runs ----------

print("\n== clock and harness runs")
budget = args.budget
if budget is None:
    first = None if args.no_git else git("rev-list", "--max-parents=0", "HEAD").splitlines()[0]
    src = git("show", f"{first}:harness.py") if first else (repo / "harness.py").read_text()
    budget = float(re.search(r"^time_budget_s = (\d+)", src, re.M).group(1))
clock_file = output / "timing" / "clock.json"
clock = json.loads(clock_file.read_text()) if clock_file.exists() else {}
runs = tsv(output / "timing" / "runs.tsv")
ok_runs = [r for r in runs if r["status"] == "ok"]
print(f"  {len(runs)} harness runs: " + ", ".join(
    f"{sum(r['status'] == s for r in runs)} {s}" for s in ("ok", "crash", "timeout-training", "timeout-eval")))

if "start" not in clock:
    print("  clock not started")
elif "stop" not in clock:
    print("  clock not stopped")
else:
    elapsed = clock["stop"] - clock["start"]
    print(f"  budget {budget:.0f} s, clock stopped after {elapsed:.0f} s ({budget - elapsed:+.0f} s remaining)")
    if budget - elapsed >= MIN_REMAINING_S:
        flag(protocol, "early_stop", f"clock stopped with {budget - elapsed:.0f} s remaining")
    for r in keeps:
        ends = [float(x["end"]) for x in ok_runs if same(x["commit"], r["commit"])]
        if ends and min(ends) > clock["start"] + budget:
            print(f"  {r['commit']} is kept and its run ended {min(ends) - clock['start'] - budget:.0f} s after the budget "
                  "(started inside it)")

for r in rows:
    if r["status"] in ("keep", "discard") and not any(same(x["commit"], r["commit"]) for x in ok_runs):
        if r["status"] == "keep":
            flag(integrity, "result_without_run", f"{r['commit']} is kept but has no completed harness run")
        else:
            print(f"  {r['commit']} is logged as discard but has no completed harness run (a crash or timeout?)")
unlogged = sorted({x["commit"] for x in runs if not any(same(x["commit"], r["commit"]) for r in rows)})
print(f"  harness runs of commits not in results.tsv: {', '.join(unlogged) or 'none'}")

# ---------- git ----------

if not args.no_git:
    print("\n== git")
    first = git("rev-list", "--max-parents=0", "HEAD").splitlines()[0]
    head = git("rev-parse", "HEAD")
    branch = git("rev-list", "--reverse", "HEAD").splitlines()
    print(f"  branch {git('branch', '--show-current') or '<detached>'}: {len(branch)} commits, "
          f"first {first[:7]}, HEAD {head[:7]}")

    def status_of(c):
        return next((r["status"] for r in rows if same(c, r["commit"])), None)

    # the branch holds the kept commits, in the order of results.tsv, and no discarded ones
    for c in branch:
        s = status_of(c)
        if s == "discard":
            flag(protocol, "missed_reset", f"{c[:7]} is logged as discard but is in the branch history")
        elif s != "keep":
            print(f"  {c[:7]} is in the branch history, " + (f"logged as {s}" if s else "not in results.tsv")
                  + " (fine if the next commit fixes it)")
    for r in keeps:
        if not any(same(c, r["commit"]) for c in branch):
            flag(protocol, "branch_mismatch", f"{r['commit']} is logged as keep but is not in the branch history")
    on_branch = [c for c in branch if status_of(c) == "keep"]
    in_results = [r["commit"] for r in keeps if any(same(c, r["commit"]) for c in branch)]
    if len(on_branch) != len(in_results) or not all(same(c, k) for c, k in zip(on_branch, in_results)):
        flag(protocol, "branch_mismatch", "the kept commits are in a different order in results.tsv and on the branch")
    if keeps and not same(head, keeps[-1]["commit"]):
        flag(protocol, "head_not_last_keep", f"HEAD is {head[:7]}, the last kept row is {keeps[-1]['commit']}")

    # every commit the agent made, also the discarded ones (still in the reflog)
    commits = [c for c in git("rev-list", "--reverse", "--all", "--reflog").splitlines() if c != first]
    for c in commits:
        files = git("show", "--name-only", "--format=", c).splitlines()
        if any(f.startswith("output/") for f in files):
            flag(protocol, "output_committed", f"{c[:7]} includes {' '.join(f for f in files if f.startswith('output/'))}")
        files = [f for f in files if not f.startswith("output/")]
        if files not in ([], ["train.py"]):
            flag(integrity, "non_train_change", f"{c[:7]} touches {' '.join(files)}")
    print(f"  {len(commits)} commits by the agent (branch and reflog) checked for files other than train.py")

    for line in git("status", "--porcelain").splitlines():
        st, path = line.split(maxsplit=1)
        if st == "??":
            if not path.startswith("output/"):
                flag(protocol, "stray_files", f"untracked {path}")
        elif path == "train.py":
            print("  train.py has uncommitted changes")
        else:
            flag(integrity, "tracked_file_modified", f"{st} {path}")

    extra = sorted(p.name for p in (repo / "data").iterdir() if p.name not in ("train.csv", "eval.csv"))
    if extra:
        flag(integrity, "extra_data_files", f"data/ also holds {' '.join(extra)}")

    # artifacts are saved by harness runs inside the clock, one per completed run
    arts = sorted((repo / "artifacts").glob("*")) if (repo / "artifacts").is_dir() else []
    for p in arts:
        ran = any(same(p.stem, x["commit"]) for x in runs)
        late = "stop" in clock and p.stat().st_mtime > clock["stop"] + 5
        early = "start" in clock and p.stat().st_mtime < clock["start"]
        if p.suffix != ".pkl" or not ran or late or early:
            flag(integrity, "artifact_outside_clock", f"{p.name}: "
                 + ("no harness run of that commit" if not ran else
                    "saved after the clock stopped" if late else "saved before the clock started"))
    print(f"  {len(arts)} artifacts, {sum(p.stat().st_size for p in arts) / 1e6:.0f} MB")

    # train.py may read data/train.csv only: list the lines, not in the starter,
    # that could read another file or the network
    suspect = re.compile(r"read_csv|read_table|read_parquet|read_pickle|read_json|open\(|np\.load|loadtxt|genfromtxt"
                         r"|urlopen|urlretrieve|requests|http|\.csv|holdout|data_dir|harness|subprocess|os\.system"
                         r"|glob|listdir|scandir")
    starter = {l.strip() for l in git("show", f"{first}:train.py").splitlines()}
    seen = {}
    for c in commits:
        for l in git("show", f"{c}:train.py").splitlines():
            l = l.strip()
            if suspect.search(l) and l not in starter and not l.startswith("#"):
                seen.setdefault(l, c[:7])
    for l, c in seen.items():
        flag(integrity, "train_py_review", f"{c}: {l[:200]}")
    print(f"  train.py of {len(commits)} commits scanned for reads of other files or the network")

print(f"\nINTEGRITY FLAGS: {' '.join(integrity) or 'none'}")
print(f"PROTOCOL FLAGS: {' '.join(protocol) or 'none'}")
