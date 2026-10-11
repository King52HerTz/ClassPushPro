#!/usr/bin/env bash
# Scoped cloud-template update. Never runs scheduled jobs or sends notifications.
set -euo pipefail
umask 077
stage="$(realpath "${1:?staging directory required}")"
case "$stage" in /opt/classpush-cloud/staging/*) ;; *) exit 1 ;; esac
current="$(realpath /opt/classpush-cloud/current)"
case "$current" in /opt/classpush-cloud/releases/*) ;; *) exit 1 ;; esac
files=(RestoredSource/src/push_content.py cloud/service.py)
for file in "${files[@]}"; do test -f "$stage/$file"; test -f "$current/$file"; done
(cd "$stage" && /opt/classpush-cloud/venv/bin/python -m unittest discover -s RestoredSource/tests -q)
(cd "$stage" && /opt/classpush-cloud/venv/bin/python -m unittest discover -s cloud/tests -q)
backup="$(mktemp -d /opt/classpush-cloud/backups/receipt-20261011-XXXXXX)"
for file in "${files[@]}"; do
  mkdir -p "$backup/$(dirname "$file")"
  cp -a "$current/$file" "$backup/$file"
done
rollback() {
  trap - ERR
  for file in "${files[@]}"; do cp -a "$backup/$file" "$current/$file"; done
  systemctl start classpush-cloud-api classpush-cloud-worker
  printf '%s\n' 'Template deployment failed; original source restored. No database restored.'
}
trap rollback ERR
systemctl stop classpush-cloud-worker classpush-cloud-api
database_before="$(sha256sum /var/lib/classpush-cloud/cloud.sqlite3)"
release_before="$(sha256sum /www/wwwroot/classpush.eliauk312.top/version.json /www/wwwroot/classpush.eliauk312.top/ClassPush_Setup.exe)"
for file in "${files[@]}"; do
  install -m 644 "$stage/$file" "$current/$file.new"
  mv -f "$current/$file.new" "$current/$file"
  cmp -s "$stage/$file" "$current/$file"
done
test "$database_before" = "$(sha256sum /var/lib/classpush-cloud/cloud.sqlite3)"
test "$release_before" = "$(sha256sum /www/wwwroot/classpush.eliauk312.top/version.json /www/wwwroot/classpush.eliauk312.top/ClassPush_Setup.exe)"
systemctl start classpush-cloud-api
healthy=false
for attempt in {1..15}; do
  if curl --silent --fail --max-time 2 http://127.0.0.1:8765/api/cloud/health >/dev/null; then healthy=true; break; fi
  sleep 1
done
test "$healthy" = true
systemctl start classpush-cloud-worker
systemctl is-active --quiet classpush-cloud-api classpush-cloud-worker
trap - ERR
printf 'Template deployed; source verified; account DB, installer and manifest unchanged. Backup: %s\n' "$backup"
