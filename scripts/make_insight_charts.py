import json
import os

from chart_style import ACCENT, QUIET_MARK, chart_figure, rounded_hbars, save_chart

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARTS = os.path.join(ROOT, "charts")

with open(os.path.join(ROOT, "benchmark", "insights.json")) as f:
    insights = json.load(f)


def station(row):
    return f"{row['station_name'].title()}  ·  {row['station_code']}"


# ---------------------------------------------------------------- Chokepoints
rows = insights["chokepoint_stations"][:12]
fig, ax = chart_figure(
    len(rows),
    f"{rows[0]['station_name'].title()} and {rows[1]['station_name'].title()} carry the most through traffic",
    "Distinct trains passing through a station that is neither their origin nor destination",
)
rounded_hbars(ax, [station(r) for r in rows], [r["passthrough_trains"] for r in rows])
save_chart(fig, os.path.join(CHARTS, "chokepoint_stations.png"))

# ---------------------------------------------------------------- Unstable trains
rows = insights["unstable_schedule_trains"][:10]
fig, ax = chart_figure(
    len(rows),
    "The trains with the least consistent halt times",
    "Standard deviation of each train's halts across its own stops, in minutes",
    label_in=3.3,
)
minutes = [float(r["halt_stddev_seconds"]) / 60 for r in rows]
rounded_hbars(ax, [r["train_name"] for r in rows], minutes,
              value_labels=[f"{m:.0f} min" for m in minutes])
save_chart(fig, os.path.join(CHARTS, "unstable_trains.png"))

# ---------------------------------------------------------------- Zone concentration
rows = insights["zone_concentration"]
values = [float(r["pct_of_zone"]) for r in rows]
fig, ax = chart_figure(
    len(rows),
    f"No zone relies on one station for more than {max(values)}% of its stops",
    "Share of each zone's train stops at its single busiest station",
    footnote="Where stations tie as a zone's busiest, the first by station code is shown.",
)
rounded_hbars(
    ax,
    [f"{r['zone']}  ·  {r['station_name'].title()}" for r in rows],
    values,
    colors=[ACCENT if v == max(values) else QUIET_MARK for v in values],
    value_labels=[f"{v}%" for v in values],
)
save_chart(fig, os.path.join(CHARTS, "zone_concentration.png"))

# ---------------------------------------------------------------- Busiest corridors
rows = insights["busiest_corridors"][:12]
fig, ax = chart_figure(
    len(rows),
    f"{rows[0]['from_station_name'].title()} to {rows[0]['to_station_name'].title()} is the busiest corridor",
    "Distinct trains running each exact origin-to-destination pair",
    label_in=3.5,
)
rounded_hbars(
    ax,
    [f"{r['from_station_name'].title()} → {r['to_station_name'].title()}" for r in rows],
    [r["train_count"] for r in rows],
)
save_chart(fig, os.path.join(CHARTS, "busiest_corridors.png"))

# ---------------------------------------------------------------- Gateway stations
rows = insights["gateway_stations"][:12]
zones = rows[0]["distinct_zones"]
assert all(r["distinct_zones"] == zones for r in rows)
fig, ax = chart_figure(
    len(rows),
    f"These stations connect trains from {zones} railway zones",
    f"Every station here is served by {zones} zones, the most in the data, so they rank by distinct trains",
)
rounded_hbars(ax, [station(r) for r in rows], [r["distinct_trains"] for r in rows])
save_chart(fig, os.path.join(CHARTS, "gateway_stations.png"))

print("Insight charts written to", CHARTS)
