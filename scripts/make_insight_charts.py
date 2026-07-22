import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARTS = os.path.join(ROOT, "charts")

with open(os.path.join(ROOT, "benchmark", "insights.json")) as f:
    insights = json.load(f)

plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "font.size": 10})

# ---------------------------------------------------------------- Chokepoints
rows = insights["chokepoint_stations"][:12]
labels = [f"{r['station_name'][:18]}\n({r['station_code']})" for r in rows][::-1]
values = [r["passthrough_trains"] for r in rows][::-1]

fig, ax = plt.subplots(figsize=(9, 6.5))
bars = ax.barh(labels, values, color="#c0392b")
ax.set_xlabel("Distinct trains passing THROUGH this station (not origin/destination)")
ax.set_title("Chokepoint Stations — Structural Single Points of Failure")
for bar, v in zip(bars, values):
    ax.annotate(str(v), (bar.get_width() + 3, bar.get_y() + bar.get_height() / 2), va="center", fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "chokepoint_stations.png"), dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- Unstable trains
rows = insights["unstable_schedule_trains"][:10]
labels = [f"{r['train_name'][:28]}\n({r['train_number']})" for r in rows][::-1]
values = [float(r["halt_stddev_seconds"]) / 60 for r in rows][::-1]

fig, ax = plt.subplots(figsize=(9, 6))
bars = ax.barh(labels, values, color="#8e44ad")
ax.set_xlabel("Halt-time std. deviation across stops (minutes)")
ax.set_title("Most Schedule-Inconsistent Trains (overnight-corrected)")
for bar, v in zip(bars, values):
    ax.annotate(f"{v:.0f}m", (bar.get_width() + 2, bar.get_y() + bar.get_height() / 2), va="center", fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "unstable_trains.png"), dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- Zone concentration
rows = insights["zone_concentration"][:12]
labels = [f"{r['zone']}: {r['station_name'][:16]}" for r in rows][::-1]
values = [float(r["pct_of_zone"]) for r in rows][::-1]

fig, ax = plt.subplots(figsize=(9, 6.5))
bars = ax.barh(labels, values, color="#16a085")
ax.set_xlabel("% of zone's total train-stops running through this one station")
ax.set_title("Zone Traffic Concentration — Busiest Station per Zone")
for bar, v in zip(bars, values):
    ax.annotate(f"{v}%", (bar.get_width() + 0.03, bar.get_y() + bar.get_height() / 2), va="center", fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(CHARTS, "zone_concentration.png"), dpi=150)
plt.close(fig)

print("Insight charts written to", CHARTS)
