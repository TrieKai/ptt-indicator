import { families, isOption, markets, validDate } from './data.ts';
import type { Family, Market } from './data.ts';

export const chartSections = { chart: 'lb-chart-sec', 'thermo-chart': 'lb-thermo' } as const;
export type ChartKey = keyof typeof chartSections;
export const articleKinds = ['loss', 'creative'] as const;
export type ArticleKind = typeof articleKinds[number];

type ChartLink = {
  key: ChartKey;
  day: string;
  market: Market;
  strip: Family;
  range: readonly [string, string] | null;
  articles: ArticleKind | null;
};

export function readChartLink(url: URL): ChartLink | null {
  const key = url.hash === '#' + chartSections.chart ? 'chart' : url.hash === '#' + chartSections['thermo-chart'] ? 'thermo-chart' : null;
  const query = url.searchParams;
  const day = query.get('day');
  if (!key || !validDate(day)) return null;
  const index = query.get('index'), strip = query.get('strip'), articles = query.get('articles');
  const from = query.get('from'), to = query.get('to');
  return {
    key, day,
    market: key === 'chart' && isOption(markets, index) ? index : 'TAIEX',
    strip: key === 'chart' && isOption(families, strip) ? strip : 'bottom',
    articles: isOption(articleKinds, articles) ? articles : null,
    range: validDate(from) && validDate(to) && from < to && from <= day && day <= to ? [from, to] : null,
  };
}

export function chartLinkUrl(base: URL, link: ChartLink): string {
  const url = new URL(base.pathname, base.origin);
  url.hash = chartSections[link.key];
  url.searchParams.set('day', link.day);
  if (link.key === 'chart') {
    url.searchParams.set('index', link.market);
    if (link.strip !== 'bottom') url.searchParams.set('strip', link.strip);
  }
  if (link.range) {
    url.searchParams.set('from', link.range[0]);
    url.searchParams.set('to', link.range[1]);
  }
  if (link.articles) url.searchParams.set('articles', link.articles);
  return url.href;
}
