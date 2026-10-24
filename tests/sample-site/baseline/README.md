# Sample-site URL baseline

Captured from the sample site by `tools/check_url_baseline.py`, the kinetis
phase-0 guard copied with only its path defaults changed. It is the theme's
guard self-test: CI builds the sample site and runs `check` against these
files, so a theme change that drops a heading id, changes a `<title>`,
canonical or `og:url`, or loses a page fails CI here before any consumer
sees it. The file format is described in kinetis `docs/baseline/README.md`.

`anchors.json` lists, per page, the ids inside the page's main landmark. That
is the outermost element that is a `<main>` tag or has `role="main"`: pydata's
`<main>` here, Furo's `<article role="main">` in a Furo build. The landmark's
own id, `sd-` ids and ids inside a `data-pagefind-ignore` subtree are left
out.

`aux.txt`, `external-anchors.txt` and `redirects.txt` are curated; the other
four files are derived.

Unlike the kinetis baseline, this one belongs to placeholder content and may
be re-captured when the sample pages change on purpose:

```sh
sphinx-build -W --keep-going -b html tests/sample-site _build
python3 tools/check_url_baseline.py capture _build
```

Re-capture never fixes a theme regression: if `check` fails after a theme
change and the sample pages did not change, the theme is wrong.
