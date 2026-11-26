"""抓期交所官方資料（CSV 為 Big5）
  pc   臺指選擇權 Put/Call Ratio（每月一次請求）→ date,put_vol,call_vol,pc_vol,put_oi,call_oi,pc_oi
  fut  三大法人臺股期貨(TXF) 外資及陸資未平倉（每年一次請求）→ date,foreign_net_oi,foreign_net_oi_amt_k
用法: python3 -I fetch_taifex.py pc 2017-06 2026-11 data/taifex_pc.csv
      python3 -I fetch_taifex.py fut 2017 2026 data/taifex_fut.csv"""
import sys, csv, io, time, calendar, datetime as dt, urllib.request, urllib.parse
kind, a, b, out = sys.argv[1:5]
def post(url, form):
    data = urllib.parse.urlencode(form).encode()
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
                return r.read().decode("big5", errors="replace")
        except Exception as e:
            print("retry", attempt + 1, e, flush=True); time.sleep(15 * (attempt + 1))
    sys.exit("failed " + str(form))
num = lambda s: float(s.replace(",", "")) if s.strip() not in ("", "-") else None
iso = lambda s: dt.date(*map(int, s.strip().split("/"))).isoformat()
rows = {}
today = dt.date.today()
if kind == "pc":
    y, m = map(int, a.split("-")); ey, em = map(int, b.split("-"))
    while (y, m) <= (ey, em):
        end = min(dt.date(y, m, calendar.monthrange(y, m)[1]), today)
        t = post("https://www.taifex.com.tw/cht/3/pcRatioDown", {"queryStartDate": f"{y}/{m:02d}/01", "queryEndDate": end.strftime("%Y/%m/%d")})
        for r in list(csv.reader(io.StringIO(t)))[1:]:
            if len(r) >= 7 and "/" in r[0]: rows[iso(r[0])] = [num(x) for x in r[1:7]]
        print(f"{y}-{m:02d} total {len(rows)}", flush=True)
        m += 1
        if m == 13: y, m = y + 1, 1
        time.sleep(3)
    header = ["date", "put_vol", "call_vol", "pc_vol", "put_oi", "call_oi", "pc_oi"]
else:
    for y in range(int(a), int(b) + 1):
        end = min(dt.date(y, 12, 31), today)
        t = post("https://www.taifex.com.tw/cht/3/futContractsDateDown",
                 {"queryStartDate": f"{y}/01/01", "queryEndDate": end.strftime("%Y/%m/%d"), "commodityId": "TXF"})
        for r in list(csv.reader(io.StringIO(t)))[1:]:
            if len(r) >= 15 and "/" in r[0] and r[2].strip() == "外資及陸資":
                rows[iso(r[0])] = [num(r[13]), num(r[14])]
        print(f"{y} total {len(rows)}", flush=True)
        time.sleep(3)
    header = ["date", "foreign_net_oi", "foreign_net_oi_amt_k"]
with open(out, "w", newline="") as f:
    w = csv.writer(f); w.writerow(header)
    for k in sorted(rows): w.writerow([k] + rows[k])
print("saved", len(rows))
