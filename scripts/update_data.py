"""
增量更新所有資料來源，再重算儀表板資料。
每個來源只抓「上個月 1 日到今天」，合併進既有檔案：重疊的日期以新抓的為準，更早的資料保留不動。
某個來源失敗時保留舊資料、繼續下一個，最後列出哪些成功、哪些失敗。

用法: python3 -I scripts/update_data.py data dashboard/data
      python3 -I scripts/update_data.py data dashboard/data --only ptt     # 只更新 PTT（盤中用）
FinMind 的資料直接併進 CSV（不留原始 JSON）。
來源：證交所（加權指數、違約公告）、櫃買中心（櫃買指數）、期交所（P/C 比）、FinMind（融資、三大法人、成交金額、
      外資臺指期、臺指期全市場未平倉、美元匯率）、CBOE（VIX）、PTT 股票版列表頁
"""
import sys, os, csv, json, time, shutil, tempfile, subprocess, collections, datetime as dt, urllib.request

D, OUT = sys.argv[1], sys.argv[2]
ONLY = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
HERE = os.path.dirname(os.path.abspath(__file__))
TZ = dt.timezone(dt.timedelta(hours=8))
today = dt.datetime.now(TZ).date()
m0 = (today.replace(day=1) - dt.timedelta(days=1)).replace(day=1)        # 上個月 1 日
ym = lambda d: f"{d.year}-{d.month:02d}"
TMP = tempfile.mkdtemp(prefix="ptt_update_")
report = []

def run(*args):
    subprocess.run([sys.executable, "-I", os.path.join(HERE, args[0]), *args[1:]], check=True, stdout=subprocess.DEVNULL)

def merge_csv(path, new_path, date_col="date"):
    """把 new_path 的列併進 path：new 涵蓋的最早日期之後，舊的列全部換成新的（同一天多列的檔案也適用）"""
    new = list(csv.DictReader(open(new_path)))
    if not new: raise RuntimeError("抓到 0 列")
    old = list(csv.DictReader(open(path))) if os.path.exists(path) else []
    cut = min(r[date_col] for r in new)
    keep = [r for r in old if r[date_col] < cut]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(new[0].keys())); w.writeheader(); w.writerows(keep + new)
    return f"{len(keep) + len(new) - len(old):+d} 列，最新 {max(r[date_col] for r in new)}"

def step(name, fn):
    if ONLY and name.split(" ")[0] not in ONLY: return
    t = time.time()
    try:
        msg = fn(); report.append((name, "成功", msg, time.time() - t))
    except Exception as e:
        report.append((name, "失敗（保留舊資料）", f"{type(e).__name__}: {e}", time.time() - t))
    print(f"{report[-1][0]:<22} {report[-1][1]:<10} {report[-1][2]}", flush=True)

# ---------- 證交所、櫃買中心、期交所（每月一次請求） ----------
def taiex():
    run("fetch_taiex.py", ym(m0), ym(today), f"{TMP}/taiex.csv"); return merge_csv(f"{D}/taiex.csv", f"{TMP}/taiex.csv")
def tpex():
    run("fetch_tpex.py", ym(m0), ym(today), f"{TMP}/tpex.csv"); return merge_csv(f"{D}/tpex.csv", f"{TMP}/tpex.csv")
def taifex_pc():
    run("fetch_taifex.py", "pc", ym(m0), ym(today), f"{TMP}/pc.csv"); return merge_csv(f"{D}/taifex_pc.csv", f"{TMP}/pc.csv")
def default():
    run("fetch_default.py", ym(m0), ym(today), f"{TMP}/dd.csv", f"{TMP}/ds.csv")
    msg = merge_csv(f"{D}/default_daily.csv", f"{TMP}/dd.csv")
    if list(csv.DictReader(open(f"{TMP}/ds.csv"))): merge_csv(f"{D}/default_stocks.csv", f"{TMP}/ds.csv")
    return msg

# ---------- FinMind（免 token 每小時 300 個請求，這裡每次 6 個）：只抓上個月到今天，直接併進 CSV，不留原始檔 ----------
FM = "https://api.finmindtrade.com/api/v4/data"
def finmind(dataset, data_id=None):
    url = f"{FM}?dataset={dataset}&start_date={m0}&end_date={today}" + (f"&data_id={data_id}" if data_id else "")
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=90) as r:
        j = json.load(r)
    rows = j.get("data") or []
    if j.get("status") != 200 or not rows: raise RuntimeError(f"FinMind {dataset}: {j.get('msg')}")
    time.sleep(1)
    return rows

def merge_rows(path, header, rows):
    """rows = [[date, ...], ...]；新資料涵蓋的最早日期之後，舊的列全部換成新的"""
    if not rows: raise RuntimeError("抓到 0 列")
    old = list(csv.reader(open(path)))[1:] if os.path.exists(path) else []
    cut = min(r[0] for r in rows)
    keep = [r for r in old if r[0] < cut]
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(keep + sorted(rows))
    return f"{len(keep) + len(rows) - len(old):+d} 列，最新 {max(r[0] for r in rows)}"

def fm_margin():
    by = collections.defaultdict(dict)
    for r in finmind("TaiwanStockTotalMarginPurchaseShortSale"):
        if r["name"] == "MarginPurchaseMoney": by[r["date"]]["a"] = r["TodayBalance"]
        if r["name"] == "MarginPurchase": by[r["date"]]["u"] = r["TodayBalance"]
    return merge_rows(f"{D}/margin.csv", ["date", "margin_units", "margin_amount"], [[k, v.get("u"), v.get("a")] for k, v in by.items()])
def fm_inst():                     # 外資（不含自營）買賣超，元
    return merge_rows(f"{D}/foreign_inst.csv", ["date", "foreign_net"],
                      [[r["date"], r["buy"] - r["sell"]] for r in finmind("TaiwanStockTotalInstitutionalInvestors") if r["name"] == "Foreign_Investor"])
def fm_turnover():
    return merge_rows(f"{D}/turnover.csv", ["date", "turnover"], [[r["date"], r["Trading_money"]] for r in finmind("TaiwanStockPrice", "TAIEX")])
def fm_fut():                      # FinMind 標示為「外資」（期交所為「外資及陸資」）
    return merge_rows(f"{D}/futures_foreign.csv", ["date", "foreign_net_oi"],
                      [[r["date"], r["long_open_interest_balance_volume"] - r["short_open_interest_balance_volume"]]
                       for r in finmind("TaiwanFuturesInstitutionalInvestors", "TX") if "外" in r["institutional_investors"]])
def fm_txoi():                     # 臺指期全市場未平倉：一般交易時段、只算單月契約
    tot = collections.Counter()
    for r in finmind("TaiwanFuturesDaily", "TX"):
        if r["trading_session"] == "position" and len(str(r["contract_date"]).strip()) == 6: tot[r["date"]] += r["open_interest"] or 0
    return merge_rows(f"{D}/tx_total_oi.csv", ["date", "total_oi"], [[k, v] for k, v in tot.items()])
def fm_usd():
    return merge_rows(f"{D}/usdtwd.csv", ["date", "usdtwd"], [[r["date"], round((r["spot_buy"] + r["spot_sell"]) / 2, 4)]
                      for r in finmind("TaiwanExchangeRate", "USD") if r["spot_buy"] and r["spot_sell"] and r["spot_buy"] > 0])

# ---------- CBOE VIX（整份歷史檔，約 0.5 MB） ----------
def vix():
    with urllib.request.urlopen(urllib.request.Request("https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv",
                                                      headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
        t = r.read().decode("utf-8")
    if not t.startswith("DATE,"): raise RuntimeError("格式不符")
    open(f"{D}/cboe_vix.csv", "w").write(t)
    return "最新 " + t.strip().splitlines()[-1].split(",")[0]

# ---------- PTT 股票版列表頁（最新文章；站內搜尋會延遲收錄） ----------
def ptt():
    pages = int(os.environ.get("PTT_PAGES", "40"))
    run("fetch_ptt_latest.py", str(pages), f"{TMP}/ptt.json")
    new = json.load(open(f"{TMP}/ptt.json"))
    path = f"{D}/ptt_latest.json"
    old = {p["id"]: p for p in (json.load(open(path)) if os.path.exists(path) else [])}
    n0 = len(old)
    for p in new: old[p["id"]] = p                                   # 同一篇以新抓的推文數為準
    rows = sorted(old.values(), key=lambda p: p["ts"])
    with open(path, "w") as f:                                       # 一篇一行，存進 git 時每次只多幾行
        f.write("[\n" + ",\n".join(json.dumps(p, ensure_ascii=False) for p in rows) + "\n]\n")
    gap = "" if min(p["ts"] for p in new) <= max(p["ts"] for p in rows[:n0] or [{"ts": 0}]) else "（警告：跟上次之間可能有漏抓，請加大 PTT_PAGES）"
    return f"+{len(rows) - n0} 篇，最新 {dt.datetime.fromtimestamp(rows[-1]['ts'], TZ):%Y-%m-%d %H:%M}{gap}"

t_all = time.time()
for name, fn in [("ptt", ptt), ("taiex 加權指數", taiex), ("tpex 櫃買指數", tpex), ("default 違約公告", default), ("pc 期交所 P/C", taifex_pc),
                 ("margin 融資", fm_margin), ("inst 三大法人", fm_inst), ("turnover 成交金額", fm_turnover), ("fut 外資臺指期", fm_fut),
                 ("txoi 全市場未平倉", fm_txoi), ("usd 匯率", fm_usd), ("vix 美國 VIX", vix)]:
    step(name, fn)
shutil.rmtree(TMP, ignore_errors=True)
t_fetch = time.time() - t_all
if os.environ.get("GITHUB_STEP_SUMMARY"):                            # GitHub Actions 執行頁面上的結果表
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
        f.write("| 來源 | 結果 | 說明 | 秒 |\n|---|---|---|---|\n" + "".join(f"| {a} | {b} | {c} | {t:.0f} |\n" for a, b, c, t in report))
if report and all(r[1] != "成功" for r in report): sys.exit("所有來源都失敗，不重算")
subprocess.run([sys.executable, "-I", os.path.join(HERE, "build_dashboard_data.py"), D, OUT], check=True, stdout=subprocess.DEVNULL)
print(f"\n抓資料 {t_fetch:.0f} 秒、重算 {time.time() - t_all - t_fetch:.0f} 秒；失敗 {sum(r[1] != '成功' for r in report)} 個來源")
