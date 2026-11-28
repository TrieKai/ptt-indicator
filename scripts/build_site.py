"""
把儀表板頁面（dashboard/index.html，原本給 claude.ai 用）包成一般網站可以直接開的靜態頁：
補上它需要的執行環境（dash.data / dash.draw / dash.colors）、配色變數（含深色模式）與 d3，資料改成讀 data/*.json。

用法: python3 -I scripts/build_site.py dashboard site
輸出: site/index.html、site/data/{daily,events,summary,status,posts}.json、
      site/card.js、site/card.html（產生連結預覽圖用）、site/og/.target（預覽圖檔名，排程用 Chrome 截圖後刪掉）
"""
import sys, os, shutil, json, hashlib, html, re

SRC, OUT = sys.argv[1], sys.argv[2]
NAMES = ["daily", "events", "summary", "status", "posts"]
page = open(os.path.join(SRC, "index.html"), encoding="utf-8").read()
SITE_URL = os.environ.get("SITE_URL", "https://triekai.github.io/ptt-indicator/")
# 瀏覽人數統計（GoatCounter，不用 cookie）：填上站台代號（<code>.goatcounter.com 的 code）才會啟用；空字串＝不統計
GOATCOUNTER = os.environ.get("GOATCOUNTER", "")

# ---------- 今日圖卡：連結預覽（og:image）----------
def load(name):
    with open(os.path.join(SRC, "data", f"{name}.json"), encoding="utf-8") as f:
        return json.load(f)

status_data = load("status")
status, summary, daily = status_data["rows"], load("summary")["rows"], load("daily")["rows"]
CARD = {"status": status, "daily": daily[-1], "summary": [r for r in summary if r["signal"] == "thermo95" and r["index"] == "TAIEX"]}
card_json = json.dumps(CARD, ensure_ascii=False, separators=(",", ":"))
# 圖檔固定叫 og/today.png，網址後面加 ?v=（跟著「資料＋畫法」變）：社群網站的預覽快取會換新圖，
# 以前分享出去的連結指向的檔案也一直存在，不會變成破圖
OG_NAME = "og/today.png"
OG_VER = hashlib.sha1((card_json + open(os.path.join(SRC, "card.js"), encoding="utf-8").read()).encode()).hexdigest()[:10]
st = {r["signal"]: r for r in status}
t = st["thermo"]["value"]
levels = [(0, "平常", "<80"), (80, "留意", "80–85"), (85, "偏恐慌", "85–90"), (90, "恐慌", "90–95"), (95, "極度恐慌", "≥95")]
limit, level, level_range = next(row for row in reversed(levels) if t >= row[0])
og_title = f"鄉民恐慌溫度 {t:.1f}（{level}）｜台股落底訊號回測"
dual = st["dual"]
dual_today = "成立" if dual["value"] == 1 else "未成立"
dual_recent = "（近 5 個交易日曾亮燈）" if dual["value"] == 0 and dual["lit5"] == 1 else ""
og_desc = (f"雙重確認本交易日{dual_today}{dual_recent}・偏空警示近 5 個交易日 {st['wscore']['value']}/3 項。"
           f"收盤資料日 {st['thermo']['asof'].replace('-', '/')}。歷史統計不代表未來，也不是投資建議。")
e = lambda x: html.escape(x, quote=True)

def seed_today(page):
    thermo = st["thermo"]
    date = lambda value: value.replace("-", "/") if value else "無"
    stamp = "收盤資料日 " + date(thermo["asof"])
    if thermo.get("ptt_asof"):
        stamp += "・PTT 文章至 " + date(thermo["ptt_asof"][5:])
    stamp = e(stamp)
    if thermo.get("ptt_lag_h", 0) > 3:
        stamp += f'<small class="lb-stamp-note">最新文章距資料產生逾 {int(thermo["ptt_lag_h"])} 小時</small>'
    scale = "".join(
        ("<li class=\"is-now\" aria-current=\"true\">" if threshold == limit else "<li>")
        + f'<i class="lamp lamp--bottom" data-s="{"on" if threshold == limit else "off"}" aria-hidden="true"></i>'
        + f"<b>{e(label)}</b><span>{e(bounds)}</span></li>"
        for threshold, label, bounds in levels
    )
    values = {
        "stamp": stamp,
        "thermo-val": f"{t:.1f}",
        "thermo-chip": e(f"{level}（{level_range}）"),
        "thermo-scale": scale,
        "thermo-c5": str(thermo["c5"]),
        "thermo-l5": str(thermo["l5"]),
        "thermo-asof": e("上次 ≥95：" + date(thermo["last_lit"])),
        "dual-pill": "本交易日" + dual_today,
        "dual-recent": "近 5 個交易日曾亮燈" if dual_recent else "",
        "sc-wscore": str(st["wscore"]["value"]),
    }
    for key, value in values.items():
        tag = rf'(<(?P<tag>[a-z]+)\b[^>]*\bdata-draw="{key}"[^>]*>)[^<]*(</(?P=tag)>)'
        page = re.sub(tag, lambda m: m[1] + value + m[3], page)
    page = page.replace(' data-draw="reading-status"', ' hidden data-draw="reading-status"', 1)
    if t >= 90:
        page = page.replace(' data-draw="thermo-chip"', ' data-tone="bottom" data-draw="thermo-chip"', 1)
    if dual["value"] == 1:
        page = page.replace(' data-draw="dual-pill"', ' data-tone="bottom" data-draw="dual-pill"', 1)
    dual_lamp = "on" if dual["value"] else "recent" if dual["lit5"] else "off"
    warn_today = any(daily[-1].get(f"f_{sig}") == 1 for sig in ("fut_short", "fut_ratio_short", "fut_chg_short"))
    warn_lamp = "on" if warn_today else "recent" if st["wscore"]["value"] else "off"
    for key, lamp in [("dual-lamp", dual_lamp), ("warn-lamp", warn_lamp)]:
        page = page.replace(f'data-draw="{key}" data-source="status" data-s="missing"', f'data-draw="{key}" data-source="status" data-s="{lamp}"')
    return page

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
<meta name="description" content="PTT 股票版鄉民恐慌溫度、雙重確認、偏空警示與歷史回測。">
%OG%<meta name="theme-color" content="#e8eaee" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0f1113" media="(prefers-color-scheme: dark)">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='13' fill='%232456ad'/%3E%3Ccircle cx='16' cy='16' r='5.5' fill='%23fff'/%3E%3C/svg%3E">
%FONTS%
<style>
  /* 版面與配色都在 dashboard/index.html 裡；這裡只放載入前的底色，避免閃白 */
  html, body { margin: 0; background: #e8eaee; color: #1c1f24; }
  @media (prefers-color-scheme: dark) { html, body { background: #0f1113; color: #e8eaed; } }
  .dash-skeleton { min-height: 120px; }
</style>
<script>
(() => {
  const NAMES = %NAMES%, today = %TODAY%;
  const store = Object.fromEntries(NAMES.map((name) => [name, { status: 'idle' }]));
  store.status = { status: 'ok', data: today.status };
  const renderers = new Map(), bindings = [], groups = new Map();
  const requests = new Map(), scripts = new Map();
  let chartState = 'idle';

  const render = (binding) => {
    if (!binding.group.active || (binding.chart && chartState !== 'ok')) return;
    if (binding.name !== 'reading-status' && binding.sources.some((n) => ['idle', 'loading'].includes(store[n].status))) return;
    try { renderers.get(binding.name)?.(binding.el); }
    catch (error) { console.error('draw ' + binding.name, error); }
  };
  const drawNamed = (name) => bindings.filter((binding) => binding.name === name).forEach(render);
  const showGroupStatus = (group) => {
    if (!group.status || !group.active) return;
    const loading = [...group.sources].some((n) => ['idle', 'loading'].includes(store[n].status)) || (group.charts && chartState === 'loading');
    const failed = [...group.sources].filter((n) => store[n].status === 'error');
    const chartFailed = group.charts && chartState === 'error';
    group.status.hidden = !loading && !failed.length && !chartFailed;
    group.status.classList.toggle('lb-err', !!failed.length || chartFailed);
    group.status.replaceChildren();
    if (loading) { group.status.textContent = '正在載入這個區段…'; return; }
    if (!failed.length && !chartFailed) return;
    group.status.textContent = chartFailed ? '圖表程式暫時無法載入。' : '這個區段有資料暫時無法載入。';
    const retry = document.createElement('button');
    retry.type = 'button'; retry.className = 'lb-btn'; retry.textContent = '重試載入';
    retry.addEventListener('click', () => {
      failed.forEach(load);
      if (chartFailed) loadCharts();
    });
    group.status.append(retry);
  };
  const notify = (source) => {
    bindings.filter((binding) => source === 'charts' ? binding.chart : binding.sources.includes(source)).forEach(render);
    groups.forEach((group) => {
      if (source === 'charts' ? group.charts : group.sources.has(source)) showGroupStatus(group);
    });
  };
  const load = (n) => {
    if (!NAMES.includes(n)) return;
    if (requests.has(n)) return requests.get(n);
    store[n] = { status: 'loading' };
    notify(n);
    const request = fetch('data/' + n + '.json', { cache: 'no-cache' })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(n + ' ' + r.status))))
      .then((j) => {
        if (!Array.isArray(j.rows)) throw new Error(n + ' data is missing rows');
        store[n] = { status: 'ok', data: j.rows, meta: j.meta, windows: j.windows };
      })
      .catch((e) => { console.error(e); store[n] = { status: 'error' }; })
      .finally(() => { requests.delete(n); notify(n); });
    requests.set(n, request);
    return request;
  };
  const loadScript = (src, ready) => {
    if (!scripts.has(src)) {
      const script = document.createElement('script');
      script.src = src;
      const pending = new Promise((resolve, reject) => {
        const fail = () => {
          script.remove(); scripts.delete(src);
          reject(new Error('程式載入失敗，請稍候再試'));
        };
        script.onload = () => ready() ? resolve() : fail();
        script.onerror = fail;
      });
      scripts.set(src, pending);
      document.head.append(script);
    }
    return scripts.get(src);
  };
  const loadCharts = () => {
    if (chartState === 'loading' || chartState === 'ok') return;
    chartState = 'loading';
    notify('charts');
    loadScript('https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js', () => window.d3)
      .then(() => { chartState = 'ok'; }, () => { chartState = 'error'; })
      .finally(() => notify('charts'));
  };
  const activate = (root) => {
    const group = groups.get(root);
    if (!group || group.active) return;
    group.active = true;
    group.sources.forEach((n) => { if (store[n].status === 'idle') load(n); });
    if (group.charts && chartState === 'idle') loadCharts();
    group.bindings.forEach(render);
    showGroupStatus(group);
  };
  const openSection = (id) => {
    const target = document.getElementById(id);
    if (target) activate(target.closest('section') || target);
  };
  const openAnchor = () => openSection(location.hash.slice(1));
  window.dash = {
    colors: ['#3b6fd0', '#7a5bd6', '#d0553b', '#2a9d8f', '#e9a23b', '#8a8a8a', '#b5477d', '#5c8a2a', '#4aa0c9'],
    today,
    data: (n) => store[n] || { status: 'error' },
    draw(n, fn) { if (fn) renderers.set(n, fn); drawNamed(n); },
    openSection, reload: load,
    loadCard: () => window.LBCard ? Promise.resolve() : loadScript('card.js', () => window.LBCard),
  };
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-draw]').forEach((el) => {
      const section = el.closest('section');
      const root = el.closest('details') || (section?.id !== 'lb-today' ? section : null);
      if (!groups.has(root)) groups.set(root, { active: false, charts: false, sources: new Set(), bindings: [] });
      const group = groups.get(root);
      const sources = el.dataset.source.split(' ').filter((name) => NAMES.includes(name));
      const chart = el.classList.contains('lb-chart');
      const binding = { el, group, sources, chart, name: el.dataset.draw };
      sources.forEach((name) => group.sources.add(name));
      group.charts ||= chart;
      group.bindings.push(binding);
      bindings.push(binding);
    });
    activate(null);
    const observer = 'IntersectionObserver' in window ? new IntersectionObserver((entries) => entries.forEach((entry) => {
      if (entry.isIntersecting) { observer.unobserve(entry.target); activate(entry.target); }
    }), { rootMargin: '96px 0px' }) : null;
    groups.forEach((group, root) => {
      if (!root) return;
      group.status = document.createElement('p');
      group.status.className = 'lb-cap lb-load-state';
      group.status.setAttribute('role', 'status');
      group.status.hidden = true;
      root.firstElementChild.after(group.status);
      if (root.tagName === 'DETAILS') {
        root.addEventListener('toggle', () => { if (root.open) activate(root); });
        if (root.open) activate(root);
      } else if (observer) observer.observe(root);
      else activate(root);
    });
    openAnchor();
  }, { once: true });
  window.addEventListener('hashchange', openAnchor);
  window.addEventListener('resize', (() => { let h, w = window.innerWidth; return () => { if (window.innerWidth === w) return; w = window.innerWidth; clearTimeout(h); h = setTimeout(() => bindings.filter((binding) => binding.chart).forEach(render), 200); }; })());
})();
</script>
</head>
<body>
"""

FOOT = """
<footer class="site-foot">
  資料產生時間：<span id="site-updated">—</span>（台灣時間）。收盤資料每天 15:40（平日）、22:10 自動更新；PTT 文章的更新時間見頁首。<br>
  資料來源：證交所、櫃買中心、期交所、FinMind、CBOE、PTT 股票版。畢業／虧損文另由 AI 讀內文確認。程式自動計算，可能有誤；歷史統計不代表未來，也不是投資建議。
</footer>
</body>
</html>
"""

os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
    gc_head = (f'<script data-goatcounter="https://{GOATCOUNTER}.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>\n'
               if GOATCOUNTER else "")
    gc_note = "本站用 GoatCounter 統計瀏覽次數，不使用 cookie、不收集個人資料。<br>\n  " if GOATCOUNTER else ""
    generated = next((item["value"] for item in status_data.get("meta", []) if item["label"] == "產生時間"), "—")
    f.write(HEAD.replace("%NAMES%", json.dumps(NAMES)).replace("%OG%", OG).replace("%FONTS%", FONTS)
            .replace("%TODAY%", card_js).replace("</head>", gc_head + "</head>")
            + seed_today(page) + FOOT.replace("  資料來源：", "  " + gc_note + "資料來源：", 1)
            .replace('<span id="site-updated">—</span>', f'<span id="site-updated">{e(generated)}</span>'))
shutil.copyfile(os.path.join(SRC, "card.js"), os.path.join(OUT, "card.js"))
open(os.path.join(OUT, "card.html"), "w", encoding="utf-8").write(CARD_HTML)
os.makedirs(os.path.join(OUT, "og"), exist_ok=True)
open(os.path.join(OUT, "og", ".target"), "w").write(OG_NAME)
for n in NAMES:
    shutil.copyfile(os.path.join(SRC, "data", f"{n}.json"), os.path.join(OUT, "data", f"{n}.json"))
open(os.path.join(OUT, ".nojekyll"), "w").close()
print("site written:", OUT, sum(os.path.getsize(os.path.join(OUT, "data", f"{n}.json")) for n in NAMES) // 1024, "KB data")
