// X4 Wallpaper Store — CrossPoint Settings plugin.
// Catalog URL: raw wallpapers.json in the x4-wallpapers repo.
// If the repo has a remote, derive it from `git remote get-url origin`
// (https://github.com/<owner>/x4-wallpapers.git ->
//  https://raw.githubusercontent.com/<owner>/x4-wallpapers/main/wallpapers.json).
// Update this constant before publishing if it was left as the fallback.
const CATALOG_URL = 'https://raw.githubusercontent.com/REPLACE-OWNER/x4-wallpapers/main/wallpapers.json';

CrossPoint.registerPlugin((container, api) => {
  const store = {
    wallpapers: [],
    downloaded: {}, // id -> 'bw' | 'gray'
  };

  function setStatus(text) {
    const node = container.querySelector('#wp-status');
    if (node) node.textContent = text;
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
  }

  async function init() {
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
