# kinetis-website inputs

Byte-identical copies of kinetis-website's `html/index.html`,
`html/404.html` and `html/css/style.css` at website commit `23a08af`
(footer Packagist link from `0ea6559`; the 404 button rules `.cta`,
`.button*` and `--amber-light`, restored in `23a08af`). They are test
fixtures, not theme sources:

- `tests/sample-website/index.md` and `404.md` carry the two `<body>`s
  verbatim in a `{raw} html` block, and the landing also carries the
  JSON-LD `<script>` from `index.html`'s head. The one deviation in both
  is `<main class="tiles">` written as `<div class="tiles">`, because
  pydata's `<main id="main-content">` is the page's only main landmark.
  `tests/test_sample_website.py` compares the built bodies, the landing's
  head whitelist and the JSON-LD with these files.
- `kinetis_website_theme/.../static/kinetis-landing.css` is `style.css`
  scoped mechanically; `tests/test_landing_css.py` re-derives it from this
  copy.

Refresh them only together with a website change that phase 5b carries
over, and say so in the commit.
