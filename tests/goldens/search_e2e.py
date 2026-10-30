#!/usr/bin/env python3
"""End-to-end checks of the site-wide Pagefind search (docs/SEARCH.md).

  search_e2e.py <website-build> <docs-build> <vector-build>

The three builds are tests/sample-website, tests/sample-site and
tests/sample-site again with html_baseurl https://kinetis.dev/vector/docs/,
each already indexed with `python -m pagefind --site <build>`. They are
assembled into a mock kinetis.dev, the website at /, the docs at /docs/ and
/vector/docs/, and served as goldens.py serves a build: a missing file gets
the root 404.html with status 404, as the website's bucket does. Then, in
Chromium:

- a search from every block returns results from all four, with the right
  URLs and section labels;
- without the Vector bundle, the rest still searches;
- a Vector bundle of another Pagefind version is left out, with one warning;
- with no bundle at all there is no search UI and no console error;
- without the component stylesheet the UI still comes up, its 404 is
  reported and the script warns;
- Ctrl+K opens the modal exactly once despite pydata's own listener, and
  Escape closes it and returns focus to the trigger, at 1280px and 375px,
  where exactly one of pydata's two trigger copies is visible;
- the modal follows pydata's mode, not the OS scheme: light and dark pages,
  each with the OS scheme the same and the opposite, give the mode's
  background, and focus is rgb(220, 38, 38) in every case;
- search.html?q= runs the query on the full-page search;
- no ordinary page requests searchindex.js or Sphinx's search scripts;
- on a narrow screen the compact trigger fits pydata's header.

The only console error excused is Chromium's "Failed to load resource" for
a probed pagefind-entry.json, the expected 404 of an absent bundle; any
other failed resource fails the run.

Runs in CI's goldens job, on mcr.microsoft.com/playwright/python. Exits
non-zero on any failure.
"""

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from goldens import serve

RED = "rgb(220, 38, 38)"
VIEWPORT = {"width": 1280, "height": 900}
NARROW = {"width": 375, "height": 800}
# Pages of each block, as deployed.
BLOCK_PAGES = {
    "Main": "",
    "Blog": "blog/posts/hello-kinetis.html",
    "Docs": "docs/guide.html",
    "Vector": "vector/docs/guide.html",
}
# One page of each section a "kinetis" search must find, by URL.
EXPECTED = {"/": "Main", "/blog/": "Blog", "/docs/": "Docs", "/vector/docs/": "Vector"}
SPHINX_SEARCH = ("searchindex.js", "searchtools.js", "language_data.js")
# Chromium logs every 4xx response as a console error. The probe of an
# absent bundle's entry file is expected to 404; nothing else is.
RESOURCE_ERROR = "Failed to load resource"
PROBE = "pagefind-entry.json"
# pydata's page background in each mode (kinetis.css), which the modal's
# must match whatever the OS scheme is.
BACKGROUNDS = {"light": "rgb(255, 255, 255)", "dark": "rgb(19, 20, 22)"}
# Pagefind's own backdrop per mode, which kinetis.css sets for both.
BACKDROPS = {"light": "rgba(0, 0, 0, 0.5)", "dark": "rgba(0, 0, 0, 0.7)"}
# (pydata mode, OS colour scheme): the same, and the opposite.
SCHEMES = (("light", "light"), ("dark", "dark"), ("light", "dark"), ("dark", "light"))
TRIGGERS_SHOWN = "[...document.querySelectorAll('pagefind-modal-trigger button')].filter(b => b.checkVisibility()).length"
TRIGGERS_ALL = "document.querySelectorAll('pagefind-modal-trigger button').length"

# Counts the modal openings: every Pagefind modal opens through showModal.
COUNT_OPENINGS = """
window.__kinetisOpenings = 0;
const showModal = HTMLDialogElement.prototype.showModal;
HTMLDialogElement.prototype.showModal = function () {
  window.__kinetisOpenings += 1;
  return showModal.apply(this, arguments);
};
"""

# Every result of a query on the default instance as {url, section}, loaded
# through Pagefind's own merged search.
SEARCH_ALL = """
async (term) => {
  const instance = window.PagefindComponents.getInstanceManager().getInstance("default");
  await instance.triggerLoad();
  const search = await instance.__pagefind__.search(term);
  const data = await Promise.all(search.results.map((result) => result.data()));
  return data.map((page) => ({url: page.url, section: page.meta.section || null}));
}
"""


def section_of(url):
    """The section a result URL belongs to: its longest prefix in EXPECTED."""
    return EXPECTED[max((prefix for prefix in EXPECTED if url.startswith(prefix)), key=len)]


def assemble(root, website, docs, vector, bundles=("website", "docs", "vector")):
    """A mock kinetis.dev under root, keeping only the named bundles."""
    for name, build, prefix in (("website", website, root), ("docs", docs, root / "docs"),
                                ("vector", vector, root / "vector" / "docs")):
        shutil.copytree(build, prefix, dirs_exist_ok=True)
        if name not in bundles:
            shutil.rmtree(prefix / "pagefind")
    return root


class Run:
    def __init__(self, browser, base):
        self.browser = browser
        self.base = base
        self.failures = []

    def check(self, condition, message):
        print(("ok    " if condition else "FAIL  ") + message)
        if not condition:
            self.failures.append(message)

    def page(self, mode="light", viewport=VIEWPORT, os_scheme=None):
        """A page in pydata mode ``mode``; the OS scheme is ``os_scheme``, else the same."""
        context = self.browser.new_context(viewport=viewport, color_scheme=os_scheme or mode, reduced_motion="reduce")
        context.add_init_script(f"localStorage.setItem('mode', '{mode}'); localStorage.setItem('theme', '{mode}');")
        context.add_init_script(COUNT_OPENINGS)
        page = context.new_page()
        page.kinetis_console = []
        page.kinetis_errors = []
        page.kinetis_requests = []
        page.on("console", lambda message: page.kinetis_console.append(
            (message.type, message.text, (message.location or {}).get("url", ""))))
        page.on("pageerror", lambda error: page.kinetis_errors.append(str(error)))
        page.on("request", lambda request: page.kinetis_requests.append(request.url))
        return page

    def eventually(self, page, expression, message, arg=None):
        """Check that a JS expression becomes truthy within a second.

        For state that settles after an event: Pagefind's 0.15s border
        transitions, and focus returning on the dialog's queued close event.
        """
        try:
            page.wait_for_function(expression, arg=arg, timeout=1000)
            self.check(True, message)
        except Exception:
            self.check(False, f"{message} (now {page.evaluate(expression, arg)!r})")

    def open(self, page, path):
        page.goto(self.base + path, wait_until="networkidle")

    def wait_for_trigger(self, page):
        page.wait_for_selector(".navbar-persistent--container pagefind-modal-trigger button", state="visible",
                               timeout=10000)

    def console_errors(self, page):
        return [f"{text} ({url})" for kind, text, url in page.kinetis_console
                if kind == "error" and not (text.startswith(RESOURCE_ERROR) and url.split("?")[0].endswith(PROBE))
                ] + page.kinetis_errors

    def warnings(self, page):
        return [text for kind, text, _ in page.kinetis_console if kind == "warning"]

    def check_triggers(self, page, label):
        shown, total = page.evaluate(TRIGGERS_SHOWN), page.evaluate(TRIGGERS_ALL)
        self.check((shown, total) == (1, 2), f"{label}: one of the two triggers is visible ({shown} of {total})")


def search_every_block(run):
    for block, path in BLOCK_PAGES.items():
        page = run.page()
        run.open(page, path)
        run.wait_for_trigger(page)
        found = page.evaluate(SEARCH_ALL, "kinetis")
        sections = {item["url"]: item["section"] for item in found}
        for url, section in EXPECTED.items():
            run.check(sections.get(url) == section,
                      f"from {block} (/{path}): 'kinetis' finds {url} as {section}, got {sections.get(url)!r}")
        wrong = [item for item in found if item["section"] != section_of(item["url"])]
        run.check(not wrong, f"from {block}: every result's section matches its URL ({wrong})")
        run.check(not run.console_errors(page), f"from {block}: no console errors ({run.console_errors(page)})")
        page.context.close()


def results_in_the_modal(run):
    page = run.page()
    run.open(page, "docs/guide.html")
    run.wait_for_trigger(page)
    page.click(".navbar-persistent--container pagefind-modal-trigger button")
    page.wait_for_selector("pagefind-modal dialog[open] pagefind-input input")
    page.fill("pagefind-modal pagefind-input input", "Configuration guide")
    page.wait_for_function(
        "document.querySelectorAll('pagefind-modal .pf-result-link[href=\"/vector/docs/guide.html\"]').length"
        " && document.querySelectorAll('pagefind-modal .pf-result-link[href=\"/docs/guide.html\"]').length",
        timeout=10000)
    rows = page.eval_on_selector_all(
        "pagefind-modal .pf-result",
        "rows => rows.map(r => [r.querySelector('.pf-result-link')?.getAttribute('href'),"
        " r.querySelector('.kinetis-search-section')?.textContent])")
    labels = dict(row for row in rows if row[0])
    run.check(labels.get("/docs/guide.html") == "Docs", f"modal: /docs/guide.html is labelled Docs ({labels})")
    run.check(labels.get("/vector/docs/guide.html") == "Vector",
              f"modal: /vector/docs/guide.html is labelled Vector ({labels})")
    options = page.eval_on_selector("pagefind-modal pagefind-filter-dropdown", "d => d.textContent")
    run.check("Section" in options, f"modal: the Section filter is shown ({options!r})")
    run.check(page.locator("pagefind-modal .pf-heading-chips").count() == 0, "modal: no sub-results")
    page.context.close()


def missing_bundle(run):
    page = run.page()
    run.open(page, "docs/guide.html")
    run.wait_for_trigger(page)
    found = {item["url"] for item in page.evaluate(SEARCH_ALL, "kinetis")}
    run.check({"/", "/blog/", "/docs/"} <= found, f"without the Vector bundle: Main, Blog and Docs are found ({found})")
    run.check(not any(url.startswith("/vector/") for url in found), "without the Vector bundle: no Vector result")
    run.check(not run.console_errors(page), f"without the Vector bundle: no console errors ({run.console_errors(page)})")
    page.context.close()


def skewed_bundle(run):
    page = run.page()
    run.open(page, "docs/guide.html")
    run.wait_for_trigger(page)
    found = {item["url"] for item in page.evaluate(SEARCH_ALL, "kinetis")}
    run.check({"/", "/blog/", "/docs/"} <= found, f"skewed Vector bundle: Main, Blog and Docs are found ({found})")
    run.check(not any(url.startswith("/vector/") for url in found), "skewed Vector bundle: not merged")
    warnings = run.warnings(page)
    run.check(len(warnings) == 1 and "/vector/docs/pagefind/" in warnings[0],
              f"skewed Vector bundle: one warning names it ({warnings})")
    run.check(not run.console_errors(page), f"skewed Vector bundle: no console errors ({run.console_errors(page)})")
    page.context.close()


def no_bundle(run):
    for path in ("", "docs/guide.html", "docs/search.html?q=kinetis"):
        page = run.page()
        run.open(page, path)
        page.wait_for_timeout(500)
        elements = page.evaluate("document.querySelectorAll('pagefind-modal-trigger, pagefind-modal, pagefind-input').length")
        filled = page.evaluate("[...document.querySelectorAll('.kinetis-search, #kinetis-search-page')]"
                               ".filter(e => e.childNodes.length).length")
        run.check(elements == 0 and filled == 0, f"no bundle, /{path}: no search UI ({elements} elements)")
        run.check(page.evaluate("typeof window.PagefindComponents") == "undefined",
                  f"no bundle, /{path}: no Pagefind script loaded")
        run.check(not run.console_errors(page), f"no bundle, /{path}: no console errors ({run.console_errors(page)})")
        run.check(not run.warnings(page), f"no bundle, /{path}: nothing logged ({run.warnings(page)})")
        page.context.close()


def unstyled(run):
    page = run.page()
    run.open(page, "docs/guide.html")
    run.wait_for_trigger(page)
    errors = run.console_errors(page)
    run.check(len(errors) == 1 and "pagefind-component-ui.css" in errors[0],
              f"no component stylesheet: its failed load is reported ({errors})")
    warnings = run.warnings(page)
    run.check(len(warnings) == 1 and "unstyled" in warnings[0], f"no component stylesheet: one warning ({warnings})")
    page.context.close()


def shortcut_and_focus(run):
    for mode, os_scheme in SCHEMES:
        label = f"{mode} page, {os_scheme} OS"
        page = run.page(mode, os_scheme=os_scheme)
        run.open(page, "docs/guide.html")
        run.wait_for_trigger(page)
        run.check(page.evaluate("document.documentElement.dataset.theme") == mode, f"{label}: page is in {mode} mode")
        run.check(page.evaluate(f"matchMedia('(prefers-color-scheme: {os_scheme})').matches"),
                  f"{label}: the OS scheme is {os_scheme}")
        run.check(page.locator("#pst-search-dialog").count() == 0, f"{label}: pydata's search dialog is gone")
        run.check_triggers(page, f"{label}, 1280px")
        page.locator("body").click(position={"x": 5, "y": 300})
        page.keyboard.press("Control+k")
        page.wait_for_selector("pagefind-modal dialog[open]")
        page.wait_for_timeout(300)
        run.check(page.evaluate("window.__kinetisOpenings") == 1,
                  f"{label}: Ctrl+K opened the modal once ({page.evaluate('window.__kinetisOpenings')})")
        run.check(page.locator("dialog[open]").count() == 1, f"{label}: one dialog is open")
        focused = page.evaluate("document.activeElement && document.activeElement.classList.contains('pf-input')")
        run.check(focused, f"{label}: the search input has focus")
        background = page.evaluate("getComputedStyle(document.querySelector('pagefind-modal dialog')).backgroundColor")
        run.check(background == BACKGROUNDS[mode], f"{label}: modal background is the {mode} page's ({background})")
        page_background = page.evaluate("getComputedStyle(document.body).backgroundColor")
        run.check(page_background == BACKGROUNDS[mode], f"{label}: page background is {mode} ({page_background})")
        backdrop = page.evaluate(
            "getComputedStyle(document.querySelector('pagefind-modal')).getPropertyValue('--pf-modal-backdrop').trim()")
        run.check(backdrop == BACKDROPS[mode], f"{label}: modal backdrop is the {mode} one ({backdrop})")
        for variable in ("--pf-outline-focus", "--pf-border-focus"):
            value = page.evaluate(
                f"getComputedStyle(document.querySelector('pagefind-modal')).getPropertyValue('{variable}').trim()")
            run.check(value.lower() == "#dc2626", f"{label}: {variable} is #DC2626 ({value})")
        # The modal's own input is borderless; its focus shows on the results.
        page.keyboard.type("Configuration guide")
        page.wait_for_selector("pagefind-modal .pf-result-link", timeout=10000)
        page.keyboard.press("ArrowDown")
        page.wait_for_function("document.activeElement.classList.contains('pf-result-link')")
        run.eventually(page, "red => getComputedStyle(document.activeElement.closest('.pf-result-card')).borderTopColor"
                             " === red", f"{label}: the focused result's border is {RED}", RED)
        page.keyboard.press("Escape")
        page.wait_for_selector("pagefind-modal dialog[open]", state="detached")
        run.eventually(page, "!!document.activeElement.closest('.navbar-persistent--container pagefind-modal-trigger')",
                       f"{label}: Escape closed the modal and focus is back on the trigger")
        page.keyboard.press("Tab")
        page.keyboard.press("Shift+Tab")
        run.eventually(page, "red => getComputedStyle(document.activeElement).outlineColor === red",
                       f"{label}: the trigger's focus ring is {RED}", RED)
        page.keyboard.press("Control+k")
        page.wait_for_selector("pagefind-modal dialog[open]")
        run.check(page.evaluate("window.__kinetisOpenings") == 2, f"{label}: Ctrl+K opens it again, once")
        run.check(not run.console_errors(page), f"{label}: no console errors ({run.console_errors(page)})")
        # The full-page search's input has a border, red on focus.
        run.open(page, "docs/search.html")
        page.wait_for_selector("#kinetis-search-page pagefind-input input")
        page.focus("#kinetis-search-page pagefind-input input")
        run.eventually(page, "red => getComputedStyle(document.activeElement).borderTopColor === red",
                       f"{label}: the focused search.html input border is {RED}", RED)
        run.check(not run.console_errors(page), f"{label}, search.html: no console errors ({run.console_errors(page)})")
        page.context.close()


def search_page(run):
    page = run.page()
    run.open(page, "docs/search.html?q=Configuration%20guide")
    page.wait_for_selector("#search-results #kinetis-search-page .pf-result-link", timeout=10000)
    hrefs = page.eval_on_selector_all("#search-results .pf-result-link", "links => links.map(a => a.getAttribute('href'))")
    run.check("/docs/guide.html" in hrefs and "/vector/docs/guide.html" in hrefs,
              f"search.html?q=: results from both docs sets ({hrefs})")
    value = page.eval_on_selector("#kinetis-search-page pagefind-input input", "i => i.value")
    run.check(value == "Configuration guide", f"search.html?q=: the input holds the query ({value!r})")
    run.check(page.locator("main #search-results").count() == 1, "search.html: #search-results is inside <main>")
    run.check(page.title() == "Search - Kinetis", f"search.html: title ({page.title()!r})")
    run.check(page.locator("pagefind-modal").count() == 1, "search.html: the modal is there too")
    run.check(not run.console_errors(page), f"search.html: no console errors ({run.console_errors(page)})")
    page.context.close()


def no_sphinx_search_assets(run):
    for path in ("", "blog/posts/hello-kinetis.html", "docs/guide.html", "vector/docs/", "docs/search.html"):
        page = run.page()
        run.open(page, path)
        loaded = [url for url in page.kinetis_requests if url.split("?")[0].endswith(SPHINX_SEARCH)]
        run.check(not loaded, f"/{path}: no Sphinx search asset requested ({loaded})")
        page.context.close()


def narrow_header(run, bare_base):
    heights = {}
    for name, base in (("indexed", run.base), ("bare", bare_base)):
        page = run.page(viewport=NARROW)
        page.goto(base + "docs/guide.html", wait_until="networkidle")
        if name == "indexed":
            page.wait_for_selector(".navbar-persistent--mobile pagefind-modal-trigger button", state="visible")
            run.check_triggers(page, "narrow, 375px")
            page.locator("main").click(position={"x": 5, "y": 5})
            page.keyboard.press("Control+k")
            page.wait_for_selector("pagefind-modal dialog[open]")
            page.wait_for_timeout(300)
            run.check(page.evaluate("window.__kinetisOpenings") == 1,
                      f"narrow: Ctrl+K opened the modal once ({page.evaluate('window.__kinetisOpenings')})")
            page.keyboard.press("Escape")
            page.wait_for_selector("pagefind-modal dialog[open]", state="detached")
            run.check(page.locator("dialog[open]").count() == 0, "narrow: Escape closed the modal")
            run.eventually(page, "!!document.activeElement.closest('.navbar-persistent--mobile pagefind-modal-trigger')",
                           "narrow: after Ctrl+K and Escape, focus is on the visible trigger")
            box = page.locator(".navbar-persistent--mobile pagefind-modal-trigger button").bounding_box()
            text = page.locator(".navbar-persistent--mobile .pf-trigger-text").count()
            run.check(text == 0, "narrow: the trigger is compact (icon only)")
            run.check(box["x"] + box["width"] <= NARROW["width"], f"narrow: the trigger is on screen ({box})")
            page.click(".navbar-persistent--mobile pagefind-modal-trigger button")
            page.wait_for_selector("pagefind-modal dialog[open]")
            run.check(page.locator("pagefind-modal dialog").is_visible(), "narrow: the modal shows")
            page.keyboard.press("Escape")
            run.eventually(page, "!!document.activeElement.closest('.navbar-persistent--mobile pagefind-modal-trigger')",
                           "narrow: focus returns to the visible trigger")
            run.check(not run.console_errors(page), f"narrow: no console errors ({run.console_errors(page)})")
        heights[name] = page.evaluate("document.querySelector('#pst-header').getBoundingClientRect().height")
        page.context.close()
    run.check(heights["indexed"] == heights["bare"],
              f"narrow: the header keeps its height with the trigger ({heights})")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("website_build", type=Path)
    parser.add_argument("docs_build", type=Path)
    parser.add_argument("vector_build", type=Path)
    parser.add_argument("--channel", help="browser channel, e.g. chrome, for a local run")
    args = parser.parse_args(argv)
    builds = (args.website_build, args.docs_build, args.vector_build)
    for build in builds:
        if not (build / "pagefind" / "pagefind-entry.json").is_file():
            parser.error(f"{build} is not an indexed build: run python -m pagefind --site {build}")

    scratch = Path(tempfile.mkdtemp(prefix="kinetis-search-e2e-"))
    try:
        full = assemble(scratch / "full", *builds)
        partial = assemble(scratch / "partial", *builds, bundles=("website", "docs"))
        bare = assemble(scratch / "bare", *builds, bundles=())
        skewed = assemble(scratch / "skewed", *builds)
        entry = skewed / "vector" / "docs" / "pagefind" / "pagefind-entry.json"
        entry.write_text(json.dumps(dict(json.loads(entry.read_text(encoding="utf-8")), version="1.0.0")),
                         encoding="utf-8")
        bare_css = assemble(scratch / "unstyled", *builds)
        (bare_css / "docs" / "pagefind" / "pagefind-component-ui.css").unlink()
        roots = {"full": full, "partial": partial, "bare": bare, "skewed": skewed, "unstyled": bare_css}
        servers = {name: serve(root) for name, root in roots.items()}
        bases = {name: f"http://127.0.0.1:{server.server_address[1]}/" for name, server in servers.items()}
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel=args.channel)
                run = Run(browser, bases["full"])
                search_every_block(run)
                results_in_the_modal(run)
                shortcut_and_focus(run)
                search_page(run)
                no_sphinx_search_assets(run)
                narrow_header(run, bases["bare"])
                failures = run.failures
                run = Run(browser, bases["partial"])
                missing_bundle(run)
                failures += run.failures
                run = Run(browser, bases["skewed"])
                skewed_bundle(run)
                failures += run.failures
                run = Run(browser, bases["unstyled"])
                unstyled(run)
                failures += run.failures
                run = Run(browser, bases["bare"])
                no_bundle(run)
                failures += run.failures
                browser.close()
        finally:
            for server in servers.values():
                server.shutdown()
    finally:
        shutil.rmtree(scratch)
    print(f"search e2e: {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
