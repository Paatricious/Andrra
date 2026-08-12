# Andrra

*Andërra për ekranin e fjetur* — "dreams for your sleeping screen."

**Andrra** (Gheg Albanian, pronounced **AHN-drah**) means **"the dream."** It's a
wallpaper store for CrossPoint e-readers (Xteink X4 Pro): a browser plugin
that downloads open-license art into your device's `/.sleep/` folder, where
the firmware rotates it every time the reader drifts off.

## Install (plugin)

**Via Plugin Store:** add this repo's store catalog URL
(`https://raw.githubusercontent.com/Paatricious/Andrra/main/store-catalog.json`)
in the reader web UI → Settings → Plugin Store, then install **Andrra**.

**By hand:** copy the `plugin/` folder to `/.crosspoint/plugins/andrra/`
on the SD card (or `/plugins/andrra/`). Reconnect to the device web UI.

## Use

1. Open Settings → **Andrra** in the device web UI.
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

Two layers:

- **The code** (plugin, pipeline, tests) is **MIT** — see `LICENSE`.
- **The wallpapers are NOT covered by the repo license.** Each image keeps
  its own open license (CC0 / CC BY / CC BY-SA / public domain), enforced by
  the pipeline's allowlist and recorded per-image with source and
  attribution in `wallpapers.json` and `THIRD_PARTY.md`. The plugin shows
  author and license on each card.
