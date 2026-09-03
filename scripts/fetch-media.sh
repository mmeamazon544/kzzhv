#!/usr/bin/env bash
# Downloads the two large Yigdal videos into site/assets/video/ at build
# time. The Rome video exceeds GitHub's 100 MB per-file limit, so both live
# as assets on the GitHub release tagged "site-media" instead of in the
# repository. Requires two environment variables, set in Netlify:
#   GITHUB_MEDIA_REPO   owner/name of this repository
#   GITHUB_MEDIA_TOKEN  fine-grained token with read access to contents
set -euo pipefail

DEST="site/assets/video"
TAG="site-media"

if [ -z "${GITHUB_MEDIA_REPO:-}" ] || [ -z "${GITHUB_MEDIA_TOKEN:-}" ]; then
  echo "fetch-media: GITHUB_MEDIA_REPO / GITHUB_MEDIA_TOKEN not set" >&2
  exit 1
fi

api="https://api.github.com/repos/${GITHUB_MEDIA_REPO}/releases/tags/${TAG}"
curl -sfL -H "Authorization: Bearer ${GITHUB_MEDIA_TOKEN}" "$api" |
python3 -c '
import json, sys
for a in json.load(sys.stdin)["assets"]:
    print(a["id"], a["name"])
' | while read -r id name; do
  out="${DEST}/${name}"
  if [ -s "$out" ]; then
    echo "fetch-media: ${name} already present, skipping"
    continue
  fi
  echo "fetch-media: downloading ${name}"
  curl -sfL --retry 3 \
    -H "Authorization: Bearer ${GITHUB_MEDIA_TOKEN}" \
    -H "Accept: application/octet-stream" \
    -o "$out" \
    "https://api.github.com/repos/${GITHUB_MEDIA_REPO}/releases/assets/${id}"
  ls -lh "$out"
done

echo "fetch-media: done"
