"""
鄉民恐慌貪婪指數（0–100，原型）：只用 PTT 股票版標題
  0 = 極度恐慌、50 = 平常、100 = 極度貪婪（反過來看，100 − 指數 就是「鄉民恐慌度」）

成分（每天，前一交易日 13:30 後 ~ 當天 13:30 的原文算當天）：
  恐慌面：創作文 5 日篇數、畢業／虧損文 5 日篇數（loss_rules.py）
  貪婪面：過熱文 5 日篇數（財富自由、人生畢業、歐印、噴、翻倍、創新高、賺爛、上車）
每個成分換成「熱度」= 過去 250 個交易日中，比今天少的天數比例（0–1）。沒有文章時熱度是 0。
指數 = 50 + 50 × (貪婪熱度 − 恐慌熱度的平均)，限制在 0–100。

用法: python3 -I ptt_fear_greed.py data out.csv
"""
import sys, os, json, glob, re, csv, bisect, datetime as dt, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loss_rules import classify

D, OUT = sys.argv[1], sys.argv[2]
TZ = dt.timezone(dt.timedelta(hours=8))
px = [(dt.date.fromisoformat(r["date"]), float(r["close"])) for r in csv.DictReader(open(f"{D}/taiex.csv"))]
days = [d for d, _ in px if d >= dt.date(2017, 6, 1)]; close = {d: c for d, c in px}
cut = [dt.datetime.combine(d, dt.time(13, 30), TZ).timestamp() for d in days]
seen = {}
for f in [f"{D}/graduation_search.json", f"{D}/creative_search.json"] + glob.glob(f"{D}/kw_*.json") + glob.glob(f"{D}/greed_*.json") + glob.glob(f"{D}/ptt_latest.json"):
    for p in json.load(open(f)): seen[p["id"]] = p
orig = [p for p in seen.values() if not re.match(r"(Re|RE|Fw|FW)\s*:", p["title"])]
cat = lambda t: (re.match(r"[\[［]([^\]］}]+)[\]］}]", t) or [None, ""])[1]
GREED = ["財富自由", "人生畢業", "歐印", "噴", "翻倍", "創新高", "賺爛", "上車"]
groups = {
    "creative": [p for p in orig if p["title"].startswith("[創作]")],
    "loss": [p for p in orig if classify(p["title"])[0]],
    "hot": [p for p in orig if cat(p["title"]) not in ("新聞", "情報", "公告") and any(k in p["title"] for k in GREED)
            and not any(k in p["title"] for k in ["斷頭", "賠光", "歸零", "追繳", "爆倉"])],
}
N = len(days)
def counts(plist):
    c = [0] * N
    for p in plist:
        i = bisect.bisect_left(cut, p["ts"])
        if i < N: c[i] += 1
    return [sum(c[max(0, i - 4):i + 1]) for i in range(N)]          # 5 日篇數
c5 = {k: counts(v) for k, v in groups.items()}
def heat(series, i):
    past = series[max(0, i - 250):i]
    return sum(x < series[i] for x in past) / len(past) if len(past) >= 250 else None
rows = []
for i in range(N):
    h = {k: heat(c5[k], i) for k in c5}
    if None in h.values(): continue
    fear = (h["creative"] + h["loss"]) / 2
    idx = max(0, min(100, 50 + 50 * (h["hot"] - fear)))
    rows.append({"date": days[i].isoformat(), "index": round(idx, 1), "fear_heat": round(fear * 100, 1), "greed_heat": round(h["hot"] * 100, 1),
                 "creative_5d": c5["creative"][i], "loss_5d": c5["loss"][i], "hot_5d": c5["hot"][i], "taiex": close[days[i]]})
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

# ---------- 檢查 ----------
rows = [r for r in rows if r["date"] >= "2019-01-02"]
cl = [r["taiex"] for r in rows]; ix = [r["index"] for r in rows]
def corr(a, b):
    ma, mb = st.mean(a), st.mean(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
print(f"期間 {rows[0]['date']} ~ {rows[-1]['date']}，{len(rows)} 天 | 最新 {rows[-1]['date']} 指數 {rows[-1]['index']}（恐慌熱度 {rows[-1]['fear_heat']}、貪婪熱度 {rows[-1]['greed_heat']}）")
dist = [sum(lo <= x < hi for x in ix) for lo, hi in [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]]
print("分布：0–20 {} 天｜20–40 {}｜40–60 {}｜60–80 {}｜80–100 {}".format(*dist))
past5 = [cl[i] / cl[i - 5] - 1 for i in range(5, len(cl))]; past20 = [cl[i] / cl[i - 20] - 1 for i in range(20, len(cl))]
print(f"跟「過去」走勢的相關（同步）：前 5 日漲跌 {corr(ix[5:], past5):+.2f}｜前 20 日漲跌 {corr(ix[20:], past20):+.2f}")
f20 = [cl[i + 20] / cl[i] - 1 for i in range(len(cl) - 20)]; f60 = [cl[i + 60] / cl[i] - 1 for i in range(len(cl) - 60)]
print(f"跟「未來」走勢的相關（預測）：後 20 日 {corr(ix[:len(f20)], f20):+.2f}｜後 60 日 {corr(ix[:len(f60)], f60):+.2f}")
print("\n指數區間     天數   後20日平均   上漲比例   後60日平均")
for lo, hi in [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]:
    s20 = [f20[i] for i in range(len(f20)) if lo <= ix[i] < hi]; s60 = [f60[i] for i in range(len(f60)) if lo <= ix[i] < hi]
    if s20: print(f"{lo:>3}–{min(hi, 100):<3}   {len(s20):>6} {st.mean(s20)*100:>+10.2f}% {sum(x > 0 for x in s20)/len(s20):>9.0%} {st.mean(s60)*100 if s60 else float('nan'):>+10.2f}%")
print(f"全部       {len(f20):>6} {st.mean(f20)*100:>+10.2f}% {sum(x > 0 for x in f20)/len(f20):>9.0%} {st.mean(f60)*100:>+10.2f}%")
low = [r for r in rows if r["index"] <= 10]
print("\n指數 ≤10 的日子（列出各段第一天）：", [r["date"] for k, r in enumerate(low) if k == 0 or (dt.date.fromisoformat(r["date"]) - dt.date.fromisoformat(low[k - 1]["date"])).days > 14])
