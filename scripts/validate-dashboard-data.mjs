import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { dataNames, parsePayload } from '../dashboard/src/data.ts';

try {
  let daily;
  let archive;
  for (const name of dataNames) {
    const raw = await readFile(join(process.argv[2], name + '.json'), 'utf8');
    const parsed = parsePayload(name, JSON.parse(raw));
    if (name === 'daily') daily = parsed.data;
    if (name === 'post_days') archive = parsed;
  }

  const { trading_days: days, latest_window: latest, data: posts } = archive;
  const offset = days.indexOf(daily[0].date);
  if (offset < 4 || days.length !== offset + daily.length || daily.some((row, i) => row.date !== days[offset + i]) ||
      days.some((day, i) => i > 0 && day <= days[i - 1]) || latest.start !== days.at(-5) || latest.end <= days.at(-1)) {
    throw new Error('post_days: 交易日和文章區間與每日資料不符');
  }
  const calendar = new Set(days);
  const counts = new Map();
  const seen = new Set();
  for (const post of posts) {
    const day = post.event.slice(4);
    const unique = post.event + ',' + post.signal + ',' + post.url;
    if (!post.event.startsWith('day-') || !calendar.has(day) || !['creative', 'loss'].includes(post.signal) || post.pending || seen.has(unique)) {
      throw new Error('post_days: 逐日文章有重複或無法計入 ' + post.event);
    }
    seen.add(unique);
    const key = day + ',' + post.signal;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  for (const [i, row] of daily.entries()) {
    const dates = days.slice(offset + i - 4, offset + i + 1);
    for (const [signal, expected] of [['creative', row.c5], ['loss', row.l5]]) {
      const total = dates.reduce((n, day) => n + (counts.get(day + ',' + signal) ?? 0), 0);
      if (total !== expected) throw new Error(`post_days: ${row.date} 的 ${signal} 文章有 ${total} 篇，每日資料是 ${expected} 篇`);
    }
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
