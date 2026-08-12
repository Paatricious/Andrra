// X4 Wallpaper Store — CrossPoint Settings plugin.
// Catalog URL: raw wallpapers.json in the x4-wallpapers repo.
// If the repo has a remote, derive it from `git remote get-url origin`
// (https://github.com/<owner>/x4-wallpapers.git ->
//  https://raw.githubusercontent.com/<owner>/x4-wallpapers/main/wallpapers.json).
// Update this constant before publishing if it was left as the fallback.
const CATALOG_URL = 'https://raw.githubusercontent.com/REPLACE-OWNER/x4-wallpapers/main/wallpapers.json';

// Only these hosts may serve wallpaper downloads. The catalog comes from
// the x4-wallpapers repo; anything else is rejected (malicious catalog).
const ALLOWED_DOWNLOAD_HOSTS = ['raw.githubusercontent.com'];
const ID_RE = /^[a-z0-9-]+$/;

CrossPoint.registerPlugin((container, api) => {
  const DOWNLOAD_KEY = 'x4wallpaper.downloaded';

  const store = {
    wallpapers: [],
    downloaded: {}, // id -> 'bw' | 'gray'
  };

  function setStatus(text) {
    const node = container.querySelector('#wp-status');
    if (node) node.textContent = text;
  }

  function loadDownloaded() {
    try {
      store.downloaded = JSON.parse(localStorage.getItem(DOWNLOAD_KEY) || '{}');
    } catch (e) {
      store.downloaded = {};
    }
  }

  function saveDownloaded() {
    localStorage.setItem(DOWNLOAD_KEY, JSON.stringify(store.downloaded));
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function resolveArtifactUrl(path) {
    // Catalog paths are relative to the catalog file; resolve against it.
    return new URL(path, CATALOG_URL).href;
  }

  async function download(id, style) {
    const wp = store.wallpapers.find((w) => w.id === id);
    if (!wp) return;
    if (!ID_RE.test(id)) {
      setStatus('Download failed: invalid wallpaper id.');
      return;
    }
    let u, url;
    try {
      url = resolveArtifactUrl(style === 'gray' ? wp.gray : wp.bw);
      u = new URL(url);
    } catch (e) {
      setStatus('Download failed: invalid download URL.');
      return;
    }
    if (u.protocol !== 'https:' || !ALLOWED_DOWNLOAD_HOSTS.includes(u.hostname)) {
      setStatus('Download failed: download host not allowed.');
      return;
    }
    setStatus('Downloading ' + wp.title + '…');
    try {
      const res = await api.fetchToSd(url, '/.sleep/' + id + '.bmp');
      if (res && res.status && res.status >= 400) throw new Error('status ' + res.status);
      store.downloaded[id] = style;
      saveDownloaded();
      render();
      setStatus('Saved ' + wp.title + ' — it will appear on the sleep screen.');
    } catch (err) {
      setStatus('Download failed: ' + err.message);
    }
  }

  async function clearSleepFolder() {
    setStatus('Clearing sleep folder…');
    try {
      const res = await fetch('/api/files?path=/.sleep');
      const files = await res.json();
      let removed = 0;
      for (const f of files) {
        if (f.isDirectory) continue;
        await fetch('/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: 'path=' + encodeURIComponent('/.sleep/' + f.name),
        });
        removed += 1;
      }
      store.downloaded = {};
      saveDownloaded();
      render();
      setStatus('Cleared ' + removed + ' file(s) from the sleep folder.');
    } catch (err) {
      setStatus('Clear failed: ' + err.message);
    }
  }

  function card(wp) {
    const saved = store.downloaded[wp.id];
    const label = saved ? 'Saved (' + (saved === 'gray' ? 'grayscale' : '1-bit') + ')' : 'Download';
    return '<div class="wp-card">'
      + '<img class="wp-thumb" src="' + escapeHtml(wp.thumb) + '" alt="' + escapeHtml(wp.title) + '">'
      + '<div class="wp-meta">'
      + '<div class="wp-title">' + escapeHtml(wp.title) + '</div>'
      + '<div class="wp-author">' + escapeHtml(wp.author) + ' · ' + escapeHtml(wp.license) + '</div>'
      + '<div class="wp-actions">'
      + '<button class="wp-dl" data-id="' + escapeHtml(wp.id) + '" data-style="bw">1-bit</button>'
      + '<button class="wp-dl" data-id="' + escapeHtml(wp.id) + '" data-style="gray">Grayscale</button>'
      + '<span class="wp-saved">' + label + '</span>'
      + '</div></div></div>';
  }

  function render() {
    container.innerHTML =
      '<div class="wp-store">'
      + '<div id="wp-status"></div>'
      + '<div id="wp-list">' + store.wallpapers.map(card).join('') + '</div>'
      + '<button id="wp-clear">Clear sleep folder</button>'
      + '<p class="wp-hint">Tip: set Settings → Sleep screen → Custom to see wallpapers.</p>'
      + '</div>';
    container.querySelectorAll('.wp-dl').forEach((btn) => {
      btn.onclick = () => download(btn.dataset.id, btn.dataset.style);
    });
    const clearBtn = container.querySelector('#wp-clear');
    if (clearBtn) clearBtn.onclick = clearSleepFolder;
  }

  async function init() {
    loadDownloaded();
    render();
    try {
      const res = await api.relay('GET', CATALOG_URL);
      const data = JSON.parse(res.body);
      store.wallpapers = Array.isArray(data.wallpapers) ? data.wallpapers : [];
      render();
    } catch (err) {
      setStatus('Could not load the wallpaper catalog: ' + err.message);
    }
  }

  return init();
});
