"""Builds a self-contained slide-deck HTML (presentation/index.html) with all
chart PNGs embedded as base64 data URIs, so it works standalone with no
external dependencies or relative-path issues."""
import base64
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARTS = os.path.join(ROOT, "charts")


def img_b64(name):
    with open(os.path.join(CHARTS, name), "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


with open(os.path.join(ROOT, "benchmark", "results.json")) as f:
    results = json.load(f)

charts = {
    name: img_b64(name)
    for name in [
        "dataset_overview.png",
        "before_after_benchmark.png",
        "speedup_ranking.png",
        "chokepoint_stations.png",
        "unstable_trains.png",
        "zone_concentration.png",
        "busiest_corridors.png",
        "gateway_stations.png",
        "write_path_benchmark.png",
    ]
}

results_rows = "\n".join(
    f"<tr><td>Q{r['n']}</td><td>{r['title']}</td><td>{r['technique']}</td>"
    f"<td>{r['before_ms']} ms</td><td>{r['after_ms']} ms</td><td><b>{r['speedup']}x</b></td></tr>"
    for r in results
)

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Indian Railways SQL Optimization</title>
<style>
  :root {{
    --bg: #0f1720; --panel:#16212c; --accent:#2ecc71; --accent2:#3498db;
    --text:#eef2f5; --muted:#9fb1c1; --danger:#e74c3c;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin:0; height:100%; background:var(--bg); color:var(--text);
    font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif; overflow:hidden; }}
  .deck {{ position:relative; width:100vw; height:100vh; }}
  .slide {{
    position:absolute; inset:0; display:none; flex-direction:column;
    justify-content:center; align-items:center; padding: 5vh 8vw;
    text-align:center;
  }}
  .slide.active {{ display:flex; }}
  .slide h1 {{ font-size:2.6rem; margin:0 0 0.4em; }}
  .slide h2 {{ font-size:1.9rem; margin:0 0 0.6em; color:var(--accent2); }}
  .slide p, .slide li {{ font-size:1.15rem; color:var(--muted); line-height:1.5; }}
  .slide .kicker {{ color:var(--accent); font-weight:600; letter-spacing:0.08em; text-transform:uppercase; font-size:0.9rem; margin-bottom:0.6em; }}
  .slide img {{ max-height:56vh; max-width:88vw; border-radius:10px; box-shadow:0 10px 40px rgba(0,0,0,0.5); margin-top: 1em; }}
  .badges span {{ display:inline-block; background:var(--panel); border:1px solid #2a3947; border-radius:20px; padding:0.35em 1em; margin:0.3em; font-size:0.95rem; }}
  table {{ border-collapse: collapse; width: 92vw; max-width:1000px; font-size:0.95rem; }}
  th, td {{ border:1px solid #2a3947; padding:0.5em 0.8em; }}
  th {{ background:var(--panel); color:var(--accent2); }}
  tr:nth-child(even) {{ background:#131e28; }}
  .nav {{ position:fixed; bottom:18px; left:50%; transform:translateX(-50%); display:flex; gap:10px; z-index:10; }}
  .nav button {{ background:var(--panel); color:var(--text); border:1px solid #2a3947; border-radius:8px; padding:8px 16px; cursor:pointer; font-size:0.95rem; }}
  .nav button:hover {{ background:#1e2c39; }}
  .count {{ position:fixed; top:18px; right:24px; color:var(--muted); font-size:0.9rem; }}
  .two-col {{ display:flex; gap:2rem; align-items:center; justify-content:center; width:100%; }}
  .two-col > div {{ flex:1; }}
  ul {{ text-align:left; max-width:700px; }}
  .highlight-red {{ color:var(--danger); font-weight:600; }}
  .highlight-green {{ color:var(--accent); font-weight:600; }}
</style>
</head>
<body>
<div class="deck" id="deck">

  <div class="slide active">
    <div class="kicker">SQL Optimization Case Study</div>
    <h1>🚆 Indian Railways SQL Optimization</h1>
    <p>Diagnosing and fixing slow queries on a real 417,080-row dataset<br>
    with <code>EXPLAIN ANALYZE</code>, indexing, query rewriting, and a materialized-view simulation.</p>
    <div class="badges">
      <span>MySQL 8.0.37</span><span>Python 3.12</span><span>7 case studies</span><span>Best speedup: 183x</span>
    </div>
  </div>

  <div class="slide">
    <div class="kicker">The Problem</div>
    <h2>Real data. Real slowness. Real diagnosis.</h2>
    <ul>
      <li>417,080 schedule rows (train stop records), 8,990 stations, 5,208 trains</li>
      <li>Started with <b>zero indexes</b> beyond primary keys — the honest, naive baseline</li>
      <li>Every "before" number is measured, not assumed — median of 5 timed runs</li>
      <li>Every fix is justified by reading <code>EXPLAIN ANALYZE</code> output first, not guessed</li>
    </ul>
  </div>

  <div class="slide">
    <div class="kicker">Dataset</div>
    <h2>Three tables, one real bottleneck</h2>
    <img src="data:image/png;base64,{charts['dataset_overview.png']}" alt="dataset overview">
  </div>

  <div class="slide">
    <div class="kicker">Method</div>
    <h2>Diagnose → Fix → Verify</h2>
    <ul>
      <li>Run query cold on unindexed table, capture <code>EXPLAIN ANALYZE</code></li>
      <li>Apply one targeted fix: index, rewrite, or summary table</li>
      <li>Re-run, re-capture <code>EXPLAIN ANALYZE</code>, compare</li>
      <li>Document <i>why</i> it worked</li>
    </ul>
  </div>

  <div class="slide">
    <div class="kicker">Results</div>
    <h2>Query Case Studies — Before vs After</h2>
    <img src="data:image/png;base64,{charts['before_after_benchmark.png']}" alt="before after benchmark">
  </div>

  <div class="slide">
    <div class="kicker">Results</div>
    <h2>Ranked by Speedup</h2>
    <img src="data:image/png;base64,{charts['speedup_ranking.png']}" alt="speedup ranking">
  </div>

  <div class="slide">
    <h2>Full Results Table</h2>
    <table>
      <tr><th>#</th><th>Query</th><th>Technique</th><th>Before</th><th>After</th><th>Speedup</th></tr>
      {results_rows}
    </table>
  </div>

  <div class="slide">
    <div class="kicker">Beyond optimization</div>
    <h2>Chokepoint Stations — Structural Single Points of Failure</h2>
    <img src="data:image/png;base64,{charts['chokepoint_stations.png']}" alt="chokepoint stations">
  </div>

  <div class="slide">
    <div class="two-col">
      <div>
        <h2>Schedule Instability</h2>
        <img src="data:image/png;base64,{charts['unstable_trains.png']}" style="max-height:40vh" alt="unstable trains">
      </div>
      <div>
        <h2>Zone Concentration</h2>
        <img src="data:image/png;base64,{charts['zone_concentration.png']}" style="max-height:40vh" alt="zone concentration">
      </div>
    </div>
  </div>

  <div class="slide">
    <div class="kicker">Beyond optimization</div>
    <h2>Busiest Origin-Destination Corridors</h2>
    <img src="data:image/png;base64,{charts['busiest_corridors.png']}" alt="busiest corridors">
  </div>

  <div class="slide">
    <div class="kicker">Beyond optimization</div>
    <h2>Gateway Stations — Cross-Zone Connectivity Hubs</h2>
    <img src="data:image/png;base64,{charts['gateway_stations.png']}" alt="gateway stations">
  </div>

  <div class="slide">
    <div class="kicker">Write-Path</div>
    <h2>Bulk Insert vs Row-by-Row</h2>
    <img src="data:image/png;base64,{charts['write_path_benchmark.png']}" alt="write path benchmark">
  </div>

  <div class="slide">
    <div class="kicker">Live Demo</div>
    <h2>Streamlit Dashboard</h2>
    <p>A deployable frontend (<code>frontend/app.py</code>) turns this repo into something clickable:<br>
    benchmark results, chokepoint insights, write-path chart, and a live Query-3 lookup against MySQL.</p>
    <div class="badges"><span>streamlit run frontend/app.py</span></div>
  </div>

  <div class="slide">
    <div class="kicker">Takeaways</div>
    <h2>What this project actually proves</h2>
    <ul>
      <li>Can read <code>EXPLAIN ANALYZE</code> and diagnose the real bottleneck, not guess</li>
      <li>Applies the right fix for the right problem: indexing, rewriting, or a summary table</li>
      <li>Builds reproducible, measured evidence instead of one-off screenshots</li>
      <li>Scope is honest: single-query latency diagnosis, not concurrency/throughput engineering</li>
    </ul>
    <p style="margin-top:2em;"><a href="https://github.com/Nithiish1/railways-sql-optimization" style="color:var(--accent2)">github.com/Nithiish1/railways-sql-optimization</a></p>
  </div>

</div>
<div class="count"><span id="cur">1</span> / <span id="total"></span></div>
<div class="nav">
  <button onclick="go(-1)">&larr; Prev</button>
  <button onclick="go(1)">Next &rarr;</button>
</div>
<script>
  const slides = document.querySelectorAll('.slide');
  let i = 0;
  document.getElementById('total').textContent = slides.length;
  function show(n) {{
    slides[i].classList.remove('active');
    i = (n + slides.length) % slides.length;
    slides[i].classList.add('active');
    document.getElementById('cur').textContent = i + 1;
  }}
  function go(delta) {{ show(i + delta); }}
  document.addEventListener('keydown', (e) => {{
    if (e.key === 'ArrowRight' || e.key === ' ') go(1);
    if (e.key === 'ArrowLeft') go(-1);
  }});
</script>
</body>
</html>
"""

out_path = os.path.join(ROOT, "presentation", "index.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print("Presentation written to", out_path, f"({len(html)/1024:.0f} KB)")
