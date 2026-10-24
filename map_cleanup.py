"""Find timestamped map packages left behind by file-only deletion."""
from pathlib import Path
import hashlib
import os
import stat
from discovery import is_pgm, is_timestamp_package


def orphan_snapshot(folder):
    """Return a fingerprint and size; refuse PGM, bags, links and unreadable trees."""
    rows, size = [], 0
    def onerror(error):
        raise error
    for directory, dirs, files in os.walk(folder, followlinks=False, onerror=onerror):
        for path in [Path(directory), *(Path(directory)/n for n in sorted(files + dirs))]:
            info = path.lstat()
            if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
                raise ValueError('Links or special files in map folder')
            if not stat.S_ISDIR(info.st_mode):
                if is_pgm(path) or path.suffix.lower() in {'.bag', '.mcap', '.db3'} or path.name == 'metadata.yaml':
                    raise ValueError('Map or rosbag data still exists')
                size += info.st_size
            rows.append((str(path.relative_to(folder)), info.st_mode, info.st_dev, info.st_ino,
                         info.st_size, info.st_mtime_ns, info.st_ctime_ns))
    if not rows:
        raise ValueError('Folder no longer exists')
    return hashlib.sha256(repr(sorted(rows)).encode()).hexdigest(), size


def find_orphans(root):
    root = Path(root)
    result = []
    def onerror(error):
        raise error
    for directory, dirs, _ in os.walk(root, followlinks=False, onerror=onerror):
        dirs[:] = sorted(n for n in dirs if not n.startswith(('.', '$', 'FOUND.'))
                         and not (Path(directory)/n).is_symlink())
        path = Path(directory)
        if is_timestamp_package(path, root):
            # A timestamp folder is a package boundary, not a classification folder.
            dirs[:] = []
            try:
                fingerprint, size = orphan_snapshot(path)
            except (OSError, ValueError):
                continue
            result.append(dict(path=str(path.relative_to(root)), bytes=size, fingerprint=fingerprint))
    return result
