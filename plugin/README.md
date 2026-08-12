# Andrra plugin

*Andërra për ekranin e fjetur* — "dreams for your sleeping screen."
**Andrra** (Gheg Albanian, pronounced **AHN-drah**) means **"the dream."**

Adds an **Andrra** card to the device web UI's Settings page.

- Fetches `wallpapers.json` from the Andrra repo (see `CATALOG_URL` in
  `plugin.js` — update it if you fork the store).
- Lists wallpapers with thumbnails, author, and license.
- "1-bit" / "Grayscale" downloads the BMP to `/.sleep/<id>.bmp` via the
  device relay (`api.fetchToSd`).
- "Clear sleep folder" deletes everything in `/.sleep/`.

Requires the sleep screen to be set to **Custom** (or **Cover + Custom**) in
reader Settings for wallpapers to appear.

## On the device

Andrra also has an on-device screen (via `device.json`): open **Plugins →
Andrra** on the reader itself, browse the wallpaper list, and tap one to
download it to `/.sleep/` — no web UI needed. The on-device list shows
title/author and downloads the 1-bit variant (the device screen is
declarative and cannot render thumbnails or a variant choice).
