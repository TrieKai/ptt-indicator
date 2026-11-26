# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Anyone on the public web, often arriving from a link posted on PTT or social media, reading Traditional Chinese. Many are first-time visitors who know the Taiwan stock market but have never seen this research. Their job is to check today's state in seconds: how fearful PTT 股票版 is right now (the 0–100 恐慌溫度), and which bottom, overheat, and bearish-warning signals are lit. They then leave. A smaller share go on to the backtest detail. Phone and desktop are used about equally: phones for the quick check, desktops for dragging charts and reading wide tables.

## Product Purpose

A public, non-commercial dashboard titled 「台股落底訊號回測」 (repo: ptt-indicator). It turns PTT 股票版 post titles into a fear thermometer, combines it with market signals into 落底分數 (/7), 過熱分數 (/8), and 偏空警示 (/3), and shows how each signal performed historically on 加權指數 and 櫃買指數 since 2019. Success: a first-time visitor understands today's reading and its historical context within seconds, and leaves with honest expectations: small samples, no prediction, not investment advice.

## Positioning

The crowd itself is the instrument. The thermometer counts capitulation in PTT 股票版 titles: 創作文 (song-parody posts written in panic) and 畢業／虧損文 (posts announcing realized losses). Each count is compared with the past 250 trading days. The backtest is reported honestly: excess return against same-year days with similar prior 5-day moves, 「贏過配對」 rates, p-values, and how close each signal came to the true low.

## Operating Context

- PTT posts are fetched every 15 minutes by a Mac on an ordinary home network. PTT blocks cloud hosts.
- Market data updates on GitHub Actions at 15:40 on weekdays and 22:10 daily, Taiwan time.
- The site is static, on GitHub Pages: https://triekai.github.io/ptt-indicator/
- A PTT day runs from 09:00 to 09:00 the next day.
- Posts made after the close count toward the next trading day and are shown as pending until then.

## Capabilities and Constraints

- Static page: `dashboard/index.html` is wrapped by `scripts/build_site.py`, which supplies tokens, a small `dash` data shim, and d3 7.9.0 from cdnjs.
- Data comes from `data/{daily,events,summary,status,posts}.json`. There is no server.
- Interactive charts:
  - main price chart with signal markers and event labels
  - thermometer chart
  - drag-to-zoom and date-range inputs
  - index switch (加權／櫃買)
  - signal-row selection that drives the event table
- Sections that must keep their function:
  - thermometer and 雙重確認
  - current signal cards (落底, 過熱, 偏空)
  - index trend with signal timeline
  - return tables and charts for each family
  - distance-to-low/high plots
  - event detail
  - PTT post list
  - definitions and sources
- Terminology is fixed: 鄉民恐慌溫度, 落底分數, 過熱分數, 偏空警示, 雙重確認, 創作文, 畢業／虧損文, 超額, 贏過配對.
- The project is non-commercial. FinMind's free tier forbids commercial use.

## Brand Commitments

- Traditional Chinese (Taiwan) throughout.
- Taiwan market colour convention: red means up, green means down. This is stated on the page.
- Voice is plain and cautious. Terms are explained in everyday words, and the page repeatedly says 「次數很少，請保守看待」.
- Every page carries the disclaimer that historical statistics do not predict the future and are not investment advice. Calculations are automated and may contain errors.

## Evidence on Hand

- Real computed data in `data/*.json`, rebuilt automatically.
- Human-annotated event notes: for example 「Fed 激進升息＋外資撤離」 for 2022/10.
- Live PTT post titles with push counts.
- No testimonials, user counts, or performance claims exist, and none may be invented.

## Product Principles

1. Today first: the current reading and what is lit come before any history.
2. Honest about uncertainty: sample sizes and caveats stay next to every headline number; nothing reads as a prediction.
3. Plain words for first-time visitors: every number is explained once, where it appears.
4. Traceable: each figure links back to its definition, threshold, and data date.
5. Equal on phone and desktop: the quick check works one-handed; the deep tables work on a wide screen.
