"""用「鄉民恐慌溫度」判斷落底準不準：溫度第一次衝到門檻（10 個交易日內不重複）當事件
看：之後報酬（跟同年度隨機日、前 5 日漲跌最接近的日子比）、低點是不是就在附近、之後還會再跌多少
用法: python3 -I eval_thermometer.py data"""
import sys, csv, random, statistics as st, collections
D = sys.argv[1]; random.seed(42)
rows = [r for r in csv.DictReader(open(f"{D}/ptt_fear_greed.csv")) if r["date"] >= "2019-01-02"]
tp = {}
for f in [f"{D}/tpex_early.csv", f"{D}/tpex.csv"]:
    for r in csv.DictReader(open(f)): tp[r["date"]] = float(r["close"])
days = [r["date"] for r in rows]; N = len(days)
PX = {"加權": [float(r["taiex"]) for r in rows], "櫃買": [tp.get(d) for d in days]}
fear = [float(r["fear_heat"]) for r in rows]; idx = [float(r["index"]) for r in rows]
def events(cond):
    ev, last = [], -99
    for i in range(N):
        if cond(i) and i - last >= 10: ev.append(i); last = i
    return ev
by_year = collections.defaultdict(list)
for i, d in enumerate(days): by_year[d[:4]].append(i)
def evaluate(name, ev):
    print(f"\n== {name}：{len(ev)} 次")
    for ix, c in PX.items():
        f = lambda i, h: c[i + h] / c[i] - 1 if i + h < N and c[i] and c[i + h] else None
        r5 = lambda i: c[i] / c[i - 5] - 1 if i >= 5 else None
        line = []
        for h in (5, 20, 60):
            e = [i for i in ev if f(i, h) is not None and r5(i) is not None]
            if len(e) < 3: continue
            r = [f(i, h) for i in e]
            sims = [st.mean(f(random.choice([j for j in by_year[days[i][:4]] if f(j, h) is not None]), h) for i in e) for _ in range(3000)]
            ctrl = [st.mean(f(j, h) for j in sorted((j for j in by_year[days[i][:4]] if abs(j - i) > 5 and f(j, h) is not None and r5(j) is not None),
                                                    key=lambda j: abs(r5(j) - r5(i)))[:10]) for i in e]
            exc = [a - b for a, b in zip(r, ctrl)]
            line.append(f"後{h}日 {st.mean(r)*100:+.2f}%（上漲 {sum(x > 0 for x in r)/len(r):.0%}，超額 {st.mean(exc)*100:+.2f}%，贏配對 {sum(x > 0 for x in exc)}/{len(exc)}，p={sum(s >= st.mean(r) for s in sims)/len(sims):.2f}）")
        lows = [min(range(i - 20, i + 21), key=lambda j: c[j]) - i for i in ev if 20 <= i < N - 20]
        deep = [min(c[i + 1:i + 21]) / c[i] - 1 for i in ev if i < N - 20]
        print(f"  {ix}：" + "；".join(line))
        print(f"        真正低點距亮燈中位數 {st.median(lows):+.0f} 天｜低點在 ±5 天內 {sum(abs(x) <= 5 for x in lows)/len(lows):.0%}｜之後 20 天平均再跌 {st.mean(deep)*100:.2f}%｜再跌超過 5% {sum(x <= -0.05 for x in deep)/len(deep):.0%}")
print(f"期間 {days[0]} ~ {days[-1]}")
evaluate("恐慌溫度 ≥ 90", events(lambda i: fear[i] >= 90))
evaluate("恐慌溫度 ≥ 95", events(lambda i: fear[i] >= 95))
evaluate("鄉民指數 ≤ 10（含過熱文，原型）", events(lambda i: idx[i] <= 10))
evaluate("對照：加權單日跌 ≥ 3%", events(lambda i: i > 0 and PX["加權"][i] / PX["加權"][i - 1] - 1 <= -0.03))
