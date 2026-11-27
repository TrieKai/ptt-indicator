"""
敏感度測試：畢業文與恐慌溫度用「幾天的篇數」比較好？
不是為了挑最好的天數，而是看結果會不會只在某個天數才成立（只在一個天數成立 = 很可能是巧合）。

訊號（都用 09:00 分界、隔天開盤進場、10 個交易日內不重複）：
  畢業文熱度 ≥ 95   ：畢業／虧損文 W 日篇數，跟過去 250 個交易日比「比今天少的天數比例」≥ 0.95
  恐慌溫度 ≥ 95     ：創作文與畢業文的 W 日熱度平均 ≥ 0.95
  畢業文 W 日 ≥ 3 篇 ：儀表板用的固定篇數規則（現行 W=5）
畢業文跟儀表板同一套：〔心得〕原文＋內文判斷（loss_labels_ref.json／loss_labels.json）
評估：後 20 日報酬、扣掉跌深反彈的超額（同年度、前 5 日漲跌最接近的 10 天）、低點在 ±5 天內的比例

用法: python3 -I window_sensitivity.py data
"""
import sys, os, json, glob, re, csv, bisect, statistics as st, collections, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loss_rules import classify
D = sys.argv[1]; TZ = dt.timezone(dt.timedelta(hours=8))

def load_px(paths):
    out = {}
    for p in paths:
        if os.path.exists(p):
            for r in csv.DictReader(open(p)): out[r["date"]] = (float(r["open"]), float(r["close"]))
    return out
tw, tp = load_px([f"{D}/taiex.csv"]), load_px([f"{D}/tpex_early.csv", f"{D}/tpex.csv"])
days = sorted(d for d in tw if d >= "2017-06-01"); N = len(days)
PX = {"加權": ([tw[d][0] for d in days], [tw[d][1] for d in days]), "櫃買": ([tp.get(d, (None, None))[0] for d in days], [tp.get(d, (None, None))[1] for d in days])}
open_cut = [dt.datetime.combine(dt.date.fromisoformat(d), dt.time(9, 0), TZ).timestamp() for d in days]
seen = {}
for f in [f"{D}/graduation_search.json", f"{D}/creative_search.json"] + glob.glob(f"{D}/kw_*.json") + glob.glob(f"{D}/ptt_latest.json"):
    for p in json.load(open(f)): seen[p["id"]] = p
def daily(plist):
    c = [0] * N
    for p in plist:
        i = bisect.bisect_left(open_cut, p["ts"]) - 1
        if 0 <= i < N: c[i] += 1
    return c
def loss_posts():
    """跟 build_dashboard_data.py 同一套畢業文：〔心得〕原文、標題規則之後看內文判斷（歷史用參考標記，新文章用 AI 判斷，還沒判斷的照標題）"""
    from loss_rules import CAT
    lp = [p for p in seen.values() if not re.match(r"(Re|RE|Fw|FW):", p["title"]) and classify(p["title"])[0]]
    if not os.path.exists(f"{D}/loss_labels_ref.json"): return lp
    ref = json.load(open(f"{D}/loss_labels_ref.json", encoding="utf-8")); rows, cut = ref["rows"], ref.get("cutoff") or 0
    ai = json.load(open(f"{D}/loss_labels.json", encoding="utf-8")) if os.path.exists(f"{D}/loss_labels.json") else {}
    out = []
    for p in lp:
        if CAT(p["title"]) != "心得": continue
        a = ai.get(p["id"]) or {}
        if p["id"] in rows: ok = rows[p["id"]]["counts"]
        elif a.get("status") == "ok" and "counts" in a: ok = a["counts"]
        elif a.get("status") == "deleted": ok = False
        else: ok = p["ts"] >= cut
        if ok: out.append(p)
    return out
loss_d = daily(loss_posts())
crea_d = daily([p for p in seen.values() if p["title"].startswith("[創作]") and not re.match(r"(Re|RE|Fw|FW)\s*:", p["title"])])
start = days.index(next(d for d in days if d >= "2019-01-02"))
roll = lambda c, w: [sum(c[max(0, i - w + 1):i + 1]) for i in range(N)]
def heat(series):
    out = [None] * N
    for i in range(250, N):
        past = series[i - 250:i]; out[i] = sum(x < series[i] for x in past) / 250
    return out
def events(cond):
    ev, last = [], -99
    for i in range(start, N):
        if cond(i) and i - last >= 10: ev.append(i); last = i
    return ev
by_year = collections.defaultdict(list)
for i in range(start, N): by_year[days[i][:4]].append(i)
def stats(ev, ix):
    o, c = PX[ix]
    f = lambda i: c[i + 20] / o[i + 1] - 1 if i + 20 < N and o[i + 1] and c[i + 20] else None
    r5 = lambda i: c[i] / c[i - 5] - 1 if c[i] and c[i - 5] else None
    e = [i for i in ev if f(i) is not None and r5(i) is not None]
    if len(e) < 3: return None
    r = [f(i) for i in e]
    ctrl = [st.mean(f(j) for j in sorted((j for j in by_year[days[i][:4]] if abs(j - i) > 5 and f(j) is not None and r5(j) is not None),
                                         key=lambda j: abs(r5(j) - r5(i)))[:10]) for i in e]
    exc = [a - b for a, b in zip(r, ctrl)]
    lows = [min(range(i - 20, i + 21), key=lambda j: c[j]) - i for i in ev if i + 20 < N]
    return f"{len(ev):>3} 次 {st.mean(r)*100:>+6.2f}% {st.mean(exc)*100:>+6.2f}% {sum(x > 0 for x in exc):>2}/{len(exc):<2} {sum(abs(x) <= 5 for x in lows)/len(lows):>4.0%}"
def main():
    print(f"期間 {days[start]} ~ {days[-1]}｜欄位：次數、後 20 日報酬、超額、贏過配對、低點在 ±5 天內\n")
    print(f"{'訊號':<22}{'天數':>4} | {'加權':^34} | {'櫃買':^34}")
    for W in [1, 3, 5, 7, 10, 20]:
        lh, ch = heat(roll(loss_d, W)), heat(roll(crea_d, W))
        rows = [("畢業文熱度 ≥95", events(lambda i: lh[i] is not None and lh[i] >= 0.95)),
                ("恐慌溫度 ≥95", events(lambda i: lh[i] is not None and (lh[i] + ch[i]) / 2 >= 0.95))]
        lw = roll(loss_d, W)
        rows.append((f"畢業文 {W} 日 ≥3 篇" + ("（現行）" if W == 5 else ""), events(lambda i: lw[i] >= 3)))
        for name, ev in rows:
            print(f"{name:<22}{W:>4} | {stats(ev, '加權') or '樣本太少':<34} | {stats(ev, '櫃買') or '樣本太少':<34}")
        print()

if __name__ == '__main__':
    main()
