import { draw, fontsReady, model } from './card.ts';
import { readToday } from './data.ts';

async function preview() {
  const today = readToday();
  const card = model(today.status, today.daily, today.summary);
  const canvas = document.getElementById('c');
  if (!card || !(canvas instanceof HTMLCanvasElement)) throw new Error('無法產生今日圖卡');
  await fontsReady(card);
  draw(canvas, card, 1);
  document.title = 'ready';
}

void preview();
