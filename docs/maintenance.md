# 維護說明

給維護這個網站的人看：怎麼在本機跑、怎麼部署、負責抓 PTT 的 Mac 怎麼設定，以及重現研究用的指令。網站本身的介紹在 [README](../README.md)。

## 在自己的電腦上跑

需要 Python 3 與 Node.js 22.18 以上。

```bash
npm ci
python3 -I scripts/update_data.py data dashboard/data        # 抓上個月 1 日到今天的新資料，合併後重算（約 2–3 分鐘）
python3 -I scripts/build_site.py dashboard site              # 驗證 JSON、檢查型別並建置網站
python3 -m http.server 8000 --directory site                 # 預覽 http://localhost:8000/
```

- 只更新 PTT：`python3 -I scripts/update_data.py data dashboard/data --only ptt`
- 某個來源失敗會保留舊資料、繼續其他來源，最後列出成功／失敗；衍生的 CSV 列數若比原本少 1% 以上會拒絕覆寫。
- 下一個交易日 09:00 之後的 PTT 文章，那天還沒有收盤資料，先列在文章表並標「尚未收盤，暫不計分」。
- 開發時可單獨跑 `npm run typecheck`。claude.ai 私人版用 `npm run build:fragment` 產生 `dashboard/.build/fragment.html`。

## 自己架一份（GitHub Pages）

不需要任何帳號密碼或 API 金鑰。

1. 在 GitHub 建立一個**公開** repo（不要勾選自動建立 README）。
2. 在這個資料夾執行（網址換成自己的 repo）：
   ```bash
   git init -b main && git add -A && git commit -m "初始版本"
   git remote add origin https://github.com/你的帳號/你的repo.git && git push -u origin main
   ```
3. repo 的 Settings → Pages → Build and deployment → Source 選 **GitHub Actions**。
4. Actions 分頁 →「更新鄉民指標」→ Run workflow（範圍選 all）先手動跑一次。執行頁面下方有各來源的結果表；ptt 那列在雲端會失敗，屬預期。
5. 網址是 `https://你的帳號.github.io/你的repo/`。

注意：

- 公開 repo 裡的程式與資料（PTT 標題與連結、整理後的市場數據）任何人都看得到；FinMind 原始檔不會上傳（見 `.gitignore`）。
- GitHub 忙碌時排程會延遲，偶爾會被跳過；公開 repo 連續 60 天沒有活動，排程會被自動停用，到 Actions 分頁重新啟用即可。
- 「存回資料」步驟若出現權限錯誤：Settings → Actions → General → Workflow permissions 改成 Read and write。

## 負責抓 PTT 的 Mac

那台 Mac 只要在一般網路（家用或公司）上，每小時的 00 分與 30 分抓一次 PTT（約 20 秒、30 MB 記憶體），推上 GitHub 後由 GitHub 重算網站。需要 macOS 內建的 git 與 Python 3（沒有的話先執行 `xcode-select --install`）。推送用只限這個 repo 的 deploy key，不需要帳號密碼。

```bash
curl -fsSL https://raw.githubusercontent.com/TrieKai/ptt-indicator/main/scripts/setup_mac_collector.sh -o /tmp/setup_ptt.sh && bash /tmp/setup_ptt.sh
```

- 第一次執行會印出一行公鑰：到 repo 的 Settings → Deploy keys → Add deploy key 貼上，**勾選 Allow write access**，再執行一次同一行指令。
- 已經裝好的 Mac，重新執行同一行指令就會換成新的排程（例如改成整點與半點）。
- 完成後 repo 在 `~/ptt-indicator`，排程是 launchd（`~/Library/LaunchAgents/com.ptt-indicator.collect.plist`），記錄檔在 `~/ptt-indicator/logs/collect.log`。
- Mac 睡眠時不會執行，醒來後補跑一次。要長時間不中斷，在「系統設定 → 電池／能源」打開「顯示器關閉時防止自動進入睡眠」（插電時）。
- 停止：`launchctl bootout gui/$(id -u)/com.ptt-indicator.collect`

### 畢業文內文判斷（Groq）

判斷規則與歷史標記見 README 的「畢業文怎麼判斷」。這裡是那台 Mac 上的設定：

- cutoff（記在 `data/loss_labels_ref.json`）之後的新文章，每輪抓完列表後交給 Groq 判斷，結果存在 `data/loss_labels.json`，跟 `ptt_latest.json` 一起推上 GitHub。
- 每輪最多 10 篇（`ANALYZE_MAX` 可調），新文章優先；額度用完或判斷失敗都不影響抓文章，下一輪再補。
- `data/loss_overlap.json` 是 60 篇歷史對照樣本，用來量 Groq 跟參考標記的一致率。換模型試跑：`bash scripts/try_model.sh qwen/qwen3.8-27b`（結果存在 `data/model_trials/`，不影響網站分數；額度用完會先停，再執行一次會接著跑）。

設定 Groq 金鑰（用個人帳號在 console.groq.com 建立；只存在本機，不進 repo）：

```bash
mkdir -p ~/.config/ptt-indicator && chmod 700 ~/.config/ptt-indicator && read -rs "K?Groq API key: " && echo && printf 'GROQ_API_KEY=%s\n' "$K" > ~/.config/ptt-indicator/groq.env && chmod 600 ~/.config/ptt-indicator/groq.env && unset K && echo 已存好
```

另一台電腦若也裝過 `setup_mac_analyzer.sh` 的排程，請停掉，避免兩台同時判斷：`launchctl bootout gui/$(id -u)/com.ptt-indicator.analyze`

## 重現研究

完整歷史資料（日常更新不需要）：

```bash
python3 -I scripts/fetch_taiex.py 2015-01 2026-11 data/taiex.csv                 # 加權指數（約 6 分鐘）
python3 -I scripts/fetch_tpex.py 2017-06 2019-05 data/tpex_early.csv            # 早期櫃買指數
python3 -I scripts/fetch_tpex.py 2019-06 2026-11 data/tpex.csv                  # 櫃買指數（約 5 分鐘）
python3 -I scripts/fetch_taifex.py pc 2017-06 2026-11 data/taifex_pc.csv        # 選擇權 P/C 比（約 7 分鐘）
python3 -I scripts/fetch_default.py 2019-02 2026-11 data/default_daily.csv data/default_stocks.csv   # 違約交割
python3 -I scripts/fetch_ptt_search.py 創作 400 data/creative_search.json        # PTT 站內搜尋（約 2 分鐘）
python3 -I scripts/fetch_ptt_search.py 畢業 200 data/graduation_search.json
for q in 斷頭 違約交割 歸零 賠光 追繳 爆倉; do python3 -I scripts/fetch_ptt_search.py "$q" 200 "data/kw_$q.json"; done
for q in 財富自由 歐印 噴 翻倍 創新高 賺爛 上車; do python3 -I scripts/fetch_ptt_search.py "$q" 200 "data/greed_$q.json"; done
python3 -I scripts/fetch_ptt_latest.py 40 data/ptt_latest.json                   # PTT 最新文章（站內搜尋會延遲收錄）
curl -sL https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv -o data/cboe_vix.csv
python3 -I scripts/build_dashboard_data.py data dashboard/data                   # 產生網站資料與逐日文章檔 post_days.json
```

- 融資：FinMind `TaiwanStockTotalMarginPurchaseShortSale`；`scripts/fetch_margin.py` 可直接從證交所抓（較慢，每天一次請求）。融資當晚才公布，只用隔天進場。
- 三大法人：FinMind `TaiwanStockTotalInstitutionalInvestors`。收盤後才公布，只用隔天開盤進場；自營商受權證、ETF 避險影響大，未納入。
- 違約交割：證交所「違約公告專區」<https://www.twse.com.tw/zh/announcement/bfigtu.html>，申報日期 = 成交日後第 2 個營業日，金額單位為元；用成交日的成交金額正規化。
- 外資臺股期貨：期交所下載只提供近 3 年（`fetch_taifex.py fut 2017 2026 data/taifex_fut.csv` 用來核對），完整歷史用 FinMind `TaiwanFuturesInstitutionalInvestors`（data_id=TX）存成 `data/futures_foreign.csv`。
- 臺指 VIX 歷史要到期交所 E-Data Shop 付費申購，網站只提供近 3 個月，所以沒有放進回測。

研究腳本：

- 恐慌溫度單獨評估：先跑 `scripts/ptt_fear_greed.py data data/ptt_fear_greed.csv`，再跑 `scripts/eval_thermometer.py data`。
- 雙重確認：拆解測試 `scripts/loss_vs_creative.py`；前後兩段與相鄰門檻 `scripts/dual_robustness.py`；天數與篇數敏感度 `scripts/window_sensitivity.py`、`scripts/threshold_sensitivity.py`；大盤跌幅條件 `scripts/dual_drawdown.py`。
- 畢業／虧損文的標題規則在 `scripts/loss_rules.py`，每篇保留或排除的原因列在 `data/loss_audit.csv`。
- 外資期貨與匯率：`python3 -I scripts/analyze_futures_fx.py data`（需要 `data/tx_total_oi.csv`、`data/usdtwd.csv`）。
- 事件說明的順序：人工註記（`build_dashboard_data.py` 的 NOTES）→ 當時 PTT 標題最常出現的主題（THEMES）。

### 早期研究：創作文爆量 vs 加權指數（`scripts/backtest.py`）

這是專案最早的版本，跟網站的算法不同：

```bash
python3 -I scripts/backtest.py data/taiex.csv data/creative_search.json data/main 5 4     # 一般門檻
python3 -I scripts/backtest.py data/taiex.csv data/creative_search.json data/strong 8 5   # 嚴格門檻
python3 -I scripts/backtest_signals.py data                                              # 畢業文、違約交割新聞、融資增減
```

- 訊號歸屬：前一交易日 13:30 後到當天 13:30 的 `[創作]` 原文算當天（網站改用 09:00 分界）。
- 爆量：當天篇數 ≥ N 且 ≥ M 倍前 60 交易日平均；10 個交易日內不重複。
- 對照：同年度隨機交易日（10,000 次抽樣）、單日跌 ≥3% 的交易日。
- 輸出：`data/*_events.csv`（每個事件的篇數與後續報酬）、`data/*_daily.csv`（每日篇數與收盤指數）。
- 事件數少（一般門檻 23 個、嚴格門檻 8 個），回測從 2020/4 起。
