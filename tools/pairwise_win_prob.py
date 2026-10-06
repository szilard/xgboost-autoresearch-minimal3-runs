#!/usr/bin/env python3
"""Pairwise win probability of the holdout AUC between models, with a plot.

For each pair of models A, B: draw one run of A and one run of B at random;
P(A > B) is the share of all (run of A, run of B) pairs in which A's holdout AUC
is higher, counting ties (equal at the 4 decimals stored) as half
(the Mann-Whitney / "probability of superiority" estimate, AUC of A vs B).
The table also gives P(A < B) and P(tie) separately. The 95% interval is a
percentile bootstrap: the runs of each model are resampled with replacement
(N_BOOT times, fixed seed) and P recomputed.

Reads each group's holdout_auc.tsv in run-multi/ and the model from each run's
driver-summary.json; groups with the same model are pooled, as in
plot_holdout_auc.py. Runs with valid = "no" are left out; caveat runs are
included unless --no-caveat is given.

run-multi/SUMMARY/holdout_auc_pairwise.png - one row per pair of models, the
  better one by mean holdout AUC labelled on the right, the other on the left:
  a dot at P(the right-hand model wins) in percent, so it leans toward the usual winner,
  its 95% bootstrap interval and a reference line at 0.5 (coin flip).
  Not written with --no-caveat or with fewer than two models.

Usage:
    tools/pairwise_win_prob.py [--no-caveat]
"""
import csv
import itertools
import json
import sys
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnnotationBbox, DrawingArea, HPacker, TextArea
from matplotlib.patches import Circle
from matplotlib.ticker import PercentFormatter

from plot_holdout_auc import GRID, INK, INK2, RANGE, RUN_MULTI, SURFACE, model_colours, save, style

N_BOOT = 10000
SEED = 1


def load_runs(valid):
    """{model: [holdout AUC, ...]} over all groups, keeping runs whose valid is in `valid`."""
    runs = defaultdict(list)
    for tsv in sorted(RUN_MULTI.glob("*/holdout_auc.tsv")):
        with open(tsv) as f:
            for r in csv.DictReader(f, delimiter="\t"):
                if r["valid"] not in valid or not r["holdout_auc"]:
                    continue
                summary = json.loads((tsv.parent / r["run"] / "driver-summary.json").read_text())
                runs[summary["model"]].append(float(r["holdout_auc"]))
    return {m: np.array(v) for m, v in runs.items()}


def win_matrix(a, b):
    """1 where a run of a beats a run of b, 0.5 for a tie, 0 otherwise (rows: a, columns: b)."""
    return (a[:, None] > b[None, :]) + 0.5 * (a[:, None] == b[None, :])


def compare(a, b, rng):
    """P(a > b), P(a < b), P(tie), and the 95% bootstrap interval of P(a > b) + P(tie) / 2."""
    gt, eq = a[:, None] > b[None, :], a[:, None] == b[None, :]
    win = win_matrix(a, b)
    ia = rng.integers(0, len(a), (N_BOOT, len(a)))
    ib = rng.integers(0, len(b), (N_BOOT, len(b)))
    boot = win[ia[:, :, None], ib[:, None, :]].mean(axis=(1, 2))
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return gt.mean(), (~gt & ~eq).mean(), eq.mean(), lo, hi


def percent(p):
    """p as a whole percent; 0% and 100% only when it is exactly that."""
    s = f"{p:.0%}"
    if s == "0%" and p > 0:
        return "<1%"
    if s == "100%" and p < 1:
        return ">99%"
    return s


def plot(rows, runs):
    """rows: (better model, worse model, P, lo, hi), drawn top to bottom in the given order.

    The better model (by mean) is labelled on the right of its row, the other on the
    left; x is P(the right-hand model wins), so each dot leans toward the model
    that usually wins.
    """
    h = 1.6 + 0.5 * len(rows)
    fig, ax = plt.subplots(figsize=(9, h), facecolor=SURFACE)
    fig.subplots_adjust(bottom=0.9 / h, left=0.22, right=0.78)
    ax.axvline(0.5, color=INK2, lw=1, ls=(0, (3, 3)), zorder=1)
    ax.text(0.5, len(rows) - 0.45, "coin flip", color=INK2, fontsize=8, ha="center", va="bottom")
    for i, (m1, m2, p, lo, hi) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.plot([lo, hi], [y, y], color=RANGE, lw=6, solid_capstyle="round", zorder=2)
        ax.scatter(p, y, s=46, color=INK, zorder=3)
        ax.text(p, y + 0.2, percent(p), color=INK, fontsize=9, ha="center", va="bottom")

    # model labels: a dot in the model's colour (as in the other plots) and the name in ink,
    # model 2 outside the left edge, model 1 (the better one) outside the right edge
    colour = model_colours(runs)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([])

    def label(m, dot_first):
        da = DrawingArea(10, 10)
        da.add_artist(Circle((5, 5), 4, color=colour[m]))
        t = TextArea(m, textprops=dict(color=INK, fontsize=10))
        return HPacker(children=[da, t] if dot_first else [t, da], pad=0, sep=4, align="center")

    for i, (m1, m2, *_) in enumerate(rows):
        y = len(rows) - 1 - i
        for m, x, dx, align, dot_first in ((m2, 0, -8, (1, 0.5), False), (m1, 1, 8, (0, 0.5), True)):
            ax.add_artist(AnnotationBbox(label(m, dot_first), (x, y), xycoords=("axes fraction", "data"),
                                         xybox=(dx, 0), boxcoords="offset points", box_alignment=align,
                                         frameon=False, annotation_clip=False))
    ax.set_ylim(-0.6, len(rows) - 0.1)
    ax.set_xlim(-0.02, 1.02)  # room for the round caps of intervals reaching 0 or 1
    ax.set_xticks(np.linspace(0, 1, 5))
    ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    ax.set_xlabel("P(right-hand model wins)", color=INK2)
    ax.grid(axis="x", color=GRID, lw=0.8)
    style(ax, "Head to head: one run of each model")
    legend = [
        Line2D([], [], marker="o", ls="", color=INK, markersize=7, label="estimate (all pairs of runs)"),
        Line2D([], [], color=RANGE, lw=6, label="95% bootstrap interval (runs resampled per model)"),
    ]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, -0.02),
               ncol=len(legend), frameon=False, fontsize=8, labelcolor=INK2, handlelength=2.4, handletextpad=0.8, columnspacing=2.0)
    save(fig, "holdout_auc_pairwise.png")


def main():
    no_caveat = "--no-caveat" in sys.argv[1:]
    valid = ("yes",) if no_caveat else ("yes", "caveat")
    runs = load_runs(valid)
    models = sorted(runs, key=lambda m: -runs[m].mean())
    rng = np.random.default_rng(SEED)
    print(f"runs included: valid in {valid}")
    for m in models:
        print(f"  {m:14s} n={len(runs[m]):2d}  mean holdout AUC {runs[m].mean():.4f}")
    print()
    print(f"{'model 1':14s} {'model 2':14s} {'P(1 better)':>12s} {'P(2 better)':>12s} {'P(tie)':>8s}"
          f" {'ties half':>10s} {'95% interval':>14s}")
    rows = []
    # models are sorted by mean, so model 1 is always the better one on average
    for m1, m2 in itertools.combinations(models, 2):
        win, lose, tie, lo, hi = compare(runs[m1], runs[m2], rng)
        p = win + tie / 2
        rows.append((m1, m2, p, lo, hi))
        print(f"{m1:14s} {m2:14s} {win:12.3f} {lose:12.3f} {tie:8.3f} {p:10.3f}   {lo:.3f}-{hi:.3f}")
    if not rows:
        print("fewer than two models: no pairs, no plot")
    elif not no_caveat:
        plot(sorted(rows, key=lambda r: -r[2]), runs)  # highest win probability on top


if __name__ == "__main__":
    main()
