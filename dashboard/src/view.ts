import type { BaseType, Selection } from 'd3';
import { backtestSignals, eventColumnNames, families, isOption, markets, postSignals, statusSignals, validDate } from './data.ts';
import type { BacktestEvent, BacktestSignal, DailyRow, EventField, EventRow, Family, LampSignal, LampState, Market, PostSignal, StatusRow, StatusSignal, SummaryRow } from './data.ts';
import type { Dashboard } from './runtime.ts';
import { dualStatus, FAM, temperatureLevels as T_LEVELS } from './signals.ts';

type MaybeNumber = number | null | undefined;
type Zoom = [Date, Date] | null;
type UrlParams = Record<string, string | null>;
type Cell = [text: string | null | undefined, value?: MaybeNumber, note?: string];
type SignalLabels = [LampSignal, string][];
const ranges = ['all', '3y', '1y', '6m'] as const;
type Range = typeof ranges[number];

function present<T>(value: T): value is NonNullable<T> {
  return value != null;
}

function requireElement<T extends HTMLElement>(element: Element | null | undefined, type: new () => T): T {
  if (!(element instanceof type)) throw new Error('儀表板缺少 ' + type.name);
  return element;
}

function byId<T extends HTMLElement>(id: string, type: new () => T): T {
  return requireElement(document.getElementById(id), type);
}

type ViewState = {
  ix: Market;
  tix: Market;
  range: Range;
  trange: Range;
  strip: Family;
  evsig: BacktestSignal;
  eventIndex: Market;
  eventDate: string | null;
  psig: PostSignal;
  pevent: string | null;
  zMain: Zoom;
  zTherm: Zoom;
};

const strips: Record<Family, SignalLabels> = {
  bottom: [['vix_high', '美國VIX高'], ['pc_high', 'P/C偏高'], ['foreign', '外資大賣'], ['margin', '融資大減'], ['default', '違約爆量'], ['loss', '畢業文'], ['creative', '創作文'], ['bigdrop', '單日跌3%']],
  warn: [['fut_short', '淨空單極端'], ['fut_ratio_short', '空單佔比極端'], ['fut_chg_short', '5日大增空單']],
  top: [['vix_low', '美國VIX低'], ['pc_low', 'P/C偏低'], ['fut_long', '外資多單'], ['foreign_buy', '外資大買'], ['margin_up', '融資大增'], ['turnover', '量能爆量'], ['hot_ptt', '過熱文'], ['stretch', '乖離過大']],
};

export function registerDashboard(dash: Dashboard, charts: () => typeof import('d3')) {
  const state: ViewState = {
    ix: 'TAIEX', tix: 'TAIEX', range: 'all', trange: '1y', strip: 'bottom',
    evsig: 'thermo95', eventIndex: 'TAIEX', eventDate: null, psig: 'creative', pevent: null,
    zMain: null, zTherm: null,
  };
  const LB = {
    ...state,
    BORDER: ['dual', 'thermo95', 'thermo90', 'combo4', 'combo3', 'combo5_3', 'vix_high', 'pc_high', 'foreign', 'margin', 'default', 'loss', 'creative', 'bigdrop'] satisfies BacktestSignal[],
    WORDER: ['fut_short', 'fut_ratio_short', 'fut_chg_short'] satisfies BacktestSignal[],
    TORDER: ['gcombo4', 'gcombo3', 'vix_low', 'pc_low', 'fut_long', 'foreign_buy', 'margin_up', 'turnover', 'hot_ptt', 'stretch'] satisfies BacktestSignal[],
    STRIP: strips,
    FAM,
    FAMC: { bottom: 'var(--lamp-blue)', top: 'var(--lamp-red)', warn: 'var(--lamp-amber)' },
    SHORT: { dual: '雙重確認', thermo95: '溫度≥95', thermo90: '溫度≥90', thermo85: '溫度≥85', thermo80: '溫度≥80', combo4: '落底≥4', combo3: '落底≥3', combo5_3: '原5訊號≥3', vix_high: '美國VIX高', pc_high: 'P/C偏高', fut_short: '淨空單極端', fut_ratio_short: '空單佔比極端', fut_chg_short: '5日大增空單', foreign: '外資大賣', margin: '融資大減', default: '違約爆量', loss: '畢業文', creative: '創作文', bigdrop: '單日跌3%',
      gcombo4: '過熱≥4', gcombo3: '過熱≥3', vix_low: '美國VIX低', pc_low: 'P/C偏低', fut_long: '外資多單', foreign_buy: '外資大買', margin_up: '融資大增', turnover: '量能爆量', hot_ptt: '過熱文', stretch: '乖離過大' } satisfies Record<BacktestSignal, string>,
    parse: (date: string) => new Date(date + 'T00:00:00Z'),
    iso: (date: Date) => date.toISOString().slice(0, 10),
    date: (date: Date) => date.toISOString().slice(0, 10).replaceAll('-', '/'),
    dateW: (date: Date) => date.toISOString().slice(0, 10).replaceAll('-', '/') + '（' + '日一二三四五六'[date.getUTCDay()] + '）',
    // 長區間標年；兩年內的月初刻度標「年/月」（手機只標「6月」，1 月標年份），其他刻度標「月/日」
    axisFormat: (spanD: number, narrow: boolean) => {
      const d3 = charts(), year = d3.utcFormat('%Y'), month = d3.utcFormat(narrow ? '%-m月' : '%Y/%m'), day = d3.utcFormat('%m/%d');
      return (date: Date) => spanD >= 800 || (narrow && date.getUTCDate() === 1 && date.getUTCMonth() === 0) ? year(date)
        : date.getUTCDate() === 1 ? month(date) : day(date);
    },
    pct: (x: MaybeNumber) => x == null ? '—' : (x > 0 ? '+' : '') + x.toFixed(2) + '%',
    pct0: (x: MaybeNumber) => x == null ? '—' : Math.round(x) + '%',
    within5: (r: SummaryRow): string => r.ext_within5 == null ? '—' :
      (r.ext_n ? r.ext_within5_n + '/' + r.ext_n + ' 次（' + LB.pct0(r.ext_within5) + '）' : LB.pct0(r.ext_within5)),
    num: (x: MaybeNumber, d?: number) => x == null ? '—' : Number(x).toLocaleString('en-US', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }),
    cls: (x: number) => x == null ? '' : x > 0 ? 'lb-up' : x < 0 ? 'lb-down' : '',
    done: (el: HTMLElement) => el.classList.remove('dash-skeleton'),
    evLabel: (r: EventRow) => r.note || (r.themes ? r.themes.split('、')[0].replace(/×\d+$/, '') : ''),
    titles: (r: EventRow) => (r.loss_titles == null || r.loss_titles === '' ? [] : Array.isArray(r.loss_titles) ? r.loss_titles : String(r.loss_titles).split('｜')).filter(Boolean),
    evLines: (r: EventRow, includeTitles = true) => [r.note ? '事件：' + r.note : '', r.themes ? '標題主題：' + r.themes : '', includeTitles && LB.titles(r).length ? '畢業文：' + LB.titles(r).slice(0, 2).join('、') : ''].filter(Boolean),
    syncDates: (a: string, b: string, rows: readonly { t: Date }[]) => {
      document.querySelectorAll<HTMLInputElement>(a).forEach((i) => { i.value = LB.iso(rows[0].t); });
      document.querySelectorAll<HTMLInputElement>(b).forEach((i) => { i.value = LB.iso(rows[rows.length - 1].t); });
    },
    // 在圖上畫一顆燈：s = 'on' 實心、'recent' 外圈加內點、'off' 空心
    lampSvg: <P extends BaseType, PD>(g: Selection<SVGGElement, unknown, P, PD>, cx: number, cy: number, r: number, color: string, s: LampState) => {
      g.append('circle').attr('cx', cx).attr('cy', cy).attr('r', r - 1).style('fill', s === 'on' ? color : 'var(--color-bg)').style('stroke', color).attr('stroke-width', 2);
      if (s === 'recent') g.append('circle').attr('cx', cx).attr('cy', cy).attr('r', Math.max(1.5, r * 0.42)).style('fill', color);
    },
  };

  const eventSelect = byId('lb-evsig', HTMLSelectElement);
  const eventIndexSelect = byId('lb-event-index', HTMLSelectElement);
  const postSelect = byId('lb-psig', HTMLSelectElement);
  const notes = byId('lb-notes', HTMLDetailsElement);
  const navMenu = requireElement(document.querySelector('.lb-nav-menu'), HTMLDetailsElement);
  const lampDetails = byId('lb-current-lamps', HTMLDetailsElement);
  const dualDetails = byId('lb-dual-conditions', HTMLDetailsElement);
  const mobileLayout = matchMedia('(max-width: 720px)');
  let pendingEventReveal: 'scroll' | 'focus' | null = null;
  const selectedOption = <T extends string>(select: HTMLSelectElement, options: readonly T[], value: string | null, fallback: T) =>
    isOption(options, value) && [...select.options].some((o) => o.value === value) ? value : fallback;
  const isPostWindow = (date: string | null) => date === 'window-latest' || date?.startsWith('window-') && validDate(date.slice(7));
  const nativeClick = (event: MouseEvent) => event.metaKey || event.ctrlKey || event.shiftKey || event.altKey;
  const sectionUrl = (id: string, params: UrlParams) => {
    const url = new URL(location.href);
    Object.entries(params).forEach(([k, v]) => v == null ? url.searchParams.delete(k) : url.searchParams.set(k, v));
    url.hash = id;
    return url;
  };
  const setEvents = (sig: BacktestSignal, date: string | null, index: Market) => {
    LB.evsig = eventSelect.value = sig;
    LB.eventIndex = eventIndexSelect.value = index;
    LB.eventDate = date;
    dash.draw('ev-body');
  };
  const setPosts = (sig: PostSignal, date: string | null) => {
    LB.psig = postSelect.value = sig; LB.pevent = date;
    dash.draw('pevent'); dash.draw('post-body'); dash.draw('post-window');
  };
  const openDisclosures = () => {
    if (location.hash === '#lb-notes') notes.open = true;
    if (location.hash === '#lb-warnings-now') lampDetails.open = true;
    if (location.hash === '#lb-dual-conditions') dualDetails.open = true;
  };
  const setLampLayout = () => { lampDetails.open = !mobileLayout.matches; openDisclosures(); };
  setLampLayout();
  mobileLayout.addEventListener('change', setLampLayout);
  document.querySelector<HTMLAnchorElement>('.lb-quick-warn')?.addEventListener('click', (event) => {
    if (!nativeClick(event)) lampDetails.open = true;
  });
  const syncSectionUrl = () => {
    const query = new URLSearchParams(location.search);
    const eventDate = query.get('event');
    const index = selectedOption(eventIndexSelect, markets, query.get('index'), 'TAIEX');
    const event = validDate(eventDate) ? eventDate : null;
    pendingEventReveal = event && location.hash === '#lb-events' ? 'scroll' : null;
    setEvents(selectedOption(eventSelect, backtestSignals, query.get('signal'), 'thermo95'), event, index);
    const date = query.get('date');
    const post = selectedOption(postSelect, postSignals, query.get('post'), 'creative');
    setPosts(post, validDate(date) || (post !== 'hot_ptt' && isPostWindow(date)) ? date : null);
    openDisclosures();
  };
  const jumpToSection = (id: string, url: URL, prepare: () => void) => {
    if (url.href !== location.href) history.pushState(null, '', url);
    prepare();
    const section = document.getElementById(id);
    dash.openSection?.(id);
    section?.querySelector('h2')?.focus({ preventScroll: true });
    section?.scrollIntoView();
  };
  function goEvents(sig: BacktestSignal, date: string | null = null, index = LB.ix) {
    jumpToSection('lb-events', sectionUrl('lb-events', { signal: sig, event: date, index }), () => {
      pendingEventReveal = date ? 'focus' : null;
      setEvents(sig, date, index);
    });
  }
  const goPosts = (sig: PostSignal, date: string, params: UrlParams = {}) => {
    jumpToSection('lb-posts', sectionUrl('lb-posts', { ...params, post: sig, date }), () => setPosts(sig, date));
  };
  document.querySelectorAll<HTMLAnchorElement>('[data-post-window]').forEach((link) => link.addEventListener('click', (event) => {
    if (nativeClick(event)) return;
    event.preventDefault();
    if (isOption(postSignals, link.dataset.postWindow)) goPosts(link.dataset.postWindow, 'window-latest');
  }));
  syncSectionUrl();
  window.addEventListener('popstate', syncSectionUrl);
  window.addEventListener('hashchange', openDisclosures);

  document.querySelectorAll<HTMLSelectElement>('select[data-ix]').forEach((s) => s.addEventListener('change', () => {
    if (!isOption(markets, s.value)) return;
    LB.ix = s.value; document.querySelectorAll<HTMLSelectElement>('select[data-ix]').forEach((o) => { o.value = LB.ix; });
    ['chart', 'sum-body', 'excess-bars', 'timing', 'timing-body'].forEach((n) => dash.draw(n));
  }));
  const lbZoomInputs = (fromId: string, toId: string, rangeId: string, resetId: string, errorId: string, key: 'zMain' | 'zTherm', name: string, rangeKey: 'range' | 'trange') => {
    const from = byId(fromId, HTMLInputElement), to = byId(toId, HTMLInputElement);
    const range = byId(rangeId, HTMLSelectElement), error = byId(errorId, HTMLElement);
    const showError = (text: string) => {
      error.textContent = text;
      [from, to].forEach((i) => { i.setAttribute('aria-invalid', String(!!text)); i.setAttribute('aria-describedby', errorId); });
    };
    [from, to].forEach((i) => i.addEventListener('change', () => {
      const text = !from.value || !to.value ? '請填寫起訖日期。' : from.value >= to.value ? '結束日期須晚於開始日期。' : '';
      showError(text);
      if (!text) { LB[key] = [LB.parse(from.value), LB.parse(to.value)]; dash.draw(name); }
    }));
    const reset = () => { showError(''); LB[key] = null; dash.draw(name); };
    byId(resetId, HTMLElement).addEventListener('click', reset);
    range.addEventListener('change', () => { if (isOption(ranges, range.value)) { LB[rangeKey] = range.value; reset(); } });
  };
  lbZoomInputs('lb-from', 'lb-to', 'lb-range', 'lb-zreset', 'lb-date-error', 'zMain', 'chart', 'range');
  lbZoomInputs('lb-tfrom', 'lb-tto', 'lb-trange', 'lb-treset', 'lb-tdate-error', 'zTherm', 'thermo-chart', 'trange');
  document.querySelectorAll<HTMLSelectElement>('#lb-tix').forEach((s) => s.addEventListener('change', () => { if (isOption(markets, s.value)) { LB.tix = s.value; dash.draw('thermo-levels'); } }));
  document.querySelectorAll<HTMLSelectElement>('#lb-strip').forEach((s) => s.addEventListener('change', () => { if (isOption(families, s.value)) { LB.strip = s.value; dash.draw('chart'); } }));
  eventSelect.addEventListener('change', () => {
    pendingEventReveal = null;
    setEvents(selectedOption(eventSelect, backtestSignals, eventSelect.value, LB.evsig), null, LB.eventIndex);
    history.replaceState(null, '', sectionUrl('lb-events', { signal: LB.evsig, event: null, index: LB.eventIndex }));
  });
  eventIndexSelect.addEventListener('change', () => {
    setEvents(LB.evsig, LB.eventDate, selectedOption(eventIndexSelect, markets, eventIndexSelect.value, LB.eventIndex));
    history.replaceState(null, '', sectionUrl('lb-events', { signal: LB.evsig, event: LB.eventDate, index: LB.eventIndex }));
  });
  postSelect.addEventListener('change', () => {
    const date = postSelect.value !== 'hot_ptt' && isPostWindow(LB.pevent) ? LB.pevent : 'latest';
    setPosts(selectedOption(postSelect, postSignals, postSelect.value, LB.psig), date);
    history.replaceState(null, '', sectionUrl('lb-posts', { post: LB.psig, date }));
  });

  // 頂部導覽
  (() => {
    const nav = document.querySelector<HTMLElement>('.lb-nav-desktop');
    if (!nav) return;
    const upd = () => nav.classList.toggle('is-more', nav.scrollWidth - nav.clientWidth - nav.scrollLeft > 4);
    nav.addEventListener('scroll', upd, { passive: true }); window.addEventListener('resize', upd); upd();
    navMenu.addEventListener('click', (event) => {
      const link = event.target instanceof Element ? event.target.closest('a') : null;
      if (!link || nativeClick(event)) return;
      if (link.hash === '#lb-notes') notes.open = true;
      navMenu.open = false;
      const section = document.getElementById(link.hash.slice(1));
      const heading = section?.querySelector<HTMLElement>('h2, summary');
      if (heading) {
        heading.tabIndex = -1;
        heading.focus({ preventScroll: true });
      }
    });
    document.addEventListener('click', (event) => { if (!navMenu.contains(event.target instanceof Node ? event.target : null)) navMenu.open = false; });
    navMenu.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape' || !navMenu.open) return;
      navMenu.open = false;
      navMenu.querySelector<HTMLElement>('summary')?.focus();
    });
    document.querySelector<HTMLAnchorElement>('.lb-nav-desktop a[href="#lb-notes"]')?.addEventListener('click', (event) => {
      if (!nativeClick(event)) notes.open = true;
    });
  })();

  // 頂部導覽：標出目前所在的章節
  (() => {
    const links = [...document.querySelectorAll<HTMLAnchorElement>('.lb-nav a')];
    const ids = ['lb-today', 'lb-thermo', 'lb-chart-sec', 'lb-lamps', 'lb-levels-sec', 'lb-bottom', 'lb-top', 'lb-warn', 'lb-events', 'lb-posts', 'lb-notes'];
    const els = ids.map((i) => document.getElementById(i)).filter(present);
    if (!('IntersectionObserver' in window) || !els.length) return;
    const vis = new Set();
    const set = () => {
      let id = els.find((e) => vis.has(e.id))?.id;
      if (id && ['lb-bottom', 'lb-top', 'lb-warn'].includes(id)) id = 'lb-levels-sec';
      links.forEach((a) => {
        if (a.hash !== '#' + id) { a.removeAttribute('aria-current'); return; }
        a.setAttribute('aria-current', 'true');
        const nav = a.closest<HTMLElement>('.lb-nav-desktop');
        if (nav?.clientWidth) {
          const l = a.offsetLeft - nav.offsetLeft;
          if (l < nav.scrollLeft || l + a.offsetWidth > nav.scrollLeft + nav.clientWidth) nav.scrollLeft = l - 8;
        }
      });
    };
    const io = new IntersectionObserver((es) => { es.forEach((e) => (e.isIntersecting ? vis.add(e.target.id) : vis.delete(e.target.id))); set(); }, { rootMargin: '-120px 0px -55% 0px' });
    els.forEach((e) => io.observe(e));
  })();

  // 今天：溫度、分數、燈號
  const statusRow = (sig: StatusSignal) => { const s = dash.data('status'); return s.status === 'ok' ? s.data.find((r) => r.signal === sig) : null; };
  const sumRow = (sig: BacktestSignal, ix: Market) => { const s = dash.data('summary'); return s.status === 'ok' ? s.data.find((r) => r.signal === sig && r.index === ix) : null; };
  const lastDaily = () => {
    const daily = dash.data('daily');
    return dash.today?.daily ?? (daily.status === 'ok' ? daily.data.at(-1) ?? null : null);
  };
  dash.draw('sc-wscore', (el) => { const r = statusRow('wscore'); el.textContent = r ? String(r.value) : '—'; });
  dash.draw('warn-lamp', (el) => {
    const r = statusRow('wscore'), daily = lastDaily();
    const on = LB.FAM.warn.some(([sig]) => daily?.[`f_${sig}`] === 1);
    el.dataset.s = !r ? 'missing' : on ? 'on' : r.value > 0 ? 'recent' : 'off';
  });
  dash.draw('reference-backtest', (el) => {
    const signal = el.dataset.signal;
    const r = isOption(backtestSignals, signal) ? sumRow(signal, 'TAIEX') : null;
    if (!r) { el.textContent = '回測資料暫時無法顯示。'; return; }
    const count = r.n20 == null ? '' : '，20 日有效 ' + r.n20 + ' 次';
    const result = r.signal === 'combo4' ? '。加權 20 日平均報酬 ' + LB.pct(r.ret20) + '、超額 ' : '。加權 20 日超額 ';
    el.textContent = (r.signal === 'combo4' ? '7 個訊號中至少 4 個在近 5 個交易日曾亮' : '外資期貨淨空單極端') +
      '，共 ' + r.n + ' 次' + count + result + LB.pct(r.excess20) + '。';
  });

  const UNIT: Record<StatusSignal, (value: number) => string> = { foreign: LB.pct, foreign_buy: LB.pct, margin: LB.pct, margin_up: LB.pct, turnover: (v) => (v > 0 ? '+' : '') + v.toFixed(1) + '%',
    stretch: LB.pct, bigdrop: LB.pct, default: (v) => '萬分之 ' + v.toFixed(3), loss: (v) => v + ' 篇', creative: (v) => v + ' 篇', hot_ptt: (v) => v + ' 篇',
    pc_high: (v) => v.toFixed(2) + '%', pc_low: (v) => v.toFixed(2) + '%', fut_short: (v) => (v > 0 ? '+' : '') + LB.num(v) + ' 口', fut_long: (v) => (v > 0 ? '+' : '') + LB.num(v) + ' 口',
    vix_high: (v) => v.toFixed(2), vix_low: (v) => v.toFixed(2), score: (v) => String(v), gscore: (v) => String(v), wscore: (v) => String(v),
    fut_ratio_short: (v) => (v > 0 ? '+' : '') + v.toFixed(1) + '%', fut_chg_short: (v) => (v > 0 ? '+' : '') + LB.num(v) + ' 口',
    thermo: (v) => v.toFixed(1), dual: (v) => (v === 1 ? '成立' : '未成立') };
  const sourceDate = (r: StatusRow) => r.source_asof || r.asof;
  const displayDate = (date: string | null | undefined) => date ? LB.date(LB.parse(date)) : '—';
  const signalThreshold = (r: StatusRow, sig: StatusSignal) => r.rule === '=' ? '條件同時成立' : r.threshold == null ? '—' : r.rule + ' ' + UNIT[sig](r.threshold);
  const lampState = (sig: LampSignal, dl: DailyRow | null): LampState => {
    const r = statusRow(sig);
    if (!r || !dl || r.asof !== dl.date || r.threshold == null) return 'missing';
    if (dl[`f_${sig}`] === 1) return 'on';
    return r.lit5 === 1 ? 'recent' : 'off';
  };
  const STATE_TXT = { on: '本交易日亮燈', recent: '本交易日未亮，近 5 日曾亮', off: '未亮燈', missing: '本交易日待資料' };
  // 點燈看的白話說明（門檻都是跟過去 250 個交易日比，約一年）
  const EXPLAIN: Partial<Record<StatusSignal, string>> = {
    vix_high: '美國 VIX 是美股的「恐慌指數」，從 S&P 500 選擇權價格算出市場預期的波動。高到過去一年最高的 5%，代表美股很恐慌。',
    vix_low: '美國 VIX 是美股的「恐慌指數」。低到過去一年最低的 5%，代表美股很安逸、大家不怕跌。',
    pc_high: 'P/C＝台指選擇權「賣權」成交量 ÷「買權」成交量。賣權像跌價保險，比值高到過去一年最高的 5%，代表大家搶買保險、很恐慌。這裡用成交量比，跟常聽到的「未平倉量比」解讀方向相反。',
    pc_low: 'P/C＝台指選擇權「賣權」成交量 ÷「買權」成交量。比值低到過去一年最低的 5%，代表幾乎都在買看漲的買權、很少人避險，市場偏樂觀。這裡用成交量比，跟常聽到的「未平倉量比」解讀方向相反。',
    foreign: '外資最近 5 天合計賣超，佔同期成交金額的比例，賣得比過去一年 95% 的日子都兇。',
    foreign_buy: '外資最近 5 天合計買超，佔同期成交金額的比例，買得比過去一年 95% 的日子都多。',
    margin: '上市融資張數 5 天內大減，減幅是過去一年最大的 5%。常見於斷頭、追繳後被迫賣出。',
    margin_up: '融資金額 20 天內大增，增幅是過去一年最大的 5%，代表借錢買股的人變多。',
    default: '投資人違約交割（買了股票付不出錢）的金額佔成交金額的比例，高到過去一年最高的 5%。',
    loss: 'PTT 股票版有人發〔心得〕文說自己做多賠錢「畢業」，而且附對帳單或寫出金額；5 個交易日內 3 篇以上。由 AI 讀內文判斷。',
    creative: 'PTT 股票版〔創作〕文（打油詩、梗圖之類，大跌時常爆量）當天 5 篇以上，而且是前 60 個交易日平均的 4 倍以上。',
    fut_long: '外資在台指期貨的淨多單（多單減空單）口數，多到過去一年最多的 5%。',
    turnover: '最近 5 天平均成交金額比前 120 天平均放大，放大幅度是過去一年最大的 5%。',
    hot_ptt: 'PTT 股票版標題有財富自由、歐印、噴、翻倍、創新高、賺爛、上車這類字的文章，5 天內 5 篇以上，而且是平常的 3 倍以上。',
    stretch: '加權指數比 120 日均線高出的幅度（乖離），大到過去一年最大的 5%，代表短期漲太快。',
    fut_short: '外資在台指期貨的淨空單口數，多到過去一年最多的 5%。只當警示。',
    fut_ratio_short: '外資淨空單佔全市場台指期未平倉的比例，高到過去一年最高的 5%。只當警示。',
    fut_chg_short: '外資 5 天內增加的台指期空單，多到過去一年最多的 5%。只當警示。',
  };
  const lampTip = (() => {
    let tip: HTMLDivElement | undefined;
    let owner: HTMLButtonElement | undefined;
    let y0 = 0;
    const close = (refocus = false) => {
      if (!owner || !tip) return;
      tip.hidden = true; owner.setAttribute('aria-expanded', 'false'); owner.removeAttribute('aria-describedby');
      if (refocus) owner.focus();
      owner = undefined;
    };
    const open = (btn: HTMLButtonElement, parts: HTMLElement[]) => {
      if (owner === btn) { close(); return; }
      close();
      if (!tip) { tip = document.createElement('div'); tip.id = 'lb-ltip'; tip.className = 'lb-tip lb-tip--fixed lb-ltip'; tip.setAttribute('role', 'tooltip'); tip.hidden = true; document.body.append(tip); }
      owner = btn; y0 = window.scrollY;
      tip.replaceChildren(...parts); tip.hidden = false;
      btn.setAttribute('aria-expanded', 'true'); btn.setAttribute('aria-describedby', 'lb-ltip');
      const c = btn.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
      const x = Math.max(8, Math.min(c.left + c.width / 2 - w / 2, window.innerWidth - w - 8));
      let y = c.bottom + 6; if (y + h > window.innerHeight - 8) y = Math.max(8, c.top - h - 6);
      tip.style.left = x + 'px'; tip.style.top = y + 'px';
    };
    document.addEventListener('click', (e) => { if (e.target instanceof Node && owner && tip && !owner.contains(e.target) && !tip.contains(e.target)) close(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(true); });
    window.addEventListener('scroll', () => { if (owner && Math.abs(window.scrollY - y0) > 40) close(); }, { passive: true });
    window.addEventListener('resize', () => close());
    return { open };
  })();

  dash.draw('fam-lamps', (el) => {
    const fam = el.dataset.fam, dl = lastDaily(); el.replaceChildren();
    if (dash.data('status').status !== 'ok') return;
    if (!isOption(families, fam)) return;
    LB.FAM[fam].forEach(([sig, short]) => {
      const r = statusRow(sig), s = lampState(sig, dl);
      const li = document.createElement('li'); li.dataset.s = s;
      const i = document.createElement('i'); i.className = 'lamp lamp--' + fam; i.dataset.s = s; i.setAttribute('aria-hidden', 'true');
      const t = document.createElement('span'); t.textContent = short;
      const btn = document.createElement('button'); btn.type = 'button'; btn.className = 'lb-lampbtn'; btn.setAttribute('aria-expanded', 'false');
      btn.append(i, t); li.append(btn);
      const full = r ? r.name : short;
      const val = r && r.value != null ? '最新值 ' + UNIT[sig](r.value) + '（' + displayDate(sourceDate(r)) + '），門檻 ' + signalThreshold(r, sig) : '';
      const state = STATE_TXT[s] + (s === 'missing' && r?.lit5 === 1 ? '，近 5 日曾亮' : '');
      btn.setAttribute('aria-label', full + '，' + state + '。點一下看說明');
      btn.addEventListener('click', () => {
        const h = document.createElement('b'); h.textContent = full;
        const st = document.createElement('div'); st.className = 'lb-ltip-s'; st.textContent = state + (val ? '・' + val : '');
        const p = document.createElement('p'); p.textContent = EXPLAIN[sig] || '';
        lampTip.open(btn, [h, st, p]);
      });
      el.append(li);
    });
  });
  dash.draw('fam-chip', (el) => {
    const r = statusRow('wscore');
    if (!r) { el.textContent = '—'; return; }
    el.textContent = r.value > 0 ? '近 5 日有警示' : '近 5 日未見警示';
    if (r.value > 0) el.dataset.tone = 'warn'; else delete el.dataset.tone;
  });

  dash.draw('stamp', (el) => {
    const r = statusRow('thermo'); if (!r) { el.textContent = '—'; return; }
    el.textContent = '收盤資料日 ' + displayDate(r.asof) + (r.ptt_asof ? '・PTT 文章至 ' + r.ptt_asof.slice(5).replace('-', '/') : '');
    if (r.ptt_lag_h != null && r.ptt_lag_h > 3) {
      const note = document.createElement('small'); note.className = 'lb-stamp-note';
      note.textContent = '最新文章距資料產生逾 ' + Math.floor(r.ptt_lag_h) + ' 小時';
      el.append(note);
    }
  });
  dash.draw('reading-status', (el) => {
    const status = dash.data('status').status;
    el.hidden = status === 'ok' && !!statusRow('thermo');
    el.classList.toggle('lb-err', status !== 'loading' && !el.hidden);
    if (el.hidden) { el.replaceChildren(); return; }
    el.textContent = status === 'loading' ? '正在載入恐慌溫度…' : '恐慌溫度暫時無法顯示。';
    const reload = dash.reload;
    if (status === 'loading' || !reload) return;
    const retry = document.createElement('button');
    retry.type = 'button'; retry.className = 'lb-btn'; retry.textContent = '重試載入';
    retry.addEventListener('click', () => reload('status'));
    el.append(' ', retry);
  });

  // 分享今天的圖卡：畫法在 card.js（連結預覽圖用的是同一份）
  (() => {
    const btn = document.querySelector<HTMLButtonElement>('#lb-share-btn'), panel = document.getElementById('lb-share-panel');
    if (!btn || !panel) return;
    const loadCard = dash.loadCard;
    if (!loadCard) { const share = btn.closest<HTMLElement>('.lb-share'); if (share) share.hidden = true; return; }
    const prev = byId('lb-share-prev', HTMLElement), go = byId('lb-share-go', HTMLButtonElement);
    const dl = byId('lb-share-dl', HTMLElement), cp = byId('lb-share-copy', HTMLElement), msg = byId('lb-share-msg', HTMLElement);
    const pageUrl = () => location.origin + location.pathname;
    let card: Awaited<ReturnType<typeof make>> | null = null;
    const say = (t: string) => { msg.textContent = t; };
    const make = async () => {
      const st = dash.data('status'), sm = dash.data('summary');
      if (st.status !== 'ok') throw new Error(st.status === 'loading' ? '資料還在載入，請稍候再試' : '資料載入失敗');
      const renderer = await loadCard();
      const m = renderer.model(st.data, lastDaily(), sm.status === 'ok' ? sm.data : dash.today?.summary || []);
      if (!m) throw new Error('找不到溫度資料');
      await renderer.fontsReady(m);
      const c = document.createElement('canvas'); renderer.draw(c, m, 2);
      const blob = await new Promise<Blob>((res, rej) => c.toBlob((b) => (b ? res(b) : rej(new Error('瀏覽器無法產生圖片'))), 'image/png'));
      const name = 'ptt-indicator-' + m.asof.replaceAll('/', '') + '.png';
      return { description: renderer.text(m), name, file: new File([blob], name, { type: 'image/png' }), url: URL.createObjectURL(blob) };
    };
    btn.addEventListener('click', async () => {
      if (!panel.hidden) { panel.hidden = true; btn.setAttribute('aria-expanded', 'false'); return; }
      btn.disabled = true; say('');
      try {
        if (card) URL.revokeObjectURL(card.url);
        card = await make();
        const img = new Image(1200, 630); img.src = card.url; img.alt = '今日圖卡：' + card.description; prev.replaceChildren(img);
        go.hidden = !(navigator.canShare && navigator.canShare({ files: [card.file] }));
        panel.hidden = false; btn.setAttribute('aria-expanded', 'true');
      } catch (e) { say('產生圖卡失敗：' + (e instanceof Error ? e.message : String(e))); panel.hidden = false; btn.setAttribute('aria-expanded', 'true'); }
      finally { btn.disabled = false; }
    });
    go.addEventListener('click', async () => {
      if (!card) return;
      try { await navigator.share({ files: [card.file], title: '台股落底訊號回測', text: card.description + ' ' + pageUrl() }); say('已開啟分享'); }
      catch (e) { if (!(e instanceof DOMException && e.name === 'AbortError')) say('分享失敗，可以改用「下載 PNG」'); }
    });
    dl.addEventListener('click', () => {
      if (!card) return;
      const a = document.createElement('a'); a.href = card.url; a.download = card.name; document.body.append(a); a.click(); a.remove();
      say('已下載 ' + card.name);
    });
    cp.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(pageUrl()); say('已複製連結'); } catch (e) { say('無法複製，請手動複製網址列'); }
    });
  })();

  // 燈號明細：訊號 × 最近 20 個交易日
  type MatrixSignal = {
    signal: LampSignal | 'thermo' | 'dual';
    event: BacktestSignal;
    flag: (row: DailyRow) => number;
    label?: string;
  };
  let matrixCell: HTMLTableCellElement | undefined;
  let matrixFocus: ((event: Event) => void) | undefined;
  dash.draw('matrix', (element) => {
    const el = requireElement(element, HTMLTableElement);
    const d = dash.data('daily'), st = dash.data('status');
    el.replaceChildren();
    if (d.status !== 'ok' || st.status !== 'ok') {
      if (d.status === 'error' || st.status === 'error') { const c = el.createTBody().insertRow().insertCell(); c.className = 'lb-err'; c.textContent = '燈號資料載入失敗。'; }
      return;
    }
    const N = 20, days = d.data.slice(-N), last = days.length - 1;
    const head = el.createTHead(), r1 = head.insertRow(), r2 = head.insertRow();
    const KEEP = 8, old = (i: number) => (i < days.length - KEEP ? ' lb-old' : '');  // 手機只顯示最近 KEEP 天
    const h0 = document.createElement('th'); h0.className = 'lb-name'; h0.rowSpan = 2; h0.textContent = '訊號'; h0.style.verticalAlign = 'bottom'; h0.style.paddingBottom = '4px'; r1.append(h0);
    let run: { m: string; start: number; th: HTMLTableCellElement; cont: boolean } | null = null;
    days.forEach((r, i) => {
      const m = r.date.slice(5, 7);
      if (!run || run.m !== m || (i === days.length - KEEP && run.start < days.length - KEEP)) {
        run = { m, start: i, th: document.createElement('th'), cont: !!run && run.m === m }; run.th.className = 'lb-d' + old(i); run.th.style.textAlign = 'left';
        if (run.cont) { const sp = document.createElement('span'); sp.className = 'lb-sm-only'; sp.textContent = (+m) + ' 月'; run.th.append(sp); } else run.th.textContent = (+m) + ' 月';
        run.th.colSpan = 1; r1.append(run.th);
      } else run.th.colSpan += 1;
      const th = document.createElement('th'); th.className = 'lb-d' + old(i) + (i === last ? ' is-today' : ''); th.textContent = String(+r.date.slice(8)); th.scope = 'col'; r2.append(th);
    });
    r1.querySelectorAll<HTMLTableCellElement>('th.lb-d').forEach((th) => { if (th.colSpan < 3) th.replaceChildren(); });   // 太窄的月份不標，免得擠成兩行
    [['最新值', ''], ['亮燈門檻', ' lb-hide-sm'], ['上次亮燈', ' lb-hide-sm']].forEach(([t, c]) => { const th = document.createElement('th'); th.className = 'lb-v' + c; th.rowSpan = 2; th.textContent = t; th.style.verticalAlign = 'bottom'; th.style.paddingBottom = '4px'; r1.append(th); });
    const body = el.createTBody(), cols = days.length + 4;
    const signalRow = (signal: LampSignal): MatrixSignal => ({ signal, event: signal, flag: (row) => row[`f_${signal}`] });
    const basicSignals = (family: Family) => LB.FAM[family].map(([signal]) => signalRow(signal));
    const groups: { name: string; family: Family; signals: MatrixSignal[]; score?: 'wscore'; total?: number }[] = [
      { name: '鄉民恐慌', family: 'bottom', signals: [
        { signal: 'thermo', label: '恐慌溫度 ≥95', flag: (r) => Number(r.fear != null && r.fear >= 95), event: 'thermo95' },
        { signal: 'dual', label: '雙重確認', flag: (r) => r.f_dual, event: 'dual' },
      ] },
      { name: '落底訊號（參考）', family: 'bottom', signals: [...basicSignals('bottom'), signalRow('bigdrop')] },
      { name: '過熱訊號（參考）', family: 'top', signals: basicSignals('top') },
      { name: '偏空警示', family: 'warn', signals: basicSignals('warn'), score: 'wscore', total: 3 },
    ];
    groups.forEach(({ name: gname, family: fam, signals, score, total }) => {
      const g = body.insertRow(); g.className = 'lb-grp';
      const gh = document.createElement('th'); gh.colSpan = cols; gh.scope = 'rowgroup';
      const gl = document.createElement('i'); gl.className = 'lamp lamp--' + fam; gl.dataset.s = 'on'; gl.setAttribute('aria-hidden', 'true');
      const sc = score ? statusRow(score) : null;
      const gs = document.createElement('span'); gs.className = 'lb-grp-l'; gs.append(gl, gname + (sc ? '・近 5 日 ' + sc.value + ' / ' + total + ' 項' : '')); gh.append(gs);
      g.append(gh);
      signals.forEach(({ signal: sig, label, flag, event }) => {
        const r = statusRow(sig); if (!r) return;
        const recent = new Map((r.recent || []).map((row) => [row[0], row]));
        const tr = body.insertRow();
        tr.dataset.sig = sig; tr.dataset.fam = fam; tr.dataset.label = label || r.name;
        const nh = document.createElement('th'); nh.className = 'lb-name'; nh.scope = 'row';
        const b = document.createElement('button'); b.type = 'button';
        const fl = document.createElement('span'); fl.className = 'lb-full'; fl.textContent = label || r.name;
        const sl = document.createElement('span'); sl.className = 'lb-short'; sl.textContent = label || (sig === 'thermo' ? r.name : LB.SHORT[sig]);
        b.append(fl, sl);
        b.title = (EXPLAIN[sig] ? EXPLAIN[sig] + '\n' : '') + '點一下看「' + (label || r.name) + '」歷史上每一次亮燈'; b.addEventListener('click', () => goEvents(event));
        const sm = document.createElement('small'); sm.textContent = '門檻 ' + signalThreshold(r, sig);
        nh.append(b, sm); tr.append(nh);
        days.forEach((dr, i) => {
          const td = tr.insertCell(); td.className = 'lb-d' + old(i) + (i === last ? ' is-today' : '');
          const rec = recent.get(dr.date);
          const missing = (rec && (rec[1] == null || rec[2] == null)) || (sig === 'thermo' && dr.fear == null) || (r.asof && dr.date > r.asof);
          const on = flag(dr) === 1;
          const state = missing ? 'missing' : on ? 'on' : 'off';
          const lamp = document.createElement('i'); lamp.className = 'lamp lamp--' + fam; lamp.dataset.s = state;
          if (state === 'off') { lamp.style.setProperty('--ls', '6px'); lamp.style.borderWidth = '0'; lamp.style.background = 'var(--rule)'; }
          td.dataset.i = String(i); td.dataset.s = state; td.tabIndex = i === last ? 0 : -1;
          td.setAttribute('aria-label', LB.dateW(LB.parse(dr.date)) + ' ' + (label || r.name) + ' ' + (missing ? '待資料' : on ? '亮燈' : '未亮'));
          td.append(lamp);
        });
        const v = tr.insertCell(); v.className = 'lb-v'; v.textContent = r.value == null ? '—' : UNIT[sig](r.value);
        if (r.value != null && sourceDate(r) && (r.asof !== days[last].date || sourceDate(r) !== r.asof)) {
          const date = document.createElement('small'); date.className = 'lb-cell-note';
          const fullDate = displayDate(sourceDate(r)); date.textContent = fullDate.slice(0, 4) === days[last].date.slice(0, 4) ? fullDate.slice(5) : fullDate;
          v.append(date);
        }
        const t = tr.insertCell(); t.className = 'lb-v lb-hide-sm'; t.textContent = signalThreshold(r, sig);
        const l = tr.insertCell(); l.className = 'lb-v lb-hide-sm'; l.textContent = r.last_lit ? LB.date(LB.parse(r.last_lit)) : '—';
      });
    });
    // 提示：指向、聚焦或點一格，顯示那天的燈號與這個訊號目前的數值
    const existingTip = document.getElementById('lb-mtip');
    const tip = existingTip ?? document.createElement('div');
    const place = () => {
      const td = matrixCell;
      if (!td?.isConnected) { tip.hidden = true; return; }
      const c = td.getBoundingClientRect(); if (c.bottom < 0 || c.top > window.innerHeight) { tip.hidden = true; return; }
      const w = tip.offsetWidth, h = tip.offsetHeight;
      let x = c.left + c.width / 2 - w / 2; x = Math.max(8, Math.min(x, window.innerWidth - w - 8));
      let y = c.top - h - 8; if (y < 72) y = c.bottom + 8;
      tip.style.left = x + 'px'; tip.style.top = y + 'px';
    };
    if (!existingTip) {
      tip.id = 'lb-mtip'; tip.className = 'lb-tip lb-tip--fixed'; tip.hidden = true; tip.setAttribute('role', 'status'); document.body.append(tip);
      const re = () => { if (!tip.hidden) place(); };
      window.addEventListener('scroll', re, { passive: true });
      el.closest('.lb-tablewrap')?.addEventListener('scroll', re, { passive: true });
      el.addEventListener('focusin', (event) => matrixFocus?.(event));
      el.addEventListener('focusout', () => { tip.hidden = true; });
    }
    const show = (td: HTMLTableCellElement) => {
      const tr = td.parentElement;
      const sig = tr?.dataset.sig;
      const i = Number(td.dataset.i), dr = days[i];
      if (!tr || !dr || !isOption(statusSignals, sig)) return;
      const r = statusRow(sig); if (!r) return;
      const state = td.dataset.s, isToday = i === last;
      tip.replaceChildren();
      const b = document.createElement('b'); b.textContent = LB.dateW(LB.parse(dr.date)) + (isToday ? '・最新一天' : ''); tip.append(b);
      const lines = [tr.dataset.label + '・' + (state === 'missing' ? '當日待資料' : state === 'on' ? '亮燈' : '未亮')];
      if (sig === 'thermo') lines.push('那天溫度 ' + (dr.fear == null ? '—' : dr.fear.toFixed(1)));
      if (sig === 'dual') lines.push('那天畢業文 5 日 ' + dr.l5 + ' 篇・創作文熱度 ' + dr.cheat);
      const rec = Array.isArray(r.recent) ? r.recent.find((x) => x[0] === dr.date) : null;
      if (rec) lines.push('那天數值 ' + (rec[1] == null ? '—' : UNIT[sig](rec[1])) + (rec[2] == null ? '' : '（門檻 ' + r.rule + ' ' + UNIT[sig](rec[2]) + '）'));
      lines.push('最新值 ' + (r.value == null ? '—' : UNIT[sig](r.value) + '（' + displayDate(sourceDate(r)) + '）') + '・門檻 ' + signalThreshold(r, sig));
      lines.push('上次亮燈 ' + (r.last_lit ? LB.date(LB.parse(r.last_lit)) : '—'));
      lines.forEach((t) => { const dv = document.createElement('div'); dv.textContent = t; tip.append(dv); });
      tip.hidden = false; matrixCell = td; place();
    };
    const cell = (e: Event) => e.target instanceof Element ? e.target.closest<HTMLTableCellElement>('td.lb-d') : null;
    el.onpointerover = (e) => { const td = cell(e); if (td) show(td); };
    el.onpointerleave = () => { if (!el.contains(document.activeElement)) tip.hidden = true; };
    el.onclick = (e) => { const td = cell(e); if (td) show(td); };
    matrixFocus = (event) => { const td = cell(event); if (td) show(td); };
    el.onkeydown = (e) => {
      const td = cell(e); if (!td) return;
      if (e.key === 'Escape') { tip.hidden = true; return; }
      const rowCells = (row: Element) => [...row.querySelectorAll<HTMLTableCellElement>('td.lb-d')].filter((cell) => cell.offsetParent !== null);
      const tr = td.parentElement;
      if (!tr) return;
      const cells = rowCells(tr), k = cells.indexOf(td);
      let next: HTMLTableCellElement | null | undefined;
      if (e.key === 'ArrowLeft') next = cells[k - 1];
      else if (e.key === 'ArrowRight') next = cells[k + 1];
      else if (e.key === 'Home') next = cells[0];
      else if (e.key === 'End') next = cells[cells.length - 1];
      else if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        let o: Element | null = tr; do { o = e.key === 'ArrowUp' ? o.previousElementSibling : o.nextElementSibling; } while (o && o.classList.contains('lb-grp'));
        if (o) next = o.querySelector<HTMLTableCellElement>('td.lb-d[data-i="' + td.dataset.i + '"]');
      }
      if (!next) return;
      e.preventDefault(); td.tabIndex = -1; next.tabIndex = 0; next.focus();
    };
  });

  const articleLink = (article: { title: string; url: string }) => {
    if (!/^https:\/\/www\.ptt\.cc\/bbs\/Stock\//.test(article.url)) return null;
    const a = document.createElement('a');
    a.href = article.url; a.target = '_blank'; a.rel = 'noopener'; a.textContent = article.title;
    return a;
  };
  const eventEvidence = (event: EventRow) => {
    const links = (event.loss_sources || []).slice(0, 2).map(articleLink).filter(present);
    if (!links.length) return null;
    const group = document.createElement('span'); group.className = 'lb-evidence';
    group.append('畢業文原文　');
    links.forEach((link, i) => {
      if (i) group.append('、');
      group.append(link);
    });
    return group;
  };

  const chartEvents = (chart: HTMLElement, marks: readonly EventRow[], index: Market) => {
    const disclosure = chart.nextElementSibling;
    if (!(disclosure instanceof HTMLElement)) return;
    const body = disclosure.querySelector('.lb-chart-event');
    if (!body) return;
    const selected = body.querySelector('select')?.value;
    disclosure.hidden = false;
    body.replaceChildren();
    if (!marks.length) { body.textContent = '這段期間沒有事件標記。'; return; }

    const events = [...marks].sort((a, b) => b.date.localeCompare(a.date));
    const key = (event: EventRow) => event.date + ',' + event.signal;
    const name = (event: EventRow) => event.signal === 'note' ? event.note : LB.SHORT[event.signal] || event.name;
    const select = document.createElement('select');
    select.setAttribute('aria-label', '選擇圖上的事件');
    events.forEach((event) => select.add(new Option(displayDate(event.date) + ' ' + name(event), key(event))));
    if (selected && events.some((event) => key(event) === selected)) select.value = selected;
    const info = document.createElement('div'); info.className = 'lb-chart-event'; info.setAttribute('aria-live', 'polite');
    const render = () => {
      const event = events[select.selectedIndex];
      const evidence = eventEvidence(event);
      const title = document.createElement('b'); title.textContent = name(event);
      const value = event.signal === 'note' ? null : event[index === 'TAIEX' ? 'tw_ret20' : 'tp_ret20'];
      const summary = [
        event.signal !== 'note' ? event.value : '',
        event.signal !== 'note' ? (index === 'TAIEX' ? '加權' : '櫃買') + '後 20 日 ' + (event.pending20 ? '尚未滿 20 日' : LB.pct(value)) : '',
        ...LB.evLines(event, !evidence).filter((line) => event.signal !== 'note' || line !== '事件：' + event.note),
      ].filter(Boolean);
      info.replaceChildren(title, ...summary.map((line) => {
        const p = document.createElement('p'); p.className = 'lb-cap'; p.textContent = line; return p;
      }));
      if (evidence) info.append(evidence);
      if (event.signal === 'note') return;
      const link = document.createElement('a'); link.className = 'lb-row-link'; link.textContent = '看這筆事件明細';
      link.href = sectionUrl('lb-events', { signal: event.signal, event: event.date, index }).href;
      link.addEventListener('click', (evt) => {
        if (nativeClick(evt)) return;
        evt.preventDefault(); goEvents(event.signal, event.date, index);
      });
      info.append(link);
    };
    select.addEventListener('change', render);
    body.append(select, info);
    render();
  };

  // 主圖
  dash.draw('chart', (el) => {
    const d3 = charts();
    const d = dash.data('daily'), e = dash.data('events');
    const disclosure = el.nextElementSibling;
    if (disclosure instanceof HTMLElement) disclosure.hidden = true;
    if (d.status === 'loading' || e.status === 'loading') { el.replaceChildren(); el.textContent = '—'; return; }
    LB.done(el); el.replaceChildren();
    if (d.status !== 'ok' || e.status !== 'ok') { const p = document.createElement('p'); p.className = 'lb-err'; p.textContent = '指數資料載入失敗。'; el.append(p); return; }
    const key = LB.ix === 'TAIEX' ? 'taiex' : 'tpex', ckey = LB.ix === 'TAIEX' ? 'tw_close' : 'tp_close';
    let rows = d.data.flatMap((r) => {
      const price = r[key];
      return price == null ? [] : [{ ...r, t: LB.parse(r.date), price }];
    });
    const last = rows.at(-1)?.t;
    const back = last ? { all: null, '3y': d3.utcYear.offset(last, -3), '1y': d3.utcYear.offset(last, -1), '6m': d3.utcMonth.offset(last, -6) }[LB.range] : null;
    if (back && !LB.zMain) rows = rows.filter((r) => r.t >= back);
    const zoom = LB.zMain;
    if (zoom) rows = rows.filter((r) => r.t >= zoom[0] && r.t <= zoom[1]);
    if (rows.length < 2) { const p = document.createElement('p'); p.className = 'lb-err'; p.textContent = '這段期間沒有資料，請按「重設範圍」。'; el.append(p); return; }
    LB.syncDates("#lb-from", "#lb-to", rows);
    const spanD = (+rows[rows.length - 1].t - +rows[0].t) / 864e5;
    const strip = LB.STRIP[LB.strip], stripC = LB.FAMC[LB.strip];
    const W = Math.max(280, el.clientWidth), narrow = W < 560;
    const priceH = narrow ? 220 : 300, rowH = 14, stripTop = priceH + 16;
    const labels = strip.map((s) => s[1]).concat(['恐慌溫度', '雙重確認', '偏空警示']);
    const H = stripTop + labels.length * rowH + 24;
    const svg = d3.select(el).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img')
      .attr('aria-label', (LB.ix === 'TAIEX' ? '加權指數' : '櫃買指數') + '走勢，標出恐慌溫度 90、95 以上與雙重確認的日子，以及各訊號亮燈日');
    const lab = svg.append('g');
    labels.forEach((t, i) => lab.append('text').attr('y', stripTop + i * rowH + rowH - 3).style('font-size', '11px').text(t));
    const [lo, hi] = d3.extent(rows, (r) => r.price);
    if (lo == null || hi == null) return;
    const y = d3.scaleLog().domain([lo * 0.97, hi * 1.03]).range([priceH - 4, 8]);
    let ticks = y.ticks(6).filter((v) => v >= lo * 0.97 && v <= hi * 1.03);
    while (ticks.length > 6) ticks = ticks.filter((v, i) => i % 2 === 0);
    const probe = svg.append('g').selectAll<SVGTextElement, unknown>('text').data(ticks).join('text').text((v) => LB.num(v));
    const labW = Math.max(...lab.selectAll<SVGTextElement, unknown>('text').nodes().concat(probe.nodes()).map((n) => n.getComputedTextLength()));
    probe.remove();
    const m = { l: Math.ceil(labW) + 10, r: 8 };
    lab.selectAll<SVGTextElement, unknown>('text').attr('x', m.l - 6).attr('text-anchor', 'end');
    const x = d3.scaleUtc().domain([rows[0].t, rows[rows.length - 1].t]).range([m.l, W - m.r]);
    svg.append('g').attr('class', 'lb-grid').selectAll('line').data(ticks).join('line').attr('x1', m.l).attr('x2', W - m.r).attr('y1', y).attr('y2', y);
    svg.append('g').selectAll<SVGTextElement, unknown>('text').data(ticks).join('text').attr('x', m.l - 6).attr('y', (v) => y(v) + 4).attr('text-anchor', 'end').text((v) => LB.num(v));
    svg.append('g').attr('class', 'lb-axis').attr('transform', `translate(0,${H - 20})`)
      .call(d3.axisBottom<Date>(x).ticks(narrow ? 4 : 8).tickSizeOuter(0).tickFormat(LB.axisFormat(spanD, narrow)));
    svg.append('path').datum(rows).attr('fill', 'none').attr('stroke-width', 1.4).style('stroke', 'var(--ink-2)')
      .attr('d', d3.line<typeof rows[number]>().x((r) => x(r.t)).y((r) => y(r.price)));
    const dates = new Set(rows.map((r) => r.date));
    const ORD = { thermo90: 0, thermo95: 1, dual: 2 };   // 後畫的蓋在上面：雙重確認最上層
    const ev = e.data.flatMap((r) => {
      if (r.signal === 'note') return [];
      const signal = r.signal, price = r[ckey];
      return isOption(['thermo90', 'thermo95', 'dual'], signal) && dates.has(r.date) && price != null
        ? [{ ...r, signal, price }] : [];
    }).sort((a, b) => ORD[a.signal] - ORD[b.signal]);
    const mk = svg.append('g');
    ev.forEach((r) => {
      const cx = x(LB.parse(r.date)), cy = y(r.price);
      if (r.signal === 'dual') mk.append('circle').attr('cx', cx).attr('cy', cy).attr('r', 9.5).style('fill', 'none').style('stroke', 'var(--lamp-blue)').attr('stroke-width', 1.5);
      LB.lampSvg(mk, cx, cy, r.signal === 'thermo90' ? 5.5 : 6, 'var(--lamp-blue)', r.signal === 'thermo90' ? 'recent' : 'on');
    });
    // 事件文字：人工註記 > 標題主題；同一個事件 20 個交易日內只標一次，文字互相重疊就略過（指向標記仍看得到）
    const idxOf = new Map(rows.map((r, i) => [r.date, i]));
    type Label = { r: EventRow; price: number; text: string; rank: number };
    const bev: Label[] = ev.filter((r) => r.side !== 'top').map((r) => ({
      r, price: r.price, text: LB.evLabel(r), rank: (r.note ? 0 : 1) * 3 + (2 - ORD[r.signal]),
    }));
    e.data.forEach((r) => {
      const price = r[ckey];
      if (r.signal === 'note' && idxOf.has(r.date) && price != null && !ev.some((q) => q.note === r.note)) {
        bev.push({ r, price, text: r.note + '（溫度未達 90）', rank: 2.5 });
      }
    });
    const labelsByRank = bev.filter((o) => o.text).sort((a, b) => a.rank - b.rank || (a.r.date < b.r.date ? -1 : 1));
    type Box = [left: number, top: number, right: number, bottom: number];
    const placed: (Label & { i: number; cx: number; ty: number; box: Box })[] = [];
    const cw = (t: string) => [...t].reduce((n, c) => n + (c.charCodeAt(0) > 255 ? 10.5 : 6), 0);
    const hit = (p: Box, q: Box) => p[0] < q[2] && q[0] < p[2] && p[1] < q[3] && q[1] < p[3];
    const dots = ev.map((r): Box => { const dx = x(LB.parse(r.date)), dy = y(r.price); return [dx - 7, dy - 7, dx + 7, dy + 7]; });
    const bisL = d3.bisector((r: typeof rows[number]) => r.t).left;
    const onLine = (q: Box) => { for (let k = Math.max(0, bisL(rows, x.invert(q[0])) - 1); k < rows.length && x(rows[k].t) <= q[2] + 1; k++) { const v = y(rows[k].price); if (v >= q[1] - 1 && v <= q[3] + 1) return true; } return false; };
    labelsByRank.forEach((o) => {
      const i = idxOf.get(o.r.date);
      if (i == null) return;
      const px = x(LB.parse(o.r.date)), py = y(o.price), w = cw(o.text);
      if (placed.some((q) => (q.text === o.text || (o.r.note && q.r.note === o.r.note)) && Math.abs(q.i - i) <= 20)) return;
      const cx = Math.min(Math.max(px, m.l + w / 2), W - m.r - w / 2);
      for (const strict of [true, false]) {
        for (const dy of [19, 31, 43, -12, -24, -36]) {
          const ty = py + dy, box: Box = [cx - w / 2 - 3, ty - 10, cx + w / 2 + 3, ty + 2];
          if (box[1] < 0 || ty > priceH - 2) continue;
          if (placed.some((q) => hit(box, q.box)) || dots.some((q) => hit(box, q)) || (strict && onLine(box))) continue;
          placed.push({ ...o, i, cx, ty, box }); return;
        }
      }
    });
    svg.append('g').selectAll('circle').data(placed.filter((o) => o.r.signal === 'note')).join('circle').attr('cx', (o) => x(LB.parse(o.r.date))).attr('cy', (o) => y(o.price))
      .attr('r', 3.5).style('fill', 'var(--ink-3)');
    svg.append('g').selectAll<SVGTextElement, unknown>('text').data(placed).join('text').attr('x', (o) => o.cx).attr('y', (o) => o.ty).attr('text-anchor', 'middle')
      .style('font-size', '11px').style('paint-order', 'stroke').style('stroke', 'var(--color-bg)').style('stroke-width', '3px').style('stroke-linejoin', 'round')
      .style('fill', (o) => (o.rank < 3 ? 'var(--ink)' : 'var(--ink-2)')).style('font-weight', (o) => (o.rank < 3 ? 500 : 400)).text((o) => o.text);
    chartEvents(el, [...ev, ...placed.filter((o) => o.r.signal === 'note').map((o) => o.r)], LB.ix);
    const step = Math.max(1.5, (W - m.l - m.r) / rows.length);
    strip.forEach(([k], i) => {
      svg.append('rect').attr('x', m.l).attr('width', W - m.l - m.r).attr('y', stripTop + i * rowH + 3).attr('height', rowH - 6).style('fill', 'var(--panel-2)');
      svg.append('g').selectAll('rect').data(rows.filter((r) => r[`f_${k}`] === 1)).join('rect')
        .attr('x', (r) => x(r.t) - step / 2).attr('width', step).attr('y', stripTop + i * rowH + 2).attr('height', rowH - 4).style('fill', stripC);
    });
    const extra: [field: 'fear' | 'f_dual' | 'wscore', color: string, lit: (value: number) => boolean, opacity: (value: number) => number][] = [['fear', 'var(--lamp-blue)', (v) => v >= 80, (v) => (v >= 95 ? 1 : v >= 90 ? 0.75 : v >= 85 ? 0.45 : 0.22)],
     ['f_dual', 'var(--lamp-blue)', (v) => v === 1, () => 1],
     ['wscore', 'var(--lamp-amber)', (v) => v > 0, (v) => 0.4 + 0.2 * v]];
    extra.forEach(([f, c, lit, op], j) => {
      const sy = stripTop + (strip.length + j) * rowH + 2;
      svg.append('rect').attr('x', m.l).attr('width', W - m.l - m.r).attr('y', sy + 1).attr('height', rowH - 6).style('fill', 'var(--panel-2)');
      svg.append('g').selectAll('rect').data(rows.flatMap((r) => { const value = r[f]; return value != null && lit(value) ? [{ t: r.t, value }] : []; })).join('rect')
        .attr('x', (r) => x(r.t) - step / 2).attr('width', step).attr('y', sy).attr('height', rowH - 4)
        .style('fill', c).attr('opacity', (r) => op(r.value));
    });
    const tip = document.createElement('div'); tip.className = 'lb-tip'; tip.hidden = true; el.append(tip);
    const rule = svg.append('line').attr('y1', 4).attr('y2', H - 20).style('stroke', 'var(--cds-chart-reference)').attr('opacity', 0);
    const bis = d3.bisector((r: typeof rows[number]) => r.t).center;
    const all = [...LB.STRIP.bottom, ...LB.STRIP.top, ...LB.STRIP.warn];
    const selR = svg.append('rect').attr('y', 0).attr('height', H - 20).attr('width', 0).style('fill', 'var(--cds-chart-muted)').attr('opacity', 0.3);
    let dragX: number | null = null;
    svg.append('rect').attr('x', m.l).attr('y', 0).attr('width', W - m.l - m.r).attr('height', H - 20).attr('fill', 'transparent').style('cursor', 'crosshair')
      .on('pointerdown', function (evt: PointerEvent) {
        if (evt.pointerType !== 'mouse' || evt.button !== 0) return;
        dragX = d3.pointer(evt)[0]; selR.attr('x', dragX).attr('width', 0); this.setPointerCapture(evt.pointerId); evt.preventDefault();
      })
      .on('pointerup', (evt: PointerEvent) => {
        if (dragX == null) return;
        const px = d3.pointer(evt)[0], a = Math.min(px, dragX), b = Math.max(px, dragX); dragX = null; selR.attr('width', 0);
        if (b - a > 8) { LB.zMain = [x.invert(a), x.invert(b)]; dash.draw('chart'); }
      })
      .on('pointermove', (evt: PointerEvent) => {
        const [px] = d3.pointer(evt);
        if (dragX != null) { selR.attr('x', Math.min(px, dragX)).attr('width', Math.abs(px - dragX)); tip.hidden = true; return; }
        const r = rows[bis(rows, x.invert(px))];
        rule.attr('x1', x(r.t)).attr('x2', x(r.t)).attr('opacity', 1);
        const lit = all.filter(([k]) => r[`f_${k}`] === 1).map((s) => s[1]);
        tip.replaceChildren();
        const b = document.createElement('b'); b.textContent = LB.dateW(r.t); tip.append(b);
        [(LB.ix === 'TAIEX' ? '加權 ' : '櫃買 ') + LB.num(r.price, 2), (r.fear != null ? '恐慌溫度 ' + r.fear.toFixed(1) : '恐慌溫度 —') + (r.f_dual === 1 ? '・雙重確認亮燈' : '') + '・偏空警示 ' + r.wscore + ' / 3',
          lit.length ? '當天亮燈：' + lit.join('、') : '當天沒有已確認的亮燈'].forEach((t) => { const div = document.createElement('div'); div.textContent = t; tip.append(div); });
        const ri = rows.indexOf(r), near = ev.filter((q) => Math.abs((idxOf.get(q.date) ?? -99) - ri) <= 2).sort((a, b) => ORD[b.signal] - ORD[a.signal])[0];
        const nt = e.data.find((q) => q.signal === 'note' && q.start <= r.date && r.date <= q.end);
        if (nt?.signal === 'note' && !near?.note) { const div = document.createElement('div'); div.textContent = '事件註記：' + nt.note + '（' + nt.start.replaceAll('-', '/') + '–' + nt.end.slice(5).replace('-', '/') + '）'; tip.append(div); }
        if (near) {
          const hd = document.createElement('b'); hd.textContent = LB.dateW(LB.parse(near.date)) + ' ' + (LB.SHORT[near.signal] || near.signal) + ' 標記'; tip.append(hd);
          [near.value || ''].concat(LB.evLines(near)).filter(Boolean).forEach((t) => { const div = document.createElement('div'); div.textContent = t; tip.append(div); });
        }
        tip.hidden = false;
        const sx = x(r.t) / W * el.clientWidth;
        tip.style.left = Math.min(Math.max(0, sx + 12), el.clientWidth - tip.offsetWidth) + 'px'; tip.style.top = '8px';
      })
      .on('pointerleave', () => { tip.hidden = true; rule.attr('opacity', 0); });
  });

  // 回測表、超額長條、極值距離
  const orderOf = (side: string | undefined): readonly BacktestSignal[] => (side === 'top' ? LB.TORDER : side === 'warn' ? LB.WORDER : LB.BORDER);
  document.querySelectorAll('table[data-compact]').forEach((t) => {
    t.classList.add('lb-compact');
    const b = document.createElement('button'); b.type = 'button'; b.className = 'lb-btn lb-colbtn'; b.textContent = '顯示全部欄位'; b.setAttribute('aria-expanded', 'false');
    const wrap = t.closest<HTMLElement>('.lb-tablewrap');
    if (!wrap) return;
    wrap.id = (t.id || t.closest('section')?.id || 'lb-table') + '-columns';
    b.setAttribute('aria-controls', wrap.id);
    b.addEventListener('click', () => { const on = t.classList.toggle('lb-compact'); b.textContent = on ? '顯示全部欄位' : '只看重點欄位'; b.setAttribute('aria-expanded', String(!on)); });
    const controls = t.id === 'lb-levels' ? document.getElementById('lb-levels-controls') : null;
    if (controls) controls.append(b);
    else wrap.before(b);
  });
  const writeCells = (tr: HTMLTableRowElement, headers: ArrayLike<HTMLTableCellElement>, fields: Cell[]) => fields.forEach(([text, value, note], i) => {
    const cell = tr.insertCell();
    cell.textContent = text ?? '';
    if (value != null) cell.className = LB.cls(value);
    if (headers[i].classList.contains('lb-minor')) cell.classList.add('lb-minor');
    if (headers[i].classList.contains('lb-hl')) cell.classList.add('lb-hl');
    if (note) {
      const detail = document.createElement('small'); detail.className = 'lb-cell-note'; detail.textContent = note;
      cell.append(detail);
    }
  });
  const sampleNote = (n: MaybeNumber) => n == null ? '' : n + ' 筆';
  const sample20Note = (r: SummaryRow) => r.n20 == null ? '' : '20 日有效 ' + r.n20;
  dash.draw('sum-body', (element) => {
    const el = requireElement(element, HTMLTableSectionElement);
    const s = dash.data('summary'); el.replaceChildren();
    if (s.status !== 'ok') { if (s.status === 'error') { const td = el.insertRow().insertCell(); td.colSpan = 13; td.className = 'lb-err'; td.textContent = '回測結果載入失敗。'; } return; }
    const headers = requireElement(el.closest('table')?.tHead, HTMLTableSectionElement).rows[1].cells;
    orderOf(el.dataset.side).forEach((k) => {
      const r = s.data.find((x) => x.signal === k && x.index === LB.ix); if (!r) return;
      const tr = el.insertRow(); tr.dataset.key = k + ',' + LB.ix; if (k.includes('combo')) tr.className = 'lb-row--combo';
      writeCells(tr, headers, [[r.name], [String(r.n), null, sample20Note(r)], [r.entry], [LB.pct(r.ret5), r.ret5, sampleNote(r.n5)], [LB.pct(r.ret20), r.ret20], [LB.pct(r.ret60), r.ret60, sampleNote(r.n60)],
        [LB.pct(r.excess5), r.excess5], [LB.pct(r.excess20), r.excess20], [LB.pct0(r.beat20)], [r.p20 == null ? '—' : r.p20.toFixed(3)],
        [LB.pct(r.excess60), r.excess60], [LB.pct0(r.beat60)], [r.p60 == null ? '—' : r.p60.toFixed(3)]]);
    });
  });

  dash.draw('excess-bars', (el) => {
    const d3 = charts();
    const s = dash.data('summary');
    if (s.status === 'loading') { el.replaceChildren(); el.textContent = '—'; return; }
    LB.done(el); el.replaceChildren();
    if (s.status !== 'ok') { const p = document.createElement('p'); p.className = 'lb-err'; p.textContent = '回測結果載入失敗。'; el.append(p); return; }
    const rows = orderOf(el.dataset.side).map((k) => s.data.find((r) => r.signal === k && r.index === LB.ix)).filter(present);
    if (!rows.length) return;
    const W = Math.max(280, el.clientWidth), bandH = W < 560 ? 40 : 44, H = rows.length * bandH + 28;
    const svg = d3.select(el).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img').attr('aria-label', '各訊號扣掉價格因素後的 5 日、20 日與 60 日超額報酬');
    const lab = svg.append('g').selectAll<SVGTextElement, unknown>('text').data(rows).join('text').text((r) => LB.SHORT[r.signal]);
    const m = { l: Math.ceil(Math.max(...lab.nodes().map((n) => n.getComputedTextLength()))) + 12, r: 56 };
    const lim = Math.max(1, d3.max(rows.flatMap((r) => [r.excess5, r.excess20, r.excess60]).filter(present), Math.abs) ?? 0);
    const x = d3.scaleLinear().domain([-lim, lim]).range([m.l + 44, W - m.r]).nice();
    const yb = d3.scaleBand().domain(rows.map((r) => r.signal)).range([6, H - 22]).padding(0.2);
    lab.attr('x', m.l - 8).attr('y', (r) => (yb(r.signal) ?? 0) + yb.bandwidth() / 2 + 4).attr('text-anchor', 'end')
      .style('fill', (r) => (r.signal.includes('combo') || r.signal === 'dual' ? 'var(--ink)' : 'var(--ink-3)')).style('font-weight', (r) => (r.signal.includes('combo') ? 700 : 400));
    svg.append('g').attr('class', 'lb-grid').selectAll('line').data(x.ticks(5)).join('line').attr('x1', x).attr('x2', x).attr('y1', 4).attr('y2', H - 22);
    svg.append('g').attr('class', 'lb-axis').attr('transform', `translate(0,${H - 22})`).call(d3.axisBottom(x).ticks(5).tickFormat((v) => v + '%').tickSizeOuter(0));
    svg.append('line').attr('x1', x(0)).attr('x2', x(0)).attr('y1', 4).attr('y2', H - 22).style('stroke', 'var(--ink-3)');
    const h2 = yb.bandwidth() / 3;
    ([['excess5', 0, 0.3], ['excess20', 1, 0.6], ['excess60', 2, 1]] as const).forEach(([f, j, op]) => {
      const g = svg.append('g'), rr = rows.flatMap((r) => { const value = r[f]; return value == null ? [] : [{ signal: r.signal, value }]; });
      g.selectAll('rect').data(rr).join('rect').attr('x', (r) => Math.min(x(0), x(r.value))).attr('width', (r) => Math.abs(x(r.value) - x(0)))
        .attr('y', (r) => (yb(r.signal) ?? 0) + j * h2).attr('height', h2 - 1).style('fill', (r) => (r.value >= 0 ? 'var(--up)' : 'var(--down)')).attr('opacity', op);
      g.selectAll<SVGTextElement, unknown>('text').data(rr).join('text').attr('x', (r) => (r.value >= 0 ? x(r.value) + 4 : x(r.value) - 4)).attr('text-anchor', (r) => (r.value >= 0 ? 'start' : 'end'))
        .attr('y', (r) => (yb(r.signal) ?? 0) + j * h2 + h2 / 2 + 3.5).style('font-size', '11px').text((r) => (W < 560 && f !== 'excess20' ? '' : LB.pct(r.value)));
    });
  });

  dash.draw('timing', (el) => {
    const d3 = charts();
    const e = dash.data('events');
    if (e.status === 'loading') { el.replaceChildren(); el.textContent = '—'; return; }
    LB.done(el); el.replaceChildren();
    if (e.status !== 'ok') { const p = document.createElement('p'); p.className = 'lb-err'; p.textContent = '事件資料載入失敗。'; el.append(p); return; }
    const side = el.dataset.side, sigs = orderOf(side), f = LB.ix === 'TAIEX' ? 'tw_ext' : 'tp_ext';
    const pts = e.data.flatMap((r) => {
      if (r.signal === 'note' || !sigs.includes(r.signal)) return [];
      const offset = r[f];
      return offset == null ? [] : [{ ...r, offset }];
    });
    const W = Math.max(280, el.clientWidth), H = sigs.length * 28 + 32;
    const svg = d3.select(el).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img')
      .attr('aria-label', side === 'top' ? '每次過熱訊號亮燈與前後 20 個交易日最高點的距離' : side === 'warn' ? '每次偏空警示亮燈與前後 20 個交易日最低點的距離' : '每次落底訊號亮燈與前後 20 個交易日最低點的距離');
    const lab = svg.append('g').selectAll<SVGTextElement, unknown>('text').data(sigs).join('text').text((k) => LB.SHORT[k]);
    const m = { l: Math.ceil(Math.max(...lab.nodes().map((n) => n.getComputedTextLength()))) + 12, r: 12 };
    const x = d3.scaleLinear().domain([-20, 20]).range([m.l, W - m.r]);
    const yb = d3.scaleBand().domain(sigs).range([6, H - 26]).padding(0.2);
    lab.attr('x', m.l - 8).attr('y', (k) => (yb(k) ?? 0) + yb.bandwidth() / 2 + 4).attr('text-anchor', 'end')
      .style('fill', (k) => (k.includes('combo') || k === 'dual' ? 'var(--ink)' : 'var(--ink-3)')).style('font-weight', (k) => (k.includes('combo') ? 700 : 400));
    svg.append('g').attr('class', 'lb-grid').selectAll('line').data([-20, -10, 10, 20]).join('line').attr('x1', x).attr('x2', x).attr('y1', 4).attr('y2', H - 26);
    svg.append('rect').attr('x', x(-5)).attr('width', x(5) - x(-5)).attr('y', 4).attr('height', H - 30).style('fill', 'var(--panel-2)');
    svg.append('line').attr('x1', x(0)).attr('x2', x(0)).attr('y1', 4).attr('y2', H - 26).style('stroke', 'var(--ink-3)');
    svg.append('g').attr('class', 'lb-axis').attr('transform', `translate(0,${H - 26})`)
      .call(d3.axisBottom(x).tickValues([-20, -10, -5, 0, 5, 10, 20]).tickFormat((v) => (+v > 0 ? '+' + v : String(v))).tickSizeOuter(0));
    const jit = (r: BacktestEvent) => { let h = 0; for (const c of r.date) h = (h * 31 + c.charCodeAt(0)) % 997; return (h / 997 - 0.5) * yb.bandwidth() * 0.7; };
    const c = LB.FAMC[isOption(families, side) ? side : 'bottom'];
    const tip = document.createElement('div'); tip.className = 'lb-tip'; tip.hidden = true; el.append(tip);
    svg.append('g').selectAll('circle').data(pts).join('circle')
      .attr('cx', (r) => x(r.offset)).attr('cy', (r) => (yb(r.signal) ?? 0) + yb.bandwidth() / 2 + jit(r)).attr('r', 4)
      .style('fill', c).attr('fill-opacity', (r) => (r.signal.includes('combo') || side === 'warn' ? 0.95 : 0.5)).style('stroke', 'var(--color-bg)')
      .on('pointerenter', (evt: PointerEvent, r) => {
        tip.replaceChildren();
        const b = document.createElement('b'); b.textContent = LB.date(LB.parse(r.date)) + '　' + r.name; tip.append(b);
        const off = r.offset, w = side === 'top' ? '高點' : '低點';
        [off === 0 ? '亮燈當天就是' + w : off < 0 ? w + '在亮燈前 ' + (-off) + ' 個交易日' : w + '在亮燈後 ' + off + ' 個交易日',
          '之後 20 日報酬 ' + LB.pct(r[LB.ix === 'TAIEX' ? 'tw_ret20' : 'tp_ret20'])].forEach((t) => { const dv = document.createElement('div'); dv.textContent = t; tip.append(dv); });
        tip.hidden = false;
        const [px, py] = d3.pointer(evt, el);
        tip.style.left = Math.min(Math.max(0, px + 12), el.clientWidth - tip.offsetWidth) + 'px'; tip.style.top = Math.max(0, py - 50) + 'px';
      })
      .on('pointerleave', () => { tip.hidden = true; });
    const s = dash.data('summary');
    if (s.status === 'ok') {
      const med = sigs.map((k) => s.data.find((r) => r.signal === k && r.index === LB.ix)).flatMap((r) => r?.ext_median == null ? [] : [{ signal: r.signal, offset: r.ext_median }]);
      svg.append('g').selectAll('line').data(med).join('line').attr('x1', (r) => x(r.offset)).attr('x2', (r) => x(r.offset))
        .attr('y1', (r) => (yb(r.signal) ?? 0) + 2).attr('y2', (r) => (yb(r.signal) ?? 0) + yb.bandwidth() - 2).style('stroke', 'var(--ink)').attr('stroke-width', 2.5);
    }
  });

  dash.draw('timing-body', (element) => {
    const el = requireElement(element, HTMLTableSectionElement);
    const s = dash.data('summary'); el.replaceChildren();
    if (s.status !== 'ok') return;
    const headers = requireElement(el.closest('table')?.tHead, HTMLTableSectionElement).rows[0].cells;
    orderOf(el.dataset.side).forEach((k) => {
      const r = s.data.find((x) => x.signal === k && x.index === LB.ix); if (!r) return;
      const tr = el.insertRow(); tr.dataset.key = k + ',' + LB.ix; if (k.includes('combo')) tr.className = 'lb-row--combo';
      writeCells(tr, headers, [[r.name], [r.ext_median == null ? '—' : (r.ext_median > 0 ? '+' : '') + r.ext_median], [LB.within5(r)], [LB.pct0(r.ext_after)],
        [LB.pct(r.further_mean), r.further_mean, sampleNote(r.further_n)], [LB.pct0(r.further_big)], [LB.pct(r.off_ext), r.off_ext]]);
    });
  });

  // 事件明細與 PTT 文章
  dash.draw('ev-body', (element) => {
    const el = requireElement(element, HTMLTableSectionElement);
    const e = dash.data('events'); el.replaceChildren();
    const head = requireElement(el.closest('table')?.tHead, HTMLTableSectionElement).rows[0];
    const locationNote = byId('lb-event-location', HTMLElement);
    locationNote.hidden = true;
    const empty = (message: string, className: string) => {
      const td = el.insertRow().insertCell();
      td.colSpan = head.cells.length; td.className = className; td.textContent = message;
    };
    if (e.status !== 'ok') {
      if (e.status === 'error') empty('事件資料載入失敗。', 'lb-err');
      return;
    }
    const isPtt = isOption(postSignals, LB.evsig);
    const isTemperature = LB.evsig === 'dual' || LB.evsig.startsWith('thermo');
    const rows = e.data.filter((r): r is BacktestEvent => r.signal === LB.evsig).reverse();
    if (!rows.length) { empty('這個訊號在回測期間沒有亮過燈。', 'lb-l'); return; }
    const selectedRow = rows.findIndex((r) => r.date === LB.eventDate);
    if (selectedRow > 0) rows.unshift(...rows.splice(selectedRow, 1));
    const market = LB.eventIndex === 'TPEx' ? 'tp' : 'tw';
    const marketName = market === 'tp' ? '櫃買指數' : '加權指數';
    const extreme = isOption(LB.TORDER, LB.evsig) ? '最高' : '最低';
    const columns = [...head.cells].map((th) => {
      const field = th.dataset.field;
      if (!isOption(eventColumnNames, field)) throw new Error('事件表格欄位無效：' + field);
      return { th, field };
    });
    const group = (field: EventField) => field.includes('_') ? Number(!field.startsWith(market + '_')) + 1 : 0;
    columns.sort((a, b) => group(a.field) - group(b.field));
    const prominent: EventField[] = ['date', 'value', `${market}_ret20`, `${market}_further`];
    columns.forEach(({ th, field }) => {
      th.classList.toggle('lb-minor', !prominent.includes(field));
      if (field.endsWith('_further')) th.textContent = (field.startsWith('tw') ? '加權' : '櫃買') + ' 20 日' + extreme + '收盤報酬';
      if (field.endsWith('_ext')) th.textContent = '距' + (field.startsWith('tw') ? '加權' : '櫃買') + (extreme === '最低' ? '低點' : '高點');
    });
    const headers = columns.map(({ th }) => th);
    head.append(...headers);
    let match: HTMLTableRowElement | null = null;
    rows.forEach((r) => {
      const tr = el.insertRow(); tr.dataset.key = r.signal + ',' + r.date;
      if (r.date === LB.eventDate) {
        tr.classList.add('lb-event-match'); tr.id = 'lb-event-match'; tr.tabIndex = -1;
        match = tr;
      }
      const pending = (value: MaybeNumber): Cell => [LB.pct(value), value, value == null && r.pending20 ? '尚未滿 20 日' : ''];
      writeCells(tr, headers, columns.map(({ field }) => {
        if (field === 'date') return [displayDate(r.date)];
        if (field === 'value') return [r.value];
        const value = r[field];
        if (field.endsWith('_close')) return [value == null ? '—' : LB.num(value, 2)];
        if (field.endsWith('_ext')) return [value == null ? '—' : (value > 0 ? '+' : '') + value];
        return field.endsWith('_ret20') || field.endsWith('_further') ? pending(value) : [LB.pct(value), value];
      }));
      const evidence = eventEvidence(r);
      const sub = LB.evLines(r, !evidence).concat(r.lit ? ['亮燈：' + r.lit] : []);
      if (sub.length || evidence) {
        tr.classList.add('lb-has-sub');
        const sr = el.insertRow(); sr.className = 'lb-evsub'; const sc = sr.insertCell(); sc.colSpan = columns.length;
        sub.forEach((t) => { const sp = document.createElement('span'); sp.textContent = t; sc.append(sp); });
        if (evidence) sc.append(evidence);
      }
      if (isPtt || isTemperature) {
        const category = isOption(postSignals, r.signal) ? r.signal : 'creative', date = isPtt ? r.date : 'window-' + r.date;
        const params = { signal: r.signal, event: r.date, index: LB.eventIndex };
        const link = document.createElement('a'); link.className = 'lb-row-link'; link.textContent = isPtt ? '看文章' : '看 5 日文章';
        link.setAttribute('aria-label', link.textContent + '（' + displayDate(r.date) + '）');
        link.href = sectionUrl('lb-posts', { ...params, post: category, date }).href;
        tr.cells[0].append(link);
        const open = (evt: MouseEvent) => {
          if (nativeClick(evt)) return;
          evt.preventDefault();
          goPosts(category, date, params);
        };
        if (isPtt) { tr.classList.add('lb-click'); tr.addEventListener('click', open); }
        else link.addEventListener('click', open);
      }
    });
    if (!LB.eventDate) return;
    locationNote.hidden = false;
    locationNote.textContent = match ? '已定位 ' + displayDate(LB.eventDate) + '・' + marketName : '這個訊號在 ' + displayDate(LB.eventDate) + ' 沒有回測事件。';
    if (match && pendingEventReveal && location.hash === '#lb-events') {
      const mode = pendingEventReveal, date = LB.eventDate;
      pendingEventReveal = null;
      requestAnimationFrame(() => {
        const row = document.getElementById('lb-event-match');
        if (!row || LB.eventDate !== date || location.hash !== '#lb-events') return;
        row.closest('section')?.scrollIntoView({ block: 'start' });
        if (mode === 'focus') row.focus({ preventScroll: true });
      });
    }
  });

  dash.draw('pevent', (element) => {
    const sel = requireElement(element, HTMLSelectElement);
    const p = dash.data('posts');
    const evs = p.status === 'ok' ? [...new Set(p.data.filter((r) => r.signal === LB.psig && validDate(r.event)).map((r) => r.event))].sort().reverse() : [];
    const opts = [new Option(LB.psig === 'creative' ? '最新一天（09:00 分界）' : '最新 5 日（含待計入文章）', 'latest')];
    if (LB.psig !== 'hot_ptt' && ((p.status === 'ok' && p.windows?.['window-latest']) || LB.pevent === 'window-latest')) {
      opts.unshift(new Option('本次恐慌溫度的 5 日文章', 'window-latest'));
    }
    if (LB.pevent && LB.pevent !== 'latest' && LB.pevent !== 'window-latest' && !evs.includes(LB.pevent)) evs.unshift(LB.pevent);
    sel.replaceChildren(...opts, ...evs.map((d) => new Option(
      isPostWindow(d) ? displayDate(d.slice(7)) + ' 的 5 日文章' : displayDate(d) + ' 那次亮燈', d,
    )));
    if (!LB.pevent) LB.pevent = opts[0].value;
    sel.value = LB.pevent;
    sel.onchange = () => {
      LB.pevent = sel.value; dash.draw('post-body'); dash.draw('post-window');
      history.replaceState(null, '', sectionUrl('lb-posts', { post: LB.psig, date: LB.pevent }));
    };
  });

  dash.draw('post-window', (el) => {
    const posts = dash.data('posts'), key = LB.pevent || 'latest';
    el.hidden = true;
    if (posts.status !== 'ok') return;
    const range = posts.windows?.[key];
    if (!range) return;
    el.hidden = false;
    const count = posts.data.filter((r) => r.signal === LB.psig && r.event === key).length;
    el.textContent = '列出計入恐慌溫度的 ' + count + ' 篇。台灣時間 ' + displayDate(range.start) +
      ' 09:00 至 ' + displayDate(range.end) + ' 09:00' + (range.end_estimated ? '（結束日暫按下一個平日估計）' : '') + '。';
  });

  dash.draw('post-body', (element) => {
    const el = requireElement(element, HTMLTableSectionElement);
    const p = dash.data('posts'); el.replaceChildren();
    if (p.status !== 'ok') { if (p.status === 'error') { const td = el.insertRow().insertCell(); td.colSpan = 3; td.className = 'lb-err'; td.textContent = '文章資料載入失敗。'; } return; }
    const ev = LB.pevent || 'latest';
    const rows = p.data.filter((r) => r.signal === LB.psig && r.event === ev);
    if (!rows.length) {
      const td = el.insertRow().insertCell(); td.colSpan = 3; td.className = 'lb-l';
      td.textContent = isPostWindow(ev) && !p.windows?.[ev] ? '這個回測區間沒有留存文章明細。' : '這段期間沒有符合的文章。';
      return;
    }
    rows.slice().reverse().forEach((r) => {
      const tr = el.insertRow(); tr.dataset.key = r.url;
      const t0 = tr.insertCell(); t0.textContent = r.posted;
      if (r.pending) {
        // 文章算在「最後一個 09:00 已經過了的交易日」：09:00 前算前一天，週末算到星期五（國定假日沒有排除）
        const m = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})/.exec(r.posted || '');
        let day = '下一個交易日';
        if (m) {
          const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
          if (+m[4] < 9) d.setUTCDate(d.getUTCDate() - 1);
          while (d.getUTCDay() === 0 || d.getUTCDay() === 6) d.setUTCDate(d.getUTCDate() - 1);
          day = (d.getUTCMonth() + 1) + '/' + d.getUTCDate();
        }
        const s = document.createElement('span'); s.className = 'lb-pend'; s.textContent = '算 ' + day + '・那天的收盤資料更新後才計分'; t0.append(s);
      }
      if (r.judge) {
        const s = document.createElement('span'); s.className = r.judge === 'title' ? 'lb-pend' : 'lb-cell-note';
        s.textContent = { title: '待 AI 讀內文・暫依標題計入', ref: '歷史內文判定', ai: 'AI 已讀內文' }[r.judge] || '';
        t0.append(s);
      }
      const td = tr.insertCell(); td.className = 'lb-l';
      td.append(articleLink(r) || r.title);
      tr.insertCell().textContent = r.nrec || '—';
    });
  });

  // 鄉民恐慌溫度
  const tRow = () => statusRow('thermo');

  dash.draw('thermo-val', (el) => { const r = tRow(); el.textContent = r ? r.value.toFixed(1) : '—'; });
  dash.draw('thermo-c5', (el) => { const r = tRow(); el.textContent = r ? String(r.c5) : '—'; });
  dash.draw('thermo-l5', (el) => { const r = tRow(); el.textContent = r ? String(r.l5) : '—'; });
  dash.draw('thermo-scale', (el) => {
    const r = tRow(); el.replaceChildren(); if (!r) return;
    const cur = [...T_LEVELS].reverse().find(([lv]) => r.value >= lv);
    T_LEVELS.forEach((lv) => {
      const li = document.createElement('li'), on = lv === cur; if (on) { li.className = 'is-now'; li.setAttribute('aria-current', 'true'); }
      const i = document.createElement('i'); i.className = 'lamp lamp--bottom'; i.dataset.s = on ? 'on' : 'off'; i.setAttribute('aria-hidden', 'true');
      const b = document.createElement('b'); b.textContent = lv[1];
      const s = document.createElement('span'); s.textContent = lv[2];
      li.append(i, b, s); el.append(li);
    });
  });
  dash.draw('thermo-chip', (el) => {
    const r = tRow(); if (!r) { el.textContent = '—'; return; }
    const v = r.value;
    el.textContent = v >= 95 ? '極度恐慌（≥95）' : v >= 90 ? '恐慌（90–95）' : v >= 85 ? '偏恐慌（85–90）' : v >= 80 ? '留意（80–85）' : '平常（<80）';
    if (v >= 90) el.dataset.tone = 'bottom'; else delete el.dataset.tone;
  });
  dash.draw('thermo-asof', (el) => {
    const r = tRow(); if (!r) { el.textContent = '—'; return; }
    el.textContent = '上次 ≥95：' + (r.last_lit ? LB.date(LB.parse(r.last_lit)) : '無');
  });
  const LEVELS = [['dual', '雙重確認', null], ['thermo95', '≥95 極度恐慌', 95], ['thermo90', '≥90 恐慌', 90], ['thermo85', '≥85 偏恐慌', 85], ['thermo80', '≥80 留意', 80]] as const;
  const dRow = () => { const r = statusRow('dual'); return r?.signal === 'dual' ? r : null; };
  dash.draw('dual-pill', (el) => {
    const r = dRow();
    el.textContent = r ? dualStatus(r.value) : '待資料';
    if (r?.value === 1) el.dataset.tone = 'bottom'; else delete el.dataset.tone;
  });
  dash.draw('dual-recent', (el) => { const r = dRow(); el.textContent = r?.value === 0 && r.lit5 === 1 ? '近 5 個交易日曾達標' : ''; });
  dash.draw('dual-lamp', (el) => { const r = dRow(); el.dataset.s = !r ? 'missing' : r.value === 1 ? 'on' : r.lit5 === 1 ? 'recent' : 'off'; });
  dash.draw('dual-l5', (el) => { const r = dRow(); el.textContent = r ? String(r.l5) : '—'; });
  dash.draw('dual-ch', (el) => { const r = dRow(); el.textContent = r?.creative_heat?.toFixed(1) ?? '—'; });
  dash.draw('dual-dd', (el) => { const r = dRow(); el.textContent = r && r.dd60 != null ? LB.pct(r.dd60) : '—'; });
  dash.draw('dual-last', (el) => { const r = dRow(); el.textContent = r ? '上次達標 ' + (r.last_lit ? LB.date(LB.parse(r.last_lit)) : '無') : '—'; });
  for (const condition of ['loss', 'creative', 'drawdown'] as const) {
    dash.draw('dual-check-' + condition, (el) => {
      const passed = dRow()?.checks?.[condition];
      el.textContent = passed == null ? '' : passed ? '達標' : '未達標';
    });
  }
  dash.draw('headline-backtest', (el) => {
    const signal = el.dataset.signal;
    const r = isOption(backtestSignals, signal) ? sumRow(signal, 'TAIEX') : null;
    if (!r) { el.textContent = '回測資料暫時無法顯示。'; return; }
    const dual = r.signal === 'dual';
    const h = document.createElement('b'); h.textContent = dual ? '雙重確認' : '溫度首次達 95';
    const count = (n: MaybeNumber) => n == null ? '' : '（' + n + ' 筆）';
    el.replaceChildren(h, ' 共 ' + r.n + ' 次。加權 20 日平均報酬 ' + LB.pct(r.ret20) + count(r.n20) +
      (dual ? '，同期超額 ' + LB.pct(r.excess20) + count(r.n20) : '，20 日平均最低收盤報酬 ' + LB.pct(r.further_mean) + count(r.further_n)) +
      '。低點在亮燈前後 5 個交易日內 ' + LB.within5(r) + '。');
  });

  dash.draw('thermo-levels', (element) => {
    const el = requireElement(element, HTMLTableSectionElement);
    const s = dash.data('summary'); el.replaceChildren();
    if (s.status !== 'ok') { if (s.status === 'error') { const td = el.insertRow().insertCell(); td.colSpan = 9; td.className = 'lb-err'; td.textContent = '分級資料載入失敗。'; } return; }
    const t = tRow(), now = t ? t.value : null;
    const cur = now == null ? null : LEVELS.find(([, , lv]) => lv != null && now >= lv)?.[0];
    const dr = dRow(), headers = requireElement(el.closest('table')?.tHead, HTMLTableSectionElement).rows[0].cells;
    LEVELS.forEach(([k, label]) => {
      const r = s.data.find((x) => x.signal === k && x.index === LB.tix); if (!r) return;
      const now_ = k === 'dual' ? dr?.value === 1 : k === cur;
      const tr = el.insertRow(); tr.dataset.key = k + ',' + LB.tix; if (now_) tr.className = 'lb-now';
      writeCells(tr, headers, [
        [label, null, k !== 'dual' && now_ ? '目前等級' : ''],
        [LB.pct(r.ret20), r.ret20], [sampleNote(r.n20) || '—', null, '共 ' + r.n + ' 次事件'],
        [LB.pct0(r.win20)], [LB.pct(r.excess20), r.excess20],
        [LB.pct0(r.beat20)], [LB.within5(r)], [LB.pct(r.further_mean), r.further_mean, sampleNote(r.further_n)],
        [LB.pct(r.ret60), r.ret60, sampleNote(r.n60)],
      ]);
      tr.cells[2].classList.add('lb-levels-sample');
      if (k === 'dual') {
        const link = document.createElement('a');
        link.href = '#lb-dual-conditions'; link.textContent = label;
        link.setAttribute('aria-label', label + '，查看達標條件');
        link.addEventListener('click', (event) => { if (!nativeClick(event)) dualDetails.open = true; });
        tr.cells[0].replaceChildren(link);
      }
    });
  });

  dash.draw('thermo-chart', (el) => {
    const d3 = charts();
    const d = dash.data('daily'), e = dash.data('events');
    const disclosure = el.nextElementSibling;
    if (disclosure instanceof HTMLElement) disclosure.hidden = true;
    if (d.status === 'loading' || e.status === 'loading') { el.replaceChildren(); el.textContent = '—'; return; }
    LB.done(el); el.replaceChildren();
    if (d.status !== 'ok' || e.status !== 'ok') { const p = document.createElement('p'); p.className = 'lb-err'; p.textContent = '溫度資料載入失敗。'; el.append(p); return; }
    let rows = d.data.filter((r): r is DailyRow & { fear: number } => r.fear != null).map((r) => ({ ...r, t: LB.parse(r.date) }));
    const last = rows.at(-1)?.t;
    const back = last ? { all: null, '3y': d3.utcYear.offset(last, -3), '1y': d3.utcYear.offset(last, -1), '6m': d3.utcMonth.offset(last, -6) }[LB.trange] : null;
    if (back && !LB.zTherm) rows = rows.filter((r) => r.t >= back);
    const zoom = LB.zTherm;
    if (zoom) rows = rows.filter((r) => r.t >= zoom[0] && r.t <= zoom[1]);
    if (rows.length < 2) { const p = document.createElement('p'); p.className = 'lb-err'; p.textContent = '這段期間沒有溫度資料，請按「重設範圍」。'; el.append(p); return; }
    LB.syncDates("#lb-tfrom", "#lb-tto", rows);
    const spanD = (+rows[rows.length - 1].t - +rows[0].t) / 864e5;
    const W = Math.max(280, el.clientWidth), narrow = W < 560, topH = narrow ? 120 : 160, gap = 18, botH = narrow ? 130 : 170, H = topH + gap + botH + 24;
    const svg = d3.select(el).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img').attr('aria-label', '加權指數與鄉民恐慌溫度走勢');
    const [lo, hi] = d3.extent(rows, (r) => r.taiex);
    if (lo == null || hi == null) return;
    const yP = d3.scaleLog().domain([lo * 0.97, hi * 1.03]).range([topH - 4, 6]);
    let pt = yP.ticks(4).filter((v) => v >= lo * 0.97 && v <= hi * 1.03); while (pt.length > 4) pt = pt.filter((v, i) => i % 2 === 0);
    const probe = svg.append('g').selectAll<SVGTextElement, unknown>('text').data(pt.map((v) => LB.num(v)).concat(['100'])).join('text').text((t) => t);
    const m = { l: Math.ceil(Math.max(...probe.nodes().map((n) => n.getComputedTextLength()))) + 10, r: 8 };
    probe.remove();
    const x = d3.scaleUtc().domain([rows[0].t, rows[rows.length - 1].t]).range([m.l, W - m.r]);
    const yT = d3.scaleLinear().domain([0, 100]).range([topH + gap + botH, topH + gap]);
    svg.append('g').attr('class', 'lb-grid').selectAll('line').data(pt).join('line').attr('x1', m.l).attr('x2', W - m.r).attr('y1', yP).attr('y2', yP);
    svg.append('g').selectAll<SVGTextElement, unknown>('text').data(pt).join('text').attr('x', m.l - 6).attr('y', (v) => yP(v) + 4).attr('text-anchor', 'end').text((v) => LB.num(v));
    svg.append('path').datum(rows).attr('fill', 'none').attr('stroke-width', 1.4).style('stroke', 'var(--ink-2)').attr('d', d3.line<typeof rows[number]>().x((r) => x(r.t)).y((r) => yP(r.taiex)));
    svg.append('g').attr('class', 'lb-grid').selectAll('line').data([0, 50, 100]).join('line').attr('x1', m.l).attr('x2', W - m.r).attr('y1', yT).attr('y2', yT);
    svg.append('g').selectAll<SVGTextElement, unknown>('text').data([0, 50, 90, 100]).join('text').attr('x', m.l - 6).attr('y', (v) => yT(v) + 4).attr('text-anchor', 'end').text((v) => v);
    svg.append('path').datum(rows).style('fill', 'var(--wash-blue)')
      .attr('d', d3.area<typeof rows[number]>().x((r) => x(r.t)).y0(yT(0)).y1((r) => yT(r.fear)));
    svg.append('path').datum(rows).attr('fill', 'none').attr('stroke-width', 1.3).style('stroke', 'var(--lamp-blue)').attr('d', d3.line<typeof rows[number]>().x((r) => x(r.t)).y((r) => yT(r.fear)));
    ([[90, 'var(--ink-3)'], [95, 'var(--lamp-blue)']] as const).forEach(([v, c]) => svg.append('line').attr('x1', m.l).attr('x2', W - m.r).attr('y1', yT(v)).attr('y2', yT(v))
      .style('stroke', c).attr('stroke-dasharray', '4 3'));
    svg.append('g').attr('class', 'lb-axis').attr('transform', `translate(0,${H - 22})`)
      .call(d3.axisBottom<Date>(x).ticks(narrow ? 4 : 8).tickSizeOuter(0).tickFormat(LB.axisFormat(spanD, narrow)));
    const byDate = new Map(rows.map((row, i) => [row.date, { row, i }]));
    const marks = e.data.flatMap((event) => {
      const position = byDate.get(event.date);
      return position ? [{ event, ...position }] : [];
    });
    const ev = marks.filter(({ event }) => event.signal === 'thermo95');
    const mk = svg.append('g');
    ev.forEach(({ row }) => {
      LB.lampSvg(mk, x(row.t), yT(row.fear), 6, 'var(--lamp-blue)', 'on');
      LB.lampSvg(mk, x(row.t), yP(row.taiex), 5.5, 'var(--lamp-blue)', 'on');
    });
    const dev = marks.filter(({ event }) => event.signal === 'dual');
    const dia = d3.symbol().type(d3.symbolDiamond).size(110);
    for (const yPosition of [(row: typeof rows[number]) => yT(row.fear), (row: typeof rows[number]) => yP(row.taiex)]) {
      svg.append('g').selectAll('path').data(dev).join('path')
        .attr('d', () => dia()).attr('transform', ({ row }) => `translate(${x(row.t)},${yPosition(row) - 14})`)
        .style('fill', 'var(--ink)').style('stroke', 'var(--color-bg)').attr('stroke-width', 1.5);
    }
    // 事件文字：雙重確認優先，3 個交易日內只標一次
    const evAll = dev.concat(ev);
    const labeled: typeof marks = [];
    evAll.forEach((mark) => {
      if (LB.evLabel(mark.event) && !labeled.some((other) => Math.abs(other.i - mark.i) <= 3)) labeled.push(mark);
    });
    labeled.sort((a, b) => a.event.date.localeCompare(b.event.date));
    svg.append('g').selectAll<SVGTextElement, unknown>('text').data(labeled).join('text')
      .attr('x', ({ row }) => Math.min(Math.max(x(row.t), m.l + 30), W - m.r - 30))
      .attr('y', ({ row }, k) => Math.max(10, yP(row.taiex) - 24 - (k % 2) * 12)).attr('text-anchor', 'middle')
      .style('font-size', '11px').style('font-weight', 500).style('fill', 'var(--ink)')
      .style('paint-order', 'stroke').style('stroke', 'var(--color-bg)').style('stroke-width', '3px').style('stroke-linejoin', 'round').text(({ event }) => LB.evLabel(event));
    const nlab = marks.filter(({ event }) => event.signal === 'note' && !evAll.some((q) => q.event.note === event.note));
    svg.append('g').selectAll('circle').data(nlab).join('circle').attr('cx', ({ row }) => x(row.t)).attr('cy', ({ row }) => yP(row.taiex)).attr('r', 3.5)
      .style('fill', 'var(--ink-3)');
    svg.append('g').selectAll<SVGTextElement, unknown>('text').data(nlab).join('text')
      .attr('x', ({ row }) => Math.min(Math.max(x(row.t), m.l + 70), W - m.r - 70))
      .attr('y', ({ row }) => Math.min(topH - 2, yP(row.taiex) + 17)).attr('text-anchor', 'middle')
      .style('font-size', '11px').style('paint-order', 'stroke').style('stroke', 'var(--color-bg)').style('stroke-width', '3px').style('stroke-linejoin', 'round')
      .style('fill', 'var(--ink-3)').text(({ event }) => event.note + '（溫度未達 95）');
    chartEvents(el, evAll.concat(nlab).map(({ event }) => event), 'TAIEX');
    const tip = document.createElement('div'); tip.className = 'lb-tip'; tip.hidden = true; el.append(tip);
    const rule = svg.append('line').attr('y1', 4).attr('y2', H - 22).style('stroke', 'var(--cds-chart-reference)').attr('opacity', 0);
    const bis = d3.bisector((r: typeof rows[number]) => r.t).center;
    const selR = svg.append('rect').attr('y', 0).attr('height', H - 22).attr('width', 0).style('fill', 'var(--cds-chart-muted)').attr('opacity', 0.3);
    let dragX: number | null = null;
    svg.append('rect').attr('x', m.l).attr('y', 0).attr('width', W - m.l - m.r).attr('height', H - 22).attr('fill', 'transparent').style('cursor', 'crosshair')
      .on('pointerdown', function (evt: PointerEvent) {
        if (evt.pointerType !== 'mouse' || evt.button !== 0) return;
        dragX = d3.pointer(evt)[0]; selR.attr('x', dragX).attr('width', 0); this.setPointerCapture(evt.pointerId); evt.preventDefault();
      })
      .on('pointerup', (evt: PointerEvent) => {
        if (dragX == null) return;
        const px = d3.pointer(evt)[0], a = Math.min(px, dragX), b = Math.max(px, dragX); dragX = null; selR.attr('width', 0);
        if (b - a > 8) { LB.zTherm = [x.invert(a), x.invert(b)]; dash.draw('thermo-chart'); }
      })
      .on('pointermove', (evt: PointerEvent) => {
        const [px] = d3.pointer(evt);
        if (dragX != null) { selR.attr('x', Math.min(px, dragX)).attr('width', Math.abs(px - dragX)); tip.hidden = true; return; }
        const r = rows[bis(rows, x.invert(px))];
        rule.attr('x1', x(r.t)).attr('x2', x(r.t)).attr('opacity', 1);
        tip.replaceChildren();
        const b = document.createElement('b'); b.textContent = LB.dateW(r.t); tip.append(b);
        const ri = rows.indexOf(r), near = evAll.find((mark) => Math.abs(mark.i - ri) <= 2)?.event;
        ['恐慌溫度 ' + r.fear.toFixed(1), '創作文 5 日 ' + r.c5 + ' 篇（熱度 ' + r.cheat + '）・畢業文 5 日 ' + r.l5 + ' 篇', '加權 ' + LB.num(r.taiex, 2)]
          .concat(r.f_dual ? ['雙重確認亮燈'] : []).concat(near ? LB.evLines(near) : [])
          .concat(((nt) => (nt && !(near && near.note) ? ['事件註記：' + nt.note] : []))(e.data.find((q) => q.signal === 'note' && q.start <= r.date && r.date <= q.end)))
          .forEach((t) => { const div = document.createElement('div'); div.textContent = t; tip.append(div); });
        tip.hidden = false;
        const sx = x(r.t) / W * el.clientWidth;
        tip.style.left = Math.min(Math.max(0, sx + 12), el.clientWidth - tip.offsetWidth) + 'px'; tip.style.top = '8px';
      })
      .on('pointerleave', () => { tip.hidden = true; rule.attr('opacity', 0); });
  });
}
