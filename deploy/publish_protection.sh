#!/usr/bin/env bash
# Publish a new immutable code directory. Preserve accounts, keys and prior releases.
set -euo pipefail
umask 077
staging="$(realpath "${1:?staging directory required}")"
case "$staging" in /opt/classpush-cloud/staging/*) ;; *) exit 1 ;; esac
site=/www/wwwroot/classpush.eliauk312.top
current=/opt/classpush-cloud/current
previous="$(realpath "$current")"
case "$previous" in /opt/classpush-cloud/releases/*) ;; *) exit 1 ;; esac
release=/opt/classpush-cloud/releases/3.0.2-protection
python=/opt/classpush-cloud/venv/bin/python
package="$staging/ClassPush_Setup_3.0.2.exe"
database=/var/lib/classpush-cloud/cloud.sqlite3
test ! -e "$release"
"$python" - "$staging/website/version.json" "$package" <<'PY'
import hashlib, json, pathlib, sys
manifest = json.loads(pathlib.Path(sys.argv[1]).read_text())
data = pathlib.Path(sys.argv[2]).read_bytes()
assert manifest['version'] == '3.0.2' and manifest['available'] is True
assert len(data) == manifest['size_bytes']
assert hashlib.sha256(data).hexdigest() == manifest['sha256']
assert data.startswith(b'MZ')
assert manifest['download_url'] == 'https://classpush.eliauk312.top/downloads/ClassPush_Setup_3.0.2.exe'
assert manifest['lanzou_url'] == manifest['download_url']
PY
(cd "$staging" && "$python" -m unittest discover -s cloud/tests -q)
mkdir -p "$release/RestoredSource"
cp -a "$staging/cloud" "$release/cloud"
cp -a "$staging/RestoredSource/src" "$release/RestoredSource/src"
cp -a "$staging/RestoredSource/requirements-core.txt" "$release/RestoredSource/"
find "$release" -type d -exec chmod 755 {} +
find "$release" -type f -exec chmod 644 {} +
backup="/opt/classpush-cloud/backups/protection-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup"
cp -a "$site" "$backup/website"
printf '%s\n' "$previous" > "$backup/previous-release.txt"
rollback() {
  trap - ERR
  systemctl stop classpush-cloud-worker classpush-cloud-api || true
  ln -s "$previous" /opt/classpush-cloud/.current-rollback
  mv -Tf /opt/classpush-cloud/.current-rollback "$current"
  while IFS= read -r -d '' file; do
    relative="${file#"$staging/website/"}"
    if [ -f "$backup/website/$relative" ]; then
      install -m 644 "$backup/website/$relative" "$site/$relative"
    fi
  done < <(find "$staging/website" -type f -print0)
  install -m 644 "$backup/website/ClassPush_Setup.exe" "$site/ClassPush_Setup.exe"
  # Keep additive schema and current user data; never overwrite the live database.
  systemctl start classpush-cloud-api classpush-cloud-worker
  printf 'Publish failed; restored prior code/site. Backup: %s\n' "$backup"
}
trap rollback ERR
systemctl stop classpush-cloud-worker classpush-cloud-api
"$python" - "$database" "$backup" <<'PY'
import json, pathlib, sqlite3, sys
db = sqlite3.connect(sys.argv[1])
backup = pathlib.Path(sys.argv[2])
copy = sqlite3.connect(backup / 'cloud.sqlite3')
db.backup(copy)
copy.close()
# No username, UID, password or encrypted state in deployment output.
rows = db.execute('SELECT id,morning,evening,grades,paused,needs_auth FROM accounts ORDER BY id').fetchall()
(backup / 'account-settings.json').write_text(json.dumps(rows))
db.close()
PY
install -d -m 755 "$site/downloads"
install -m 644 "$package" "$site/downloads/.ClassPush_Setup_3.0.2.exe.new"
mv -f "$site/downloads/.ClassPush_Setup_3.0.2.exe.new" "$site/downloads/ClassPush_Setup_3.0.2.exe"
install -m 644 "$package" "$site/.ClassPush_Setup.exe.new"
mv -f "$site/.ClassPush_Setup.exe.new" "$site/ClassPush_Setup.exe"
while IFS= read -r -d '' file; do
  relative="${file#"$staging/website/"}"
  [ "$relative" != version.json ] || continue
  install -d -m 755 "$(dirname "$site/$relative")"
  install -m 644 "$file" "$site/$relative.classpush-new"
  mv -f "$site/$relative.classpush-new" "$site/$relative"
done < <(find "$staging/website" -type f -print0)
ln -s "$release" /opt/classpush-cloud/.current-new
mv -Tf /opt/classpush-cloud/.current-new "$current"
systemctl start classpush-cloud-api
healthy=false
for attempt in {1..20}; do
  if curl --silent --fail --max-time 2 http://127.0.0.1:8765/api/cloud/health >/dev/null; then healthy=true; break; fi
  sleep 1
done
test "$healthy" = true
"$python" - "$database" "$backup/account-settings.json" <<'PY'
import json, pathlib, sqlite3, sys
db = sqlite3.connect(sys.argv[1])
rows = db.execute('SELECT id,morning,evening,grades,paused,needs_auth FROM accounts ORDER BY id').fetchall()
assert [list(row) for row in rows] == json.loads(pathlib.Path(sys.argv[2]).read_text())
assert db.execute('SELECT COUNT(*) FROM school_outbound WHERE id=1').fetchone()[0] == 1
assert 'retry_at' in {row[1] for row in db.execute('PRAGMA table_info(jobs)')}
print('Account settings preserved; protection schema ready. Account count:', len(rows))
db.close()
PY
systemctl start classpush-cloud-worker
systemctl is-active --quiet classpush-cloud-api classpush-cloud-worker
# Legacy clients see the new manifest only after the installer and services are ready.
install -m 644 "$staging/website/version.json" "$site/.version.json.new"
mv -f "$site/.version.json.new" "$site/version.json"
trap - ERR
printf 'Release 3.0.2 published. Backup: %s\n' "$backup"
