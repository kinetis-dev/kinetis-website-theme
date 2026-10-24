"""Run the theme's kinetis-sidebar-scroll.js in node and assert on its behaviour.

Each scenario is a short sequence of page loads sharing one fake
sessionStorage, as one browser tab does across kinetis.dev. A page load runs
the script in a fresh node:vm context with a minimal document, location and
window, then pydata-sphinx-theme 0.23.0's own use of the key (read on load,
written on beforeunload, only with .bd-docs-nav), so the assertions see what
pydata would read. Skipped when node is not on PATH.
"""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "kinetis_website_theme" / "theme" / "kinetis_website_theme" / "static" / "kinetis-sidebar-scroll.js"
NODE = shutil.which("node")

# argv: the script path and a JSON list of page loads. Prints one JSON result
# per load: what pydata read, the storage after the script ran, the storage
# after beforeunload, and any error that escaped.
HARNESS = r"""
const fs = require("fs");
const vm = require("vm");
const [scriptPath, loadsJson] = process.argv.slice(1);
const code = fs.readFileSync(scriptPath, "utf8");
const store = new Map();
const storage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => { store.set(k, String(v)); },
  removeItem: (k) => { store.delete(k); },
};
const throwing = () => { throw new Error("SecurityError: storage disabled"); };
const throwingStorage = { getItem: throwing, setItem: throwing, removeItem: throwing };
const snapshot = () => Object.fromEntries([...store.entries()].sort());

const results = [];
for (const load of JSON.parse(loadsJson)) {
  const listeners = [];
  const sidebar = { scrollTop: 0 };
  const dataset = {};
  if (load.contentRoot != null) dataset.content_root = load.contentRoot;
  const context = {
    URL,
    location: { href: load.href },
    document: {
      documentElement: { dataset },
      querySelector: (sel) => {
        if (sel === ".bd-docs-nav") return load.docsNav ? {} : null;
        if (sel === "div.bd-sidebar") return sidebar;
        throw new Error("unexpected selector " + sel);
      },
    },
  };
  if (load.urlRoot != null) context.DOCUMENTATION_OPTIONS = { URL_ROOT: load.urlRoot };
  if (load.storage === "throwing-getter") {
    Object.defineProperty(context, "sessionStorage", { get: throwing });
  } else {
    context.sessionStorage = load.storage === "throwing" ? throwingStorage : storage;
  }
  context.window = context;
  context.addEventListener = (type, fn) => { listeners.push([type, fn]); };
  vm.createContext(context);
  const result = { error: null, pydataRead: null };
  try {
    vm.runInContext(code, context, { filename: scriptPath });
    result.afterLoad = snapshot();
    // pydata 0.23.0, deferred, after the head scripts.
    if (load.docsNav && !load.storage) {
      const t = parseInt(storage.getItem("sidebar-scroll-top"), 10);
      result.pydataRead = isNaN(t) ? null : t;
      if (!isNaN(t)) sidebar.scrollTop = t;
      listeners.push(["beforeunload", () => { storage.setItem("sidebar-scroll-top", sidebar.scrollTop); }]);
    }
    if (load.scrollTo != null) sidebar.scrollTop = load.scrollTo;
    for (const [type, fn] of listeners) if (type === "beforeunload") fn();
    result.afterUnload = snapshot();
  } catch (e) {
    result.error = String(e);
  }
  results.push(result);
}
console.log(JSON.stringify(results));
"""


def docs_page(root, page="guide.html", content_root="./", **load):
    return dict(href=f"https://kinetis.dev{root}{page}", contentRoot=content_root, docsNav=True, **load)


def run(*loads):
    result = subprocess.run(
        [NODE, "-e", HARNESS, str(SCRIPT), json.dumps(loads)], capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return json.loads(result.stdout)


@unittest.skipIf(NODE is None, "node is not on PATH: kinetis-sidebar-scroll.js behaviour not tested")
class SidebarScrollTest(unittest.TestCase):
    def assertNoErrors(self, results):
        self.assertEqual([None] * len(results), [r["error"] for r in results])

    def test_docs_and_vector_docs_keep_separate_values(self):
        results = run(
            docs_page("/docs/", scrollTo=120),
            docs_page("/vector/docs/", scrollTo=40),
            docs_page("/docs/", "sub/page.html", content_root="../"),
            docs_page("/vector/docs/", "index.html"),
        )
        self.assertNoErrors(results)
        self.assertEqual([None, None, 120, 40], [r["pydataRead"] for r in results])
        self.assertEqual("120", results[1]["afterUnload"]["kinetis-sidebar-scroll-top:/docs/"])
        self.assertEqual("40", results[1]["afterUnload"]["kinetis-sidebar-scroll-top:/vector/docs/"])

    def test_no_scoped_value_removes_the_pydata_key_before_pydata_reads_it(self):
        results = run(docs_page("/docs/", scrollTo=300), docs_page("/vector/docs/"))
        self.assertNoErrors(results)
        self.assertEqual("300", results[0]["afterUnload"]["sidebar-scroll-top"])
        self.assertNotIn("sidebar-scroll-top", results[1]["afterLoad"])
        self.assertIsNone(results[1]["pydataRead"])

    def test_a_page_without_docs_nav_saves_nothing(self):
        # A landing page: it has div.bd-sidebar (navbar items on narrow
        # screens) but no .bd-docs-nav.
        results = run(dict(href="https://kinetis.dev/", contentRoot="./", docsNav=False, scrollTo=75))
        self.assertNoErrors(results)
        self.assertEqual({}, results[0]["afterUnload"])

    def test_a_throwing_session_storage_does_not_escape(self):
        for storage in ("throwing", "throwing-getter"):
            with self.subTest(storage=storage):
                results = run(docs_page("/docs/", storage=storage, scrollTo=10))
                self.assertNoErrors(results)

    def test_documentation_options_url_root_is_the_fallback_scope(self):
        results = run(
            docs_page("/docs/", content_root=None, urlRoot="./", scrollTo=60),
            docs_page("/vector/docs/", content_root=None, urlRoot="./"),
        )
        self.assertNoErrors(results)
        self.assertEqual("60", results[0]["afterUnload"]["kinetis-sidebar-scroll-top:/docs/"])
        self.assertIsNone(results[1]["pydataRead"])

    def test_without_a_root_it_does_nothing(self):
        results = run(
            docs_page("/docs/", scrollTo=90),
            docs_page("/vector/docs/", content_root=None, scrollTo=20),
        )
        self.assertNoErrors(results)
        # pydata's own behaviour: the shared key carries over, and only pydata wrote.
        self.assertEqual(90, results[1]["pydataRead"])
        self.assertEqual(
            {"kinetis-sidebar-scroll-top:/docs/": "90", "sidebar-scroll-top": "20"}, results[1]["afterUnload"]
        )


if __name__ == "__main__":
    unittest.main()
