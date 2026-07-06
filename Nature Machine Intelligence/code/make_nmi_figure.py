#!/usr/bin/env python3
"""NMI journal cross-check SI figure, styled to match the main paper's TrendPlots.pdf."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({"font.size": 11, "font.family": "DejaVu Sans",
                     "axes.spines.top": False, "axes.spines.right": False,
                     "svg.fonttype": "none"})  # keep SVG text as editable <text>, not outlines

YEARS = ["2022", "2023", "2024", "2025"]
x = np.arange(len(YEARS))
total = np.array([90, 101, 109, 124])
main = np.array([1, 7, 7, 20])
sic = np.array([1, 3, 0, 3])            # surfaced only by SI/code
comb = main + sic
comb_pct = comb / total * 100
main_pct = main / total * 100
sic_pct = sic / total * 100
dep = np.array([0, 1, 0, 5])
base = np.array([0, 1, 4, 15])

GRAY_MAIN, GRAY_SI = "#6e6e6e", "#b8b8b8"
DEP_C, BASE_C = "#c0392b", "#fdae6b"


def draw_inset(ax, x0, x1, y0, header, rows, lh=0.085, fs=9):
    from matplotlib.patches import FancyBboxPatch
    pad = 0.02
    h = lh * (len(rows) + 1) + 2 * pad
    ax.add_patch(FancyBboxPatch((x0 - pad, y0 - h + lh - pad + 0.02), (x1 - x0) + 2 * pad, h,
                                boxstyle="round,pad=0.005", transform=ax.transAxes,
                                facecolor="white", edgecolor="#cccccc", lw=0.7, zorder=5))
    ax.text(x0, y0, header[0], transform=ax.transAxes, fontweight="bold", fontsize=fs, va="top", ha="left", zorder=6)
    ax.text(x1, y0, header[1], transform=ax.transAxes, fontweight="bold", fontsize=fs, va="top", ha="right", zorder=6)
    ax.plot([x0, x1], [y0 - 0.045, y0 - 0.045], transform=ax.transAxes, color="#999", lw=0.8, zorder=6)
    y = y0 - lh
    for name, cnt in rows:
        ax.text(x0, y, name, transform=ax.transAxes, fontsize=fs, va="top", ha="left", zorder=6)
        ax.text(x1, y, cnt, transform=ax.transAxes, fontsize=fs, va="top", ha="right", zorder=6)
        y -= lh


fig, (axA, axB) = plt.subplots(1, 2, figsize=(13, 4.3))

# ---------- Panel A: prevalence ----------
axA.bar(x, main_pct, color=GRAY_MAIN, label="Main text")
axA.bar(x, sic_pct, bottom=main_pct, color=GRAY_SI, label="Supplementary (PDF + code)")
for xi, p in zip(x, comb_pct):
    axA.text(xi, p + 0.5, f"{p:.1f}%", ha="center", fontsize=10, color="#333")
axA.set_ylabel("Articles with closed-source refs (%)")
axA.set_xlabel("Year"); axA.set_xticks(x); axA.set_xticklabels(YEARS)
axA.set_ylim(0, 22)
axA.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=9.5)
axA.text(-0.13, 1.06, "A", transform=axA.transAxes, fontsize=20, fontweight="bold")
draw_inset(axA, 0.30, 0.66, 0.93, ("Top Model Names", "Articles"),
           [("gpt-4", "22"), ("gpt-3", "22"), ("gpt-3.5", "13"), ("gpt-4o", "7")])

# ---------- Panel B: reproducibility risk ----------
axB.bar(x, dep, color=DEP_C, label="Deprecated model")
axB.bar(x, base, bottom=dep, color=BASE_C, label="Base-name only")
for xi, d, b in zip(x, dep, base):
    if d + b > 0:
        axB.text(xi, d + b + 0.3, f"{d + b}", ha="center", fontsize=10, color="#333")
axB.set_ylabel("Articles at reproducibility risk")
axB.set_xlabel("Year"); axB.set_xticks(x); axB.set_xticklabels(YEARS)
axB.set_ylim(0, 23)
axB.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=9.5)
axB.text(-0.13, 1.06, "B", transform=axB.transAxes, fontsize=20, fontweight="bold")
draw_inset(axB, 0.13, 0.66, 0.93, ("Top Deprecated Names", "Articles"),
           [("gpt-4-0314", "2"), ("dall-e-2", "1"), ("gpt-3.5-turbo-0301", "1"),
            ("gpt-3.5-turbo-instruct", "1"), ("gpt-4-1106-preview", "1")], fs=8.5)

fig.tight_layout()
fig.savefig("/home/aipexws3/Jessica/GhostAI/NMI/NMI_crosscheck.pdf", bbox_inches="tight")
fig.savefig("/home/aipexws3/Jessica/GhostAI/NMI/NMI_crosscheck.svg", bbox_inches="tight")
fig.savefig("/home/aipexws3/Jessica/GhostAI/NMI/NMI_crosscheck_preview.png", dpi=140, bbox_inches="tight")
print("saved NMI_crosscheck.pdf + .svg + preview")
