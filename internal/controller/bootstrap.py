"""Materialize and run only the controller embedded in this AllSet executable."""

import base64
import fcntl
import hashlib
import io
import os
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
import zipfile


def private_directory(path):
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError("Runtime cache paths cannot contain symlinks")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("Runtime cache must be a private directory owned by this user")


def materialize(encoded):
    payload = base64.b64decode(encoded, validate=True)
    revision = hashlib.sha256(payload).hexdigest()
    cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    if not cache.is_absolute():
        raise ValueError("Runtime cache location must be absolute")
    root = cache / "allset" / "controller"
    private_directory(root)
    archive = zipfile.ZipFile(io.BytesIO(payload))
    contents = {}
    for entry in archive.infolist():
        name = entry.filename
        if Path(name).name != name or name in contents or entry.is_dir():
            raise ValueError("Invalid embedded controller asset")
        contents[name] = archive.read(entry)
    target = root / revision
    descriptor = os.open(root / "install.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not target.exists() and not target.is_symlink():
            temporary = Path(tempfile.mkdtemp(prefix=".install-", dir=root))
            try:
                for name, data in contents.items():
                    with (temporary / name).open("xb") as output:
                        os.chmod(output.name, 0o600)
                        output.write(data)
                temporary.rename(target)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
        private_directory(target)
        if set(p.name for p in target.iterdir()) != set(contents):
            raise ValueError("Bundled controller cache has unexpected files; existing files were left untouched")
        for name, data in contents.items():
            file = target / name
            info = file.lstat()
            if file.is_symlink() or not file.is_file() or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError("Bundled controller cache contains an unsafe file")
            if file.read_bytes() != data:
                raise ValueError("Bundled controller cache was modified; existing files were left untouched")
    return target


def main():
    if sys.version_info < (3, 11):
        raise ValueError("Python 3.11+ is required by the bundled Box runtime")
    state, box, herdr, *command = sys.argv[1:]
    if not Path(state).is_absolute():
        raise ValueError("Project state location must be absolute")
    # Never allow inherited environment variables to override the Go plan's
    # project state or native executables.
    os.environ.update(_ALLSET_STATE_ROOT=state, _ALLSET_BOX_BIN=box, _ALLSET_HERDR_BIN=herdr)
    directory = materialize(_ARCHIVE)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(directory))
    if command[0] == "-c":
        script = command[1]
        sys.argv = ["allset-runtime", str(directory), *command[3:]]
        exec(compile(script, "<allset-bridge>", "exec"), {"__name__": "__main__"})
    else:
        name = Path(command[0]).name
        if name not in ("projects.py", "project_shell.py"):
            raise ValueError("Unsupported bundled controller entry point")
        sys.argv = [str(directory / name), *command[1:]]
        runpy.run_path(str(directory / name), run_name="__main__")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as error:
        print("allset:", str(error), file=sys.stderr)
        raise SystemExit(1)
