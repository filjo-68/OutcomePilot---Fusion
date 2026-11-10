"""Adversarial release packaging checks for the Claude edition; independent of live model behaviour."""
import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

DEV = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[2]
SKILL = 'skills/outcomepilot-fusion'


def load(name):
    spec = importlib.util.spec_from_file_location(name, DEV / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = load('release_check')
builder = load('build_release')


def rehash(root):
    obj = {}
    for p in root.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.name != 'FILE_HASHES.json' and p.suffix != '.pyc':
            obj[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    (root / 'FILE_HASHES.json').write_text(json.dumps(obj, sort_keys=True, indent=2) + '\n')


class ReleaseHardening(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'pkg'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        rehash(self.root)

    # helpers -------------------------------------------------------------
    def assert_rejected(self, needle):
        rehash(self.root)
        errors = release.check(self.root)
        self.assertTrue(any(needle in e for e in errors), errors)

    def edit_text(self, rel, change):
        p = self.root / rel
        p.write_text(change(p.read_text(encoding='utf-8')), encoding='utf-8')

    def edit_json(self, rel, change):
        p = self.root / rel
        data = json.loads(p.read_text(encoding='utf-8'))
        change(data)
        p.write_text(json.dumps(data), encoding='utf-8')

    def edit_catalog_line(self, index, change):
        p = self.root / 'dev/evals/scenario_catalog.jsonl'
        lines = p.read_text(encoding='utf-8').splitlines()
        case = json.loads(lines[index])
        change(case)
        lines[index] = json.dumps(case)
        p.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    # baseline and hashes ---------------------------------------------------
    def test_static_original_passes(self):
        self.assertEqual(release.check(self.root), [])

    def test_missing_hash_manifest_rejected(self):
        (self.root / 'FILE_HASHES.json').unlink()
        self.assertTrue(any('FILE_HASHES.json' in e for e in release.check(self.root)))

    def test_tampered_file_rejected_without_rehash(self):
        (self.root / 'README.md').write_text('tampered but still parseable')
        self.assertTrue(any('FILE_HASHES mismatch' in e for e in release.check(self.root)))

    def test_unlisted_file_rejected_without_rehash(self):
        (self.root / 'extra.md').write_text('not in manifest')
        self.assertTrue(any('FILE_HASHES mismatch' in e for e in release.check(self.root)))

    # manifest ----------------------------------------------------------------
    def test_missing_claude_manifest_rejected(self):
        (self.root / '.claude-plugin/plugin.json').unlink()
        self.assertTrue(any('.claude-plugin/plugin.json' in e for e in release.check(self.root)))

    def test_malformed_manifest_json_rejected(self):
        (self.root / '.claude-plugin/plugin.json').write_text('{bad json')
        self.assert_rejected('Cannot parse JSON')

    def test_manifest_not_object_rejected_safely(self):
        (self.root / '.claude-plugin/plugin.json').write_text('[]')
        self.assert_rejected('Manifest root must be object')

    def test_manifest_name_not_slug(self):
        self.edit_json('.claude-plugin/plugin.json', lambda d: d.update(name='OutcomePilot Fusion'))
        self.assert_rejected('Manifest name must be')

    def test_manifest_version_not_semver(self):
        self.edit_json('.claude-plugin/plugin.json', lambda d: d.update(version='v2'))
        self.assert_rejected('Manifest version must be semver')

    def test_manifest_blank_description(self):
        self.edit_json('.claude-plugin/plugin.json', lambda d: d.update(description='  '))
        self.assert_rejected('Manifest description')

    def test_manifest_author_malformed_rejected_safely(self):
        self.edit_json('.claude-plugin/plugin.json', lambda d: d.update(author=None))
        self.assert_rejected('Manifest author.name')

    def test_legacy_root_manifest_rejected(self):
        (self.root / 'plugin.json').write_text('{"name": "outcomepilot-fusion"}')
        self.assert_rejected('Legacy manifest of another host')

    def test_legacy_codex_manifest_rejected(self):
        (self.root / '.codex-plugin').mkdir()
        (self.root / '.codex-plugin/plugin.json').write_text('{}')
        self.assert_rejected('Legacy manifest of another host')

    # license and icon --------------------------------------------------------
    def test_missing_license_file_rejected(self):
        (self.root / 'LICENSE').unlink()
        self.assertTrue(any('Missing required file: LICENSE' in e for e in release.check(self.root)))

    def test_manifest_without_license_rejected(self):
        self.edit_json('.claude-plugin/plugin.json', lambda d: d.pop('license'))
        self.assert_rejected('Manifest license must be')

    def test_license_text_must_match_manifest(self):
        (self.root / 'LICENSE').write_text('All rights reserved.\n')
        self.assert_rejected('LICENSE file does not match')

    def test_missing_icon_rejected(self):
        (self.root / '.claude-plugin/icon.png').unlink()
        self.assertTrue(any('icon.png' in e for e in release.check(self.root)))

    def test_icon_not_png_rejected(self):
        (self.root / '.claude-plugin/icon.png').write_bytes(b'GIF89a' + b'0' * 64)
        self.assert_rejected('Icon must be a PNG')

    def test_icon_wrong_dimensions_rejected(self):
        p = self.root / '.claude-plugin/icon.png'
        data = bytearray(p.read_bytes())
        data[16:24] = (256).to_bytes(4, 'big') + (256).to_bytes(4, 'big')
        p.write_bytes(bytes(data))
        self.assert_rejected('Icon must be square')

    def test_icon_not_square_rejected(self):
        p = self.root / '.claude-plugin/icon.png'
        data = bytearray(p.read_bytes())
        data[20:24] = (512).to_bytes(4, 'big')
        p.write_bytes(bytes(data))
        self.assert_rejected('Icon must be square')

    # skill -------------------------------------------------------------------
    def test_version_disagreement(self):
        self.edit_json('.claude-plugin/plugin.json', lambda d: d.update(version='99.99.99'))
        self.assert_rejected('Skill metadata version disagrees')

    def test_wrong_skill_frontmatter(self):
        self.edit_text(f'{SKILL}/SKILL.md', lambda t: t.replace('name: outcomepilot-fusion', 'name: rogue', 1))
        self.assert_rejected('Invalid skill front matter')

    def test_skill_without_frontmatter(self):
        self.edit_text(f'{SKILL}/SKILL.md', lambda t: t[4:])
        self.assert_rejected('Invalid skill front matter')

    def test_skill_description_too_long(self):
        self.edit_text(f'{SKILL}/SKILL.md', lambda t: t.replace('description: ', 'description: ' + 'x' * 1100 + ' ', 1))
        self.assert_rejected('Skill description exceeds')

    def test_skill_description_angle_brackets(self):
        self.edit_text(f'{SKILL}/SKILL.md', lambda t: t.replace('description: ', 'description: <task> ', 1))
        self.assert_rejected('angle brackets')

    def test_skill_description_missing(self):
        self.edit_text(f'{SKILL}/SKILL.md', lambda t: t.replace('description: ', 'summary: ', 1))
        self.assert_rejected('Skill description missing')

    def test_skill_body_too_long(self):
        self.edit_text(f'{SKILL}/SKILL.md', lambda t: t + '\n' + 'word ' * 3001)
        self.assert_rejected('Skill body exceeds')

    def test_broken_skill_reference(self):
        self.edit_text(f'{SKILL}/SKILL.md', lambda t: t + '\nMissing `references/DOES_NOT_EXIST.md`\n')
        self.assert_rejected('Broken skill reference')

    def test_orphan_reference_rejected(self):
        (self.root / SKILL / 'references/orphan.md').write_text('# never routed\n')
        self.assert_rejected('Reference not routed from SKILL.md')

    def test_foreign_host_wording_rejected(self):
        self.edit_text(f'{SKILL}/references/quickstart-bg.md', lambda t: t + '\nUse @' + 'OutcomePilot Fusion\n')
        self.assert_rejected('Wording for another host')

    # agent -------------------------------------------------------------------
    def test_missing_agent_rejected(self):
        (self.root / 'agents/outcome-verifier.md').unlink()
        self.assertTrue(any('agents/outcome-verifier.md' in e for e in release.check(self.root)))

    def test_agent_name_mismatch(self):
        self.edit_text('agents/outcome-verifier.md', lambda t: t.replace('name: outcome-verifier', 'name: Other_Agent', 1))
        self.assert_rejected('Agent name must be')

    def test_agent_bad_model(self):
        self.edit_text('agents/outcome-verifier.md', lambda t: t.replace('model: inherit', 'model: gpt', 1))
        self.assert_rejected('Agent model must be')

    def test_agent_bad_color(self):
        self.edit_text('agents/outcome-verifier.md', lambda t: t.replace('color: yellow', 'color: beige', 1))
        self.assert_rejected('Agent color')

    def test_agent_without_examples(self):
        self.edit_text('agents/outcome-verifier.md', lambda t: t.replace('<example>', '<sample>'))
        self.assert_rejected('Agent description needs')

    def test_agent_empty_prompt(self):
        self.edit_text('agents/outcome-verifier.md', lambda t: t[:t.index('\n---\n', 4) + 5])
        self.assert_rejected('Agent system prompt is empty')

    # schema ------------------------------------------------------------------
    def test_schema_relaxation_rejected(self):
        self.edit_json(f'{SKILL}/schemas/execution_record.schema.json', lambda d: d.update(additionalProperties=True))
        self.assert_rejected('Invalid/unsupported JSON schema')

    def test_missing_schema_required_list_rejected_safely(self):
        self.edit_json(f'{SKILL}/schemas/execution_record.schema.json', lambda d: d.update(required=None))
        self.assert_rejected('Schema lacks essential fields')

    # content scans -------------------------------------------------------------
    def test_secret_like_content_detected(self):
        self.edit_text('README.md', lambda t: t + '\nsk-proj-' + 'A' * 31 + '\n')
        self.assert_rejected('Potential credential leak')

    def test_anthropic_style_key_detected(self):
        self.edit_text('README.md', lambda t: t + '\nsk-ant-' + 'api03-' + 'B' * 40 + '\n')
        self.assert_rejected('Potential credential leak')

    def test_github_token_detected(self):
        self.edit_text('CHANGELOG.md', lambda t: t + '\nghp_' + 'c' * 36 + '\n')
        self.assert_rejected('Potential credential leak')

    def test_private_key_header_detected(self):
        self.edit_text('README.md', lambda t: t + '\n-----BEGIN RSA ' + 'PRIVATE KEY-----\n')
        self.assert_rejected('Potential credential leak')

    def test_invalid_python_detected(self):
        (self.root / 'dev/broken.py').write_text('def (:\n')
        self.assert_rejected('Invalid Python')

    def test_checker_rejects_symlinks(self):
        (self.root / 'bad-link').symlink_to('README.md')
        self.assertTrue(any('Symlink disallowed' in e for e in release.check(self.root)))

    # evaluation catalog ----------------------------------------------------------
    def test_bad_catalog_jsonl(self):
        self.edit_text('dev/evals/scenario_catalog.jsonl', lambda t: t + '\n{bad')
        self.assert_rejected('Invalid JSONL line')

    def test_duplicate_catalog_id(self):
        self.edit_text('dev/evals/scenario_catalog.jsonl', lambda t: t + t.splitlines()[0] + '\n')
        self.assert_rejected('Duplicate evaluation case id')

    def test_catalog_too_small(self):
        self.edit_text('dev/evals/scenario_catalog.jsonl', lambda t: t.splitlines()[0] + '\n')
        self.assert_rejected('Evaluation catalog unexpectedly short')

    def test_incomplete_catalog_case(self):
        self.edit_catalog_line(2, lambda c: c.pop('must_not'))
        self.assert_rejected('Incomplete evaluation case')

    def test_unrun_catalog_cannot_claim_success(self):
        self.edit_catalog_line(0, lambda c: c.update(status='PASSED_WITHOUT_TRACE'))
        self.assert_rejected('Fixture catalog must remain NOT_RUN')

    def test_catalog_cannot_claim_evaluated_without_trace(self):
        self.edit_catalog_line(1, lambda c: c.update(status='EVALUATED_WITH_TRACE'))
        self.assert_rejected('Fixture catalog must remain NOT_RUN')

    # archive builder -----------------------------------------------------------
    def test_archive_traversal_detected(self):
        p = Path(self.tmp.name) / 'bad.zip'
        with zipfile.ZipFile(p, 'w') as z:
            z.writestr('../target', 'bad')
        self.assertTrue(builder.audit_archive(p))

    def test_archive_duplicate_entry_detected(self):
        p = Path(self.tmp.name) / 'duplicate.zip'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('a', 'one')
                z.writestr('a', 'two')
        self.assertTrue(any('duplicate' in e for e in builder.audit_archive(p)))

    def test_reproducible_archive(self):
        a = Path(self.tmp.name) / 'a.plugin'
        b = Path(self.tmp.name) / 'b.plugin'
        builder.build(self.root, a)
        builder.build(self.root, b)
        self.assertEqual(hashlib.sha256(a.read_bytes()).digest(), hashlib.sha256(b.read_bytes()).digest())
        self.assertEqual(release.check(self.root), [])

    def test_archive_has_manifest_at_root_and_no_legacy(self):
        a = Path(self.tmp.name) / 'a.plugin'
        builder.build(self.root, a)
        with zipfile.ZipFile(a) as z:
            names = set(z.namelist())
        self.assertIn('.claude-plugin/plugin.json', names)
        self.assertIn(f'{SKILL}/SKILL.md', names)
        self.assertIn('agents/outcome-verifier.md', names)
        self.assertIn('LICENSE', names)
        self.assertIn('.claude-plugin/icon.png', names)
        self.assertNotIn('plugin.json', names)
        self.assertFalse(any('__pycache__' in n or n.endswith('.pyc') for n in names))

    def test_archive_destination_within_package_rejected(self):
        with self.assertRaises(ValueError):
            builder.build(self.root, self.root / 'plugin.zip')

    def test_builder_rejects_symlinks(self):
        (self.root / 'bad-link').symlink_to('README.md')
        with self.assertRaises(ValueError):
            builder.build(self.root, Path(self.tmp.name) / 'out.plugin')

    def test_builder_requires_claude_manifest(self):
        (self.root / '.claude-plugin/plugin.json').unlink()
        with self.assertRaises(ValueError):
            builder.build(self.root, Path(self.tmp.name) / 'out.plugin')


class FrontmatterParsing(unittest.TestCase):
    def test_plain_and_nested_values(self):
        fields = release.top_level_scalars('name: a-b\ndescription: Some text here\nmetadata:\n  version: "1.2.3"')
        self.assertEqual(fields['name'], 'a-b')
        self.assertEqual(fields['metadata']['version'], '1.2.3')

    def test_block_scalar_collected(self):
        fields = release.top_level_scalars('description: |\n  first\n\n  <example>\n  user: "x"\n  </example>\nmodel: inherit')
        self.assertIn('<example>', fields['description'])
        self.assertIn('user: "x"', fields['description'])
        self.assertEqual(fields['model'], 'inherit')

    def test_no_frontmatter(self):
        self.assertEqual(release.split_frontmatter('# title\n'), (None, '# title\n'))


if __name__ == '__main__':
    unittest.main()
