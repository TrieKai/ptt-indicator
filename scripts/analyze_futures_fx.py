"""外資臺股期貨淨未平倉跟指數高低、全市場未平倉、匯率、外資現貨買賣超的關係
用法: python3 -I analyze_futures_fx.py data"""
import sys, csv, json, statistics as st, collections
D = sys.argv[1]
rd = lambda f, k: {r["date"]: float(r[k]) for r in csv.DictReader(open(f"{D}/{f}")) if r[k]}
tw, net, tot, fx, tv = rd("taiex.csv", "close"), rd("futures_foreign.csv", "foreign_net_oi"), rd("tx_total_oi.csv", "total_oi"), rd("usdtwd.csv", "usdtwd"), rd("turnover.csv", "turnover")
spot = collections.defaultdict(float)
for r in json.load(open(f"{D}/finmind_inst.json"))["data"]:
    if r["name"] == "Foreign_Investor": spot[r["date"]] = r["buy"] - r["sell"]
days = sorted(d for d in net if d in tw and d in tot and d in fx and tv.get(d) and d in spot)
def corr(a, b):
    ma, mb = st.mean(a), st.mean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return num / (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
print(f"期間 {days[0]} ~ {days[-1]}，{len(days)} 天\n")
print("== 每年平均")
print(f"{'年':<6}{'加權':>9}{'外資淨未平倉(口)':>16}{'全市場未平倉':>12}{'淨空單佔比':>10}{'淨部位名目(億)':>14}{'美元兌台幣':>10}")
by = collections.defaultdict(list)
for d in days: by[d[:4]].append(d)
for y in sorted(by):
    ds = by[y]; m = lambda f: st.mean(f(d) for d in ds)
    print(f"{y:<6}{m(lambda d: tw[d]):>9,.0f}{m(lambda d: net[d]):>16,.0f}{m(lambda d: tot[d]):>12,.0f}{m(lambda d: net[d] / tot[d]) * 100:>9.0f}%"
          f"{m(lambda d: net[d] * 200 * tw[d] / 1e8):>14,.0f}{m(lambda d: fx[d]):>10.2f}")
print("\n== 水準的相關係數（整段期間）")
print(f"  外資淨未平倉(口) vs 加權指數       {corr([net[d] for d in days], [tw[d] for d in days]):+.2f}")
print(f"  淨空單佔全市場比例 vs 加權指數     {corr([net[d] / tot[d] for d in days], [tw[d] for d in days]):+.2f}")
print(f"  外資淨未平倉(口) vs 美元兌台幣     {corr([net[d] for d in days], [fx[d] for d in days]):+.2f}")
print(f"  加權指數 vs 美元兌台幣              {corr([tw[d] for d in days], [fx[d] for d in days]):+.2f}")
print("\n== 每日變化的相關係數（看同一天誰跟著誰動）")
ch = lambda s, i: s[days[i]] / s[days[i - 1]] - 1
dn = lambda i: net[days[i]] - net[days[i - 1]]
idx = range(1, len(days))
rows = {"加權漲跌%": [ch(tw, i) for i in idx], "台幣貶值%(美元兌台幣變化)": [ch(fx, i) for i in idx],
        "外資期貨淨部位變化(口)": [dn(i) for i in idx], "外資現貨買賣超/成交額": [spot[days[i]] / tv[days[i]] for i in idx]}
ks = list(rows)
for a in range(len(ks)):
    for b in range(a + 1, len(ks)):
        print(f"  {ks[a]:<24} vs {ks[b]:<24} {corr(rows[ks[a]], rows[ks[b]]):+.2f}")
print("\n== 5 日變化的相關係數")
i5 = range(5, len(days))
c5 = lambda s, i: s[days[i]] / s[days[i - 5]] - 1
r5 = {"加權 5 日漲跌": [c5(tw, i) for i in i5], "台幣 5 日貶值": [c5(fx, i) for i in i5],
      "外資期貨 5 日淨部位變化": [net[days[i]] - net[days[i - 5]] for i in i5],
      "外資現貨 5 日買賣超/成交額": [sum(spot[days[j]] for j in range(i - 4, i + 1)) / sum(tv[days[j]] for j in range(i - 4, i + 1)) for i in i5]}
ks = list(r5)
for a in range(len(ks)):
    for b in range(a + 1, len(ks)):
        print(f"  {ks[a]:<22} vs {ks[b]:<24} {corr(r5[ks[a]], r5[ks[b]]):+.2f}")
