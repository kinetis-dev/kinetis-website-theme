"""The kinetis.dev site navigation, defined once for every section."""

from typing import NamedTuple


class Item(NamedTuple):
    label: str
    href: str


NAV = (
    Item("Home", "/"),
    Item("Docs", "/docs/"),
    Item("Vector", "/vector/"),
    Item("Blog", "/blog/"),
)


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
