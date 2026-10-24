#!/usr/bin/env python3
"""Point a consumer's kinetis-website-theme pin at another release.

  bump_pin.py <requirements.txt> <version>

Rewrites the one `kinetis-website-theme ... @ <release wheel URL>` line,
keeping any extras, and prints the change as a unified diff. Every other
line is left byte for byte. Exits 1 when the file has no such line or more
than one.
"""

import argparse
import difflib
import re
import sys
from pathlib import Path

URL = "https://github.com/kinetis-dev/kinetis-website-theme/releases/download/v{0}/kinetis_website_theme-{0}-py3-none-any.whl"
PIN = re.compile(r"^kinetis[-_.]website[-_.]theme\s*(?P<extras>\[[^\]]*\])?\s*@", re.I)
VERSION = re.compile(r"^\d+\.\d+\.\d+$")


def pin_line(version, extras=""):
    return f"kinetis-website-theme{extras} @ {URL.format(version)}"


def bump(text, version):
    """Return ``text`` with the theme pin pointing at ``version``."""
    if not VERSION.match(version):
        raise ValueError(f"version {version!r}: expected X.Y.Z")
    lines = text.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if PIN.match(line)]
    if len(matches) != 1:
        raise ValueError(f"expected one kinetis-website-theme @ <url> line, found {len(matches)}")
    i = matches[0]
    ending = lines[i][len(lines[i].rstrip("\r\n")):]
    lines[i] = pin_line(version, PIN.match(lines[i]).group("extras") or "") + ending
    return "".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("requirements", type=Path)
    parser.add_argument("version", help="release version without the v, e.g. 0.2.0")
    args = parser.parse_args(argv)

    # Bytes, not text mode, so CRLF line endings survive untouched.
    before = args.requirements.read_bytes().decode("utf-8")
    try:
        after = bump(before, args.version)
    except ValueError as error:
        print(f"{args.requirements}: {error}", file=sys.stderr)
        return 1
    if after == before:
        print(f"{args.requirements}: already pinned to {args.version}")
        return 0
    args.requirements.write_bytes(after.encode("utf-8"))
    name = str(args.requirements)
    sys.stdout.writelines(
        difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), name, name)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
