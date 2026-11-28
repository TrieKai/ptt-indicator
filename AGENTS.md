# AGENTS.md

給寫程式的 AI agent 看的工作說明。給人看的介紹在 `README.md`。

## 專案

公開、非商業的儀表板「台股落底訊號回測」：PTT 股票版的畢業文與創作文 → 鄉民恐慌溫度（0–100），加上市場數據的燈號與 2019 年以來的回測。網址 <https://triekai.github.io/ptt-indicator/>，從 `main` 部署到 GitHub Pages。

動手前先讀：

- `PRODUCT.md`：使用者、產品原則、固定用語。
- `DESIGN.md`：視覺規則（燈號配色、紅漲綠跌、不加陰影、表格數字等寬）。
- `.impeccable/surfaces/dashboard-index-html.md`：首頁的版面約定。

## 檔案地圖

| 路徑 | 內容 |
|---|---|
| `scripts/build_dashboard_data.py` | 所有訊號、門檻、回測與輸出 JSON 的定義（檔頭有完整說明） |
| `scripts/update_data.py` | 增量抓資料並重算；`--only ptt` 只抓 PTT |
| `scripts/build_site.py` | 驗證 JSON → `npm run build` → 輸出 `site/`，並產生 meta 與 og 文字 |
| `scripts/collect_ptt.sh`、`scripts/setup_mac_collector.sh` | 抓 PTT 的 Mac 排程（launchd，每小時 00 分與 30 分） |
| `.github/workflows/update.yml` | 市場資料排程、推到 main 後重算並部署 |
| `dashboard/index.html` | 頁面結構與全部 CSS |
| `dashboard/src/view.ts` | 所有區塊的繪製（`dash.draw('名稱', …)` 對應 HTML 的 `data-draw`） |
| `dashboard/src/runtime.ts` | 依區段延遲載入資料；元素的 `data-source` 決定它所在區段要抓哪些 JSON |
| `dashboard/src/data.ts` | valibot 資料格式；建置與瀏覽器都用它驗證 |
| `dashboard/src/signals.ts` | 共用標籤（`dualTitle`、燈號簡稱、溫度等級） |
| `dashboard/src/card.ts` | 分享圖卡；連結預覽圖（og:image）也是它畫的 |

## 指令

```bash
npm ci                                                        # Node.js 22.18+
npm run typecheck
python3 -I scripts/build_dashboard_data.py data dashboard/data   # 重算全部 JSON（約 40 秒）
python3 -I scripts/build_site.py dashboard site                  # 驗證、型別檢查、建置
python3 -m http.server 8765 --bind 127.0.0.1 --directory site    # 預覽
```

- Python 一律加 `-I`。
- `dashboard/data/`、`dashboard/.build/`、`site/`、`logs/` 是產出，不進 repo。
- `data/` 是原始資料，由排程更新並 commit；不要手動改。

## 規則

- **介面文字用台灣繁體中文**，用語照 `PRODUCT.md` 固定：鄉民恐慌溫度、落底分數、過熱分數、偏空警示、雙重確認、創作文、畢業／虧損文、超額、贏過配對。不要用「恐慌文」，要寫出「畢業文、創作文」。
- **改一個用語要全部一起改**：`dashboard/index.html`、`dashboard/src/view.ts`、`dashboard/src/signals.ts`／`card.ts`（圖卡），以及 `scripts/build_site.py`（meta 與 og 文字）。
- **不加沒有資料根據的說法**：數字都來自計算結果，不要自己寫績效或預測。免責聲明保留。
- **訊號只用當時已知的資料**：PTT 以 09:00 分界、隔天開盤進場；門檻用過去 250 個交易日的百分位。改訊號定義就要重跑回測並更新說明。
- **日期**：`YYYY-MM-DD` 一律當成 UTC 零點解析（`LB.parse`），取星期、日期用 `getUTC*`，不然在其他時區會差一天。
- **顏色**：燈號顏色只代表訊號類別；報酬數字紅漲綠跌。偏空燈一定是黃藍對切，不是純黃色。

## 容易踩到的地方

- PTT 會擋 GitHub 的主機（HTTP 403），雲端抓不到 PTT；PTT 只能由那台 Mac 抓。
- `main` 會一直收到機器人的 commit（「PTT 文章更新」每 30 分鐘一次，還有 Actions 的資料更新）。推之前先 `git pull --rebase`。
- 推到 `main` 而且改到 `dashboard/**` 或 `update.yml` 裡列出的腳本，就會觸發重算並部署正式網站。
- `posts.json` 的 `event` 欄位有幾種格式：回測事件日期 `YYYY-MM-DD`、`latest`、`window-latest`、`window-YYYY-MM-DD`（恐慌溫度的 5 日文章），以及 `day-YYYY-MM-DD`（那天計入的畢業文，圖表點某一天時用）。
- 兩張圖各自用 `nextElementSibling` 找「查看圖上事件」的 `<details>`：圖表後面一定要緊接著它。
- 改了 `card.ts` 的文字，記得字型預載的字集（`glyphs`）也要涵蓋新的字。

## 檢查

- `python3 -I scripts/build_site.py dashboard site` 要通過。
- 在瀏覽器看 375px 手機寬度與桌機寬度、淺色與深色：沒有橫向捲動、圖表提示框與點選正常、文字沒有孤字斷行。
- 改到資料算法時，比對 `dashboard/data/summary.json` 改前改後的差異，並在回報中說明。

## Commit

- 訊息用中文，一行標題描述改了什麼，必要時加幾行條列說明，比照 `git log` 的寫法。
- 只 commit 跟這次修改有關的檔案；`.claude/` 等本機設定不要 commit。
