#!/usr/bin/env bash
# Downloads the two large Yigdal videos into site/assets/video/ at build
# time. The Rome video exceeds GitHub's 100 MB per-file limit, so both live
# as assets on the public GitHub release tagged "site-media" instead of in
# the repository. No token needed: the repository is public.
set -euo pipefail

BASE="https://github.com/mmeamazon544/kzzhv/releases/download/site-media"
DEST="site/assets/video"

for name in \
  yigdal-rome-tempio-maggiore-hoshana-rabbah.mp4 \
  yigdal-london-bevis-marks-dweck.mp4
do
  if [ -s "${DEST}/${name}" ]; then
    echo "fetch-media: ${name} already present, skipping"
    continue
  fi
  echo "fetch-media: downloading ${name}"
  curl -sfL --retry 3 -o "${DEST}/${name}" "${BASE}/${name}"
  ls -lh "${DEST}/${name}"
done

echo "fetch-media: done"
