"""抓臺灣證交所「發行量加權股價指數歷史資料」(每月一次請求)，存成 CSV: date,open,high,low,close"""
import sys, json, time, csv, datetime as dt, urllib.request

start, end, out = sys.argv[1], sys.argv[2], sys.argv[3]          # YYYY-MM YYYY-MM path
y, m = map(int, start.split("-")); ey, em = map(int, end.split("-"))
rows = []
while (y, m) <= (ey, em):
    url = f"https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?date={y}{m:02d}01&response=json"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
                d = json.load(r)
            break
        except Exception as e:
            print(f"{y}-{m:02d} retry {attempt+1}: {e}", flush=True); time.sleep(10)
    else:
        sys.exit(f"failed at {y}-{m:02d}")
    for r in d.get("data", []):
        ry, rm, rd = map(int, r[0].split("/"))
        rows.append([dt.date(ry + 1911, rm, rd).isoformat()] + [float(x.replace(",", "")) for x in r[1:5]])
    print(f"{y}-{m:02d}: {len(d.get('data', []))} days", flush=True)
    m += 1
    if m == 13: y, m = y + 1, 1
    time.sleep(2.5)                       # 證交所有頻率限制，放慢
with open(out, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date", "open", "high", "low", "close"]); w.writerows(rows)
print("saved", len(rows), "rows")
