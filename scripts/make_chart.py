import json
import os

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

from chart_style import (
    ACCENT, BASELINE, GRID, INK, INK_MUTED, INK_SECONDARY, LEFT_IN, MUTED_MARK,
    QUIET_MARK, SURFACE, WIDTH_IN, add_header, chart_figure, format_ms,
    format_speedup, rounded_hbars, save_chart,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARTS = os.path.join(ROOT, "charts")

with open(os.path.join(ROOT, "benchmark", "results.json")) as f:
    results = json.load(f)

with open(os.path.join(ROOT, "benchmark", "write_path_results.json")) as f:
    write_path = json.load(f)

SHORT_TITLES = {
    1: "Average halt per station",
    2: "Station time-window lookup",
    3: "Longest halt per train",
    4: "Rajdhani/Duronto stations",
    5: "Train lookup by origin",
    6: "Deep pagination",
    7: "Dashboard aggregate",
}
Q3_FOOTNOTE = "Q3's before time is a single run because each run takes about 6 minutes. All other times are medians of 5 runs."


def query_label(r):
    return f"Q{r['n']}  {SHORT_TITLES[r['n']]}"


# ---------------------------------------------------------------- Chart 1
# Before vs after per query: a dumbbell on a log time scale
fig, ax = chart_figure(
    len(results),
    "Every query got faster after its fix",
    "End-to-end query time before and after each fix, on a log scale",
    footnote=Q3_FOOTNOTE,
)
positions = list(range(len(results) - 1, -1, -1))
ax.set_xscale("log")
ax.set_xlim(1, 1000000)
ax.set_ylim(-0.6, len(results) - 0.4)
ax.set_yticks(positions, [query_label(r) for r in results])
ax.set_xticks([1, 10, 100, 1000, 10000, 100000])
ax.minorticks_off()
ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: format_ms(v)))
ax.xaxis.tick_top()
ax.tick_params(axis="x", length=0, labelsize=9.5, pad=4)
ax.grid(axis="x", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
ax.spines["left"].set_visible(False)

for y, r in zip(positions, results):
    ax.plot([r["after_ms"], r["before_ms"]], [y, y], color=QUIET_MARK, linewidth=2, zorder=2)
    ax.scatter(r["before_ms"], y, s=75, color=MUTED_MARK, edgecolor=SURFACE, linewidth=1.5, zorder=3)
    ax.scatter(r["after_ms"], y, s=75, color=ACCENT, edgecolor=SURFACE, linewidth=1.5, zorder=3)
    ax.annotate(format_speedup(r["speedup"]), (1, y), xycoords=("axes fraction", "data"),
                xytext=(14, 0), textcoords="offset points", va="center",
                fontsize=11, fontweight="semibold", color=INK, annotation_clip=False)

ax.annotate("Speedup", (1, 1), xycoords="axes fraction", xytext=(14, 4),
            textcoords="offset points", fontsize=9.5, color=INK_MUTED, annotation_clip=False)
fig.legend(
    handles=[
        Line2D([], [], marker="o", linestyle="", markersize=8, color=MUTED_MARK, label="Before"),
        Line2D([], [], marker="o", linestyle="", markersize=8, color=ACCENT, label="After"),
    ],
    loc="upper right", bbox_to_anchor=(1 - LEFT_IN / WIDTH_IN, 0.985), ncol=2,
    frameon=False, fontsize=10.5, labelcolor=INK_SECONDARY, handletextpad=0.2, columnspacing=1.2,
)
save_chart(fig, os.path.join(CHARTS, "before_after_benchmark.png"))

# ---------------------------------------------------------------- Chart 2
# Speedup ranking, with the 10x-or-better fixes highlighted
ranked = sorted(results, key=lambda r: r["speedup"], reverse=True)
fig, ax = chart_figure(
    len(ranked),
    f"Speedups ranged from {format_speedup(ranked[-1]['speedup'])} to {format_speedup(ranked[0]['speedup'])}",
    "Times faster than before, on a log scale. Blue marks fixes of 10x or better",
)
rounded_hbars(
    ax,
    [query_label(r) for r in ranked],
    [r["speedup"] for r in ranked],
    colors=[ACCENT if r["speedup"] >= 10 else QUIET_MARK for r in ranked],
    value_labels=[format_speedup(r["speedup"]) for r in ranked],
    scale="log",
    baseline=1,
    x_max=ranked[0]["speedup"],
)
save_chart(fig, os.path.join(CHARTS, "speedup_ranking.png"))

# ---------------------------------------------------------------- Chart 3
# Write-path benchmark
autocommit_ms = write_path["row_by_row_autocommit_ms"]
txn_ms = write_path["row_by_row_single_txn_ms"]
bulk_ms = write_path["bulk_executemany_ms"]
bulk_speedup = format_speedup(autocommit_ms / bulk_ms)
fig, ax = chart_figure(
    3,
    f"Bulk inserts were {bulk_speedup} faster than autocommit",
    f"Time to insert {write_path['n_rows']:,} rows",
    right_in=1.6,
)
rounded_hbars(
    ax,
    ["Row by row, autocommit", "Row by row, one transaction", "Bulk insert (executemany)"],
    [autocommit_ms, txn_ms, bulk_ms],
    colors=[QUIET_MARK, QUIET_MARK, ACCENT],
    value_labels=[
        f"{autocommit_ms:,.0f} ms",
        f"{txn_ms:,.0f} ms  ·  {format_speedup(autocommit_ms / txn_ms)} faster",
        f"{bulk_ms:,.0f} ms  ·  {bulk_speedup} faster",
    ],
)
save_chart(fig, os.path.join(CHARTS, "write_path_benchmark.png"))

# ---------------------------------------------------------------- Chart 4
# Dataset overview: three headline numbers, so tiles rather than bars
TABLES = [("schedules", 417080, "one row per train stop"),
          ("stations", 8990, "lookup table"),
          ("trains", 5208, "lookup table")]
height = 2.75
fig = plt.figure(figsize=(WIDTH_IN, height))
add_header(fig, height, "One large table holds nearly all the data", "Rows in each table of the indian_railways database")
tile_width = (WIDTH_IN - 2 * LEFT_IN) / len(TABLES)
for i, (name, rows, role) in enumerate(TABLES):
    x = LEFT_IN + i * tile_width
    if i:
        fig.add_artist(Line2D([(x - 0.3) / WIDTH_IN] * 2, [0.14, 0.52], color=BASELINE, linewidth=0.8))
    fig.text(x / WIDTH_IN, 0.3, f"{rows:,}", fontsize=32, fontweight="semibold", color=INK)
    fig.text(x / WIDTH_IN, 0.13, f"{name}, {role}", fontsize=11, color=INK_SECONDARY)
save_chart(fig, os.path.join(CHARTS, "dataset_overview.png"))

print("Charts written to", CHARTS)
