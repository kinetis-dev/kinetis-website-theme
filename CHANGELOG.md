# Changelog

All notable changes to this theme. Versions follow semantic versioning: nav
changes and pydata-sphinx-theme bumps are minor, template or variable
removals are major.

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
