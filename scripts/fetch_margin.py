"""抓證交所「信用交易統計」(上市整體融資融券餘額)，每個交易日一次請求，可中斷續抓
用法: python3 -I fetch_margin.py taiex.csv 2020-01-01 margin.csv"""
import sys, os, csv, json, time, urllib.request
taiex_csv, since, out = sys.argv[1], sys.argv[2], sys.argv[3]
days = [r["date"] for r in csv.DictReader(open(taiex_csv)) if r["date"] >= since]
done = {r["date"] for r in csv.DictReader(open(out))} if os.path.exists(out) else set()
new = not os.path.exists(out)
f = open(out, "a", newline=""); w = csv.writer(f)
if new: w.writerow(["date", "margin_units", "margin_amount_k", "short_units"])
num = lambda s: int(s.replace(",", ""))
for i, d in enumerate(days):
    if d in done: continue
    url = f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?date={d.replace('-', '')}&selectType=MS&response=json"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
                j = json.load(r)
            rows = {x[0]: x for x in j["tables"][0]["data"]}
            w.writerow([d, num(rows["融資(交易單位)"][5]), num(rows["融資金額(仟元)"][5]), num(rows["融券(交易單位)"][5])]); f.flush()
            break
        except Exception as e:
            print(d, "retry", attempt + 1, e, flush=True); time.sleep(15 * (attempt + 1))
    if i % 100 == 0: print(d, flush=True)
    time.sleep(2.2)
print("done")
