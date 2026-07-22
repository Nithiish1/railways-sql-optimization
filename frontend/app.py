"""
Streamlit dashboard for the Indian Railways SQL Optimization project.

Two modes:
- If a live MySQL connection is available (same creds as scripts/run_all.py),
  Q3 (station + time-window lookup) runs live against the real database.
- Everything else (benchmark results, insights) reads from the committed
  JSON files in benchmark/, so the dashboard works even without a DB
  connection (e.g. when deployed to Streamlit Cloud).

Run: streamlit run frontend/app.py
"""
import json
import os

import pandas as pd
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="Indian Railways SQL Optimization", page_icon="🚆", layout="wide")

st.title("🚆 Indian Railways SQL Optimization — Dashboard")
st.caption(
    "A query-optimization case study on a real 417K-row Indian Railways dataset. "
    "10 queries diagnosed and fixed with EXPLAIN ANALYZE, plus chokepoint/insight analysis."
)


@st.cache_data
def load_json(name):
    with open(os.path.join(ROOT, "benchmark", name)) as f:
        return json.load(f)


results = load_json("results.json")
write_path = load_json("write_path_results.json")
try:
    insights = load_json("insights.json")
except FileNotFoundError:
    insights = None

tab1, tab2, tab3, tab4 = st.tabs(["📊 Benchmark Results", "🔎 Chokepoint Insights", "✍️ Write-Path", "🚉 Live Lookup"])

with tab1:
    st.subheader("Before vs After — all 10 query case studies")
    df = pd.DataFrame(results)
    df_display = df[["n", "title", "technique", "before_ms", "after_ms", "speedup"]]
    df_display.columns = ["#", "Query", "Technique", "Before (ms)", "After (ms)", "Speedup"]
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    chart_df = pd.DataFrame({
        "Query": [f"Q{r['n']}" for r in results],
        "Before (ms)": [r["before_ms"] for r in results],
        "After (ms)": [r["after_ms"] for r in results],
    }).set_index("Query")
    st.bar_chart(chart_df, height=380)

    st.markdown(
        "Three queries (**Q1, Q4, Q9**) show little or no improvement — "
        "documented on purpose. See the README's *Reading the Results Honestly* "
        "section for why."
    )

with tab2:
    if insights is None:
        st.warning("Run `python scripts/insights.py` first to generate benchmark/insights.json.")
    else:
        st.subheader("Chokepoint stations (structural single points of failure)")
        st.caption(
            "Stations where the most distinct trains merely PASS THROUGH "
            "(not origin/destination) — if disrupted, the most journeys that "
            "don't even start or end there are affected."
        )
        cp_df = pd.DataFrame(insights["chokepoint_stations"])
        st.dataframe(cp_df, use_container_width=True, hide_index=True)
        st.image("charts/chokepoint_stations.png")

        st.subheader("Most schedule-inconsistent trains")
        st.caption("Highest halt-time standard deviation across a train's own stops (overnight-corrected).")
        st.image("charts/unstable_trains.png")

        st.subheader("Zone traffic concentration")
        st.caption(
            "% of each zone's total train-stops running through its single busiest station. "
            "Max concentration found is ~1.6% — the network turns out to be well distributed, "
            "no zone has a dominant single-station bottleneck by this measure."
        )
        st.image("charts/zone_concentration.png")

        st.subheader("Longest single-train routes")
        st.caption("Longest end-to-end journeys — most exposed to any single delay compounding.")
        lr_df = pd.DataFrame(insights["longest_routes"])
        st.dataframe(lr_df, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Write-path optimization: insert strategy")
    wp_df = pd.DataFrame({
        "Strategy": ["Row-by-row (autocommit)", "Row-by-row (1 transaction)", "Bulk (executemany)"],
        "Time (ms)": [
            write_path["row_by_row_autocommit_ms"],
            write_path["row_by_row_single_txn_ms"],
            write_path["bulk_executemany_ms"],
        ],
    }).set_index("Strategy")
    st.bar_chart(wp_df, height=300)
    st.metric("Bulk vs autocommit speedup", f"{write_path['speedup_bulk_vs_autocommit']}x")

with tab4:
    st.subheader("Live lookup (Query 3): trains through a station in a time window")
    st.caption("Runs directly against MySQL if a local connection is available.")
    station_code = st.text_input("Station code", value="CNB")
    col1, col2 = st.columns(2)
    start = col1.time_input("From")
    end = col2.time_input("To")

    if st.button("Run query"):
        try:
            import pymysql
            conn = pymysql.connect(host="localhost", user="root", password="root",
                                    port=3306, database="indian_railways")
            cur = conn.cursor(pymysql.cursors.DictCursor)
            cur.execute(
                "SELECT train_number, train_name, arrival, departure FROM schedules "
                "WHERE station_code = %s AND arrival BETWEEN %s AND %s ORDER BY arrival",
                (station_code, start, end),
            )
            rows = cur.fetchall()
            conn.close()
            if rows:
                df = pd.DataFrame(rows)

                def fmt_time(v):
                    if v is None or pd.isna(v):
                        return None
                    total_seconds = int(v.total_seconds())
                    h, rem = divmod(total_seconds, 3600)
                    m, s = divmod(rem, 60)
                    return f"{h:02d}:{m:02d}:{s:02d}"

                df["arrival"] = df["arrival"].apply(fmt_time)
                df["departure"] = df["departure"].apply(fmt_time)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No trains found for that station/time window.")
        except Exception as e:
            st.error(f"Could not reach a local MySQL instance ({e}). This tab needs a live DB connection.")

st.divider()
st.caption("Source: [github.com/Nithiish1/railways-sql-optimization](https://github.com/Nithiish1/railways-sql-optimization)")
