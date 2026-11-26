"""
把儀表板頁面（dashboard/index.html，原本給 claude.ai 用）包成一般網站可以直接開的靜態頁：
補上它需要的執行環境（dash.data / dash.draw / dash.colors）、配色變數（含深色模式）與 d3，資料改成讀 data/*.json。

用法: python3 -I scripts/build_site.py dashboard site
輸出: site/index.html、site/data/{daily,events,summary,status,posts}.json、
      site/card.js、site/card.html（產生連結預覽圖用）、site/og/.target（預覽圖檔名，排程用 Chrome 截圖後刪掉）
"""
import sys, os, shutil, json, hashlib, html

SRC, OUT = sys.argv[1], sys.argv[2]
NAMES = ["daily", "events", "summary", "status", "posts"]
page = open(os.path.join(SRC, "index.html"), encoding="utf-8").read()
SITE_URL = os.environ.get("SITE_URL", "https://triekai.github.io/ptt-indicator/")
# 瀏覽人數統計（GoatCounter，不用 cookie）：填上站台代號（<code>.goatcounter.com 的 code）才會啟用；空字串＝不統計
GOATCOUNTER = os.environ.get("GOATCOUNTER", "")

# ---------- 今日圖卡：連結預覽（og:image）----------
load = lambda n: json.load(open(os.path.join(SRC, "data", f"{n}.json"), encoding="utf-8"))["rows"]
status, summary, daily = load("status"), load("summary"), load("daily")
CARD = {"status": status, "daily": daily[-1], "summary": [r for r in summary if r["signal"] == "thermo95" and r["index"] == "TAIEX"]}
card_json = json.dumps(CARD, ensure_ascii=False, separators=(",", ":"))
# 圖檔固定叫 og/today.png，網址後面加 ?v=（跟著「資料＋畫法」變）：社群網站的預覽快取會換新圖，
# 以前分享出去的連結指向的檔案也一直存在，不會變成破圖
OG_NAME = "og/today.png"
OG_VER = hashlib.sha1((card_json + open(os.path.join(SRC, "card.js"), encoding="utf-8").read()).encode()).hexdigest()[:10]
st = {r["signal"]: r for r in status}
t = st["thermo"]["value"]
level = "極度恐慌" if t >= 95 else "恐慌" if t >= 90 else "偏恐慌" if t >= 85 else "留意" if t >= 80 else "平常"
og_title = f"鄉民恐慌溫度 {t:.1f}（{level}）｜台股落底訊號回測"
og_desc = (f"落底 {st['score']['value']}/7・過熱 {st['gscore']['value']}/8・偏空 {st['wscore']['value']}/3"
           + ("・雙重確認今天亮燈" if st["dual"]["value"] == 1 else "")
           + f"（資料日 {st['thermo']['asof'].replace('-', '/')}）。PTT 股票版恐慌溫度與落底訊號的歷史回測；歷史統計不代表未來，也不是投資建議。")
e = lambda x: html.escape(x, quote=True)
OG = f"""<meta property="og:type" content="website">
<meta property="og:site_name" content="台股落底訊號回測">
<meta property="og:locale" content="zh_TW">
<meta property="og:url" content="{e(SITE_URL)}">
<meta property="og:title" content="{e(og_title)}">
<meta property="og:description" content="{e(og_desc)}">
<meta property="og:image" content="{e(SITE_URL + OG_NAME + "?v=" + OG_VER)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(og_title)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(og_title)}">
<meta name="twitter:description" content="{e(og_desc)}">
<meta name="twitter:image" content="{e(SITE_URL + OG_NAME + "?v=" + OG_VER)}">
"""
FONTS = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&display=swap">"""
card_js = card_json.replace("</", "<\\/")   # 避免資料裡的 </ 提前結束 <script>
CARD_HTML = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex">
<title>今日圖卡</title>
{FONTS}
<style>html, body {{ margin: 0; background: #fff; }} canvas {{ display: block; width: 1200px; height: 630px; }}</style>
<script src="card.js"></script>
</head>
<body>
<canvas id="c" width="1200" height="630"></canvas>
<script>
const D = {card_js};
(async () => {{
  const m = LBCard.model(D.status, D.daily, D.summary);
  await LBCard.fontsReady(m);
  LBCard.draw(document.getElementById('c'), m, 1);
  document.title = 'ready';
}})();
</script>
</body>
</html>
"""

HEAD = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>台股落底訊號回測</title>
<meta name="description" content="PTT 股票版鄉民恐慌溫度、落底與過熱分數，以及歷史回測。">
%OG%<meta name="theme-color" content="#e8eaee" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0f1113" media="(prefers-color-scheme: dark)">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='13' fill='%232456ad'/%3E%3Ccircle cx='16' cy='16' r='5.5' fill='%23fff'/%3E%3C/svg%3E">
%FONTS%
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script src="card.js"></script>
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
    gc_head = (f'<script data-goatcounter="https://{GOATCOUNTER}.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>\n'
               if GOATCOUNTER else "")
    gc_note = "本站用 GoatCounter 統計瀏覽次數，不使用 cookie、不收集個人資料。<br>\n  " if GOATCOUNTER else ""
    f.write(HEAD.replace("%NAMES%", str(NAMES)).replace("%OG%", OG).replace("%FONTS%", FONTS).replace("</head>", gc_head + "</head>")
            + page + FOOT.replace("  資料來源：", "  " + gc_note + "資料來源：", 1))
shutil.copyfile(os.path.join(SRC, "card.js"), os.path.join(OUT, "card.js"))
open(os.path.join(OUT, "card.html"), "w", encoding="utf-8").write(CARD_HTML)
os.makedirs(os.path.join(OUT, "og"), exist_ok=True)
open(os.path.join(OUT, "og", ".target"), "w").write(OG_NAME)
for n in NAMES:
    shutil.copyfile(os.path.join(SRC, "data", f"{n}.json"), os.path.join(OUT, "data", f"{n}.json"))
open(os.path.join(OUT, ".nojekyll"), "w").close()
print("site written:", OUT, sum(os.path.getsize(os.path.join(OUT, "data", f"{n}.json")) for n in NAMES) // 1024, "KB data")
