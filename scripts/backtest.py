"""
回測：PTT 股票版 [創作] 文爆量日之後，加權指數的報酬

用法: python3 -I backtest.py taiex.csv creative_search.json out_prefix MIN_N MULT [SINCE=2020-01-01]

- 訊號歸屬：前一交易日 13:30 之後 ~ 當天 13:30 的文章算「當天」，收盤時已知，不偷看未來
  （週末、連假的文章會累積到下一個交易日）
- 爆量：當天篇數 >= MIN_N 且 >= MULT x 前 60 個交易日平均
- 去重：距離「上一個已記錄事件」不到 10 個交易日的爆量日略過（每一波只取第一個警示日）
- 對照 1：同年度的交易日隨機抽樣 10,000 次（控制牛熊年份），算單尾 p 值
- 對照 2：「單日跌 3% 以上」的交易日（看創作文是否只是大跌的影子）
限制：只看得到「沒被刪」的文章；事件數少，p 值僅供參考
"""
import sys, json, csv, random, statistics as st, datetime as dt, bisect, collections

taiex_csv, posts_json, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
MIN_N, MULT = int(sys.argv[4]), float(sys.argv[5])
SINCE = dt.date.fromisoformat(sys.argv[6] if len(sys.argv) > 6 else "2020-01-01")
BASE, GAP, HORIZONS = 60, 10, [1, 5, 20, 60]
TZ = dt.timezone(dt.timedelta(hours=8))

px = [(dt.date.fromisoformat(r["date"]), float(r["close"])) for r in csv.DictReader(open(taiex_csv))]
days = [d for d, _ in px]; close = [c for _, c in px]
cut = [dt.datetime.combine(d, dt.time(13, 30), TZ).timestamp() for d in days]
posts = [p for p in json.load(open(posts_json)) if p["title"].startswith("[創作]")]
cnt = [0] * len(days)
for p in posts:
    i = bisect.bisect_left(cut, p["ts"])
    if i < len(days): cnt[i] += 1
start = bisect.bisect_left(days, SINCE) + BASE

fwd = lambda i, h: close[i + h] / close[i] - 1 if i + h < len(close) else None
ret = lambda i, h: close[i] / close[i - h] - 1
base = lambda i: sum(cnt[i - BASE:i]) / BASE

events, last = [], -10**9
for i in range(start, len(days)):
    if cnt[i] >= MIN_N and cnt[i] >= MULT * max(base(i), 0.1) and i - last >= GAP:
        events.append(i); last = i

with open(prefix + "_events.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["date", "creative_posts", "baseline_60d", "ret_same_day", "ret_past_5d"] + [f"fwd_{h}d" for h in HORIZONS])
    for i in events:
        w.writerow([days[i], cnt[i], round(base(i), 2), round(ret(i, 1), 4), round(ret(i, 5), 4)] +
                   [None if fwd(i, h) is None else round(fwd(i, h), 4) for h in HORIZONS])
with open(prefix + "_daily.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date", "creative_posts", "taiex_close"])
    for i in range(start - BASE, len(days)): w.writerow([days[i], cnt[i], close[i]])

pct = lambda x: f"{x*100:+.2f}%"
print(f"期間 {days[start]} ~ {days[-1]}（{len(days)-start} 個交易日）| [創作] 原文 {len(posts)} 篇")
print(f"爆量：當天 >= {MIN_N} 篇且 >= {MULT:g} 倍 60 日平均 → 事件 {len(events)} 個")
print("事件日：" + ", ".join(f"{days[i]}({cnt[i]})" for i in events))

by_year = collections.defaultdict(list)
for i in range(start, len(days)): by_year[days[i].year].append(i)
drops = [i for i in range(start, len(days)) if ret(i, 1) <= -0.03]
random.seed(42)
print(f"\n{'期間':<5}{'事件平均':>9}{'中位數':>9}{'上漲比例':>8} |{'同年度隨機平均':>12}{'p值':>8} |{'全部日平均':>10} |{'大跌日(n=' + str(len(drops)) + ')平均':>14}")
for h in HORIZONS:
    ev = [i for i in events if fwd(i, h) is not None]
    if not ev: continue
    r = [fwd(i, h) for i in ev]; m = st.mean(r)
    pools = [[j for j in by_year[days[i].year] if fwd(j, h) is not None] for i in ev]
    sims = [st.mean(fwd(random.choice(p), h) for p in pools) for _ in range(10000)]
    allp = [fwd(i, h) for i in range(start, len(days)) if fwd(i, h) is not None]
    dr = [fwd(i, h) for i in drops if fwd(i, h) is not None]
    print(f"後{h:>2}日 {pct(m):>9}{pct(st.median(r)):>9}{sum(x > 0 for x in r)/len(r):>8.0%} |"
          f"{pct(st.mean(sims)):>12}{sum(s >= m for s in sims)/len(sims):>8.3f} |{pct(st.mean(allp)):>10} |{pct(st.mean(dr)):>14}   (n={len(r)})")
