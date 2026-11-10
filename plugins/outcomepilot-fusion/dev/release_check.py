#!/usr/bin/env python3
"""Strict, offline packaging gate for the Claude edition of the plugin.

Checks structure, metadata, references, hashes and fixtures, then runs the local
unit tests. It never measures live model behaviour or the truth of any source.
Python 3.9+, standard library only.
"""
import ast
import hashlib
import json
import re
import struct
import sys
import unittest
from pathlib import Path

SLUG = 'outcomepilot-fusion'
SKILL = Path('skills') / SLUG
MANIFEST = '.claude-plugin/plugin.json'
AGENT = 'agents/outcome-verifier.md'
ICON = '.claude-plugin/icon.png'
CATALOG = 'dev/evals/scenario_catalog.jsonl'
ESSENTIAL = (MANIFEST, f'{SKILL.as_posix()}/SKILL.md',
             f'{SKILL.as_posix()}/schemas/execution_record.schema.json',
             f'{SKILL.as_posix()}/scripts/record_audit.py',
             AGENT, CATALOG, ICON, 'LICENSE', 'README.md', 'CHANGELOG.md', 'FILE_HASHES.json')
# Manifests of other hosts must not ship: two manifests drift apart.
LEGACY = ('plugin.json', '.codex-plugin')
KEBAB = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
SEMVER = re.compile(r'\d+\.\d+\.\d+')
AGENT_MODELS = frozenset(('inherit', 'sonnet', 'opus', 'haiku'))
AGENT_COLORS = frozenset(('blue', 'cyan', 'green', 'yellow', 'magenta', 'red'))
MAX_DESCRIPTION = 1024
MAX_SKILL_WORDS = 3000
MIN_CATALOG = 30
ICON_MIN, ICON_MAX, ICON_MAX_BYTES = 512, 2048, 2 * 1024 * 1024
# SPDX id in the manifest -> phrases the LICENSE file has to contain.
LICENSE_MARKERS = {'Apache-2.0': ('Apache License', 'Version 2.0, January 2004')}
# Wording that only makes sense on the host this plugin was ported from.
FOREIGN_HOST = re.compile(r'@OutcomePilot|com\.openai|\.codex-plugin|ChatGPT|\bCodex\b')
CREDENTIALS = (
    re.compile(r'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}'),
    re.compile(r'\bghp_[A-Za-z0-9]{30,}'),
    re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{10,}'),
    re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
)
TEXT_SUFFIXES = ('.md', '.json', '.yaml', '.yml', '.jsonl', '.py', '.txt')
SKIP_NAMES = ('FILE_HASHES.json', '.DS_Store')


def _load_json(path, errors):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f'Cannot parse JSON {path.name}: {exc}')
        return {}


def split_frontmatter(text):
    """Return (frontmatter, body), or (None, text) when there is no front matter."""
    if not text.startswith('---\n'):
        return None, text
    end = text.find('\n---\n', 4)
    if end == -1:
        return None, text
    return text[4:end], text[end + 5:]


def top_level_scalars(frontmatter):
    """Read `key: value` pairs at column 0 plus one level of two-space nesting.

    Deliberately small: enough to verify the fields this gate cares about without
    a YAML dependency. Block scalars (`key: |`) yield the indented lines joined.
    """
    fields, parent, block = {}, None, None
    for line in frontmatter.split('\n'):
        if block is not None:
            if line.startswith(' ') or not line.strip():
                fields[block] = (fields[block] + '\n' + line.strip()).strip('\n')
                continue
            block = None
        top = re.fullmatch(r'([A-Za-z_][\w-]*):(?: (.*))?', line)
        if top:
            key, value = top.group(1), (top.group(2) or '').strip()
            if value in ('|', '|-', '>', '>-'):
                fields[key], block, parent = '', key, None
            elif value == '':
                fields[key], parent = {}, key
            else:
                fields[key], parent = value.strip('"\''), None
            continue
        nested = re.fullmatch(r'  ([A-Za-z_][\w-]*): (.*)', line)
        if nested and parent is not None and isinstance(fields.get(parent), dict):
            fields[parent][nested.group(1)] = nested.group(2).strip().strip('"\'')
    return fields


def release_files(root):
    return [p for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts
            and p.name not in SKIP_NAMES and p.suffix != '.pyc']


def _check_manifest(root, errors):
    manifest = _load_json(root / MANIFEST, errors)
    if not isinstance(manifest, dict):
        errors.append('Manifest root must be object')
        return None
    name = manifest.get('name')
    if name != SLUG or not isinstance(name, str) or not KEBAB.fullmatch(name):
        errors.append('Manifest name must be the kebab-case plugin slug')
    version = manifest.get('version')
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        errors.append('Manifest version must be semver x.y.z')
        version = None
    description = manifest.get('description')
    if not isinstance(description, str) or not description.strip():
        errors.append('Manifest description must be nonempty string')
    author = manifest.get('author')
    if not isinstance(author, dict) or not isinstance(author.get('name'), str) or not author['name'].strip():
        errors.append('Manifest author.name must be nonempty string')
    license_id = manifest.get('license')
    if license_id not in LICENSE_MARKERS:
        errors.append('Manifest license must be a supported SPDX id')
    else:
        try:
            text = (root / 'LICENSE').read_text(encoding='utf-8')
        except (OSError, UnicodeError):
            text = ''
        if not all(marker in text for marker in LICENSE_MARKERS[license_id]):
            errors.append('LICENSE file does not match the manifest license')
    for rel in LEGACY:
        if (root / rel).exists():
            errors.append(f'Legacy manifest of another host present: {rel}')
    return version


def _check_skill(root, version, errors):
    text = (root / SKILL / 'SKILL.md').read_text(encoding='utf-8')
    frontmatter, body = split_frontmatter(text)
    if frontmatter is None:
        errors.append('Invalid skill front matter')
        return
    fields = top_level_scalars(frontmatter)
    if fields.get('name') != SLUG:
        errors.append('Invalid skill front matter')
    description = fields.get('description')
    if not isinstance(description, str) or not description.strip():
        errors.append('Skill description missing')
    else:
        if len(description) > MAX_DESCRIPTION:
            errors.append(f'Skill description exceeds {MAX_DESCRIPTION} characters')
        if '<' in description or '>' in description:
            errors.append('Skill description must not contain angle brackets')
    metadata = fields.get('metadata')
    skill_version = metadata.get('version') if isinstance(metadata, dict) else None
    if version and skill_version != version:
        errors.append('Skill metadata version disagrees with manifest')
    if len(body.split()) > MAX_SKILL_WORDS:
        errors.append(f'Skill body exceeds {MAX_SKILL_WORDS} words')
    cited = set(re.findall(r'`((?:references|schemas|scripts|examples)/[^`\n]+?\.(?:md|json|py))`', body))
    for rel in sorted(cited):
        if not (root / SKILL / rel).is_file():
            errors.append(f'Broken skill reference: {rel}')
    references = root / SKILL / 'references'
    if references.is_dir():
        for path in sorted(references.glob('*.md')):
            if f'references/{path.name}' not in cited:
                errors.append(f'Reference not routed from SKILL.md: {path.name}')


def _check_agent(root, errors):
    frontmatter, body = split_frontmatter((root / AGENT).read_text(encoding='utf-8'))
    if frontmatter is None:
        errors.append('Invalid agent front matter')
        return
    fields = top_level_scalars(frontmatter)
    name = fields.get('name')
    if not isinstance(name, str) or not KEBAB.fullmatch(name) or not 3 <= len(name) <= 50 \
            or name != Path(AGENT).stem:
        errors.append('Agent name must be kebab-case and match its file name')
    if not isinstance(fields.get('description'), str) or '<example>' not in fields['description']:
        errors.append('Agent description needs triggering conditions with an <example> block')
    if fields.get('model') not in AGENT_MODELS:
        errors.append('Agent model must be inherit, sonnet, opus or haiku')
    if fields.get('color') not in AGENT_COLORS:
        errors.append('Agent color is not an allowed value')
    if not body.strip():
        errors.append('Agent system prompt is empty')


def _check_icon(root, errors):
    data = (root / ICON).read_bytes()
    if len(data) < 24 or data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
        errors.append('Icon must be a PNG file')
        return
    width, height = struct.unpack('>II', data[16:24])
    if width != height or not ICON_MIN <= width <= ICON_MAX:
        errors.append(f'Icon must be square, {ICON_MIN} to {ICON_MAX} px on each side')
    if len(data) >= ICON_MAX_BYTES:
        errors.append('Icon must be under 2 MB')


def _check_schema(root, errors):
    schema = _load_json(root / SKILL / 'schemas/execution_record.schema.json', errors)
    if not isinstance(schema, dict) or schema.get('$schema') != 'https://json-schema.org/draft/2020-12/schema' \
            or schema.get('additionalProperties') is not False:
        errors.append('Invalid/unsupported JSON schema structure')
    if isinstance(schema, dict) and (not isinstance(schema.get('required'), list)
                                     or not {'objective', 'criteria', 'evidence', 'actions'}.issubset(schema['required'])):
        errors.append('Schema lacks essential fields')


def _check_files(root, errors):
    for p in root.rglob('*'):
        if p.is_symlink():
            errors.append(f'Symlink disallowed: {p.relative_to(root)}')
            continue
        if not p.is_file() or '__pycache__' in p.parts:
            continue
        rel = p.relative_to(root)
        if p.suffix == '.py':
            try:
                ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
            except (SyntaxError, UnicodeError) as exc:
                errors.append(f'Invalid Python: {rel}: {exc}')
        if p.suffix in TEXT_SUFFIXES:
            try:
                content = p.read_text(encoding='utf-8')
            except UnicodeError as exc:
                errors.append(f'Invalid UTF-8: {rel}: {exc}')
                continue
            if any(pattern.search(content) for pattern in CREDENTIALS):
                errors.append(f'Potential credential leak: {rel}')
            if rel.parts[0] in ('skills', 'agents') and p.suffix == '.md' and FOREIGN_HOST.search(content):
                errors.append(f'Wording for another host left in: {rel}')


def _check_hashes(root, errors):
    hashes = _load_json(root / 'FILE_HASHES.json', errors)
    actual = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in release_files(root)}
    if not isinstance(hashes, dict) or actual != hashes:
        errors.append('FILE_HASHES mismatch: modified/missing/unlisted file')


def _check_catalog(root, errors):
    seen = set()
    for lineno, line in enumerate((root / CATALOG).read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            errors.append(f'Empty evaluation catalog line {lineno}')
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f'Invalid JSONL line {lineno}')
            continue
        keys = ('id', 'mode', 'prompt', 'acceptance', 'must_not', 'domain', 'status')
        if not isinstance(case, dict) or not all(isinstance(case.get(k), str) and case[k].strip() for k in keys):
            errors.append(f'Incomplete evaluation case at line {lineno}')
            continue
        if case['id'] in seen:
            errors.append(f'Duplicate evaluation case id: {case["id"]}')
        seen.add(case['id'])
        if case['status'] != 'NOT_RUN':
            errors.append(f'Fixture catalog must remain NOT_RUN; store actual test runs separately at line {lineno}')
    if len(seen) < MIN_CATALOG:
        errors.append('Evaluation catalog unexpectedly short')


def check(root):
    errors = []
    root = Path(root)
    for rel in ESSENTIAL:
        if not (root / rel).is_file():
            errors.append(f'Missing required file: {rel}')
    if errors:
        return errors
    version = _check_manifest(root, errors)
    _check_skill(root, version, errors)
    _check_agent(root, errors)
    _check_icon(root, errors)
    _check_schema(root, errors)
    _check_files(root, errors)
    _check_hashes(root, errors)
    _check_catalog(root, errors)
    return sorted(set(errors))


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    errors = check(root)
    if errors:
        for error in errors:
            print('FAIL', error)
        return 1
    print('STATIC_OK: manifest / license / icon / skill / agent / hashes / schema / references / catalog checked; NOT live model truth')
    suite = unittest.defaultTestLoader.discover(str(root / 'dev' / 'tests'), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        return 1
    print(f'OFFLINE_TESTED: {result.testsRun} local tests passed; real task accuracy still unmeasured')
    return 0


if __name__ == '__main__':
    sys.exit(main())
