import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('dynamic_inventory', HERE / 'dynamic.py')
dynamic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dynamic)
MAPPER = dynamic.load_budget().load_mapper()


def scan(text, extra=None):
    sources = {'app.py': text.encode('utf-8')}
    sources.update(extra or {})
    return dynamic.inspect_sources(sources, MAPPER)


class DynamicTests(unittest.TestCase):
    def test_execution_trap_and_manifest(self):
        result = dynamic.analyze(HERE / 'examples')
        self.assertEqual(result['summary'], {'call_sites': 3, 'parse_issues': 0, 'local_candidates': 1})
        self.assertEqual(result['calls'][0]['local_paths'], ['plugin.py'])
        entry = result['inventory']['manifest'][0]
        self.assertEqual(entry['sha256'], hashlib.sha256((HERE / 'examples' / entry['path']).read_bytes()).hexdigest())

    def test_alias_forms_and_relative_import_not_alias(self):
        result = scan('import importlib as il\nfrom importlib import import_module as load\n'
                      'import builtins as bi\nfrom builtins import __import__ as imp\n'
                      'from .importlib import import_module as other\n'
                      'il.import_module("a"); load("a"); bi.__import__("a"); imp("a"); other("a")',
                      {'a.py': b''})
        self.assertEqual(len(result['calls']), 4)
        self.assertTrue(all(c['classification'] == 'local_source_candidate' for c in result['calls']))
        self.assertEqual(len(result['alias_evidence']), 4)

    def test_relative_literal_package(self):
        calls = scan('importlib.import_module("..plugin", "pkg.sub")\n'
                     'importlib.import_module(".plugin", package="pkg")',
                     {'pkg/plugin.py': b''})['calls']
        self.assertEqual([c['target_candidate'] for c in calls], ['pkg.plugin', 'pkg.plugin'])
        self.assertTrue(all(c['local_paths'] == ['pkg/plugin.py'] for c in calls))

    def test_relative_context_never_guessed(self):
        calls = scan('importlib.import_module(".x")\n'
                     'importlib.import_module(".x", __package__)\n'
                     '__import__("x", level=1)\n__import__("x", level=chosen)\n'
                     'importlib.import_module("...x", "pkg")')['calls']
        self.assertEqual([c['classification'] for c in calls], ['relative_context_unknown',
                         'relative_context_unknown', 'relative_or_unknown_level',
                         'relative_or_unknown_level', 'invalid_relative_name'])
        self.assertTrue(all(c['target_candidate'] is None for c in calls))

    def test_computed_unpacking_and_conflicts(self):
        calls = scan('__import__(prefix + "x")\n__import__(*args)\n'
                     '__import__("x", **options)\n__import__("x", name="y")\n'
                     'importlib.import_module(f"{prefix}.x")')['calls']
        self.assertTrue(all(c['classification'] == 'computed_or_unbound_arguments' for c in calls))

    def test_keyword_and_invalid_literals(self):
        calls = scan('__import__(name="a")\n__import__(123)\n__import__()\n'
                     '__import__("")\n__import__(".a")\n__import__("a", level=False)',
                     {'a.py': b''})['calls']
        self.assertEqual(calls[0]['classification'], 'local_source_candidate')
        self.assertEqual([c['classification'] for c in calls[1:]],
                         ['invalid_or_missing_literal_name'] * 3 +
                         ['invalid_absolute_name', 'relative_or_unknown_level'])

    def test_scope_shadowing_explicitly_unverified(self):
        result = scan('def f(load):\n load("a")\n'
                      'if False:\n from importlib import import_module as load\n'
                      'load = print\nload("a")', {'a.py': b''})
        self.assertEqual(len(result['calls']), 2)
        self.assertTrue(all(c['binding_verified'] is False for c in result['calls']))
        self.assertIn('file-wide', dynamic.SCOPE)

    def test_ambiguous_alias_does_not_choose_api(self):
        call = scan('from importlib import import_module as load\n'
                    'from builtins import __import__ as load\nload("a")')['calls'][0]
        self.assertEqual(call['classification'], 'ambiguous_api_alias')
        self.assertIsNone(call['target_candidate'])

    def test_collision_and_missing_sources(self):
        calls = scan('__import__("a")\n__import__("missing")',
                     {'a.py': b'', 'a/__init__.py': b''})['calls']
        self.assertEqual(calls[0]['classification'], 'ambiguous_local_sources')
        self.assertEqual(calls[0]['local_paths'], ['a.py', 'a/__init__.py'])
        self.assertEqual(calls[1]['classification'], 'nonlocal_or_missing')

    def test_encodings_parse_errors_and_determinism(self):
        sources = {'z.py': b'\x00', 'bom.py': b'\xef\xbb\xbf__import__("x")',
                   'latin.py': b'# coding: latin-1\n__import__("caf\xe9")',
                   'bad.py': b'if :\n'}
        a = dynamic.inspect_sources(sources, MAPPER)
        b = dynamic.inspect_sources(dict(reversed(list(sources.items()))), MAPPER)
        self.assertEqual(a, b)
        self.assertEqual(a['summary']['parse_issues'], 2)
        self.assertEqual([c['target_candidate'] for c in a['calls']], ['x', 'caf\xe9'])

    def test_budget_refuses_before_partial_inventory(self):
        limits = dict(dynamic.load_budget().DEFAULTS, files=1)
        with self.assertRaises(ValueError):
            dynamic.analyze(HERE / 'examples', limits)

    def test_strings_comments_and_wrappers_are_not_calls(self):
        result = scan('# __import__("a")\n'
                      '''text = '__import__("a")'\n'''
                      'getattr(importlib, "import_module")("a")\n'
                      'my_loader("a")\n')
        self.assertEqual(result['calls'], [])

    def test_cli_exit_contract(self):
        base = [sys.executable, '-B', str(HERE / 'dynamic.py'), str(HERE / 'examples'), '--json']
        normal = subprocess.run(base, capture_output=True, text=True)
        strict = subprocess.run(base + ['--strict'], capture_output=True, text=True)
        refused = subprocess.run(base + ['--max-files', '1'], capture_output=True, text=True)
        self.assertEqual((normal.returncode, strict.returncode, refused.returncode), (0, 1, 2))
        self.assertIn('"status": "refused"', refused.stdout)
        self.assertNotIn('"calls"', refused.stdout)


if __name__ == '__main__':
    unittest.main()
