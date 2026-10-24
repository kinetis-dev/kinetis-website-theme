# Screenshot goldens

`goldens.py` screenshots the two built sample projects in light and dark
mode with Playwright (Chromium, 1280×900 viewport) and compares each shot
with the PNG here:

| Shot | Project | URL | Goldens |
|---|---|---|---|
| `docs-guide` | `tests/sample-site` | `/guide.html` | `docs-guide-light.png`, `docs-guide-dark.png` |
| `website-landing` | `tests/sample-website` | `/` | `website-landing-light.png`, `website-landing-dark.png` |
| `website-404` | `tests/sample-website` | `/a/b/c/missing` | `website-404-light.png`, `website-404-dark.png` |
| `website-blog-post` | `tests/sample-website` | `/blog/posts/hello-kinetis.html` | `website-blog-post-light.png`, `website-blog-post-dark.png` |

The 404 shot requests a nested URL that does not exist. The harness's server
answers every missing file with the build's `404.html` and status 404, as
the website's S3 bucket does with its ErrorDocument, so the shot shows the
page rendering from any depth.

## Tolerance

A pixel counts as changed when any colour channel differs by more than
`CHANNEL_TOLERANCE` (24 of 255), which absorbs antialiasing noise. A
screenshot fails when more than `MAX_CHANGED_RATIO` (0.2%) of its pixels
changed, or when its size differs. A shot with no golden PNG here also
fails, and the run names it. On failure the CI job uploads the
`goldens-output` artifact, which holds `<name>-actual.png` and a black and
white `<name>-diff.png` mask of the changed pixels.

## Capturing and re-capturing

Font rendering differs between operating systems, so goldens are only valid
when they are captured in the image CI uses. Never commit shots from a
desktop browser.

From the repository root, with Docker:

```sh
docker run --rm -v "$PWD":/work -w /work mcr.microsoft.com/playwright/python:v1.63.0-noble bash -c '
  export PIP_BREAK_SYSTEM_PACKAGES=1 &&
  python3 -m pip install -q build playwright==1.63.0 pillow &&
  python3 -m build --wheel --outdir /tmp/dist &&
  python3 -m pip install -q "$(ls /tmp/dist/*.whl)[blog,notfound]" \
    -r tests/sample-site/requirements.txt -r tests/sample-website/requirements.txt &&
  cd /tmp && sphinx-build -W --keep-going -b html /work/tests/sample-site /tmp/site &&
  sphinx-build -W --keep-going -b html /work/tests/sample-website /tmp/website &&
  python3 /work/tests/goldens/goldens.py update /tmp/site /tmp/website --only "$@"' goldens \
  website-landing website-404 website-blog-post
```

The names after `goldens` are the shots to capture. Add `docs-guide` only
when a change to the docs page is intended. To re-capture every shot, drop
both the names and `--only "$@"`.

Without Docker, take the `goldens-output` artifact of a failed CI run and
copy its `*-actual.png` files here without the `-actual` suffix.

Either way, open the images and check them before committing: a
re-capture accepts whatever the theme renders now. Re-capture only when a
visual change is intended, and say so in the PR.
