import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import { build } from 'esbuild';

const outdir = 'dashboard/.build';
const shared = {
  bundle: true,
  target: 'es2022',
  minify: true,
  legalComments: 'inline',
};

if (process.argv.includes('--fragment')) {
  const result = await build({ ...shared, entryPoints: ['dashboard/src/fragment.ts'], format: 'iife', write: false });
  const html = await readFile('dashboard/index.html', 'utf8');
  await mkdir(outdir, { recursive: true });
  await writeFile(`${outdir}/fragment.html`, html + '<script>\n' + result.outputFiles[0].text + '</script>\n');
} else {
  await build({
    ...shared,
    entryPoints: ['dashboard/src/dashboard.ts'],
    outfile: `${outdir}/assets/dashboard.js`,
    format: 'esm',
  });
  await Promise.all([
    build({ ...shared, entryPoints: ['dashboard/src/card-view.ts'], outfile: `${outdir}/assets/card-view.js`, format: 'iife' }),
    build({ ...shared, entryPoints: ['dashboard/src/card-preview.ts'], outfile: `${outdir}/card.js`, format: 'iife' }),
    copyFile('node_modules/d3/dist/d3.min.js', `${outdir}/assets/d3.min.js`),
    copyFile('node_modules/d3/LICENSE', `${outdir}/assets/d3-LICENSE.txt`),
    copyFile('node_modules/valibot/LICENSE.md', `${outdir}/assets/valibot-LICENSE.md`),
  ]);
}
