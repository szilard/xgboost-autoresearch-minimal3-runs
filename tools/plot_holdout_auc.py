#!/usr/bin/env python3
"""Plot the holdout AUC of all run groups in run-multi/, coloured by model.

Reads each group's holdout_auc.tsv (written by /xgb-multi), the model from each
run's driver-summary.json and the per-experiment scores from its
holdout_scores.tsv. Groups with the same model are pooled (all runs are effort
max). Runs with valid = "no" are left out; caveat runs are drawn hollow/dashed.

run-multi/SUMMARY/holdout_auc_beeswarm.png - one row per model, one dot per run
  (modelled on Fig. 1 of arXiv:2609.33812): a filled dot per valid run and a
  hollow dot per caveat run, a grey bar over the full range, the mean with its
  90% interval (t) and the 10th/90th percentiles (nearest run) when the row has
  >= 5 runs.

Three views of the holdout AUC path of each run, i.e. the holdout AUC of the
kept model after each experiment (x: experiment number n as in the runs'
auc_history.png, the baseline is n = 1; y: holdout AUC of each kept commit, held
until the next keep). The median and percentiles at experiment n are over all
of a model's runs, a run that has ended counting with its final value; they
stop when fewer than MIN_N_PATH runs are still going.

run-multi/SUMMARY/holdout_auc_path_panels.png - small multiples, one panel per
  model on shared axes: its runs as thin lines, their median path in bold, the
  other models' runs faint grey behind.

run-multi/SUMMARY/holdout_auc_path_bands.png - one panel: per model the median
  path and a shaded 10th-90th percentile band, no individual runs.

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
from matplotlib.patches import Patch
from scipy import stats

# categorical slots in fixed order (reference palette, light mode)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
# colour follows the model in every plot: add new models here with the next free slot;
# models not listed get the remaining slots in sorted order (and a warning)
MODEL_SLOT = {"gpt-6-astra": 0, "gpt-6-sol": 1, "gpt-6-luna": 2}
SURFACE, INK, INK2, GRID, RANGE = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#d9d8d3"
OTHER_RUNS = "#bebdb7"  # the other models' runs behind each panel of the panels path plot
MIN_N_STATS = 5  # interval and percentiles only from this many runs up
MIN_N_PATH = 5  # median / percentile paths only where at least this many runs are still going
XLIM = None  # fixed holdout AUC range of the strip plot, e.g. (0.68, 0.70); None: the runs' range
RUN_MULTI = Path(__file__).resolve().parent.parent / "run-multi"
OUT_DIR = RUN_MULTI / "SUMMARY"


def load_group(gdir):
    """Runs of one group as dicts: run, dir, model, holdout, valid."""
    runs = []
    with open(gdir / "holdout_auc.tsv") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["valid"] not in ("yes", "caveat") or not r["holdout_auc"]:
                continue
            summary = json.loads((gdir / r["run"] / "driver-summary.json").read_text())
            runs.append({"run": r["run"], "dir": gdir / r["run"], "model": summary["model"],
                         "holdout": float(r["holdout_auc"]), "valid": r["valid"]})
    return runs


def keep_path(run_dir):
    """(n, holdout AUC) of each kept commit, n counted over all rows of holdout_scores.tsv."""
    path = []
    with open(run_dir / "holdout_scores.tsv") as f:
        for n, r in enumerate(csv.DictReader(f, delimiter="\t"), 1):
            if r["status"] == "keep" and r["holdout_auc"] not in ("", "N/A"):
                path.append((n, float(r["holdout_auc"])))
    return path


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
            filled = r["valid"] == "yes"
            ax.scatter(r["holdout"], y + dy, s=46, zorder=3, linewidths=1.4,
                       facecolors=colour[m] if filled else SURFACE, edgecolors=colour[m])
        mean = x.mean()
        if n >= MIN_N_STATS:
            half = stats.t.ppf(0.95, n - 1) * x.std(ddof=1) / np.sqrt(n)
            ax.errorbar(mean, y + 0.22, xerr=half, fmt="none", ecolor=INK, elinewidth=1.6, capsize=3, zorder=4)
            # "nearest": each percentile is an actual run (with n = 10, the 2nd and 9th)
            p10, p90 = np.percentile(x, [10, 90], method="nearest")
            ax.scatter([p10, p90], [y, y], marker="|", s=260, color=INK, linewidths=1.6, zorder=2)
        ax.scatter(mean, y + 0.22, s=34, color=INK, zorder=5)

    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(list(reversed(rows)), color=INK)
    ax.set_xlabel("holdout AUC", color=INK2)
    ax.grid(axis="x", color=GRID, lw=0.8)
    style(ax, "Holdout AUC per run")
    legend = [
        Line2D([], [], marker="o", ls="", color=INK2, markersize=7, label="run"),
        Line2D([], [], marker="o", ls="", markerfacecolor=SURFACE, markeredgecolor=INK2, markersize=7,
               label="run with caveat"),
        Line2D([], [], marker="o", color=INK, markersize=5, lw=1.6, label=f"mean, 90% interval (n >= {MIN_N_STATS})"),
        Line2D([], [], marker="|", ls="", color=INK2, markersize=9, markeredgewidth=1.6, label="10th and 90th percentile"),
    ]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, -0.02),
               ncol=len(legend), frameon=False, fontsize=8, labelcolor=INK2, handletextpad=0.4, columnspacing=1.2)
    save(fig, "holdout_auc_beeswarm.png")


def step_series(run_dir):
    """Holdout AUC of the kept model at every experiment n = 1..n_last (held until the next keep)."""
    path = keep_path(run_dir)
    with open(run_dir / "holdout_scores.tsv") as f:
        n_last = sum(1 for _ in f) - 1
    values = np.full(n_last, np.nan)
    for n, auc in path:
        values[n - 1:] = auc
    return values


def path_quantiles(runs, model, qs):
    """(n, {q: values}) of the per-n quantiles over all the model's runs.

    A run that has ended keeps its final value (the model it ended with), so a run
    finishing early doesn't make the quantiles jump; the paths stop where fewer than
    MIN_N_PATH runs are still going.
    """
    series = [step_series(r["dir"]) for r in runs if r["model"] == model]
    n_max = max(len(v) for v in series)
    grid = np.empty((len(series), n_max))
    for i, v in enumerate(series):
        grid[i, :len(v)] = v
        grid[i, len(v):] = v[-1]
    going = np.array([sum(len(v) > j for v in series) for j in range(n_max)])
    keep = going >= MIN_N_PATH
    return np.arange(1, n_max + 1)[keep], {q: np.quantile(grid[:, keep], q, axis=0) for q in qs}


def draw_runs(ax, runs, colour_of, lw, alpha, dots=True):
    for r in runs:
        path = keep_path(r["dir"])
        if not path:
            continue
        n, auc = zip(*path)
        with open(r["dir"] / "holdout_scores.tsv") as f:
            n_last = sum(1 for _ in f) - 1
        c = colour_of(r)
        ax.step(list(n) + [n_last], list(auc) + [auc[-1]], where="post", color=c,
                lw=lw, alpha=alpha, ls="-" if r["valid"] == "yes" else (0, (4, 2)), zorder=2)
        if dots:
            ax.scatter(n_last, auc[-1], s=12, zorder=3, color=c, alpha=min(1, alpha + 0.2))


def draw_median(ax, runs, m, colour, lw=2.4):
    n, q = path_quantiles(runs, m, [0.5])
    ax.step(n, q[0.5], where="post", color=colour, lw=lw, zorder=4, solid_capstyle="round")


def path_panels(runs, colour):
    models = sorted(colour, key=lambda m: -st.mean(r["holdout"] for r in runs if r["model"] == m))
    fig, axes = plt.subplots(1, len(models), figsize=(4 * len(models), 4.4), sharex=True, sharey=True,
                             facecolor=SURFACE)
    axes = np.atleast_1d(axes)
    fig.subplots_adjust(bottom=0.24, top=0.82, left=0.07, right=0.98, wspace=0.08)
    for ax, m in zip(axes, models):
        draw_runs(ax, [r for r in runs if r["model"] != m], lambda r: OTHER_RUNS, lw=0.6, alpha=0.8, dots=False)
        draw_runs(ax, [r for r in runs if r["model"] == m], lambda r: colour[m], lw=0.9, alpha=0.8)
        draw_median(ax, runs, m, colour[m])
        ax.grid(color=GRID, lw=0.8)
        ax.set_xlim(left=0)
        style(ax, "")
        ax.set_title(m, color=INK, fontsize=10, loc="left", pad=6)
        ax.set_xlabel("experiment n (baseline = 1)", color=INK2)
    axes[0].set_ylabel("holdout AUC", color=INK2)
    fig.suptitle("Holdout AUC path per run, one panel per model", x=0.07, ha="left", color=INK, fontsize=11)
    legend = [
        Line2D([], [], color=INK2, lw=0.9, label="run"),
        Line2D([], [], color=INK2, lw=0.9, ls=(0, (4, 2)), label="run with caveat"),
        Line2D([], [], color=INK2, lw=2.4, label="median of the runs"),
        Line2D([], [], color=OTHER_RUNS, alpha=0.8, lw=1.2, label="other models' runs"),
    ]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.0),
               ncol=len(legend), frameon=False, fontsize=8, labelcolor=INK2, handletextpad=0.4, columnspacing=1.2)
    save(fig, "holdout_auc_path_panels.png")


def path_bands(runs, colour):
    models = sorted(colour, key=lambda m: -st.mean(r["holdout"] for r in runs if r["model"] == m))
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
    fig.subplots_adjust(bottom=0.2, right=0.97)
    for m in models:
        n, q = path_quantiles(runs, m, [0.1, 0.5, 0.9])
        ax.fill_between(n, q[0.1], q[0.9], step="post", color=colour[m], alpha=0.18, lw=0, zorder=2)
        ax.step(n, q[0.5], where="post", color=colour[m], lw=2.2, zorder=4)
    ax.set_xlabel("experiment n (baseline = 1)", color=INK2)
    ax.set_ylabel("holdout AUC", color=INK2)
    ax.grid(color=GRID, lw=0.8)
    ax.set_xlim(left=0)
    style(ax, "Holdout AUC path: median and 10th-90th percentile of the runs")
    legend = [Line2D([], [], color=colour[m], lw=2.2, label=m) for m in models] + [
        Patch(facecolor=INK2, alpha=0.18, label="10th-90th percentile"),
        Line2D([], [], color=INK2, lw=2.2, label="median of the runs"),
    ]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, -0.02),
               ncol=len(legend), frameon=False, fontsize=8, labelcolor=INK2, handletextpad=0.4, columnspacing=1.2)
    save(fig, "holdout_auc_path_bands.png")


def path_median(runs, colour):
    models = sorted(colour, key=lambda m: -st.mean(r["holdout"] for r in runs if r["model"] == m))
    fig, ax = plt.subplots(figsize=(9, 5.2), facecolor=SURFACE)
    fig.subplots_adjust(bottom=0.2, right=0.97)
    draw_runs(ax, runs, lambda r: colour[r["model"]], lw=0.75, alpha=0.4)
    for m in models:
        draw_median(ax, runs, m, colour[m], lw=2.6)
    ax.set_xlabel("experiment n (baseline = 1)", color=INK2)
    ax.set_ylabel("holdout AUC", color=INK2)
    ax.grid(color=GRID, lw=0.8)
    ax.set_xlim(left=0)
    style(ax, "Holdout AUC path per run, median in bold")
    legend = [Line2D([], [], color=colour[m], lw=2.6, label=m) for m in models] + [
        Line2D([], [], color=INK2, lw=0.75, alpha=0.6, label="run"),
        Line2D([], [], color=INK2, lw=0.75, alpha=0.6, ls=(0, (4, 2)), label="run with caveat"),
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

    colour = model_colours({r["model"] for r in runs})
    strip_plot(runs, colour)
    path_panels(runs, colour)
    path_bands(runs, colour)
    path_median(runs, colour)


if __name__ == "__main__":
    main()
