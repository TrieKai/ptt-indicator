"""
多訊號事件回測（2020 年起）：
  1. 鄉民虧損文：標題含 畢業／斷頭／歸零／賠光／追繳／爆倉／違約交割 的原文（排除新聞、回文、「人生畢業」等）
  2. 新聞違約交割／斷頭：[新聞]/[情報] 標題含 違約交割／斷頭／追繳（媒體報導，當作違約交割的代理指標）
  3. 融資大減：融資張數 5 日變化 <= 過去 250 日的第 5 百分位（去槓桿、斷頭潮）
  4. 融資大增：融資張數 20 日變化 >= 過去 250 日的第 95 百分位（散戶追價）

對照：
  - 同年度隨機日（10,000 次抽樣），p = 隨機平均 >= 事件平均 的比例
  - 價格配對：同年度「前 5 日漲跌幅最接近」的 10 個交易日，看訊號有沒有提供股價以外的資訊

用法: python3 -I backtest_signals.py data
"""
import sys, json, csv, glob, random, bisect, re, statistics as st, datetime as dt, collections

D = sys.argv[1]
TZ = dt.timezone(dt.timedelta(hours=8))
SINCE, GAP, HORIZONS = dt.date(2020, 4, 1), 10, [1, 5, 20, 60]

px = [(dt.date.fromisoformat(r["date"]), float(r["open"]), float(r["close"])) for r in csv.DictReader(open(f"{D}/taiex.csv"))]
days = [d for d, _, _ in px]; opn = [o for _, o, _ in px]; close = [c for _, _, c in px]
cut = [dt.datetime.combine(d, dt.time(13, 30), TZ).timestamp() for d in days]
start = bisect.bisect_left(days, SINCE)
# 進場時點：close0 = 當天收盤（PTT 訊號 13:30 前已知）；open1 = 隔天開盤；close1 = 隔天收盤
ENTRY = "close0"
def fwd(i, h):
    if ENTRY == "close0": return close[i + h] / close[i] - 1 if i + h < len(close) else None
    if ENTRY == "open1":  return close[i + h] / opn[i + 1] - 1 if i + h < len(close) else None
    return close[i + 1 + h] / close[i + 1] - 1 if i + 1 + h < len(close) else None
ret = lambda i, h: close[i] / close[i - h] - 1

# ---------- PTT 文章 ----------
seen = {}
for f in [f"{D}/graduation_search.json"] + glob.glob(f"{D}/kw_*.json"):
    for p in json.load(open(f)): seen[p["id"]] = p
orig = [p for p in seen.values() if not re.match(r"(Re|RE|Fw|FW):", p["title"])]
cat = lambda t: (re.match(r"\[([^\]]+)\]", t) or [None, ""])[1]
LOSS = ["畢業", "斷頭", "歸零", "賠光", "追繳", "爆倉", "違約交割"]
META = ["太少", "這麼少", "很少", "沒有畢業", "人生", "財富自由", "退休", "畢業生", "畢業典禮", "大學", "研究所", "想畢業"]
retail = [p for p in orig if cat(p["title"]) not in ("新聞", "情報", "公告", "創作")
          and any(k in p["title"] for k in LOSS) and not any(k in p["title"] for k in META)]
news = [p for p in orig if cat(p["title"]) in ("新聞", "情報") and any(k in p["title"] for k in ["違約交割", "斷頭", "追繳"])]

def daily(posts):
    c = [0] * len(days)
    for p in posts:
        i = bisect.bisect_left(cut, p["ts"])
        if i < len(days): c[i] += 1
    return c

def roll_events(c, win, k):
    ev, last = [], -10**9
    for i in range(start, len(days)):
        s = sum(c[i - win + 1:i + 1])
        if s >= k and i - last >= GAP: ev.append((i, s)); last = i
    return ev

# ---------- 融資 ----------
mg = {dt.date.fromisoformat(r["date"]): int(r["margin_units"]) for r in csv.DictReader(open(f"{D}/margin.csv")) if r["margin_units"]}
units = [mg.get(d) for d in days]
def pctile(xs, q): xs = sorted(xs); return xs[min(len(xs) - 1, int(q * len(xs)))]
def margin_events(win, low):
    ev, last, hist = [], -10**9, []
    for i in range(len(days)):
        if units[i] is None or i < win or units[i - win] is None: continue
        ch = units[i] / units[i - win] - 1
        if len(hist) >= 250 and i >= start and i - last >= GAP:
            th = pctile(hist[-250:], 0.05 if low else 0.95)
            if (ch <= th) if low else (ch >= th): ev.append((i, ch)); last = i
        hist.append(ch)
    return ev

# ---------- 評估 ----------
by_year = collections.defaultdict(list)
for i in range(start, len(days)): by_year[days[i].year].append(i)
pct = lambda x: f"{x*100:+.2f}%"
random.seed(42)

def evaluate(name, events, fmt, entry="close0", show=True):
    global ENTRY; ENTRY = entry
    print(f"\n===== {name}：{len(events)} 個事件（進場：{ {'close0':'當天收盤','open1':'隔天開盤','close1':'隔天收盤'}[entry] }）")
    if not show: pass
    else:
        print("  " + ", ".join(f"{days[i]}({fmt(v)}, 當天{pct(ret(i,1))})" for i, v in events))
    print(f"  {'期間':<4}{'事件平均':>9}{'上漲比例':>8} |{'同年度隨機':>10}{'p值':>7} |{'價格配對':>9}{'超額':>9}")
    for h in HORIZONS:
        ev = [i for i, _ in events if fwd(i, h) is not None]
        if len(ev) < 3: continue
        r = [fwd(i, h) for i in ev]; m = st.mean(r)
        pools = [[j for j in by_year[days[i].year] if fwd(j, h) is not None] for i in ev]
        sims = [st.mean(fwd(random.choice(p), h) for p in pools) for _ in range(10000)]
        ctrl = []
        for i, p in zip(ev, pools):
            near = sorted((j for j in p if abs(j - i) > 5), key=lambda j: abs(ret(j, 5) - ret(i, 5)))[:10]
            ctrl.append(st.mean(fwd(j, h) for j in near))
        exc = [a - b for a, b in zip(r, ctrl)]
        print(f"  後{h:>2}日 {pct(m):>9}{sum(x > 0 for x in r)/len(r):>8.0%} |{pct(st.mean(sims)):>10}{sum(s >= m for s in sims)/len(sims):>7.3f} |"
              f"{pct(st.mean(ctrl)):>9}{pct(st.mean(exc)):>9}  (n={len(r)}, 贏過配對 {sum(e > 0 for e in exc)}/{len(exc)})")

rc, nc = daily(retail), daily(news)
print(f"鄉民虧損文 {len(retail)} 篇、新聞違約交割／斷頭 {len(news)} 篇（原文，2015 年起；回測期間 {days[start]} ~ {days[-1]}）")
evaluate("鄉民虧損文：5 日內 >= 3 篇", roll_events(rc, 5, 3), lambda v: f"{v}篇")
evaluate("新聞違約交割／斷頭：5 日內 >= 2 篇", roll_events(nc, 5, 2), lambda v: f"{v}篇")
# 融資資料在當天晚上才公布，不能用當天收盤進場
for e in ["open1", "close1"]:
    evaluate("融資張數 5 日大減（<= 第 5 百分位）", margin_events(5, True), pct, e, show=False)
for e in ["open1", "close1"]:
    evaluate("融資張數 20 日大增（>= 第 95 百分位）", margin_events(20, False), pct, e, show=False)
# 穩健性：PTT 訊號改用隔天開盤進場
evaluate("鄉民虧損文：5 日內 >= 3 篇", roll_events(rc, 5, 3), lambda v: f"{v}篇", "open1", show=False)

# ---------- 證交所違約交割（申報日期 = 成交日後第 2 個營業日；當天 11:30 後公告）----------
import os
if os.path.exists(f"{D}/default_daily.csv"):
    dd = {dt.date.fromisoformat(r["date"]): (int(r["gross_amount"]), int(r["net_amount"])) for r in csv.DictReader(open(f"{D}/default_daily.csv"))}
    def default_events(col):
        ev, last, hist = [], -10**9, []
        for i in range(len(days)):
            v = dd.get(days[i])
            if v is None: continue
            x = v[col]
            if len(hist) >= 250 and i >= start and i - last >= GAP and x >= pctile(hist[-250:], 0.95):
                ev.append((i, x)); last = i
            hist.append(x)
        return ev
    yi = lambda v: f"{v/1e8:.2f}億"
    print(f"\n\n######## 證交所違約交割（{min(dd)} ~ {max(dd)}，{len(dd)} 天）")
    evaluate("違約金額（買賣相抵後）>= 過去 250 日第 95 百分位", default_events(1), yi, "close0")
    evaluate("違約金額（買賣相抵後）>= 過去 250 日第 95 百分位", default_events(1), yi, "open1", show=False)
    evaluate("違約金額（買賣合計）>= 過去 250 日第 95 百分位", default_events(0), yi, "open1")

# ---------- 三大法人買賣超（FinMind 整理自證交所 BFI82U；收盤後公布 → 隔天開盤進場）----------
if os.path.exists(f"{D}/finmind_inst.json"):
    inst = collections.defaultdict(dict)
    for r in json.load(open(f"{D}/finmind_inst.json"))["data"]:
        inst[r["name"]][dt.date.fromisoformat(r["date"])] = r["buy"] - r["sell"]
    def flow_events(name, win, low):
        s = inst[name]; ev, last, hist = [], -10**9, []
        for i in range(len(days)):
            vals = [s.get(days[j]) for j in range(i - win + 1, i + 1)] if i >= win else [None]
            if None in vals: continue
            x = sum(vals)
            if len(hist) >= 250 and i >= start and i - last >= GAP:
                th = pctile(hist[-250:], 0.05 if low else 0.95)
                if (x <= th) if low else (x >= th): ev.append((i, x)); last = i
            hist.append(x)
        return ev
    yi = lambda v: f"{v/1e8:+.0f}億"
    print(f"\n\n######## 三大法人買賣超（{min(inst['total'])} ~ {max(inst['total'])}）")
    for label, name in [("外資", "Foreign_Investor"), ("投信", "Investment_Trust")]:
        evaluate(f"{label} 5 日累計賣超（<= 第 5 百分位）", flow_events(name, 5, True), yi, "open1")
        evaluate(f"{label} 5 日累計買超（>= 第 95 百分位）", flow_events(name, 5, False), yi, "open1")
