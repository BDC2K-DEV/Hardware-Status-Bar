#!/usr/bin/env python3
"""Install or remove the packaged GNOME extension for the current user."""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

UUID = 'hardware-bar@creator.local'
FILES = {'extension.js', 'metadata.json', 'metrics.py', 'stylesheet.css', 'thermometer-symbolic.svg'}


def run(*args):
    return subprocess.run(args, text=True, capture_output=True, check=True).stdout.strip()


def supported(version):
    match = re.search(r'(\d+)\.', version)
    return bool(match and match.group(1) == '50')


def validate_archive(path):
    with zipfile.ZipFile(path) as archive:
        if set(archive.namelist()) != FILES or len(archive.namelist()) != len(FILES):
            raise ValueError('Unexpected extension archive contents.')
        metadata = json.loads(archive.read('metadata.json'))
        if metadata.get('uuid') != UUID or metadata.get('shell-version') != ['50']:
            raise ValueError('Unexpected extension identity or compatibility.')
        if sum(info.file_size for info in archive.infolist()) > 2_000_000:
            raise ValueError('Extension archive is unexpectedly large.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--check', action='store_true', help='Check compatibility without installing')
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise RuntimeError('This release requires Linux with GNOME Shell 50.')
    if os.geteuid() == 0:
        raise RuntimeError('Run this as your desktop user, without sudo.')
    for program in ('gnome-shell', 'gnome-extensions', 'gsettings'):
        if not shutil.which(program):
            raise RuntimeError(f'Missing {program}. This release requires the GNOME desktop.')
    version = run('gnome-shell', '--version')
    if not args.uninstall and not supported(version):
        raise RuntimeError(f'{version} is not supported by this release. GNOME Shell 50 is required.')
    if not Path('/usr/bin/python3').exists() or not hasattr(os, 'pidfd_open'):
        raise RuntimeError('Python 3.9+ with Linux pidfd support is required.')
    # Check the session before changing any files.
    enabled = ast.literal_eval(run('gsettings', 'get', 'org.gnome.shell', 'enabled-extensions').removeprefix('@as '))
    base = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    target = base / 'gnome-shell/extensions' / UUID
    if args.check:
        print(f'Compatible: {version}. Installation location: {target}')
        return
    if args.uninstall:
        subprocess.run(['gnome-extensions', 'disable', UUID], capture_output=True)
        run('gsettings', 'set', 'org.gnome.shell', 'enabled-extensions', repr([x for x in enabled if x != UUID]))
        if target.is_symlink():
            raise RuntimeError('Refusing to remove a symlink; inspect the installation manually.')
        if target.exists():
            if json.loads((target / 'metadata.json').read_text()).get('uuid') != UUID:
                raise RuntimeError('Extension identity mismatch; nothing removed.')
            shutil.rmtree(target)
        print('Hardware Status Bar removed. A session restart may be needed to unload it fully.')
        return
    archive = Path(__file__).resolve().parent / 'hardware-status-bar.extension.zip'
    validate_archive(archive)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        raise RuntimeError('Hardware Status Bar is already installed. Uninstall it first, then install this release.')
    with tempfile.TemporaryDirectory(dir=target.parent, prefix='.hardware-bar-') as staging:
        with zipfile.ZipFile(archive) as package:
            package.extractall(staging)  # exact allowlisted, flat paths validated above
        shutil.copytree(staging, target)
    try:
        run('gsettings', 'set', 'org.gnome.shell', 'enabled-extensions', repr(enabled + [UUID] if UUID not in enabled else enabled))
    except Exception:
        shutil.rmtree(target)
        raise
    subprocess.run(['gnome-extensions', 'enable', UUID], capture_output=True)
    print('Installed and enabled for future logins. Save your work, then log out and back in once.')
    print('Click the bar for applications. Kill closes the app immediately and loses unsaved work.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print(f'Setup: {exc}', file=sys.stderr)
        sys.exit(1)
