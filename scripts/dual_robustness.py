"""「畢業文＋創作文同時亮燈」穩不穩：(1) 前後兩段分開看 (2) 相鄰門檻的格子
用法: python3 -I dual_robustness.py data"""
import sys, os, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import window_sensitivity as w
L5, C5 = w.roll(w.loss_d, 5), w.roll(w.crea_d, 5)
ch = w.heat(C5)
def ret20(ev, ix="加權"):
    o, c = w.PX[ix]
    return [c[i + 20] / o[i + 1] - 1 for i in ev if i + 20 < w.N]
cond = lambda k, hc: (lambda i: L5[i] >= k and ch[i] is not None and ch[i] >= hc)
ev = w.events(cond(3, 0.90))
print("== 前後兩段（同時亮燈：畢業文 ≥3、創作文熱度 ≥90）")
for name, lo, hi in [("2019–2022", "2019", "2022-12-31"), ("2023–2026", "2023", "2026-12-31")]:
    e = [i for i in ev if lo <= w.days[i] <= hi]
    r = ret20(e)
    print(f"  {name}：{len(e)} 次，日期 {' '.join(w.days[i] for i in e)}；有後續資料 {len(r)} 次，後 20 日平均 {st.mean(r)*100:+.2f}%，上漲 {sum(x > 0 for x in r)}/{len(r)}" if r else f"  {name}：{len(e)} 次")
print("\n== 相鄰門檻：後 20 日加權平均（次數）｜列＝畢業文 5 日篇數，欄＝創作文熱度")
hs = [0.80, 0.85, 0.90, 0.95]
print("        " + "".join(f"{'熱度≥' + str(int(h*100)):>14}" for h in hs))
for k in [2, 3, 4]:
    cells = []
    for h in hs:
        r = ret20(w.events(cond(k, h)))
        cells.append(f"{st.mean(r)*100:+.1f}%（{len(r)}）" if r else "—")
    print(f"畢業文≥{k}  " + "".join(f"{c:>14}" for c in cells))
r_all = [w.PX['加權'][1][i + 20] / w.PX['加權'][0][i + 1] - 1 for i in range(w.start, w.N - 20)]
print(f"\n對照：任一天隔天開盤買進，後 20 日平均 {st.mean(r_all)*100:+.2f}%")
