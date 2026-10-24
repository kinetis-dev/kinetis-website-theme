"""Build tests/sample-site with the installed theme and assert on its HTML.

The site is built three times with `-W --keep-going`, with html_baseurl at
/docs/ (as in its conf.py), /vector/docs/ and /, so each nav section is
active on a real rendered page. The /docs/ build is also the guard
self-test's input.
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SAMPLE = REPO / "tests" / "sample-site"

BASEURLS = {
    "Docs": "https://kinetis.dev/docs/",
    "Vector": "https://kinetis.dev/vector/docs/",
    "Home": "https://kinetis.dev/",
}
NAV_HREFS = {"Home": "/", "Docs": "/docs/", "Vector": "/vector/docs/"}
FAVICONS = [
    {"rel": "icon", "type": "image/svg+xml", "href": "/assets/favicon.svg"},
    {"rel": "icon", "href": "/assets/favicon.ico", "sizes": "256x256"},
    {"rel": "apple-touch-icon", "href": "/assets/favicon.png", "sizes": "256x256"},
]
NOINDEX_PAGES = {"internal.html", "404.html"}
GITHUB = "https://github.com/kinetis-dev"
PACKAGIST = "https://packagist.org/packages/kinetis/framework"

BUILDS = {}
BUILD_OUTPUT = {}


def load_guard():
    spec = importlib.util.spec_from_file_location("check_url_baseline", REPO / "tools" / "check_url_baseline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def setUpModule():
    root = Path(tempfile.mkdtemp(prefix="kinetis-sample-"))
    unittest.addModuleCleanup(shutil.rmtree, root)
    for section, baseurl in BASEURLS.items():
        out = root / section
        result = subprocess.run(
            [sys.executable, "-m", "sphinx", "-W", "--keep-going", "-E", "-b", "html",
             "-D", f"html_baseurl={baseurl}", str(SAMPLE), str(out)],
            # Outside the repo, so `python -m` imports the installed theme, not ./kinetis_website_theme.
            capture_output=True, text=True, cwd=root,
        )
        BUILDS[section] = out
        BUILD_OUTPUT[section] = result


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
        self.packagist_links = []
        self.articles = []
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

    def handle_endtag(self, tag):
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
        if p.relative_to(build).parts[0] != "_static"
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
        for name in ("kinetis.css", "logo.svg"):
            self.assertTrue((static / name).is_file(), name)
        self.assertIn('href="_static/kinetis.css', page("Docs", "guide.html").raw)


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

    def test_brand_links_to_the_marketing_site(self):
        self.assertIn('<a class="navbar-brand logo" href="https://kinetis.dev/"', page("Docs", "guide.html").raw)

    def test_github_links_go_to_the_org(self):
        for section in BUILDS:
            for name in ("index.html", "guide.html"):
                with self.subTest(section=section, page=name):
                    links = page(section, name).github_links
                    self.assertGreaterEqual(len(links), 2)  # navbar icon and footer
                    self.assertEqual({GITHUB}, set(links))

    def test_packagist_link_goes_to_the_framework_package(self):
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

    def test_article_is_role_main_and_the_pagefind_body(self):
        articles = page("Docs", "guide.html").articles
        self.assertEqual(1, len(articles))
        self.assertEqual("main", articles[0].get("role"))
        self.assertIn("data-pagefind-body", articles[0])


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
        self.assertIn('anchor guide.html#environment-variables: missing from <article role="main">', result.stdout)
        self.assertEqual(
            ['anchor guide.html#environment-variables: missing from <article role="main">'],
            load_guard().check(build),
        )


if __name__ == "__main__":
    unittest.main()
