import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARTS = os.path.join(ROOT, "charts")

with open(os.path.join(ROOT, "benchmark", "results.json")) as f:
    results = json.load(f)

with open(os.path.join(ROOT, "benchmark", "write_path_results.json")) as f:
    write_path = json.load(f)

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.size": 10,
})

# ---------------------------------------------------------------- Chart 1
# Before vs after, log scale, all 10 queries
labels = [f"Q{r['n']}" for r in results]
before = [r["before_ms"] for r in results]
after = [r["after_ms"] for r in results]

x = range(len(labels))
width = 0.38

fig, ax = plt.subplots(figsize=(12, 6))
ax.bar([i - width / 2 for i in x], before, width, label="Before", color="#c0392b")
ax.bar([i + width / 2 for i in x], after, width, label="After", color="#27ae60")
ax.set_yscale("log")
ax.set_ylabel("Median time (ms, log scale)")
ax.set_title("Before vs After — Query Optimizations (median of 5 runs)")
ax.set_xticks(list(x))
ax.set_xticklabels(labels)
ax.legend()
ax.grid(axis="y", linestyle="--", alpha=0.4)
for i, r in enumerate(results):
    ax.annotate(f"{r['speedup']}x", (i, max(r['before_ms'], r['after_ms']) * 1.2),
                ha="center", fontsize=8, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "before_after_benchmark.png"), dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- Chart 2
# Speedup ranking, horizontal, color-coded
sorted_results = sorted(results, key=lambda r: r["speedup"])
labels2 = [f"Q{r['n']}: {r['title'][:38]}" for r in sorted_results]
speedups = [r["speedup"] for r in sorted_results]
colors = ["#f39c12" if s < 5 else "#27ae60" for s in speedups]

fig, ax = plt.subplots(figsize=(11, 5.5))
bars = ax.barh(labels2, speedups, color=colors)
ax.axvline(1, color="black", linewidth=0.8, linestyle="--")
ax.set_xscale("log")
ax.set_xlabel("Speedup (x, log scale)")
ax.set_title("Speedup by Query — sorted")
for bar, s in zip(bars, speedups):
    ax.annotate(f"{s}x", (bar.get_width() * 1.05, bar.get_y() + bar.get_height() / 2),
                va="center", fontsize=9, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "speedup_ranking.png"), dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- Chart 3
# Write-path benchmark
wp_labels = ["Row-by-row\n(autocommit)", "Row-by-row\n(1 transaction)", "Bulk\n(executemany)"]
wp_values = [write_path["row_by_row_autocommit_ms"], write_path["row_by_row_single_txn_ms"], write_path["bulk_executemany_ms"]]
wp_colors = ["#c0392b", "#f39c12", "#27ae60"]

fig, ax = plt.subplots(figsize=(7, 5.5))
bars = ax.bar(wp_labels, wp_values, color=wp_colors)
ax.set_ylabel("Time for 5,000 inserts (ms)")
ax.set_title("Write-Path Optimization: Insert Strategy Comparison")
for bar, v in zip(bars, wp_values):
    ax.annotate(f"{v:,.0f} ms", (bar.get_x() + bar.get_width() / 2, v),
                ha="center", va="bottom", fontsize=9, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "write_path_benchmark.png"), dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- Chart 4
# Dataset overview
fig, ax = plt.subplots(figsize=(6, 4.5))
tables = ["stations", "trains", "schedules"]
counts = [8990, 5208, 417080]
bars = ax.bar(tables, counts, color=["#2980b9", "#8e44ad", "#16a085"])
ax.set_yscale("log")
ax.set_ylabel("Row count (log scale)")
ax.set_title("Dataset Size by Table")
for bar, c in zip(bars, counts):
    ax.annotate(f"{c:,}", (bar.get_x() + bar.get_width() / 2, c),
                ha="center", va="bottom", fontsize=9, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "dataset_overview.png"), dpi=150)
plt.close(fig)

print("Charts written to", CHARTS)
