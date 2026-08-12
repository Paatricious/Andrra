import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const root = new URL('../', import.meta.url);

export async function loadPlugin(globals = {}) {
  let render;
  const context = vm.createContext({
    CrossPoint: {
      registerPlugin(fn) { render = fn; },
    },
    URL,
    URLSearchParams,
    TextEncoder,
    TextDecoder,
    Uint8Array,
    DataView,
    Map,
    Date,
    Math,
    Array,
    String,
    Number,
    Object,
    Promise,
    encodeURIComponent,
    decodeURIComponent,
    atob,
    btoa,
    setTimeout,
    console,
    ...globals,
  });
  const source = await readFile(new URL('plugin/plugin.js', root), 'utf8');
  vm.runInContext(source, context, { filename: 'plugin.js' });
  assert.equal(typeof render, 'function', 'plugin.js should register a render function');
  return { render, context, source };
}

// A container mock with an element registry so tests can wire and click
// buttons the way the plugin does against a real DOM container.
export function makeContainer() {
  const registry = new Map();
  let dlButtons = [];
  const container = {
    innerHTML: '',
    elements: {
      set(id, el) { registry.set(id, el); },
      get(id) { return registry.get(id) || null; },
    },
    querySelector(sel) { return registry.get(sel) || null; },
    querySelectorAll(sel) {
      if (sel !== '.wp-dl') return [];
      // Parse the current innerHTML into live button objects. Cache by
      // id:style pair so render()'s wiring and the test's clicks hit the
      // same objects even after a re-render.
      const re = /data-id="([^"]+)" data-style="([^"]+)"/g;
      let m;
      const fresh = [];
      while ((m = re.exec(this.innerHTML))) {
        let btn = dlButtons.find((b) => b.dataset.id === m[1] && b.dataset.style === m[2]);
        if (!btn) btn = { dataset: { id: m[1], style: m[2] }, onclick: null };
        fresh.push(btn);
      }
      dlButtons = fresh;
      return dlButtons;
    },
  };
  return container;
}
