import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { loadPlugin, makeContainer } from './helpers.js';

const CATALOG = {
  name: 'X4 Wallpaper Store',
  wallpapers: [{
    id: 'wm-aurora-001',
    title: 'Aurora over Norway',
    author: 'Photo Author',
    license: 'CC BY-SA 4.0',
    attribution: '© Photo Author, CC BY-SA 4.0',
    category: 'landscape',
    bw: 'wallpapers/bw/wm-aurora-001.bmp',
    gray: 'wallpapers/gray/wm-aurora-001.bmp',
    thumb: 'wallpapers/thumbs/wm-aurora-001.png',
  }],
};

test('manifest satisfies the contract', async () => {
  const manifest = JSON.parse(await readFile(new URL('../plugin/manifest.json', import.meta.url), 'utf8'));
  assert.equal(typeof manifest.title, 'string');
  assert.ok(manifest.title.trim());
  assert.equal(manifest.mount, 'settings');
});

test('plugin.js declares an absolute http(s) catalog URL', async () => {
  const { source } = await loadPlugin();
  const m = source.match(/CATALOG_URL\s*=\s*'([^']+)'/);
  assert.ok(m, 'CATALOG_URL constant missing');
  assert.match(m[1], /^https?:\/\//);
});

test('render fetches the catalog through the relay and lists wallpapers', async () => {
  const relays = [];
  const api = {
    async relay(method, url, headers) {
      relays.push({ method, url, headers });
      return { status: 200, body: JSON.stringify(CATALOG), headers: [] };
    },
    async fetchToSd() { throw new Error('unexpected fetchToSd'); },
  };
  const { render } = await loadPlugin();
  const container = makeContainer();
  await render(container, api);

  assert.equal(relays.length, 1);
  assert.equal(relays[0].method, 'GET');
  assert.match(relays[0].url, /wallpapers\.json/);
  assert.match(container.innerHTML, /Aurora over Norway/);
  assert.match(container.innerHTML, /Photo Author/);
  assert.match(container.innerHTML, /CC BY-SA 4\.0/);
  assert.match(container.innerHTML, /wallpapers\/thumbs\/wm-aurora-001\.png/);
  assert.match(container.innerHTML, /data-id="wm-aurora-001" data-style="bw"/);
  assert.match(container.innerHTML, /data-id="wm-aurora-001" data-style="gray"/);
});

test('download sends the chosen variant to /.sleep/<id>.bmp and records state', async () => {
  const relays = [];
  const downloads = [];
  const storage = new Map();
  const api = {
    async relay(method, url) {
      relays.push({ method, url });
      return { status: 200, body: JSON.stringify(CATALOG), headers: [] };
    },
    async fetchToSd(url, dest, headers) {
      downloads.push({ url, dest, headers });
      return { status: 200, bytes: 1234 };
    },
  };
  const { render } = await loadPlugin({
    localStorage: {
      getItem: (k) => storage.get(k) ?? null,
      setItem: (k, v) => storage.set(k, v),
    },
  });
  const container = makeContainer();
  await render(container, api);
  const buttons = container.querySelectorAll('.wp-dl');

  const bw = buttons.find((b) => b.dataset.style === 'bw');
  await bw.onclick();

  assert.equal(downloads.length, 1);
  assert.equal(downloads[0].url, CATALOG.wallpapers[0].bw);
  assert.equal(downloads[0].dest, '/.sleep/wm-aurora-001.bmp');
  assert.equal(JSON.parse(storage.get('x4wallpaper.downloaded'))['wm-aurora-001'], 'bw');
  assert.match(container.innerHTML, /Saved \(1-bit\)/);

  const gray = buttons.find((b) => b.dataset.style === 'gray');
  await gray.onclick();
  assert.equal(downloads[1].url, CATALOG.wallpapers[0].gray);
  assert.equal(downloads[1].dest, '/.sleep/wm-aurora-001.bmp');
  assert.match(container.innerHTML, /Saved \(grayscale\)/);
});

test('catalog failure renders a status message without throwing', async () => {
  const { render } = await loadPlugin();
  const container = makeContainer();
  const api = {
    async relay() { throw new Error('network down'); },
    async fetchToSd() { throw new Error('unexpected'); },
  };
  await render(container, api);
  assert.match(container.querySelector('#wp-status').textContent, /Could not load/);
});
