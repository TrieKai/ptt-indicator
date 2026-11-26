"""抓證交所「違約公告專區」：證券商申報投資人違約金額（108/2/1 起），每月一次請求
用法: python3 -I fetch_default.py 2019-02 2026-11 data/default_daily.csv data/default_stocks.csv
金額單位：元（申報日期 = 成交日後第 2 個營業日）"""
import sys, csv, json, time, calendar, datetime as dt, urllib.request
start, end, out_daily, out_stocks = sys.argv[1:5]
y, m = map(int, start.split("-")); ey, em = map(int, end.split("-"))
num = lambda s: int(str(s).replace(",", "")) if s not in (None, "") else None
roc = lambda s, sep: dt.date(int(s.split(sep)[0]) + 1911, int(s.split(sep)[1]), int(s.split(sep)[2])).isoformat()
daily, stocks = [], []
while (y, m) <= (ey, em):
    last = min(dt.date(y, m, calendar.monthrange(y, m)[1]), dt.date.today()).day   # 結束日不能超過今天，否則整月回傳空的
    url = f"https://www.twse.com.tw/rwd/zh/announcement/BFIGTU?startDate={y}{m:02d}01&endDate={y}{m:02d}{last}&response=json"
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
        if "違約金額" in (t.get("title") or ""):
            for r in t.get("data", []):
                if r[0] and "/" in r[0]: daily.append([roc(r[0], "/"), num(r[1]), num(r[2])])
        elif "揭露標準" in (t.get("title") or ""):
            for r in t.get("data", []):
                if r[0] and "." in r[0]: stocks.append([roc(r[0], "."), r[1], r[2], num(r[4])])
    print(f"{y}-{m:02d}: daily {len(daily)} stocks {len(stocks)}", flush=True)
    m += 1
    if m == 13: y, m = y + 1, 1
    time.sleep(3)
with open(out_daily, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date", "gross_amount", "net_amount"]); w.writerows(daily)
with open(out_stocks, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["date", "code", "name", "amount"]); w.writerows(stocks)
print("saved", len(daily), "days,", len(stocks), "stock disclosures")
