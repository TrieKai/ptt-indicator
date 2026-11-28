import * as v from 'valibot';

export const dataNames = ['daily', 'events', 'summary', 'status', 'posts'] as const;
export type DataName = typeof dataNames[number];

export const markets = ['TAIEX', 'TPEx'] as const;
export type Market = typeof markets[number];

export const families = ['bottom', 'top', 'warn'] as const;
export type Family = typeof families[number];

export const lampSignals = [
  'creative', 'loss', 'margin', 'default', 'foreign', 'pc_high', 'vix_high', 'bigdrop',
  'hot_ptt', 'turnover', 'margin_up', 'foreign_buy', 'stretch', 'pc_low', 'fut_long', 'vix_low',
  'fut_short', 'fut_ratio_short', 'fut_chg_short',
] as const;
export type LampSignal = typeof lampSignals[number];
export type LampState = 'on' | 'recent' | 'off' | 'missing';

export const backtestSignals = [
  ...lampSignals, 'dual', 'thermo80', 'thermo85', 'thermo90', 'thermo95',
  'combo3', 'combo4', 'combo5_3', 'gcombo3', 'gcombo4',
] as const;
export type BacktestSignal = typeof backtestSignals[number];

const standardStatusSignals = [...lampSignals, 'score', 'gscore', 'wscore'] as const;
export const statusSignals = [...standardStatusSignals, 'dual', 'thermo'] as const;
export type StatusSignal = typeof statusSignals[number];

export const postSignals = ['creative', 'loss', 'hot_ptt'] as const;
export type PostSignal = typeof postSignals[number];

export function isOption<const T extends string>(options: readonly T[], value: unknown): value is T {
  return options.some((option) => option === value);
}

export function validDate(value: unknown): value is string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(value + 'T00:00:00Z');
  return Number.isFinite(+date) && date.toISOString().slice(0, 10) === value;
}

const date = v.pipe(v.string(), v.check((value) => validDate(value), '日期須為有效的 YYYY-MM-DD'));
const number = v.pipe(v.number(), v.finite());
const count = v.pipe(number, v.integer(), v.minValue(0));
const binary = v.picklist([0, 1]);
const maybeNumber = v.nullable(number);
const optionalNumber = v.nullish(number);
const side = v.picklist(families);
const lampFields = Object.fromEntries(lampSignals.map((signal) => [`f_${signal}`, binary])) as
  Record<`f_${LampSignal}`, typeof binary>;

const dailyRow = v.object({
  date, taiex: number, tpex: maybeNumber, score: count, gscore: count, wscore: count,
  fear: maybeNumber, c5: count, l5: count, f_dual: binary, cheat: maybeNumber, ...lampFields,
});
export type DailyRow = v.InferOutput<typeof dailyRow>;

const eventFields = {
  date,
  value: v.optional(v.string()),
  tw_close: maybeNumber, tw_ret5: maybeNumber, tw_ret20: maybeNumber, tw_ret60: maybeNumber,
  tw_further: maybeNumber, tw_ext: maybeNumber,
  tp_close: maybeNumber, tp_ret5: maybeNumber, tp_ret20: maybeNumber, tp_ret60: maybeNumber,
  tp_further: maybeNumber, tp_ext: maybeNumber,
};
export type EventField = keyof typeof eventFields;
export const eventColumnNames = Object.keys(eventFields) as EventField[];

const article = { title: v.string(), url: v.string() };
const eventBase = {
  name: v.string(), side, date, tw_close: maybeNumber, tp_close: maybeNumber,
  note: v.optional(v.string()), themes: v.optional(v.string()),
  loss_titles: v.nullish(v.union([v.string(), v.array(v.string())])),
  creative_n5: v.optional(count), loss_sources: v.optional(v.array(v.object(article))),
};
const backtestEvent = v.object({
  ...eventBase, ...eventFields, signal: v.picklist(backtestSignals),
  value: v.string(), pending20: v.boolean(), lit: v.string(),
});
const eventRow = v.variant('signal', [
  backtestEvent,
  v.object({
    ...eventBase, signal: v.literal('note'), note: v.string(), start: date, end: date,
    lit: v.optional(v.never()),
  }),
]);
export type BacktestEvent = v.InferOutput<typeof backtestEvent>;
export type EventRow = v.InferOutput<typeof eventRow>;

const horizons = [1, 5, 20, 60] as const;
const metrics = ['ret', 'win', 'rand', 'p', 'excess', 'beat'] as const;
const sampleFields = Object.fromEntries(horizons.map((horizon) => [`n${horizon}`, count])) as
  Record<`n${typeof horizons[number]}`, typeof count>;
const metricFields = Object.fromEntries(metrics.flatMap((metric) =>
  horizons.map((horizon) => [`${metric}${horizon}`, optionalNumber]))) as
  Record<`${typeof metrics[number]}${typeof horizons[number]}`, typeof optionalNumber>;
const summaryRow = v.object({
  signal: v.picklist(backtestSignals), name: v.string(), side, index: v.picklist(markets),
  entry: v.picklist(['當天收盤', '隔天開盤']), n: count, ...sampleFields, ...metricFields,
  ext_median: maybeNumber, ext_n: count, ext_within5_n: count, ext_within5: maybeNumber,
  ext_after: maybeNumber, further_mean: maybeNumber, further_n: count, further_big: maybeNumber, off_ext: maybeNumber,
});
export type SummaryRow = v.InferOutput<typeof summaryRow>;

const statusFields = {
  name: v.string(), side, asof: date, value: number,
  source_asof: v.nullish(date), threshold: maybeNumber, unit: v.string(), rule: v.picklist(['≥', '≤', '=']),
  lit5: binary, last_lit: v.nullable(date), recent: v.optional(v.array(v.tuple([date, maybeNumber, maybeNumber]))),
  pending: v.optional(count), l5: v.optional(count), creative_heat: optionalNumber, dd60: optionalNumber,
  c5: v.optional(count), loss_heat: optionalNumber, ptt_asof: v.optional(v.string()), ptt_lag_h: v.optional(number),
};
const statusRow = v.variant('signal', [
  v.object({ ...statusFields, signal: v.picklist(standardStatusSignals) }),
  v.object({ ...statusFields, signal: v.literal('dual'), value: binary, l5: count, creative_heat: number, dd60: number,
    checks: v.optional(v.object({ loss: v.boolean(), creative: v.boolean(), drawdown: v.boolean() })) }),
  v.object({ ...statusFields, signal: v.literal('thermo'), value: v.pipe(number, v.minValue(0), v.maxValue(100)), c5: count, l5: count }),
]);
export type StatusRow = v.InferOutput<typeof statusRow>;

const postWindow = v.object({ start: date, end: date, end_estimated: v.boolean() });
export type PostWindow = v.InferOutput<typeof postWindow>;
const postRow = v.object({
  ...article, signal: v.picklist(postSignals), event: v.string(), posted: v.string(), nrec: v.string(),
  pending: v.optional(v.boolean()), judge: v.optional(v.picklist(['ref', 'ai', 'title'])),
});

const meta = v.object({ label: v.string(), value: v.string(), type: v.optional(v.string()), lang: v.optional(v.string()) });
type Meta = v.InferOutput<typeof meta>;
const statusRows = v.pipe(v.array(statusRow), v.check(
  (rows) => (['thermo', 'dual', 'wscore'] as const).every((signal) => rows.some((row) => row.signal === signal)),
  '缺少恐慌溫度、雙重確認或偏空警示資料',
));

const payloads = {
  daily: v.object({ rows: v.pipe(v.array(dailyRow), v.nonEmpty()), meta: v.optional(v.array(meta)) }),
  events: v.object({ rows: v.array(eventRow), meta: v.optional(v.array(meta)) }),
  summary: v.object({ rows: v.array(summaryRow), meta: v.optional(v.array(meta)) }),
  status: v.object({ rows: statusRows, meta: v.optional(v.array(meta)) }),
  posts: v.object({ rows: v.array(postRow), meta: v.optional(v.array(meta)), windows: v.optional(v.record(v.string(), postWindow)) }),
};

type Rows = { [K in DataName]: v.InferOutput<typeof payloads[K]>['rows'] };
type LoadedByName = { [K in DataName]: {
  status: 'ok';
  data: Rows[K];
  meta?: Meta[];
} & (K extends 'posts' ? { windows?: Record<string, PostWindow> } : unknown) };
export type DataStore = { [K in DataName]: LoadedByName[K] | { status: 'idle' | 'loading' | 'error' } };
export type LoadState<K extends DataName> = DataStore[K];

const todaySchema = v.object({
  status: statusRows,
  daily: dailyRow,
  summary: v.array(summaryRow),
});
export type Today = v.InferOutput<typeof todaySchema>;

function parse<S extends v.GenericSchema>(name: string, schema: S, value: unknown): v.InferOutput<S> {
  const result = v.safeParse(schema, value, { abortEarly: true });
  if (result.success) return result.output;
  const issue = result.issues[0];
  const path = issue.path?.map(({ key }) => String(key)).join('.');
  throw new Error(`${name}${path ? '.' + path : ''}: ${issue.message}`);
}

export function parsePayload<K extends DataName>(name: K, value: unknown): LoadedByName[K] {
  const { rows, ...metadata } = parse(name, payloads[name], value);
  // The same key selects both the row schema and the return type.
  return { status: 'ok', data: rows, ...metadata } as LoadedByName[K];
}

export function readToday(): Today {
  const json = document.getElementById('dashboard-today')?.textContent;
  if (!json) throw new Error('找不到頁面的今日資料');
  return parse('today', todaySchema, JSON.parse(json));
}
