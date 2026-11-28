import { dataNames, isOption, parsePayload } from './data.ts';
import type { DataName, DataStore, LoadState, Today } from './data.ts';

type Charts = typeof import('d3');
export type Card = typeof import('./card.ts');
declare global {
  interface Window {
    d3?: Charts;
    LBCard?: Card;
  }
}
type Renderer = (element: HTMLElement) => void;
type Binding = { el: HTMLElement; group: Group; sources: DataName[]; chart: boolean; name: string };
type Group = { active: boolean; charts: boolean; sources: Set<DataName>; bindings: Binding[]; status?: HTMLElement };

export interface Dashboard {
  today?: Today;
  data<K extends DataName>(name: K): LoadState<K>;
  draw(name: string, render?: Renderer): void;
  openSection?(id: string): void;
  reload?(name: DataName): Promise<void>;
  loadCard?(): Promise<Card>;
}

function loadScript<T>(file: string, getValue: () => T | undefined): Promise<T> {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    const fail = () => {
      script.remove();
      reject(new Error('程式載入失敗：' + file));
    };
    script.onload = () => {
      const value = getValue();
      if (value) resolve(value);
      else fail();
    };
    script.onerror = fail;
    script.src = new URL(file, import.meta.url).href;
    document.head.append(script);
  });
}

export function createDashboard(today: Today) {
  const store: DataStore = {
    daily: { status: 'idle' },
    events: { status: 'idle' },
    summary: { status: 'idle' },
    status: { status: 'ok', data: today.status },
    posts: { status: 'idle' },
  };
  const renderers = new Map<string, Renderer>();
  const bindings: Binding[] = [];
  const groups = new Map<Element | null, Group>();
  const requests = new Map<DataName, Promise<void>>();
  let chartState: 'idle' | 'loading' | 'error' | 'ok' = 'idle';
  let d3: Charts | undefined;
  let cardRequest: Promise<Card> | undefined;

  const waiting = (n: DataName) => store[n].status === 'idle' || store[n].status === 'loading';
  const render = (binding: Binding) => {
    if (!binding.group.active || (binding.chart && chartState !== 'ok')) return;
    if (binding.name !== 'reading-status' && binding.sources.some(waiting)) return;
    try { renderers.get(binding.name)?.(binding.el); }
    catch (error) { console.error('draw ' + binding.name, error); }
  };
  const showGroupStatus = (group: Group) => {
    if (!group.status || !group.active) return;
    const loading = [...group.sources].some(waiting) || (group.charts && chartState === 'loading');
    const failed = [...group.sources].filter((n) => store[n].status === 'error');
    const chartFailed = group.charts && chartState === 'error';
    group.status.hidden = !loading && !failed.length && !chartFailed;
    group.status.classList.toggle('lb-err', !!failed.length || chartFailed);
    group.status.replaceChildren();
    if (loading) { group.status.textContent = '正在載入這個區段…'; return; }
    if (!failed.length && !chartFailed) return;
    group.status.textContent = chartFailed ? '圖表程式暫時無法載入。' : '這個區段有資料暫時無法載入。';
    const retry = document.createElement('button');
    retry.type = 'button'; retry.className = 'lb-btn'; retry.textContent = '重試載入';
    retry.addEventListener('click', () => {
      failed.forEach(load);
      if (chartFailed) loadCharts();
    });
    group.status.append(retry);
  };
  const notify = (source: DataName | 'charts') => {
    bindings.filter((binding) => source === 'charts' ? binding.chart : binding.sources.includes(source)).forEach(render);
    groups.forEach((group) => {
      if (source === 'charts' ? group.charts : group.sources.has(source)) showGroupStatus(group);
    });
  };
  const load = <K extends DataName>(name: K) => {
    const pending = requests.get(name);
    if (pending) return pending;
    store[name] = { status: 'loading' };
    notify(name);
    const request = fetch('data/' + name + '.json', { cache: 'no-cache' })
      .then((response) => {
        if (!response.ok) throw new Error(name + ' ' + response.status);
        return response.json() as Promise<unknown>;
      })
      .then((json) => { store[name] = parsePayload(name, json); })
      .catch((error) => { console.error(error); store[name] = { status: 'error' }; })
      .finally(() => { requests.delete(name); notify(name); });
    requests.set(name, request);
    return request;
  };
  const loadCharts = () => {
    if (chartState === 'loading' || chartState === 'ok') return;
    chartState = 'loading';
    notify('charts');
    void loadScript('d3.min.js', () => window.d3)
      .then((module) => { d3 = module; chartState = 'ok'; })
      .catch((error) => { console.error(error); chartState = 'error'; })
      .finally(() => notify('charts'));
  };
  const activate = (root: Element | null) => {
    const group = groups.get(root);
    if (!group || group.active) return;
    group.active = true;
    group.sources.forEach((n) => { if (store[n].status === 'idle') void load(n); });
    if (group.charts && chartState === 'idle') loadCharts();
    group.bindings.forEach(render);
    showGroupStatus(group);
  };
  const openSection = (id: string) => {
    const target = document.getElementById(id);
    if (target) activate(target.closest('section') || target);
  };
  const openAnchor = () => openSection(location.hash.slice(1));
  const dash: Dashboard = {
    today,
    data: (name) => store[name],
    draw(name, renderer) {
      if (renderer) renderers.set(name, renderer);
      bindings.filter((binding) => binding.name === name).forEach(render);
    },
    openSection, reload: load,
    loadCard() {
      return cardRequest ??= loadScript('card-view.js', () => window.LBCard).catch((error) => {
        cardRequest = undefined;
        throw error;
      });
    },
  };
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll<HTMLElement>('[data-draw]').forEach((el) => {
      const name = el.dataset.draw;
      if (!name) return;
      const section = el.closest('section');
      const root = el.closest('details') || (section?.id !== 'lb-today' ? section : null);
      let group = groups.get(root);
      if (!group) {
        group = { active: false, charts: false, sources: new Set(), bindings: [] };
        groups.set(root, group);
      }
      const sources = (el.dataset.source ?? '').split(' ').filter((key) => isOption(dataNames, key));
      const chart = el.classList.contains('lb-chart');
      const binding = { el, group, sources, chart, name };
      for (const source of sources) group.sources.add(source);
      group.charts ||= chart;
      group.bindings.push(binding);
      bindings.push(binding);
    });
    activate(null);
    const observer = typeof IntersectionObserver === 'function' ? new IntersectionObserver((entries, io) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) { io.unobserve(entry.target); activate(entry.target); }
      });
    }, { rootMargin: '96px 0px' }) : null;
    groups.forEach((group, root) => {
      if (!root) return;
      group.status = document.createElement('p');
      group.status.className = 'lb-cap lb-load-state';
      group.status.setAttribute('role', 'status');
      group.status.hidden = true;
      root.firstElementChild?.after(group.status);
      if (root instanceof HTMLDetailsElement) {
        root.addEventListener('toggle', () => { if (root.open) activate(root); });
        if (root.open) activate(root);
      } else if (observer) observer.observe(root);
      else activate(root);
    });
    openAnchor();
  }, { once: true });
  window.addEventListener('hashchange', openAnchor);
  let resizeTimer: number | undefined;
  let width = window.innerWidth;
  window.addEventListener('resize', () => {
    if (window.innerWidth === width) return;
    width = window.innerWidth;
    clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => bindings.filter((binding) => binding.chart).forEach(render), 200);
  });
  const charts = () => {
    if (!d3) throw new Error('圖表程式尚未載入');
    return d3;
  };
  return { dash, charts };
}
