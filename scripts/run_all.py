"""
Orchestrates all 7 query case studies for the Indian Railways SQL
optimization project: runs the 'before' query, captures EXPLAIN ANALYZE +
median-of-5 timing, applies the fix (index/rewrite/summary table),
re-runs 'after', and writes everything to queries/, plans/, benchmark/.
"""
import pymysql
import statistics
import time
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUERIES = os.path.join(ROOT, "queries")
PLANS = os.path.join(ROOT, "plans")
BENCH = os.path.join(ROOT, "benchmark")

conn = pymysql.connect(host="localhost", user="root", password="root",
                        port=3306, database="indian_railways", autocommit=True)


def run_timed(sql, runs=5):
    times = []
    cur = conn.cursor()
    for _ in range(runs):
        t0 = time.perf_counter()
        cur.execute(sql)
        cur.fetchall()
        times.append((time.perf_counter() - t0) * 1000
                      )
    cur.close()
    return round(statistics.median(times), 2), times


def explain_analyze(sql):
    cur = conn.cursor()
    cur.execute("EXPLAIN ANALYZE " + sql)
    rows = cur.fetchall()
    cur.close()
    return "\n".join(r[0] for r in rows)


def exec_ddl(sql):
    cur = conn.cursor()
    cur.execute(sql)
    cur.close()


def save(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def cleanup():
    cleanup_ddls = [
        "DROP INDEX idx_sched_halt ON schedules",
        "DROP INDEX idx_sched_station_arrival ON schedules",
        "DROP INDEX idx_trains_type ON trains",
        "DROP INDEX idx_trains_from ON trains",
        "DROP INDEX idx_sched_trainnum ON schedules",
        "DROP TABLE IF EXISTS station_traffic_summary",
        "DROP TABLE IF EXISTS q_working_set",
    ]
    cur = conn.cursor()
    for ddl in cleanup_ddls:
        try:
            cur.execute(ddl)
        except pymysql.err.Error:
            pass
    cur.close()


cleanup()

results = []


def case_study(n, title, technique, before_sql, ddl_fixes, after_sql, notes=""):
    print(f"\n=== Query {n}: {title} ===")
    before_ms, _ = run_timed(before_sql)
    before_plan = explain_analyze(before_sql)
    print(f"before: {before_ms} ms")

    for ddl in ddl_fixes:
        print(f"applying fix: {ddl.strip()[:80]}...")
        exec_ddl(ddl)

    after_ms, _ = run_timed(after_sql)
    after_plan = explain_analyze(after_sql)
    print(f"after: {after_ms} ms")

    save(os.path.join(QUERIES, f"query{n}_before.sql"), before_sql.strip() + "\n")
    save(os.path.join(QUERIES, f"query{n}_after.sql"), after_sql.strip() + "\n")
    save(os.path.join(PLANS, f"query{n}_before.txt"), before_plan)
    save(os.path.join(PLANS, f"query{n}_after.txt"), after_plan)

    results.append({
        "n": n, "title": title, "technique": technique,
        "before_ms": before_ms, "after_ms": after_ms,
        "speedup": round(before_ms / after_ms, 1) if after_ms else None,
        "notes": notes,
    })


# ---------------------------------------------------------------- Query 1
case_study(
    1, "Average halt time per station",
    "Covering index on filter+group+aggregate columns",
    before_sql="""
        SELECT station_code, station_name,
               AVG(TIMESTAMPDIFF(SECOND, arrival, departure)) AS avg_halt_seconds,
               COUNT(*) AS stop_count
        FROM schedules
        WHERE arrival IS NOT NULL AND departure IS NOT NULL
        GROUP BY station_code, station_name
        ORDER BY avg_halt_seconds DESC
        LIMIT 20;
    """,
    ddl_fixes=[
        "CREATE INDEX idx_sched_halt ON schedules (station_code, station_name, arrival, departure);",
    ],
    after_sql="""
        SELECT station_code, station_name,
               AVG(TIMESTAMPDIFF(SECOND, arrival, departure)) AS avg_halt_seconds,
               COUNT(*) AS stop_count
        FROM schedules
        WHERE arrival IS NOT NULL AND departure IS NOT NULL
        GROUP BY station_code, station_name
        ORDER BY avg_halt_seconds DESC
        LIMIT 20;
    """,
    notes="Ranking is skewed by low stop_count stations; production version would add HAVING stop_count >= N.",
)

# ---------------------------------------------------------------- Query 2
case_study(
    2, "Trains passing through a station within a time window",
    "Composite index on (station_code, arrival)",
    before_sql="""
        SELECT train_number, train_name, arrival, departure
        FROM schedules
        WHERE station_code = 'CNB' AND arrival BETWEEN '06:00:00' AND '10:00:00'
        ORDER BY arrival;
    """,
    ddl_fixes=[
        "CREATE INDEX idx_sched_station_arrival ON schedules (station_code, arrival);",
    ],
    after_sql="""
        SELECT train_number, train_name, arrival, departure
        FROM schedules
        WHERE station_code = 'CNB' AND arrival BETWEEN '06:00:00' AND '10:00:00'
        ORDER BY arrival;
    """,
    notes="Classic range-query composite index: equality column first, range column second.",
)

# ---------------------------------------------------------------- Query 3
exec_ddl("DROP TABLE IF EXISTS q_working_set")
exec_ddl("""
    CREATE TABLE q_working_set AS
    SELECT train_number, station_code, station_name,
           TIMESTAMPDIFF(SECOND, arrival, departure) AS halt_seconds
    FROM schedules
    WHERE arrival IS NOT NULL AND departure IS NOT NULL
      AND train_number IN (SELECT train_number FROM (SELECT DISTINCT train_number FROM schedules ORDER BY train_number LIMIT 20) t300);
""")
case_study(
    3, "Longest-halting station per train",
    "Correlated subquery -> window function (RANK)",
    before_sql="""
        SELECT s1.train_number, s1.station_code, s1.station_name, s1.halt_seconds
        FROM q_working_set s1
        WHERE s1.halt_seconds = (
            SELECT MAX(s2.halt_seconds) FROM q_working_set s2 WHERE s2.train_number = s1.train_number
        );
    """,
    ddl_fixes=[],
    after_sql="""
        SELECT train_number, station_code, station_name, halt_seconds
        FROM (
            SELECT train_number, station_code, station_name, halt_seconds,
                   RANK() OVER (PARTITION BY train_number ORDER BY halt_seconds DESC) AS rnk
            FROM q_working_set
        ) ranked
        WHERE rnk = 1;
    """,
    notes="Demonstrated on a 20-train / ~650-row working set materialized from schedules (the full, unindexed-train_number correlated version re-scanning all 417K rows per outer row would take many minutes on the raw table, so the underlying data is pre-filtered here for a tractable, fair before/after comparison). The correlated subquery still re-evaluates its inner MAX subquery once per outer row (O(n^2) within the working set); the window function computes the ranking in a single pass over the same data.",
)

# ---------------------------------------------------------------- Query 4
case_study(
    4, "Stations served by at least one Rajdhani/Duronto train",
    "Index on join/filter column (schedules.train_number) + JOIN rewrite",
    before_sql="""
        SELECT DISTINCT station_code, station_name
        FROM schedules
        WHERE train_number IN (
            SELECT train_number FROM trains WHERE train_type IN ('Raj', 'Drnt')
        );
    """,
    ddl_fixes=[
        "CREATE INDEX idx_trains_type ON trains (train_type);",
        "CREATE INDEX idx_sched_trainnum ON schedules (train_number);",
    ],
    after_sql="""
        SELECT DISTINCT sch.station_code, sch.station_name
        FROM schedules sch
        JOIN trains t ON t.train_number = sch.train_number
        WHERE t.train_type IN ('Raj', 'Drnt');
    """,
    notes="The real bottleneck here wasn't IN vs JOIN (both were tested and performed the same once indexed) - it was a full 417K-row scan of schedules with no index on the FK column being filtered/joined on (train_number). Adding idx_sched_trainnum alongside idx_trains_type is what actually fixes it; the JOIN form is kept because it's the clearer way to write the same query, not because it's structurally faster than IN here.",
)

# ---------------------------------------------------------------- Query 5
case_study(
    5, "Full train route detail lookup",
    "SELECT * vs projected columns",
    before_sql="""
        SELECT * FROM trains WHERE from_station_code = 'NDLS';
    """,
    ddl_fixes=[
        "CREATE INDEX idx_trains_from ON trains (from_station_code);",
    ],
    after_sql="""
        SELECT train_number, train_name, train_type, to_station_code, departure, arrival, distance
        FROM trains WHERE from_station_code = 'NDLS';
    """,
    notes="SELECT * drags the large route_path TEXT column off-page for every row; projecting only needed columns lets the query be answered largely from the index/short row data.",
)

# ---------------------------------------------------------------- Query 6
case_study(
    6, "Paginating deep into the schedules table",
    "OFFSET pagination vs keyset (seek) pagination",
    before_sql="""
        SELECT id, train_number, station_code, arrival
        FROM schedules
        ORDER BY id
        LIMIT 20 OFFSET 300000;
    """,
    ddl_fixes=[],
    after_sql="""
        SELECT id, train_number, station_code, arrival
        FROM schedules
        WHERE id > 300000
        ORDER BY id
        LIMIT 20;
    """,
    notes="OFFSET forces MySQL to scan and discard 300,000 rows before returning 20; keyset pagination seeks directly via the primary key.",
)

# ---------------------------------------------------------------- Query 7
case_study(
    7, "Live aggregation vs materialized-view-style summary table",
    "Summary table simulating a materialized view",
    before_sql="""
        SELECT station_code, station_name, COUNT(*) AS total_stops,
               COUNT(DISTINCT train_number) AS train_count,
               AVG(TIMESTAMPDIFF(SECOND, arrival, departure)) AS avg_halt_seconds
        FROM schedules
        WHERE arrival IS NOT NULL AND departure IS NOT NULL
        GROUP BY station_code, station_name;
    """,
    ddl_fixes=[
        "DROP TABLE IF EXISTS station_traffic_summary;",
        """CREATE TABLE station_traffic_summary AS
           SELECT station_code, station_name, COUNT(*) AS total_stops,
                  COUNT(DISTINCT train_number) AS train_count,
                  AVG(TIMESTAMPDIFF(SECOND, arrival, departure)) AS avg_halt_seconds
           FROM schedules
           WHERE arrival IS NOT NULL AND departure IS NOT NULL
           GROUP BY station_code, station_name;""",
        "ALTER TABLE station_traffic_summary ADD PRIMARY KEY (station_code);",
    ],
    after_sql="""
        SELECT station_code, station_name, total_stops, train_count, avg_halt_seconds
        FROM station_traffic_summary;
    """,
    notes="MySQL has no native materialized view; this simulates one with a summary table refreshed periodically (e.g. via an EVENT). Query time drops to a plain table read at the cost of staleness between refreshes.",
)

save(os.path.join(BENCH, "results.json"), json.dumps(results, indent=2))
print("\n\nAll 7 case studies complete. Results written to benchmark/results.json")
for r in results:
    print(f"Q{r['n']:>2} {r['title'][:45]:45} {r['before_ms']:>9} ms -> {r['after_ms']:>9} ms  ({r['speedup']}x)")

conn.close()
