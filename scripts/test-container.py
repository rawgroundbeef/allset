#!/usr/bin/env python3
"""Test a release archive in a disposable, offline container with synthetic state."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python3 scripts/test-container.py RELEASE_ARCHIVE')
    archive = Path(sys.argv[1]).resolve(strict=True)
    root = Path(__file__).resolve().parent / 'container'
    tag = 'allset-packaging-test:' + uuid.uuid4().hex
    container = 'allset-packaging-test-' + uuid.uuid4().hex
    try:
        with tempfile.TemporaryDirectory(prefix='allset-container-') as directory:
            context = Path(directory)
            # Explicit allowlist: no repository tree, home, credentials or socket.
            shutil.copyfile(archive, context / 'allset.tar.gz')
            for name in ('Dockerfile', 'smoke.py', 'transport.py'):
                shutil.copyfile(root / name, context / name)
            subprocess.run(['docker', 'build', '--tag', tag, str(context)], check=True)
        subprocess.run(['docker', 'run', '--name', container, '--rm', '--network', 'none', '--cap-drop', 'ALL',
                        '--security-opt', 'no-new-privileges', '--pids-limit', '128',
                        '--memory', '512m', '--cpus', '2', tag], check=True, timeout=180)
    finally:
        subprocess.run(['docker', 'rm', '--force', container], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)
        subprocess.run(['docker', 'image', 'rm', tag], stdout=subprocess.DEVNULL, check=False)


if __name__ == '__main__':
    main()
