#!/bin/sh
set -eu

mkdir -p \
  /var/www/html/storage/projects \
  /var/www/html/storage/songbooks \
  /var/www/html/storage/exports \
  /var/www/html/storage/cache \
  /var/www/html/storage/cache/runtime-home/.cache \
  /var/www/html/storage/cache/runtime-home/.config \
  /var/www/html/storage/cache/runtime-home/.local/share \
  /var/www/html/storage/logs \
  /var/www/html/storage/jobs/pending \
  /var/www/html/storage/jobs/processing \
  /var/www/html/storage/jobs/completed \
  /var/www/html/storage/jobs/failed

chown -R www-data:www-data /var/www/html/storage

exec "$@"
