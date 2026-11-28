"""
產生「台股落底訊號回測」儀表板的資料：5 個 JSON 檔，各為 {rows, meta}
  daily.json    每日：加權、櫃買、各訊號是否亮燈與數值、落底分數、過熱分數
  events.json   每個訊號事件：日期、當時數值、兩個指數的後續報酬、再跌／再漲幅度、距波段低點／高點天數
  summary.json  每個訊號 × 指數：後 1/5/20/60 日報酬、同年度隨機對照、價格配對超額、精準度
  status.json   最新一天每個訊號的數值、門檻、最近亮燈日
  posts.json    PTT 訊號（創作文、畢業文、過熱文）每次事件與最近 5 日的文章標題與連結

用法: python3 -I build_dashboard_data.py data out_dir

落底訊號（亮燈條件只用當時已知的資料；百分位都用「過去 250 個交易日」）：
  creative  PTT [創作] 原文當天 >= 5 篇且 >= 4 倍前 60 交易日平均（09:00 分界，隔天開盤進場）
  loss      PTT 多方畢業／虧損文（loss_rules.py：排除問句、市場機制、空軍畢業、不相關），5 日內 >= 3 篇（09:00 分界，隔天開盤進場）
  margin    融資張數 5 日變化 <= 第 5 百分位（晚上公布 → 隔天開盤進場）
  default   違約金額（買賣相抵後）÷ 成交日成交金額 >= 第 95 百分位（隔天開盤進場）
  foreign   外資 5 日累計買賣超 ÷ 5 日成交金額 <= 第 5 百分位（隔天開盤進場）
過熱訊號：
  hot_ptt   PTT 財富自由／人生畢業／歐印／噴／翻倍／創新高／賺爛／上車 原文，5 日內 >= 5 篇且 >= 3 倍前 60 日的 5 日平均（09:00 分界，隔天開盤進場）
  turnover  5 日平均成交金額 ÷ 前 120 日平均 >= 第 95 百分位（隔天開盤進場）
  margin_up 融資金額 20 日變化 >= 第 95 百分位（隔天開盤進場）
  foreign_buy 外資 5 日累計買賣超 ÷ 5 日成交金額 >= 第 95 百分位（隔天開盤進場）
  stretch   加權收盤 ÷ 120 日均線 − 1 >= 第 95 百分位（當天收盤進場）
選擇權、期貨與國外恐慌指數（落底／過熱各一邊，隔天開盤進場）：
  pc_high / pc_low     臺指選擇權 P/C 成交量比 >= 第 95 ／ <= 第 5 百分位（期交所）
  fut_short / fut_long 外資臺股期貨淨未平倉口數 <= 第 5 ／ >= 第 95 百分位（FinMind，與期交所比對一致）
  vix_high / vix_low   美國 CBOE VIX >= 第 95 ／ <= 第 5 百分位（美股收盤在台灣隔天開盤前）
對照：bigdrop 加權單日跌 >= 3%
合成：combo3/4 = 過去 5 個交易日內 7 個落底訊號有 >= 3／>= 4 個亮燈；gcombo3/4 = 8 個過熱訊號同理（隔天開盤進場）
偏空警示（不算進分數）：fut_short、fut_ratio_short（淨空單 ÷ 全市場未平倉）、fut_chg_short（5 日淨部位變化）<= 第 5 百分位
事件去重：距上一個事件不到 10 個交易日略過。回測期間 2019/1 起（之前的資料只用來算門檻）。
另印出外資、違約「未正規化」版本的結果，方便比較。
"""
import sys, os, json, csv, glob, random, bisect, re, statistics as st, datetime as dt, collections

D, OUT = sys.argv[1], sys.argv[2]
SRC = open(os.path.abspath(__file__), encoding="utf-8").read()
TZ = dt.timezone(dt.timedelta(hours=8))
SINCE, GAP, H = dt.date(2019, 1, 2), 10, [1, 5, 20, 60]
random.seed(42)

# ---------- 指數與成交金額 ----------
def load_px(paths):
    out = {}
    for p in paths:
        if os.path.exists(p):
            for r in csv.DictReader(open(p)): out[dt.date.fromisoformat(r["date"])] = (float(r["open"]), float(r["close"]))
    return out
tw = load_px([f"{D}/taiex.csv"]); tp = load_px([f"{D}/tpex_early.csv", f"{D}/tpex.csv"])
turn = {dt.date.fromisoformat(r["date"]): int(r["turnover"]) for r in csv.DictReader(open(f"{D}/turnover.csv"))}
days = sorted(d for d in tw if d >= dt.date(2017, 6, 1))
N = len(days)
PX = {"TAIEX": ([tw[d][0] for d in days], [tw[d][1] for d in days]),
      "TPEx": ([tp.get(d, (None, None))[0] for d in days], [tp.get(d, (None, None))[1] for d in days])}
TV = [turn.get(d) for d in days]
start = bisect.bisect_left(days, SINCE)
cut = [dt.datetime.combine(d, dt.time(13, 30), TZ).timestamp() for d in days]
def pctile(xs, q): xs = sorted(xs); return xs[min(len(xs) - 1, int(q * len(xs)))]
ctw = PX["TAIEX"][1]

# ---------- PTT ----------
open_cut = [dt.datetime.combine(d, dt.time(9, 0), TZ).timestamp() for d in days]
# PTT 文章歸屬：當天 09:00 到下一個交易日 09:00 前發的文都算當天（盤中、收盤後、隔天開盤前、週末都算進前一個交易日）
# 當天的篇數要到下一個交易日 09:00 才完整，所以 PTT 訊號一律用隔天開盤進場
_nd = days[-1] + dt.timedelta(days=1)
while _nd.weekday() >= 5: _nd += dt.timedelta(days=1)
next_open = dt.datetime.combine(_nd, dt.time(9, 0), TZ).timestamp()   # 下一個交易日（以平日估計）09:00；之後的文章屬於還沒收盤的那一天
def bucket_idx(ts): return N if ts >= next_open else bisect.bisect_left(open_cut, ts) - 1
def bucket(posts):
    c = [0] * N
    for p in posts:
        i = bucket_idx(p["ts"])
        if 0 <= i < N: c[i] += 1
    return c
seen = {}
for f in [f"{D}/graduation_search.json", f"{D}/creative_search.json"] + glob.glob(f"{D}/kw_*.json") + glob.glob(f"{D}/greed_*.json") + glob.glob(f"{D}/ptt_latest.json"):
    for p in json.load(open(f)): seen[p["id"]] = p
orig = [p for p in seen.values() if not re.match(r"(Re|RE|Fw|FW):", p["title"])]
cat = lambda t: (re.match(r"\[([^\]]+)\]", t) or [None, ""])[1]
LOSS = ["畢業", "斷頭", "歸零", "賠光", "追繳", "爆倉", "違約交割"]
META = ["太少", "這麼少", "很少", "沒有畢業", "人生", "財富自由", "退休", "畢業生", "畢業典禮", "大學", "研究所", "想畢業"]
GREED = ["財富自由", "人生畢業", "歐印", "噴", "翻倍", "創新高", "賺爛", "上車"]
creative_posts = [p for p in orig if p["title"].startswith("[創作]")]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loss_rules import classify as loss_classify              # 只留下鄉民自己做多賠錢的文章（規則與排除原因見 loss_rules.py）
loss_posts = [p for p in orig if loss_classify(p["title"])[0]]
# 畢業文改用內文判斷（2026/11/27 起）：只算〔心得〕原文，內文要是作者本人做多認賠或重大虧損、而且有截圖或具體金額。
# 歷史（cutoff 之前）用參考標記 loss_labels_ref.json（Claude 判斷＋複核）；cutoff 之後的新文章用 loss_labels.json（Groq 判斷）；
# 還沒判斷到的新文章暫時照標題規則算。JUDGE 記下每篇的判斷來源，文章列表會標出來。
from loss_rules import CAT as loss_cat
JUDGE = {}
if os.path.exists(f"{D}/loss_labels_ref.json"):
    _ref = json.load(open(f"{D}/loss_labels_ref.json", encoding="utf-8"))
    _rows, _cut = _ref["rows"], _ref.get("cutoff") or 0
    _ai = json.load(open(f"{D}/loss_labels.json", encoding="utf-8")) if os.path.exists(f"{D}/loss_labels.json") else {}
    _keep = []
    for p in loss_posts:
        if loss_cat(p["title"]) != "心得": continue
        a = _ai.get(p["id"]) or {}
        if p["id"] in _rows:
            if _rows[p["id"]]["counts"]: _keep.append(p); JUDGE[p["id"]] = "ref"
        elif a.get("status") == "ok" and "counts" in a:
            if a["counts"]: _keep.append(p); JUDGE[p["id"]] = "ai"
        elif a.get("status") == "deleted":
            continue
        elif p["ts"] >= _cut:
            _keep.append(p); JUDGE[p["id"]] = "title"
    loss_posts = _keep
if os.environ.get("LOSS_IDS"):   # 實驗用：指定要算進畢業文的文章 id（例如只算內文有依據的），正式建置不會設定
    _ids = set(json.load(open(os.environ["LOSS_IDS"], encoding="utf-8")))
    loss_posts = [seen[i] for i in _ids if i in seen]
hot_posts = [p for p in orig if cat(p["title"]) not in ("新聞", "情報", "公告")
             and any(k in p["title"] for k in GREED) and not any(k in p["title"] for k in ["斷頭", "賠光", "歸零", "追繳", "爆倉"])]
cc, lc, hc = bucket(creative_posts), bucket(loss_posts), bucket(hot_posts)

# ---------- 鄉民恐慌溫度（0–100）：創作文、畢業／虧損文 5 日篇數，各自跟過去 250 個交易日比「比今天少的天數比例」，兩者平均 ----------
roll5 = lambda c: [sum(c[max(0, i - 4):i + 1]) for i in range(len(c))]
c5c, l5c = roll5(cc), roll5(lc)
def heat(series, i):
    past = series[max(0, i - 250):i]
    return sum(x < series[i] for x in past) / len(past) if len(past) >= 250 else None
fear = [None if heat(c5c, i) is None else (heat(c5c, i) + heat(l5c, i)) / 2 * 100 for i in range(N)]

# ---------- 融資、違約、外資 ----------
mgu, mga = {}, {}
for r in csv.DictReader(open(f"{D}/margin.csv")):
    d = dt.date.fromisoformat(r["date"])
    if r["margin_units"]: mgu[d] = int(r["margin_units"])
    if r["margin_amount"]: mga[d] = int(r["margin_amount"])
ddn = {dt.date.fromisoformat(r["date"]): int(r["net_amount"]) for r in csv.DictReader(open(f"{D}/default_daily.csv"))}
fi = {}
for r in csv.DictReader(open(f"{D}/foreign_inst.csv")):            # 外資（不含自營）買賣超，元；FinMind TaiwanStockTotalInstitutionalInvestors 的 Foreign_Investor
    fi[dt.date.fromisoformat(r["date"])] = int(r["foreign_net"])

pcv = {dt.date.fromisoformat(r["date"]): (float(r["pc_vol"]), float(r["pc_oi"])) for r in csv.DictReader(open(f"{D}/taifex_pc.csv")) if r["pc_vol"] and r["pc_oi"]}
futn = {dt.date.fromisoformat(r["date"]): float(r["foreign_net_oi"]) for r in csv.DictReader(open(f"{D}/futures_foreign.csv"))}
usvix = [None] * N                                   # 美股日 t 的 VIX 收盤 → 對到 <= t 的最後一個台股交易日
usvix_dates = [None] * N
for r in csv.DictReader(open(f"{D}/cboe_vix.csv")):
    t = dt.datetime.strptime(r["DATE"], "%m/%d/%Y").date()
    i = bisect.bisect_right(days, t) - 1
    if 0 <= i < N:
        usvix[i] = float(r["CLOSE"])
        usvix_dates[i] = t.isoformat()

BOT = ["creative", "loss", "margin", "default", "foreign", "pc_high", "vix_high"]
WARN = ["fut_short", "fut_ratio_short", "fut_chg_short"]   # 偏空警示：外資期貨空單極端之後通常續弱，不算進落底分數
TOP = ["hot_ptt", "turnover", "margin_up", "foreign_buy", "stretch", "pc_low", "fut_long", "vix_low"]
txoi = {dt.date.fromisoformat(r["date"]): int(r["total_oi"]) for r in csv.DictReader(open(f"{D}/tx_total_oi.csv"))}
fx = {dt.date.fromisoformat(r["date"]): float(r["usdtwd"]) for r in csv.DictReader(open(f"{D}/usdtwd.csv"))}
EXTRA = ["foreign_raw", "default_raw", "pc_oi_high", "pc_oi_low", "fut_ratio_long", "fut_chg_long", "twd_dep", "twd_app"]
ALL = BOT + TOP + WARN + EXTRA
flag = {k: [False] * N for k in ALL + ["bigdrop"]}
val = {k: [None] * N for k in ALL}
thr = {k: [None] * N for k in ALL}
hist = collections.defaultdict(list)
def pct_rule(k, i, x, low):
    if x is None: return
    if len(hist[k]) >= 250:
        thr[k][i] = pctile(hist[k][-250:], 0.05 if low else 0.95)
        flag[k][i] = (x <= thr[k][i]) if low else (x >= thr[k][i])
    val[k][i] = x; hist[k].append(x)
for i in range(N):
    d = days[i]
    if i >= 60:
        base = sum(cc[i - 60:i]) / 60
        val["creative"][i], thr["creative"][i] = cc[i], max(5, 4 * max(base, 0.1))
        flag["creative"][i] = cc[i] >= thr["creative"][i]
    if i >= 4:
        val["loss"][i], thr["loss"][i] = sum(lc[i - 4:i + 1]), 3
        flag["loss"][i] = val["loss"][i] >= 3
    if i >= 64:
        h5 = sum(hc[i - 4:i + 1]); base5 = sum(hc[i - 64:i - 4]) / 60 * 5
        val["hot_ptt"][i], thr["hot_ptt"][i] = h5, max(5, 3 * max(base5, 0.1))
        flag["hot_ptt"][i] = h5 >= thr["hot_ptt"][i]
    u, u5 = mgu.get(d), (mgu.get(days[i - 5]) if i >= 5 else None)
    pct_rule("margin", i, (u / u5 - 1) if u and u5 else None, True)
    a, a20 = mga.get(d), (mga.get(days[i - 20]) if i >= 20 else None)
    pct_rule("margin_up", i, (a / a20 - 1) if a and a20 else None, False)
    # 違約申報日 = 成交日後第 2 個營業日 → 用成交日（i-2）的成交金額
    x = ddn.get(d); tv2 = TV[i - 2] if i >= 2 else None
    pct_rule("default_raw", i, x, False)
    pct_rule("default", i, (x / tv2) if x is not None and tv2 else None, False)
    w = [fi.get(days[j]) for j in range(i - 4, i + 1)] if i >= 4 else [None]
    t5 = [TV[j] for j in range(i - 4, i + 1)] if i >= 4 else [None]
    f5 = sum(w) if None not in w else None
    tv5 = sum(t5) if None not in t5 else None
    pct_rule("foreign_raw", i, f5, True)
    ratio = f5 / tv5 if f5 is not None and tv5 else None
    pct_rule("foreign", i, ratio, True)          # 同一個比率：低於第 5 百分位 = 大賣超
    pct_rule("foreign_buy", i, ratio, False)     #            高於第 95 百分位 = 大買超
    if i >= 124 and None not in TV[i - 124:i + 1]:
        pct_rule("turnover", i, (sum(TV[i - 4:i + 1]) / 5) / (sum(TV[i - 124:i - 4]) / 120) - 1, False)
    if i >= 119:
        pct_rule("stretch", i, ctw[i] / (sum(ctw[i - 119:i + 1]) / 120) - 1, False)
    pc = pcv.get(d)
    pct_rule("pc_high", i, pc[0] if pc else None, False); pct_rule("pc_low", i, pc[0] if pc else None, True)
    pct_rule("pc_oi_high", i, pc[1] if pc else None, False); pct_rule("pc_oi_low", i, pc[1] if pc else None, True)
    fn = futn.get(d)
    pct_rule("fut_short", i, fn, True); pct_rule("fut_long", i, fn, False)
    pct_rule("vix_high", i, usvix[i], False); pct_rule("vix_low", i, usvix[i], True)
    ratio_oi = fn / txoi[d] if fn is not None and txoi.get(d) else None          # 外資淨未平倉 ÷ 全市場未平倉
    pct_rule("fut_ratio_short", i, ratio_oi, True); pct_rule("fut_ratio_long", i, ratio_oi, False)
    f5 = futn.get(days[i - 5]) if i >= 5 else None                               # 5 日內淨未平倉變化（口）
    chg = fn - f5 if fn is not None and f5 is not None else None
    pct_rule("fut_chg_short", i, chg, True); pct_rule("fut_chg_long", i, chg, False)
    x0, x5 = fx.get(d), (fx.get(days[i - 5]) if i >= 5 else None)                # 美元兌台幣 5 日變化（正 = 台幣貶值）
    fxc = x0 / x5 - 1 if x0 and x5 else None
    pct_rule("twd_dep", i, fxc, False); pct_rule("twd_app", i, fxc, True)
    if i >= 1: flag["bigdrop"][i] = ctw[i] / ctw[i - 1] - 1 <= -0.03
def score_of(keys):
    return [sum(any(flag[k][j] for j in range(max(0, i - 4), i + 1)) for k in keys) for i in range(N)]
score, gscore, wscore = score_of(BOT), score_of(TOP), score_of(WARN)
flag["combo3"] = [s >= 3 for s in score]; flag["combo4"] = [s >= 4 for s in score]
for t in (95, 90, 85, 80): flag[f"thermo{t}"] = [f is not None and f >= t for f in fear]      # 溫度分級
# 雙重確認：畢業文 5 日 >= 3 篇（有人認賠出場），同時創作文 5 日熱度 >= 0.90（大家正在恐慌），
#           而且加權指數距 60 日高點至少跌 5%（大盤真的有跌；排除像 2020/7/20 合一重挫這種單一個股事件）
ch5 = [heat(c5c, i) for i in range(N)]
dd60 = [ctw[i] / max(ctw[max(0, i - 60):i + 1]) - 1 for i in range(N)]
dual_checks = [{"loss": l5c[i] >= 3, "creative": ch5[i] is not None and ch5[i] >= 0.90,
                "drawdown": dd60[i] <= -0.05} for i in range(N)]
flag["dual"] = [all(checks.values()) for checks in dual_checks]
score5 = score_of(BOT[:5]); flag["combo5_3"] = [s >= 3 for s in score5]   # 對照：加入選擇權／期貨／VIX 前的 5 訊號版本
flag["gcombo3"] = [s >= 3 for s in gscore]; flag["gcombo4"] = [s >= 4 for s in gscore]

ENTRY = {k: "open1" for k in ALL + ["combo3", "combo4", "combo5_3", "gcombo3", "gcombo4"]}
ENTRY.update({f"thermo{t}": "open1" for t in (95, 90, 85, 80)}); ENTRY["dual"] = "open1"
ENTRY.update({"stretch": "close0", "bigdrop": "close0"})          # PTT 訊號（創作文、畢業文、過熱文、溫度）用隔天開盤
NAMES = {"creative": "PTT 創作文爆量", "loss": "PTT 畢業／虧損文", "margin": "融資張數 5 日大減", "default": "違約金額爆量（佔成交額）",
         "foreign": "外資 5 日大賣超（佔成交額）", "bigdrop": "加權單日跌 ≥3%（對照）", "dual": "雙重確認", "thermo95": "鄉民恐慌溫度 ≥95", "thermo90": "鄉民恐慌溫度 ≥90", "thermo85": "鄉民恐慌溫度 ≥85", "thermo80": "鄉民恐慌溫度 ≥80", "combo3": "落底分數 ≥3", "combo4": "落底分數 ≥4", "combo5_3": "原 5 訊號落底分數 ≥3（對照）",
         "hot_ptt": "PTT 過熱文爆量", "turnover": "成交金額爆量", "margin_up": "融資金額 20 日大增", "foreign_buy": "外資 5 日大買超（佔成交額）",
         "stretch": "加權乖離 120 日線", "gcombo3": "過熱分數 ≥3", "gcombo4": "過熱分數 ≥4",
         "pc_high": "選擇權 P/C 成交量比偏高", "pc_low": "選擇權 P/C 成交量比偏低", "fut_short": "外資期貨淨空單極端", "fut_long": "外資期貨淨多單極端",
         "vix_high": "美國 VIX 恐慌", "vix_low": "美國 VIX 過度安逸", "fut_ratio_short": "外資淨空單佔全市場未平倉（極端）", "fut_ratio_long": "外資淨多單佔全市場未平倉（極端）",
         "fut_chg_short": "外資 5 日大增空單", "fut_chg_long": "外資 5 日大增多單", "twd_dep": "台幣 5 日急貶", "twd_app": "台幣 5 日急升", "pc_oi_high": "P/C 未平倉比偏高（參考）", "pc_oi_low": "P/C 未平倉比偏低（參考）",
         "foreign_raw": "外資 5 日大賣超（金額，舊版）", "default_raw": "違約金額爆量（金額，舊版）"}
BORDER = ["dual", "thermo95", "thermo90", "thermo85", "thermo80", "combo4", "combo3", "combo5_3", "vix_high", "pc_high", "foreign", "margin", "default", "loss", "creative", "bigdrop"]
TORDER = ["gcombo4", "gcombo3", "vix_low", "pc_low", "fut_long", "foreign_buy", "margin_up", "turnover", "hot_ptt", "stretch"]
WORDER = ["fut_short", "fut_ratio_short", "fut_chg_short"]
SIDE = {k: "bottom" for k in BORDER + ["foreign_raw", "default_raw", "pc_oi_high", "twd_dep"]}
SIDE.update({k: "warn" for k in WORDER})
SIDE.update({k: "top" for k in TORDER + ["pc_oi_low", "fut_ratio_long", "fut_chg_long", "twd_app"]})

# ---------- 報酬與精準度 ----------
def entry_px(ix, i, e):
    o, c = PX[ix]
    if e == "close0": return c[i]
    return o[i + 1] if i + 1 < N else None
def fwd(ix, i, h, e):
    c = PX[ix][1]; p0 = entry_px(ix, i, e)
    if i + h >= N or p0 is None or c[i + h] is None: return None
    return c[i + h] / p0 - 1
def ret5(ix, i):
    c = PX[ix][1]
    return c[i] / c[i - 5] - 1 if i >= 5 and c[i] and c[i - 5] else None
def ext20(ix, i, e, fn):
    c = PX[ix][1]; p0 = entry_px(ix, i, e)
    if p0 is None or i + 20 >= N or None in c[i + 1:i + 21]: return None
    return fn(c[i + 1:i + 21]) / p0 - 1
def turn_off(ix, i, fn):
    c = PX[ix][1]
    if i + 20 >= N: return None
    js = [j for j in range(i - 20, i + 21) if c[j] is not None]
    return fn(js, key=lambda j: c[j]) - i
def off_ext(ix, i, top):
    c = PX[ix][1]; w = [x for x in c[max(0, i - 60):i + 1] if x]
    return c[i] / (min(w) if top else max(w)) - 1

events = {}
for k in BORDER + TORDER + WORDER + EXTRA:
    ev, last = [], -10**9
    for i in range(start, N):
        if flag[k][i] and i - last >= GAP: ev.append(i); last = i
    events[k] = ev

by_year = collections.defaultdict(list)
for i in range(start, N): by_year[days[i].year].append(i)
r2 = lambda x, n=2: None if x is None else round(x * 100, n)

def summarize(k, ix):
    e, top = ENTRY[k], SIDE[k] == "top"
    neg = SIDE[k] in ("top", "warn")      # 過熱與偏空警示：亮燈後偏弱才算「準」
    row = {"signal": k, "name": NAMES[k], "side": SIDE[k], "index": ix, "entry": "當天收盤" if e == "close0" else "隔天開盤", "n": len(events[k])}
    for h in H:
        ev = [i for i in events[k] if fwd(ix, i, h, e) is not None]
        row[f"n{h}"] = len(ev)
        if len(ev) < 3: continue
        r = [fwd(ix, i, h, e) for i in ev]; m = st.mean(r)
        pools = [[j for j in by_year[days[i].year] if fwd(ix, j, h, e) is not None] for i in ev]
        sims = [st.mean(fwd(ix, random.choice(p), h, e) for p in pools) for _ in range(4000)]
        ctrl = []
        for i, p in zip(ev, pools):
            near = sorted((j for j in p if abs(j - i) > 5 and ret5(ix, j) is not None), key=lambda j: abs(ret5(ix, j) - ret5(ix, i)))[:10]
            ctrl.append(st.mean(fwd(ix, j, h, e) for j in near))
        exc = [a - b for a, b in zip(r, ctrl)]
        row.update({f"ret{h}": r2(m), f"win{h}": r2(sum(x > 0 for x in r) / len(r), 0), f"rand{h}": r2(st.mean(sims)),
                    f"p{h}": round(sum((s <= m) if neg else (s >= m) for s in sims) / len(sims), 3),
                    f"excess{h}": r2(st.mean(exc)), f"beat{h}": r2(sum((x < 0) if neg else (x > 0) for x in exc) / len(exc), 0)})
    offs = [turn_off(ix, i, max if top else min) for i in events[k]]; offs = [x for x in offs if x is not None]
    further = [ext20(ix, i, e, max if top else min) for i in events[k]]; further = [x for x in further if x is not None]
    within5 = sum(abs(x) <= 5 for x in offs)
    row.update({"ext_median": st.median(offs) if offs else None, "ext_n": len(offs), "ext_within5_n": within5,
                "ext_within5": r2(within5 / len(offs), 0) if offs else None,
                "ext_after": r2(sum(x > 5 for x in offs) / len(offs), 0) if offs else None,
                "further_mean": r2(st.mean(further)) if further else None, "further_n": len(further),
                "further_big": r2(sum((x >= 0.05) if top else (x <= -0.05) for x in further) / len(further), 0) if further else None,
                "off_ext": r2(st.mean(off_ext(ix, i, top) for i in events[k])) if events[k] else None})
    return row

summary = [summarize(k, ix) for k in BORDER + TORDER + WORDER for ix in ["TAIEX", "TPEx"]]

def vtext(k, i):
    v = val.get(k, [None] * N)[i]
    return {"creative": lambda: f"{cc[i]} 篇", "loss": lambda: f"5 日 {v} 篇", "hot_ptt": lambda: f"5 日 {v} 篇",
            "margin": lambda: f"{v*100:+.2f}%", "margin_up": lambda: f"{v*100:+.2f}%",
            "default": lambda: f"萬分之 {v*1e4:.3f}", "foreign": lambda: f"{v*100:+.2f}%", "foreign_buy": lambda: f"{v*100:+.2f}%",
            "turnover": lambda: f"{v*100:+.1f}%", "stretch": lambda: f"{v*100:+.2f}%",
            "bigdrop": lambda: f"{(ctw[i]/ctw[i-1]-1)*100:+.2f}%",
            "pc_high": lambda: f"{v:.2f}%", "pc_low": lambda: f"{v:.2f}%", "fut_short": lambda: f"{v:+,.0f} 口", "fut_long": lambda: f"{v:+,.0f} 口", "fut_ratio_short": lambda: f"{v*100:+.1f}%", "fut_chg_short": lambda: f"{v:+,.0f} 口",
            "vix_high": lambda: f"{v:.2f}", "vix_low": lambda: f"{v:.2f}",
            "dual": lambda: f"畢業文 5 日 {l5c[i]} 篇、創作文熱度 {ch5[i]*100:.0f}、加權距高點 {dd60[i]*100:.1f}%", "thermo95": lambda: f"溫度 {fear[i]:.1f}", "thermo90": lambda: f"溫度 {fear[i]:.1f}", "thermo85": lambda: f"溫度 {fear[i]:.1f}", "thermo80": lambda: f"溫度 {fear[i]:.1f}",
            "combo3": lambda: f"{score[i]} 個訊號", "combo4": lambda: f"{score[i]} 個訊號", "combo5_3": lambda: f"{score5[i]} 個訊號",
            "gcombo3": lambda: f"{gscore[i]} 個訊號", "gcombo4": lambda: f"{gscore[i]} 個訊號"}[k]()
# ---------- 事件說明：從當時的畢業文、創作文標題抓主題，加上少數人工註記 ----------
THEMES = {"合一": ["合一"], "台積電": ["台積", "GG", "2330", "積積"], "聯發科": ["聯發科", "發哥", "2454"], "航運": ["航運", "海運", "長榮", "陽明", "萬海", "貨櫃", "水手", "船"],
          "面板": ["面板", "友達", "群創"], "被動元件": ["被動元件", "國巨", "華新科"], "記憶體": ["記憶體", "南亞科", "華邦"], "輝達／AI": ["輝達", "NVDA", "仁勳", "黃仁勳", "AI"],
          "關稅／川普": ["關稅", "川普", "Trump"], "疫情": ["疫情", "肺炎", "武漢", "封城", "確診"], "融資斷頭": ["融資", "斷頭", "追繳"], "外資": ["外資"],
          "槓桿 ETF": ["正2", "正二", "00631L", "00675L", "槓桿"], "期貨選擇權": ["期貨", "台指", "選擇權", "微台"], "VIX": ["VIX", "vix"], "原油": ["原油", "石油"], "美債": ["美債", "債券", "TLT"]}
NOTES = [("2020-03-09", "2020-03-31", "新冠疫情全球股災"), ("2021-05-10", "2021-05-20", "美國通膨疑慮＋台灣本土疫情升溫"),
         ("2024-07-17", "2024-07-31", "AI 半導體股回檔"), ("2024-08-01", "2024-08-09", "日圓套利平倉全球股災"), ("2025-04-02", "2025-04-15", "美國對等關稅股災"),
         ("2022-09-26", "2022-10-31", "Fed 激進升息＋外資撤離")]   # 2022/10/25 收 12,666 為 2022 年低點；當時報導主因：Fed 強勢升息、新台幣重貶、外資賣超
loss_idx, crea_idx = collections.defaultdict(list), collections.defaultdict(list)
for p in loss_posts: loss_idx[bucket_idx(p["ts"])].append(p)
for p in creative_posts: crea_idx[bucket_idx(p["ts"])].append(p)
def post_url(post):
    return "https://www.ptt.cc/bbs/Stock/" + post["id"] + ".html"

def context(i):
    lp = sorted((p for j in range(i - 4, i + 1) for p in loss_idx.get(j, [])), key=lambda p: p["ts"])
    cp = [p for j in range(i - 4, i + 1) for p in crea_idx.get(j, [])]
    cnt = collections.Counter()
    for p in lp + cp:
        for name, kws in THEMES.items():
            if any(k in p["title"] for k in kws): cnt[name] += 1
    note = next((n for a, b, n in NOTES if a <= days[i].isoformat() <= b), "")
    strip = lambda t: re.sub(r"^[\[［][^\]］}]+[\]］}]\s*", "", t).strip()
    return {"note": note, "themes": "、".join(f"{n}×{c}" for n, c in cnt.most_common(3) if c >= 2),
            "loss_titles": "｜".join(strip(p["title"])[:30] for p in lp[:4]), "creative_n5": len(cp),
            "loss_sources": [{"title": p["title"], "url": post_url(p)} for p in lp[:4]]}
CTX = {"dual", "thermo95", "thermo90", "thermo85", "thermo80", "loss", "creative", "combo3", "combo4", "combo5_3"}

ev_rows = []
for k in BORDER + TORDER + WORDER:
    e, top = ENTRY[k], SIDE[k] == "top"
    keys = TOP if k.startswith("g") and k[1:5] == "comb" else (BOT[:5] if k == "combo5_3" else BOT)
    for i in events[k]:
        row = {"signal": k, "name": NAMES[k], "side": SIDE[k], "date": days[i].isoformat(), "value": vtext(k, i), "pending20": i + 20 >= N,
               "lit": "、".join(NAMES[s] for s in keys if any(flag[s][j] for j in range(i - 4, i + 1))) if "combo" in k else ""}
        if k in CTX: row.update(context(i))
        for ix, tag in [("TAIEX", "tw"), ("TPEx", "tp")]:
            row[f"{tag}_close"] = PX[ix][1][i]
            for h in [5, 20, 60]: row[f"{tag}_ret{h}"] = r2(fwd(ix, i, h, e))
            row[f"{tag}_further"] = r2(ext20(ix, i, e, max if top else min))
            row[f"{tag}_ext"] = turn_off(ix, i, max if top else min)
        ev_rows.append(row)

for a, b, n in NOTES:
    ii = [i for i in range(start, N) if a <= days[i].isoformat() <= b]
    if not ii: continue
    i = min(ii, key=lambda j: ctw[j])
    ev_rows.append({"signal": "note", "name": "事件註記", "side": "bottom", "date": days[i].isoformat(), "note": n, "start": a, "end": b,
                    "tw_close": PX["TAIEX"][1][i], "tp_close": PX["TPEx"][1][i]})

daily = []
for i in range(start, N):
    row = {"date": days[i].isoformat(), "taiex": PX["TAIEX"][1][i], "tpex": PX["TPEx"][1][i], "score": score[i], "gscore": gscore[i], "wscore": wscore[i],
           "fear": None if fear[i] is None else round(fear[i], 1), "c5": c5c[i], "l5": l5c[i], "f_dual": int(flag["dual"][i]),
           "cheat": None if ch5[i] is None else round(ch5[i] * 100, 1)}
    row.update({f"f_{k}": int(flag[k][i]) for k in BOT + TOP + WARN + ["bigdrop"]})
    daily.append(row)

UNIT = {"creative": "篇", "loss": "篇（5 日）", "hot_ptt": "篇（5 日）", "margin": "%", "margin_up": "%", "default": "萬分之",
        "foreign": "%", "foreign_buy": "%", "turnover": "%", "stretch": "%", "bigdrop": "%",
        "pc_high": "%", "pc_low": "%", "fut_short": "口", "fut_long": "口", "vix_high": "", "vix_low": "", "fut_ratio_short": "%", "fut_chg_short": "口"}
def disp(k, x):
    if x is None: return None
    if k in ("margin", "margin_up", "foreign", "foreign_buy", "stretch"): return round(x * 100, 2)
    if k == "turnover": return round(x * 100, 1)
    if k == "default": return round(x * 1e4, 3)
    if k in ("creative", "hot_ptt", "pc_high", "pc_low", "vix_high", "vix_low"): return round(x, 2)
    if k in ("fut_short", "fut_long", "fut_chg_short"): return round(x)
    if k == "fut_ratio_short": return round(x * 100, 1)
    return x
status = []
for k in BOT + TOP + WARN + ["bigdrop"]:
    last_i = max((i for i in range(N) if flag[k][i]), default=None)
    if k == "bigdrop":
        li, v, t = N - 1, r2(ctw[-1] / ctw[-2] - 1), -3.0
    else:
        li = max(i for i in range(N) if val[k][i] is not None)
        v, t = disp(k, val[k][li]), disp(k, thr[k][li])
    rule = "≤" if k in ("margin", "foreign", "bigdrop", "pc_low", "fut_short", "fut_ratio_short", "fut_chg_short", "vix_low") else "≥"
    # 最近 20 個交易日每天的數值與門檻（燈號明細的提示用）：[日期, 數值, 門檻]
    if k == "bigdrop":
        recent = [[days[i].isoformat(), r2(ctw[i] / ctw[i - 1] - 1), -3.0] for i in range(N - 20, N)]
    else:
        recent = [[days[i].isoformat(), disp(k, val[k][i]), disp(k, thr[k][i])] for i in range(N - 20, N)]
    status.append({"signal": k, "name": NAMES[k], "side": "top" if k in TOP else ("warn" if k in WARN else "bottom"), "asof": days[li].isoformat(), "value": v,
                   **({"source_asof": usvix_dates[li]} if k in ("vix_high", "vix_low") else {}),
                   "threshold": t, "unit": UNIT[k], "rule": rule, "lit5": int(any(flag[k][j] for j in range(N - 5, N))),
                   "last_lit": days[last_i].isoformat() if last_i is not None else None, "recent": recent})
for k, s, name, side, th, unit in [("score", score, "落底分數", "bottom", 3, "/7"), ("gscore", gscore, "過熱分數", "top", 3, "/8"),
                                   ("wscore", wscore, "偏空警示", "warn", 1, "/3")]:
    status.append({"signal": k, "name": name, "side": side, "asof": days[-1].isoformat(), "value": s[-1], "threshold": th, "unit": unit,
                   "rule": "≥", "lit5": int(s[-1] >= th), "last_lit": max((days[i].isoformat() for i in range(N) if s[i] >= th), default=None)})

d_last = max((i for i in range(N) if flag["dual"][i]), default=None)
status.append({"signal": "dual", "name": NAMES["dual"], "side": "bottom", "asof": days[-1].isoformat(), "value": int(flag["dual"][-1]),
               "threshold": 1, "unit": "", "rule": "=", "lit5": int(any(flag["dual"][j] for j in range(N - 5, N))),
               "last_lit": days[d_last].isoformat() if d_last is not None else None, "l5": l5c[-1], "creative_heat": round(ch5[-1] * 100, 1),
               "dd60": round(dd60[-1] * 100, 1), "checks": dual_checks[-1]})
t_last = max((i for i in range(N) if flag["thermo95"][i]), default=None)
status.append({"signal": "thermo", "name": "鄉民恐慌溫度", "side": "bottom", "asof": days[-1].isoformat(), "value": round(fear[-1], 1),
               "threshold": 95, "unit": "/100", "rule": "≥", "lit5": int(any(flag["thermo95"][j] for j in range(N - 5, N))),
               "last_lit": days[t_last].isoformat() if t_last is not None else None, "c5": c5c[-1], "l5": l5c[-1],
               "creative_heat": None if heat(c5c, N - 1) is None else round(heat(c5c, N - 1) * 100, 1),
               "loss_heat": None if heat(l5c, N - 1) is None else round(heat(l5c, N - 1) * 100, 1),
               "ptt_asof": dt.datetime.fromtimestamp(max(p["ts"] for p in seen.values()), TZ).strftime("%Y-%m-%d %H:%M"),
               "ptt_lag_h": round((dt.datetime.now(TZ).timestamp() - max(p["ts"] for p in seen.values())) / 3600, 1)})

# ---------- 收盤後（下一個交易日）新增的 PTT 文章 ----------
after_cut = lambda plist: [p for p in plist if p["ts"] >= next_open]   # 下一個交易日 09:00 之後的文章：那天還沒有收盤資料，先列出、不算分數
PENDING = {"creative": after_cut(creative_posts), "loss": after_cut(loss_posts), "hot_ptt": after_cut(hot_posts)}
for r in status:
    if r["signal"] in PENDING: r["pending"] = len(PENDING[r["signal"]])

# ---------- PTT 文章連結 ----------
def post_row(k, ev, p):
    return {"signal": k, "event": ev, "posted": dt.datetime.fromtimestamp(p["ts"], TZ).strftime("%Y-%m-%d %H:%M"),
            "title": p["title"], "url": post_url(p), "nrec": p.get("nrec", ""),
            **({"judge": JUDGE.get(p["id"], "title")} if k == "loss" and JUDGE else {})}
posts = []
post_windows = {}
def add_temperature_window(key, i):
    first = max(0, i - 4)
    end = days[i + 1] if i + 1 < N else _nd
    post_windows[key] = {"start": days[first].isoformat(), "end": end.isoformat(), "end_estimated": i == N - 1}
    for k, idx in [("creative", crea_idx), ("loss", loss_idx)]:
        for j in range(first, i + 1):
            for p in sorted(idx.get(j, []), key=lambda p: p["ts"]):
                posts.append(post_row(k, key, p))

for k, plist, win in [("creative", creative_posts, 1), ("loss", loss_posts, 5), ("hot_ptt", hot_posts, 5)]:
    idx = collections.defaultdict(list)
    for p in plist: idx[bucket_idx(p["ts"])].append(p)
    for i in events[k]:
        for j in range(i - win + 1, i + 1):
            for p in sorted(idx.get(j, []), key=lambda p: p["ts"]): posts.append(post_row(k, days[i].isoformat(), p))
    for j in range(N - win, N):                  # 最近一天往回 win 個交易日
        for p in sorted(idx.get(j, []), key=lambda p: p["ts"]): posts.append(post_row(k, "latest", p))
    for p in PENDING[k]: posts.append({**post_row(k, "latest", p), "pending": True})
add_temperature_window("window-latest", N - 1)
for i in sorted(set().union(*(events[k] for k in ("thermo80", "thermo85", "thermo90", "thermo95", "dual")))):
    add_temperature_window("window-" + days[i].isoformat(), i)

# ---------- 比較：外資、違約 正規化前後 ----------
print("== 正規化前後比較（後 20 日超額 / 贏過配對）")
for k in ["fut_short", "fut_ratio_short", "fut_chg_short", "fut_long", "fut_ratio_long", "fut_chg_long", "twd_dep", "twd_app"]:
    for ix in ["TAIEX", "TPEx"]:
        s = summarize(k, ix)
        print(f"  {NAMES[k]:<22}{ix:<6} n={s['n']:>3}  ret5={s.get('ret5')} ret20={s.get('ret20')} ret60={s.get('ret60')} | exc20={s.get('excess20')} beat20={s.get('beat20')} p20={s.get('p20')} | exc60={s.get('excess60')} beat60={s.get('beat60')} p60={s.get('p60')}")
print("== 2020/3 前後亮燈")
for i in range(N):
    if dt.date(2020, 2, 20) <= days[i] <= dt.date(2020, 4, 10):
        lit = [k for k in BOT + ["bigdrop"] if flag[k][i]]
        if lit or score[i]: print(f"  {days[i]} 加權 {ctw[i]:>9.2f} 落底分數 {score[i]} 亮燈 {lit}")

meta = [{"label": "build_dashboard_data.py", "value": SRC, "type": "code", "lang": "python"},
        {"label": "輸入", "value": "taifex_pc.csv（期交所 Put/Call Ratio）、futures_foreign.csv（FinMind，與期交所三大法人期貨比對一致）、cboe_vix.csv（CBOE VIX History）、ptt_latest.json（PTT 列表頁最新文章）、taiex.csv（證交所 MI_5MINS_HIST）、tpex.csv（櫃買中心 indexInfo/inx）、turnover.csv（FinMind，與證交所 FMTQIK 抽樣一致）、PTT 股票版站內搜尋（只比對標題）、margin.csv（FinMind，整理自證交所 MI_MARGN）、default_daily.csv（證交所違約公告專區 BFIGTU）、foreign_inst.csv（FinMind，整理自證交所 BFI82U）"},
        {"label": "產生時間", "value": dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M")}]
os.makedirs(OUT, exist_ok=True)
for name, rows in [("daily", daily), ("events", ev_rows), ("summary", summary), ("status", status), ("posts", posts)]:
    payload = {"rows": rows, "meta": meta}
    if name == "posts":
        payload["windows"] = post_windows
    with open(f"{OUT}/{name}.json", "w") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    print(name, len(rows), "rows", os.path.getsize(f"{OUT}/{name}.json") // 1024, "KB")
