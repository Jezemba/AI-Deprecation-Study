#!/usr/bin/env python3
"""
Supervisor-facing charts for the COMPLETE NMI analysis (main text + SI/appendix
+ supplementary code), specific closed-source model identifiers only.
Saves individual PNGs and a combined dashboard into this directory.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

OUT = os.path.dirname(os.path.abspath(__file__))
plt.rcParams.update({"font.size": 11, "axes.titlesize": 12, "axes.titleweight": "bold",
                     "figure.dpi": 130, "savefig.dpi": 160, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.axisbelow": True})

YEARS = [2022, 2023, 2024, 2025]
nmi_total   = [90, 101, 109, 124]           # extracted papers/yr (424 total)
# combined specific-model papers/yr (main + SI + code), and main-text-only
comb_cnt    = [2, 10, 7, 23]
main_cnt    = [1, 7, 7, 20]
comb_pct    = [c/t*100 for c, t in zip(comb_cnt, nmi_total)]   # 2.2,9.9,6.4,18.5
main_pct    = [c/t*100 for c, t in zip(main_cnt, nmi_total)]
conf_pct    = [0.1, 2.9, 12.4, 20.1]        # conferences, paper Table 1

NMI_C, MAIN_C, CONF_C, DEP_C, SI_C, CODE_C = "#2b8cbe", "#9ecae1", "#bdbdbd", "#d7301f", "#fd8d3c", "#74c476"


def takeaway(ax, text, color="#222"):
    ax.text(0.5, -0.30, text, transform=ax.transAxes, ha="center", va="top",
            fontsize=10, style="italic", color=color, wrap=True)


def chart_trend(ax):
    ax.plot(YEARS, comb_pct, "-o", color=NMI_C, lw=2.5, ms=8, label="NMI combined (text+SI+code)")
    ax.plot(YEARS, main_pct, "-o", color=MAIN_C, lw=1.8, ms=6, label="NMI main text only")
    ax.plot(YEARS, conf_pct, "--s", color="#555", lw=2, ms=7, label="AAAI/NeurIPS/ICLR/ICML")
    for x, y in zip(YEARS, comb_pct):
        ax.annotate(f"{y:.1f}%", (x, y), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=NMI_C)
    ax.set_title("1. Adoption trend (full pipeline)")
    ax.set_ylabel("% of papers w/ specific model")
    ax.set_xticks(YEARS); ax.set_ylim(0, 24); ax.legend(loc="upper left", fontsize=8.5)
    takeaway(ax, "Combined run reaches 18.5% in 2025, tracking the conferences; SI+code lift every year.")


def chart_sources(ax):
    # waterfall-ish: main 35, +SI 6, +code 1 = 42
    labels = ["Main\ntext", "+ SI /\nappendix", "+ Code", "Combined"]
    base   = [0, 35, 41, 0]
    height = [35, 6, 1, 42]
    colors = [MAIN_C, SI_C, CODE_C, NMI_C]
    ax.bar(labels, height, bottom=base, color=colors)
    for i, (b, h) in enumerate(zip(base, height)):
        ax.text(i, b + h + 0.7, f"+{h}" if 0 < i < 3 else str(h), ha="center", fontweight="bold")
    ax.set_title("2. What each source contributes")
    ax.set_ylabel("papers with a specific model"); ax.set_ylim(0, 48)
    takeaway(ax, "The appendix (SI) adds 6 papers the main text missed; code adds 1 → 35 to 42 (+20%).")


def chart_scale(ax):
    labels = ["Matched\npapers", "Deprecated\npapers", "Future-shutdown\npapers"]
    nmi = [42, 6, 0.4]      # 0 -> 0.4 so it's visible on log
    conf = [4817, 640, 536]
    x = np.arange(len(labels)); w = 0.38
    b1 = ax.bar(x - w/2, nmi, w, color=NMI_C, label="NMI (combined)")
    b2 = ax.bar(x + w/2, conf, w, color=CONF_C, label="Conferences")
    ax.set_yscale("log"); ax.set_ylim(0.3, 1e4)
    ax.set_title("3. Absolute scale still tiny")
    ax.set_ylabel("count (log)"); ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9); ax.legend(fontsize=9)
    for b, v in zip(b1, [42, 6, 0]):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()*1.15, str(v), ha="center", fontsize=9, fontweight="bold", color=NMI_C)
    for b, v in zip(b2, conf):
        ax.text(b.get_x()+b.get_width()/2, b.get_height()*1.15, f"{v:,}", ha="center", fontsize=8, color="#666")
    takeaway(ax, "Even with SI+code, 6 deprecated papers vs 640 — still ~100x smaller than the conferences.", DEP_C)


def chart_repro(ax):
    cats = ["Deprecated\nmodel", "Base-name only\n(no checkpoint)", "Versioned\ncheckpoint"]
    vals = [6, 20, 8]
    pct = [v/42*100 for v in vals]
    bars = ax.bar(cats, vals, color=[DEP_C, "#fdae6b", NMI_C], width=0.6)
    for b, v, p in zip(bars, vals, pct):
        ax.text(b.get_x()+b.get_width()/2, v+0.4, f"{v}\n({p:.0f}%)", ha="center", fontsize=9, fontweight="bold")
    ax.set_title("4. Reproducibility risk among the 42")
    ax.set_ylabel("papers"); ax.set_ylim(0, 24)
    takeaway(ax, "6 already-deprecated; 48% name only a base model w/o a checkpoint — the paper's pattern, at small n.")


def save(fn, fig):
    p = os.path.join(OUT, fn); fig.savefig(p, bbox_inches="tight"); plt.close(fig); print("saved", p)


for fn_func, fn in [(chart_trend, "1_adoption_trend.png"), (chart_sources, "2_source_contribution.png"),
                    (chart_scale, "3_absolute_scale.png"), (chart_repro, "4_repro_risk.png")]:
    fig, ax = plt.subplots(figsize=(7, 5)); fn_func(ax); save(fn, fig)

fig, axs = plt.subplots(2, 2, figsize=(15, 12))
chart_trend(axs[0, 0]); chart_sources(axs[0, 1]); chart_scale(axs[1, 0]); chart_repro(axs[1, 1])
fig.suptitle("Nature Machine Intelligence — complete pipeline (main text + SI/appendix + supplementary code)\n"
             "42 of 424 papers (9.9%) reference a specific closed-source model; trend tracks the conferences, absolute scale stays small",
             fontsize=14, fontweight="bold", y=0.99)
fig.subplots_adjust(hspace=0.55, wspace=0.25, top=0.91)
save("0_NMI_dashboard.png", fig)
print("\nCombined: main 35 + SI 6 + code 1 = 42 papers; deprecation 4 (text) -> 6 (combined).")
