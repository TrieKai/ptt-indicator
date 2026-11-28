import { validDate } from './data.ts';
import type { Today } from './data.ts';

const hour = 60 * 60 * 1000;
const checkInterval = hour / 2;

export function taiwanTime(value: unknown): number | null {
  if (typeof value !== 'string') return null;
  const match = /^(\d{4}-\d{2}-\d{2}) ((?:[01]\d|2[0-3]):[0-5]\d)$/.exec(value);
  return match && validDate(match[1]) ? Date.parse(match[1] + 'T' + match[2] + ':00+08:00') : null;
}

export function reportNotice(now: number, generated: number | null, posted: number | null): string {
  const age = (time: number | null) => time == null ? 0 : Math.floor((now - time) / hour);
  if (age(generated) >= 3) return '目前畫面的資料約 ' + age(generated) + ' 小時前產生';
  if (age(posted) >= 3) return '最後收錄的文章約 ' + age(posted) + ' 小時前發出';
  return '';
}

export function registerReportStatus(today: Today | undefined) {
  const panel = document.querySelector<HTMLDetailsElement>('#lb-report-times');
  if (!panel) return;
  const thermostatus = today?.status.find((row) => row.signal === 'thermo');
  const generatedAt = taiwanTime(today?.generated_at);
  const lastArticle = taiwanTime(thermostatus?.ptt_asof);
  const controls = panel.querySelector<HTMLElement>('[data-report-controls]');
  const checkButton = panel.querySelector<HTMLButtonElement>('[data-report-check]');
  const loadButton = panel.querySelector<HTMLButtonElement>('[data-report-load]');
  const result = panel.querySelector<HTMLElement>('[data-report-result]');
  const notices = document.querySelectorAll<HTMLElement>('[data-report-notice]');
  const open = () => {
    const parent = panel.parentElement;
    if (parent instanceof HTMLDetailsElement) parent.open = true;
    panel.open = true;
  };
  const restore = () => { if (location.hash === '#lb-report-times') open(); };
  document.querySelectorAll<HTMLAnchorElement>('a[href="#lb-report-times"]').forEach((link) => {
    link.addEventListener('click', (event) => { if (!event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) open(); });
  });
  window.addEventListener('hashchange', restore);
  restore();

  let newer: { at: number; label: string } | null = null;
  function updateNotice(now: number) {
    const text = newer ? '有新版資料可載入' : reportNotice(now, generatedAt, lastArticle);
    for (const notice of notices) {
      if (notice.textContent !== text) notice.textContent = text;
      notice.hidden = !text;
    }
  }
  updateNotice(Date.now());
  if (generatedAt == null || !controls || !checkButton || !loadButton || !result) return;
  controls.hidden = false;
  let checkedAt = 0;
  let checking = false;
  const check = async (manual: boolean) => {
    if (checking) return;
    checking = true;
    checkedAt = Date.now();
    checkButton.setAttribute('aria-disabled', 'true');
    if (manual) result.textContent = '正在檢查更新…';
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch('data/report.json', { cache: 'no-cache', signal: controller.signal });
      if (!response.ok) throw new Error('資料時間載入失敗');
      const timestamp: unknown = (await response.json())?.generated_at;
      const remote = taiwanTime(timestamp);
      if (remote == null || typeof timestamp !== 'string') throw new Error('資料時間格式有誤');
      if (remote > generatedAt && (!newer || remote > newer.at)) newer = { at: remote, label: timestamp.replaceAll('-', '/') };
      if (newer) {
        loadButton.hidden = false;
        result.textContent = '新版資料於 ' + newer.label + ' 產生。';
      } else if (manual) result.textContent = '目前沒有新版資料。';
    } catch {
      if (manual) result.textContent = '暫時無法檢查更新，請稍後再試。';
    } finally {
      clearTimeout(timeout);
      checking = false;
      checkButton.removeAttribute('aria-disabled');
      updateNotice(Date.now());
    }
  };
  const tick = () => {
    if (document.hidden) return;
    const now = Date.now();
    updateNotice(now);
    if (!newer && now - Math.max(generatedAt, checkedAt) >= checkInterval) void check(false);
  };
  checkButton.addEventListener('click', () => void check(true));
  loadButton.addEventListener('click', () => {
    if (!newer) return;
    const next = new URL(location.href);
    next.searchParams.set('report', String(newer.at));
    location.replace(next.href);
  });
  window.addEventListener('pageshow', tick);
  document.addEventListener('visibilitychange', tick);
  window.setInterval(tick, 60000);
  tick();
}
