# Sample docs project for the theme's CI: the shape of kinetis/docs (MyST,
# captioned toctrees, /docs/ base URL) with placeholder content.
#
# The navigation tests rebuild it with -D html_baseurl=... to place the same
# pages under /vector/docs/ and /. Keep html_baseurl a literal assignment:
# tools/check_url_baseline.py reads it from this file with a regex.

project = "Kinetis"
copyright = "2026, Kinetis"
author = "Kinetis"

extensions = [
    "myst_parser",
    "sphinxext.opengraph",
    "sphinx_sitemap",
]

myst_heading_anchors = 4

source_suffix = {
    ".md": "markdown",
}

exclude_patterns = ["_build", "baseline", "Thumbs.db", ".DS_Store"]

# -- HTML output -------------------------------------------------------------
# Consumers set only html_theme; every theme default comes from the theme.

html_theme = "kinetis_website_theme"
html_title = "Kinetis"
html_baseurl = "https://kinetis.dev/docs/"

ogp_site_url = html_baseurl
ogp_site_name = "Kinetis"

sitemap_url_scheme = "{link}"
sitemap_excludes = [
    "404.html",
]
