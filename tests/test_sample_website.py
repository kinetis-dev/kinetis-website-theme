"""Build tests/sample-website with the installed theme and assert on it.

The sample website is shaped like kinetis.dev as a Sphinx project (design
5.1, 5.2, 5.4): the landing and 404 bodies of tests/website-inputs/, an
ablog blog, directory-style index URLs and the sitemap pruner. It is built
with `-W --keep-going`, and again at `-j 2`: the pruner must not depend on
state lost when pages are written in worker processes. ablog is not safe for
parallel reading, so that build warns twice (untyped warnings, which
suppress_warnings cannot reach) and runs without -W; the test asserts those
are its only warnings. One more build switches the pruner off (the sitemap
assertion must then fail), and one never writes a sitemap (the build must
then fail). Two rebuild an output directory without -E: one after touching
a post (the sitemap must come out the same), one in which sphinx-sitemap
writes nothing (the previous, already-pruned sitemap must not be pruned
again; the build fails instead). The docs sample, tests/sample-site, is
built once too, for the assertions every page of both samples must meet:
the default header height and the one shared footer.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
# Parses only sitemaps and feeds this test just built.
import xml.etree.ElementTree as ET  # nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SAMPLE = REPO / "tests" / "sample-website"
DOCS_SAMPLE = REPO / "tests" / "sample-site"
INPUTS = REPO / "tests" / "website-inputs"

SITE = "https://kinetis.dev/"
SITEMAP = "main-sitemap.xml"
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
ALLOWED_LOCS = {
    "https://kinetis.dev/",
    "https://kinetis.dev/blog/",
    "https://kinetis.dev/blog/posts/hello-kinetis.html",
    "https://kinetis.dev/blog/posts/second-post.html",
}
LANDING_TITLE = "Kinetis: A Complete PHP Framework, Built for Speed"
NOT_FOUND_TITLE = "Page not found — Kinetis"
# ablog's listings (blog.html is its own root listing) and Sphinx's search page.
LISTINGS = [
    "blog.html", "blog/tag.html", "blog/tag/php.html", "blog/tag/release.html",
    "blog/category.html", "blog/category/news.html", "blog/category/engineering.html",
    "blog/archive.html", "blog/2026.html", "blog/author.html", "blog/author/kinetis.html",
    "blog/drafts.html", "search.html",
]
POSTS = ["blog/posts/hello-kinetis.html", "blog/posts/second-post.html"]
LANDING_CSS = "_static/kinetis-landing.css"
GITHUB = "https://github.com/kinetis-dev"
FOOTER = '<p class="kinetis-footer">'

BUILDS = {}
RESULTS = {}


ABLOG_PARALLEL_WARNINGS = [
    "WARNING: the ablog extension is not safe for parallel reading",
    "WARNING: doing serial read",
]


def sphinx(src, out, *options, cwd, strict=True, fresh=True):
    return subprocess.run(
        # -N: CI forces colour, and ANSI codes would break the exact warning match.
        [sys.executable, "-m", "sphinx", "-N", *(["-W"] if strict else []), "--keep-going", *(["-E"] if fresh else []),
         "-b", "html", *options, str(src), str(out)],
        # Outside the repo, so `python -m` imports the installed theme, not ./kinetis_website_theme.
        capture_output=True, text=True, cwd=cwd,
    )


def variant(root, name, conf_lines):
    """A copy of the sample website with lines appended to its conf.py."""
    src = root / f"src-{name}"
    shutil.copytree(SAMPLE, src)
    with open(src / "conf.py", "a", encoding="utf-8") as conf:
        conf.write("\n# Test variant.\n" + "".join(line + "\n" for line in conf_lines))
    return src


def setUpModule():
    root = Path(tempfile.mkdtemp(prefix="kinetis-website-"))
    unittest.addModuleCleanup(shutil.rmtree, root)
    # kinetis_* values cannot be overridden with -D: the theme registers them
    # after Sphinx has applied overrides, and -W fails on the warning.
    builds = {
        "serial": (SAMPLE, ()),
        "parallel": (SAMPLE, ("-j", "2")),
        "unpruned": (variant(root, "unpruned", ["kinetis_prune_sitemap = False"]), ()),
        "no-sitemap": (SAMPLE, ("-D", "sitemap_excludes=*")),
    }
    for name, (src, options) in builds.items():
        out = root / name
        RESULTS[name] = sphinx(src, out, *options, cwd=root, strict=name != "parallel")
        BUILDS[name] = out

    # Rebuilds of an existing output directory, without -E.
    src = variant(root, "incremental", [])
    out = BUILDS["incremental"] = root / "incremental"
    RESULTS["incremental-first"] = sphinx(src, out, cwd=root)
    post = src / "blog" / "posts" / "second-post.md"
    later = post.stat().st_mtime + 10
    os.utime(post, (later, later))
    RESULTS["incremental"] = sphinx(src, out, cwd=root, fresh=False)

    out = BUILDS["stale"] = root / "stale"
    RESULTS["stale-first"] = sphinx(SAMPLE, out, cwd=root)
    RESULTS["stale"] = sphinx(SAMPLE, out, "-D", "sitemap_excludes=*", cwd=root, fresh=False)

    out = BUILDS["docs-sample"] = root / "docs-sample"
    RESULTS["docs-sample"] = sphinx(DOCS_SAMPLE, out, cwd=root)


class Page(HTMLParser):
    """The parts of a built page the assertions look at."""

    WHITELIST_META = re.compile(r"^(description|og:.*|twitter:.*)$")

    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.raw = path.read_text(encoding="utf-8")
        self.in_head = False
        self.title = None
        self._title = None
        self.whitelist = []
        self.robots = []
        self.og_properties = []
        self.stylesheets = []
        self.urls = []
        self.landmarks = []
        self.classes = []
        self.elements = []
        self.feed(self.raw)
        self.close()

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "head":
            self.in_head = True
        elif tag == "body":
            self.in_head = False
        for key in ("href", "src", "action"):
            if key in a:
                self.urls.append((tag, key, a[key]))
        if tag == "link" and a.get("rel") == "stylesheet":
            self.stylesheets.append(a.get("href", ""))
        self.classes.extend(a.get("class", "").split())
        self.elements.append((tag, a))
        if tag == "main" or a.get("role") == "main":
            self.landmarks.append((tag, a))
        if not self.in_head:
            return
        if tag == "title" and self.title is None:
            self._title = []
        elif tag == "meta":
            key = a.get("name") or a.get("property") or ""
            if key == "robots":
                self.robots.append(a.get("content"))
            if a.get("property", "").startswith("og:"):
                self.og_properties.append(a["property"])
            if self.WHITELIST_META.match(key):
                attr = "name" if "name" in a else "property"
                self.whitelist.append(("meta", attr, key, a.get("content")))
        elif tag == "link" and a.get("rel") == "canonical":
            self.whitelist.append(("link", "canonical", a.get("href")))
        elif tag == "link" and a.get("rel") in ("icon", "apple-touch-icon"):
            self.whitelist.append(("link", a["rel"], a.get("type"), a.get("href"), a.get("sizes")))

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False
        elif tag == "title" and self._title is not None:
            self.title = "".join(self._title)
            self._title = None
            self.whitelist.append(("title", self.title))

    def handle_data(self, data):
        if self._title is not None:
            self._title.append(data)


class TextParser(HTMLParser):
    """The whitespace-normalised text of an HTML fragment."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.feed(html)
        self.close()

    def handle_data(self, data):
        self.parts.append(data)

    @property
    def text(self):
        return " ".join("".join(self.parts).split())


def page(name, build="serial"):
    return Page(BUILDS[build] / name)


def html_pages(build="serial"):
    out = BUILDS[build]
    return sorted(p.relative_to(out).as_posix() for p in out.rglob("*.html") if p.relative_to(out).parts[0] != "_static")


def input_head(name):
    parsed = Page(INPUTS / name)
    return parsed


INPUT_FOOTER = re.compile(r"\s*<footer>.*?</footer>", re.DOTALL)


def input_body(name):
    """The input page's <body> content, with the two allowed deviations:
    <main class="tiles"> demoted to <div class="tiles"> (pydata's <main> is
    the page's only landmark), and the input's single <footer> element
    removed with the whitespace before it (pydata's footer with the shared
    kinetis-footer is the page's only footer)."""
    raw = (INPUTS / name).read_text(encoding="utf-8")
    body = raw[raw.index("<body>\n") + len("<body>\n") : raw.index("</body>")]
    body = body.replace('<main class="tiles">', '<div class="tiles">').replace("</main>", "</div>")
    assert len(INPUT_FOOTER.findall(body)) == 1, f"{name}: expected exactly one <footer>"
    return INPUT_FOOTER.sub("", body)


def input_jsonld():
    raw = (INPUTS / "index.html").read_text(encoding="utf-8")
    start = raw.index('<script type="application/ld+json">')
    return raw[start : raw.index("</script>", start) + len("</script>")]


def landing_content(raw):
    """The markup inside <div class="kinetis-landing" ...>."""
    start = raw.index('<div class="kinetis-landing" data-pagefind-body>')
    end = raw.index("</main>", start)
    return raw[start:end]


def pydata_footer(raw):
    """The markup of pydata's <footer class="bd-footer">, the last footer on a page."""
    start = raw.index('<footer class="bd-footer">')
    return raw[start : raw.index("</footer>", start) + len("</footer>")]


def github_links(raw):
    return re.findall(r'<a [^>]*href="(https://github\.com[^"]*)"', raw)


def nav_links(raw):
    """(label, active) per link of each kinetis-nav: the header's and pydata's mobile copy."""
    navs = re.findall(r'<nav class="kinetis-nav" aria-label="Site">(.*?)</nav>', raw, re.DOTALL)
    return [
        [(label, 'aria-current="page"' in attrs)
         for attrs, label in re.findall(r"<a ([^>]*)>([^<]*)</a>", nav)]
        for nav in navs
    ]


def sitemap_locs(build):
    root = ET.parse(BUILDS[build] / SITEMAP).getroot()
    return [loc.text for loc in root.iter(f"{SITEMAP_NS}loc")]


class BuildTest(unittest.TestCase):
    def test_builds_are_clean_under_w_keep_going(self):
        for name in ("serial", "unpruned", "docs-sample"):
            with self.subTest(build=name):
                result = RESULTS[name]
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertNotIn("WARNING", result.stdout + result.stderr)

    def test_parallel_build_warns_only_that_ablog_reads_serially(self):
        result = RESULTS["parallel"]
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        warnings = [line for line in (result.stdout + result.stderr).splitlines() if "WARNING" in line]
        self.assertEqual(ABLOG_PARALLEL_WARNINGS, warnings)

    def test_a_missing_sitemap_fails_the_build_clearly(self):
        result = RESULTS["no-sitemap"]
        self.assertNotEqual(0, result.returncode)
        self.assertIn(f"kinetis_prune_sitemap: the sitemap", result.stdout + result.stderr)
        self.assertIn(f"{SITEMAP} does not exist", result.stdout + result.stderr)


class LandingTest(unittest.TestCase):
    def test_title_is_the_document_title_without_suffix(self):
        self.assertEqual(LANDING_TITLE, page("index.html").title)
        self.assertEqual(input_head("index.html").title, page("index.html").title)

    def test_canonical_and_og_url_are_the_site_root(self):
        raw = page("index.html").raw
        self.assertIn(f'<link rel="canonical" href="{SITE}" />', raw)
        self.assertIn(f'<meta property="og:url" content="{SITE}" />', raw)

    def test_head_whitelist_matches_the_input(self):
        expected = sorted(input_head("index.html").whitelist, key=repr)
        actual = sorted(page("index.html").whitelist, key=repr)
        self.assertEqual(expected, actual)

    def test_no_duplicate_og_tags(self):
        properties = page("index.html").og_properties
        self.assertEqual(sorted(set(properties)), sorted(properties))

    def test_json_ld_is_in_the_body_byte_identical(self):
        raw = page("index.html").raw
        head, body = raw.split("</head>", 1)
        self.assertNotIn("application/ld+json", head)
        self.assertEqual(1, body.count(input_jsonld()))
        json.loads(input_jsonld().split(">", 1)[1].rsplit("<", 1)[0])

    def test_body_is_the_input_body(self):
        content = landing_content(page("index.html").raw)
        self.assertIn(input_body("index.html"), content)

    def test_no_sidebars_or_article_chrome_but_pydata_footer(self):
        parsed = page("index.html")
        for cls in ("bd-sidebar-secondary", "sidebar-primary-items__start", "bd-article", "bd-header-article",
                    "prev-next-footer", "bd-footer-article", "bd-footer-content", "secondary-toggle"):
            with self.subTest(cls=cls):
                self.assertNotIn(cls, parsed.classes)
        self.assertEqual(1, parsed.classes.count("bd-footer"))
        self.assertEqual(1, [tag for tag, a in parsed.elements if "bd-footer" in a.get("class", "").split()].count("footer"))
        self.assertNotIn("article", [tag for tag, _ in parsed.elements])
        # The primary sidebar holds only the navbar items, for narrow screens.
        primary = [a for tag, a in parsed.elements if a.get("id") == "pst-primary-sidebar"]
        self.assertEqual(1, len(primary))
        self.assertIn("hide-on-wide", primary[0]["class"].split())

    def test_one_main_landmark_with_the_skip_link_target(self):
        for name in ("index.html", "404.html"):
            with self.subTest(page=name):
                landmarks = page(name).landmarks
                self.assertEqual(1, len(landmarks), landmarks)
                tag, attrs = landmarks[0]
                self.assertEqual(("main", "main-content", "main"), (tag, attrs.get("id"), attrs.get("role")))
                self.assertIn('href="#main-content"', page(name).raw)

    def test_home_is_active(self):
        raw = page("index.html").raw
        self.assertEqual(2, raw.count('<a class="nav-link nav-internal active" href="/" aria-current="page">Home</a>'))
        self.assertEqual(2, raw.count('aria-current="page"'))

    def test_default_header_height_and_pagefind_marks(self):
        # pydata's own 4rem header on every page of both samples, landing and 404 included.
        for build in ("serial", "docs-sample"):
            for name in html_pages(build):
                with self.subTest(build=build, page=name):
                    self.assertNotIn("--pst-header-height", page(name, build).raw)
        raw = page("index.html").raw
        self.assertIn('<header id="pst-header" class="bd-header navbar navbar-expand-lg bd-navbar d-print-none" data-pagefind-ignore>', raw)
        self.assertEqual(1, raw.count("data-pagefind-body"))
        self.assertIn('<div class="kinetis-landing" data-pagefind-body>', raw)

    def test_landing_and_404_link_github_only_in_the_footer_and_the_body(self):
        # Outside the body, the footer's organisation link is the only
        # github.com link, as on docs pages; the body keeps the input's own
        # "Source on GitHub" tile.
        for name in ("index.html", "404.html"):
            with self.subTest(page=name):
                raw = page(name).raw
                body = github_links(landing_content(raw))
                self.assertEqual(github_links(input_body(name)), body)
                self.assertNotIn(GITHUB, body)
                self.assertEqual([GITHUB], github_links(pydata_footer(raw)))
                self.assertEqual([*body, GITHUB], github_links(raw))

    def test_no_header_github_icon(self):
        self.assertNotIn("navbar-icon-links", page("index.html").raw)

    def test_landing_css_only_on_landing_pages(self):
        for name in html_pages():
            with self.subTest(page=name):
                linked = [href for href in page(name).stylesheets if "kinetis-landing.css" in href]
                self.assertEqual(1 if name in ("index.html", "404.html") else 0, len(linked), linked)
        self.assertTrue((BUILDS["serial"] / LANDING_CSS).is_file())
        self.assertTrue((BUILDS["serial"] / "_static" / "logo.svg").is_file())


class FooterTest(unittest.TestCase):
    def test_every_page_of_both_samples_has_the_one_shared_footer(self):
        # Docs pages, landing, 404, blog index, posts, listings and search.
        names = {"serial": html_pages("serial"), "docs-sample": html_pages("docs-sample")}
        for name in ("index.html", "404.html", "blog/index.html", *POSTS, *LISTINGS):
            self.assertIn(name, names["serial"])
        for name in ("guide.html", "404.html", "search.html", "genindex.html"):
            self.assertIn(name, names["docs-sample"])
        for build, pages in names.items():
            for name in pages:
                with self.subTest(build=build, page=name):
                    raw = page(name, build).raw
                    self.assertEqual(1, raw.count(FOOTER))
                    self.assertEqual(1, raw.count('<footer class="bd-footer">'))
                    self.assertEqual(1, pydata_footer(raw).count(FOOTER))

    def test_landing_bodies_carry_no_footer(self):
        for name in ("index.html", "404.html"):
            with self.subTest(page=name):
                self.assertNotIn("<footer", landing_content(page(name).raw))

    def test_the_footer_is_the_themes_kinetis_footer_unchanged(self):
        expected = pydata_footer(page("guide.html", "docs-sample").raw)
        for name in ("index.html", "404.html", "blog/index.html", POSTS[0], "blog.html"):
            with self.subTest(page=name):
                self.assertEqual(expected, pydata_footer(page(name).raw))
        self.assertIn(f'<a href="{GITHUB}">GitHub</a>', expected)
        self.assertIn('<a href="/docs/">Docs</a>', expected)


class WebsiteNavTest(unittest.TestCase):
    def assertActive(self, name, expected):
        navs = nav_links(page(name).raw)
        self.assertEqual(2, len(navs), name)
        for links in navs:
            self.assertEqual(["Home", "Docs", "Vector", "Blog"], [label for label, _ in links])
            self.assertEqual([expected] if expected else [], [label for label, active in links if active])

    def test_blog_is_active_on_the_blog_index_posts_and_root_listing(self):
        for name in ("blog/index.html", *POSTS, "blog.html", "blog/tag/php.html"):
            with self.subTest(page=name):
                self.assertActive(name, "Blog")

    def test_home_is_active_on_the_landing_and_nothing_on_404(self):
        self.assertActive("index.html", "Home")
        # The 404 page's deployed path is /404.html, which no item owns.
        self.assertActive("404.html", None)
        self.assertActive("search.html", None)


class NotFoundTest(unittest.TestCase):
    def test_title(self):
        self.assertEqual(NOT_FOUND_TITLE, page("404.html").title)
        self.assertEqual(input_head("404.html").title, page("404.html").title)

    def test_noindex(self):
        self.assertEqual(["noindex"], page("404.html").robots)

    def test_every_asset_and_link_is_absolute(self):
        # Served for any missing URL, e.g. /a/b/c/missing: nothing may be
        # page-relative, form actions (pydata's search) included.
        urls = page("404.html").urls
        self.assertIn(("form", "action", "/search.html"), urls)
        self.assertGreater(len(urls), 30)
        for tag, key, url in urls:
            with self.subTest(url=url):
                self.assertTrue(url.startswith(("/", "https://", "#")), (tag, key, url))
        hrefs = {url for _, _, url in urls}
        for asset in ("/_static/kinetis.css", "/_static/kinetis-landing.css", "/_static/styles/pydata-sphinx-theme.css",
                      "/_static/scripts/pydata-sphinx-theme.js", "/_static/logo-h.svg"):
            with self.subTest(asset=asset):
                self.assertTrue(any(url.split("?")[0] == asset for url in hrefs), asset)
        for icon in ("/assets/favicon.svg", "/assets/favicon.ico", "/assets/favicon.png"):
            self.assertIn(icon, hrefs)

    def test_body_matches_the_input(self):
        content = landing_content(page("404.html").raw)
        self.assertIn(input_body("404.html"), content)
        self.assertEqual(TextParser(input_body("404.html")).text, TextParser(content).text)

    def test_rendered_from_the_404_document(self):
        # sphinx-notfound-page renders the 404 document, not its own template.
        self.assertIn("This page moved, or never existed", page("404.html").raw)
        self.assertNotIn("Unfortunately we couldn't find the content", page("404.html").raw)


class BlogTest(unittest.TestCase):
    def test_blog_index_is_a_directory_url(self):
        raw = page("blog/index.html").raw
        self.assertIn(f'<link rel="canonical" href="{SITE}blog/" />', raw)
        self.assertIn(f'<meta property="og:url" content="{SITE}blog/" />', raw)

    def test_listings_are_noindex_and_blog_index_and_posts_are_not(self):
        built = set(html_pages())
        for name in LISTINGS:
            with self.subTest(page=name):
                self.assertIn(name, built)
                self.assertEqual(["noindex"], page(name).robots)
        for name in ["index.html", "blog/index.html", *POSTS]:
            with self.subTest(page=name):
                self.assertEqual([], page(name).robots)

    def test_atom_feed(self):
        feed = BUILDS["serial"] / "blog" / "atom.xml"
        self.assertTrue(feed.is_file())
        root = ET.parse(feed).getroot()
        atom = "{http://www.w3.org/2005/Atom}"
        self.assertEqual(2, len(root.findall(f"{atom}entry")))
        self.assertIn(f"{SITE}blog/atom.xml", [link.get("href") for link in root.findall(f"{atom}link")])

    def test_post_pages_use_the_ablog_sidebars(self):
        raw = page(POSTS[0]).raw
        for block in ("ablog__postcard", "ablog__recentposts", "ablog__tagcloud", "ablog__categories", "ablog__archives"):
            with self.subTest(block=block):
                self.assertIn(f"ablog-sidebar-item {block}", raw)
        self.assertIn('<li class="ablog-post">', page("blog/index.html").raw)


class SitemapTest(unittest.TestCase):
    def test_locs_are_exactly_root_blog_and_posts(self):
        self.assertEqual(ALLOWED_LOCS, set(sitemap_locs("serial")))
        self.assertEqual(len(ALLOWED_LOCS), len(sitemap_locs("serial")))

    def test_parallel_build_writes_the_same_sitemap(self):
        serial = (BUILDS["serial"] / SITEMAP).read_bytes()
        self.assertEqual(serial, (BUILDS["parallel"] / SITEMAP).read_bytes())

    def test_an_incremental_rebuild_keeps_the_exact_sitemap(self):
        for name in ("incremental-first", "incremental"):
            with self.subTest(build=name):
                result = RESULTS[name]
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertNotIn("WARNING", result.stdout + result.stderr)
        self.assertIn("kinetis: pruned 13 noindex page(s)", RESULTS["incremental"].stdout)
        self.assertEqual(ALLOWED_LOCS, set(sitemap_locs("incremental")))
        self.assertEqual((BUILDS["serial"] / SITEMAP).read_bytes(), (BUILDS["incremental"] / SITEMAP).read_bytes())

    def test_a_previous_builds_sitemap_is_not_pruned_again(self):
        self.assertEqual(0, RESULTS["stale-first"].returncode, RESULTS["stale-first"].stdout)
        result = RESULTS["stale"]
        output = result.stdout + result.stderr
        self.assertNotEqual(0, result.returncode, output)
        self.assertIn("does not exist: sphinx-sitemap wrote none in this build", output)
        self.assertNotIn("cannot map sitemap loc", output)
        self.assertFalse((BUILDS["stale"] / SITEMAP).exists())

    def test_the_loc_assertion_fails_without_the_pruner(self):
        locs = set(sitemap_locs("unpruned"))
        self.assertNotEqual(ALLOWED_LOCS, locs)
        self.assertIn(f"{SITE}blog/tag/php.html", locs)
        self.assertIn(f"{SITE}index.html", locs)

    def test_declaration_and_namespace_are_kept(self):
        raw = (BUILDS["serial"] / SITEMAP).read_text(encoding="utf-8")
        self.assertTrue(raw.startswith(
            "<?xml version='1.0' encoding='utf-8'?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\"><url>"
        ), raw[:200])
        self.assertNotIn("ns0:", raw)
        self.assertFalse((BUILDS["serial"] / "sitemap.xml").exists())

    def test_noindex_and_sitemap_agree_on_every_page(self):
        # One definition of noindex: a page carries the meta exactly when the
        # pruner leaves it out (404.html is also in sitemap_excludes).
        locs = set(sitemap_locs("serial"))
        for name in html_pages():
            with self.subTest(page=name):
                url = SITE + (name[: -len("index.html")] if name.endswith("index.html") else name)
                self.assertEqual(page(name).robots == ["noindex"], url not in locs)


if __name__ == "__main__":
    unittest.main()
