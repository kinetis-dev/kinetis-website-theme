"""kinetis.dev Sphinx theme: pydata-sphinx-theme with the Kinetis look.

Consumers set only ``html_theme = "kinetis_website_theme"``; every other
default comes from here.
"""

from copy import deepcopy
from fnmatch import fnmatch
from pathlib import Path
from urllib.parse import urlparse

from .nav import NAV, active_section

__version__ = "0.1.1"

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
    # Per-project Sphinx search, as Furo has today.
    "navbar_persistent": ["search-button"],
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


def apply_defaults(app, config):
    """Merge the theme defaults into the consumer's configuration."""
    # In place: the HTML builder took its reference to this dict before it
    # loaded the theme, so a replacement dict would never reach it.
    options = config.html_theme_options
    for key, value in THEME_OPTION_DEFAULTS.items():
        options.setdefault(key, deepcopy(value))
    if not config.html_sidebars:
        config.html_sidebars = dict(HTML_SIDEBARS_DEFAULT)


def page_url_path(baseurl, pagename):
    """The deployed path of a page: /docs/guide.html for kinetis' guide."""
    return urlparse(baseurl or "").path + pagename + ".html"


def is_noindex(pagename, metadata, patterns):
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


def setup(app):
    app.add_html_theme("kinetis_website_theme", str(THEME_PATH))
    # Component templates are looked up by bare name, as pydata's own are.
    app.config.templates_path.append(str(THEME_PATH / "components"))

    # fnmatch patterns on docnames whose pages get <meta name="robots" content="noindex">.
    app.add_config_value("kinetis_noindex_patterns", [], "html", types=[list])
    # TODO(phase 4, v0.2.0): rewrite .../index.html to .../ in canonical and the sitemap.
    # Registered now so v0.2.0 adds no config names; it has no effect yet.
    app.add_config_value("kinetis_index_as_directory", False, "html", types=[bool])
    # TODO(phase 4, v0.2.0): build-finished sitemap pruner (priority 600) dropping
    # kinetis_noindex_patterns locs. Registered now; it has no effect yet.
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
    # Loads after pydata's stylesheet and before the consumer's html_css_files.
    app.add_css_file("kinetis.css")

    return {"version": __version__, "parallel_read_safe": True, "parallel_write_safe": True}
