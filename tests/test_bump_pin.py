import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import bump_pin  # noqa: E402

OLD = "https://github.com/kinetis-dev/kinetis-website-theme/releases/download/v0.1.0/kinetis_website_theme-0.1.0-py3-none-any.whl"
NEW = "https://github.com/kinetis-dev/kinetis-website-theme/releases/download/v0.2.0/kinetis_website_theme-0.2.0-py3-none-any.whl"

REQUIREMENTS = f"""sphinx>=8.0,<9
myst-parser>=4.0
kinetis-website-theme @ {OLD}
sphinx-sitemap>=2.6
"""


class BumpPinTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.path = self.root / "requirements.txt"

    def run_main(self, text, version):
        self.path.write_bytes(text.encode())
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = bump_pin.main([str(self.path), version])
        return code, out.getvalue(), err.getvalue()

    def test_rewrites_only_the_pin_line_and_prints_a_diff(self):
        code, out, _ = self.run_main(REQUIREMENTS, "0.2.0")
        self.assertEqual(0, code)
        self.assertEqual(REQUIREMENTS.replace(OLD, NEW), self.path.read_text())
        self.assertIn(f"-kinetis-website-theme @ {OLD}\n", out)
        self.assertIn(f"+kinetis-website-theme @ {NEW}\n", out)
        self.assertNotIn("-sphinx>=8.0,<9", out)

    def test_keeps_extras(self):
        text = f"kinetis-website-theme[blog,notfound] @ {OLD}\n"
        self.run_main(text, "0.2.0")
        self.assertEqual(f"kinetis-website-theme[blog,notfound] @ {NEW}\n", self.path.read_text())

    def test_keeps_crlf_line_endings(self):
        text = REQUIREMENTS.replace("\n", "\r\n")
        self.run_main(text, "0.2.0")
        self.assertEqual(text.replace(OLD, NEW).encode(), self.path.read_bytes())

    def test_same_version_is_a_no_op(self):
        code, out, _ = self.run_main(REQUIREMENTS, "0.1.0")
        self.assertEqual(0, code)
        self.assertIn("already pinned to 0.1.0", out)
        self.assertEqual(REQUIREMENTS, self.path.read_text())

    def test_missing_pin_fails_without_writing(self):
        text = "sphinx>=8.0,<9\nfuro>=2024.8\n"
        code, _, err = self.run_main(text, "0.2.0")
        self.assertEqual(1, code)
        self.assertIn("found 0", err)
        self.assertEqual(text, self.path.read_text())

    def test_two_pins_fail(self):
        code, _, err = self.run_main(REQUIREMENTS + f"kinetis_website_theme @ {OLD}\n", "0.2.0")
        self.assertEqual(1, code)
        self.assertIn("found 2", err)

    def test_rejects_a_tag_instead_of_a_version(self):
        code, _, err = self.run_main(REQUIREMENTS, "v0.2.0")
        self.assertEqual(1, code)
        self.assertIn("expected X.Y.Z", err)
        self.assertEqual(REQUIREMENTS, self.path.read_text())


if __name__ == "__main__":
    unittest.main()
