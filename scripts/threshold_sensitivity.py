"""敏感度測試：畢業文篇數門檻、創作文篇數門檻、恐慌溫度門檻換成別的數字，結果還在不在？
用法: python3 -I threshold_sensitivity.py data"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import window_sensitivity as w
L5, C1 = w.roll(w.loss_d, 5), w.crea_d
base = lambda i: sum(C1[max(0, i - 60):i]) / 60
lh, ch = w.heat(w.roll(w.loss_d, 5)), w.heat(w.roll(w.crea_d, 5))
print(f"期間 {w.days[w.start]} ~ {w.days[-1]}｜欄位：次數、後 20 日報酬、超額、贏過配對、低點在 ±5 天內\n")
print(f"{'訊號':<30} | {'加權':^34} | {'櫃買':^34}")
tests = [(f"畢業文 5 日 ≥{k} 篇" + ("（現行）" if k == 3 else ""), (lambda k: lambda i: L5[i] >= k)(k)) for k in [1, 2, 3, 4, 5]]
tests += [("", None)]
tests += [(f"創作文當天 ≥{k} 篇且 ≥4 倍 60 日平均" + ("（現行）" if k == 5 else ""), (lambda k: lambda i: C1[i] >= k and C1[i] >= 4 * max(base(i), 0.1))(k)) for k in [3, 5, 8]]
tests += [("創作文當天 ≥5 篇（不看倍數）", lambda i: C1[i] >= 5)]
tests += [("", None)]
tests += [(f"恐慌溫度 ≥{t}" + ("（現行）" if t == 95 else ""), (lambda t: lambda i: lh[i] is not None and (lh[i] + ch[i]) / 2 * 100 >= t)(t)) for t in [80, 85, 90, 95, 98]]
for name, cond in tests:
    if cond is None: print(); continue
    ev = w.events(cond)
    print(f"{name:<30} | {w.stats(ev, '加權') or '樣本太少':<34} | {w.stats(ev, '櫃買') or '樣本太少':<34}")
