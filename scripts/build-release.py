#!/usr/bin/env python3
"""Build native release archives without fetching credentials or publishing."""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python3 scripts/build-release.py OUTPUT_DIRECTORY')
    root = Path(__file__).resolve().parent.parent
    version = subprocess.check_output(
        ['go', 'run', './cmd/allset', '--version'], cwd=root, text=True
    ).strip().removeprefix('allset ')
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-z0-9.]+)?', version):
        raise SystemExit('CLI returned an invalid release version')
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    checksums = []
    with tempfile.TemporaryDirectory(prefix='allset-build-') as directory:
        binary = Path(directory) / 'allset'
        for system in ('darwin', 'linux'):
            for architecture in ('amd64', 'arm64'):
                subprocess.run(
                    ['go', 'build', '-trimpath', '-buildvcs=false', '-o', str(binary), './cmd/allset'],
                    cwd=root, env={**os.environ, 'GOOS': system, 'GOARCH': architecture, 'CGO_ENABLED': '0'},
                    check=True,
                )
                archive = output / f'allset_{version}_{system}_{architecture}.tar.gz'
                with tarfile.open(archive, 'w:gz') as bundle:
                    bundle.add(binary, arcname='allset')
                    for name in ('LICENSE', 'README.md'):
                        bundle.add(root / name, arcname=name)
                checksums.append(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name)
    (output / 'SHA256SUMS').write_text('\n'.join(checksums) + '\n')
    print(f'Built {len(checksums)} archives for AllSet {version} in {output}')


if __name__ == '__main__':
    main()
