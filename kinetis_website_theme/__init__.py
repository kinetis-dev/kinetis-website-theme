"""kinetis.dev Sphinx theme: pydata-sphinx-theme with the Kinetis look.

Consumers set only ``html_theme = "kinetis_website_theme"``; every other
default comes from here.
"""

import html
import json
import re
from copy import deepcopy
from fnmatch import fnmatch
from pathlib import Path
from urllib.parse import urlparse

# Parses only the sitemap sphinx-sitemap just wrote into this build, never
# third-party XML; ElementTree does not resolve external entities.
import xml.etree.ElementTree as ET  # nosemgrep: python.lang.security.use-defused-xml.use-defused-xml

from pydata_sphinx_theme.utils import config_provided_by_user
from sphinx.errors import ExtensionError
from sphinx.util import logging

from .nav import NAV, SEARCH_BUNDLES, active_section, search_section

__version__ = "0.5.0"

logger = logging.getLogger(__name__)

THEME_PATH = Path(__file__).parent / "theme" / "kinetis_website_theme"

# Applied to html_theme_options key by key, only where the consumer set nothing.
THEME_OPTION_DEFAULTS = {
    # Bundled theme static; the brand links to the marketing site, as the
    # Furo sidebar/brand.html override did. logo-h.svg is the horizontal
    # lockup of logo.svg, legible at navbar height.
    "logo": {
        "image_light": "logo-h.svg",
        "image_dark": "logo-h.svg",
        "link": "https://kinetis.dev/",
        "alt_text": "Kinetis",
    },
    "navbar_start": ["navbar-logo"],
    # Replaces pydata's toctree-driven navbar-nav.
    "navbar_center": ["kinetis-nav"],
    # No navbar-icon-links: the header carries no GitHub icon (the footer
    # links the organisation), so no empty icon container renders either.
    "navbar_end": ["theme-switcher"],
    # The site-wide Pagefind search trigger (docs/SEARCH.md §5), filled in by
    # kinetis-search.js; pydata's own search is off.
    "navbar_persistent": ["kinetis-search"],
    "disable_search": True,
    "icon_links": [],
    # No breadcrumbs: keep the Furo look.
    "article_header_start": [],
    # Furo's right-hand "On this page"; no edit or source links.
    "secondary_sidebar_items": ["page-toc"],
    # Drops pydata's ethical-ads slot.
    "primary_sidebar_end": [],
    # Drops "Made with Sphinx" and the theme version.
    "footer_start": ["kinetis-footer"],
    "footer_center": [],
    "footer_end": [],
    "show_prev_next": True,
    # Explicit: pydata has warned when this is unset, and -W turns that into a failure.
    "navigation_with_keys": False,
    "show_toc_level": 2,
    # Furo's pair: furo/theme/furo/theme.conf sets pygments_style = a11y-light,
    # and furo registers pygments_dark_style with default "native".
    "pygments_light_style": "a11y-light",
    "pygments_dark_style": "native",
}

HTML_SIDEBARS_DEFAULT = {"**": ["kinetis-sidebar-nav"]}

TRUE_VALUES = {"true", "yes", "1", "on"}

# Front matter `kinetis_template: <key>` renders the page with this template.
PAGE_TEMPLATES = {"landing": "kinetis/landing.html"}
LANDING_CSS = "kinetis-landing.css"

# Handler priorities; Sphinx runs lower numbers first, and extensions connect
# at 500 by default. The landing setup runs after pydata's own page-context
# handlers, so the sidebar lists it empties stay empty. The index rewrite runs
# after sphinxext-opengraph has written og:url into metatags, whatever order
# the extensions were set up in. The sitemap pruner runs after sphinx-sitemap
# has written the file.
# The permalink icon default runs after pydata's update_config, which writes
# "#" at the default priority.
LANDING_PRIORITY = 700
PERMALINKS_ICON_PRIORITY = 600
INDEX_AS_DIRECTORY_PRIORITY = 800
PRUNE_SITEMAP_PRIORITY = 600

SUPPORTED_SITEMAP_SCHEME = "{link}"

# The same "#" as pydata's, kept out of Pagefind's titles and words.
PERMALINKS_ICON = "<span data-pagefind-ignore>#</span>"
SEARCH_JS = "kinetis-search.js"


def apply_defaults(app, config):
    """Merge the theme defaults into the consumer's configuration."""
    # In place: the HTML builder took its reference to this dict before it
    # loaded the theme, so a replacement dict would never reach it.
    options = config.html_theme_options
    for key, value in THEME_OPTION_DEFAULTS.items():
        options.setdefault(key, deepcopy(value))
    if not config.html_sidebars:
        config.html_sidebars = dict(HTML_SIDEBARS_DEFAULT)


def default_permalinks_icon(app):
    """Headerlinks render "#" inside data-pagefind-ignore (builder-inited, priority 600).

    Without it Pagefind titles a page "Routing#". Runs after pydata has
    written its own "#" default, and only when the consumer set no icon.
    """
    if not config_provided_by_user(app, "html_permalinks_icon"):
        app.config.html_permalinks_icon = PERMALINKS_ICON


def page_url_path(baseurl, pagename):
    """The deployed path of a page: /docs/guide.html for kinetis' guide."""
    return urlparse(baseurl or "").path + pagename + ".html"


def is_noindex(pagename, metadata, patterns):
    """The one definition of a noindex page, for the meta tag and the sitemap."""
    if pagename == "404":
        return True
    if str(metadata.get("kinetis_noindex", "")).strip().lower() in TRUE_VALUES:
        return True
    return any(fnmatch(pagename, pattern) for pattern in patterns)


def html_page_context(app, pagename, templatename, context, doctree):
    active = active_section(page_url_path(app.config.html_baseurl, pagename))
    context["kinetis_active"] = active
    # Absolute hrefs, never pathto(): correct from every prefix and on the 404 page.
    context["kinetis_nav"] = [
        {"label": item.label, "href": item.href, "active": item.label == active} for item in NAV
    ]
    context["kinetis_noindex"] = is_noindex(
        pagename, app.env.metadata.get(pagename, {}), app.config.kinetis_noindex_patterns
    )
    context["kinetis_pagefind_body"] = is_search_indexed(app.env, pagename, app.config.kinetis_noindex_patterns)
    context["kinetis_search_section"] = search_section(active)


def is_search_indexed(env, pagename, patterns):
    """Whether Pagefind indexes the page: a source document that is not noindex.

    Pages Sphinx or an extension generates (search, genindex, ablog listings)
    are not in found_docs. Read from the environment alone, so -j builds
    mark the same pages.
    """
    return pagename in env.found_docs and not is_noindex(pagename, env.metadata.get(pagename, {}), patterns)


def page_template(pagename, metadata):
    """The template a page's front matter selects, or None for the default."""
    key = metadata.get("kinetis_template")
    if key is None:
        return None
    key = str(key).strip()
    if key not in PAGE_TEMPLATES:
        logger.warning(
            "unknown kinetis_template %r; known: %s", key, ", ".join(sorted(PAGE_TEMPLATES)),
            location=pagename, type="kinetis", subtype="template",
        )
        return None
    return PAGE_TEMPLATES[key]


def landing_page_context(app, pagename, templatename, context, doctree):
    """Render pages with `kinetis_template: landing` through kinetis/landing.html."""
    template = page_template(pagename, app.env.metadata.get(pagename, {}))
    if template is None:
        return None
    # No primary sidebar content and no "On this page": the primary sidebar
    # then holds only the navbar items, and only on narrow screens.
    context["sidebars"] = []
    context["secondary_sidebar_items"] = []
    # Added for this page only, so docs pages never link it.
    app.add_css_file(LANDING_CSS)
    return template


def is_index_page(pagename):
    return pagename == "index" or pagename.endswith("/index")


def index_as_directory(app, pagename, templatename, context, doctree):
    """Canonical and og:url of an index page name its directory: .../ for .../index.html."""
    if not app.config.kinetis_index_as_directory or not is_index_page(pagename):
        return
    index_file = "index" + app.builder.out_suffix
    pageurl = context.get("pageurl")
    if pageurl and pageurl.endswith("/" + index_file):
        context["pageurl"] = pageurl[: -len(index_file)]
    # An og:url set in front matter is the page's own choice and stays.
    if "og:url" in (context.get("meta") or {}):
        return
    if context.get("metatags"):
        og_url = re.compile(r'(<meta property="og:url" content="[^"]*/)' + re.escape(index_file) + '(" />)')
        context["metatags"] = og_url.sub(r"\1\2", context["metatags"])


def sitemap_base(config):
    """The prefix sphinx-sitemap 2.9.0 puts before every "{link}" loc.

    Exactly its own: site_url, else html_baseurl, used as given. Its
    `site_url.rstrip("/") + "/"` line discards its result, so a base without
    a trailing slash is not normalised there and must not be here either.
    """
    return config.site_url or config.html_baseurl


def loc_pagename(loc, site_url, suffix, known):
    """The page name behind a sitemap loc written with sitemap_url_scheme "{link}".

    ``known(pagename)`` says whether the build has that page; a loc that maps
    to no page means the base or the layout is not what sphinx-sitemap used,
    and guessing would keep or drop the wrong pages silently.
    """
    if not loc.startswith(site_url) or not loc.endswith(suffix):
        raise ExtensionError(
            f"kinetis_prune_sitemap: cannot map sitemap loc {loc!r} to a page: "
            f"expected {site_url}<page>{suffix}"
        )
    pagename = loc[len(site_url) : -len(suffix)]
    if not pagename or pagename.startswith("/") or not known(pagename):
        raise ExtensionError(
            f"kinetis_prune_sitemap: sitemap loc {loc!r} maps to {pagename!r} under {site_url!r}, "
            "which is no page of this build; check html_baseurl (and site_url) against the sitemap"
        )
    return pagename


SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
# One <url> element as sphinx-sitemap writes it, with the whitespace before it
# (sitemap_indent), so a removal leaves the rest of the layout as it was.
SITEMAP_URL = re.compile(r"\s*<url>(?P<content>.*?)</url>", re.DOTALL)
SITEMAP_LOC = re.compile(r"(<loc>\s*)(?P<loc>[^<]*?)(\s*</loc>)")


def prune_sitemap_file(path, site_url, suffix, noindex, index_as_directory, known):
    """Rewrite a sphinx-sitemap file in place.

    Drops every <url> whose page is noindex (``noindex(pagename)`` is true)
    and, with ``index_as_directory``, ends index locs at their directory.
    Every loc must map to a page ``known(pagename)`` accepts.
    Only those <url> elements change: the declaration, the namespaces and
    every other byte of the file stay as sphinx-sitemap wrote them. Returns
    the page names removed.
    """
    path = Path(path)
    if not path.is_file():
        raise ExtensionError(
            f"kinetis_prune_sitemap: the sitemap {path} does not exist: sphinx-sitemap wrote none "
            "in this build. It writes one at build-finished when sphinx_sitemap is in extensions, "
            "html_baseurl is set and at least one page is not in sitemap_excludes."
        )
    text = path.read_text(encoding="utf-8")
    # The parsed locs are the reference; the text edits below must see the same ones.
    root = ET.fromstring(text.encode("utf-8"))
    if root.tag != f"{{{SITEMAP_NAMESPACE}}}urlset":
        raise ExtensionError(f"kinetis_prune_sitemap: {path} is not a sitemap <urlset>")
    parsed = [(loc.text or "").strip() for loc in root.iter(f"{{{SITEMAP_NAMESPACE}}}loc")]

    index_file = "index" + suffix
    removed = []
    seen = []

    def rewrite(url):
        locs = list(SITEMAP_LOC.finditer(url["content"]))
        if len(locs) != 1:
            raise ExtensionError(f"kinetis_prune_sitemap: a <url> in {path} has {len(locs)} <loc> elements")
        loc = html.unescape(locs[0]["loc"])
        seen.append(loc)
        pagename = loc_pagename(loc, site_url, suffix, known)
        if noindex(pagename):
            removed.append(pagename)
            return ""
        if index_as_directory and is_index_page(pagename):
            start, end = locs[0].span("loc")
            offset = url.start("content") - url.start()
            whole = url.group(0)
            return whole[: offset + start] + locs[0]["loc"][: -len(index_file)] + whole[offset + end :]
        return url.group(0)

    pruned = SITEMAP_URL.sub(rewrite, text)
    if seen != parsed:
        raise ExtensionError(f"kinetis_prune_sitemap: {path} is not laid out as sphinx-sitemap writes it")
    path.write_text(pruned, encoding="utf-8")
    return removed


def prunes_sitemap(app):
    return app.config.kinetis_prune_sitemap and app.builder.format == "html" and app.builder.name == "html"


def remove_previous_sitemap(app):
    """Delete an earlier build's sitemap before this build writes its own (builder-inited).

    sphinx-sitemap leaves the file alone when it collects no pages, so in an
    output directory that was built before, the pruner would otherwise find
    the previous build's already-pruned file and prune it again. Without it,
    a sitemap sphinx-sitemap did not write in this build is a missing file,
    and prune_sitemap fails on it clearly.
    """
    if not prunes_sitemap(app) or "sitemap_filename" not in app.config:
        return
    path = Path(app.outdir) / app.config.sitemap_filename
    if path.is_file():
        path.unlink()


def prune_sitemap(app, exception):
    """Drop noindex pages from sphinx-sitemap's file (build-finished, priority 600)."""
    if exception is not None or not app.config.kinetis_prune_sitemap or app.builder.format != "html":
        return
    config = app.config
    if "sitemap_filename" not in config:
        raise ExtensionError("kinetis_prune_sitemap needs sphinx_sitemap in extensions")
    if app.builder.name != "html":
        raise ExtensionError(
            f"kinetis_prune_sitemap supports the html builder only, not {app.builder.name!r}"
        )
    if config.sitemap_url_scheme != SUPPORTED_SITEMAP_SCHEME:
        raise ExtensionError(
            f"kinetis_prune_sitemap needs sitemap_url_scheme = {SUPPORTED_SITEMAP_SCHEME!r} to map "
            f"sitemap locs back to pages; it is {config.sitemap_url_scheme!r}"
        )
    site_url = sitemap_base(config)
    if not site_url:
        raise ExtensionError("kinetis_prune_sitemap needs html_baseurl")
    # Computed here in the main process from the environment alone: state
    # collected in html-page-context is lost when -j writes pages in workers.
    # Pages Sphinx or an extension generates (ablog listings, search) are not
    # in found_docs and have no metadata, so only the patterns decide them.
    env = app.env
    patterns = config.kinetis_noindex_patterns
    noindex = {name for name in env.found_docs if is_noindex(name, env.metadata.get(name, {}), patterns)}

    def page_is_noindex(pagename):
        if pagename in env.found_docs:
            return pagename in noindex
        return is_noindex(pagename, {}, patterns)

    outdir = Path(app.outdir)
    suffix = app.builder.out_suffix

    def page_is_known(pagename):
        # A source document, or a page Sphinx or an extension wrote (an
        # ablog listing, search): every sitemap loc is a written page.
        return pagename in env.found_docs or (outdir / (pagename + suffix)).is_file()

    path = outdir / config.sitemap_filename
    removed = prune_sitemap_file(path, site_url, suffix, page_is_noindex,
                                 config.kinetis_index_as_directory, page_is_known)
    logger.info("kinetis: pruned %d noindex page(s) from %s", len(removed), config.sitemap_filename)


def setup(app):
    app.add_html_theme("kinetis_website_theme", str(THEME_PATH))
    # Component templates are looked up by bare name, as pydata's own are.
    app.config.templates_path.append(str(THEME_PATH / "components"))

    # fnmatch patterns on docnames whose pages get <meta name="robots" content="noindex">.
    app.add_config_value("kinetis_noindex_patterns", [], "html", types=[list])
    # Canonical, og:url and (with the pruner) sitemap locs of index pages end at
    # the directory: https://kinetis.dev/ rather than https://kinetis.dev/index.html.
    app.add_config_value("kinetis_index_as_directory", False, "html", types=[bool])
    # Drop noindex pages from sphinx-sitemap's file at build-finished.
    app.add_config_value("kinetis_prune_sitemap", False, "html", types=[bool])

    # Sphinx loads an html_themes entry point while it initialises the
    # builder, after config-inited has already been emitted, so the merge
    # runs here directly. Listed under `extensions` instead, it runs on
    # config-inited.
    if getattr(app, "builder", None) is not None:
        apply_defaults(app, app.config)
    else:
        app.connect("config-inited", apply_defaults)

    app.connect("html-page-context", html_page_context)
    app.connect("html-page-context", landing_page_context, priority=LANDING_PRIORITY)
    app.connect("html-page-context", index_as_directory, priority=INDEX_AS_DIRECTORY_PRIORITY)
    app.connect("builder-inited", remove_previous_sitemap)
    app.connect("builder-inited", default_permalinks_icon, priority=PERMALINKS_ICON_PRIORITY)
    app.connect("build-finished", prune_sitemap, priority=PRUNE_SITEMAP_PRIORITY)
    # Loads after pydata's stylesheet and before the consumer's html_css_files.
    app.add_css_file("kinetis.css")
    # Neither defer nor async: it runs while the head is parsed, before
    # pydata's deferred script reads the sidebar scroll key it scopes.
    app.add_js_file("kinetis-sidebar-scroll.js")
    # Probes SEARCH_BUNDLES and builds the Pagefind UI once the page is parsed.
    app.add_js_file(SEARCH_JS, loading_method="defer", **{"data-kinetis-bundles": json.dumps(list(SEARCH_BUNDLES))})

    return {"version": __version__, "parallel_read_safe": True, "parallel_write_safe": True}
