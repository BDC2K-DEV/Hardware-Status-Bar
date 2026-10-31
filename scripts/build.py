#!/usr/bin/env python3
"""Create deterministic release archives from an explicit file allowlist."""
from pathlib import Path
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
FILES = ['extension.js', 'metadata.json', 'metrics.py', 'stylesheet.css', 'thermometer-symbolic.svg']


def archive(path, entries):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as out:
        for name, data in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if name.endswith('.sh') else 0o100644) << 16
            out.writestr(info, data)


def main():
    DIST.mkdir(exist_ok=True)
    ext = DIST / 'hardware-status-bar.extension.zip'
    archive(ext, [(name, (ROOT/'extension'/name).read_bytes()) for name in FILES])
    archive(DIST/'hardware-status-bar-linux.zip', [
        ('hardware-status-bar.extension.zip', ext.read_bytes()),
        ('install.sh', (ROOT/'scripts/install.sh').read_bytes()),
        ('install.py', (ROOT/'scripts/install.py').read_bytes()),
        ('README.md', (ROOT/'README.md').read_bytes()),
        ('LICENSE', (ROOT/'LICENSE').read_bytes()),
        *[(name, (ROOT/name).read_bytes()) for name in ['CONTRIBUTING.md', 'SECURITY.md', 'CHANGELOG.md', 'docs/compatibility.md', 'docs/images/bar.png', 'docs/images/menu.png']],
    ])
    (DIST/'download.sh').write_bytes((ROOT/'scripts/download.sh').read_bytes())
    names = ['hardware-status-bar.extension.zip', 'hardware-status-bar-linux.zip', 'download.sh']
    (DIST/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256((DIST/n).read_bytes()).hexdigest()}  {n}\n' for n in names))
    print('Built release assets in dist/')

if __name__ == '__main__':
    main()
