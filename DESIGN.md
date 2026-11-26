---
name: 台股落底訊號回測
description: A public signal report where every score is a row of lamps, in the register of the 國發會 monthly 景氣對策信號 table.
colors:
  ground: "#e8eaee"
  panel: "#ffffff"
  panel-2: "#f3f4f7"
  ink: "#1c1f24"
  ink-2: "#464d58"
  ink-3: "#5f6671"
  rule: "#d2d5db"
  rule-2: "#e4e6eb"
  rule-ink: "#1c1f24"
  lamp-blue: "#2456ad"
  lamp-red: "#cc3328"
  lamp-amber: "#d99511"
  lamp-green: "#2c9152"
  lamp-yr: "#e0731f"
  lamp-off: "#b9bec6"
  wash-blue: "#e4ebf7"
  wash-red: "#f9e5e2"
  wash-amber: "#f8eed6"
  up: "#c22b24"
  down: "#15734a"
  warn: "#9a5600"
  focus: "#2456ad"
  chart-axis: "#8c929b"
  chart-muted: "#c9cdd3"
  ground-dark: "#0f1113"
  panel-dark: "#171a1e"
  panel-2-dark: "#1e2227"
  ink-dark: "#e8eaed"
  ink-2-dark: "#c1c6cd"
  ink-3-dark: "#a1a8b2"
  rule-dark: "#2d3239"
  rule-2-dark: "#252a30"
  lamp-blue-dark: "#5d8ff0"
  lamp-red-dark: "#ff6457"
  lamp-amber-dark: "#f0b43c"
  lamp-green-dark: "#4cc27c"
  lamp-yr-dark: "#ff9a4d"
  lamp-off-dark: "#4b525b"
  wash-blue-dark: "#1b2840"
  wash-red-dark: "#3a1f1d"
  wash-amber-dark: "#352a14"
  up-dark: "#ff6b63"
  down-dark: "#4cc38a"
  warn-dark: "#f0a43a"
  focus-dark: "#7da6f5"
  chart-axis-dark: "#7d848e"
  chart-muted-dark: "#3d434b"
typography:
  display:
    fontFamily: "Noto Sans TC, system-ui, -apple-system, PingFang TC, Microsoft JhengHei, sans-serif"
    fontSize: "5.5rem"
    fontWeight: 900
    lineHeight: 1
    letterSpacing: "-0.035em"
    fontFeature: "tnum"
  score:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "2rem"
    fontWeight: 900
    letterSpacing: "-0.02em"
    fontFeature: "tnum"
  headline:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 900
    letterSpacing: "0.01em"
  brand:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 900
    letterSpacing: "0.02em"
  title:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
  body:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.6
  body-sm:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
  caption:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.6
  lamp-label:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.25
  display-sm:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "3.75rem"
    fontWeight: 900
    lineHeight: 1
    letterSpacing: "-0.035em"
    fontFeature: "tnum"
  score-sm:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "1.625rem"
    fontWeight: 900
    letterSpacing: "-0.02em"
    fontFeature: "tnum"
  lamp-label-sm:
    fontFamily: "Noto Sans TC, system-ui, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 400
    lineHeight: 1.25
rounded:
  focus: "2px"
  panel: "3px"
  control: "4px"
  lamp: "50%"
spacing:
  gutter: "24px"
  gutter-sm: "16px"
  section-gap: "16px"
  section-pad: "24px"
  stack: "14px"
  row: "10px"
  container: "1240px"
components:
  report-panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "24px 24px 22px"
  chip:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink-3}"
    rounded: "{rounded.panel}"
    padding: "0 8px"
    typography: "{typography.caption}"
  chip-bottom:
    backgroundColor: "{colors.wash-blue}"
    textColor: "{colors.lamp-blue}"
    rounded: "{rounded.panel}"
  chip-top:
    backgroundColor: "{colors.wash-red}"
    textColor: "{colors.lamp-red}"
    rounded: "{rounded.panel}"
  chip-warn:
    backgroundColor: "{colors.wash-amber}"
    textColor: "{colors.warn}"
    rounded: "{rounded.panel}"
  chip-level:
    rounded: "{rounded.panel}"
    padding: "1px 10px"
    typography: "{typography.body-sm}"
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.panel}"
    rounded: "{rounded.control}"
    padding: "5px 14px"
    typography: "{typography.body-sm}"
  nav-link:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.control}"
    padding: "6px 10px"
    typography: "{typography.body-sm}"
  nav-link-hover:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.ink}"
  nav-link-current:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.panel}"
  button:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "4px 12px"
    height: "34px"
  select:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "4px 28px 4px 10px"
    height: "34px"
  tooltip:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 10px"
    typography: "{typography.caption}"
  lamp:
    rounded: "{rounded.lamp}"
    size: "14px"
  lamp-row-lamp:
    rounded: "{rounded.lamp}"
    size: "26px"
  matrix-lamp:
    rounded: "{rounded.lamp}"
    size: "13px"
---

# Design System: 台股落底訊號回測

## Overview

**Creative North Star: "The Signal Report"**

The page is a government statistical bulletin that happens to be interactive. White ruled panels sit on a cool gray ground, every heading is set in heavy Noto Sans TC ink over a 2px ink rule, and the only saturated colour on the page belongs to lamps. A score is not a number in a card: it is a row of lamps, and the number beside it is a count of the lit ones. The register is the 國發會 景氣對策信號 table, which a Taiwanese reader already knows how to read.

Density is high and deliberate. Tables, the lamp matrix and charts carry the content; prose is short, plain and cautious, and captions sit next to every headline number. Nothing floats, glows or tilts. Depth comes from the step between the gray ground and the white panel, and from rules, not from shadows.

Colour carries two separate meanings that must never cross. Lamp colours name the signal family (blue 落底, red 過熱, amber-over-blue 偏空). Red and green on numbers name direction of return (red up, green down, the Taiwan convention). The page states this on itself.

**Key Characteristics:**
- Cool gray ground (#e8eaee), white ruled report panels, ink #1c1f24, one typeface.
- Lamps are the signature: solid = lit today, dot inside a ring = lit within 5 days, hollow gray ring = off.
- Heavy 900-weight numerals and headings over 2px ink rules; everything else light and gray.
- Tabular figures everywhere numbers appear.
- Flat: one soft shadow in the whole system, on floating tooltips only.

## Colors

A near-monochrome ink-and-paper report with four lamp hues that each mean exactly one thing.

### Primary
- **Signal Blue** (lamp-blue): the 落底 family lamp, the thermometer line and its ≥95 reference, the dual-confirmation lamp, the disclosure triangle, link hover. Also the focus ring colour (focus).
- **Signal Red** (lamp-red): the 過熱 family lamp, markers and dots only.
- **Signal Amber** (lamp-amber): the 偏空 family; on lamps always paired with blue as a diagonal split.

### Secondary
- **Brand-mark Green** (lamp-green) and **Brand-mark Yellow-Red** (lamp-yr): exist only to complete the five-lamp 景氣對策信號 sequence in the brand mark. No signal family uses them.
- **Washes** (wash-blue, wash-red, wash-amber): tinted chip grounds for family chips; wash-blue also marks the current row in tables, the thermometer area fill and text selection.

### Tertiary
- **Return Up** (up) and **Return Down** (down): text and return bars only, for signed returns. `up` doubles as the error-text colour.
- **Caution Ochre** (warn): text-safe amber for stale data stamps, pending-post notes and the 偏空 chip text.

### Neutral
- **Cool Gray Ground** (ground): page background and sticky top bar.
- **Report White** (panel) and **Panel Tint** (panel-2): panels; panel-2 for hover rows, today's matrix column, chart bands and buttons.
- **Ink** (ink), **Ink 2** (ink-2), **Ink 3** (ink-3): headings and numerals / body prose / captions, axis text, labels.
- **Rule** (rule), **Light Rule** (rule-2), **Ink Rule** (rule-ink): panel borders and row dividers / table body lines and chart grid / the 2px heading underline and table header line.
- **Lamp Off** (lamp-off): the hollow ring of an unlit lamp.
- Dark mode swaps every token for its `-dark` value (ground #0f1113, panel #171a1e, ink #e8eaed); lamps brighten rather than darken. It follows `prefers-color-scheme` unless `data-theme="light"`, and `data-theme="dark"` forces it.

### Named Rules
**The Two Reds Rule.** Lamp colours mean signal family; red/green on figures means return direction. Never colour a lamp by return, never colour a return by family. Lamp red (#cc3328) and return red (#c22b24) are separate tokens for this reason.

**The Lamps Own the Colour Rule.** Saturated colour appears on lamps, family chips and data marks. Panels, headings, nav and controls stay ink and gray.

**The Split Lamp Rule.** 偏空 is never plain amber on a lamp: fill is a 135deg split, amber top-left and blue bottom-right, and the ring is amber on top/left, blue on right/bottom.

## Typography

**Display Font:** Noto Sans TC (with system-ui, -apple-system, PingFang TC, Microsoft JhengHei, sans-serif)
**Body Font:** Noto Sans TC, same stack
**Label/Mono Font:** none; numbers use `font-variant-numeric: tabular-nums` on `.lb-num` and all tables.

**Character:** One sans family carries the whole report through weight alone: 900 for numerals, section titles and the brand; 700 for subheads and emphasis; 500 for nav, current-state labels and table headers; 400 for prose.

### Hierarchy
- **Display** (900, 5.5rem, lh 1, -0.035em): the 鄉民恐慌溫度 reading only. 3.75rem at ≤720px. Its "/ 100" suffix is 1.25rem 500 ink-3, followed by the level chip (`.lb-level`, 14px, padding 1px 10px, blue-toned at ≥90) centred on the numeral line.
- **Score** (900, 2rem, -0.02em): family scores beside each lamp row; 1.625rem at ≤720px, suffix "/ 7" at 1rem ink-3.
- **Headline** (900, 1.25rem, 0.01em): section titles, always over a 2px ink rule with 10px padding.
- **Brand** (900, 1.0625rem, 0.02em): top-bar title; 1rem at ≤720px.
- **Title** (700, 1rem): sub-headings inside panels and the today band.
- **Body** (400, 0.9375rem, lh 1.6): prose, capped at 46–52em.
- **Body small** (0.875rem): tables, nav, controls, disclosure summaries.
- **Caption** (0.8125rem, lh 1.6, ink-3): context lines, legends, table headers, tooltips, stamps, chips (chips at 700).
- **Lamp label** (0.75rem, lh 1.25): names under lamps, matrix date headers; 0.6875rem at ≤720px. Chart text 12px, chart event labels 11px with a 3px panel-coloured halo stroke.

### Named Rules
**The Weight Not Size Rule.** Hierarchy steps are small (13 / 14 / 15 / 16 / 20px); weight does the work. Only the reading and the scores break scale.

## Layout

Single column of stacked report panels inside a 1240px container with 24px gutters (16px at ≤720px).

- **Top bar:** sticky, on the ground colour, 1px rule beneath, min-height 60px (52px mobile). Three-column grid: brand, nav, data stamp. `scroll-padding-top` 116px (104px mobile).
- **Today band:** full-width white band with a bottom rule, 32px/28px vertical padding, grid 5fr : 6fr with 32px row and 56px column gaps. Left: reading; right: three family lamp rows and the lamp key.
- **Main:** panels in a grid with a 16px gap (12px mobile), each padded 24 / 24 / 22 with a 14px internal stack.
- **Rhythm:** 4 / 6 / 8 / 10 / 14 / 16 / 18 / 24 / 32px; nothing larger than 56px.

**At ≤1080px:** the today band becomes one column; the nav drops to its own full-width second row in the top bar and scrolls horizontally with hidden scrollbar.

**At ≤720px:** the reading block dissolves (`display: contents`) and its parts reorder: mobile stamp, title, reading (numeral and level chip), scale, caveat context line, then the three family lamp rows, then the lamp key, then the data line, then 雙重確認, then the 「溫度怎麼算」 disclosure last. Family captions lead with the sample size, clamp to two lines and expand on tap (they become role=button). Panels bleed 8px into the gutter (margin 0 -8px, padding 18/14/16). Lamp rows shrink to 20px lamps with 2px gaps. The matrix keeps only the last 8 days (`KEEP = 8`), drops the threshold and last-lit columns, swaps to short names (min 6.5em) with the threshold as a small line beneath, narrows day columns to 20px and tightens the value column to 13px with 6px left padding. Table first columns wrap within 7.5–9.5em. The top-bar stamp hides in favour of the in-band stamp.

## Elevation & Depth

Flat. Depth is the step from gray ground to white panel plus 1px rules. The one shadow lives on floating tooltips. Horizontally scrolling tables use a scroll-shadow gradient (panel-coloured fades with a 12px radial edge shade) to signal overflow.

### Shadow Vocabulary
- **Tooltip lift** (`box-shadow: 0 6px 20px rgba(20, 24, 30, 0.16)`; dark `rgba(0,0,0,0.5)`): chart and matrix tooltips only.

### Named Rules
**The Ruled Not Raised Rule.** Separate with rules (1px rule, 2px ink under headings), never with shadow, on any resting surface.

## Shapes

Barely softened rectangles and true circles. Panels and chips round 3px; controls, nav links and tooltips 4px. Lamps are perfect circles with a 2px ring (3px in lamp rows, 2.5px on mobile). Disclosure markers are CSS triangles in signal blue that rotate 90deg when open. Chart markers reuse the lamp geometry; event labels on the thermometer chart use a small ink diamond.

## Components

### Lamp (signature)
A circle with a ring and an optional inner dot, sized by `--ls` (14px default).
- **on (lit today):** ring and fill in the family colour.
- **recent (lit within 5 days, counts toward the score):** family-colour ring, inset 22% dot in the family colour, open gap between.
- **off:** hollow lamp-off ring.
- **偏空 split:** fill is a 135deg amber/blue split; ring amber top-left, blue bottom-right, in both on and recent.
- **In SVG charts:** the same three states drawn with circles: on = filled, recent = ring on panel fill plus a dot at 42% radius, stroke 2.
- **In the matrix:** off cells are not rings but a 6px rule-gray dot with no border, so lit lamps read at matrix density.
- Sizes: 26px lamp rows, 20px scale and dual, 13px matrix and key, 12px legends, 11px group headers.

### Lamp Row
One row per family: title, family chip, then the score (900, 2rem) right-aligned with "/ N". Below it an 8-column grid of lamps with 12px labels; lit and recent labels turn ink 500. Fixed signal order so a lamp's position never moves day to day. Rows separate with 1px rules, padding 16px.

### Thermometer Scale
A five-step ordered list on a 2px ink top rule: 平常 <80, 留意, 偏恐慌, 恐慌, 極度恐慌 ≥95. Each step a 20px blue lamp; only the current step is lit, with its name at ink 900.

### Lamp Matrix
Signals × last 20 trading days. Sticky name column (min 11.5em) with names as underline-on-hover buttons that open the signal's event history. 30px rows on rule-2 lines, ink-rule header. Group header rows carry an 11px lit family lamp, the group name and score inside a sticky-left span, so the label stays in view while days scroll. Today's column sits on panel-2 with a bold date. Value column right-aligned, the 今日值 cell bold. Rows hover to panel-2.
- **Keyboard:** lamp cells are focusable with one tab stop per row (today's cell), roving with Left/Right, Home/End and Up/Down (skipping group rows); inset 2px focus ring. Escape hides the tooltip.
- **Cell tooltip:** one shared fixed tooltip (`#lb-mtip`, role=status) that escapes the scroll container and re-places itself on window and table scroll, above the cell or below it when there is no room. Lines: the date (marked 最新一天 for today), the lit state, that day's value with its threshold (from the status `recent` array), then today's value with threshold and the last-lit date.

### Report Panels
White, 1px rule border, 3px radius, 24px padding. Heading 1.25rem 900 over a 2px ink rule. Lead paragraph in ink-2, max 48em. The definitions panel is a `details` with the same border.

### Tables
Collapsed, 14px, right-aligned tabular figures, sticky left label column on panel. Headers 13px 500 ink-3, balanced wrap, ink rule below; body rows on rule-2. Clickable rows hover to panel-2; the current row sits on wash-blue at 700. Combination rows (combo) are bold. Event rows carry a caption sub-row joined with "｜" separators.

### Chips
Inline 13px 700 labels, 3px radius, line-height 1.7, padding 0 8px. Neutral: 1px rule border, ink-3. The level chip beside the reading is the one larger variant (14px, padding 1px 10px). Toned: borderless on a wash with the family colour as text (bottom / top), warn uses ochre text on amber wash.

### Controls
Select, button and date inputs share 14px type, 1px rule border, 4px radius, 34px min-height. Buttons sit on panel-2 and press to rule-2; selects draw a two-gradient chevron in ink-3. Hover darkens the border to ink-3.

### Navigation
Top-bar section links: 14px 500 ink-2, 6px 10px padding, 4px radius. Hover to panel-2/ink; the current section inverts to ink background with panel text. Transitions 150ms ease-out.

### Tooltips
Panel background, 1px rule border, 4px radius, 8px 10px padding, 13px lh 1.55, max 280px, tooltip-lift shadow. Absolute inside charts; the matrix uses the `.lb-tip--fixed` variant (position fixed, z-index 20) so it is never clipped by the table's scroll container.

### Charts
- Price line ink-2 1.4px; event dots ink-3; event labels 11px with halo.
- Signal markers drawn as lamps in family colour: ≥4 on, ≥3 recent.
- Score strips: blue / red / amber bars whose opacity steps with the score (0.2, 0.45, 0.75, 1).
- Return bars: up/down colours by sign, never family colours.
- Distance-to-low dots: family colour, 4px, combos at 0.95 opacity, singles at 0.5, panel-colour stroke.
- Thermometer: blue line over a wash-blue area, dashed (4 3) reference lines: 90 in ink-3, 95 in lamp-blue (only the signal threshold takes the family colour).
- Grid rule-2, axis #8c929b, hover rule and drag-select band in chart-muted at 0.3.

## Do's and Don'ts

### Do:
- **Do** express any family score as a row of lamps with the count beside it.
- **Do** use the three lamp states exactly: solid today, dot-in-ring within 5 days, hollow off.
- **Do** keep red-up/green-down on return figures and return bars, using `up` and `down`.
- **Do** put every section title over a 2px ink rule at 1.25rem 900.
- **Do** use tabular figures for every number and right-align numeric columns.
- **Do** keep the matrix keyboard-reachable: one tabbable cell per row, arrow/Home/End roving, inset 2px focus ring, Escape to dismiss the tooltip.

### Don't:
- **Don't** colour a lamp, marker or family chip by return direction, or a return figure by family.
- **Don't** use lamp-green or lamp-yr outside the five-lamp brand mark.
- **Don't** draw 偏空 as a plain amber lamp; it is always the amber/blue split.
- **Don't** add shadows to resting panels, chips or controls; only floating tooltips lift.
- **Don't** introduce a second typeface; weight carries hierarchy.
- **Don't** replace the lamp-row score with a gauge or a metric card.
