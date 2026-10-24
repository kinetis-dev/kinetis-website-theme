/* One primary-sidebar scroll memory per docs set.
 *
 * pydata-sphinx-theme 0.23.0 (scripts/pydata-sphinx-theme.js, deferred)
 * restores div.bd-sidebar's scrollTop from sessionStorage key
 * "sidebar-scroll-top" on pages with .bd-docs-nav, and writes it back on
 * beforeunload. sessionStorage is per origin, so /docs/ and /vector/docs/ on
 * kinetis.dev share that one value. This script, loaded in the head without
 * defer, runs before pydata reads the key: it copies the value saved for this
 * docs set's root path into "sidebar-scroll-top", or removes that key so
 * pydata scrolls the active link into view, and saves this set's own value.
 */
(function () {
  "use strict";

  var PYDATA_KEY = "sidebar-scroll-top";

  function docsRoot() {
    var root = document.documentElement.dataset.content_root;
    if (root === undefined && typeof DOCUMENTATION_OPTIONS !== "undefined") {
      root = DOCUMENTATION_OPTIONS.URL_ROOT;
    }
    if (root === undefined || root === null) {
      return null;
    }
    return new URL(root, location.href).pathname;
  }

  var root;
  try {
    root = docsRoot();
  } catch (e) {
    return;
  }
  if (root === null) {
    return;
  }
  var key = "kinetis-sidebar-scroll-top:" + root;

  try {
    var saved = sessionStorage.getItem(key);
    if (saved === null) {
      sessionStorage.removeItem(PYDATA_KEY);
    } else {
      sessionStorage.setItem(PYDATA_KEY, saved);
    }
  } catch (e) {
    // Storage unavailable: pydata behaves as it does without this script.
  }

  window.addEventListener("beforeunload", function () {
    if (!document.querySelector(".bd-docs-nav")) {
      return;
    }
    var sidebar = document.querySelector("div.bd-sidebar");
    if (!sidebar) {
      return;
    }
    try {
      sessionStorage.setItem(key, String(sidebar.scrollTop));
    } catch (e) {
      // As above.
    }
  });
})();
