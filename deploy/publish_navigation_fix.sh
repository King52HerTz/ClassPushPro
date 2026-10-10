#!/usr/bin/env bash
# Change only public navigation and caching; retain installer, manifest and cloud data.
set -euo pipefail
umask 077
staging="$(realpath "${1:?staging directory required}")"
case "$staging" in /opt/classpush-cloud/staging/*) ;; *) exit 1 ;; esac
site=/www/wwwroot/classpush.eliauk312.top
include=/www/server/panel/vhost/nginx/classpush-cloud.inc
nginx=/www/server/nginx/sbin/nginx
files=(site.js index.html cloud.html calendar.html download.html faq.html privacy.html)
for file in "${files[@]}"; do test -f "$staging/website/$file"; done
test -f "$staging/deploy/nginx-cloud.conf"
backup="/opt/classpush-cloud/backups/navigation-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup"
cp -a "$site" "$backup/website"
cp -a "$include" "$backup/nginx-cloud.inc"
before="$(sha256sum "$site/version.json" "$site/ClassPush_Setup.exe")"
rollback() {
  trap - ERR
  for file in "${files[@]}"; do install -m 644 "$backup/website/$file" "$site/$file"; done
  install -m 644 "$backup/nginx-cloud.inc" "$include"
  "$nginx" -t && "$nginx" -s reload
  printf 'Navigation publish failed; restored backup: %s\n' "$backup"
}
trap rollback ERR
for file in "${files[@]}"; do
  install -m 644 "$staging/website/$file" "$site/$file.classpush-new"
  mv -f "$site/$file.classpush-new" "$site/$file"
done
install -m 644 "$staging/deploy/nginx-cloud.conf" "$include"
"$nginx" -t
"$nginx" -s reload
after="$(sha256sum "$site/version.json" "$site/ClassPush_Setup.exe")"
test "$before" = "$after"
trap - ERR
printf 'Navigation/cache fix published. Installer/manifest unchanged. Backup: %s\n' "$backup"
