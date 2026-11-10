#!/usr/bin/env python3
"""Reproducible release builder for the Claude .plugin archive.

Refreshes FILE_HASHES.json, writes a deterministic ZIP and audits it: rejects
symlinks, path traversal and duplicate entries. No network access. Writes only
the hash manifest inside the plugin root and the archive at the chosen path.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

ESSENTIAL = ('.claude-plugin/plugin.json', 'skills/outcomepilot-fusion/SKILL.md')
DEFAULT_ARCHIVE = 'outcomepilot-fusion.plugin'
SKIP_NAMES = ('.DS_Store',)


def release_files(root):
    result = []
    for p in root.rglob('*'):
        if p.is_symlink():
            raise ValueError(f'Symlink not permitted: {p}')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and p.name not in SKIP_NAMES:
            result.append(p)
    return sorted(result, key=lambda p: p.relative_to(root).as_posix())


def audit_archive(path):
    errors = []
    with zipfile.ZipFile(path) as z:
        seen = set()
        for inf in z.infolist():
            n = inf.filename
            parts = PurePosixPath(n).parts
            if n in seen:
                errors.append(f'duplicate: {n}')
            seen.add(n)
            if not parts or n.startswith(('/', '\\')) or '\\' in n or '..' in parts or '.' in parts or ':' in parts[0]:
                errors.append(f'unsafe path: {n}')
            if stat.S_IFMT(inf.external_attr >> 16) == stat.S_IFLNK:
                errors.append(f'symlink: {n}')
        bad_crc = z.testzip()
        if bad_crc:
            errors.append(f'CRC: {bad_crc}')
    return errors


def build(root, out):
    root = Path(root).resolve()
    out = Path(out).resolve()
    if out.is_relative_to(root):
        raise ValueError('Archive destination must be OUTSIDE plugin root')
    files = release_files(root)
    names = [p.relative_to(root).as_posix() for p in files]
    if any(name not in names for name in ESSENTIAL):
        raise ValueError('Missing essential plugin file')
    hashes = {name: hashlib.sha256(p.read_bytes()).hexdigest()
              for name, p in zip(names, files) if name != 'FILE_HASHES.json'}
    (root / 'FILE_HASHES.json').write_text(json.dumps(hashes, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in release_files(root):
            name = p.relative_to(root).as_posix()
            inf = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            inf.compress_type = zipfile.ZIP_DEFLATED
            inf.external_attr = (0o100644 << 16)
            z.writestr(inf, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    err = audit_archive(out)
    if err:
        raise ValueError('; '.join(err))
    return {'files': len(release_files(root)), 'archive': str(out), 'sha256': hashlib.sha256(out.read_bytes()).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root', nargs='?', default='.')
    ap.add_argument('out', nargs='?')
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out = Path(args.out).resolve() if args.out else root.parent / DEFAULT_ARCHIVE
    print(json.dumps(build(root, out), indent=2))


if __name__ == '__main__':
    main()
