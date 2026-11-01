"""
Orchestrates all 7 query case studies for the Indian Railways SQL
optimization project: resets to primary keys only, runs the 'before' query,
captures EXPLAIN ANALYZE + median-of-5 timing, applies the fix
(index/rewrite/summary table), re-runs 'after', checks both return the same
rows, and writes everything to queries/, plans/, benchmark/.
"""
import pymysql
import statistics
import time
import json
import os

from db import connect, halt_seconds, valid_halt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUERIES = os.path.join(ROOT, "queries")
PLANS = os.path.join(ROOT, "plans")
BENCH = os.path.join(ROOT, "benchmark")

conn = connect(autocommit=True)

INDEXES = {
    "idx_sched_halt": ("schedules", "CREATE INDEX idx_sched_halt ON schedules (station_code, station_name, arrival, departure);"),
    "idx_sched_station_arrival": ("schedules", "CREATE INDEX idx_sched_station_arrival ON schedules (station_code, arrival);"),
    "idx_sched_trainnum": ("schedules", "CREATE INDEX idx_sched_trainnum ON schedules (train_number);"),
    "idx_trains_type": ("trains", "CREATE INDEX idx_trains_type ON trains (train_type);"),
    "idx_trains_from": ("trains", "CREATE INDEX idx_trains_from ON trains (from_station_code);"),
}


def run_timed(sql, runs=5):
    times = []
    cur = conn.cursor()
    for _ in range(runs):
        t0 = time.perf_counter()
        cur.execute(sql)
        rows = cur.fetchall()
        times.append((time.perf_counter() - t0) * 1000
                      )
    cur.close()
    return round(statistics.median(times), 2), sorted(rows, key=repr)


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


def drop_indexes():
    cur = conn.cursor()
    for name, (table, _) in INDEXES.items():
        try:
            cur.execute(f"DROP INDEX {name} ON {table}")
        except pymysql.err.Error:
            pass
    cur.close()


def cleanup():
    drop_indexes()
    exec_ddl("DROP TABLE IF EXISTS station_traffic_summary")
    exec_ddl("DROP TABLE IF EXISTS q_working_set")


cleanup()

results = []


def case_study(n, title, technique, before_sql, ddl_fixes, after_sql, notes="",
               setup_ddls=(), variants=None, same_rows=True, before_runs=5):
    print(f"\n=== Query {n}: {title} ===")
    # Every case study starts from primary keys only, so no query inherits
    # an index from an earlier one. setup_ddls are prerequisites shared by
    # both sides of the comparison.
    drop_indexes()
    for ddl in setup_ddls:
        exec_ddl(ddl)

    before_ms, before_rows = run_timed(before_sql, runs=before_runs)
    before_plan = explain_analyze(before_sql)
    print(f"before: {before_ms} ms")

    for ddl in ddl_fixes:
        print(f"applying fix: {ddl.strip()[:80]}...")
        exec_ddl(ddl)

    after_ms, after_rows = run_timed(after_sql)
    after_plan = explain_analyze(after_sql)
    print(f"after: {after_ms} ms")

    if same_rows and before_rows != after_rows:
        raise RuntimeError(f"Query {n}: before and after returned different rows")

    variants_ms = {}
    for label, sql in (variants or {}).items():
        variants_ms[label], _ = run_timed(sql)
        print(f"variant '{label}': {variants_ms[label]} ms")

    save(os.path.join(QUERIES, f"query{n}_before.sql"), before_sql.strip() + "\n")
    save(os.path.join(QUERIES, f"query{n}_after.sql"), after_sql.strip() + "\n")
    save(os.path.join(PLANS, f"query{n}_before.txt"), before_plan)
    save(os.path.join(PLANS, f"query{n}_after.txt"), after_plan)

    results.append({
        "n": n, "title": title, "technique": technique,
        "before_ms": before_ms, "after_ms": after_ms, "before_runs": before_runs,
        "speedup": round(before_ms / after_ms, 1) if after_ms else None,
        "same_rows_checked": same_rows,
        "variants_ms": variants_ms,
        "notes": notes,
    })


# ---------------------------------------------------------------- Query 1
q1_sql = f"""
    SELECT station_code, station_name,
           AVG({halt_seconds()}) AS avg_halt_seconds,
           COUNT(*) AS stop_count
    FROM schedules
    WHERE {valid_halt()}
    GROUP BY station_code, station_name
    HAVING stop_count >= 20
    ORDER BY avg_halt_seconds DESC, station_code
    LIMIT 20;
"""
case_study(
    1, "Average halt time per station",
    "Covering index on filter+group+aggregate columns",
    before_sql=q1_sql,
    ddl_fixes=[INDEXES["idx_sched_halt"][1]],
    after_sql=q1_sql,
    notes="Stations with fewer than 20 timed stops are excluded so a handful of long halts can't top the ranking.",
)

# ---------------------------------------------------------------- Query 2
q2_sql = """
    SELECT train_number, train_name, arrival, departure
    FROM schedules
    WHERE station_code = 'CNB' AND arrival BETWEEN '06:00:00' AND '10:00:00'
    ORDER BY arrival;
"""
case_study(
    2, "Trains passing through a station within a time window",
    "Composite index on (station_code, arrival)",
    before_sql=q2_sql,
    ddl_fixes=[INDEXES["idx_sched_station_arrival"][1]],
    after_sql=q2_sql,
    notes="Classic range-query composite index: equality column first, range column second.",
)

# ---------------------------------------------------------------- Query 3
case_study(
    3, "Longest-halting station per train",
    "Correlated subquery -> window function (RANK)",
    before_sql=f"""
        SELECT s1.train_number, s1.station_code, s1.station_name,
               {halt_seconds('s1')} AS halt_seconds
        FROM schedules s1
        WHERE {valid_halt('s1')}
          AND {halt_seconds('s1')} = (
              SELECT MAX({halt_seconds('s2')})
              FROM schedules s2
              WHERE s2.train_number = s1.train_number AND {valid_halt('s2')}
          );
    """,
    ddl_fixes=[],
    after_sql=f"""
        SELECT train_number, station_code, station_name, halt_seconds
        FROM (
            SELECT train_number, station_code, station_name,
                   {halt_seconds()} AS halt_seconds,
                   RANK() OVER (PARTITION BY train_number ORDER BY {halt_seconds()} DESC) AS rnk
            FROM schedules
            WHERE {valid_halt()}
        ) ranked
        WHERE rnk = 1;
    """,
    setup_ddls=[INDEXES["idx_sched_trainnum"][1]],
    before_runs=1,
    notes="The correlated form takes minutes per run, so before_ms is a single run rather than a median of 5. Both sides run on the full table with idx_sched_trainnum in place, because without it the correlated subquery re-scans all 417K rows for each of ~384K outer rows and never finishes in practical time. The correlated form still runs its inner MAX once per outer row; the window function ranks everything in one sort.",
)

# ---------------------------------------------------------------- Query 4
q4_in_sql = """
    SELECT DISTINCT station_code, station_name
    FROM schedules
    WHERE train_number IN (
        SELECT train_number FROM trains WHERE train_type IN ('Raj', 'Drnt')
    );
"""
case_study(
    4, "Stations served by at least one Rajdhani/Duronto train",
    "Index on join/filter column (schedules.train_number) + JOIN rewrite",
    before_sql=q4_in_sql,
    ddl_fixes=[
        INDEXES["idx_trains_type"][1],
        INDEXES["idx_sched_trainnum"][1],
    ],
    after_sql="""
        SELECT DISTINCT sch.station_code, sch.station_name
        FROM schedules sch
        JOIN trains t ON t.train_number = sch.train_number
        WHERE t.train_type IN ('Raj', 'Drnt');
    """,
    variants={
        "IN, indexed": q4_in_sql,
        "EXISTS, indexed": """
            SELECT DISTINCT sch.station_code, sch.station_name
            FROM schedules sch
            WHERE EXISTS (
                SELECT 1 FROM trains t
                WHERE t.train_number = sch.train_number AND t.train_type IN ('Raj', 'Drnt')
            );
        """,
    },
    notes="The bottleneck is the full 417K-row scan of schedules with no index on train_number, not the IN/EXISTS/JOIN syntax: variants_ms times all three forms once indexed. The JOIN form is kept for clarity.",
)

# ---------------------------------------------------------------- Query 5
q5_star_sql = """
    SELECT * FROM trains WHERE from_station_code = 'NDLS';
"""
case_study(
    5, "Full train route detail lookup",
    "Index on from_station_code + SELECT * -> projected columns",
    before_sql=q5_star_sql,
    ddl_fixes=[INDEXES["idx_trains_from"][1]],
    after_sql="""
        SELECT train_number, train_name, train_type, to_station_code, departure, arrival, distance
        FROM trains WHERE from_station_code = 'NDLS';
    """,
    variants={"SELECT *, indexed": q5_star_sql},
    same_rows=False,
    notes="Two changes are bundled here, so variants_ms times SELECT * with the index alone to separate them: the gap from before_ms is the index, the gap to after_ms is dropping route_path and the other unused columns. Rows aren't compared because the projection returns fewer columns.",
)

# ---------------------------------------------------------------- Query 6
# The cursor is the last id of the previous page. ids have gaps, so it is
# not simply 300000; a real client would already hold it from that page.
cur = conn.cursor()
cur.execute("SELECT id FROM schedules ORDER BY id LIMIT 1 OFFSET 299999")
page_cursor = cur.fetchone()[0]
cur.close()

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
    after_sql=f"""
        SELECT id, train_number, station_code, arrival
        FROM schedules
        WHERE id > {page_cursor}
        ORDER BY id
        LIMIT 20;
    """,
    notes=f"OFFSET forces MySQL to scan and discard 300,000 rows before returning 20; keyset pagination seeks directly via the primary key. The cursor {page_cursor} is the last id of the previous page, so both queries return the same 20 rows.",
)

# ---------------------------------------------------------------- Query 7
q7_aggregate = f"""
    SELECT station_code, station_name, COUNT(*) AS total_stops,
           COUNT(DISTINCT train_number) AS train_count,
           AVG({halt_seconds()}) AS avg_halt_seconds
    FROM schedules
    WHERE {valid_halt()}
    GROUP BY station_code, station_name
"""
case_study(
    7, "Live aggregation vs materialized-view-style summary table",
    "Summary table simulating a materialized view",
    before_sql=q7_aggregate + ";",
    ddl_fixes=[
        "DROP TABLE IF EXISTS station_traffic_summary;",
        f"CREATE TABLE station_traffic_summary AS {q7_aggregate};",
        "ALTER TABLE station_traffic_summary ADD PRIMARY KEY (station_code);",
    ],
    after_sql="""
        SELECT station_code, station_name, total_stops, train_count, avg_halt_seconds
        FROM station_traffic_summary;
    """,
    notes="MySQL has no native materialized view; this simulates one with a summary table refreshed periodically (e.g. via an EVENT). Query time drops to a plain table read at the cost of staleness between refreshes.",
)

# Leave the database fully optimized for insights.py and the live dashboard.
drop_indexes()
for _, ddl in INDEXES.values():
    exec_ddl(ddl)

save(os.path.join(BENCH, "results.json"), json.dumps(results, indent=2))
print("\n\nAll 7 case studies complete. Results written to benchmark/results.json")
for r in results:
    print(f"Q{r['n']:>2} {r['title'][:45]:45} {r['before_ms']:>9} ms -> {r['after_ms']:>9} ms  ({r['speedup']}x)")

conn.close()
