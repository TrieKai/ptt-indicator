"""雙重確認每一次亮燈時，大盤距 60 日高點跌了多少；加上「大盤真的有跌」的條件後結果如何
用法: python3 -I dual_drawdown.py data"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import window_sensitivity as w
L5, C5 = w.roll(w.loss_d, 5), w.roll(w.crea_d, 5)
ch = w.heat(C5)
def dd(ix, i):
    c = w.PX[ix][1]; win = [x for x in c[max(0, i - 60):i + 1] if x]
    return c[i] / max(win) - 1
base = lambda i: L5[i] >= 3 and ch[i] is not None and ch[i] >= 0.90
print("== 雙重確認每一次：亮燈當天距 60 日高點")
for i in w.events(base):
    o, c = w.PX["加權"]
    r20 = f"{(c[i+20]/o[i+1]-1)*100:+.1f}%" if i + 20 < w.N else "—"
    print(f"  {w.days[i]}  加權距高點 {dd('加權', i)*100:+.1f}%  櫃買距高點 {dd('櫃買', i)*100:+.1f}%  加權後 20 日 {r20}")
print()
for name, extra in [("加上：加權距 60 日高點 ≤ −5%", lambda i: dd("加權", i) <= -0.05),
                    ("加上：加權距 60 日高點 ≤ −8%", lambda i: dd("加權", i) <= -0.08),
                    ("加上：加權或櫃買距 60 日高點 ≤ −8%", lambda i: min(dd("加權", i), dd("櫃買", i)) <= -0.08)]:
    ev = w.events(lambda i: base(i) and extra(i))
    print(f"{name}：{' '.join(w.days[i][2:] for i in ev)}\n   加權：{w.stats(ev, '加權') or '樣本太少'}\n   櫃買：{w.stats(ev, '櫃買') or '樣本太少'}")
