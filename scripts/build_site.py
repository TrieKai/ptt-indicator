"""
編譯 TypeScript、驗證資料並建立 GitHub Pages 靜態頁。

用法: python3 -I scripts/build_site.py dashboard site
輸出: site/index.html、site/data/{daily,events,summary,status,posts}.json、
      site/assets/、site/card.js、site/card.html、site/og/.target
"""
import sys, os, shutil, json, hashlib, html, re, subprocess
from pathlib import Path

SRC, OUT = sys.argv[1], sys.argv[2]
ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "dashboard" / ".build"
subprocess.run(["node", "scripts/validate-dashboard-data.mjs", str(Path(SRC, "data").resolve())], cwd=ROOT, check=True)
subprocess.run(["npm", "run", "build"], cwd=ROOT, check=True)

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
OG_VER = hashlib.sha1(card_json.encode() + (BUILD / "card.js").read_bytes()).hexdigest()[:10]
st = {r["signal"]: r for r in status}
t = st["thermo"]["value"]
levels = [(0, "平常", "<80"), (80, "留意", "80–85"), (85, "偏恐慌", "85–90"), (90, "恐慌", "90–95"), (95, "極度恐慌", "≥95")]
limit, level, level_range = next(row for row in reversed(levels) if t >= row[0])
og_title = f"鄉民恐慌溫度 {t:.1f}（{level}）｜台股落底訊號回測"
dual = st["dual"]
dual_today = "本交易日已同時達標" if dual["value"] == 1 else "本交易日未同時達標"
dual_recent = "近 5 個交易日曾達標" if dual["value"] == 0 and dual["lit5"] == 1 else ""
og_desc = (f"PTT 恐慌文與大盤跌幅，{dual_today}"
           + (f"（{dual_recent}）" if dual_recent else "")
           + f"。偏空警示近 5 個交易日 {st['wscore']['value']}/3 項。"
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
        "dual-pill": dual_today,
        "dual-recent": dual_recent,
        "dual-l5": str(dual["l5"]),
        "dual-ch": f'{dual["creative_heat"]:.1f}',
        "dual-dd": f'{dual["dd60"]:.2f}%',
        "dual-last": "上次達標 " + date(dual["last_lit"]),
        **{f"dual-check-{key}": "達標" if passed else "未達標" for key, passed in dual.get("checks", {}).items()},
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
</head>
<body>
<canvas id="c" width="1200" height="630"></canvas>
<script type="application/json" id="dashboard-today">{card_js}</script>
<script src="card.js"></script>
</body>
</html>
"""

HEAD = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>台股落底訊號回測</title>
<meta name="description" content="查看 PTT 股票版鄉民恐慌溫度、恐慌文與大盤跌幅是否達標、偏空警示和歷史回測。">
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
<script type="application/json" id="dashboard-today">%TODAY%</script>
<script type="module" src="assets/dashboard.js"></script>
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
    f.write(HEAD.replace("%OG%", OG).replace("%FONTS%", FONTS)
            .replace("%TODAY%", card_js).replace("</head>", gc_head + "</head>")
            + seed_today(page) + FOOT.replace("  資料來源：", "  " + gc_note + "資料來源：", 1)
            .replace('<span id="site-updated">—</span>', f'<span id="site-updated">{e(generated)}</span>'))
shutil.copytree(BUILD / "assets", Path(OUT, "assets"), dirs_exist_ok=True)
shutil.copyfile(BUILD / "card.js", os.path.join(OUT, "card.js"))
open(os.path.join(OUT, "card.html"), "w", encoding="utf-8").write(CARD_HTML)
os.makedirs(os.path.join(OUT, "og"), exist_ok=True)
open(os.path.join(OUT, "og", ".target"), "w").write(OG_NAME)
for n in NAMES:
    shutil.copyfile(os.path.join(SRC, "data", f"{n}.json"), os.path.join(OUT, "data", f"{n}.json"))
open(os.path.join(OUT, ".nojekyll"), "w").close()
print("site written:", OUT, sum(os.path.getsize(os.path.join(OUT, "data", f"{n}.json")) for n in NAMES) // 1024, "KB data")
