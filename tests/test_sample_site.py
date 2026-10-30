"""Build tests/sample-site with the installed theme and assert on its HTML.

The site is built three times with `-W --keep-going`, with html_baseurl at
/docs/ (as in its conf.py), /vector/docs/ and /, so each nav section is
active on a real rendered page. The /docs/ build is also the guard
self-test's input. The /vector/docs/ build sets html_last_updated_fmt, for
the docbuild:last-update meta. Each of the three is then indexed with the
pinned Pagefind, as consumers do, and the tests read back what it indexed.
One more build sets html_permalinks_icon, which the theme must leave alone.
"""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

import pagefind_index
from kinetis_website_theme.nav import SEARCH_BUNDLES

REPO = Path(__file__).resolve().parents[1]
SAMPLE = REPO / "tests" / "sample-site"

BASEURLS = {
    "Docs": "https://kinetis.dev/docs/",
    "Vector": "https://kinetis.dev/vector/docs/",
    "Home": "https://kinetis.dev/",
}
NAV_HREFS = {"Home": "/", "Docs": "/docs/", "Vector": "/vector/docs/", "Blog": "/blog/"}
FAVICONS = [
    {"rel": "icon", "type": "image/svg+xml", "href": "/assets/favicon.svg"},
    {"rel": "icon", "href": "/assets/favicon.ico", "sizes": "256x256"},
    {"rel": "apple-touch-icon", "href": "/assets/favicon.png", "sizes": "256x256"},
]
NOINDEX_PAGES = {"internal.html", "404.html"}
GITHUB = "https://github.com/kinetis-dev"
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
PACKAGIST = "https://packagist.org/packages/kinetis/"

# Extra -D options per build.
BUILD_OPTIONS = {"Vector": ["-D", "html_last_updated_fmt=%Y-%m-%d"]}
PERMALINK_OVERRIDE = "¶"

# Pagefind's URL and title of every page it must index: the source documents
# that are not noindex. 404 and internal are noindex; genindex, search and
# py-modindex are Sphinx's own pages.
INDEXED = {
    "/": "Kinetis",
    "/agents.html": "AI agents",
    "/auth.html": "Authentication",
    "/guide.html": "Configuration guide",
    "/logging.html": "Logging",
    "/persistence.html": "Persistence",
    "/queue.html": "Queues & retries",
    "/reference.html": "The kinetis reference",
    "/runtime.html": "Runtime adapters",
    "/storage.html": "Storage",
    "/tutorial.html": "Tutorial",
}
NOT_INDEXED = ["404.html", "internal.html", "genindex.html", "search.html", "py-modindex.html"]
SEARCH_SECTIONS = {"Docs": "Docs", "Vector": "Vector", "Home": "Main"}
SPHINX_SEARCH_SCRIPTS = ("searchtools.js", "language_data.js", "searchindex.js")

BUILDS = {}
BUILD_OUTPUT = {}
INDEX_OUTPUT = {}
FRAGMENTS = {}
OVERRIDE = {}


def load_guard():
    spec = importlib.util.spec_from_file_location("check_url_baseline", REPO / "tools" / "check_url_baseline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sphinx(out, *options, cwd):
    return subprocess.run(
        [sys.executable, "-m", "sphinx", "-W", "--keep-going", "-E", "-b", "html", *options, str(SAMPLE), str(out)],
        # Outside the repo, so `python -m` imports the installed theme, not ./kinetis_website_theme.
        capture_output=True, text=True, cwd=cwd,
    )


def setUpModule():
    root = Path(tempfile.mkdtemp(prefix="kinetis-sample-"))
    unittest.addModuleCleanup(shutil.rmtree, root)
    for section, baseurl in BASEURLS.items():
        out = root / section
        BUILD_OUTPUT[section] = sphinx(out, "-D", f"html_baseurl={baseurl}", *BUILD_OPTIONS.get(section, []), cwd=root)
        BUILDS[section] = out
        INDEX_OUTPUT[section] = pagefind_index.index(out)
        FRAGMENTS[section] = pagefind_index.fragments(out)
    out = OVERRIDE["build"] = root / "permalinks"
    OVERRIDE["output"] = sphinx(out, "-D", f"html_permalinks_icon={PERMALINK_OVERRIDE}", cwd=root)


class Page(HTMLParser):
    """The parts of a built page the assertions look at."""

    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.raw = path.read_text(encoding="utf-8")
        self.in_head = False
        self.title = None
        self._title = None
        self.icons = []
        self.robots = []
        self.navs = []
        self._nav_depth = 0
        self._nav_link = None
        self.github_links = []
        self.header_github_links = []
        self._header_depth = 0
        self.packagist_links = []
        self.articles = []
        self.role_main = []
        self.feed(self.raw)
        self.close()

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "head":
            self.in_head = True
        elif tag == "body":
            self.in_head = False
        if self.in_head:
            if tag == "title" and self.title is None:
                self._title = []
            elif tag == "link" and a.get("rel") in ("icon", "apple-touch-icon", "shortcut icon"):
                self.icons.append({k: v for k, v in a.items()})
            elif tag == "meta" and a.get("name") == "robots":
                self.robots.append(a.get("content"))
            return
        if self._header_depth and tag not in VOID_TAGS:
            self._header_depth += 1
        elif tag == "header" and "bd-header" in a.get("class", "").split():
            self._header_depth = 1
        if tag == "a" and self._header_depth and "github.com" in a.get("href", ""):
            self.header_github_links.append(a["href"])
        if tag == "nav" and "kinetis-nav" in a.get("class", "").split():
            self._nav_depth = 1
            self.navs.append([])
        elif tag == "nav" and self._nav_depth:
            self._nav_depth += 1
        if tag == "a" and self._nav_depth:
            self._nav_link = dict(a, text="")
            self.navs[-1].append(self._nav_link)
        if tag == "a" and "github.com" in a.get("href", ""):
            self.github_links.append(a["href"])
        if tag == "a" and "packagist.org" in a.get("href", ""):
            self.packagist_links.append(a["href"])
        if tag == "article":
            self.articles.append(a)
        if a.get("role") == "main":
            self.role_main.append((tag, a))

    def handle_endtag(self, tag):
        if self._header_depth and tag not in VOID_TAGS:
            self._header_depth -= 1
        if tag == "head":
            self.in_head = False
        elif tag == "title" and self._title is not None:
            self.title = "".join(self._title)
            self._title = None
        elif tag == "nav" and self._nav_depth:
            self._nav_depth -= 1
        elif tag == "a":
            self._nav_link = None

    def handle_data(self, data):
        if self._title is not None:
            self._title.append(data)
        if self._nav_link is not None:
            self._nav_link["text"] += data.strip()



def pages(section):
    build = BUILDS[section]
    return {
        p.relative_to(build).as_posix(): p
        for p in build.rglob("*.html")
        if p.relative_to(build).parts[0] not in ("_static", "pagefind")
    }


def page(section, name):
    return Page(BUILDS[section] / name)


class BuildTest(unittest.TestCase):
    def test_builds_are_clean_under_w_keep_going(self):
        for section, result in BUILD_OUTPUT.items():
            with self.subTest(section=section):
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertNotIn("WARNING", result.stdout + result.stderr)

    def test_theme_static_files_are_shipped(self):
        static = BUILDS["Docs"] / "_static"
        for name in ("kinetis.css", "logo.svg", "logo-h.svg"):
            self.assertTrue((static / name).is_file(), name)
        self.assertIn('href="_static/kinetis.css', page("Docs", "guide.html").raw)

    def test_landing_stylesheet_is_linked_on_no_docs_page(self):
        # Shipped with the theme, linked only by kinetis/landing.html pages.
        self.assertTrue((BUILDS["Docs"] / "_static" / "kinetis-landing.css").is_file())
        for section in BUILDS:
            for name in pages(section):
                with self.subTest(section=section, page=name):
                    self.assertNotIn("kinetis-landing", page(section, name).raw)


class NavTest(unittest.TestCase):
    def assertActive(self, section, name, expected):
        navs = page(section, name).navs
        # The header nav, plus pydata's copy of navbar_center in the mobile sidebar.
        self.assertEqual(2, len(navs), name)
        for links in navs:
            self.assertEqual(list(NAV_HREFS), [link["text"] for link in links], name)
            self.assertEqual(list(NAV_HREFS.values()), [link["href"] for link in links], name)
            active = [link["text"] for link in links if link.get("aria-current") == "page"]
            self.assertEqual([expected] if expected else [], active, f"{section} build, {name}")
            for link in links:
                is_active = link.get("aria-current") == "page"
                self.assertEqual(is_active, "active" in link["class"].split(), f"{name}: {link['text']}")

    def test_docs_section_is_active_on_every_docs_page(self):
        for name in pages("Docs"):
            with self.subTest(page=name):
                self.assertActive("Docs", name, "Docs")

    def test_vector_section_is_active_on_every_vector_page(self):
        for name in pages("Vector"):
            with self.subTest(page=name):
                self.assertActive("Vector", name, "Vector")

    def test_home_is_active_on_the_site_root_only(self):
        self.assertActive("Home", "index.html", "Home")
        for name in ("guide.html", "tutorial.html", "404.html"):
            with self.subTest(page=name):
                self.assertActive("Home", name, None)

    def test_docs_pages_link_vector_and_blog(self):
        for name in pages("Docs"):
            with self.subTest(page=name):
                raw = page("Docs", name).raw
                self.assertEqual(2, raw.count('<a class="nav-link nav-internal" href="/vector/docs/">Vector</a>'))
                self.assertEqual(2, raw.count('<a class="nav-link nav-internal" href="/blog/">Blog</a>'))

    def test_brand_links_to_the_marketing_site(self):
        self.assertIn('<a class="navbar-brand logo" href="https://kinetis.dev/"', page("Docs", "guide.html").raw)
        self.assertIn('src="_static/logo-h.svg"', page("Docs", "guide.html").raw)

    def test_github_link_is_the_footer_one_to_the_org(self):
        for section in BUILDS:
            for name in ("index.html", "guide.html"):
                with self.subTest(section=section, page=name):
                    parsed = page(section, name)
                    self.assertEqual([GITHUB], parsed.github_links)  # the footer's
                    self.assertIn(f'<a href="{GITHUB}">GitHub</a>', parsed.raw)

    def test_header_links_nowhere_on_github(self):
        for section in BUILDS:
            for name in pages(section):
                with self.subTest(section=section, page=name):
                    parsed = page(section, name)
                    self.assertEqual([], parsed.header_github_links)
                    self.assertEqual(0, parsed._header_depth, "unbalanced .bd-header")
                    self.assertNotIn("navbar-icon-links", parsed.raw)

    def test_packagist_link_goes_to_the_vendor_page(self):
        for section in BUILDS:
            for name in ("index.html", "guide.html"):
                with self.subTest(section=section, page=name):
                    self.assertEqual([PACKAGIST], page(section, name).packagist_links)

    def test_sidebar_is_the_global_toctree_with_every_caption(self):
        raw = page("Docs", "guide.html").raw
        captions = [
            "Start here", "Building an application", "Working with data", "Background work",
            "Authentication and sessions", "Runtime and performance", "Observability",
            "Integrations", "AI agents", "Reference",
        ]
        positions = [raw.find(f'<span class="caption-text">{c}</span>') for c in captions]
        self.assertNotIn(-1, positions)
        self.assertEqual(sorted(positions), positions)
        self.assertIn('href="index.html">Home</a>', raw)
        self.assertIn('class="toctree-l1 current active"><a aria-current="page" class="current reference internal" href="#">Configuration guide</a>', raw)


class HeadTest(unittest.TestCase):
    def test_three_favicon_links_root_relative(self):
        for name in pages("Docs"):
            with self.subTest(page=name):
                self.assertEqual(FAVICONS, page("Docs", name).icons)

    def test_root_title_has_no_suffix(self):
        self.assertEqual("Kinetis", page("Docs", "index.html").title)
        self.assertIn("<title>Kinetis</title>", page("Docs", "index.html").raw)

    def test_subpage_titles_use_hyphen_minus(self):
        self.assertEqual("Tutorial - Kinetis", page("Docs", "tutorial.html").title)
        self.assertEqual("Index - Kinetis", page("Docs", "genindex.html").title)
        self.assertEqual("Search - Kinetis", page("Docs", "search.html").title)
        # Furo's escaping, byte for byte: &amp; in the source, inline markup stripped.
        self.assertIn("<title>Queues &amp; retries - Kinetis</title>", page("Docs", "queue.html").raw)
        self.assertIn("<title>The kinetis reference - Kinetis</title>", page("Docs", "reference.html").raw)
        for name in pages("Docs"):
            if name == "index.html":
                continue
            with self.subTest(page=name):
                title = page("Docs", name).title
                self.assertTrue(title.endswith(" - Kinetis"), title)
                self.assertNotIn("—", title)
                self.assertNotIn("–", title)

    def test_noindex_only_on_404_and_front_matter_pages(self):
        for name in pages("Docs"):
            with self.subTest(page=name):
                expected = ["noindex"] if name in NOINDEX_PAGES else []
                self.assertEqual(expected, page("Docs", name).robots)

    def test_canonical_and_og_url_are_the_deployed_url(self):
        raw = page("Docs", "guide.html").raw
        self.assertIn('<link rel="canonical" href="https://kinetis.dev/docs/guide.html" />', raw)
        self.assertIn('<meta property="og:url" content="https://kinetis.dev/docs/guide.html" />', raw)

    def test_article_is_the_pagefind_body_and_not_a_landmark(self):
        articles = page("Docs", "guide.html").articles
        self.assertEqual(1, len(articles))
        self.assertNotIn("role", articles[0])
        self.assertIn("data-pagefind-body", articles[0])

    def test_every_page_has_one_main_landmark(self):
        for section in BUILDS:
            for name in pages(section):
                with self.subTest(section=section, page=name):
                    landmarks = page(section, name).role_main
                    self.assertEqual(1, len(landmarks), landmarks)
                    self.assertEqual("main", landmarks[0][0])
                    self.assertEqual("main-content", landmarks[0][1].get("id"))


class GuardSelfTest(unittest.TestCase):
    def test_guard_passes_on_the_sample_build(self):
        result = subprocess.run(
            [sys.executable, str(REPO / "tools" / "check_url_baseline.py"), "check", str(BUILDS["Docs"])],
            capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("url baseline: 0 violation(s)", result.stdout)

    def test_guard_fails_when_one_anchor_is_removed(self):
        scratch = Path(tempfile.mkdtemp(prefix="kinetis-guard-"))
        self.addCleanup(shutil.rmtree, scratch)
        build = scratch / "html"
        shutil.copytree(BUILDS["Docs"], build)
        guide = build / "guide.html"
        html = guide.read_text(encoding="utf-8")
        self.assertEqual(1, html.count('id="environment-variables"'))
        guide.write_text(html.replace('id="environment-variables"', ""), encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(REPO / "tools" / "check_url_baseline.py"), "check", str(build)],
            capture_output=True, text=True,
        )
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn('anchor guide.html#environment-variables: missing from the main landmark', result.stdout)
        self.assertEqual(
            ['anchor guide.html#environment-variables: missing from the main landmark'],
            load_guard().check(build),
        )


class HeadElements(HTMLParser):
    """Every start tag in <head>, in order, as (tag, attributes)."""

    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self._in_head = False
        self.feed(raw)
        self.close()

    def handle_starttag(self, tag, attrs):
        if tag == "head":
            self._in_head = True
        elif self._in_head:
            self.elements.append((tag, {k: (v or "") for k, v in attrs}))

    def handle_endtag(self, tag):
        if tag == "head":
            self._in_head = False


def head(section, name):
    return HeadElements(page(section, name).raw).elements


def body_markers(raw):
    """The data-pagefind-body elements of a page, as their opening tags."""
    return re.findall(r"<[a-z]+ [^>]*\bdata-pagefind-body\b[^>]*>", raw)


# pydata 0.23.0's extrahead block, verbatim. layout.html copies it without
# the three script lines; when the pin moves and this changes, re-copy it.
PYDATA_EXTRAHEAD = """{%- block extrahead %}
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta name="color-scheme" content="light dark"/>
  <meta name="docsearch:language" content="{{ language }}"/>
  <meta name="docsearch:version" content="{{ version }}" />
  {%- if last_updated %}
    <meta name="docbuild:last-update" content="{{ last_updated | e }}"/>
  {%- endif %}
  {% if pagename == 'search' %}
    {# Search tools are already loaded on search page. Don't load them twice. #}
  {% else %}
    {# Load Sphinx's built-in search tools so that our custom inline search
       experience can work on any page. #}
    <script src="{{ pathto('_static/searchtools.js', 1) | e }}"></script>
    <script src="{{ pathto('_static/language_data.js', 1) | e }}"></script>
    <script src="{{ pathto('searchindex.js', 1) | e }}"></script>
  {% endif %}
{%- endblock extrahead %}"""


class SearchIndexTest(unittest.TestCase):
    """What the pinned Pagefind indexes in each build (docs/SEARCH.md §2, §3)."""

    def test_pagefind_is_the_pinned_version(self):
        self.assertEqual(f"pagefind {pagefind_index.PAGEFIND_VERSION}", pagefind_index.version())

    def test_every_build_indexes(self):
        for section, result in INDEX_OUTPUT.items():
            with self.subTest(section=section):
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertTrue((BUILDS[section] / "pagefind" / "pagefind-entry.json").is_file())

    def test_exactly_the_source_documents_that_are_not_noindex_are_indexed(self):
        for section in BUILDS:
            with self.subTest(section=section):
                self.assertEqual(sorted(INDEXED), sorted(FRAGMENTS[section]))
        for name in NOT_INDEXED:
            self.assertIn(name, pages("Docs"))

    def test_only_indexed_pages_carry_the_body_marker_and_title_meta(self):
        indexed = {"index.html" if url == "/" else url.lstrip("/") for url in INDEXED}
        for section in BUILDS:
            for name in pages(section):
                with self.subTest(section=section, page=name):
                    raw = page(section, name).raw
                    titles = [a for tag, a in head(section, name)
                              if tag == "meta" and a.get("data-pagefind-meta") == "title[content]"]
                    self.assertEqual(1 if name in indexed else 0, len(body_markers(raw)))
                    self.assertEqual(1 if name in indexed else 0, len(titles))

    def test_titles_are_the_page_titles_without_the_permalink_sign(self):
        for section in BUILDS:
            for url, fragment in FRAGMENTS[section].items():
                with self.subTest(section=section, url=url):
                    self.assertEqual(INDEXED[url], fragment["meta"]["title"])
                    self.assertNotIn("#", fragment["meta"]["title"])
                    self.assertNotIn("#", fragment["content"])

    def test_every_page_has_its_section_as_filter_and_meta(self):
        for section, expected in SEARCH_SECTIONS.items():
            for url, fragment in FRAGMENTS[section].items():
                with self.subTest(section=section, url=url):
                    self.assertEqual({"section": [expected]}, fragment["filters"])
                    self.assertEqual(expected, fragment["meta"]["section"])

    def test_the_article_is_the_body(self):
        self.assertEqual(
            ['<article class="bd-article" data-pagefind-body data-pagefind-filter="section:Docs"'
             ' data-pagefind-meta="section:Docs">'],
            body_markers(page("Docs", "guide.html").raw))


class PermalinkTest(unittest.TestCase):
    HEADERLINK = re.compile(r'<a class="headerlink" [^>]*>(.*?)</a>')

    def test_the_default_icon_is_kept_out_of_the_index(self):
        icons = self.HEADERLINK.findall(page("Docs", "guide.html").raw)
        self.assertEqual(3, len(icons))
        self.assertEqual({"<span data-pagefind-ignore>#</span>"}, set(icons))

    def test_a_consumer_icon_is_left_alone(self):
        self.assertEqual(0, OVERRIDE["output"].returncode, OVERRIDE["output"].stdout + OVERRIDE["output"].stderr)
        icons = self.HEADERLINK.findall((OVERRIDE["build"] / "guide.html").read_text(encoding="utf-8"))
        self.assertEqual(3, len(icons))
        self.assertEqual({PERMALINK_OVERRIDE}, set(icons))


class ExtraheadTest(unittest.TestCase):
    """layout.html's extrahead: pydata's, without Sphinx's search scripts (docs/SEARCH.md §5)."""

    def test_pydatas_block_is_the_one_layout_html_copies(self):
        import pydata_sphinx_theme

        layout = Path(pydata_sphinx_theme.__file__).parent / "theme" / "pydata_sphinx_theme" / "layout.html"
        text = layout.read_text(encoding="utf-8")
        start = text.index("{%- block extrahead %}")
        end = text.index("{%- endblock extrahead %}") + len("{%- endblock extrahead %}")
        self.assertEqual(PYDATA_EXTRAHEAD, text[start:end])
        ours = (REPO / "kinetis_website_theme" / "theme" / "kinetis_website_theme" / "layout.html").read_text(encoding="utf-8")
        kept = PYDATA_EXTRAHEAD[: PYDATA_EXTRAHEAD.index("  {% if pagename == 'search' %}")]
        self.assertIn(kept, ours)

    def expected(self, last_updated=None, noindex=False, title=None):
        elements = [
            ("meta", {"name": "viewport", "content": "width=device-width, initial-scale=1"}),
            ("meta", {"name": "color-scheme", "content": "light dark"}),
            ("meta", {"name": "docsearch:language", "content": "en"}),
            ("meta", {"name": "docsearch:version", "content": ""}),
        ]
        if last_updated:
            elements.append(("meta", {"name": "docbuild:last-update", "content": last_updated}))
        elements += [("link", icon) for icon in FAVICONS]
        if noindex:
            elements.append(("meta", {"name": "robots", "content": "noindex"}))
        if title:
            elements.append(("meta", {"data-pagefind-meta": "title[content]", "content": title}))
        return elements

    def tail(self, section, name):
        """The head from the extrahead block's viewport meta on: that block's output.

        The same viewport meta is also in pydata's metatags, earlier; the
        block's is the last one.
        """
        elements = head(section, name)
        viewport = ("meta", {"name": "viewport", "content": "width=device-width, initial-scale=1"})
        start = len(elements) - 1 - elements[::-1].index(viewport)
        return elements[start:]

    def test_output_in_order(self):
        self.assertEqual(self.expected(title="Configuration guide"), self.tail("Docs", "guide.html"))
        self.assertEqual(self.expected(noindex=True), self.tail("Docs", "404.html"))
        self.assertEqual(self.expected(), self.tail("Docs", "search.html"))
        last_updated = [a["content"] for tag, a in head("Vector", "guide.html") if a.get("name") == "docbuild:last-update"]
        self.assertEqual(1, len(last_updated))
        self.assertRegex(last_updated[0], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(self.expected(last_updated=last_updated[0], title="Configuration guide"),
                         self.tail("Vector", "guide.html"))

    def test_no_page_loads_sphinx_search_scripts(self):
        for section in BUILDS:
            for name in pages(section):
                with self.subTest(section=section, page=name):
                    raw = page(section, name).raw
                    for script in SPHINX_SEARCH_SCRIPTS:
                        self.assertNotRegex(raw, r'<script [^>]*src="[^"]*' + re.escape(script), script)

    def test_sphinx_still_writes_its_search_index(self):
        self.assertTrue((BUILDS["Docs"] / "searchindex.js").is_file())


class SearchUITest(unittest.TestCase):
    """The static markup kinetis-search.js builds on (docs/SEARCH.md §4.3, §5)."""

    def test_two_empty_placeholders_and_no_pagefind_element_or_pydata_search(self):
        for section in BUILDS:
            for name in pages(section):
                with self.subTest(section=section, page=name):
                    raw = page(section, name).raw
                    # Wide and narrow copies of navbar_persistent.
                    self.assertEqual(2, raw.count('<div class="kinetis-search"></div>'))
                    self.assertNotIn("<pagefind-", raw)
                    self.assertNotIn("pst-search-dialog", raw)
                    self.assertNotIn("search-button", raw)

    def test_the_script_is_deferred_with_the_bundle_list(self):
        for name in ("index.html", "guide.html", "search.html", "404.html"):
            with self.subTest(page=name):
                scripts = [a for tag, a in head("Docs", name)
                           if tag == "script" and a.get("src", "").split("?")[0].endswith("kinetis-search.js")]
                self.assertEqual(1, len(scripts))
                self.assertEqual("defer", scripts[0]["defer"])
                self.assertEqual(list(SEARCH_BUNDLES), json.loads(scripts[0]["data-kinetis-bundles"]))
        self.assertTrue((BUILDS["Docs"] / "_static" / "kinetis-search.js").is_file())

    def test_search_page(self):
        parsed = page("Docs", "search.html")
        raw = parsed.raw
        self.assertEqual("Search - Kinetis", parsed.title)
        self.assertIn("<h1>Search</h1>", raw)
        self.assertIn("<noscript>", raw)
        self.assertRegex(raw, r'<div id="search-results">\s*<div id="kinetis-search-page"></div>\s*</div>')
        self.assertEqual([], body_markers(raw))
        # Inside the main landmark, where the consumers' URL guards look for it.
        self.assertIn("search-results", load_guard().parse_page(BUILDS["Docs"] / "search.html").main_ids)


if __name__ == "__main__":
    unittest.main()
