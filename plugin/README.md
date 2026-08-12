# Wallpaper Store plugin

Adds a **Wallpaper Store** card to the device web UI's Settings page.

- Fetches `wallpapers.json` from the x4-wallpapers repo (see
  `CATALOG_URL` in `plugin.js` — update it after moving to your own fork).
- Lists wallpapers with thumbnails, author, and license.
- "1-bit" / "Grayscale" downloads the BMP to `/.sleep/<id>.bmp` via the
  device relay (`api.fetchToSd`).
- "Clear sleep folder" deletes everything in `/.sleep/`.

Requires the sleep screen to be set to **Custom** (or **Cover + Custom**) in
reader Settings for wallpapers to appear.
