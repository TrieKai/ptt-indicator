import { validDate } from './data.ts';
import type { DailyRow, Today } from './data.ts';

const storageKey = 'ptt-indicator:comparison:v1';
type Reading = { date: string; fear: number; dual: 0 | 1; warnings: number };

function reading(row: DailyRow | null | undefined): Reading | null {
  if (!row || row.fear == null) return null;
  return { date: row.date, fear: row.fear, dual: row.f_dual, warnings: row.wscore };
}

function savedReading(): Reading | null {
  try {
    const item = JSON.parse(localStorage.getItem(storageKey) ?? 'null') as Partial<Reading> | null;
    if (item && validDate(item.date) && typeof item.fear === 'number' && item.fear >= 0 && item.fear <= 100 &&
        (item.dual === 0 || item.dual === 1) && typeof item.warnings === 'number' && Number.isInteger(item.warnings) &&
        item.warnings >= 0 && item.warnings <= 3) {
      return { date: item.date, fear: item.fear, dual: item.dual, warnings: item.warnings };
    }
  } catch { /* 有些瀏覽器模式無法讀取網站儲存。 */ }
  return null;
}

function temperatureChange(current: Reading, base: Reading): string {
  const points = Math.round((current.fear - base.fear) * 10) / 10;
  return points === 0 ? '持平' : (points > 0 ? '升 ' : '降 ') + Math.abs(points).toFixed(1) + ' 點';
}

export function registerReadingComparison(today: Today | undefined) {
  const current = reading(today?.daily), previous = reading(today?.previous_daily);
  const panel = document.querySelector<HTMLDetailsElement>('#lb-reading-comparison');
  if (!panel || !current) return;
  const summary = panel.querySelector('.lb-compare-summary');
  const date = panel.querySelector('[data-comparison-date]');
  const baseHeading = panel.querySelector('[data-comparison-base]');
  const table = panel.querySelector('table');
  const tbody = table?.tBodies[0];
  const save = panel.querySelector<HTMLButtonElement>('[data-comparison-save]');
  const clear = panel.querySelector<HTMLButtonElement>('[data-comparison-clear]');
  const message = panel.querySelector<HTMLElement>('[data-comparison-message]');
  if (!summary || !date || !baseHeading || !table || !tbody || !save || !clear || !message) return;

  let stored = savedReading();
  const asDate = (value: string) => value.replaceAll('-', '/');
  const savedCurrent = () => stored?.date === current.date && stored.fear === current.fear &&
    stored.dual === current.dual && stored.warnings === current.warnings;
  const announce = (text: string) => { message.hidden = false; message.textContent = text; };
  const render = () => {
    const unchanged = savedCurrent();
    const savedBase = unchanged ? null : stored;
    const base = savedBase ?? previous;
    summary.textContent = savedBase ? '與記錄相比，溫度' + temperatureChange(current, savedBase)
      : unchanged ? '已記住本次讀值' : previous ? '溫度較上個交易日' + temperatureChange(current, previous) : '';
    baseHeading.textContent = savedBase ? '記住的讀值' : '上個交易日';
    date.textContent = base ? '收盤資料日 ' + asDate(base.date) + ' 與 ' + asDate(current.date) : '暫無上個交易日的讀值。';
    table.hidden = !base;
    tbody.replaceChildren();
    if (base) {
      for (const [name, from, to] of [
        ['鄉民恐慌溫度', base.fear.toFixed(1), current.fear.toFixed(1)],
        ['雙重確認', base.dual ? '達標' : '未達標', current.dual ? '達標' : '未達標'],
        ['偏空警示', base.warnings + '／3 項', current.warnings + '／3 項'],
      ]) {
        const row = tbody.insertRow();
        const label = document.createElement('th'); label.scope = 'row'; label.textContent = name;
        row.append(label);
        row.insertCell().textContent = from;
        row.insertCell().textContent = to;
      }
    }
    clear.hidden = !stored;
    save.textContent = unchanged ? '已記住這次讀值' : stored ? '用本次更新記錄' : '記住這次讀值';
    save.setAttribute('aria-disabled', String(unchanged));
  };

  save.addEventListener('click', () => {
    if (savedCurrent()) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify(current));
      stored = current;
      render();
      announce('已記住 ' + asDate(current.date) + ' 的讀值。');
    } catch { announce('這個瀏覽器目前無法儲存讀值。'); }
  });
  clear.addEventListener('click', () => {
    try {
      localStorage.removeItem(storageKey);
      stored = null;
      render();
      save.focus({ preventScroll: true });
      announce('已清除記錄。');
    } catch { announce('目前無法清除讀值記錄，請再試一次。'); }
  });
  window.addEventListener('storage', (event) => {
    if (event.key !== storageKey && event.key !== null) return;
    stored = savedReading();
    render();
  });
  render();
  panel.hidden = false;
}
