"""Write-path optimization: row-by-row autocommit vs transaction-wrapped vs bulk insert."""
import pymysql
import time
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = 5000

conn = pymysql.connect(host="localhost", user="root", password="root",
                        port=3306, database="indian_railways", autocommit=True)
cur = conn.cursor()
cur.execute("DROP TABLE IF EXISTS write_bench")
cur.execute("""
    CREATE TABLE write_bench (
        id INT PRIMARY KEY AUTO_INCREMENT,
        train_number VARCHAR(50),
        station_code VARCHAR(150),
        arrival TIME,
        departure TIME,
        day INT
    )
""")

cur.execute("SELECT train_number, station_code, arrival, departure, day FROM schedules LIMIT %s", (N,))
rows = cur.fetchall()

# 1. Row-by-row, autocommit on (each INSERT is its own transaction)
conn.autocommit(True)
cur.execute("TRUNCATE write_bench")
t0 = time.perf_counter()
for r in rows:
    cur.execute("INSERT INTO write_bench (train_number, station_code, arrival, departure, day) VALUES (%s,%s,%s,%s,%s)", r)
row_by_row_autocommit_ms = (time.perf_counter() - t0) * 1000

# 2. Row-by-row, wrapped in a single explicit transaction
conn.autocommit(False)
cur.execute("TRUNCATE write_bench")
t0 = time.perf_counter()
for r in rows:
    cur.execute("INSERT INTO write_bench (train_number, station_code, arrival, departure, day) VALUES (%s,%s,%s,%s,%s)", r)
conn.commit()
row_by_row_txn_ms = (time.perf_counter() - t0) * 1000
conn.autocommit(True)

# 3. Bulk multi-row INSERT (single statement, executemany)
cur.execute("TRUNCATE write_bench")
t0 = time.perf_counter()
cur.executemany(
    "INSERT INTO write_bench (train_number, station_code, arrival, departure, day) VALUES (%s,%s,%s,%s,%s)",
    rows,
)
bulk_ms = (time.perf_counter() - t0) * 1000

results = {
    "n_rows": N,
    "row_by_row_autocommit_ms": round(row_by_row_autocommit_ms, 2),
    "row_by_row_single_txn_ms": round(row_by_row_txn_ms, 2),
    "bulk_executemany_ms": round(bulk_ms, 2),
    "speedup_txn_vs_autocommit": round(row_by_row_autocommit_ms / row_by_row_txn_ms, 1),
    "speedup_bulk_vs_autocommit": round(row_by_row_autocommit_ms / bulk_ms, 1),
}

with open(os.path.join(ROOT, "benchmark", "write_path_results.json"), "w") as f:
    json.dump(results, f, indent=2)

print(json.dumps(results, indent=2))

cur.execute("DROP TABLE write_bench")
conn.close()
