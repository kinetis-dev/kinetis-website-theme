/* Site-wide search: Pagefind's Component UI over every kinetis.dev bundle.
 *
 * docs/SEARCH.md §4 and §5 are the contract. The candidates are this page's
 * own bundle (pagefind/ under <html data-content_root>) and the theme's
 * SEARCH_BUNDLES, passed in this script's data-kinetis-bundles. Pagefind
 * 1.5.2 fails the whole instance when a merged bundle is missing, so each is
 * probed first; the first present one is the primary, whose Component UI is
 * loaded and configured with every other present bundle of the same version
 * as mergeIndex. Only then are the <pagefind-*> elements inserted:
 * configureInstance is ignored once a component of the instance connected.
 * With no bundle present nothing is inserted and nothing is logged.
 */
(function () {
  "use strict";

  var script = document.currentScript;
  var ENTRY = "pagefind-entry.json";
  var RESULT_TEMPLATE = [
    '<li class="pf-result">',
    '  <div class="pf-result-card">',
    '    <div class="pf-result-content">',
    '      <p class="pf-result-title">',
    '        <a class="pf-result-link" href="{{ meta.url | default(url) | safeUrl }}">{{ meta.title }}</a>',
    '        {{#if meta.section}}<span class="kinetis-search-section">{{ meta.section }}</span>{{/if}}',
    "      </p>",
    "      {{#if excerpt}}",
    '      <p class="pf-result-excerpt">{{+ excerpt +}}</p>',
    "      {{/if}}",
    "    </div>",
    "  </div>",
    "</li>",
  ].join("\n");

  function candidates() {
    var paths = [];
    var root = document.documentElement.dataset.content_root;
    if (root !== undefined) {
      paths.push(new URL("pagefind/", new URL(root, location.href)).pathname);
    }
    JSON.parse(script.dataset.kinetisBundles || "[]").forEach(function (bundle) {
      paths.push(new URL(bundle, location.href).pathname);
    });
    return paths.filter(function (path, i) {
      return paths.indexOf(path) === i;
    });
  }

  // {path, version} when the bundle's entry file is there, else null: a 404,
  // the website's HTML 404 page and a network error are all absent.
  function probe(path) {
    return fetch(path + ENTRY, { cache: "no-store" })
      .then(function (response) {
        return response.ok ? response.json() : null;
      })
      .then(function (entry) {
        var present =
          entry !== null &&
          typeof entry === "object" &&
          typeof entry.version === "string" &&
          entry.languages !== null &&
          typeof entry.languages === "object" &&
          !Array.isArray(entry.languages);
        return present ? { path: path, version: entry.version } : null;
      })
      .catch(function () {
        return null;
      });
  }

  function load(tag, attributes) {
    return new Promise(function (resolve, reject) {
      var node = document.createElement(tag);
      Object.keys(attributes).forEach(function (name) {
        node.setAttribute(name, attributes[name]);
      });
      node.onload = resolve;
      node.onerror = function () {
        reject(new Error("could not load " + (attributes.src || attributes.href)));
      };
      document.head.appendChild(node);
    });
  }

  function element(tag, attributes, children) {
    var node = document.createElement(tag);
    Object.keys(attributes || {}).forEach(function (name) {
      node.setAttribute(name, attributes[name]);
    });
    (children || []).forEach(function (child) {
      node.appendChild(child);
    });
    return node;
  }

  function results(attributes) {
    var template = element("script", { type: "text/pagefind-template" });
    template.textContent = RESULT_TEMPLATE;
    return element("pagefind-results", attributes, [template]);
  }

  function options(primary, merged) {
    return {
      bundlePath: primary.path,
      mergeIndex: merged.map(function (bundle) {
        return { bundlePath: bundle.path };
      }),
    };
  }

  // One trigger per placeholder (pydata renders navbar_persistent twice, the
  // narrow-screen copy compact) and one modal. The modal goes in <body>: a
  // <dialog> under the placeholder that is display:none would never show.
  function buildModal(placeholders) {
    var triggers = placeholders.map(function (placeholder) {
      var narrow = placeholder.closest(".navbar-persistent--mobile") !== null;
      var trigger = element("pagefind-modal-trigger", narrow ? { compact: "", "hide-shortcut": "" } : {});
      placeholder.appendChild(trigger);
      return trigger;
    });
    var modal = element("pagefind-modal", { class: "kinetis-search-modal" }, [
      element("pagefind-modal-header", {}, [element("pagefind-input")]),
      element("pagefind-modal-body", {}, [
        element("pagefind-filter-dropdown", { filter: "section", label: "Section" }),
        element("pagefind-summary"),
        results({ "hide-sub-results": "" }),
      ]),
      element("pagefind-modal-footer", {}, [element("pagefind-keyboard-hints")]),
    ]);
    document.body.appendChild(modal);
    // Pagefind returns focus to the first trigger, which is hidden on narrow
    // screens; move it to the one on screen. "close" does not bubble, so
    // this listens in the capture phase, which survives the modal's
    // re-rendering of its <dialog>.
    modal.addEventListener(
      "close",
      function () {
        var shown = triggers.filter(function (trigger) {
          return trigger.offsetParent !== null;
        })[0];
        var button = shown && shown.querySelector("button");
        if (button && document.activeElement !== button) {
          button.focus();
        }
      },
      true,
    );
  }

  function buildPage(container, components) {
    container.appendChild(element("pagefind-input", { instance: "page" }));
    container.appendChild(element("pagefind-filter-dropdown", { instance: "page", filter: "section", label: "Section" }));
    container.appendChild(element("pagefind-summary", { instance: "page" }));
    container.appendChild(results({ instance: "page", "hide-sub-results": "" }));
    var query = new URLSearchParams(location.search).get("q");
    if (query) {
      components.getInstanceManager().getInstance("page").triggerSearch(query);
    }
  }

  function start(primary, merged) {
    var placeholders = Array.prototype.slice.call(document.querySelectorAll(".kinetis-search"));
    var page = document.getElementById("kinetis-search-page");
    if (!placeholders.length && !page) {
      return;
    }
    // The stylesheet is cosmetic, so the UI still comes up without it, but
    // its loss is reported; the script is required.
    var css = load("link", { rel: "stylesheet", href: primary.path + "pagefind-component-ui.css" }).catch(function (error) {
      console.warn("[kinetis-search] search is unstyled: " + error.message);
    });
    var js = load("script", { src: primary.path + "pagefind-component-ui.js" });
    Promise.all([css, js])
      .then(function () {
        var components = window.PagefindComponents;
        if (!components) {
          throw new Error("pagefind-component-ui.js defined no PagefindComponents");
        }
        components.configureInstance("default", options(primary, merged));
        if (page) {
          components.configureInstance("page", options(primary, merged));
        }
        if (placeholders.length) {
          buildModal(placeholders);
        }
        if (page) {
          buildPage(page, components);
        }
      })
      .catch(function (error) {
        console.warn("[kinetis-search] search is unavailable: " + error.message);
      });
  }

  if (!script || !/^https?:$/.test(location.protocol)) {
    return;
  }
  Promise.all(candidates().map(probe)).then(function (found) {
    var present = found.filter(Boolean);
    if (!present.length) {
      return;
    }
    // The own bundle is the first candidate, so the first present one is the
    // own bundle when it is there.
    var primary = present[0];
    var merged = present.slice(1).filter(function (bundle) {
      if (bundle.version === primary.version) {
        return true;
      }
      console.warn(
        "[kinetis-search] not merging " + bundle.path + ": Pagefind " + bundle.version +
          ", but " + primary.path + " is Pagefind " + primary.version,
      );
      return false;
    });
    start(primary, merged);
  });
})();
