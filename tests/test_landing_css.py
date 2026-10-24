"""kinetis-landing.css is kinetis-website's style.css, scoped mechanically.

The rules (design 2.5, brief item 2): every selector is prefixed with
.kinetis-landing; `:root` and `body` become .kinetis-landing itself; the
prefers-color-scheme dark block becomes html[data-theme="dark"]
.kinetis-landing, since pydata always stamps a resolved data-theme on <html>;
the logo url points at the theme's bundled logo.svg, next to the stylesheet;
the width @media queries stay, scoped; a rule whose every selector starts
with `footer` is dropped, with the comment heading such rules, because
landing pages show pydata's footer with the shared kinetis-footer and the
body carries none. scope() below applies exactly those rules to
tests/website-inputs/style.css, and the stylesheet the theme ships
must equal its output after the file's header comment, so no colour, value
or rule can enter or leave the stylesheet by hand.
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STYLE_CSS = REPO / "tests" / "website-inputs" / "style.css"
LANDING_CSS = REPO / "kinetis_website_theme" / "theme" / "kinetis_website_theme" / "static" / "kinetis-landing.css"

SCOPE = ".kinetis-landing"
DARK_MEDIA = "@media (prefers-color-scheme: dark)"
DARK_SCOPE = 'html[data-theme="dark"] .kinetis-landing'
LOGO_URLS = ("url('../assets/logo.svg')", "url('logo.svg')")


def scope_selector(selector):
    selector = selector.strip()
    if selector in (":root", "body"):
        return SCOPE
    return f"{SCOPE} {selector}"


FOOTER_SELECTOR = re.compile(r"footer(?![\w-])")


def is_footer_rule(prelude):
    return not prelude.startswith("@") and all(FOOTER_SELECTOR.match(s.strip()) for s in prelude.split(","))


def next_prelude(css, i):
    """The prelude of the rule after offset i, past whitespace, or None."""
    while i < len(css) and css[i].isspace():
        i += 1
    if i >= len(css) or css.startswith("/*", i) or "{" not in css[i:]:
        return None
    return css[i : css.index("{", i)].strip()


def drop_trailing_whitespace(out):
    while out and out[-1].isspace():
        out.pop()


def matching_brace(css, start):
    depth = 0
    for i in range(start, len(css)):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"unbalanced braces from offset {start}")


def scope(css, dropped=None):
    """Apply the scoping rules; comments and whitespace pass through unchanged.

    A dropped footer rule or its heading comment goes with the whitespace
    before it; its source text is appended to ``dropped`` when given.
    """
    if dropped is None:
        dropped = []
    out = []
    i = 0
    while i < len(css):
        if css.startswith("/*", i):
            end = css.index("*/", i) + 2
            following = next_prelude(css, end)
            if following is not None and is_footer_rule(following):
                drop_trailing_whitespace(out)
                dropped.append(css[i:end])
            else:
                out.append(css[i:end])
            i = end
            continue
        if css[i].isspace():
            out.append(css[i])
            i += 1
            continue
        brace = css.index("{", i)
        prelude = css[i:brace].strip()
        close = matching_brace(css, brace)
        block = css[brace + 1 : close]
        if prelude == DARK_MEDIA:
            inner = block.strip()
            if not inner.startswith(":root") or inner.count("{") != 1:
                raise ValueError("the dark @media block must hold one :root rule")
            declarations = inner[inner.index("{") + 1 : inner.rindex("}")]
            # One nesting level less, as the rule leaves the @media block.
            declarations = "\n".join(line.removeprefix("    ") for line in declarations.split("\n"))
            out.append(f"{DARK_SCOPE} {{{declarations}}}")
        elif prelude.startswith("@media"):
            out.append(f"{prelude} {{{scope(block, dropped)}}}")
        elif prelude.startswith("@"):
            raise ValueError(f"no scoping rule for {prelude}")
        elif is_footer_rule(prelude):
            drop_trailing_whitespace(out)
            dropped.append(css[i : close + 1])
        else:
            selectors = ", ".join(scope_selector(s) for s in prelude.split(","))
            out.append(f"{selectors} {{{block.replace(*LOGO_URLS)}}}")
        i = close + 1
    return "".join(out)


def without_header_comment(css):
    match = re.match(r"/\*.*?\*/\n\n", css, re.DOTALL)
    if not match:
        raise AssertionError("kinetis-landing.css must start with its header comment and a blank line")
    return css[match.end() :]


def selectors(css):
    """Every selector of every rule, @media preludes excluded."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    found = []
    for prelude in re.findall(r"([^{}]+)\{", css):
        prelude = prelude.strip()
        if not prelude.startswith("@"):
            found.extend(s.strip() for s in prelude.split(","))
    return found


class LandingCssTest(unittest.TestCase):
    def test_shipped_stylesheet_is_style_css_scoped(self):
        expected = scope(STYLE_CSS.read_text(encoding="utf-8"))
        actual = without_header_comment(LANDING_CSS.read_text(encoding="utf-8"))
        self.assertEqual(expected, actual)

    def test_every_selector_is_scoped(self):
        found = selectors(without_header_comment(LANDING_CSS.read_text(encoding="utf-8")))
        self.assertGreater(len(found), 30)
        for selector in found:
            with self.subTest(selector=selector):
                self.assertTrue(selector == SCOPE or selector.startswith((SCOPE + " ", DARK_SCOPE)), selector)

    def test_no_colour_or_value_is_added_or_lost(self):
        def values(css):
            return sorted(re.findall(r"#[0-9A-Fa-f]{3,8}\b|\b\d*\.?\d+(?:px|rem|em|%)?\b", re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)))

        source = STYLE_CSS.read_text(encoding="utf-8")
        shipped = without_header_comment(LANDING_CSS.read_text(encoding="utf-8"))
        dropped = []
        scope(source, dropped)
        # Every value of style.css is either shipped or in a dropped footer rule.
        self.assertEqual(values(source), sorted(values(shipped) + values("\n".join(dropped))))

    def test_footer_rules_and_their_heading_are_dropped(self):
        source = STYLE_CSS.read_text(encoding="utf-8")
        dropped = []
        scope(source, dropped)
        self.assertEqual(["/* Footer */", "footer {", "footer a {", "footer a:hover {", "footer .sep {"],
                         [text.split("\n", 1)[0] for text in dropped])
        shipped = without_header_comment(LANDING_CSS.read_text(encoding="utf-8"))
        self.assertNotIn("footer", re.sub(r"/\*.*?\*/", "", shipped, flags=re.DOTALL))
        self.assertNotIn("/* Footer */", shipped)
        self.assertIn("color: var(--amber);\n}\n\n.kinetis-landing .eyebrow {", shipped)

    def test_dark_mode_keys_off_data_theme_not_the_media_query(self):
        shipped = LANDING_CSS.read_text(encoding="utf-8")
        self.assertNotIn("prefers-color-scheme", without_header_comment(shipped))
        self.assertEqual(1, shipped.count(DARK_SCOPE + " {"))
        self.assertNotIn(":root", without_header_comment(shipped))

    def test_logo_resolves_next_to_the_stylesheet(self):
        shipped = LANDING_CSS.read_text(encoding="utf-8")
        self.assertIn("url('logo.svg')", shipped)
        self.assertNotIn("../assets/", shipped)
        self.assertTrue((LANDING_CSS.parent / "logo.svg").is_file())

    def test_the_restored_404_button_rules_are_scoped(self):
        shipped = LANDING_CSS.read_text(encoding="utf-8")
        for selector in (".cta", ".button", ".button.primary", ".button.primary:hover",
                         ".button.secondary", ".button.secondary:hover"):
            with self.subTest(selector=selector):
                self.assertIn(f"\n{SCOPE} {selector} {{", shipped)
        self.assertIn("--amber-light: #F59E0B;", shipped)


if __name__ == "__main__":
    unittest.main()
