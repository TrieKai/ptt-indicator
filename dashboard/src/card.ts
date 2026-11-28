// 今日圖卡：網頁上的「分享今天」與連結預覽圖（og:image）共用這一份畫法。
// 圖卡一律用淺色，1200 × 630（連結預覽的標準比例）；scale 2 給分享用的高解析度版本。
import { FAM, temperatureLevels as LEVELS } from './signals.ts';
import type { DailyRow, Family, LampSignal, LampState, StatusRow, SummaryRow } from './data.ts';

// 落底面、過熱面只當參考（分數回測不顯著，2026/11/27 起不顯示分數）；偏空警示照舊
const FAM_INFO = { bottom: ['落底面', 'score', 7], top: ['過熱面', 'gscore', 8], warn: ['偏空警示', 'wscore', 3] } as const;
const C = {
  ground: '#e8eaee', panel: '#ffffff', ink: '#1c1f24', ink2: '#464d58', ink3: '#5f6671', rule: '#d2d5db', rule2: '#e4e6eb',
  blue: '#2456ad', red: '#cc3328', amber: '#d99511', green: '#2c9152', yr: '#e0731f', off: '#b9bec6',
  washBlue: '#e4ebf7', washRed: '#f9e5e2', washAmber: '#f8eed6', warn: '#9a5600',
};
const FAMC = { bottom: C.blue, top: C.red, warn: C.amber };
const FONT = '"Noto Sans TC", system-ui, -apple-system, "PingFang TC", "Microsoft JhengHei", sans-serif';
const ymd = (s: string | null | undefined) => (s ? s.replaceAll('-', '/') : '—');
const pct = (x: number | null | undefined) => (x == null ? '—' : (x > 0 ? '+' : '') + x.toFixed(2) + '%');

// 由 status（全部列）、最新一天的 daily 列、summary（全部列）整理出圖卡要畫的內容
export const model = (status: StatusRow[], dailyLast: DailyRow | null, summary: SummaryRow[]) => {
  const st = (k: StatusRow['signal']) => status.find((r) => r.signal === k) || null;
  const sm = (k: SummaryRow['signal']) => (summary || []).find((r) => r.signal === k && r.index === 'TAIEX') || null;
  const t = st('thermo'); if (!t) return null;
  const level = [...LEVELS].reverse().find(([lv]) => t.value >= lv) ?? LEVELS[0];
  const lamp = (sig: LampSignal): LampState => {
    const r = st(sig);
    if (!r || !dailyLast || r.asof !== dailyLast.date || r.threshold == null) return 'missing';
    if (dailyLast[`f_${sig}`] === 1) return 'on';
    return r.lit5 === 1 ? 'recent' : 'off';
  };
  const fams = (['bottom', 'warn'] as const).map((key) => {   // 過熱面回測沒有效果，2026/11/27 起圖卡不畫
    const [name, scoreSig, of] = FAM_INFO[key], sc = st(scoreSig), v = sc ? sc.value : 0;
    const on = key === 'warn' ? v >= 1 : v >= 3;
    const ref = key !== 'warn';
    return { key, name, score: v, of, on: ref ? false : on, ref, chip: ref ? '參考' : (on ? '近 5 日有警示' : '近 5 日未見警示'),
      lamps: FAM[key].map(([sig, label]) => ({ sig, label, s: lamp(sig) })) };
  });
  const dualLamp = (d: StatusRow): LampState => d.value === 1 ? 'on' : d.lit5 === 1 ? 'recent' : 'off';
  const d = st('dual'), s95 = sm('thermo95');
  return {
    asof: ymd(t.asof), ptt: t.ptt_asof ? t.ptt_asof.slice(5).replace('-', '/') : null,
    thermo: t.value, level: level[1], levelRange: level[2], levelIdx: LEVELS.indexOf(level),
    t95: s95 ? {
      n: s95.n, n20: s95.n20, nDrawdown: s95.further_n,
      low: s95.ext_n ? s95.ext_within5_n + '/' + s95.ext_n + ' 次' : s95.ext_within5 == null ? '—' : Math.round(s95.ext_within5) + '%',
      ret: pct(s95.ret20), dd: pct(s95.further_mean),
    } : null,
    dual: d ? {
      s: dualLamp(d),
      text: d.value === 1 ? '本交易日成立' : '本交易日未成立',
      recent: d.value === 0 && d.lit5 === 1,
    } : null,
    fams,
  };
};

// 分享時附的文字
type CardModel = NonNullable<ReturnType<typeof model>>;

export const text = (m: CardModel) => '鄉民恐慌溫度 ' + m.thermo.toFixed(1) + '（' + m.level + '）'
  + (m.dual ? '・雙重確認' + m.dual.text + (m.dual.recent ? '（近 5 個交易日曾亮燈）' : '') : '') + '（收盤資料日 ' + m.asof + '）';

// 圖卡上出現的字（先載入字型的對應字集）
const glyphs = (m: CardModel) => ['台股落底訊號回測資料日鄉民恐慌溫度/100（）≥平常留意偏恐慌極度0123456789.+-–%<>',
  '2019 年起達 95 共次，低點在亮燈前後 5 個交易日內。20 日平均報酬平均最低收盤筆樣本少請保守看待',
  '雙重確認本交易日成立未近5個交易日曾亮燈畢業文創作文達門檻加權距高點跌至少藍黃＝落底偏空虛線待資料收盤',
  'triekai.github.io/ptt-indicator歷史統計不代表未來，也不是投資建議', m ? m.fams.map((f) => f.name + f.chip + f.lamps.map((l) => l.label).join('')).join('') : '',
  'VIXP/C高低外資賣買融資減增違約期貨多單量能乖離淨空佔比警示亮燈未達參考面'].join('');
export const fontsReady = async (m: CardModel) => {
  if (!document.fonts || !document.fonts.load) return;
  const t = glyphs(m);
  const load = Promise.all(['400', '500', '700', '900'].map((w) => document.fonts.load(w + ' 24px "Noto Sans TC"', t)));
  await Promise.race([load, new Promise((r) => setTimeout(r, 5000))]);
};

const lampAt = (g: CanvasRenderingContext2D, x: number, y: number, r: number, fam: Family | null, s: LampState) => {
  const col = fam ? FAMC[fam] : C.off, lw = Math.max(1.5, r * 0.2);
  if (s === 'missing') {
    g.save(); g.setLineDash([3, 3]); g.lineWidth = lw; g.strokeStyle = C.ink3;
    g.beginPath(); g.arc(x, y, r - lw / 2, 0, Math.PI * 2); g.stroke(); g.restore();
    return;
  }
  const split = fam === 'warn' && s !== 'off';
  const fillSplit = (rr: number) => {
    g.save(); g.beginPath(); g.arc(x, y, rr, 0, Math.PI * 2); g.clip();
    g.fillStyle = C.amber; g.fillRect(x - rr, y - rr, rr * 2, rr * 2);
    g.fillStyle = C.blue; g.beginPath(); g.moveTo(x + rr, y - rr); g.lineTo(x + rr, y + rr); g.lineTo(x - rr, y + rr); g.closePath(); g.fill();
    g.restore();
  };
  const ring = () => {
    g.lineWidth = lw;
    if (split) {
      g.strokeStyle = C.amber; g.beginPath(); g.arc(x, y, r - lw / 2, Math.PI * 0.75, Math.PI * 1.75); g.stroke();
      g.strokeStyle = C.blue; g.beginPath(); g.arc(x, y, r - lw / 2, Math.PI * 1.75, Math.PI * 2.75); g.stroke();
    } else { g.strokeStyle = s === 'off' ? C.off : col; g.beginPath(); g.arc(x, y, r - lw / 2, 0, Math.PI * 2); g.stroke(); }
  };
  if (s === 'on') { if (split) fillSplit(r); else { g.fillStyle = col; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.fill(); } }
  else if (s === 'recent') { ring(); if (split) fillSplit(r * 0.45); else { g.fillStyle = col; g.beginPath(); g.arc(x, y, r * 0.45, 0, Math.PI * 2); g.fill(); } }
  else ring();
};
const chip = (g: CanvasRenderingContext2D, x: number, y: number, label: string, tone: Family | null, size: number) => {
  g.font = '700 ' + size + 'px ' + FONT;
  const w = g.measureText(label).width + size * 0.9, h = size * 1.6;
  const bg = tone && { bottom: C.washBlue, top: C.washRed, warn: C.washAmber }[tone], fg = tone && { bottom: C.blue, top: C.red, warn: C.warn }[tone];
  if (bg) { g.fillStyle = bg; rr(g, x, y - h / 2, w, h, 4); g.fill(); }
  else { g.strokeStyle = C.rule; g.lineWidth = 1.5; rr(g, x + 0.75, y - h / 2 + 0.75, w - 1.5, h - 1.5, 4); g.stroke(); }
  g.fillStyle = fg || C.ink3; g.textBaseline = 'middle'; g.fillText(label, x + size * 0.45, y + 1); g.textBaseline = 'alphabetic';
  return w;
};
const rr = (g: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) => { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); };
const wrap = (g: CanvasRenderingContext2D, s: string, maxW: number) => {
  const out = []; let line = '';
  const hang = '，。、）」％：；！？%';   // 標點不放在行首
  for (const ch of s) {
    if (g.measureText(line + ch).width > maxW && line && !hang.includes(ch)) { out.push(line); line = ch.trim() ? ch : ''; } else line += ch;
  }
  if (line) out.push(line); return out;
};

const W = 1200, H = 630;
export const draw = (canvas: HTMLCanvasElement, m: CardModel, scale: number) => {
  const s = scale || 1; canvas.width = W * s; canvas.height = H * s;
  const g = canvas.getContext('2d');
  if (!g) throw new Error('瀏覽器無法建立圖卡畫布');
  g.setTransform(s, 0, 0, s, 0, 0);
  g.fillStyle = C.panel; g.fillRect(0, 0, W, H);
  // 頁首
  g.fillStyle = C.ground; g.fillRect(0, 0, W, 72);
  g.fillStyle = C.rule; g.fillRect(0, 72, W, 1);
  [C.blue, null, C.green, C.yr, C.red].forEach((c, i) => {
    const x = 56 + i * 17, y = 36;
    if (c) { g.fillStyle = c; g.beginPath(); g.arc(x, y, 6.5, 0, Math.PI * 2); g.fill(); } else lampAt(g, x, y, 6.5, 'warn', 'on');
  });
  g.fillStyle = C.ink; g.font = '900 27px ' + FONT; g.fillText('台股落底訊號回測', 148, 46);
  g.textAlign = 'right'; g.fillStyle = C.ink3; g.font = '500 19px ' + FONT;
  g.fillText('收盤資料日 ' + m.asof + (m.ptt ? '・PTT 文章至 ' + m.ptt : ''), W - 48, 44); g.textAlign = 'left';

  // 左：鄉民恐慌溫度
  const L = 48, LW = 520;
  g.fillStyle = C.ink; g.font = '700 24px ' + FONT; g.fillText('鄉民恐慌溫度', L, 122);
  g.font = '900 150px ' + FONT; const num = m.thermo.toFixed(1); g.fillText(num, L - 4, 262);
  const nw = g.measureText(num).width;
  g.fillStyle = C.ink3; g.font = '500 28px ' + FONT; g.fillText('/ 100', L + nw + 8, 262);
  chip(g, L, 306, m.level + '（' + m.levelRange + '）', m.thermo >= 90 ? 'bottom' : null, 21);
  g.fillStyle = C.ink; g.fillRect(L, 346, LW, 2.5);
  const sw = LW / 5;
  LEVELS.forEach((lv, i) => {
    const x = L + i * sw, on = i === m.levelIdx;
    lampAt(g, x + 11, 376, 11, on ? 'bottom' : null, on ? 'on' : 'off');
    g.fillStyle = on ? C.ink : C.ink2; g.font = (on ? '900 ' : '500 ') + '18px ' + FONT; g.fillText(lv[1], x, 412);
    g.fillStyle = C.ink3; g.font = '400 15px ' + FONT; g.fillText(lv[2], x, 434);
  });
  if (m.t95) {
    const count = (n: number | null | undefined) => n == null ? '' : '（' + n + ' 筆）';
    g.font = '400 18px ' + FONT; g.fillStyle = C.ink2;
    const cav = [
      '2019 年起達 95 共 ' + m.t95.n + ' 次。低點在亮燈前後 5 個交易日內 ' + m.t95.low + '。',
      '20 日平均報酬 ' + m.t95.ret + count(m.t95.n20) + '，平均最低收盤 ' + m.t95.dd + count(m.t95.nDrawdown) + '。',
      '樣本少，請保守看待。',
    ];
    cav.flatMap((line) => wrap(g, line, LW)).forEach((ln, i) => g.fillText(ln, L, 464 + i * 20));
  }

  // 右：落底面與偏空警示兩排燈、雙重確認
  const R = 628, RW = W - 48 - R;
  m.fams.forEach((f, k) => {
    const top = 92 + k * 132;
    g.fillStyle = C.ink; g.font = '700 23px ' + FONT; g.fillText(f.name, R, top + 32);
    const nmw = g.measureText(f.name).width;
    chip(g, R + nmw + 12, top + 24, f.chip, f.on ? f.key : null, 17);
    if (!f.ref) {   // 參考燈號不畫分數
      g.textAlign = 'right';
      g.fillStyle = C.ink3; g.font = '500 21px ' + FONT; g.fillText('/ ' + f.of, W - 48, top + 36);
      const ow = g.measureText('/ ' + f.of).width;
      g.fillStyle = C.ink; g.font = '900 44px ' + FONT; g.fillText(String(f.score), W - 48 - ow - 6, top + 38);
      g.textAlign = 'left';
    }
    const slot = RW / 8;
    f.lamps.forEach((l, i) => {
      const cx = R + slot * i + slot / 2;
      lampAt(g, cx, top + 74, 15, l.s === 'off' ? null : f.key, l.s);
      g.textAlign = 'center'; g.fillStyle = l.s === 'off' ? C.ink3 : C.ink; g.font = (l.s === 'off' ? '400 ' : '700 ') + '15px ' + FONT;
      g.fillText(l.label, cx, top + 112); g.textAlign = 'left';
    });
    g.fillStyle = C.rule2; g.fillRect(R, top + 126, RW, 1.5);
  });
  if (m.dual) {
    const y = 92 + m.fams.length * 132 + 40;
    lampAt(g, R + 12, y, 12, m.dual.s === 'off' ? null : 'bottom', m.dual.s);
    g.fillStyle = C.ink; g.font = '700 20px ' + FONT; g.fillText('雙重確認', R + 34, y + 7);
    const sx = R + 34 + g.measureText('雙重確認').width + 10;
    const sw = chip(g, sx, y, m.dual.text, m.dual.s === 'on' ? 'bottom' : null, 16);
    g.font = '400 16px ' + FONT; g.fillStyle = C.ink2;
    if (m.dual.recent) g.fillText('近 5 個交易日曾亮燈', sx + sw + 12, y + 6);
    g.fillText('畢業文與創作文達門檻，加權距 60 日高點跌至少 5%。', R + 34, y + 37);
  }

  // 頁尾：網址、燈號說明、免責
  g.fillStyle = C.rule; g.fillRect(48, 556, W - 96, 1);
  g.fillStyle = C.ink; g.font = '700 18px ' + FONT; g.fillText('triekai.github.io/ptt-indicator', 48, 594);
  let x = 400; g.font = '400 15px ' + FONT;
  ([['bottom', 'on', '藍＝落底'], ['warn', 'on', '黃藍＝偏空'], ['bottom', 'recent', '近 5 日亮過'], [null, 'missing', '待資料']] as const).forEach(([fam, st, t]) => {
    lampAt(g, x + 7, 588, 7, fam, st); g.fillStyle = C.ink3; g.fillText(t, x + 19, 594); x += 19 + g.measureText(t).width + 16;
  });
  g.textAlign = 'right'; g.fillStyle = C.ink3; g.font = '400 15px ' + FONT;
  g.fillText('歷史統計不代表未來，也不是投資建議', W - 48, 594); g.textAlign = 'left';
};
