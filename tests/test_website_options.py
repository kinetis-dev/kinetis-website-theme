"""Unit tests for the website-facing options: the landing template choice,
kinetis_index_as_directory and the kinetis_prune_sitemap pruner."""

import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from sphinx.errors import ExtensionError
from sphinx.events import EventManager

import kinetis_website_theme as theme

SITE = "https://kinetis.dev/"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def sitemap(*links, declaration="<?xml version='1.0' encoding='utf-8'?>\n", base=SITE):
    """A sitemap as sphinx-sitemap 2.9 writes it for sitemap_url_scheme "{link}"."""
    urls = "".join(f"<url><loc>{base}{link}</loc></url>" for link in links)
    return f'{declaration}<urlset xmlns="{NS}">{urls}</urlset>'


class SitemapFileTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="kinetis-sitemap-"))
        self.addCleanup(shutil.rmtree, self.dir)
        self.path = self.dir / "main-sitemap.xml"

    def prune(self, content, noindex=(), index_as_directory=False, known=lambda name: True):
        self.path.write_text(content, encoding="utf-8")
        removed = theme.prune_sitemap_file(
            self.path, SITE, ".html", lambda name: name in noindex, index_as_directory, known
        )
        return removed, self.path.read_text(encoding="utf-8")

    def test_noindex_locs_are_removed(self):
        removed, out = self.prune(
            sitemap("index.html", "blog/tag/php.html", "blog/posts/a.html", "blog.html"),
            noindex={"blog/tag/php", "blog"},
        )
        self.assertEqual(["blog/tag/php", "blog"], removed)
        self.assertEqual(sitemap("index.html", "blog/posts/a.html"), out)

    def test_index_locs_are_rewritten_to_their_directory(self):
        _, out = self.prune(sitemap("index.html", "blog/index.html", "blog/posts/index-of-x.html"), index_as_directory=True)
        self.assertEqual(sitemap("", "blog/", "blog/posts/index-of-x.html"), out)

    def test_index_locs_stay_without_index_as_directory(self):
        _, out = self.prune(sitemap("index.html", "blog/index.html"))
        self.assertEqual(sitemap("index.html", "blog/index.html"), out)

    def test_declaration_namespace_and_other_elements_are_kept(self):
        # Nothing to change: the file is rewritten byte for byte, lastmod and
        # xhtml alternates included.
        content = (
            "<?xml version='1.0' encoding='utf-8'?>\n"
            f'<urlset xmlns="{NS}" xmlns:xhtml="http://www.w3.org/1999/xhtml">'
            f"<url><loc>{SITE}a.html</loc><lastmod>2026-10-01T00:00:00Z</lastmod>"
            f'<xhtml:link href="{SITE}de/a.html" hreflang="de" rel="alternate" /></url>'
            "</urlset>"
        )
        _, out = self.prune(content, noindex={"b"})
        self.assertEqual(content, out)

    def test_removal_keeps_the_namespace_and_declaration(self):
        _, out = self.prune(sitemap("a.html", "b.html"), noindex={"a"})
        self.assertTrue(out.startswith(f"<?xml version='1.0' encoding='utf-8'?>\n<urlset xmlns=\"{NS}\"><url>"), out)
        self.assertNotIn("ns0", out)

    def test_an_indented_sitemap_keeps_its_layout(self):
        # sitemap_indent = 2
        def url(link):
            return f"  <url>\n    <loc>{SITE}{link}</loc>\n  </url>\n"

        head = f"<?xml version='1.0' encoding='utf-8'?>\n<urlset xmlns=\"{NS}\">\n"
        _, out = self.prune(head + url("a.html") + url("b/index.html") + url("c.html") + "</urlset>",
                            noindex={"a"}, index_as_directory=True)
        self.assertEqual(head + url("b/") + url("c.html") + "</urlset>", out)

    def test_escaped_locs_are_mapped_and_kept(self):
        _, out = self.prune(sitemap("a&amp;b.html", "c.html"), noindex={"c"})
        self.assertEqual(sitemap("a&amp;b.html"), out)

    def test_a_file_that_is_not_a_urlset_is_an_error(self):
        with self.assertRaisesRegex(ExtensionError, "not a sitemap <urlset>"):
            self.prune(f'<sitemapindex xmlns="{NS}"><sitemap><loc>{SITE}a.xml</loc></sitemap></sitemapindex>')

    def test_missing_file_is_an_error(self):
        with self.assertRaisesRegex(ExtensionError, r"the sitemap .*main-sitemap\.xml does not exist"):
            theme.prune_sitemap_file(self.path, SITE, ".html", lambda name: False, False, lambda name: True)

    def test_a_loc_that_maps_to_no_page_is_an_error(self):
        for link, known, pagename in (
            (".html", lambda name: True, ""),
            ("/blog/tag/php.html", lambda name: True, "/blog/tag/php"),
            ("blog/tag/gone.html", lambda name: name != "blog/tag/gone", "blog/tag/gone"),
        ):
            with self.subTest(link=link):
                with self.assertRaisesRegex(ExtensionError, f"maps to '{pagename}' under '{SITE}', which is no page"):
                    self.prune(sitemap(link), known=known)

    def test_a_loc_outside_the_site_is_an_error(self):
        with self.assertRaisesRegex(ExtensionError, "cannot map sitemap loc 'https://example.com/a.html'"):
            self.prune(f'<urlset xmlns="{NS}"><url><loc>https://example.com/a.html</loc></url></urlset>')


class FakeConfig(SimpleNamespace):
    def __contains__(self, name):
        return hasattr(self, name)


class PruneSitemapHandlerTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="kinetis-sitemap-"))
        self.addCleanup(shutil.rmtree, self.dir)

    def app(self, **config):
        values = dict(
            kinetis_prune_sitemap=True, kinetis_index_as_directory=True, kinetis_noindex_patterns=["blog/tag*"],
            sitemap_filename="main-sitemap.xml", sitemap_url_scheme="{link}", sitemap_indent=0,
            site_url=None, html_baseurl=SITE,
        )
        values.update(config)
        env = SimpleNamespace(
            found_docs={"index", "blog/index", "notes", "blog/posts/a"},
            metadata={"notes": {"kinetis_noindex": "true"}, "index": {}, "blog/index": {}, "blog/posts/a": {}},
        )
        builder = SimpleNamespace(format="html", name="html", out_suffix=".html")
        return SimpleNamespace(config=FakeConfig(**values), env=env, builder=builder, outdir=str(self.dir))

    def written(self, *pages):
        """Pages an extension wrote: not source documents, but in the output."""
        for name in pages:
            (self.dir / name).parent.mkdir(parents=True, exist_ok=True)
            (self.dir / name).write_text("<html></html>", encoding="utf-8")

    def test_noindex_comes_from_the_environment_and_the_patterns(self):
        self.written("blog/tag/php.html", "404.html", "search.html")
        path = self.dir / "main-sitemap.xml"
        path.write_text(sitemap("index.html", "blog/index.html", "notes.html", "blog/posts/a.html",
                                "blog/tag/php.html", "404.html", "search.html"), encoding="utf-8")
        theme.prune_sitemap(self.app(), None)
        # notes: front matter; blog/tag/php: a pattern (ablog page, not in
        # found_docs); 404: always. search is neither.
        self.assertEqual(sitemap("", "blog/", "blog/posts/a.html", "search.html"), path.read_text(encoding="utf-8"))

    def test_a_loc_for_a_page_the_build_lacks_is_an_error(self):
        (self.dir / "main-sitemap.xml").write_text(sitemap("index.html", "blog/tag/php.html"), encoding="utf-8")
        with self.assertRaisesRegex(ExtensionError, "maps to 'blog/tag/php'.*no page of this build"):
            theme.prune_sitemap(self.app(), None)

    def test_a_base_without_trailing_slash_is_used_as_sphinx_sitemap_uses_it(self):
        # sphinx-sitemap 2.9.0 does not normalise the base: its locs are
        # "https://kinetis.dev" + "blog/tag/php.html". The pruner maps them back
        # with the same prefix and prunes the same pages.
        base = SITE.rstrip("/")
        self.written("blog/tag/php.html")
        path = self.dir / "main-sitemap.xml"
        path.write_text(sitemap("index.html", "blog/tag/php.html", "blog/posts/a.html", base=base), encoding="utf-8")
        theme.prune_sitemap(self.app(html_baseurl=base), None)
        self.assertEqual(sitemap("", "blog/posts/a.html", base=base), path.read_text(encoding="utf-8"))

    def test_a_base_that_differs_from_the_locs_is_an_error_not_a_silent_keep(self):
        # Locs written with a trailing slash, mapped with a base without one:
        # "/blog/tag/php" would match no pattern and stay in the sitemap.
        self.written("blog/tag/php.html")
        (self.dir / "main-sitemap.xml").write_text(sitemap("blog/tag/php.html"), encoding="utf-8")
        with self.assertRaisesRegex(ExtensionError, "maps to '/blog/tag/php' under 'https://kinetis.dev'"):
            theme.prune_sitemap(self.app(html_baseurl=SITE.rstrip("/")), None)

    def test_site_url_wins_over_html_baseurl_as_in_sphinx_sitemap(self):
        config = FakeConfig(site_url="https://example.com/", html_baseurl=SITE)
        self.assertEqual("https://example.com/", theme.sitemap_base(config))
        self.assertEqual("https://kinetis.dev", theme.sitemap_base(FakeConfig(site_url=None, html_baseurl="https://kinetis.dev")))

    def test_the_previous_builds_sitemap_is_removed_at_builder_inited(self):
        path = self.dir / "main-sitemap.xml"
        path.write_text(sitemap(""), encoding="utf-8")
        theme.remove_previous_sitemap(self.app(kinetis_prune_sitemap=False))
        self.assertTrue(path.is_file())
        theme.remove_previous_sitemap(self.app())
        self.assertFalse(path.exists())
        theme.remove_previous_sitemap(self.app())  # nothing there: no error
        # So a build in which sphinx-sitemap writes nothing fails clearly
        # instead of pruning the old, already-pruned file again.
        with self.assertRaisesRegex(ExtensionError, "does not exist: sphinx-sitemap wrote none in this build"):
            theme.prune_sitemap(self.app(), None)

    def test_unsupported_url_scheme_is_an_error(self):
        with self.assertRaisesRegex(ExtensionError, r"needs sitemap_url_scheme = '\{link\}'.*'\{lang\}\{version\}\{link\}'"):
            theme.prune_sitemap(self.app(sitemap_url_scheme="{lang}{version}{link}"), None)

    def test_missing_sitemap_is_an_error(self):
        with self.assertRaisesRegex(ExtensionError, "does not exist"):
            theme.prune_sitemap(self.app(), None)

    def test_sphinx_sitemap_must_be_loaded(self):
        app = self.app()
        del app.config.sitemap_filename
        with self.assertRaisesRegex(ExtensionError, "needs sphinx_sitemap"):
            theme.prune_sitemap(app, None)

    def test_off_by_default_and_after_a_failed_build(self):
        theme.prune_sitemap(self.app(kinetis_prune_sitemap=False), None)
        theme.prune_sitemap(self.app(), RuntimeError("build failed"))

    def test_non_html_builders_are_skipped_and_dirhtml_refused(self):
        app = self.app()
        app.builder.format = "text"
        theme.prune_sitemap(app, None)
        app.builder.format, app.builder.name = "html", "dirhtml"
        with self.assertRaisesRegex(ExtensionError, "html builder only"):
            theme.prune_sitemap(app, None)


OG_URL = '<meta property="og:url" content="{}" />'


class IndexAsDirectoryTest(unittest.TestCase):
    def app(self, enabled=True):
        return SimpleNamespace(
            config=SimpleNamespace(kinetis_index_as_directory=enabled),
            builder=SimpleNamespace(out_suffix=".html"),
            pdb=False,
        )

    def context(self, url, meta=None):
        return {"pageurl": url, "metatags": "<meta property=\"og:title\" content=\"x\" />\n" + OG_URL.format(url) + "\n", "meta": meta}

    def test_index_pages_name_their_directory(self):
        for pagename, url, expected in (
            ("index", SITE + "index.html", SITE),
            ("blog/index", SITE + "blog/index.html", SITE + "blog/"),
        ):
            with self.subTest(page=pagename):
                context = self.context(url)
                theme.index_as_directory(self.app(), pagename, "page.html", context, None)
                self.assertEqual(expected, context["pageurl"])
                self.assertIn(OG_URL.format(expected), context["metatags"])
                self.assertIn('<meta property="og:title" content="x" />', context["metatags"])

    def test_other_pages_and_the_option_off_are_untouched(self):
        for app, pagename, url in (
            (self.app(), "blog/posts/index-of-x", SITE + "blog/posts/index-of-x.html"),
            (self.app(), "reindex", SITE + "reindex.html"),
            (self.app(enabled=False), "index", SITE + "index.html"),
        ):
            with self.subTest(page=pagename):
                context = self.context(url)
                before = dict(context)
                theme.index_as_directory(app, pagename, "page.html", context, None)
                self.assertEqual(before, context)

    def test_front_matter_og_url_wins(self):
        context = self.context(SITE + "index.html", meta={"og:url": SITE + "index.html"})
        theme.index_as_directory(self.app(), "index", "page.html", context, None)
        self.assertEqual(SITE, context["pageurl"])
        self.assertIn(OG_URL.format(SITE + "index.html"), context["metatags"])

    def test_the_rewrite_follows_og_url_whatever_the_registration_order(self):
        # sphinxext-opengraph appends og:url to metatags at the default
        # priority; the rewrite is connected first here and still runs after it.
        def opengraph(app, pagename, templatename, context, doctree):
            context["metatags"] += OG_URL.format(SITE + "index.html") + "\n"

        app = self.app()
        events = EventManager(app)
        events.add("html-page-context")  # registered by the HTML builder in a real build
        events.connect("html-page-context", theme.index_as_directory, theme.INDEX_AS_DIRECTORY_PRIORITY)
        events.connect("html-page-context", opengraph, 500)
        context = {"pageurl": SITE + "index.html", "metatags": "", "meta": {}}
        events.emit("html-page-context", "index", "page.html", context, None)
        self.assertEqual(OG_URL.format(SITE) + "\n", context["metatags"])


class SetupTest(unittest.TestCase):
    def test_handlers_and_priorities(self):
        connected = []
        scripts = []
        app = SimpleNamespace(
            builder=None,
            config=SimpleNamespace(templates_path=[]),
            add_html_theme=lambda *args: None,
            add_config_value=lambda *args, **kwargs: None,
            add_css_file=lambda *args, **kwargs: None,
            add_js_file=lambda *args, **kwargs: scripts.append((args, kwargs)),
            connect=lambda event, handler, priority=500: connected.append((event, handler.__name__, priority)),
        )
        theme.setup(app)
        self.assertIn(("html-page-context", "html_page_context", 500), connected)
        # After pydata's page-context handlers (500), which fill the sidebar lists.
        self.assertIn(("html-page-context", "landing_page_context", 700), connected)
        # After sphinxext-opengraph (500), which writes og:url.
        self.assertIn(("html-page-context", "index_as_directory", 800), connected)
        # After sphinx-sitemap's create_sitemap (500).
        self.assertIn(("build-finished", "prune_sitemap", 600), connected)
        self.assertIn(("builder-inited", "remove_previous_sitemap", 500), connected)
        # Neither defer nor async, so it runs before pydata's deferred script.
        self.assertEqual([(("kinetis-sidebar-scroll.js",), {})], scripts)


class LandingTemplateTest(unittest.TestCase):
    def test_front_matter_selects_the_landing_template(self):
        self.assertEqual("kinetis/landing.html", theme.page_template("index", {"kinetis_template": "landing"}))
        self.assertEqual("kinetis/landing.html", theme.page_template("index", {"kinetis_template": " landing "}))
        self.assertIsNone(theme.page_template("guide", {}))

    def test_template_file_exists(self):
        self.assertTrue((theme.THEME_PATH / "kinetis" / "landing.html").is_file())
        self.assertTrue((theme.THEME_PATH / "static" / "kinetis-landing.css").is_file())

    def test_unknown_template_warns(self):
        with self.assertLogs("sphinx.kinetis_website_theme", level="WARNING") as logs:
            self.assertIsNone(theme.page_template("index", {"kinetis_template": "hero"}))
        self.assertIn("unknown kinetis_template 'hero'", "\n".join(logs.output))

    def test_landing_page_context(self):
        added = []
        app = SimpleNamespace(env=SimpleNamespace(metadata={"index": {"kinetis_template": "landing"}, "guide": {}}),
                              add_css_file=lambda name, **kwargs: added.append(name))
        context = {"sidebars": ["kinetis-sidebar-nav"], "secondary_sidebar_items": ["page-toc"]}
        self.assertEqual("kinetis/landing.html", theme.landing_page_context(app, "index", "page.html", context, None))
        self.assertEqual({"sidebars": [], "secondary_sidebar_items": []}, context)
        self.assertEqual(["kinetis-landing.css"], added)
        docs_context = {"sidebars": ["kinetis-sidebar-nav"]}
        self.assertIsNone(theme.landing_page_context(app, "guide", "page.html", docs_context, None))
        self.assertEqual({"sidebars": ["kinetis-sidebar-nav"]}, docs_context)
        self.assertEqual(["kinetis-landing.css"], added)


if __name__ == "__main__":
    unittest.main()
