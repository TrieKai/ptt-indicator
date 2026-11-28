import { readToday } from './data.ts';
import { createDashboard } from './runtime.ts';
import { registerDashboard } from './view.ts';

const { dash, charts } = createDashboard(readToday());
registerDashboard(dash, charts);
