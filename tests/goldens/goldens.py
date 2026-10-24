#!/usr/bin/env python3
"""Light/dark screenshot goldens of the built sample site.

  goldens.py check <build-dir>    compare against tests/goldens/*.png
  goldens.py update <build-dir>   re-capture tests/goldens/*.png

Runs in CI on mcr.microsoft.com/playwright/python; see README.md here for
why the goldens must be captured in that image and how. Needs playwright
and pillow, which are not theme dependencies.
"""

import argparse
import functools
import http.server
import sys
import threading
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

GOLDENS = Path(__file__).resolve().parent
# Docs page only in v0.1.0; landing, 404 and blog post goldens arrive in phase 4.
PAGES = {"docs-guide": "guide.html"}
MODES = ("light", "dark")
VIEWPORT = {"width": 1280, "height": 900}
# A pixel counts as changed when any channel moves by more than this
# (absorbs antialiasing noise) ...
CHANNEL_TOLERANCE = 24
# ... and a screenshot fails when more than this fraction of pixels changed.
MAX_CHANGED_RATIO = 0.002


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(build):
    handler = functools.partial(QuietHandler, directory=str(build))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def capture(build, channel=None):
    """Yield (name, PNG bytes) for every page in every mode."""
    server = serve(build)
    base = f"http://127.0.0.1:{server.server_address[1]}/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel=channel)
            for mode in MODES:
                context = browser.new_context(viewport=VIEWPORT, color_scheme=mode, reduced_motion="reduce")
                # pydata reads the chosen mode from localStorage before first paint.
                context.add_init_script(f"localStorage.setItem('mode', '{mode}'); localStorage.setItem('theme', '{mode}');")
                page = context.new_page()
                for name, path in PAGES.items():
                    page.goto(base + path, wait_until="networkidle")
                    page.evaluate("document.fonts.ready")
                    yield f"{name}-{mode}", page.screenshot(animations="disabled", caret="hide")
                context.close()
            browser.close()
    finally:
        server.shutdown()


def changed_ratio(golden, actual):
    if golden.size != actual.size:
        return 1.0, None
    red, green, blue = ImageChops.difference(golden.convert("RGB"), actual.convert("RGB")).split()
    # The largest channel difference per pixel, thresholded to a 0/255 mask.
    largest = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    mask = largest.point(lambda v: 255 if v > CHANNEL_TOLERANCE else 0)
    changed = mask.histogram()[255]
    return changed / (golden.width * golden.height), mask


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("check", "update"))
    parser.add_argument("build", type=Path)
    parser.add_argument("--out", type=Path, default=Path("goldens-output"),
                        help="where check writes actual and diff images (default: ./goldens-output)")
    parser.add_argument("--channel", help="browser channel, e.g. chrome, for a local preview run")
    args = parser.parse_args(argv)

    failures = 0
    args.out.mkdir(parents=True, exist_ok=True)
    for name, png in capture(args.build, args.channel):
        golden_path = GOLDENS / f"{name}.png"
        if args.mode == "update":
            golden_path.write_bytes(png)
            print(f"{name}: captured {golden_path}")
            continue
        actual_path = args.out / f"{name}-actual.png"
        actual_path.write_bytes(png)
        if not golden_path.exists():
            print(f"{name}: no golden at {golden_path}; captured {actual_path}")
            failures += 1
            continue
        with Image.open(golden_path) as golden, Image.open(actual_path) as actual:
            ratio, mask = changed_ratio(golden, actual)
        ok = ratio <= MAX_CHANGED_RATIO
        print(f"{name}: {ratio:.4%} of pixels changed (limit {MAX_CHANGED_RATIO:.2%}) {'ok' if ok else 'FAIL'}")
        if not ok:
            failures += 1
            if mask is not None:
                mask.save(args.out / f"{name}-diff.png")
    if failures:
        print(f"goldens: {failures} failure(s); actual and diff images are in {args.out}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
