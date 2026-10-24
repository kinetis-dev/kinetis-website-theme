"""Unit tests for the URL-baseline guard's main-landmark anchor rule."""

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_guard():
    spec = importlib.util.spec_from_file_location("check_url_baseline", REPO / "tools" / "check_url_baseline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse(html):
    parser = load_guard().PageParser()
    parser.feed(html)
    parser.close()
    return parser


# pydata 0.23.0's shape, as the theme renders it.
PYDATA_PAGE = """<!DOCTYPE html>
<html><head><title>Guide - Kinetis</title></head>
<body>
<header id="pst-header" data-pagefind-ignore><nav id="site-nav"></nav></header>
<div class="bd-container">
  <div id="pst-primary-sidebar" class="bd-sidebar-primary" data-pagefind-ignore></div>
  <main id="main-content" class="bd-main" role="main">
    <div class="bd-content">
      <div class="bd-article-container">
        <article class="bd-article" data-pagefind-body>
          <section id="configuration-guide"><h1>Guide</h1>
            <section id="environment-variables"><h2>Env</h2>
              <div class="sd-tab-set"><input id="sd-tab-item-0" type="radio"></div>
            </section>
          </section>
        </article>
      </div>
      <div id="pst-secondary-sidebar" class="bd-sidebar-secondary" data-pagefind-ignore>
        <nav id="pst-page-navigation-heading-2"><ul><li id="toc-entry"></li></ul></nav>
      </div>
    </div>
    <footer id="bd-footer-content"></footer>
  </main>
</div>
<footer id="site-footer"></footer>
</body></html>
"""

# pydata's search.html replaces docs_body, so <main> holds no article.
SEARCH_PAGE = """<!DOCTYPE html>
<html><head><title>Search - Kinetis</title></head>
<body>
<main id="main-content" class="bd-main" role="main">
  <div class="bd-content"><h1>Search</h1><div id="search-results"></div></div>
</main>
</body></html>
"""

# Furo's shape: no <main> tag; the landmark is the article.
FURO_PAGE = """<!DOCTYPE html>
<html><head><title>Guide - Kinetis</title></head>
<body>
<div class="page">
  <aside id="sidebar" class="sidebar-drawer"><div id="sidebar-tree"></div></aside>
  <div class="main">
    <div class="content">
      <article role="main" id="furo-main-content">
        <section id="configuration-guide"><h1>Guide</h1>
          <section id="environment-variables"><h2>Env</h2>
            <article id="nested-article"><p id="in-nested">x</p></article>
            <p id="after-nested">y</p>
            <div id="sd-tab-set-0"></div>
          </section>
        </section>
      </article>
      <footer id="furo-footer"></footer>
    </div>
    <aside class="toc-drawer"><div id="toc-tree"></div></aside>
  </div>
</div>
</body></html>
"""

# What the v0.1.0 parser (<article role="main"> only) collects from FURO_PAGE.
FURO_V010_IDS = {"configuration-guide", "environment-variables", "nested-article", "in-nested", "after-nested"}


class MainLandmarkTest(unittest.TestCase):
    def test_pydata_page_collects_the_article_and_skips_pagefind_ignore(self):
        parser = parse(PYDATA_PAGE)
        self.assertEqual({"configuration-guide", "environment-variables", "bd-footer-content"}, parser.main_ids)
        # Every id still counts for external anchors.
        for anchor in ("main-content", "pst-secondary-sidebar", "toc-entry", "site-footer", "sd-tab-item-0"):
            self.assertIn(anchor, parser.ids)

    def test_search_page_collects_ids_in_main_without_an_article(self):
        self.assertEqual({"search-results"}, parse(SEARCH_PAGE).main_ids)

    def test_furo_page_collects_what_v010_did(self):
        parser = parse(FURO_PAGE)
        self.assertEqual(FURO_V010_IDS, parser.main_ids)
        self.assertNotIn("furo-main-content", parser.main_ids)
        self.assertIn("furo-main-content", parser.ids)

    def test_nested_main_and_article_do_not_end_the_landmark_early(self):
        html = """<body><main role="main" id="main-content">
          <main id="inner-main"><article id="inner-article" role="main"><p id="deep"></p></article>
            <p id="after-article"></p></main>
          <p id="after-inner-main"></p>
          <div data-pagefind-ignore><div><div id="ignored"></div></div><p id="still-ignored"></p></div>
          <p id="after-ignore"></p>
        </main><p id="outside"></p>
        <article role="main"><p id="second-landmark"></p></article></body>"""
        self.assertEqual(
            {"inner-main", "inner-article", "deep", "after-article", "after-inner-main", "after-ignore", "second-landmark"},
            parse(html).main_ids,
        )

    def test_void_pagefind_ignore_element_does_not_open_a_subtree(self):
        html = '<main><input id="query" data-pagefind-ignore><p id="kept"></p></main>'
        self.assertEqual({"kept"}, parse(html).main_ids)

    def test_page_without_a_landmark_collects_nothing(self):
        self.assertEqual(set(), parse('<body><div id="a"></div></body>').main_ids)


if __name__ == "__main__":
    unittest.main()
