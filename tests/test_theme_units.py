"""Unit tests for nav.py and the theme's config and page-context helpers."""

import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import kinetis_website_theme as theme
from kinetis_website_theme import nav
from kinetis_website_theme.nav import NAV, SEARCH_BUNDLES, Item, active_section, search_section

REPO = Path(__file__).resolve().parents[1]


class ActiveSectionTest(unittest.TestCase):
    def test_nav_items_and_order(self):
        self.assertEqual(
            [("Home", "/"), ("Docs", "/docs/"), ("Vector", "/vector/docs/"), ("Blog", "/blog/")],
            [tuple(item) for item in NAV],
        )

    def test_docs_pages_are_docs(self):
        for path in ("/docs/", "/docs/index.html", "/docs/guide.html", "/docs/genindex.html"):
            self.assertEqual("Docs", active_section(path), path)

    def test_vector_pages_are_vector(self):
        for path in ("/vector/docs/", "/vector/docs/index.html", "/vector/docs/install.html"):
            self.assertEqual("Vector", active_section(path), path)

    def test_blog_pages_are_blog(self):
        # /blog.html is ablog's root listing, Blog by the exact .html rule.
        for path in ("/blog/", "/blog/index.html", "/blog/posts/x.html", "/blog/tag/php.html", "/blog.html"):
            self.assertEqual("Blog", active_section(path), path)

    def test_root_is_home_and_only_the_root(self):
        self.assertEqual("Home", active_section("/"))
        self.assertEqual("Home", active_section("/index.html"))

    def test_html_rule_applies_to_every_item_but_home(self):
        # Each non-root href without its slash plus .html is that item's page;
        # Home's href is "/", which the rule never reads as "/.html" or "/home.html".
        self.assertEqual("Docs", active_section("/docs.html"))
        self.assertEqual("Vector", active_section("/vector/docs.html"))
        self.assertEqual("Blog", active_section("/blog.html"))
        for path in ("/home.html", "/.html", ".html"):
            self.assertIsNone(active_section(path), path)

    def test_unowned_paths_are_none(self):
        # The .html rule is exact, not a fuzzy prefix: no item owns these.
        # Vector's href is /vector/docs/, so /vector/ and its other pages,
        # /vector.html included, belong to no item.
        for path in ("/about.html", "/docs-old/x.html", "/blogger.html", "/vector-x/", "/vector.htm",
                     "/docs.html/x", "/blog.html/", "/vector/", "/vector/index.html", "/vector/x.html",
                     "/vector.html"):
            self.assertIsNone(active_section(path), path)

    def test_longest_prefix_wins(self):
        # With NAV as shipped, Vector's href is /vector/docs/: it owns
        # /vector/docs/x.html and no item owns /vector/x.html. With a mocked
        # NAV holding both /vector/ and /vector/docs/, /vector/docs/x.html is
        # under both; the longer href wins in either order.
        self.assertEqual("Vector", active_section("/vector/docs/x.html"))
        self.assertIsNone(active_section("/vector/x.html"))
        self.assertNotEqual("Home", active_section("/docs/x.html"))
        for items in (
            (Item("Vector", "/vector/"), Item("Vector docs", "/vector/docs/")),
            (Item("Vector docs", "/vector/docs/"), Item("Vector", "/vector/")),
        ):
            with self.subTest(order=[item.href for item in items]), mock.patch.object(nav, "NAV", (NAV[0], *items)):
                self.assertEqual("Vector docs", active_section("/vector/docs/x.html"))
                self.assertEqual("Vector", active_section("/vector/x.html"))

    def test_url_path_is_baseurl_path_plus_pagename(self):
        self.assertEqual("/docs/guide.html", theme.page_url_path("https://kinetis.dev/docs/", "guide"))
        self.assertEqual("/vector/docs/a/b.html", theme.page_url_path("https://kinetis.dev/vector/docs/", "a/b"))
        self.assertEqual("/index.html", theme.page_url_path("https://kinetis.dev/", "index"))


class DefaultsTest(unittest.TestCase):
    def config(self, **values):
        return SimpleNamespace(html_theme_options=values.pop("html_theme_options", {}), html_sidebars={}, **values)

    def test_empty_config_gets_every_default(self):
        config = self.config()
        theme.apply_defaults(None, config)
        self.assertEqual(theme.THEME_OPTION_DEFAULTS, config.html_theme_options)
        self.assertEqual({"**": ["kinetis-sidebar-nav"]}, config.html_sidebars)
        self.assertIs(False, config.html_theme_options["navigation_with_keys"])
        # No header GitHub icon: the footer carries the only GitHub link.
        self.assertEqual([], config.html_theme_options["icon_links"])
        self.assertEqual(["theme-switcher"], config.html_theme_options["navbar_end"])

    def test_consumer_keys_win_and_the_dict_is_updated_in_place(self):
        # Values that differ from the defaults, so only a consumer win passes.
        options = {"navbar_end": ["theme-switcher", "navbar-icon-links"], "show_toc_level": 3}
        config = self.config(html_theme_options=options)
        config.html_sidebars = {"**": ["mine.html"]}
        theme.apply_defaults(None, config)
        self.assertIs(options, config.html_theme_options)
        self.assertNotEqual(theme.THEME_OPTION_DEFAULTS["navbar_end"], options["navbar_end"])
        self.assertEqual(["theme-switcher", "navbar-icon-links"], options["navbar_end"])
        self.assertEqual(3, options["show_toc_level"])
        self.assertEqual(["kinetis-nav"], options["navbar_center"])
        self.assertEqual({"**": ["mine.html"]}, config.html_sidebars)

    def test_defaults_are_not_shared_between_builds(self):
        first, second = self.config(), self.config()
        theme.apply_defaults(None, first)
        first.html_theme_options["icon_links"].append({"name": "x"})
        first.html_theme_options["logo"]["link"] = "https://example.com/"
        theme.apply_defaults(None, second)
        self.assertEqual([], second.html_theme_options["icon_links"])
        self.assertEqual("https://kinetis.dev/", second.html_theme_options["logo"]["link"])
        self.assertEqual([], theme.THEME_OPTION_DEFAULTS["icon_links"])

    def test_search_is_the_themes_pagefind_trigger_and_pydatas_is_off(self):
        config = self.config()
        theme.apply_defaults(None, config)
        self.assertEqual(["kinetis-search"], config.html_theme_options["navbar_persistent"])
        self.assertIs(True, config.html_theme_options["disable_search"])
        self.assertTrue((theme.THEME_PATH / "components" / "kinetis-search.html").is_file())
        self.assertTrue((theme.THEME_PATH / "static" / "kinetis-search.js").is_file())
        self.assertTrue((theme.THEME_PATH / "search.html").is_file())

    def test_consumer_search_options_win(self):
        options = {"navbar_persistent": ["search-button"], "disable_search": False}
        config = self.config(html_theme_options=options)
        theme.apply_defaults(None, config)
        self.assertEqual(["search-button"], options["navbar_persistent"])
        self.assertIs(False, options["disable_search"])

    def test_pygments_pair_is_furos(self):
        options = theme.THEME_OPTION_DEFAULTS
        self.assertEqual(("a11y-light", "native"), (options["pygments_light_style"], options["pygments_dark_style"]))


class NoindexTest(unittest.TestCase):
    def test_404_is_noindex(self):
        self.assertTrue(theme.is_noindex("404", {}, []))

    def test_front_matter(self):
        self.assertTrue(theme.is_noindex("notes", {"kinetis_noindex": "true"}, []))
        self.assertTrue(theme.is_noindex("notes", {"kinetis_noindex": True}, []))
        self.assertFalse(theme.is_noindex("notes", {"kinetis_noindex": "false"}, []))

    def test_patterns_are_fnmatch_on_docnames(self):
        patterns = ["blog/tag*", "drafts"]
        self.assertTrue(theme.is_noindex("blog/tag/php", {}, patterns))
        self.assertTrue(theme.is_noindex("drafts", {}, patterns))
        self.assertFalse(theme.is_noindex("blog/posts/hello", {}, patterns))

    def test_ordinary_page_is_indexed(self):
        self.assertFalse(theme.is_noindex("guide", {"title": "Guide"}, []))


class SearchTest(unittest.TestCase):
    def test_bundles(self):
        self.assertEqual(("/pagefind/", "/docs/pagefind/", "/vector/docs/pagefind/"), SEARCH_BUNDLES)

    def test_every_bundle_is_a_nav_sections_root(self):
        # The bundle of each build lives at its root; the website's holds Home and Blog.
        roots = {item.href for item in NAV} - {"/blog/"}
        self.assertEqual(roots, {bundle.removesuffix("pagefind/") for bundle in SEARCH_BUNDLES})

    def test_sections(self):
        self.assertEqual("Docs", search_section("Docs"))
        self.assertEqual("Vector", search_section("Vector"))
        self.assertEqual("Blog", search_section("Blog"))
        self.assertEqual("Main", search_section("Home"))
        self.assertEqual("Main", search_section(None))

    def test_sections_from_deployed_paths(self):
        for path, section in (("/index.html", "Main"), ("/about.html", "Main"), ("/blog/index.html", "Blog"),
                              ("/blog/posts/x.html", "Blog"), ("/docs/guide.html", "Docs"),
                              ("/vector/docs/index.html", "Vector")):
            self.assertEqual(section, search_section(active_section(path)), path)

    def test_indexed_pages_are_source_documents_that_are_not_noindex(self):
        env = SimpleNamespace(found_docs={"index", "guide", "404", "notes", "blog/tag"},
                              metadata={"notes": {"kinetis_noindex": "true"}})
        patterns = ["blog/tag*"]
        self.assertTrue(theme.is_search_indexed(env, "index", patterns))
        self.assertTrue(theme.is_search_indexed(env, "guide", patterns))
        for pagename in ("404", "notes", "blog/tag", "search", "genindex", "py-modindex", "blog"):
            self.assertFalse(theme.is_search_indexed(env, pagename, patterns), pagename)


class PermalinksIconTest(unittest.TestCase):
    def app(self, raw=None, overrides=None):
        config = SimpleNamespace(overrides=overrides or {}, _raw_config=raw or {}, html_permalinks_icon="#")
        return SimpleNamespace(config=config)

    def test_default_is_kept_out_of_pagefind(self):
        app = self.app()
        theme.default_permalinks_icon(app)
        self.assertEqual("<span data-pagefind-ignore>#</span>", app.config.html_permalinks_icon)

    def test_conf_py_value_wins(self):
        app = self.app(raw={"html_permalinks_icon": "#"})
        theme.default_permalinks_icon(app)
        self.assertEqual("#", app.config.html_permalinks_icon)

    def test_command_line_value_wins(self):
        app = self.app(overrides={"html_permalinks_icon": "#"})
        theme.default_permalinks_icon(app)
        self.assertEqual("#", app.config.html_permalinks_icon)

    def test_runs_after_pydatas_default(self):
        # pydata's update_config writes "#" at builder-inited, default priority 500.
        self.assertGreater(theme.PERMALINKS_ICON_PRIORITY, 500)


class VersionTest(unittest.TestCase):
    def test_module_version_matches_pyproject(self):
        with open(REPO / "pyproject.toml", "rb") as f:
            self.assertEqual(tomllib.load(f)["project"]["version"], theme.__version__)


if __name__ == "__main__":
    unittest.main()
