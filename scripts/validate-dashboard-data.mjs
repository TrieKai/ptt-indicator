import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { dataNames, parsePayload } from '../dashboard/src/data.ts';

try {
  for (const name of dataNames) {
    const raw = await readFile(join(process.argv[2], name + '.json'), 'utf8');
    parsePayload(name, JSON.parse(raw));
  }
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
