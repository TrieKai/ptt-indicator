"""抓櫃買中心「櫃買指數」月查詢（官方），存成 CSV: date,open,high,low,close
用法: python3 -I fetch_tpex.py 2019-06 2026-11 data/tpex.csv"""
import sys, json, time, csv, datetime as dt, urllib.request
start, end, out = sys.argv[1:4]
y, m = map(int, start.split("-")); ey, em = map(int, end.split("-"))
rows = []
num = lambda s: float(s.replace(",", ""))
while (y, m) <= (ey, em):
    url = f"https://www.tpex.org.tw/www/zh-tw/indexInfo/inx?date={y}%2F{m:02d}%2F01&response=json"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
                j = json.load(r)
            break
        except Exception as e:
            print(f"{y}-{m:02d} retry {attempt+1}: {e}", flush=True); time.sleep(15 * (attempt + 1))
    else:
        sys.exit(f"failed at {y}-{m:02d}")
    for t in j.get("tables", []):
        for r in t.get("data", []):
            d = dt.date(*map(int, r[0].split("/")))
            rows.append([d.isoformat(), num(r[1]), num(r[2]), num(r[3]), num(r[4])])
    print(f"{y}-{m:02d}: total {len(rows)}", flush=True)
    m += 1
    if m == 13: y, m = y + 1, 1
    time.sleep(3)
with open(out, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date", "open", "high", "low", "close"]); w.writerows(rows)
print("saved", len(rows))
