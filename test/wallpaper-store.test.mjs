import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { loadPlugin, makeContainer } from './helpers.js';

const CATALOG = {
  name: 'Andrra',
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
  assert.match(container.innerHTML, /src="https:\/\/raw\.githubusercontent\.com\/[^"]+wallpapers\/thumbs\/wm-aurora-001\.png"/);
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
  const { render, source } = await loadPlugin({
    localStorage: {
      getItem: (k) => storage.get(k) ?? null,
      setItem: (k, v) => storage.set(k, v),
    },
  });
  const catalogUrl = source.match(/CATALOG_URL\s*=\s*'([^']+)'/)[1];
  const container = makeContainer();
  await render(container, api);
  const dl = container.querySelectorAll('.wp-dl');
  const styles = container.querySelectorAll('.wp-style');

  // Default selection is 1-bit; the Download button fetches it.
  await dl[0].onclick();

  assert.equal(downloads.length, 1);
  // Relative catalog paths resolve to absolute URLs against the catalog URL.
  assert.equal(downloads[0].url, new URL(CATALOG.wallpapers[0].bw, catalogUrl).href);
  assert.ok(downloads[0].url.startsWith('https://raw.githubusercontent.com/'));
  assert.equal(downloads[0].dest, '/.sleep/wm-aurora-001.bmp');
  assert.equal(JSON.parse(storage.get('x4wallpaper.downloaded'))['wm-aurora-001'], 'bw');
  assert.match(container.innerHTML, /Saved \(1-bit\)/);

  // Select Grayscale, then Download again — the gray variant is fetched.
  styles.find((b) => b.dataset.style === 'gray').onclick();
  await dl[0].onclick();
  assert.equal(downloads.length, 2);
  assert.equal(downloads[1].url, new URL(CATALOG.wallpapers[0].gray, catalogUrl).href);
  assert.ok(downloads[1].url.startsWith('https://raw.githubusercontent.com/'));
  assert.equal(downloads[1].dest, '/.sleep/wm-aurora-001.bmp');
  assert.match(container.innerHTML, /Saved \(grayscale\)/);
});

test('download rejects a wallpaper id that could escape /.sleep (path traversal)', async () => {
  const evilCatalog = {
    wallpapers: [{
      id: '../../evil',
      title: 'Evil',
      author: 'Author',
      license: 'MIT',
      bw: 'wallpapers/bw/evil.bmp',
      gray: 'wallpapers/gray/evil.bmp',
      thumb: 'thumb.png',
    }],
  };
  const downloads = [];
  const api = {
    async relay() { return { status: 200, body: JSON.stringify(evilCatalog), headers: [] }; },
    async fetchToSd(url, dest) { downloads.push({ url, dest }); return { status: 200 }; },
  };
  const { render } = await loadPlugin();
  const container = makeContainer();
  await render(container, api);
  await container.querySelectorAll('.wp-dl')[0].onclick();
  assert.equal(downloads.length, 0);
  assert.match(container.querySelector('#wp-status').textContent, /invalid wallpaper id/);
});

test('download creates /.sleep before fetching', async () => {
  const mkdirs = [];
  async function fetch(url, options = {}) {
    if (url === '/mkdir') {
      mkdirs.push(options.body || '');
      return { ok: true };
    }
    if (url.startsWith('/api/files')) return { ok: true, async json() { return []; } };
    throw new Error('unexpected fetch: ' + url);
  }
  const downloads = [];
  const api = {
    async relay() { return { status: 200, body: JSON.stringify(CATALOG), headers: [] }; },
    async fetchToSd(url, dest) { downloads.push({ url, dest }); return { status: 200 }; },
  };
  const { render } = await loadPlugin({ fetch });
  const container = makeContainer();
  await render(container, api);
  await container.querySelectorAll('.wp-dl')[0].onclick();

  assert.equal(mkdirs.length, 1);
  assert.match(mkdirs[0], /name=\.sleep/);
  assert.match(mkdirs[0], /path=%2F/);
  assert.equal(downloads.length, 1);
  assert.equal(downloads[0].dest, '/.sleep/wm-aurora-001.bmp');
});

test('download rejects absolute URLs from disallowed hosts or non-https protocols', async () => {
  const badCatalog = {
    wallpapers: [
      {
        id: 'evil-host',
        title: 'Evil Host',
        author: 'Author',
        license: 'MIT',
        bw: 'https://evil.example.com/payload.bmp',
        gray: 'https://evil.example.com/payload-gray.bmp',
        thumb: 'thumb.png',
      },
      {
        id: 'http-only',
        title: 'HTTP Only',
        author: 'Author',
        license: 'MIT',
        bw: 'http://raw.githubusercontent.com/x.bmp',
        gray: 'http://raw.githubusercontent.com/y.bmp',
        thumb: 'thumb.png',
      },
    ],
  };
  const downloads = [];
  const api = {
    async relay() { return { status: 200, body: JSON.stringify(badCatalog), headers: [] }; },
    async fetchToSd(url, dest) { downloads.push({ url, dest }); return { status: 200 }; },
  };
  const { render } = await loadPlugin();
  const container = makeContainer();
  await render(container, api);
  const buttons = container.querySelectorAll('.wp-dl');

  await buttons[0].onclick(); // evil.example.com (bw default)
  assert.equal(downloads.length, 0);
  assert.match(container.querySelector('#wp-status').textContent, /host not allowed/);

  await buttons[1].onclick(); // http://raw.githubusercontent.com (bw default)
  assert.equal(downloads.length, 0);
  assert.match(container.querySelector('#wp-status').textContent, /host not allowed/);
});

test('download rejects a malformed artifact URL without throwing', async () => {
  const badCatalog = {
    wallpapers: [{
      id: 'bad-url',
      title: 'Bad URL',
      author: 'Author',
      license: 'MIT',
      bw: 'https://exa mple.com/payload.bmp', // space in host -> new URL throws
      gray: 'https://exa mple.com/payload-gray.bmp',
      thumb: 'thumb.png',
    }],
  };
  const downloads = [];
  const api = {
    async relay() { return { status: 200, body: JSON.stringify(badCatalog), headers: [] }; },
    async fetchToSd(url, dest) { downloads.push({ url, dest }); return { status: 200 }; },
  };
  const { render } = await loadPlugin();
  const container = makeContainer();
  await render(container, api);
  await container.querySelectorAll('.wp-dl')[0].onclick();
  assert.equal(downloads.length, 0);
  assert.match(container.querySelector('#wp-status').textContent, /invalid download URL/);
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

test('clear sleep folder lists /.sleep and deletes every file', async () => {
  const deletes = [];
  async function fetch(url, options = {}) {
    if (url.startsWith('/api/files')) {
      return { ok: true, async json() { return [
        { name: 'wm-aurora-001.bmp', isDirectory: false },
        { name: 'notes.txt', isDirectory: false },
      ]; } };
    }
    if (url === '/delete') {
      deletes.push(new URLSearchParams(options.body).get('path'));
      return { ok: true, async json() { return {}; } };
    }
    throw new Error('unexpected fetch: ' + url);
  }
  const storage = new Map();
  storage.set('x4wallpaper.downloaded', JSON.stringify({ 'wm-aurora-001': 'bw' }));
  const api = {
    async relay() { return { status: 200, body: JSON.stringify(CATALOG), headers: [] }; },
    async fetchToSd() { throw new Error('unexpected'); },
  };
  const { render } = await loadPlugin({
    fetch,
    localStorage: {
      getItem: (k) => storage.get(k) ?? null,
      setItem: (k, v) => storage.set(k, v),
    },
  });
  const container = makeContainer();
  // Register the fixed elements BEFORE render so render()'s wiring finds them
  // (render() sets innerHTML, then querySelector('#wp-clear')/('#wp-status')).
  container.elements.set('#wp-clear', { onclick: null });
  container.elements.set('#wp-status', { textContent: '' });
  await render(container, api);
  container.querySelector('#wp-clear').onclick();
  await new Promise((r) => setTimeout(r, 0)); // let the async clear finish
  assert.deepEqual(deletes, ['/.sleep/wm-aurora-001.bmp', '/.sleep/notes.txt']);
  assert.match(container.querySelector('#wp-status').textContent, /Cleared 2 file/);
  assert.deepEqual(JSON.parse(storage.get('x4wallpaper.downloaded')), {});
});

test('catalog fields with HTML are escaped in rendered cards', async () => {
  const xssCatalog = {
    wallpapers: [{
      id: 'xss-1',
      title: '<img src=x onerror=alert(1)>',
      author: 'Author',
      license: 'MIT',
      bw: 'bw.bmp',
      gray: 'gray.bmp',
      thumb: 'thumb.png',
    }],
  };
  const api = {
    async relay() { return { status: 200, body: JSON.stringify(xssCatalog), headers: [] }; },
    async fetchToSd() { throw new Error('unexpected'); },
  };
  const { render } = await loadPlugin();
  const container = makeContainer();
  await render(container, api);
  assert.match(container.innerHTML, /&lt;img src=x onerror=alert\(1\)&gt;/);
  assert.doesNotMatch(container.innerHTML, /<img src=x onerror=alert\(1\)>/);
});

test('device.json declares a valid on-device screen', async () => {
  const d = JSON.parse(await readFile(new URL('../plugin/device.json', import.meta.url), 'utf8'));
  assert.equal(d.title, 'Andrra');
  assert.equal(d.version, '1.0.0');
  assert.equal(d.browse.items, 'wallpapers');
  assert.equal(d.browse.fields.id, 'id');
  assert.match(d.browse.url, /wallpapers\.json$/);
  assert.equal(d.download.dest_dir, '/.sleep');
  assert.match(d.download.url, /\{id\}/);
  assert.match(d.download.filename, /\{id\}\.bmp$/);
});

test('store-catalog.json satisfies the plugin-store catalog spec', async () => {
  const catalog = JSON.parse(await readFile(new URL('../store-catalog.json', import.meta.url), 'utf8'));
  const entry = catalog.plugins.find((p) => p.name === 'andrra');
  assert.ok(entry, 'andrra entry missing');
  assert.ok(entry.base.endsWith('/plugin/'));
  assert.ok(entry.files.includes('manifest.json'));
  assert.ok(entry.files.includes('plugin.js'));
  assert.match(entry.base, /^https:\/\/raw\.githubusercontent\.com\//);
});
