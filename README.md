# 🚆 Indian Railways SQL Optimization Project

![MySQL](https://img.shields.io/badge/MySQL-8.0.37-4479A1?logo=mysql&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Rows](https://img.shields.io/badge/schedules-417%2C080%20rows-16a085)
![Queries](https://img.shields.io/badge/case%20studies-7-orange)
![Best speedup](https://img.shields.io/badge/best%20speedup-193x-success)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

A query-optimization case study on a real, ~430K-row Indian Railways
dataset (stations, trains, schedules) — diagnosing slow queries with
`EXPLAIN ANALYZE`, fixing them through indexing, query rewriting, and
a materialized-view simulation, and measuring the before/after impact
with a reproducible benchmark harness.

**TL;DR:** 7 real queries, each measured from a primary-keys-only
baseline (median of 5 runs on a warm cache), speedups from 1.8x up to
**193x**, every before/after pair checked to return the same rows, and
every `EXPLAIN ANALYZE` plan and query committed to this repo.

## Table of Contents

- [Dataset](#dataset)
- [Schema](#schema)
- [Data Quality Notes](#data-quality-notes)
- [Optimization Techniques Covered](#optimization-techniques-covered)
- [Setup](#setup)
- [Why These Queries](#why-these-queries)
- [What This Project Does Not Model](#what-this-project-does-not-model)
- [Results — Query Case Studies](#results--query-case-studies)
- [Write-Path Optimization](#write-path-optimization-bulk-vs-row-by-row-insert)
- [Insights & Network Analysis](#insights--network-analysis)
- [Frontend Dashboard](#frontend-dashboard)
- [Presentation](#presentation)
- [Reproducing](#reproducing)

## Project Structure

```
railways-sql-optimization/
├── sql/schema.sql              # raw, unindexed table definitions
├── sql/load.sql                # loads the CSVs and verifies row counts
├── convert.py                  # GeoJSON -> flat CSV converter
├── requirements.txt            # dependencies for scripts/
├── queries/                    # query{1-7}_{before,after}.sql
├── plans/                      # EXPLAIN ANALYZE output, one file per query per state
├── benchmark/                  # results.json, write_path_results.json, insights.json
├── charts/                     # generated PNG charts (this README embeds them)
├── frontend/app.py             # Streamlit dashboard (benchmarks, insights, live lookup)
├── presentation/index.html     # self-contained slide-deck walkthrough
└── scripts/
    ├── db.py                    # MySQL connection and shared halt-time SQL
    ├── run_all.py               # orchestrates all 7 case studies end-to-end
    ├── insights.py              # chokepoint/instability/zone/corridor/gateway queries
    ├── make_chart.py            # regenerates benchmark charts
    ├── make_insight_charts.py   # regenerates insight charts
    ├── make_presentation.py     # regenerates presentation/index.html
    └── write_path_bench.py      # bulk vs row-by-row insert benchmark
```

## Dataset

Source: Indian Railways public dataset (station list, train list, and
train-schedule/stop data), originally scraped and published as GeoJSON
on Kaggle (mirrors of the datameet/railways project).

![Dataset overview](charts/dataset_overview.png)

- `stations` — 8,990 rows
- `trains` — 5,208 rows
- `schedules` — 417,080 rows (train stop records — one row per train
  per station per stop)

## Schema

```mermaid
erDiagram
  STATIONS ||--o{ SCHEDULES : "appears in"
  TRAINS ||--o{ SCHEDULES : "runs as"
  STATIONS {
    varchar code PK
    varchar name
    varchar state
    varchar zone
    varchar address
    decimal latitude
    decimal longitude
  }
  TRAINS {
    varchar train_number PK
    varchar train_name
    varchar train_type
    varchar from_station_code
    varchar to_station_code
    time departure
    time arrival
    int distance
    text route_path
  }
  SCHEDULES {
    int id PK
    varchar train_number
    varchar station_code
    time arrival
    time departure
    int day
  }
```

`stations` and `trains` are small lookup tables; `schedules` is the
~417K-row fact table where nearly all query and optimization work in
this project happens — every station appears in many schedule rows,
every train runs as many schedule stops, and `schedules` is the
many-to-many join point between them.

The relationships above are logical: `schema.sql` declares no foreign
keys, because MySQL would add an index for each one and the baseline
has to start with primary keys only. Every `train_number` and
`station_code` in `schedules` does match a row in `trains` and
`stations`.

## Data Quality Notes

Real, messy, scraped data required active handling rather than a
straight `LOAD DATA INFILE`. Issues found and how they were resolved:

**1. Nested GeoJSON structure**
Both `stations.json` and `trains.json` are GeoJSON `FeatureCollection`s,
not flat tables. Station code/name/state/zone/address live inside a
`properties` object, and coordinates live inside a separate `geometry`
object (`[longitude, latitude]` order). Trains additionally carry a
full route path as a `LineString` of coordinate pairs. A Python
conversion script (`convert.py`) flattens both files into plain CSVs
before loading, splitting `geometry.coordinates` into separate
`latitude`/`longitude` columns for stations, and preserving the full
route path as a JSON-text `route_path` column on `trains` (unused by
current queries, kept for potential future geospatial work).

**2. Inconsistent null representation**
`schedules.json` represents missing arrival/departure times inconsistently
— sometimes as JSON `null`, sometimes as the literal string `"None"`.
Both are normalized to true SQL `NULL` during conversion, rather than
being loaded as the text `"None"`.

**3. Malformed / oversized "code" fields**
Several station and train identifier fields contain corrupted values far
longer than a normal station/train code — for example, one station
`code` value is `"YAKUT PUR(YKA"` instead of a short code, and one
train's `return_train` field contains a leaked HTML fragment
(`Trivandrum Jan Shatabdi" href=/train/13981/1242/59> 12081`), evidence
that the original data was scraped from a webpage and a stray `<a href>`
tag fragment ended up in the field. Rather than truncating or silently
dropping these rows, the affected columns (`code`, `train_number`,
`from_station_code`, `to_station_code`, `return_train`) were sized
generously (`VARCHAR(50)`–`VARCHAR(255)`) to preserve the data as-is,
and the issue is documented here rather than hidden.

**4. Overnight / boundary trains**
Some schedule rows have `NULL` arrival or departure (trains starting or
terminating at a stop), and some halts cross midnight. MySQL `TIME` has
no date, so a naive `TIMESTAMPDIFF(SECOND, arrival, departure)` reads
`23:58 → 00:04` as negative. All halt calculations use
`MOD(diff + 86400, 86400)` to correct this (see `scripts/db.py`).

**5. Impossible halt times**
A few stops have a departure before their arrival that no midnight
crossing can explain — for example train 40051 at TBMS arrives 11:03 and
departs 11:02, which the midnight correction would turn into a
23 h 59 min halt. No real halt in the data falls between 8 and 17 hours,
so anything of 12 hours or more is treated as an error. That excludes
6 of the 384,107 timed stops; the other 115 stops that wrap past
midnight are kept.

## Optimization Techniques Covered

- Indexing: single-column, composite, and covering indexes
- Query rewriting: correlated subquery → window function, `IN` vs
  `EXISTS` vs `JOIN`, `SELECT *` vs projected columns, `OFFSET` vs
  keyset pagination
- Materialized-view simulation (MySQL has no native materialized view):
  a scheduled summary table for a read-heavy dashboard query
- Write-path optimization: bulk vs row-by-row insert, transaction
  wrapping

Each technique is benchmarked with a reproducible harness (median of 5
timed runs on a warm cache, except Q3's before, which is a single run)
and documented as problem → before → fix → after.

## Setup

1. `pip install -r requirements.txt`
2. Set `MYSQL_PASSWORD` in your environment (`MYSQL_HOST`, `MYSQL_PORT`,
   `MYSQL_USER` and `MYSQL_DATABASE` are also read, defaulting to
   `localhost`, `3306`, `root` and `indian_railways`)
3. `python convert.py` — flattens the raw JSON into `data/*.csv`
4. Copy the CSVs into MySQL's `secure_file_priv` folder
5. Run `sql/schema.sql` — creates the raw, unindexed tables
6. Run `sql/load.sql` — loads and verifies row counts (edit its three
   file paths if your `secure_file_priv` folder isn't the Windows default)

## Why These Queries

These weren't picked at random — each maps to a real access pattern
this schema would actually see, and together they were chosen to hit
every technique in the list above at least once:

| Query | Real-world analogue |
|---|---|
| Q1 | Station dashboard / ops reporting ("how long do trains halt at each station") — heavy aggregation over the whole fact table, the kind of query a nightly report or admin panel would run |
| Q2 | Passenger-facing search ("what trains pass through my station this morning") — a selective, latency-sensitive lookup, the most common query shape in a real booking/enquiry system |
| Q3 | Analytics ("longest halt per train") — a per-group ranking, the exact shape that tempts people into a correlated subquery in real reporting code |
| Q4 | Catalog/filter query ("stations served by premium trains") — the classic case where the real fix turns out to be a missing index on the join/filter column, not the `IN`/`JOIN` syntax itself |
| Q5 | Any API endpoint returning train details — `SELECT *` is extremely common in real backend code and easy to overlook as a cost |
| Q6 | Any paginated API/UI (train list, search results) — OFFSET pagination is the default nearly every ORM generates, and the one that quietly falls over at scale |
| Q7 | A live dashboard reloading a station-summary aggregate on every page view — the case for a summary table over recomputing |

The two intentionally excluded from the list are: (a) point lookups by
primary key, which are already fast without any of this and wouldn't
demonstrate anything, and (b) full-text train-name search
(`LIKE '%Express%'`), which the README's Optimization Techniques
section flags but isn't benchmarked here — a real fix needs `FULLTEXT`
indexing or an external search engine, not a B-tree prefix index, and
was left as a stated-but-not-implemented case rather than faked.

## What This Project Does *Not* Model

Being direct about the limits of a single-connection, read-optimized
benchmark, since a real railway booking/enquiry system's workload
would stress things this project never touches:

- **Every benchmark here is read-only, single-connection.** All
  timings are one client, one query at a time, on an otherwise idle
  server. A real system would have concurrent readers *and* writers
  hitting `schedules` simultaneously — row-lock contention, gap locks
  from range scans, and replication lag are not exercised anywhere in
  this repo. The reported numbers are best-case latency, not
  throughput under load.
- **Every index added has a write-side cost this project never
  measures.** By the end of the 7 case studies, `schedules` carries
  3 secondary indexes and `trains` carries 2 — each one is extra work
  on every `INSERT`/`UPDATE`/`DELETE` (index maintenance, extra
  B-tree pages, more WAL/redo log volume) and extra disk space. For a
  fact table that's genuinely write-heavy in production (railways
  schedule data changes far less often than it's read, so this
  particular tradeoff would lean read-optimized in real life — but
  that's a judgment call this README hadn't stated explicitly until
  now, not a benchmarked one).
- **The write-path benchmark (bulk vs row-by-row insert) is isolated,
  not concurrent** — it measures one client loading 5,000 rows against
  an unlocked table, not insert throughput while the read queries
  above are also running against the same rows.
- **No connection pooling, replica reads, or caching layer** are
  modeled. A production system would likely put a cache (Redis) or a
  read replica in front of the Q1/Q7-style dashboard queries
  rather than relying solely on the summary-table trick shown in Q7.

The honest scope of this project is: *diagnosing and fixing single-query
latency on a realistic schema*, not capacity planning or
concurrency/throughput engineering for a production system.

## Results — Query Case Studies

Every query below was run on the same MySQL 8.0.37 instance, on the
full 417,080-row `schedules` table (plus the small `stations`/`trains`
lookup tables). The harness (`scripts/run_all.py`) drops every secondary
index before each case study, so no query inherits an index from an
earlier one, and it stops with an error if a before/after pair returns
different rows (Q5 is the one exception, because its projection
deliberately returns fewer columns). Each number is the **median of 5
timed runs** on a warm cache, measured end-to-end (query execution +
result fetch), so the numbers are reproducible rather than a single
lucky/unlucky run. Full query text
is in [`queries/`](queries/), full `EXPLAIN ANALYZE` output for every
before/after pair is in [`plans/`](plans/), raw timings are in
[`benchmark/results.json`](benchmark/results.json), and the chart
below is generated by `scripts/make_chart.py`.

![Before/after benchmark chart](charts/before_after_benchmark.png)

![Speedup ranking](charts/speedup_ranking.png)

| # | Query | Technique | Before | After | Speedup |
|---|-------|-----------|-------:|------:|--------:|
| 1 | Average halt time per station | Covering index `(station_code, station_name, arrival, departure)` | 1731 ms | 971 ms | 1.8x |
| 2 | Trains through a station in a time window | Composite index `(station_code, arrival)` | 415 ms | 3.4 ms | **122x** |
| 3 | Longest-halting station per train | Correlated subquery → `RANK() OVER` window function | 360.6 s | 7.4 s | **48x** |
| 4 | Stations served by a Rajdhani/Duronto train | Index on `schedules.train_number` + `JOIN` rewrite | 916 ms | 113 ms | 8.1x |
| 5 | Full train route lookup by origin station | Index + `SELECT *` → projected columns | 29 ms | 5.1 ms | 5.8x |
| 6 | Deep pagination into `schedules` | `OFFSET 300000` → keyset (seek) pagination | 274 ms | 1.4 ms | **193x** |
| 7 | Station traffic dashboard aggregation | Materialized-view-style summary table | 3250 ms | 118 ms | **28x** |

A few of these need context to read fairly:

- **Q1** only reaches 1.8x because it still reads every row; the covering
  index removes the temporary table but not the full scan. Stations with
  fewer than 20 timed stops are excluded so a couple of long halts can't
  top the ranking.
- **Q3** runs on the full table with `idx_sched_trainnum` in place on
  both sides, because without that index the correlated subquery
  re-scans all 417K rows for each of 384K outer rows. Even with it, the
  before takes about 6 minutes, so that number is a **single run** rather
  than a median of 5.
- **Q4**'s gain comes from the indexes, not the rewrite. Once indexed,
  `JOIN`, `IN` and `EXISTS` all land within noise of each other
  (113 ms, 107 ms and 106 ms).
- **Q5** bundles two changes, so `SELECT *` was also timed with the index
  alone: the index takes it from 29 ms to 6.8 ms, and projecting fewer
  columns takes it the rest of the way to 5.1 ms.
- **Q7**'s after is a 3 ms table read on the server (see its plan); most
  of the 118 ms is fetching 7,499 rows into Python.

### Proof, not just a claim — Q6's actual EXPLAIN ANALYZE

<details>
<summary><b>Before</b> — OFFSET 300000 (click to expand)</summary>

```
-> Limit/Offset: 20/300000 row(s)  (cost=21615 rows=20) (actual time=316..316 rows=20 loops=1)
    -> Index scan on schedules using PRIMARY  (cost=21615 rows=300020) (actual time=0.102..289 rows=300020 loops=1)
```

MySQL still has to walk **300,020 rows** through the primary key index
before it can throw away the first 300,000 and return the last 20.

</details>

<details>
<summary><b>After</b> — keyset (seek) pagination (click to expand)</summary>

```
-> Limit: 20 row(s)  (cost=42644 rows=20) (actual time=0.0209..0.0392 rows=20 loops=1)
    -> Filter: (schedules.id > 423375)  (cost=42644 rows=212829) (actual time=0.0203..0.037 rows=20 loops=1)
        -> Index range scan on schedules using PRIMARY over (423375 < id)  (cost=42644 rows=212829) (actual time=0.0189..0.0336 rows=20 loops=1)
```

Same index, same table, same 20 rows — but `WHERE id > 423375 LIMIT 20`
seeks directly to the right spot instead of scanning past everything
before it: 289 ms → 0.03 ms of actual scan time. The cursor is 423375,
not 300000, because ids have gaps: it's the last id of the previous page,
which a real client would already hold.

</details>

All other before/after plans are in [`plans/`](plans/) if you want to
check any of the other queries the same way.

### Write-path optimization (bulk vs row-by-row insert)

Beyond the read queries above, `scripts/write_path_bench.py` benchmarks
insert strategy on 5,000 rows (results in
[`benchmark/write_path_results.json`](benchmark/write_path_results.json)):

![Write path benchmark](charts/write_path_benchmark.png)

| Strategy | Time (5,000 rows) | Speedup vs autocommit |
|---|---:|---:|
| Row-by-row, autocommit per insert | 11,756 ms | 1x |
| Row-by-row, wrapped in one transaction | 735 ms | 16x |
| Bulk multi-row `INSERT` (`executemany`) | 67 ms | **175x** |

Autocommit-per-row pays a full transaction commit (fsync) for every
single row; wrapping the same loop in one transaction removes that
per-row commit cost; and a true bulk insert additionally collapses
5,000 round-trips into a handful of multi-row `INSERT` statements —
which is why `sql/load.sql` uses `LOAD DATA INFILE` rather than
row-by-row inserts for the original 417K-row load.

## Insights & Network Analysis

Beyond optimizing queries, the same dataset was mined for a few honest,
data-backed findings about the network itself (`scripts/insights.py`,
raw output in [`benchmark/insights.json`](benchmark/insights.json)).

### Chokepoint stations (structural single points of failure)

Stations ranked by how many *distinct trains merely pass through* them
(i.e. the station is neither the train's origin nor its destination).
A high count here means many journeys structurally depend on that one
station being operational, even though it's not their starting or
ending point:

![Chokepoint stations](charts/chokepoint_stations.png)

| Station | Code | Trains passing through |
|---|---|---:|
| Sahibabad | SBB | 285 |
| Ghaziabad | GZB | 283 |
| Itarsi Jn | ET | 279 |
| Kopar Road | KOPR | 262 |
| Kanpur Central | CNB | 252 |

### Schedule instability (most inconsistent halt times)

For each train, the standard deviation of its own halt time across its
stops — a proxy for scheduling inconsistency (some stops padded
heavily, others barely touched). This ranking depends on both halt-time
fixes in the Data Quality Notes: without the midnight correction it
fills up with negative halts, and with the correction alone the top 3
are EMU trains whose impossible times become fake 22-to-24-hour halts.
With both, the leaders sit at 33–44 minutes and are mostly passenger and
slip-coach services:

![Unstable trains](charts/unstable_trains.png)

### Zone traffic concentration

For each railway zone, what share of its total train-stops run through
its single busiest station — a proxy for whether one station is a
bottleneck for its whole zone:

![Zone concentration](charts/zone_concentration.png)

The honest finding here is a **non-finding**: the highest concentration
across all 17 named zones is only ~1.6% (Majorda and Suravali, tied in
the small KR zone).
No zone in this dataset has a single station carrying a disproportionate
share of its traffic — the network is structurally well-distributed by
this measure, which is a real, if less dramatic, result worth reporting
as-is rather than searching for a more dramatic number.

### Busiest origin-destination corridors

Which exact station pairs have the most distinct trains running
directly between them — the routes with the most redundancy/competition,
as opposed to routes served by only one or two trains:

![Busiest corridors](charts/busiest_corridors.png)

| Route | Trains |
|---|---:|
| Chennai Beach → Velachery | 70 |
| Lingampalli → Kacheguda Falaknuma | 30 |
| Chennai Beach → Tambaram | 29 |
| Kacheguda Falaknuma → Lingampalli | 28 |
| Hyderabad Deccan → Lingampalli | 26 |

The top of this list is dominated by suburban EMU corridors (Chennai,
Hyderabad), not the long-distance expresses that dominate the
chokepoint/gateway lists above — a genuinely different slice of the
network, and a sanity check that the query is measuring what it claims
to (short, high-frequency commuter routes look different from
long-haul trunk routes, as they should).

### Gateway stations (cross-zone connectivity hubs)

Different from the chokepoint metric above (which measures raw
pass-through volume), this measures how many **distinct railway zones**
have trains converging at a station — a proxy for structural
importance to inter-zone travel specifically, not just general traffic:

![Gateway stations](charts/gateway_stations.png)

| Station | Code | Distinct zones | Distinct trains |
|---|---|---:|---:|
| Itarsi Jn | ET | 16 | 293 |
| Bhopal Jn | BPL | 16 | 233 |
| Bhusaval Jn | BSL | 16 | 230 |
| Diva | DIVA | 16 | 228 |
| Bina Jn | BINA | 16 | 222 |

Itarsi, Bhopal, and Bhusaval are well-known real junctions on India's
north-south and east-west trunk routes, which is a reasonable
plausibility check that this query is finding real structural hubs and
not an artifact of the data.

## Frontend Dashboard

A Streamlit dashboard (`frontend/app.py`) turns the static results into
something clickable: benchmark results with sortable tables and
charts, the insight/network analysis above, the write-path
comparison, and a **live Query-2 lookup** (station + time window) that
runs directly against MySQL if a connection is available (using the
same `MYSQL_*` settings as the scripts) — falling back gracefully to
"no DB connection" if not.

```
pip install -r frontend/requirements.txt
streamlit run frontend/app.py
```

Tabs: **Benchmark Results** · **Chokepoint Insights** · **Write-Path** · **Live Lookup**

## Presentation

A self-contained, dependency-free slide deck (`presentation/index.html`)
walks through the problem, method, results, and insights — open it
directly in any browser (arrow keys or the Prev/Next buttons to
navigate). Regenerate it any time with:

```
python scripts/make_presentation.py
```

### Reproducing

```
python scripts/run_all.py            # runs all 7 case studies (about 15 minutes), writes queries/, plans/, benchmark/results.json
python scripts/insights.py           # runs the network/insight queries, writes benchmark/insights.json
python scripts/make_chart.py         # regenerates the benchmark charts
python scripts/make_insight_charts.py  # regenerates the insight charts
python scripts/write_path_bench.py
python scripts/make_presentation.py  # regenerates presentation/index.html
```
