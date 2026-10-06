#!/usr/bin/env python3
"""Plot the holdout AUC of all run groups in run-multi/, coloured by model.

Reads each group's holdout_auc.tsv (written by /xgb-multi), the model from each
run's driver-summary.json, the per-experiment scores from its
holdout_scores.tsv and the harness timing from its timing/ folder. Groups with
the same model are pooled (all runs are effort max). Runs with valid = "no" are
left out. Caveat runs are drawn like any other run, unless one of their caveats
is of a kind to be marked (see CAVEAT_MARKED): those are drawn hollow/dashed.

run-multi/SUMMARY/holdout_auc_beeswarm.png - one row per model, one dot per run
  (modelled on Fig. 1 of arXiv:2609.33812): a filled dot per run and a hollow
  dot per run with a marked caveat, a grey bar over the full range, the mean with its
  95% confidence interval (t) and the 10th/90th percentiles (nearest run) when
  the row has >= 5 runs.

Two views of the holdout AUC path of each run, i.e. the holdout AUC of the
kept model over the time of the run (x: minutes since the run's clock started;
y: holdout AUC of each kept commit, from the end of its harness run until the
next keep). The median at time t is over all of a model's runs, from when every
run has its baseline; a run that has ended counts with its final value, so the
median ends at the median of the runs' last kept models. Models with fewer than
MIN_N_PATH runs get no median.

run-multi/SUMMARY/holdout_auc_path_panels.png - small multiples, one panel per
  model on shared axes: its runs as thin lines, their median path in bold, the
  other models' runs faint grey behind.

run-multi/SUMMARY/holdout_auc_path_median.png - one panel: all runs as thin
  faded lines, the median path per model in bold.

Usage:
    tools/plot_holdout_auc.py
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from scipy import stats

# categorical slots in fixed order (reference palette, light mode)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
# colour follows the model in every plot: add new models here with the next free slot;
# models not listed get the remaining slots in sorted order (and a warning)
MODEL_SLOT = {"gpt-6-astra": 0, "gpt-6-sol": 1, "gpt-6-luna": 2}
# caveats by kind (see caveat_kinds): a run is drawn hollow/dashed unless all its caveats are in
# CAVEAT_PLAIN. Each kind is decided once, when it first turns up: summary_table.py warns about a
# kind that is in neither set. Never move a kind from one set to the other.
CAVEAT_MARKED = set()
CAVEAT_PLAIN = {"keep_rule_tie"}
SURFACE, INK, INK2, GRID, RANGE = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#d9d8d3"
OTHER_RUNS = "#bebdb7"  # the other models' runs behind each panel of the panels path plot
MIN_N_STATS = 5  # interval and percentiles only from this many runs up
MIN_N_PATH = 5  # median paths only for models with at least this many runs
XLIM = None  # fixed holdout AUC range of the strip plot, e.g. (0.68, 0.70); None: the runs' range
RUN_MULTI = Path(__file__).resolve().parent.parent / "run-multi"
OUT_DIR = RUN_MULTI / "SUMMARY"


def caveat_kinds(flags, summary):
    """The caveats of a run: the flags of its holdout_auc.tsv row, with keep_rule split in two.

    run_checks.py flags keep_rule itself only for a kept commit with a lower Eval AUC
    (protocol_flags of driver-summary.json). A keep_rule that is in holdout_auc.tsv only
    was added in the review, for a tie kept without being simpler or faster: keep_rule_tie.
    """
    kinds = [k.strip() for k in flags.split(",") if k.strip()]
    if "keep_rule" not in summary.get("protocol_flags", "").split():
        kinds = ["keep_rule_tie" if k == "keep_rule" else k for k in kinds]
    return kinds


def load_group(gdir):
    """Runs of one group as dicts: run, dir, model, holdout, valid, marked (its caveats not in CAVEAT_PLAIN)."""
    runs = []
    with open(gdir / "holdout_auc.tsv") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["valid"] not in ("yes", "caveat") or not r["holdout_auc"]:
                continue
            summary = json.loads((gdir / r["run"] / "driver-summary.json").read_text())
            kinds = caveat_kinds(r.get("flags") or "", summary) if r["valid"] == "caveat" else []
            runs.append({"run": r["run"], "dir": gdir / r["run"], "model": summary["model"],
                         "holdout": float(r["holdout_auc"]), "valid": r["valid"],
                         "marked": [k for k in kinds if k not in CAVEAT_PLAIN]})
    return runs


def marked_label(runs):
    """Legend label of the runs drawn hollow/dashed, None if there are none."""
    kinds = sorted({k for r in runs for k in r["marked"]})
    return f"run with caveat ({', '.join(kinds)})" if kinds else None


def keep_path(run_dir):
    """((minutes, holdout AUC) of each kept commit, the minutes at which the run ended).

    Minutes are counted from the start of the run's clock; a kept commit counts from
    the end of its harness run.
    """
    clock = json.loads((run_dir / "timing" / "clock.json").read_text())
    end = {}  # of the first completed harness run of each commit
    with open(run_dir / "timing" / "runs.tsv") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["status"] == "ok":
                end.setdefault(r["commit"], (float(r["end"]) - clock["start"]) / 60)
    path = []
    with open(run_dir / "holdout_scores.tsv") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            # a kept commit whose holdout scoring failed has N/A or CRASH instead of an AUC
            if r["status"] == "keep" and r["holdout_auc"] not in ("", "N/A", "CRASH"):
                if r["commit"] not in end:
                    sys.exit(f"{run_dir.name}: the kept commit {r['commit']} has no completed run in timing/runs.tsv")
                path.append((end[r["commit"]], float(r["holdout_auc"])))
    return path, (clock["stop"] - clock["start"]) / 60


def model_colours(models):
    """{model: colour}: the fixed MODEL_SLOT colour, else the next free slot (with a warning)."""
    models = sorted(models)
    colour = {m: SERIES[MODEL_SLOT[m]] for m in models if m in MODEL_SLOT}
    free = [c for i, c in enumerate(SERIES) if i not in MODEL_SLOT.values()]
    for m in (m for m in models if m not in MODEL_SLOT):
        if not free:
            sys.exit(f"too many models; the palette has {len(SERIES)} colours")
        colour[m] = free.pop(0)
        print(f"warning: {m} has no fixed colour; add it to MODEL_SLOT", file=sys.stderr)
    return colour


def style(ax, title):
    ax.set_facecolor(SURFACE)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)
    ax.set_title(title, color=INK, fontsize=11, loc="left", pad=16)


def save(fig, name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / name
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=SURFACE)
    print(out)


def swarm_offsets(xs, ax, y, diameter_pt):
    """Vertical offsets (data units) so that dots at xs on row y don't overlap (a simple beeswarm).

    Dots are placed left to right; each takes the first free slot of 0, -1, -2, ... dot
    diameters below the row's centre line (never above: the mean and its interval sit there),
    so a dot only leaves the centre line when it would touch another.
    """
    fig = ax.figure
    d = diameter_pt * fig.dpi / 72  # pixels
    px = ax.transData.transform(np.column_stack([xs, np.full(len(xs), y)]))[:, 0]
    dy_per_px = 1 / (ax.transData.transform((0, 1))[1] - ax.transData.transform((0, 0))[1])
    placed, offsets = [], np.zeros(len(xs))
    for i in np.argsort(px):
        for k in range(len(xs)):
            slot = -k * d  # 0, -d, -2d, ... (pixels grow upward in display coordinates)
            if all((px[i] - pj) ** 2 + (slot - sj) ** 2 >= d ** 2 for pj, sj in placed):
                break
        placed.append((px[i], slot))
        offsets[i] = slot * dy_per_px
    return offsets


def strip_plot(runs, colour):
    # rows top to bottom by mean holdout AUC, best on top
    rows = sorted(colour, key=lambda m: -st.mean(r["holdout"] for r in runs if r["model"] == m))
    h = 1.6 + 0.75 * len(rows)  # height per row leaves room for the beeswarm below each row
    fig, ax = plt.subplots(figsize=(9, h), facecolor=SURFACE)
    fig.subplots_adjust(bottom=0.85 / h, right=0.97)
    lo, hi = min(r["holdout"] for r in runs), max(r["holdout"] for r in runs)
    if XLIM:
        if lo < XLIM[0] or hi > XLIM[1]:
            print(f"warning: runs span {lo:.4f}-{hi:.4f}, outside XLIM; some are cut off", file=sys.stderr)
        ax.set_xlim(*XLIM)
    else:
        pad = (hi - lo) * 0.05 or 0.001
        ax.set_xlim(lo - pad, hi + pad)

    ax.set_ylim(-0.6, len(rows) - 0.4)  # before the swarm: it needs the final data -> pixel scale
    for i, m in enumerate(rows):
        y = len(rows) - 1 - i
        rr = [r for r in runs if r["model"] == m]
        x = np.array([r["holdout"] for r in rr])
        n = len(x)
        ax.plot([x.min(), x.max()], [y, y], color=RANGE, lw=6, solid_capstyle="round", zorder=1)
        # dots that would overlap are spread vertically (beeswarm); x stays exact
        # diameter: marker size 46 pt^2 -> ~6.8 pt, plus the 1.4 pt edge, plus 0.6 pt of air
        dys = swarm_offsets(x, ax, y, np.sqrt(46) + 1.4 + 0.6)
        for r, dy in zip(rr, dys):
            filled = not r["marked"]
            ax.scatter(r["holdout"], y + dy, s=46, zorder=3, linewidths=1.4,
                       facecolors=colour[m] if filled else SURFACE, edgecolors=colour[m])
        mean = x.mean()
        if n >= MIN_N_STATS:
            half = stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n)
            ax.errorbar(mean, y + 0.22, xerr=half, fmt="none", ecolor=INK, elinewidth=1.6, capsize=3, zorder=4)
            # "nearest": each percentile is an actual run (with n = 10, the 2nd and 9th)
            p10, p90 = np.percentile(x, [10, 90], method="nearest")
            # above the dots: each mark is on a run, and a dot stacked below would hide half of it
            ax.scatter([p10, p90], [y, y], marker="|", s=260, color=INK, linewidths=1.6, zorder=4)
        ax.scatter(mean, y + 0.22, s=34, color=INK, zorder=5)

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(list(reversed(rows)), color=INK)
    ax.set_xlabel("holdout AUC", color=INK2)
    ax.grid(axis="x", color=GRID, lw=0.8)
    style(ax, "Holdout AUC per run")
    caveat = marked_label(runs)
    legend = [
        Line2D([], [], marker="o", ls="", color=INK2, markersize=7, label="run"),
        *([Line2D([], [], marker="o", ls="", markerfacecolor=SURFACE, markeredgecolor=INK2, markersize=7,
                  label=caveat)] if caveat else []),
        # what describes the runs first (range, percentiles), then the mean
        Line2D([], [], color=RANGE, lw=6, solid_capstyle="butt", label="full range"),  # butt: stays clear of its label
        Line2D([], [], marker="|", ls="", color=INK2, markersize=9, markeredgewidth=1.6, label="10th and 90th percentile"),
        Line2D([], [], marker="o", color=INK, markersize=5, lw=1.6, label=f"mean, 95% CI of the mean (n >= {MIN_N_STATS})"),
    ]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, -0.02),
               ncol=len(legend), frameon=False, fontsize=8, labelcolor=INK2, handletextpad=0.4, columnspacing=1.2)
    save(fig, "holdout_auc_beeswarm.png")


def median_path(runs, model):
    """(minutes, median holdout AUC of the kept models) over all the model's runs, as steps.

    It starts when every run has its baseline. A run that has ended keeps its final
    value (the model it ended with), so the path ends at the median of the runs' last
    kept models.
    """
    paths, ends = zip(*(keep_path(r["dir"]) for r in runs if r["model"] == model))
    paths = [p for p in paths if p]
    start = max(p[0][0] for p in paths)
    times = sorted({t for p in paths for t, _ in p if t >= start})
    median = [np.median([[auc for t, auc in p if t <= ti][-1] for p in paths]) for ti in times]
    return times + [max(ends)], median + [median[-1]]


def draw_runs(ax, runs, colour_of, lw, alpha):
    for r in runs:
        path, end = keep_path(r["dir"])
        if not path:
            continue
        t, auc = zip(*path)
        ax.step(list(t) + [end], list(auc) + [auc[-1]], where="post", color=colour_of(r),
                lw=lw, alpha=alpha, ls=(0, (4, 2)) if r["marked"] else "-", zorder=2)


def draw_median(ax, runs, m, colour, lw=2.4):
    if sum(r["model"] == m for r in runs) < MIN_N_PATH:
        return
    t, median = median_path(runs, m)
    ax.step(t, median, where="post", color=colour, lw=lw, zorder=4, solid_capstyle="round")


def path_panels(runs, colour):
    models = sorted(colour, key=lambda m: -st.mean(r["holdout"] for r in runs if r["model"] == m))
    fig, axes = plt.subplots(1, len(models), figsize=(4 * len(models), 4.4), sharex=True, sharey=True,
                             facecolor=SURFACE)
    axes = np.atleast_1d(axes)
    fig.subplots_adjust(bottom=0.24, top=0.82, left=0.07, right=0.98, wspace=0.08)
    for ax, m in zip(axes, models):
        draw_runs(ax, [r for r in runs if r["model"] != m], lambda r: OTHER_RUNS, lw=0.6, alpha=0.8)
        draw_runs(ax, [r for r in runs if r["model"] == m], lambda r: colour[m], lw=0.9, alpha=0.8)
        draw_median(ax, runs, m, colour[m])
        ax.grid(color=GRID, lw=0.8)
        ax.set_xlim(left=0)
        style(ax, "")
        ax.set_title(m, color=INK, fontsize=10, loc="left", pad=6)
        ax.set_xlabel("minutes since the clock started", color=INK2)
    axes[0].set_ylabel("holdout AUC", color=INK2)
    fig.suptitle("Holdout AUC path per run, one panel per model", x=0.07, ha="left", color=INK, fontsize=11)
    caveat = marked_label(runs)
    legend = [
        Line2D([], [], color=INK2, lw=0.9, label="run"),
        *([Line2D([], [], color=INK2, lw=0.9, ls=(0, (4, 2)), label=caveat)] if caveat else []),
        Line2D([], [], color=INK2, lw=2.4, label="median of the runs"),
        Line2D([], [], color=OTHER_RUNS, alpha=0.8, lw=1.2, label="other models' runs"),
    ]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.0),
               ncol=len(legend), frameon=False, fontsize=8, labelcolor=INK2, handletextpad=0.4, columnspacing=1.2)
    save(fig, "holdout_auc_path_panels.png")


def path_median(runs, colour):
    models = sorted(colour, key=lambda m: -st.mean(r["holdout"] for r in runs if r["model"] == m))
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
    fig.subplots_adjust(bottom=0.2, right=0.97)
    draw_runs(ax, runs, lambda r: colour[r["model"]], lw=0.75, alpha=0.4)
    for m in models:
        draw_median(ax, runs, m, colour[m], lw=2.6)
    ax.set_xlabel("minutes since the clock started", color=INK2)
    ax.set_ylabel("holdout AUC", color=INK2)
    ax.grid(color=GRID, lw=0.8)
    ax.set_xlim(left=0)
    style(ax, "Holdout AUC path per run, median in bold")
    caveat = marked_label(runs)
    legend = [Line2D([], [], color=colour[m], lw=2.6, label=m) for m in models] + [
        Line2D([], [], color=INK2, lw=0.75, alpha=0.6, label="run"),
        *([Line2D([], [], color=INK2, lw=0.75, alpha=0.6, ls=(0, (4, 2)), label=caveat)] if caveat else []),
        Line2D([], [], color=INK2, lw=2.6, label="median of the runs"),
    ]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, -0.02),
               ncol=len(legend), frameon=False, fontsize=8, labelcolor=INK2, handletextpad=0.4, columnspacing=1.2)
    save(fig, "holdout_auc_path_median.png")


def main():
    groups = sorted(d for d in RUN_MULTI.iterdir() if (d / "holdout_auc.tsv").is_file())
    runs = [r for g in groups for r in load_group(g)]
    if not runs:
        sys.exit(f"no valid runs in {RUN_MULTI}")

    for k in sorted({k for r in runs for k in r["marked"]} - CAVEAT_MARKED):
        print(f"warning: caveat {k} has no plotting rule (drawn as marked); add it to CAVEAT_MARKED or CAVEAT_PLAIN",
              file=sys.stderr)
    colour = model_colours({r["model"] for r in runs})
    strip_plot(runs, colour)
    path_panels(runs, colour)
    path_median(runs, colour)


if __name__ == "__main__":
    main()
