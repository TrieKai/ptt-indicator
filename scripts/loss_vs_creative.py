"""畢業文和創作文各自代表什麼？拆開測：單獨、同時出現、只有其中一種
（09:00 分界、隔天開盤進場、10 個交易日內不重複；欄位：次數、後 20 日、超額、贏過配對、低點在 ±5 天內）
另外看「亮燈後還會再跌多少」與「低點在亮燈前還是後」，分辨是『恐慌進行中』還是『恐慌尾聲』
用法: python3 -I loss_vs_creative.py data"""
import sys, os, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import window_sensitivity as w
L5, C5 = w.roll(w.loss_d, 5), w.roll(w.crea_d, 5)
lh, ch = w.heat(L5), w.heat(C5)
def timing(ev):
    c = w.PX["加權"][1]
    e = [i for i in ev if i + 20 < w.N]
    lows = [min(range(i - 20, i + 21), key=lambda j: c[j]) - i for i in e]
    deep = [min(c[i + 1:i + 21]) / c[i] - 1 for i in e]
    return (f"低點在亮燈前 {sum(x < -1 for x in lows)}／附近 {sum(abs(x) <= 1 for x in lows)}／之後 {sum(x > 1 for x in lows)} 次，"
            f"之後 20 天平均再跌 {st.mean(deep)*100:.1f}%，再跌超過 5% {sum(x <= -0.05 for x in deep)}/{len(deep)}") if e else "-"
tests = [
    ("畢業文 5 日 ≥3 篇（單獨）", lambda i: L5[i] >= 3),
    ("創作文熱度 ≥95（單獨）", lambda i: ch[i] is not None and ch[i] >= 0.95),
    ("畢業文 ≥3 且 創作文熱度 ≥90（同時）", lambda i: L5[i] >= 3 and ch[i] is not None and ch[i] >= 0.90),
    ("畢業文 ≥3 但 創作文熱度 <90（只有畢業文）", lambda i: L5[i] >= 3 and ch[i] is not None and ch[i] < 0.90),
    ("創作文熱度 ≥95 但 畢業文 5 日 0 篇（只有創作文）", lambda i: ch[i] is not None and ch[i] >= 0.95 and L5[i] == 0),
    ("恐慌溫度 ≥95（兩者平均，現行）", lambda i: lh[i] is not None and (lh[i] + ch[i]) / 2 >= 0.95),
]
print(f"期間 {w.days[w.start]} ~ {w.days[-1]}\n")
for name, cond in tests:
    ev = w.events(cond)
    print(f"{name}\n   加權：{w.stats(ev, '加權') or '樣本太少'}\n   櫃買：{w.stats(ev, '櫃買') or '樣本太少'}\n   時機（加權）：{timing(ev)}")
    print("   日期：", " ".join(w.days[i][2:] for i in ev[-12:]), "\n")
