# kinetis-website inputs

Byte-identical copies of kinetis-website's `html/index.html`,
`html/404.html` and `html/css/style.css` at website commit `23a08af`
(footer Packagist link from `0ea6559`; the 404 button rules `.cta`,
`.button*` and `--amber-light`, restored in `23a08af`). They are test
fixtures, not theme sources:

- `tests/sample-website/index.md` and `404.md` carry the two `<body>`s
  verbatim in a `{raw} html` block, and the landing also carries the
  JSON-LD `<script>` from `index.html`'s head. They deviate in two ways,
  both in both pages. `<main class="tiles">` is written as
  `<div class="tiles">`, because pydata's `<main id="main-content">` is the
  page's only main landmark. The body's single `<footer>…</footer>` element
  is left out, with the whitespace before it, because pydata's footer with
  the theme's shared `kinetis-footer` is the page's only footer (theme
  0.3.0). `tests/test_sample_website.py` compares the built bodies (its
  `input_body()` applies exactly these two deviations), the landing's head
  whitelist and the JSON-LD with these files.
- `kinetis_website_theme/.../static/kinetis-landing.css` is `style.css`
  scoped mechanically, its footer rules dropped; `tests/test_landing_css.py`
  re-derives it from this copy.

Refresh them only together with a website change that phase 5b carries
over, and say so in the commit.
