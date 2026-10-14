"""Bounded, read-only discovery of removable drives and common ROS data folders."""
import hashlib
import os
import sys
from pathlib import Path


def has_data(root, max_depth=5, max_dirs=1500):
    count = 0
    try:
        for folder, dirs, files in os.walk(root, followlinks=False):
            count += 1
            if count > max_dirs:
                break
            p = Path(folder)
            dirs[:] = [d for d in dirs if not d.startswith(('.', '$', 'FOUND.'))
                       and d not in {'System Volume Information', 'node_modules', 'build', 'install', 'log'}
                       and not (p/d).is_symlink()]
            if len(p.relative_to(root).parts) >= max_depth:
                dirs[:] = []
            if any(n == 'metadata.yaml' or (not n.startswith('.') and Path(n).suffix.lower() in {'.pgm', '.mcap', '.db3', '.bag', '.simplemap'}) for n in files):
                return True
    except OSError:
        pass
    return False


def mounted_roots():
    roots = []
    if sys.platform == 'darwin':
        bases = [Path('/Volumes')]
    else:
        bases = [Path('/media'), Path('/run/media'), Path('/mnt')]
    for base in bases:
        if not base.is_dir():
            continue
        try:
            children = list(base.iterdir())
            for p in children:
                if p.is_symlink() or not p.is_dir() or p.name.startswith('.'):
                    continue
                if os.path.ismount(p):
                    roots.append(p)
                else:
                    for child in p.iterdir():
                        if child.is_dir() and not child.is_symlink() and os.path.ismount(child):
                            roots.append(child)
        except OSError:
            continue
    return roots


def discover(home=None, mounts=None):
    home = Path.home() if home is None else Path(home)
    candidates = list(mounted_roots() if mounts is None else mounts)
    candidates += [
    home/'ros2_ws'/'rosbag',
    home/'ros2_ws'/'bags',
    home/'ros2_ws'/'maps',
    home/'ros2_ws'/'src'/'oit_deliverybot_02'/'maps',
    Path('/home/oit/ros2_ws/src/oit_deliverybot_02/maps'),
    home/'rosbag',
    home/'rosbag2',
    home/'maps',
    ]
    sources = []
    for candidate in candidates:
        p = Path(candidate)
        if p.is_symlink() or not p.is_dir():
            continue
        p = p.resolve()
        if any(p == Path(s['path']) or Path(s['path']) in p.parents for s in sources):
            continue
        if has_data(p):
            sources.append({'id':'auto-'+hashlib.sha256(str(p).encode()).hexdigest()[:12],
                            'name':p.name, 'path':str(p), 'writable':False})
    return sources
