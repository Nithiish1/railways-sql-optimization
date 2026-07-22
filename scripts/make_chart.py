import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "benchmark", "results.json")) as f:
    results = json.load(f)

labels = [f"Q{r['n']}" for r in results]
before = [r["before_ms"] for r in results]
after = [r["after_ms"] for r in results]

x = range(len(labels))
width = 0.38

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.bar([i - width / 2 for i in x], before, width, label="Before", color="#c0392b")
ax.bar([i + width / 2 for i in x], after, width, label="After", color="#27ae60")
ax.set_yscale("log")
ax.set_ylabel("Median time (ms, log scale)")
ax.set_title("Indian Railways SQL Optimization — Before vs After (median of 5 runs)")
ax.set_xticks(list(x))
ax.set_xticklabels(labels)
ax.legend()
ax.grid(axis="y", linestyle="--", alpha=0.4)

for i, r in enumerate(results):
    ax.annotate(f"{r['speedup']}x", (i, max(r['before_ms'], r['after_ms']) * 1.15),
                ha="center", fontsize=8)

plt.tight_layout()
out_path = os.path.join(ROOT, "charts", "before_after_benchmark.png")
plt.savefig(out_path, dpi=150)
print("saved", out_path)
