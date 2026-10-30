# Consumers

Every repository that builds with this theme pins one release URL in one
requirements file. A release reaches a property only through a one-line pin
bump PR there. Dependabot cannot bump URL requirements, so these are made by
hand or with `tools/bump_pin.py`.

| Repository | Pin location | Deploys to | Search bundle (0.5.0) | Extras | Status |
|---|---|---|---|---|---|
| `kinetis-dev/kinetis` | `docs/requirements.txt` | `https://kinetis.dev/docs/` | `/docs/pagefind/` | none | adopts in phase 3 |
| `kinetis-dev/vector-dev` | `docs/requirements.txt` | `https://kinetis.dev/vector/docs/` | `/vector/docs/pagefind/` | none | adopts in phase 2 |
| `kinetis-dev/kinetis-website` | `site/requirements.txt` | `https://kinetis.dev/` | `/pagefind/` | `[blog,notfound]` | future, when `site/` exists (phase 5b) |

From 0.5.0 the same requirements file also pins Pagefind
(`pagefind[extended]==1.5.2`, `pagefind-bin-extended==1.5.2`), and each
build is indexed into its search bundle; see "Adopting 0.5.0".

The pin line:

```
kinetis-website-theme @ https://github.com/kinetis-dev/kinetis-website-theme/releases/download/vX.Y.Z/kinetis_website_theme-X.Y.Z-py3-none-any.whl
```

The website pins the same URL with the extras, which pull in ABlog and
sphinx-notfound-page (`ablog>=0.11,<0.12`, `sphinx-notfound-page>=1.0,<2`):

```
kinetis-website-theme[blog,notfound] @ https://github.com/kinetis-dev/kinetis-website-theme/releases/download/vX.Y.Z/kinetis_website_theme-X.Y.Z-py3-none-any.whl
```

## What the website sets (0.2.0 and later)

The docs consumers set only `html_theme`. The website also uses the options
below; the README has the details, and `tests/sample-website/` is a working
project that phase 5b can copy.

- `kinetis_index_as_directory = True`: the canonical URL and `og:url` of
  `index` pages end at the directory (`https://kinetis.dev/`,
  `https://kinetis.dev/blog/`), and so do their sitemap locs when the pruner
  is on. An `og:url` in front matter wins.
- `kinetis_prune_sitemap = True`: noindex pages are dropped from the
  sitemap. It needs `sitemap_url_scheme = "{link}"`. The file name comes
  from `sitemap_filename`, which sphinx-sitemap 2.9.0 supports, so
  `sitemap_filename = "main-sitemap.xml"` works.
- `kinetis_noindex_patterns`: the ablog listings. ablog 0.11 writes its root
  listing of all posts at `blog.html` (pattern `blog`), and each year's
  archive at `blog/<year>.html` (pattern `blog/[0-9][0-9][0-9][0-9]`), next
  to `blog/tag*`, `blog/category*`, `blog/archive*`, `blog/author*`,
  `blog/language*`, `blog/location*` and `blog/drafts`. Its Atom feed is
  `blog/atom.xml`.
- Front matter `kinetis_template: landing` renders a page with the landing
  template, and `kinetis_noindex: true` marks a page noindex.
- Page titles without a heading use the `{title}` directive, not a
  front-matter `title:` key (MyST does not make that the document title).
- `404.md` uses `orphan: true` and `kinetis_template: landing`, and conf
  enables `notfound.extension` with `notfound_urls_prefix = "/"`.

## Adopting 0.3.0

The navigation changes (Vector links `/vector/`, Blog `/blog/`), so bump in
the order below, the website first. Landing pages (`kinetis_template:
landing`, the 404 page included) now render the theme's shared footer, so in
the same PR as the pin bump the website removes the `<footer>…</footer>`
element from the bodies of its three landing pages, `/`, `/404` and
`/vector/`. A body that keeps one shows two footers. The docs consumers have
no landing pages and change nothing but the pin.

## Adopting 0.4.0

The Vector nav item links to `/vector/docs/` (was `/vector/`). It is a pin
bump only: no option, template or CSS changes. Bump kinetis and vector-dev
in either order, and the website last, because the website's 0.4.0 PR also
deletes its Vector landing page, `/vector/`. Bumped in this order, no
section links to `/vector/` after it is gone.

## Adopting 0.5.0

Site-wide search with Pagefind; `docs/SEARCH.md` is the contract. Every
consumer, in the PR that bumps the pin:

1. Adds the two Pagefind pins to the requirements file that builds the site
   (`docs/requirements.txt`, or `site/requirements.txt` for the website). Pin
   both exactly: the wrapper alone accepts any 1.x binary, and bundles of
   different Pagefind versions must not meet in one search.

   ```
   pagefind[extended]==1.5.2
   pagefind-bin-extended==1.5.2
   ```

2. Indexes its finished build in CI and in the deploy workflow, after
   `sphinx-build` and after any step that removes files from the output, and
   before the build's checks:

   ```sh
   python -m pagefind --site <output-dir>
   ```

   No other flag and no `pagefind.yml`. Pagefind fails only on a build with
   no HTML at all; it does not notice missing theme markers, so keep the
   theme pinned to a tested release.

3. Deploys the bundle with the build. It lands at `<output-dir>/pagefind/`,
   so it is served at the section's bundle path in the table above. Let the
   URL guard accept the new `pagefind/` files; new URLs are allowed by the
   docs baseline rules. The website's root sync must not delete `/docs/` or
   `/vector/`, which it already excludes.

4. Keeps `html_baseurl` set to the deployed URL: it decides each page's
   search section.

Order: release the theme, deploy kinetis and vector-dev in either order,
then the website last, and confirm that a search from each section returns
results from all four (website, blog, Kinetis docs, Vector docs). Until a
section deploys, the others search without it. A build served on its own
after indexing (`python -m http.server -d <output-dir>`) searches only
itself; one that is not indexed shows no search box.

## Bumping a consumer

From a checkout of the consumer:

```sh
python3 /path/to/kinetis-website-theme/tools/bump_pin.py docs/requirements.txt 0.5.0
```

It rewrites only the pin line, keeps any extras, and prints the diff. It
refuses a file with no pin line or more than one. Open the PR with that one
change. The consumer's CI builds with the new wheel and runs its URL-baseline
guard before merge, and merging to `main` redeploys that section.

For releases that change the navigation, bump in this order: the website
first, so a new nav target exists before the other sections link to it, then
kinetis, then vector-dev. A release that drops a nav target the website
then deletes reverses this, the website last, as 0.4.0 does. The sections
show different navbars until all three are merged.
