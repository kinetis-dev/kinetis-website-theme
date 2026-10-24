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
kinetis-website-theme @ https://github.com/kinetis-dev/kinetis-website-theme/releases/download/v0.3.0/kinetis_website_theme-0.3.0-py3-none-any.whl
```

The website, which needs ABlog and the 404 page, adds the extras (pip
accepts extras on a direct-URL requirement):

```
kinetis-website-theme[blog,notfound] @ https://github.com/kinetis-dev/kinetis-website-theme/releases/download/v0.3.0/kinetis_website_theme-0.3.0-py3-none-any.whl
```

pip downloads only the theme from that URL and resolves its dependencies
(`pydata-sphinx-theme`, `sphinx`, the extras) from PyPI as usual, so no git
and no extra index is involved. Then, in `conf.py`:

```python
html_theme = "kinetis_website_theme"
```

That is all a consumer sets. The theme supplies the rest:

- The navbar: the horizontal Kinetis logo (`logo-h.svg`) linking to `https://kinetis.dev/`, the site
  navigation (Home `/`, Docs `/docs/`, Vector `/vector/`, Blog `/blog/`)
  with the current section marked, search and the light/dark switcher. It
  has no GitHub icon (`icon_links` is empty). The section is the item whose
  href is the longest prefix of the page's deployed path (Home only for the
  root itself), so every `/vector/docs/` page is Vector; ablog's root
  listing `/blog.html` is Blog by one exact rule, an href without its
  trailing slash plus `.html`.
- The primary sidebar shows the project's whole toctree with its captions, as
  Furo did. The secondary sidebar is "On this page".
- The footer: copyright, Docs, GitHub (`https://github.com/kinetis-dev`) and
  Packagist (`https://packagist.org/packages/kinetis/`). It is the same on
  every page, landing and 404 pages included.
- The kinetis.dev colours, the heading colours and full-width tables.
- The three `/assets/favicon.*` links. Leave `html_favicon` unset.
- `<title>` in Furo's format, `Page - Project` with the project name alone on
  the root page, so existing titles do not change.
- `<meta name="robots" content="noindex">` on `404`, on any page whose front
  matter sets `kinetis_noindex: true`, and on pages matching
  `kinetis_noindex_patterns`.
- ABlog styling hooks: post entries (`.ablog-post`) and ablog's sidebar
  templates on the theme's tokens, in light and dark. Nothing else is
  ablog-specific.

Defaults are merged into `html_theme_options` key by key, and only where the
consumer set nothing, so any single option can still be overridden.
`html_sidebars` is set only when the consumer left it empty.

### Configuration values

| Name | Default | Effect |
|---|---|---|
| `kinetis_noindex_patterns` | `[]` | `fnmatch` patterns on page names; matching pages get the noindex meta (and, with the pruner, leave the sitemap). |
| `kinetis_index_as_directory` | `False` | Canonical and `og:url` of `index` and `*/index` pages end at the directory (`https://kinetis.dev/blog/`, not `…/blog/index.html`); with the pruner on, so do their sitemap locs. An `og:url` set in front matter wins. |
| `kinetis_prune_sitemap` | `False` | After sphinx-sitemap writes its file, drop every noindex page from it. |

The docs consumers set none of them. With all three at their defaults, the
docs output does not change.

A page is noindex when its name is `404`, its front matter sets
`kinetis_noindex: true`, or it matches a `kinetis_noindex_patterns` pattern.
That one rule decides both the meta tag and the sitemap.

The sitemap pruner runs at `build-finished` with priority 600, after
sphinx-sitemap (500). It reads the file name from `sitemap_filename`, which
the pinned sphinx-sitemap 2.9.0 supports, and maps each loc back to its page
through `site_url` or `html_baseurl`. It needs
`sitemap_url_scheme = "{link}"` and the `html` builder. Without them, or
when the sitemap file is missing, it fails the build with a clear error.
At `builder-inited` it deletes an earlier build's sitemap from the output
directory. sphinx-sitemap leaves the old file in place when it collects no
pages, so this way a build without a sitemap of its own fails, rather than
pruning the old file a second time. The base is the one sphinx-sitemap 2.9.0
uses, `site_url` or else `html_baseurl`, taken exactly as given. Every loc
must map to a page of the build; one that maps to nothing (for example
because the base and the locs disagree about a trailing slash) is an error,
never a silent keep. Only the pruned `<url>` elements change; the declaration, the namespace and
every other element stay byte for byte. The noindex set is computed in the
main process from the environment (found documents, their metadata and the
patterns), never from per-page state, so `-j` builds prune the same pages.
The patterns alone decide pages that Sphinx or an extension generates, such
as ablog's listings and `search`.

The `index` rewrite of canonical and `og:url` is an `html-page-context`
handler with priority 800. That runs it after every handler at the default
500, sphinxext-opengraph's included, whatever order the extensions were set
up in.

### The website: landing pages, 404 and blog

Front matter keys the theme reads:

| Key | Effect |
|---|---|
| `kinetis_template: landing` | Render the page with `kinetis/landing.html`. |
| `kinetis_noindex: true` | Add the noindex meta (and prune the page from the sitemap). |

`kinetis/landing.html` keeps pydata's header, at the same default height as
on docs pages, with the brand, the site nav and the theme switcher. The page
body follows inside `<div class="kinetis-landing" data-pagefind-body>`,
within pydata's `<main id="main-content">`, which stays the page's only main
landmark. The page has no sidebars (the primary sidebar only carries the
navbar items on narrow screens), no article chrome and no prev/next. It ends
with pydata's footer and the shared `kinetis-footer`, exactly as docs pages
do. `<title>` is the page title verbatim, with no ` - Project` suffix. The favicons and the noindex meta are as on every page.
`kinetis-landing.css` is the website's `style.css` scoped to
`.kinetis-landing`, without its footer rules, and only landing pages link it.

The body is the old static page's `<body>` markup in a MyST `{raw} html`
block, with the JSON-LD `<script type="application/ld+json">` included.
Write the body's own `<main>` as a `<div>`, and leave its `<footer>` out:
the body must not carry a footer of its own, or the page shows two.

**The title.** A MyST front-matter `title:` with no `#` heading does not
become the Sphinx document title. It only lands in the page metadata, and
the page title stays `<no title>`. Give the title with docutils' `title`
directive instead. It sets the document title, renders no heading, and is
used verbatim in `<title>` and `og:title`:

````md
---
kinetis_template: landing
og:description: "Shown by link previews."
og:image:width: "1200"
og:image:height: "630"
myst:
  html_meta:
    description: "Shown by search engines."
    twitter:card: "summary_large_image"
    twitter:title: "Kinetis: A Complete PHP Framework, Built for Speed"
---

```{title} Kinetis: A Complete PHP Framework, Built for Speed
```

```{raw} html
<div class="wrap">…</div>
```
````

Per-page `og:*` values are sphinxext-opengraph front-matter fields. Other
`<meta>` tags, such as `description` and `twitter:*`, come from MyST's
`html_meta`. Don't put an `og:*` key in `html_meta` as well, or the tag is
emitted twice. Set `ogp_image_alt = False` when the page should have no
`og:image:alt`. With `kinetis_index_as_directory`, the root's canonical and
`og:url` are `https://kinetis.dev/` without any front matter.
`tests/sample-website/index.md` reproduces kinetis.dev's landing head this
way.

**404.** Write `404.md` with `orphan: true` and `kinetis_template: landing`,
and give it the full title (`Page not found — Kinetis`), since the landing
template adds no suffix. Enable `notfound.extension` with
`notfound_urls_prefix = "/"`. sphinx-notfound-page then renders `404.md`
through the landing template with every CSS, JS, logo and favicon link
absolute, so the page works for any missing URL. The theme ships no separate
404 template, and `404` is always noindex.

**ABlog.** With `blog_path = "blog"`, ablog 0.11 writes its own root listing
of all posts at `blog.html` (page name `blog`). A hand-written
`blog/index.md` becomes `/blog/` next to it. The listings are `blog/tag*`,
`blog/category*`, `blog/archive*`, `blog/author*`, `blog/language*`,
`blog/location*`, `blog/drafts` and one `blog/<year>.html` per year. The Atom
feed is `blog/atom.xml`, written when `blog_baseurl` is set. Mark the
listings noindex with `kinetis_noindex_patterns`, including
`blog/[0-9][0-9][0-9][0-9]`, and the pruner keeps them out of the sitemap.
`tests/sample-website/conf.py` is a working configuration.

## Development

```sh
python -m pip install build
python -m build --wheel
pip install "$(ls dist/*.whl)[blog,notfound]" -r tests/sample-site/requirements.txt \
  -r tests/sample-website/requirements.txt
sphinx-build -W --keep-going -b html tests/sample-site _build
sphinx-build -W --keep-going -b html tests/sample-website build/website
python tools/check_url_baseline.py check _build
python -m unittest discover -s tests -v
```

`tests/sample-site/` is a small docs project shaped like kinetis/docs.
`tests/test_sample_site.py` builds it three times, with `html_baseurl` set to
`/docs/`, `/vector/docs/` and `/`, and asserts on the HTML. The cases include
the active nav item, the footer links, the favicons, the title format, noindex
and a clean `-W` build. `tools/check_url_baseline.py` is the kinetis URL
guard, and the sample site's baseline is its self-test.

`tests/sample-website/` is shaped like kinetis.dev as a Sphinx project: the
landing and 404 page built from the website's own markup
(`tests/website-inputs/`), an ablog blog with two posts, directory URLs and
the sitemap pruner. `tests/test_sample_website.py` builds it serially and at
`-j 2`. It asserts on the landing head and body, the 404 page's links,
noindex on the listings, the feed and the exact sitemap.
`tests/test_landing_css.py` re-derives `kinetis-landing.css` from the
website's `style.css`. Screenshot goldens are described in
`tests/goldens/README.md`.

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
