#!/usr/bin/env python3
"""Holdout AUC table per model for the README, with checks of the group files.

Reads each group's holdout_auc.tsv in run-multi/ and each run's
driver-summary.json, like plot_holdout_auc.py: groups with the same model are
pooled, runs with valid = "no" are left out of the statistics, caveat runs are
included. Changes nothing.

Prints
- the groups: model, runs, how many are valid, with a caveat, excluded;
- the settings of the valid runs (codex version, effort, upstream commit, time
  budget, memory cap), which should be the same for all runs that are compared;
- the table, as markdown: one row per model, the best mean on top, AUCs rounded
  to 4 decimals, sd the sample standard deviation (n - 1);
- NOTE lines for the caveats, the exclusions and valid runs with integrity
  flags (to be explained in the run's run.md);
- WARNING lines for anything that doesn't fit: a group that looks like a test,
  a row of holdout_auc.tsv that disagrees with the run's driver-summary.json, a
  valid run without a holdout AUC or of a failed driver, a run folder that is
  not in holdout_auc.tsv, mixed settings.

Usage:
    tools/summary_table.py
"""
import csv
import json
import statistics as st
import sys
from collections import Counter, defaultdict

from plot_holdout_auc import RUN_MULTI

SETTINGS = ["codex_version", "effort", "upstream", "time_budget_s", "memory_limit_bytes"]


def number(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def main():
    groups = sorted(d for d in RUN_MULTI.iterdir() if (d / "holdout_auc.tsv").is_file())
    if not groups:
        sys.exit(f"no groups in {RUN_MULTI}")

    notes, warnings = [], []
    models = defaultdict(lambda: {"groups": [], "holdout": [], "caveat": 0, "excluded": 0})
    settings = {k: Counter() for k in SETTINGS}

    print("groups:")
    for g in groups:
        with open(g / "holdout_auc.tsv") as f:
            rows = list(csv.DictReader(f, delimiter="\t"))
        summaries = {}
        for r in rows:
            sfile = g / r["run"] / "driver-summary.json"
            if sfile.is_file():
                summaries[r["run"]] = json.loads(sfile.read_text())
            else:
                warnings.append(f"{r['run']}: no driver-summary.json")
        group_models = Counter(s["model"] for s in summaries.values())
        if len(group_models) > 1:
            warnings.append(f"group {g.name} has runs of more than one model: {dict(group_models)}")
        model = group_models.most_common(1)[0][0] if group_models else "?"
        m = models[model]
        m["groups"].append(g.name)

        n = Counter()
        for r in rows:
            s = summaries.get(r["run"], {})
            valid, flags = r["valid"], r.get("flags") or ""
            n[valid] += 1
            # the row was written by hand from driver-summary.json: it must agree with it
            for col, key in (("best_commit", "best_commit"), ("eval_auc", "best_eval_auc"),
                             ("holdout_auc", "best_holdout_auc")):
                if s and r[col] and r[col] != s.get(key):
                    warnings.append(f"{r['run']}: {col} is {r[col]} in holdout_auc.tsv, {s.get(key)} in driver-summary.json")
            e, h, gap = number(r["eval_auc"]), number(r["holdout_auc"]), number(r["gap"])
            if None not in (e, h, gap) and abs(gap - (h - e)) > 0.00005:
                warnings.append(f"{r['run']}: gap is {r['gap']}, holdout - eval is {h - e:+.4f}")

            if valid == "no":
                m["excluded"] += 1
                notes.append(f"{r['run']} excluded: {flags or 'no reason given'}")
            elif valid in ("yes", "caveat"):
                if h is None:
                    warnings.append(f"{r['run']}: valid = {valid} without a holdout AUC (left out of the table and the plots)")
                    continue
                m["holdout"].append(h)
                for k in SETTINGS:
                    settings[k][str(s.get(k, "?"))] += 1
                if s.get("status", "ok") != "ok":
                    warnings.append(f"{r['run']}: valid = {valid}, but the driver's status is {s['status']} ({s.get('reason')})")
                if s.get("integrity_flags", "none") not in ("none", ""):
                    notes.append(f"{r['run']} is valid with integrity flags: {s['integrity_flags']}")
                if valid == "caveat":
                    m["caveat"] += 1
                    notes.append(f"{r['run']} caveat: {flags or 'no flags given'}")
                elif flags:
                    warnings.append(f"{r['run']}: valid = yes with flags: {flags}")
            else:
                warnings.append(f"{r['run']}: valid is '{valid}', not yes, caveat or no")

        in_tsv = {r["run"] for r in rows}
        for d in sorted(p.name for p in g.iterdir() if p.is_dir() and p.name not in in_tsv):
            warnings.append(f"{g.name}/{d} is not in holdout_auc.tsv (a run still going or not yet reviewed?)")
        if "test" in g.name.lower():
            warnings.append(f"group {g.name} looks like a test group: its runs are pooled with all other {model} runs")
        print(f"  {g.name}: {model}, {len(rows)} runs: {n['yes'] + n['caveat']} valid "
              f"({n['caveat']} with caveat), {n['no']} excluded")

    print("\nsettings of the valid runs:")
    for k in SETTINGS:
        print(f"  {k}: " + ", ".join(f"{v} ({c} run{'s' * (c != 1)})" for v, c in settings[k].most_common()))
        if len(settings[k]) > 1:
            warnings.append(f"mixed {k} among the valid runs: {', '.join(settings[k])}")

    print("\n| model | groups | valid runs | excluded | holdout AUC mean | sd | min | median | max |")
    print("|---|---|---|---|---|---|---|---|---|")
    # best mean on top, models without a valid run last
    for model in sorted(models, key=lambda k: -st.mean(models[k]["holdout"]) if models[k]["holdout"] else 1):
        m = models[model]
        x = m["holdout"]
        links = ", ".join(f"[{g}](run-multi/{g}/results_summary.md)" for g in m["groups"])
        n_valid = f"{len(x)} ({m['caveat']} with caveat)" if m["caveat"] else str(len(x))
        stats = [st.mean(x), st.stdev(x) if len(x) > 1 else None, min(x), st.median(x), max(x)] if x else [None] * 5
        print(f"| {model} | {links} | {n_valid} | {m['excluded']} | "
              + " | ".join("-" if v is None else f"{v:.4f}" for v in stats) + " |")

    print()
    for line in notes:
        print(f"NOTE: {line}")
    for line in warnings:
        print(f"WARNING: {line}")
    print(f"{len(warnings)} warning(s)")


if __name__ == "__main__":
    main()
