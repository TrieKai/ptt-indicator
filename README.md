# 台股落底訊號回測

把 PTT 股票版的畢業文與創作文換算成「鄉民恐慌溫度」，搭配融資、外資、選擇權、期貨與美國 VIX 等市場數據做成燈號，回測 2019 年以來每次亮燈之後，加權指數與櫃買指數的表現。

網站：<https://triekai.github.io/ptt-indicator/>

> 歷史統計不代表未來，也不是投資建議。事件數少，請保守看待。這是非商業的公開研究。

## 網站上看得到什麼

- **鄉民恐慌溫度（0–100）**：畢業／虧損文與創作文的近 5 個交易日篇數，各自跟過去 250 個交易日比，算出「比這次少的天數比例」，兩者平均後換成 0–100。80 以上留意、85 以上偏恐慌、90 以上恐慌、95 以上極度恐慌。
- **雙重確認**：三項同時達標才亮燈。PTT 這邊要畢業文 5 日 ≥3 篇、創作文熱度 ≥90；大盤這邊要加權指數比 60 日高點至少跌 5%。兩邊互相確認，所以叫雙重確認。
- **落底面（7 個）、過熱面（8 個）燈號**：融資、外資、違約交割、P/C 比、美國 VIX 等。分數的回測不顯著，所以只當參考燈號。
- **偏空警示（3 項）**：外資臺股期貨的淨空單口數、佔全市場未平倉比例、5 日淨部位變化，任一項低於過去 250 個交易日的第 5 百分位就亮燈。不算進落底分數。
- **回測與事件明細**：每個訊號亮燈後 5／20／60 日的報酬、跟同年度隨機日與價格相近日的比較，以及每一次亮燈的日期與當時的 PTT 文章。
- **分享**：今天的圖卡可以下載，或直接分享到 LINE、Facebook、Threads、X。

## 資料來源與更新時間

| 資料 | 來源 |
|---|---|
| 加權指數 | 證交所 MI_5MINS_HIST |
| 櫃買指數 | 櫃買中心（已與 FinMind 全期比對一致） |
| 成交金額 | FinMind（與證交所 FMTQIK 抽樣一致） |
| 融資 | FinMind（整理自證交所 MI_MARGN，抽 15 個交易日比對一致） |
| 違約交割 | 證交所違約公告專區（2019/2 起） |
| 三大法人買賣超 | FinMind（整理自證交所 BFI82U，抽 4 天 × 5 類法人比對一致） |
| 臺指選擇權 P/C 比 | 期交所 Put/Call Ratio |
| 外資臺股期貨未平倉 | FinMind（與期交所重疊的 701 天完全一致） |
| 美國 VIX | CBOE VIX History |
| PTT 股票版文章 | PTT 列表頁與站內搜尋（創作文、過熱文只比對標題；畢業文另外讀內文判斷） |

更新時間（台灣時間）：

- **市場資料**：GitHub Actions 在平日 15:40 完整更新，16:40、18:10 備援；每天 22:10 再更新一次（融資、違約公告），週二到週六 08:50 開盤前補最後一次。
- **PTT 文章**：PTT 會擋 GitHub 的主機，所以由一台 Mac 在每小時的 00 分與 30 分抓取並推上 GitHub，網站收到後幾分鐘內重算。頁首會顯示「PTT 文章至 …」；最新文章距資料產生超過 3 小時會另外標示，代表溫度可能偏低。
- 盤後資料公布時間：指數、P/C 比、三大法人約 15:00 後；融資約 21:30 後；美國 VIX 是台灣早上。

## 限制

- 只看得到沒被刪的文章。被刪文章的墓碑列幾天內就會從列表頁清掉，歷史上無法回補。
- 站內搜尋只比對標題；`[創作]` 分類 2020 年才開始活躍。
- 事件數少，而且測過多組門檻與期間，p 值僅供參考。
- 訊號只用當時已知的資料：PTT 文章以 09:00 分界（當天 09:00 到下一個交易日 09:00 前算當天），PTT 與盤後資料的訊號都用隔天開盤進場。
- FinMind 免費方案標明不得用於「公司內部系統等商業用途」（2026/11 查詢）。若要在公司正式使用，FinMind 的 6 項資料應改用證交所／期交所官方來源（先前已逐項比對一致），或購買商業方案。

## 運作方式

```
PTT（Mac，每 :00／:30）──┐
                          ├─► data/（原始 CSV、JSON，存在 repo）
市場資料（GitHub Actions）─┘          │
                                      ▼
            scripts/build_dashboard_data.py：算訊號、回測 → dashboard/data/*.json
                                      │
                                      ▼
            scripts/build_site.py：驗證 JSON、編譯 TypeScript → site/ → GitHub Pages
```

- 所有訊號與回測的定義都在 `scripts/build_dashboard_data.py` 檔頭。
- 頁面在 `dashboard/index.html`，前端程式在 `dashboard/src/`（TypeScript，用 valibot 驗證資料格式）。
- 分享圖卡與連結預覽圖用同一份畫法（`dashboard/src/card.ts`）；預覽圖由 GitHub Actions 用 Chrome 截圖產生。

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

畢業文只算〔心得〕分類，而且內文要是作者本人做多認賠或重大虧損，並附對帳單截圖或具體金額。

- **歷史文章**：由 Claude 逐篇判斷並做一致性複核，存在 `data/loss_labels_ref.json`（裡面記著 cutoff）。2026/11/27 人工覆核 38 篇原文（構成訊號的 30 篇＋模型意見不同的 8 篇），改判 3 篇；各列的 `human` 欄位是人工判斷，`ai_counts` 是改判前的結果。
- **cutoff 之後的新文章**：抓 PTT 的 Mac 每輪抓完列表後交給 Groq 判斷，結果存在 `data/loss_labels.json`，跟 `ptt_latest.json` 一起推上 GitHub。每輪最多 10 篇（`ANALYZE_MAX` 可調），新文章優先；額度用完或判斷失敗都不影響抓文章，下一輪再補。
- **還沒判斷到的新文章**暫時照標題計算，網站上會註明。
- `data/loss_overlap.json` 是 60 篇歷史對照樣本，用來量 Groq 跟參考標記的一致率。換模型試跑：`bash scripts/try_model.sh qwen/qwen3.8-27b`（結果存在 `data/model_trials/`，不影響網站分數）。

在抓 PTT 的 Mac 上設定 Groq 金鑰（用個人帳號在 console.groq.com 建立；只存在本機，不進 repo）：

```bash
mkdir -p ~/.config/ptt-indicator && chmod 700 ~/.config/ptt-indicator && read -rs "K?Groq API key: " && echo && printf 'GROQ_API_KEY=%s\n' "$K" > ~/.config/ptt-indicator/groq.env && chmod 600 ~/.config/ptt-indicator/groq.env && unset K && echo 已存好
```

另一台電腦若也裝過 `setup_mac_analyzer.sh` 的排程，請停掉，避免兩台同時判斷：`launchctl bootout gui/$(id -u)/com.ptt-indicator.analyze`

## 重現研究

<details>
<summary>從頭抓資料與研究用腳本</summary>

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
python3 -I scripts/build_dashboard_data.py data dashboard/data                   # 產生 daily/events/summary/status/posts.json
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

</details>
