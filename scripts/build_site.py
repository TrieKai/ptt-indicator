"""
把儀表板頁面（dashboard/index.html，原本給 claude.ai 用）包成一般網站可以直接開的靜態頁：
補上它需要的執行環境（dash.data / dash.draw / dash.colors）、配色變數（含深色模式）與 d3，資料改成讀 data/*.json。

用法: python3 -I scripts/build_site.py dashboard site
輸出: site/index.html、site/data/{daily,events,summary,status,posts}.json
"""
import sys, os, shutil

SRC, OUT = sys.argv[1], sys.argv[2]
NAMES = ["daily", "events", "summary", "status", "posts"]
page = open(os.path.join(SRC, "index.html"), encoding="utf-8").read()

HEAD = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>台股落底訊號回測</title>
<meta name="description" content="PTT 股票版鄉民恐慌溫度、落底與過熱分數，以及歷史回測。">
<meta name="theme-color" content="#e8eaee" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0f1113" media="(prefers-color-scheme: dark)">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='13' fill='%232456ad'/%3E%3Ccircle cx='16' cy='16' r='5.5' fill='%23fff'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&display=swap">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<style>
  /* 版面與配色都在 dashboard/index.html 裡；這裡只放載入前的底色，避免閃白 */
  html, body { margin: 0; background: #e8eaee; color: #1c1f24; }
  @media (prefers-color-scheme: dark) { html, body { background: #0f1113; color: #e8eaed; } }
  .dash-skeleton { min-height: 120px; }
</style>
<script>
(() => {
  const NAMES = %NAMES%, store = {}, fns = {};
  NAMES.forEach((n) => { store[n] = { status: 'loading' }; });
  const redraw = (n) => {
    const f = fns[n]; if (!f) return;
    document.querySelectorAll('[data-draw="' + n + '"]').forEach((el) => { try { f(el); } catch (e) { console.error('draw ' + n, e); } });
  };
  window.dash = {
    colors: ['#3b6fd0', '#7a5bd6', '#d0553b', '#2a9d8f', '#e9a23b', '#8a8a8a', '#b5477d', '#5c8a2a', '#4aa0c9'],
    data: (n) => store[n] || { status: 'error' },
    draw(n, fn) { if (fn) fns[n] = fn; if (document.readyState !== 'loading' || !fn) redraw(n); },
  };
  const load = (n) => fetch('data/' + n + '.json', { cache: 'no-cache' })
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(n + ' ' + r.status))))
    .then((j) => { store[n] = { status: 'ok', data: j.rows, meta: j.meta }; })
    .catch((e) => { console.error(e); store[n] = { status: 'error' }; });
  const ready = new Promise((res) => (document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', res) : res()));
  Promise.all([ready, ...NAMES.map(load)]).then(() => {
    Object.keys(fns).forEach(redraw);
    let t = (store.daily.meta || []).find((m) => m.label === '產生時間');
    const el = document.getElementById('site-updated'); if (el && t) el.textContent = t.value;
  });
  window.addEventListener('resize', (() => { let h, w = window.innerWidth; return () => { if (window.innerWidth === w) return; w = window.innerWidth; clearTimeout(h); h = setTimeout(() => ['chart', 'thermo-chart', 'excess-bars', 'timing'].forEach(redraw), 200); }; })());
})();
</script>
</head>
<body>
"""

FOOT = """
<footer class="site-foot">
  資料產生時間：<span id="site-updated">—</span>（台灣時間）。收盤資料每天 15:40（平日）、22:10 自動更新；PTT 文章的更新時間見頁首。<br>
  資料來源：證交所、櫃買中心、期交所、FinMind、CBOE、PTT 股票版（只看標題）。程式自動計算，可能有誤；歷史統計不代表未來，也不是投資建議。
</footer>
</body>
</html>
"""

os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
    f.write(HEAD.replace("%NAMES%", str(NAMES)) + page + FOOT)
for n in NAMES:
    shutil.copyfile(os.path.join(SRC, "data", f"{n}.json"), os.path.join(OUT, "data", f"{n}.json"))
open(os.path.join(OUT, ".nojekyll"), "w").close()
print("site written:", OUT, sum(os.path.getsize(os.path.join(OUT, "data", f"{n}.json")) for n in NAMES) // 1024, "KB data")
