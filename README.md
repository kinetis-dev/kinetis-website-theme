# kinetis-website-theme

The shared Sphinx theme for the kinetis.dev properties: the website at `/`,
the Kinetis docs at `/docs/` and the Kinetis Vector docs at `/vector/docs/`.
It inherits [pydata-sphinx-theme](https://pydata-sphinx-theme.readthedocs.io/)
and keeps the look and the frozen head metadata of the Furo-era docs, while
adding a navbar and footer that all three properties share.

- Distribution `kinetis-website-theme`; import and theme name `kinetis_website_theme`.
- Released as a wheel on this repository's GitHub releases, not on PyPI.
- Requires Python 3.11+ and Sphinx 8 (`sphinx>=8.0,<9`). pydata-sphinx-theme
  is pinned exactly (`==0.23.0`, which itself needs Sphinx 8.2 or later).

## Usage

Pin the release in the consumer's `requirements.txt`, replacing `furo`:

```
kinetis-website-theme @ https://github.com/kinetis-dev/kinetis-website-theme/releases/download/v0.1.1/kinetis_website_theme-0.1.1-py3-none-any.whl
```

The website, which needs ABlog and the 404 page, adds the extras:

```
kinetis-website-theme[blog,notfound] @ https://github.com/kinetis-dev/kinetis-website-theme/releases/download/v0.1.1/kinetis_website_theme-0.1.1-py3-none-any.whl
```

pip downloads only the theme from that URL and resolves its dependencies
(`pydata-sphinx-theme`, `sphinx`, the extras) from PyPI as usual, so no git
and no extra index is involved. Then, in `conf.py`:

```python
html_theme = "kinetis_website_theme"
```

That is all a consumer sets. The theme supplies the rest:

- The navbar: the horizontal Kinetis logo (`logo-h.svg`) linking to `https://kinetis.dev/`, the site
  navigation (Home, Docs, Vector) with the current section marked, search
  and the light/dark switcher. It has no GitHub icon (`icon_links` is empty).
- The primary sidebar shows the project's whole toctree with its captions, as
  Furo did. The secondary sidebar is "On this page".
- The footer: copyright, Docs, GitHub (`https://github.com/kinetis-dev`) and
  Packagist (`https://packagist.org/packages/kinetis/`).
- The kinetis.dev colours, the heading colours and full-width tables.
- The three `/assets/favicon.*` links. Leave `html_favicon` unset.
- `<title>` in Furo's format, `Page - Project` with the project name alone on
  the root page, so existing titles do not change.
- `<meta name="robots" content="noindex">` on `404` and on any page whose front
  matter sets `kinetis_noindex: true`.

Defaults are merged into `html_theme_options` key by key, and only where the
consumer set nothing, so any single option can still be overridden.
`html_sidebars` is set only when the consumer left it empty.

### Configuration values

| Name | Default | Effect |
|---|---|---|
| `kinetis_noindex_patterns` | `[]` | `fnmatch` patterns on docnames; matching pages get the noindex meta. |
| `kinetis_index_as_directory` | `False` | Reserved for v0.2.0 (directory URLs for `index` pages); no effect yet. |
| `kinetis_prune_sitemap` | `False` | Reserved for v0.2.0 (drop noindex pages from the sitemap); no effect yet. |

## Development

```sh
python -m pip install build
python -m build --wheel
pip install "$(ls dist/*.whl)[blog,notfound]" -r tests/sample-site/requirements.txt
sphinx-build -W --keep-going -b html tests/sample-site _build
python tools/check_url_baseline.py check _build
python -m unittest discover -s tests -v
```

`tests/sample-site/` is a small docs project shaped like kinetis/docs.
`tests/test_sample_site.py` builds it three times, with `html_baseurl` set to
`/docs/`, `/vector/docs/` and `/`, and asserts on the HTML. The cases include
the active nav item, the footer links, the favicons, the title format, noindex
and a clean `-W` build. `tools/check_url_baseline.py` is the kinetis URL
guard, and the sample site's baseline is its self-test. Screenshot goldens are
described in `tests/goldens/README.md`.

## Releasing

1. Merge the release PR to `main`. It bumps `version` in `pyproject.toml` and
   `__version__` in `kinetis_website_theme/__init__.py`, and adds the
   `CHANGELOG.md` entry.
2. Tag the merge commit and push the tag:
   ```sh
   git tag v0.1.0 && git push origin v0.1.0
   ```
3. `.github/workflows/release.yml` asserts that the tag equals the
   `pyproject.toml` version. It then runs the tests, builds the wheel and
   sdist, and creates the GitHub release with generated notes. Finally, in a
   clean `python:3.12-slim` without git, it installs the release URL and
   imports the package.
4. Bump each consumer as described in `docs/CONSUMERS.md`.

A release is never edited after the fact. If an asset is wrong, release a new
patch version: consumers pin the asset URL, so replacing the file under it
would silently change their builds. The workflow refuses to run for a tag
that already has a release.

## Versioning

Semantic versioning. Navigation changes and pydata-sphinx-theme bumps are
minor releases. Removing a template, component, option or CSS variable is
major. See `CHANGELOG.md`.

## License

MIT, see `LICENSE`.
