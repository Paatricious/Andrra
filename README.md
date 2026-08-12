# X4 Wallpaper Store

Open-license wallpapers for the Xteink X4 Pro (CrossPoint firmware) sleep
screen, delivered by a CrossPoint browser plugin.

## Install (plugin)

**Via Plugin Store:** add the store catalog URL (this repo's
`store-catalog.json`) in the reader web UI → Settings → Plugin Store, then
install "Wallpaper Store".

**By hand:** copy the `plugin/` folder to `/.crosspoint/plugins/wallpaper-store/`
on the SD card (or `/plugins/wallpaper-store/`). Reconnect to the device web UI.

## Use

1. Open Settings → **Wallpaper Store** in the device web UI.
2. Pick a wallpaper, choose **1-bit** or **Grayscale**, tap the button.
   The device downloads it to `/.sleep/<id>.bmp`.
3. On the reader: **Settings → Sleep screen → Custom** (or **Cover + Custom**).
   Each sleep shows a random wallpaper from `/.sleep/`. A `sleep.bmp` at the
   SD root overrides the folder.

## How the pipeline works

A scheduled GitHub Action runs `scripts/convert.py`:

- `pull` — fetches candidate images from open-license sources (Wikimedia
  Commons featured pictures) and merges new entries into `sources.json`.
- `convert` — for each entry without artifacts, center-crops to 480×800 and
  writes a 1-bit dithered BMP (`wallpapers/bw/`), an 8-bit grayscale BMP
  (`wallpapers/gray/`), and a thumbnail (`wallpapers/thumbs/`); regenerates
  `wallpapers.json` and `THIRD_PARTY.md`.
- Contributors submit wallpapers as PRs adding one entry to `sources.json`
  (see `docs/CONTRIBUTING.md`). The pipeline converts on merge.

## Licensing

Only open-license images (CC0 / CC BY / CC BY-SA / public domain) are
accepted — enforced by the pipeline's license allowlist. Every wallpaper
carries source, license, and attribution in `wallpapers.json` and
`THIRD_PARTY.md`. The plugin shows author and license on each card.
