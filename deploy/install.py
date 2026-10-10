"""Root-only Linux installer. Never prints environment values or credentials."""
import base64
import datetime
import json
import os
import pwd
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path('/opt/classpush-cloud')
SITE = Path('/www/wwwroot/classpush.eliauk312.top')
NGINX_CONFIG = Path('/www/server/panel/vhost/nginx/classpush.eliauk312.top.conf')
NGINX = '/www/server/nginx/sbin/nginx'


def run(*args):
    subprocess.run(args, check=True)


def configure_secret_file():
    target = Path('/etc/classpush-cloud.env')
    if target.exists():
        os.chmod(target, 0o600)
        return
    # Only the school AppToken is migrated. Personal account/password are not copied.
    legacy = Path('/root/classpush.env')
    values = {}
    if legacy.exists():
        for line in legacy.read_text().splitlines():
            key, separator, value = line.partition('=')
            if separator:
                values[key.strip().removeprefix('export ')] = value.strip().strip('\"\'')
    private_token = Path('/root/classpush-hnit-token.txt')
    token = (private_token.read_text(encoding='utf-8-sig').strip() if private_token.exists()
             else values.get('CP_APP_TOKEN', values.get('WXPUSHER_APP_TOKEN', '')))
    if not re.fullmatch(r'AT_[A-Za-z0-9]+', token):
        raise RuntimeError('Existing HNIT token missing; configure server environment privately')
    content = ('CLOUD_ORIGIN=https://classpush.eliauk312.top\n'
               'CLOUD_DATA_DIR=/var/lib/classpush-cloud\n'
               'CLOUD_DATA_KEY=' + base64.b64encode(secrets.token_bytes(32)).decode() + '\n'
               'WXPUSHER_APP_TOKEN=' + token + '\n')
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(content)
    if private_token.exists():
        private_token.unlink()


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Run as root')
    os.umask(0o077)
    release = Path(__file__).resolve().parents[1]
    if release.parent != BASE / 'releases':
        raise RuntimeError('Release must be inside /opt/classpush-cloud/releases')
    os.chdir(release)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = BASE / 'backups' / stamp
    backup.mkdir(parents=True)
    shutil.copy2(NGINX_CONFIG, backup / 'nginx.conf')
    # Keep public website backups outside the public root. No user database backups here.
    shutil.copytree(SITE, backup / 'website')
    try:
        account = pwd.getpwnam('classpush')
    except KeyError:
        run('useradd', '--system', '--home', '/var/lib/classpush-cloud', '--shell', '/usr/sbin/nologin', 'classpush')
        account = pwd.getpwnam('classpush')
    data = Path('/var/lib/classpush-cloud')
    data.mkdir(exist_ok=True)
    os.chmod(data, 0o700)
    os.chown(data, account.pw_uid, account.pw_gid)
    # Code/static files must be readable by the unprivileged service / web server.
    for folder, dirs, files in os.walk(release):
        os.chmod(folder, 0o755)
        for filename in files:
            os.chmod(Path(folder) / filename, 0o644)
    os.chmod(BASE, 0o755)
    os.chmod(BASE / 'releases', 0o755)
    venv = BASE / 'venv'
    if not venv.exists():
        run('python3', '-m', 'venv', str(venv))
    run(str(venv / 'bin/pip'), 'install', '-r', str(release / 'cloud/requirements.txt'))
    # pip inherits restrictive umask, so give the service read/execute access to libraries.
    run('chmod', '-R', 'a+rX', str(venv))
    configure_secret_file()
    run(str(venv / 'bin/python'), '-m', 'unittest', 'discover', '-s', str(release / 'cloud/tests'), '-v')
    current = BASE / 'current'
    previous = str(current.resolve()) if current.exists() else None
    if current.is_symlink():
        current.unlink()
    elif current.exists():
        raise RuntimeError('current is not a symlink')
    current.symlink_to(release, target_is_directory=True)
    for name in ('classpush-cloud-api', 'classpush-cloud-worker'):
        shutil.copy2(release / ('deploy/' + name + '.service'), '/etc/systemd/system/' + name + '.service')
    run('systemctl', 'daemon-reload')
    run('systemctl', 'enable', '--now', 'classpush-cloud-api', 'classpush-cloud-worker')
    run('systemctl', 'restart', 'classpush-cloud-api', 'classpush-cloud-worker')
    for attempt in range(30):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8765/api/cloud/health', timeout=2) as response:
                if response.status == 200:
                    break
        except (OSError, ValueError):
            pass
        time.sleep(1)
    else:
        run('systemctl', 'stop', 'classpush-cloud-api', 'classpush-cloud-worker')
        raise RuntimeError('Cloud API health check failed; public website was not changed')
    run('systemctl', 'is-active', '--quiet', 'classpush-cloud-worker')
    # The HTTPS configuration already exists. Add only one include directive.
    snippet = Path('/www/server/panel/vhost/nginx/classpush-cloud.inc')
    shutil.copy2(release / 'deploy/nginx-cloud.conf', snippet)
    os.chmod(snippet, 0o644)
    original = NGINX_CONFIG.read_text()
    include = '    include ' + str(snippet) + ';\n'
    try:
        if include.strip() not in original:
            position = original.rfind('}')
            NGINX_CONFIG.write_text(original[:position] + include + original[position:])
        run(NGINX, '-t')
        run(NGINX, '-s', 'reload')
    except Exception:
        shutil.copy2(backup / 'nginx.conf', NGINX_CONFIG)
        run('systemctl', 'stop', 'classpush-cloud-api', 'classpush-cloud-worker')
        if previous:
            current.unlink()
            current.symlink_to(previous, target_is_directory=True)
        raise
    # Publish new management routes, but not the homepage, download package or version manifest.
    for name in ('cloud.html', 'cloud.css', 'cloud.js', 'privacy.html', 'calendar.html'):
        target = SITE / name
        shutil.copy2(release / 'website' / name, target)
        os.chmod(target, 0o644)
    print('Cloud services installed; existing homepage/download/version preserved.')


if __name__ == '__main__':
    main()
