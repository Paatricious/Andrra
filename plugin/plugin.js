// X4 Wallpaper Store — CrossPoint Settings plugin.
// Catalog URL: raw wallpapers.json in the x4-wallpapers repo.
// If the repo has a remote, derive it from `git remote get-url origin`
// (https://github.com/<owner>/x4-wallpapers.git ->
//  https://raw.githubusercontent.com/<owner>/x4-wallpapers/main/wallpapers.json).
// Update this constant before publishing if it was left as the fallback.
const CATALOG_URL = 'https://raw.githubusercontent.com/REPLACE-OWNER/x4-wallpapers/main/wallpapers.json';

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

  async function download(id, style) {
    const wp = store.wallpapers.find((w) => w.id === id);
    if (!wp) return;
    const url = style === 'gray' ? wp.gray : wp.bw;
    setStatus('Downloading ' + wp.title + '…');
    try {
      const res = await api.fetchToSd(url, '/.sleep/' + id + '.bmp');
      if (res && res.status && res.status >= 400) throw new Error('status ' + res.status);
      store.downloaded[id] = style;
      saveDownloaded();
      setStatus('Saved ' + wp.title + ' — it will appear on the sleep screen.');
      render();
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
      setStatus('Cleared ' + removed + ' file(s) from the sleep folder.');
      render();
    } catch (err) {
      setStatus('Clear failed: ' + err.message);
    }
  }

  function card(wp) {
    const saved = store.downloaded[wp.id];
    const label = saved ? 'Saved (' + (saved === 'gray' ? 'grayscale' : '1-bit') + ')' : 'Download';
    return '<div class="wp-card">'
      + '<img class="wp-thumb" src="' + wp.thumb + '" alt="' + wp.title + '">'
      + '<div class="wp-meta">'
      + '<div class="wp-title">' + wp.title + '</div>'
      + '<div class="wp-author">' + wp.author + ' · ' + wp.license + '</div>'
      + '<div class="wp-actions">'
      + '<button class="wp-dl" data-id="' + wp.id + '" data-style="bw">1-bit</button>'
      + '<button class="wp-dl" data-id="' + wp.id + '" data-style="gray">Grayscale</button>'
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
