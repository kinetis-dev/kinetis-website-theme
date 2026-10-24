# Changelog

All notable changes to this theme. Versions follow semantic versioning: nav
changes and pydata-sphinx-theme bumps are minor, template or variable
removals are major.

## 0.3.0

The navigation gains the Vector landing page and the blog, and every page,
landing and 404 pages included, now has the same header and the same
footer. Minor under the rule above: the navigation changes.

**Consumer impact:** landing pages now render pydata's footer with the
theme's `kinetis-footer`. A landing page body (`kinetis_template: landing`,
404 included) that still carries its own `<footer>` now shows two footers.
Remove the body's footer when bumping to 0.3.0. The website removes its
three (`/`, `/404` and `/vector/`) in the same PR that bumps its pin.

Added:

- A Blog nav item, `/blog/`. Every `/blog/...` page is Blog, and so is
  ablog's root listing `/blog.html`, by one exact rule: a path equal to an
  item's href without its trailing slash plus `.html`. It is no fuzzy
  match, so `/blogger.html` and `/docs-old/x.html` belong to no item.

Changed:

- The Vector nav item links to the Vector landing page, `/vector/` (was
  `/vector/docs/`). Every `/vector/docs/...` page stays Vector by the
  longest-prefix rule.
- `kinetis/landing.html` renders pydata's header at its default height, as
  on docs pages: the `--pst-header-height: 3rem` override is gone.
- `kinetis/landing.html` keeps pydata's footer, with
  `footer_start: ["kinetis-footer"]`, so landing and 404 pages show the same
  footer as docs pages. `kinetis-footer.html` is unchanged. Landing pages
  still have no article footer (prev/next).
- `kinetis-landing.css` drops the website's `footer` rules and their
  heading comment; the footer takes pydata's footer styling.
- `tests/sample-website/`'s landing and 404 bodies no longer carry a
  `<footer>`; the test fixtures in `tests/website-inputs/` are unchanged.

## 0.2.0

What the website needs to become a Sphinx project: a landing template, a
404 page that works from any URL depth, directory URLs for `index` pages,
and noindex listings pruned from the sitemap. Docs consumers set none of the
new options, so their pages change only as listed under "Changed".

Added:

- `kinetis/landing.html`, selected by front matter `kinetis_template: landing`.
  pydata's header is rendered as a 3rem bar, followed by the page body inside
  `<div class="kinetis-landing" data-pagefind-body>` in pydata's single
  `<main>` landmark. The page has no sidebars, article chrome, prev/next or
  pydata footer, and its `<title>` is the page title with no suffix.
- `kinetis-landing.css`: the website's `style.css` scoped mechanically to
  `.kinetis-landing`, with dark mode keyed off `html[data-theme="dark"]` and
  the logo url at the bundled `logo.svg`. Only landing pages link it.
- 404 support: a `404.md` with `kinetis_template: landing`, rendered by
  sphinx-notfound-page with `notfound_urls_prefix = "/"`, gets absolute links
  to every asset. No separate template.
- `kinetis_index_as_directory`: canonical and `og:url` of `index` and
  `*/index` pages end at the directory. An `og:url` in front matter wins. The
  handler runs at priority 800, after sphinxext-opengraph.
- `kinetis_prune_sitemap`: a `build-finished` handler at priority 600, after
  sphinx-sitemap, drops noindex pages from `sitemap_filename` and, with
  `kinetis_index_as_directory`, rewrites `index` locs. It needs
  `sitemap_url_scheme = "{link}"`. It fails the build clearly when this
  build wrote no sitemap (an earlier build's file is deleted at
  `builder-inited`, so it is never pruned twice) and when a loc maps to no
  page of the build. The noindex set comes from the environment, so `-j`
  builds prune the same pages.
- ABlog hooks in `kinetis.css`: `.ablog-post` entries and ablog's sidebar
  templates, on the theme's tokens.
- `tests/sample-website/`, a kinetis.dev-shaped project with landing, 404,
  blog and pruned sitemap, built and asserted on in CI. The goldens harness
  covers it too: landing, 404 (from a nested missing URL) and a blog post,
  light and dark.

Changed:

- The header has no GitHub icon: `icon_links` defaults to `[]`, and
  `navbar-icon-links` is gone from `navbar_end`. The footer keeps GitHub
  (`https://github.com/kinetis-dev`).
- The footer's Packagist link is `https://packagist.org/packages/kinetis/`, the
  vendor page (was `…/kinetis/framework`).
- `kinetis.css` gains the ABlog rules, so its `?v=` checksum changes on every
  page. Docs pages have no ABlog markup, so they render the same.

## 0.1.1

One main landmark per page. This is a patch release even though it removes an
attribute, because no released consumer depends on it: neither kinetis nor
vector-dev has integrated 0.1.0.

- `role="main"` is removed from `<article class="bd-article">`. This reverses
  the 0.1.0 "restored on the article" entry. pydata's
  `<main id="main-content" role="main">` is now the page's single main
  landmark, and the article stays the `data-pagefind-body`.
- The `kinetis.css` heading selectors use `.bd-article h1`–`h6` instead of
  `article[role="main"]`. They match the same elements.
- `tools/check_url_baseline.py` reads anchors from the page's main landmark,
  which is the outermost `<main>` or `role="main"` element, and skips
  `data-pagefind-ignore` subtrees. Under Furo that landmark is still
  `<article role="main">`, so Furo results are unchanged. Under pydata it also
  covers pages without an article, such as `search.html`. The missing-anchor
  error now reads `missing from the main landmark`.

## 0.1.0

First release. No consumer uses it yet.

- `kinetis_website_theme`, inheriting `pydata-sphinx-theme==0.23.0` on
  `sphinx>=8.0,<9`. Extras `blog` (`ablog>=0.11,<0.12`) and `notfound`
  (`sphinx-notfound-page>=1.0,<2`) are declared for the website.
- Defaults merged into `html_theme_options` where the consumer set none:
  - Navbar: the horizontal logo `logo-h.svg` (the outline K of
    the mark extended to KINETIS, with the comet in front of the I) to `https://kinetis.dev/`, the site nav, search, the theme
    switcher and GitHub (`https://github.com/kinetis-dev`).
  - "On this page" secondary sidebar, no breadcrumbs, no ethical-ads slot,
    prev/next links, `show_toc_level: 2` and `navigation_with_keys: False`.
  - Furo's Pygments pair, `a11y-light` and `native`.
  - `html_sidebars = {"**": ["kinetis-sidebar-nav"]}` when empty.
- Site navigation: Home `/`, Docs `/docs/`, Vector `/vector/docs/`. The
  active item is chosen by longest prefix of the deployed path
  (`html_baseurl` path + page), with `aria-current="page"` and `.active`.
- `<title>` in Furo's format: `Page - Project`, and the project name alone on
  the root document.
- The three root-relative `/assets/favicon.*` links.
- `<meta name="robots" content="noindex">` on `404`, on pages matching
  `kinetis_noindex_patterns`, and on pages with front matter
  `kinetis_noindex: true`.
- `<article role="main">` restored on the article, with `data-pagefind-*`
  attributes on the article, navbar and sidebars.
- Footer: copyright, Docs, GitHub, Packagist.
- `kinetis.css`: the kinetis.dev colour tokens for light and dark, red `h1`,
  amber `h2`–`h6`, and full-width `table.docutils`.
- `kinetis_index_as_directory` and `kinetis_prune_sitemap` are registered but
  have no effect until 0.2.0.
- `tools/check_url_baseline.py` (the kinetis URL guard) with a sample-site
  baseline, and `tools/bump_pin.py` for consumer pin bumps.
