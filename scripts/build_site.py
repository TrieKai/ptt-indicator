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
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<style>
  :root {
    --color-bg: #ffffff; --color-fg: #1f1f1e; --color-fg-muted: #6b6b68; --color-panel: #f5f5f2; --color-border-line: #e0e0da;
    --color-bad: #c8312b; --color-ok: #1f7a45; --color-warn: #b86a00;
    --cds-chart-grid: #e6e6e1; --cds-chart-axis: #8a8a85; --cds-chart-reference: #9a9a95; --cds-chart-muted: #bdbdb7;
    --cds-surface-popover: #ffffff; --cds-border: #dcdcd6; --cds-text-secondary: #6b6b68; --cds-shadow-popover: 0 4px 16px rgba(0,0,0,.12);
    --cds-gap-xs: 4px; --cds-gap-sm: 8px; --cds-gap-md: 12px; --cds-gap-lg: 16px; --cds-gap-xl: 28px;
    --cds-pad-sm: 6px; --cds-pad-md: 10px; --cds-pad-lg: 16px; --cds-radius: 8px;
    --cds-font-size-caption: 12.5px; --cds-font-size-body: 15px; --cds-font-size-heading: 18px; --cds-font-size-title: 26px; --cds-font-weight-medium: 600;
    --font-anthropic-sans: system-ui, -apple-system, "PingFang TC", "Noto Sans TC", "Microsoft JhengHei", sans-serif;
    --font-anthropic-serif: "Noto Serif TC", "Songti TC", "PMingLiU", serif;
    color-scheme: light;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --color-bg: #1c1c1b; --color-fg: #ecece8; --color-fg-muted: #a3a39e; --color-panel: #262624; --color-border-line: #3a3a37;
      --color-bad: #ff6b63; --color-ok: #4cc38a; --color-warn: #f0a43a;
      --cds-chart-grid: #333331; --cds-chart-axis: #8f8f8a; --cds-chart-reference: #8f8f8a; --cds-chart-muted: #4d4d4a;
      --cds-surface-popover: #2a2a28; --cds-border: #44443f; --cds-text-secondary: #a3a39e; --cds-shadow-popover: 0 4px 16px rgba(0,0,0,.5);
      color-scheme: dark;
    }
  }
  html, body { background: var(--color-bg); color: var(--color-fg); }
  body { margin: 0 auto; max-width: 1180px; padding: 20px 16px 40px; font-family: var(--font-anthropic-sans); font-size: var(--cds-font-size-body); }
  a { color: inherit; }
  .dash-select { font: inherit; font-size: var(--cds-font-size-caption); color: var(--color-fg); background: var(--color-panel);
                 border: 1px solid var(--color-border-line); border-radius: var(--cds-radius); padding: 4px 8px; }
  .dash-skeleton { min-height: 120px; }
  table { font-variant-numeric: tabular-nums; }
  .site-foot { margin-top: 32px; font-size: var(--cds-font-size-caption); color: var(--color-fg-muted); line-height: 1.6; }
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
  window.addEventListener('resize', (() => { let h; return () => { clearTimeout(h); h = setTimeout(() => ['chart', 'thermo-chart'].forEach(redraw), 200); }; })());
})();
</script>
</head>
<body>
"""

FOOT = """
<footer class="site-foot">
  資料產生時間：<span id="site-updated">—</span>（台灣時間）。收盤資料每天 15:40（平日）、22:10 自動更新；PTT 文章的更新時間見溫度計旁的說明。<br>
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
