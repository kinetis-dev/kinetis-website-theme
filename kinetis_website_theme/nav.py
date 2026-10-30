"""The kinetis.dev site navigation, defined once for every section."""

from typing import NamedTuple


class Item(NamedTuple):
    label: str
    href: str


NAV = (
    Item("Home", "/"),
    Item("Docs", "/docs/"),
    Item("Vector", "/vector/docs/"),
    Item("Blog", "/blog/"),
)

# The Pagefind bundle of every kinetis.dev build (docs/SEARCH.md §1, §4.1).
# kinetis-search.js probes these, after the page's own bundle, and merges
# every one that is present.
SEARCH_BUNDLES = ("/pagefind/", "/docs/pagefind/", "/vector/docs/pagefind/")

# The Pagefind `section` of a page, by the NAV item that owns it; a page no
# item owns, the site root included, is Main (docs/SEARCH.md §3).
SEARCH_SECTIONS = {"Docs": "Docs", "Vector": "Vector", "Blog": "Blog"}
MAIN_SECTION = "Main"


def search_section(active: str | None) -> str:
    """The Pagefind section of a page whose active NAV item is ``active``."""
    return SEARCH_SECTIONS.get(active, MAIN_SECTION)


def active_section(url_path: str) -> str | None:
    """Return the label of the NAV item that owns ``url_path``.

    The longest href that is a prefix of the path wins. "/" is a prefix of
    every path, so it matches only the site root itself; a trailing
    ``index.html`` is read as its directory, so ``/index.html`` is the root.
    One exact rule more: a path equal to an href without its trailing slash
    plus ``.html`` belongs to that item, so ablog's root listing
    ``/blog.html`` is Blog. It is no general prefix: ``/blogger.html`` is not.
    """
    if url_path.endswith("/index.html"):
        url_path = url_path[: -len("index.html")]
    best = None
    for item in NAV:
        if item.href == "/":
            matches = url_path == "/"
        else:
            matches = url_path.startswith(item.href) or url_path == item.href.removesuffix("/") + ".html"
        if matches and (best is None or len(item.href) > len(best.href)):
            best = item
    return best.label if best else None
