# Screenshot goldens

`goldens.py` screenshots the built sample site in light and dark mode with
Playwright (Chromium, 1280×900 viewport) and compares each shot with the PNG
here. v0.1.0 covers one docs page (`guide.html`): `docs-guide-light.png` and
`docs-guide-dark.png`. Landing, 404 and blog post goldens arrive in v0.2.0.

## Tolerance

A pixel counts as changed when any colour channel differs by more than
`CHANNEL_TOLERANCE` (24 of 255), which absorbs antialiasing noise. A
screenshot fails when more than `MAX_CHANGED_RATIO` (0.2%) of its pixels
changed, or when its size differs. On failure the CI job uploads the
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
  python3 -m pip install -q "$(ls /tmp/dist/*.whl)" -r tests/sample-site/requirements.txt &&
  cd /tmp && sphinx-build -W --keep-going -b html /work/tests/sample-site /tmp/site &&
  python3 /work/tests/goldens/goldens.py update /tmp/site'
```

Without Docker, take the `goldens-output` artifact of a failed CI run and
copy its `*-actual.png` files here without the `-actual` suffix.

Either way, open the images and check them before committing: a
re-capture accepts whatever the theme renders now. Re-capture only when a
visual change is intended, and say so in the PR.
