# Contributing wallpapers

Add one entry to `sources.json` in a PR. The pipeline validates and converts
it on merge — you don't need to run anything locally.

```jsonc
{
  "id": "my-wallpaper",              // lowercase letters, digits, hyphens
  "title": "My Wallpaper",
  "author": "Artist or Photographer",
  "license": "CC BY-SA 4.0",         // CC0 | CC BY | CC BY-SA | CC BY 3.0 | CC BY-SA 3.0 | CC BY 4.0 | CC BY-SA 4.0 | Public Domain | Public domain
  "attribution": "© Artist, CC BY-SA 4.0",  // required for all entries
  "category": "landscape",           // optional, default "general"
  "source": "https://…/page",        // where the image came from (for attribution)
  "source_url": "https://…/image.jpg" // direct image URL
}
```

The CI run fails (and the PR is blocked) if the license is not in the
allowlist or attribution is missing. Only open-licensed images are accepted.
