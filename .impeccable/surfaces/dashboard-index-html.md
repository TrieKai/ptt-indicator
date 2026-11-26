---
version: 1
slug: "dashboard-index-html"
primary_target: "dashboard/index.html"
related_targets: ["scripts/build_site.py"]
---

# Surface: public dashboard (dashboard/index.html → site/index.html)

Mode: Operate. Public visitors (often from a PTT/social link) check today's state in seconds on phone or desktop, then leave; a smaller share dig into backtests. Every existing section and interaction stays (see PRODUCT.md). Memorable moment: the score is visibly "how many lamps are lit".

## Direction contract

THESIS: 落底分數 is literally the number of lit lamps. Every signal is a lamp in a 景氣對策信號-style signal table, and each family score is a row of lamps. Refuses the category default: semicircle fear gauge plus same-size metric cards.

OWN-WORLD: The register of the 國發會 monthly signal report. White ruled report panels sit on a cool gray ground, in ink #1c1f24, set in Noto Sans TC only. Lamps:
- 藍燈 = 落底 lit
- 紅燈 = 過熱 lit
- 黃藍燈 (split amber/blue) = 偏空 lit
- gray ring = off

Lamp state:
- solid = lit today
- solid inside a ring = lit within 5 days, so it counts toward the score
- hollow = not lit

Returns keep red-up/green-down as text only, never on lamps.

STORY: Within one glance, the visitor sees today's fear reading and how many lamps are lit per family. The plain-language context and sample sizes sit beside it. Scrolling reaches the lamp matrix: which signals lit, and when. From there the visitor drills into backtests and events. Every lamp traces back to its value, threshold, last-lit date and definition.

FIRST VIEWPORT:
- Sticky top bar: title, section nav, 資料日 and PTT time.
- Today band, left: 鄉民恐慌溫度 numeral 98.0 at about 88px, a level chip, a horizontal 0–100 scale with stops at 80/85/90/95, a context line, and the 雙重確認 lamp.
- Today band, right: three lamp rows (落底 7, 過熱 8, 偏空 3), each with its score and a 「≥3 亮燈」 note.
- The lamp matrix (signals × last 20 trading days) starts at the fold.
- No primary CTA: the action is reading. The nav is the action.

FORM: IMPECCABLE'S PICK, #1 of 7 grounded candidates; seed:593087ef747e7778. Signature interaction: in the lamp matrix, hovering or focusing a lamp shows its date and value, and choosing a signal row opens that signal's event history.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Open decisions
- None beyond the build; chart internals keep their current interactions.
