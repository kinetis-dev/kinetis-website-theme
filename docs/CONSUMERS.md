# Consumers

Every repository that builds with this theme pins one release URL in one
requirements file. A release reaches a property only through a one-line pin
bump PR there. Dependabot cannot bump URL requirements, so these are made by
hand or with `tools/bump_pin.py`.

| Repository | Pin location | Deploys to | Extras | Status |
|---|---|---|---|---|
| `kinetis-dev/kinetis` | `docs/requirements.txt` | `https://kinetis.dev/docs/` | none | adopts in phase 3 |
| `kinetis-dev/vector-dev` | `docs/requirements.txt` | `https://kinetis.dev/vector/docs/` | none | adopts in phase 2 |
| `kinetis-dev/kinetis-website` | `site/requirements.txt` | `https://kinetis.dev/` | `[blog,notfound]` | future, when `site/` exists (phase 5b) |

The pin line:

```
kinetis-website-theme @ https://github.com/kinetis-dev/kinetis-website-theme/releases/download/vX.Y.Z/kinetis_website_theme-X.Y.Z-py3-none-any.whl
```

## Bumping a consumer

From a checkout of the consumer:

```sh
python3 /path/to/kinetis-website-theme/tools/bump_pin.py docs/requirements.txt 0.2.0
```

It rewrites only the pin line, keeps any extras, and prints the diff. It
refuses a file with no pin line or more than one. Open the PR with that one
change. The consumer's CI builds with the new wheel and runs its URL-baseline
guard before merge, and merging to `main` redeploys that section.

For releases that change the navigation, bump in this order: the website
first, so a new nav target exists before the other sections link to it, then
kinetis, then vector-dev. The sections show different navbars until all
three are merged.
