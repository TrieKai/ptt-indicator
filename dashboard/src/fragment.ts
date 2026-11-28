import type { Card, Dashboard } from './runtime.ts';
import { registerDashboard } from './view.ts';

declare const dash: Omit<Dashboard, 'loadCard'> & { loadCard?(): Promise<void> };
declare const d3: typeof import('d3');

const loadCard = window.LBCard || dash.loadCard ? async (): Promise<Card> => {
  if (!window.LBCard) await dash.loadCard?.();
  if (!window.LBCard) throw new Error('找不到圖卡程式');
  return window.LBCard;
} : undefined;

registerDashboard({
  today: dash.today,
  data: (name) => dash.data(name),
  draw: (name, renderer) => dash.draw(name, renderer),
  openSection: (id) => dash.openSection?.(id),
  reload: dash.reload?.bind(dash),
  loadCard,
}, () => d3);
