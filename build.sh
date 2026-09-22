#!/usr/bin/env bash
# Render / CI build: install, collect static from static/, migrate.
#
# Also set this exact command in the Render dashboard Build Command
# (blueprint updates do not always override an existing service):
#   bash build.sh
set -euo pipefail

pip install -r requirements.txt

python manage.py collectstatic --noinput --clear

# Fail the build if WhiteNoise would ship without critical assets.
required=(
  staticfiles/css/index.css
  staticfiles/css/booking.css
  staticfiles/css/counsellors.css
  staticfiles/js/index.js
  staticfiles/js/booking.js
  staticfiles/js/counsellors.js
)
for path in "${required[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "collectstatic missing required file: $path" >&2
    exit 1
  fi
done

echo "collectstatic ok: $(find staticfiles -type f | wc -l) files"

python manage.py migrate --noinput
