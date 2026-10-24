"""The kinetis.dev site navigation, defined once for every section."""

from typing import NamedTuple


class Item(NamedTuple):
    label: str
    href: str


NAV = (
    Item("Home", "/"),
    Item("Docs", "/docs/"),
    Item("Vector", "/vector/docs/"),  # v0.1-v0.2; becomes "/vector/" in v0.3.0 when the landing exists
    # Item("Blog", "/blog/")          # v0.3.0
)


def active_section(url_path: str) -> str | None:
    """Return the label of the NAV item that owns ``url_path``.

    The longest href that is a prefix of the path wins. "/" is a prefix of
    every path, so it matches only the site root itself; a trailing
    ``index.html`` is read as its directory, so ``/index.html`` is the root.
    """
    if url_path.endswith("/index.html"):
        url_path = url_path[: -len("index.html")]
    best = None
    for item in NAV:
        matches = url_path == "/" if item.href == "/" else url_path.startswith(item.href)
        if matches and (best is None or len(item.href) > len(best.href)):
            best = item
    return best.label if best else None
