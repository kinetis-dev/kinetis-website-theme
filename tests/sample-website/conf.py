# Sample website project for the theme's CI: the shape of the kinetis.dev
# site (design 5.1, 5.2 and 5.4) with the landing and 404 bodies of
# kinetis-website 23a08af (tests/website-inputs/) and placeholder posts.
#
# Everything the landing's head needs comes from front matter and the
# values below; the theme carries no Kinetis copy for it.

project = "Kinetis"
copyright = "2026, Kinetis"
author = "Kinetis"

extensions = [
    "myst_parser",
    "sphinxext.opengraph",
    "sphinx_sitemap",
    "notfound.extension",
    "ablog",
]

source_suffix = {
    ".md": "markdown",
}

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- HTML output -------------------------------------------------------------

html_theme = "kinetis_website_theme"
html_title = "Kinetis"
html_baseurl = "https://kinetis.dev/"
html_copy_source = False
html_show_sourcelink = False
html_use_index = False
html_domain_indices = False

ogp_site_url = html_baseurl
ogp_site_name = "Kinetis"
ogp_image = "https://kinetis.dev/assets/og-image.png"
# The landing head has no og:image:alt; sphinxext-opengraph would add one.
ogp_image_alt = False

# /sitemap.xml is the website's hand-written sitemap index.
sitemap_filename = "main-sitemap.xml"
sitemap_url_scheme = "{link}"
sitemap_excludes = ["404.html"]

notfound_urls_prefix = "/"

kinetis_index_as_directory = True
kinetis_prune_sitemap = True
# Design 5.2: every ablog listing is noindex and leaves the sitemap; /blog/
# and the posts under /blog/posts/ stay. Two lines go beyond the design's
# list: ablog 0.11 writes each year's archive at blog/<year>.html, not under
# blog/archive, and "search" is Sphinx's search page. "blog" is ablog's own
# root listing, blog.html.
kinetis_noindex_patterns = [
    "blog/tag*",
    "blog/category*",
    "blog/archive*",
    "blog/[0-9][0-9][0-9][0-9]",
    "blog/author*",
    "blog/drafts",
    "blog/language*",
    "blog/location*",
    "blog",
    "search",
]

# -- ABlog (design 5.4) --------------------------------------------------------

blog_path = "blog"
blog_post_pattern = "blog/posts/*.md"
blog_baseurl = "https://kinetis.dev/"
blog_title = "Kinetis blog"
post_auto_image = 0
blog_feed_fulltext = True

html_sidebars = {
    "blog/**": [
        "ablog/postcard.html",
        "ablog/recentposts.html",
        "ablog/tagcloud.html",
        "ablog/categories.html",
        "ablog/archives.html",
    ],
}
