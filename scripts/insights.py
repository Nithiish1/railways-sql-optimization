"""
Real-data insight queries beyond the pure query-optimization case studies:
chokepoint stations (single points of failure), unstable-schedule trains,
and zone traffic concentration. Results feed the README's Insights section
and the Streamlit frontend.
"""
import pymysql
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
conn = pymysql.connect(host="localhost", user="root", password="root",
                        port=3306, database="indian_railways")
cur = conn.cursor(pymysql.cursors.DictCursor)

insights = {}

# ---------------------------------------------------------------- Insight 1
# Chokepoint stations: stations where a train merely PASSES THROUGH
# (not its origin or destination) for the most distinct trains.
# High pass-through count = many routes structurally depend on this single
# station; if it goes down (accident, maintenance, strike), it disrupts the
# most journeys that don't even start or end there.
cur.execute("""
    SELECT s.station_code, s.station_name, COUNT(DISTINCT s.train_number) AS passthrough_trains
    FROM schedules s
    JOIN trains t ON t.train_number = s.train_number
    WHERE s.station_code <> t.from_station_code
      AND s.station_code <> t.to_station_code
    GROUP BY s.station_code, s.station_name
    ORDER BY passthrough_trains DESC
    LIMIT 15
""")
insights["chokepoint_stations"] = cur.fetchall()

# ---------------------------------------------------------------- Insight 2
# Schedule instability: trains whose halt times vary the most across their
# own stops (high stddev) - a proxy for inconsistent/unstable scheduling
# (some stops padded heavily, others barely touched).
cur.execute("""
    SELECT train_number, train_name,
           COUNT(*) AS stops,
           ROUND(STDDEV(MOD(TIMESTAMPDIFF(SECOND, arrival, departure) + 86400, 86400)), 1) AS halt_stddev_seconds,
           ROUND(AVG(MOD(TIMESTAMPDIFF(SECOND, arrival, departure) + 86400, 86400)), 1) AS halt_avg_seconds
    FROM schedules
    WHERE arrival IS NOT NULL AND departure IS NOT NULL
    GROUP BY train_number, train_name
    HAVING stops >= 10
    ORDER BY halt_stddev_seconds DESC
    LIMIT 15
""")
insights["unstable_schedule_trains"] = cur.fetchall()

# ---------------------------------------------------------------- Insight 3
# Zone concentration risk: for each zone, what share of that zone's total
# train-stops runs through its single busiest station? A high share means
# that one station is a structural single point of failure for the zone.
cur.execute("""
    WITH zone_totals AS (
        SELECT t.zone, COUNT(*) AS zone_stop_count
        FROM schedules s JOIN trains t ON t.train_number = s.train_number
        WHERE t.zone IS NOT NULL AND t.zone <> '' AND t.zone <> '?'
        GROUP BY t.zone
    ),
    station_in_zone AS (
        SELECT t.zone, s.station_code, s.station_name, COUNT(*) AS stop_count
        FROM schedules s JOIN trains t ON t.train_number = s.train_number
        WHERE t.zone IS NOT NULL AND t.zone <> '' AND t.zone <> '?'
        GROUP BY t.zone, s.station_code, s.station_name
    ),
    ranked AS (
        SELECT siz.*, ROW_NUMBER() OVER (PARTITION BY siz.zone ORDER BY siz.stop_count DESC) AS rnk
        FROM station_in_zone siz
    )
    SELECT r.zone, r.station_code, r.station_name, r.stop_count, zt.zone_stop_count,
           ROUND(100.0 * r.stop_count / zt.zone_stop_count, 1) AS pct_of_zone
    FROM ranked r
    JOIN zone_totals zt ON zt.zone = r.zone
    WHERE r.rnk = 1
    ORDER BY pct_of_zone DESC
    LIMIT 15
""")
insights["zone_concentration"] = cur.fetchall()

# ---------------------------------------------------------------- Insight 4
# Longest single-train routes (distance) - operationally most exposed to
# any single delay compounding over the whole journey.
cur.execute("""
    SELECT train_number, train_name, from_station_name, to_station_name, distance
    FROM trains
    WHERE distance IS NOT NULL
    ORDER BY distance DESC
    LIMIT 10
""")
insights["longest_routes"] = cur.fetchall()

with open(os.path.join(ROOT, "benchmark", "insights.json"), "w") as f:
    json.dump(insights, f, indent=2, default=str)

for k, v in insights.items():
    print(f"\n=== {k} ===")
    for row in v[:5]:
        print(row)

conn.close()
