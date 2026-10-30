"""Index a built sample with the pinned Pagefind and read back what it indexed.

Pagefind writes one fragment per indexed page under pagefind/fragment/: gzip
data that starts with the "pagefind_dcd" signature, then the page's JSON
(url, content, meta, filters). The build tests assert on those, so they see
exactly what a search will find.
"""

import gzip
import json
import subprocess
import sys
from pathlib import Path

# The version every consumer pins (docs/SEARCH.md §1); CI installs it.
PAGEFIND_VERSION = "1.5.2"
SIGNATURE = b"pagefind_dcd"


def index(build):
    """Run `python -m pagefind --site <build>`, as every consumer does."""
    return subprocess.run([sys.executable, "-m", "pagefind", "--site", str(build)], capture_output=True, text=True)


def version():
    result = subprocess.run([sys.executable, "-m", "pagefind", "--version"], capture_output=True, text=True)
    return result.stdout.strip()


def fragments(build):
    """{url: fragment} for every page Pagefind indexed in the build."""
    pages = {}
    for path in sorted((Path(build) / "pagefind" / "fragment").glob("*.pf_fragment")):
        data = gzip.decompress(path.read_bytes())
        if not data.startswith(SIGNATURE):
            raise ValueError(f"{path}: not a Pagefind fragment")
        fragment = json.loads(data[len(SIGNATURE):])
        pages[fragment["url"]] = fragment
    return pages
