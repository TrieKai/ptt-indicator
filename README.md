# PTT 股票版 [創作] 文爆量 vs 加權指數 回測

## 重跑步驟

```bash
python3 -I scripts/fetch_taiex.py 2015-01 2026-11 data/taiex.csv          # 證交所加權指數日資料（約 6 分鐘）
python3 -I scripts/fetch_ptt_search.py 創作 400 data/creative_search.json  # PTT 站內搜尋標題（約 2 分鐘）
python3 -I scripts/backtest.py data/taiex.csv data/creative_search.json data/main 5 4     # 一般門檻
python3 -I scripts/backtest.py data/taiex.csv data/creative_search.json data/strong 8 5   # 嚴格門檻
```

### 畢業文、違約交割新聞、融資增減（scripts/backtest_signals.py）

```bash
for q in 斷頭 違約交割 歸零 賠光 追繳 爆倉; do python3 -I scripts/fetch_ptt_search.py "$q" 200 "data/kw_$q.json"; done
python3 -I scripts/fetch_ptt_search.py 畢業 200 data/graduation_search.json
curl -s "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockTotalMarginPurchaseShortSale&start_date=2020-01-01&end_date=2026-11-25" -o data/finmind_margin.json
python3 -I scripts/backtest_signals.py data
```

- 融資資料來自 FinMind（整理自證交所），抽 15 個交易日與證交所 MI_MARGN 比對完全一致；`scripts/fetch_margin.py` 可直接從證交所抓（較慢，每天一次請求）
- 融資資料當晚才公布，所以融資訊號只用「隔天開盤／隔天收盤」進場
- 違約交割：證交所「違約公告專區」https://www.twse.com.tw/zh/announcement/bfigtu.html（108/2/1 起），
  資料介面 `rwd/zh/announcement/BFIGTU?startDate=YYYYMMDD&endDate=YYYYMMDD&response=json`；
  `python3 -I scripts/fetch_default.py 2019-02 2026-11 data/default_daily.csv data/default_stocks.csv`
  （申報日期 = 成交日後第 2 個營業日，金額單位：元）。PTT [新聞] 標題的違約交割次數另外保留作對照
- 三大法人買賣超：FinMind `TaiwanStockTotalInstitutionalInvestors`（整理自證交所 BFI82U，
  `twse.com.tw/rwd/zh/fund/BFI82U?type=day&dayDate=YYYYMMDD&response=json`），抽 4 天 × 5 類法人比對完全一致；
  `curl -s "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockTotalInstitutionalInvestors&start_date=2020-01-01&end_date=2026-11-25" -o data/finmind_inst.json`
  收盤後才公布，所以只用隔天開盤進場；自營商（避險）受權證、ETF 避險影響大，未納入

### 日常更新（增量，約 2–3 分鐘）

```bash
python3 -I scripts/update_data.py data dashboard/data              # 全部來源：只抓上個月 1 日到今天，合併進既有檔案，再重算
python3 -I scripts/update_data.py data dashboard/data --only ptt   # 盤中只更新 PTT
```

- 某個來源失敗會保留舊資料、繼續其他來源，最後列出成功／失敗；衍生的 CSV 列數若比原本少 1% 以上會拒絕覆寫
- 注意授權：FinMind 免費方案（含 Backer／Sponsor）標明不得用於「公司內部系統等商業用途」（finmind.github.io/en/Pricing/，2026/11 查詢）。
  公司正式使用前，FinMind 的 6 項資料應改用證交所／期交所官方來源（先前已逐項比對一致），或購買商業方案
- 執行時間（2026/11/26 實測）：全部來源抓取約 70 秒、重算約 30 秒 CPU；只更新 PTT 時抓取約 40 秒、重算一樣約 30 秒
- 盤後資料公布時間：加權／櫃買指數、P/C 比、三大法人約 15:00 後；融資約 21:30 後；美國 VIX 是台灣早上
- 下一個交易日 09:00 之後的 PTT 文章，那天還沒有收盤資料，先列在文章表（標「尚未收盤，暫不計分」），不算進最後一天

### 部署到 GitHub（公開 repo，GitHub Actions 排程 ＋ GitHub Pages）

排程設定在 `.github/workflows/update.yml`：台灣 15:40（平日）與 22:10 完整更新；
**PTT 會擋 GitHub 的主機（2026/11/26 實測 HTTP 403）**，雲端抓不到 PTT，PTT 文章要從可連線的電腦更新後推上來（`--only ptt` 後 commit、push）。

每次重算後把 `data/` 的變動存回 repo，並把 `site/` 發布到 GitHub Pages。不需要任何帳號密碼或 API 金鑰。

1. 在 GitHub 建立一個**公開** repo（不要勾選自動建立 README）
2. 在這個資料夾執行（把網址換成自己的 repo）：
   ```bash
   git init -b main && git add -A && git commit -m "初始版本"
   git remote add origin https://github.com/你的帳號/你的repo.git && git push -u origin main
   ```
3. repo 的 Settings → Pages → Build and deployment → Source 選 **GitHub Actions**
4. Actions 分頁 → 「更新鄉民指標」→ Run workflow（範圍選 all）先手動跑一次。
   執行頁面下方有各來源的結果表（ptt 那列在雲端會失敗，屬預期；其他來源都應該成功）
5. 網址是 `https://你的帳號.github.io/你的repo/`

注意：
- 公開 repo 裡的程式、資料（PTT 標題與連結、整理後的市場數據）任何人都看得到；FinMind 原始檔不會上傳（見 `.gitignore`）
- 排程在 GitHub 忙碌時會延遲，偶爾會被跳過
- 溫度計旁會顯示「PTT 文章至 …」；超過 3 小時沒有新文章會變色警示，代表溫度可能偏低
- 公開 repo 連續 60 天沒有活動，排程會被自動停用；到 Actions 分頁重新啟用即可
- 若「存回資料」步驟出現權限錯誤：Settings → Actions → General → Workflow permissions 改成 Read and write
- 本機測試（2026/11/26）：在乾淨的 clone 裡跑 PTT 更新＋重算約 43 秒，repo 壓縮後約 0.7 MB，每次資料 commit 約增加數 KB

### 用另一台 Mac 負責抓 PTT（PTT 會擋雲端主機）

那台 Mac 只要在一般網路（家用或公司），每 30 分鐘抓一次 PTT（約 20 秒、30 MB 記憶體），推上 GitHub 後由 GitHub 重算並更新網站。
需要 macOS 內建的 git 與 Python 3（沒有的話先執行 `xcode-select --install`），不需要帳號密碼：推送用只限這個 repo 的 deploy key。

```bash
curl -fsSL https://raw.githubusercontent.com/TrieKai/ptt-indicator/main/scripts/setup_mac_collector.sh -o /tmp/setup_ptt.sh && bash /tmp/setup_ptt.sh
```

- 第一次執行會印出一行公鑰：到 repo 的 Settings → Deploy keys → Add deploy key 貼上，**勾選 Allow write access**，再執行一次同一行指令
- 已安裝的 Mac 可重新執行新版安裝腳本，讓 launchd 套用 30 分鐘的間隔
- 完成後 repo 在 `~/ptt-indicator`，排程是 launchd（`~/Library/LaunchAgents/com.ptt-indicator.collect.plist`），記錄檔 `~/ptt-indicator/logs/collect.log`
- Mac 睡眠時不會執行，醒來後補跑；要長時間不中斷，在「系統設定 → 電池／能源」打開「顯示器關閉時防止自動進入睡眠」（插電時）
- 停止：`launchctl bootout gui/$(id -u)/com.ptt-indicator.collect`

### 落底訊號儀表板（dashboard/）

```bash
python3 -I scripts/fetch_tpex.py 2019-06 2026-11 data/tpex.csv                 # 櫃買中心官方櫃買指數（約 5 分鐘）
python3 -I scripts/build_dashboard_data.py data dashboard/data               # 產生 daily/events/summary/status/posts.json
npm ci                                                                       # 需 Node.js 22.18+
npm run typecheck                                                            # 開發時可單獨檢查 TypeScript
python3 -I scripts/build_site.py dashboard site                              # 驗證 JSON、檢查型別並編譯靜態網站
python3 -m http.server 8000 --directory site                                   # 本機預覽 http://localhost:8000/
```

- 頁面版型在 `dashboard/index.html`，前端程式在 `dashboard/src/`。建置和瀏覽器使用 `dashboard/src/data.ts` 驗證 JSON。
- claude.ai 私人版用 `npm run build:fragment` 產生 `dashboard/.build/fragment.html`，在原本提供 `dash` 與 `d3` 的環境使用。資料更新後，可在「來源」面板替換 5 個 JSON。
- 落底分數 = 過去 5 個交易日內，外資大賣超、融資大減、違約爆量、畢業文、創作文 5 個訊號有幾個亮燈
- 過熱分數 = 外資大買超、融資金額大增、成交金額爆量、PTT 過熱文、乖離 120 日線 5 個訊號同理
- 目前版本：落底分數 7 個訊號（創作文、畢業文、融資大減、違約、外資大賣、P/C 成交量比偏高、美國 VIX 恐慌）；過熱分數 8 個；
  另有「偏空警示」3 項（外資臺股期貨淨空單口數、佔全市場未平倉比例、5 日淨部位變化），不算進落底分數
- 儀表板的 PTT 文章一律用 09:00 分界：當天 09:00 到下一個交易日 09:00 前發的算當天（畢業文 29% 盤中、54% 收盤後；創作文 80% 收盤後），
  PTT 訊號用隔天開盤進場。上面「方法」一節的 13:30 分界只適用早期的 `backtest.py`
- 鄉民恐慌溫度（0–100）：創作文與畢業／虧損文 5 日篇數，各自跟過去 250 個交易日比「比今天少的天數比例」後平均 ×100，
  在 `build_dashboard_data.py` 計算並放在儀表板最上方；單獨評估用 `python3 -I scripts/eval_thermometer.py data`
  （先跑 `scripts/ptt_fear_greed.py data data/ptt_fear_greed.csv`，該檔另含含過熱文的 0–100 原型指數）
- 雙重確認（畢業文 5 日 ≥3 篇且創作文 5 日熱度 ≥90）：拆解測試 `scripts/loss_vs_creative.py`、
  前後兩段與相鄰門檻檢查 `scripts/dual_robustness.py`；天數與篇數敏感度 `scripts/window_sensitivity.py`、`scripts/threshold_sensitivity.py`
- 事件說明：溫度計與主圖的落底標記（combo3／combo4）都附事件文字，順序是人工註記（`build_dashboard_data.py` 的 NOTES）→ 當時 PTT 標題最常出現的主題（THEMES）→ 亮燈訊號簡稱（只在放大到約 2 年內時用灰字顯示）
- 畢業／虧損文分類規則在 `scripts/loss_rules.py`（只看標題）；每篇被保留或排除的原因列在 `data/loss_audit.csv`
- 外資期貨與匯率關係的分析：`python3 -I scripts/analyze_futures_fx.py data`（需要 `data/tx_total_oi.csv`、`data/usdtwd.csv`，由 FinMind TaiwanFuturesDaily、TaiwanExchangeRate 整理）
- 外資、違約都除以成交金額（`data/turnover.csv`，FinMind，與證交所 FMTQIK 抽樣一致）；資料從 2017/6 起，回測從 2019/1 起
- PTT 過熱文關鍵字：`for q in 財富自由 歐印 噴 翻倍 創新高 賺爛 上車; do python3 -I scripts/fetch_ptt_search.py "$q" 200 "data/greed_$q.json"; done`
- 早期櫃買指數：`python3 -I scripts/fetch_tpex.py 2017-06 2019-05 data/tpex_early.csv`
- 選擇權 P/C 比（期交所，約 7 分鐘）：`python3 -I scripts/fetch_taifex.py pc 2017-06 2026-11 data/taifex_pc.csv`
- 外資臺股期貨未平倉：期交所下載只提供近 3 年（`fetch_taifex.py fut 2017 2026 data/taifex_fut.csv` 用來核對），完整歷史用 FinMind `TaiwanFuturesInstitutionalInvestors`（data_id=TX）存成 `data/futures_foreign.csv`，兩者重疊 701 天完全一致
- 美國 VIX：`curl -sL https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv -o data/cboe_vix.csv`
- PTT 最新文章（站內搜尋會延遲收錄）：`python3 -I scripts/fetch_ptt_latest.py 40 data/ptt_latest.json`
- 臺指 VIX 歷史要到期交所 E-Data Shop 付費申購，網站只提供近 3 個月，所以沒有放進回測
- 櫃買指數已與 FinMind 全期比對一致；加權指數 FinMind 與證交所全期一致

## 方法
- 訊號歸屬：前一交易日 13:30 後 ~ 當天 13:30 的 `[創作]` 原文算當天（收盤時已知，不偷看未來）
- 爆量：當天篇數 >= N 且 >= M 倍前 60 交易日平均；每波只取第一個警示日（10 交易日內不重複）
- 對照：同年度隨機交易日（10,000 次抽樣）、單日跌 >= 3% 的交易日

## 輸出
- `data/*_events.csv`：每個事件日的篇數、當天／前 5 日報酬、後 1/5/20/60 日報酬
- `data/*_daily.csv`：每日創作文篇數與收盤指數

## 限制
- 只看得到沒被刪的文章；被刪文章的墓碑列幾天內就會從列表頁清掉，歷史上無法回補
- 站內搜尋只比對標題；`[創作]` 分類 2020 年才開始活躍，回測從 2020/4 起
- 事件數少（一般門檻 23 個、嚴格門檻 8 個），且測了多個門檻與期間，p 值僅供參考
- 結果為歷史統計，不構成投資建議；使用前請自行查證

## 畢業文內文判斷（Groq，跟抓 PTT 同一台電腦）

畢業文只算〔心得〕分類，而且內文要有依據（對帳單截圖或具體虧損金額）。
- 歷史文章：由 Claude 逐篇判斷並做一致性複核，存在 `data/loss_labels_ref.json`（裡面記著 cutoff）。
  2026/11/27 人工覆核 38 篇原文（構成訊號的 30 篇＋模型意見不同的 8 篇），改判 3 篇；各列的 `human` 欄位是人工判斷，`ai_counts` 是改判前的結果。
- cutoff 之後的新文章：負責抓 PTT 的電腦在每輪抓完列表後，交給 Groq 判斷，結果存在 `data/loss_labels.json`，跟 `ptt_latest.json` 一起推上 GitHub。
- `data/loss_overlap.json` 是 60 篇對照樣本（歷史文章），也交給 Groq 判斷，用來量 Groq 跟參考標記的一致率。
- 網站算分（2026/11/27 起）：cutoff 以前用參考標記，之後用 Groq 的判斷；還沒判斷到的新文章暫時照標題計算，網站上會註明。

換模型試跑（結果存在 `data/model_trials/`，不影響網站分數）：在有金鑰的電腦執行 `bash scripts/try_model.sh qwen/qwen3.8-27b`，
會用同一套提示詞判斷這 60 篇樣本並推上 GitHub；額度用完會先停，再執行一次會接著跑。

在負責抓 PTT 的 Mac 上設定 Groq 金鑰（用個人帳號在 console.groq.com 建立；只存在本機，不進 repo），之後的排程就會自動判斷：

```bash
mkdir -p ~/.config/ptt-indicator && chmod 700 ~/.config/ptt-indicator && read -rs "K?Groq API key: " && echo && printf 'GROQ_API_KEY=%s\n' "$K" > ~/.config/ptt-indicator/groq.env && chmod 600 ~/.config/ptt-indicator/groq.env && unset K && echo 已存好
```

每輪最多判斷 10 篇（`ANALYZE_MAX` 可調），新文章優先；Groq 免費額度用完或判斷失敗都不影響抓文章，下一輪再補。
另一台電腦若也裝過 `setup_mac_analyzer.sh` 的排程，請停掉，避免兩台同時判斷：`launchctl bootout gui/$(id -u)/com.ptt-indicator.analyze`
