#!/usr/bin/env bash
# Publish the verified installer first and the legacy-compatible manifest last.
set -euo pipefail
umask 077
staging="$(realpath "${1:?staging directory required}")"
case "$staging" in /opt/classpush-cloud/staging/*) ;; *) exit 1 ;; esac
site=/www/wwwroot/classpush.eliauk312.top
current="$(realpath /opt/classpush-cloud/current)"
case "$current" in /opt/classpush-cloud/releases/*) ;; *) exit 1 ;; esac
package="$staging/ClassPush_Setup_3.0.0.exe"
python=/opt/classpush-cloud/venv/bin/python
"$python" - "$staging/website/version.json" "$package" <<'PY'
import hashlib, json, pathlib, sys
release = json.loads(pathlib.Path(sys.argv[1]).read_text())
data = pathlib.Path(sys.argv[2]).read_bytes()
assert release['version'] == '3.0.0' and release['available'] is True
assert len(data) == release['size_bytes']
assert hashlib.sha256(data).hexdigest() == release['sha256']
assert data.startswith(b'MZ')
assert release['download_url'] == 'https://classpush.eliauk312.top/downloads/ClassPush_Setup_3.0.0.exe'
assert release['lanzou_url'] == release['download_url']
assert isinstance(release['changelog'], str)
PY
(cd "$staging" && "$python" -m unittest discover -s cloud/tests -q)
backup="/opt/classpush-cloud/backups/release-3.0.0-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup"
cp -a "$site" "$backup/website"
cp -a "$current/cloud/app.py" "$backup/cloud-app.py"
rollback() {
  trap - ERR
  # Restore only published paths; BaoTa may make unrelated .user.ini immutable.
  while IFS= read -r -d '' file; do
    relative="${file#"$staging/website/"}"
    if [ -f "$backup/website/$relative" ]; then
      install -m 644 "$backup/website/$relative" "$site/$relative"
    fi
  done < <(find "$staging/website" -type f -print0)
  install -m 644 "$backup/website/ClassPush_Setup.exe" "$site/ClassPush_Setup.exe"
  install -m 644 "$backup/cloud-app.py" "$current/cloud/app.py"
  systemctl restart classpush-cloud-api
  printf 'Publish failed; previous website, manifest, installer and API restored from %s\n' "$backup"
}
trap rollback ERR
install -d -m 755 "$site/downloads"
install -m 644 "$package" "$site/downloads/.ClassPush_Setup_3.0.0.exe.new"
mv -f "$site/downloads/.ClassPush_Setup_3.0.0.exe.new" "$site/downloads/ClassPush_Setup_3.0.0.exe"
install -m 644 "$package" "$site/.ClassPush_Setup.exe.new"
mv -f "$site/.ClassPush_Setup.exe.new" "$site/ClassPush_Setup.exe"
while IFS= read -r -d '' file; do
  relative="${file#"$staging/website/"}"
  [ "$relative" != version.json ] || continue
  install -d -m 755 "$(dirname "$site/$relative")"
  install -m 644 "$file" "$site/$relative.classpush-new"
  mv -f "$site/$relative.classpush-new" "$site/$relative"
done < <(find "$staging/website" -type f -print0)
install -m 644 "$staging/cloud/app.py" "$current/cloud/.app.py.new"
mv -f "$current/cloud/.app.py.new" "$current/cloud/app.py"
systemctl restart classpush-cloud-api
healthy=false
for attempt in {1..20}; do
  if curl --silent --fail --max-time 2 http://127.0.0.1:8765/api/cloud/health >/dev/null; then healthy=true; break; fi
  sleep 1
done
test "$healthy" = true
systemctl is-active --quiet classpush-cloud-worker
# This is the switch seen by old clients; do not publish before the package exists.
install -m 644 "$staging/website/version.json" "$site/.version.json.new"
mv -f "$site/.version.json.new" "$site/version.json"
trap - ERR
printf 'Release 3.0.0 published; cloud accounts, credentials and worker data untouched.\nBackup: %s\n' "$backup"
