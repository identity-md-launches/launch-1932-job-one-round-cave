import csv
import io
from pathlib import Path
import tempfile
import unittest
import order_csv as tool


class ReadingOrderCSV(unittest.TestCase):
    def setUp(self):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir='test/scratch')
        self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def put(self, name, text):
        path = self.root / name
        path.write_text(text)
        return path
    def test_dependency_direction_and_exact_hashes(self):
        self.put('app.py', 'import leaf\nraise RuntimeError("never run")\n')
        self.put('leaf.py', '')
        text, evidence = tool.snapshot(self.root)
        rows = {r['module']: r for r in csv.DictReader(io.StringIO(text))}
        self.assertEqual(rows['leaf']['wave'], '1')
        self.assertEqual(rows['app']['wave'], '2')
        import hashlib
        self.assertEqual(rows['app']['source_sha256'], hashlib.sha256((self.root/'app.py').read_bytes()).hexdigest())
        self.assertEqual(evidence['summary']['selected_module_count'], 2)
    def test_changed_dependency_and_content_are_reviewable(self):
        self.put('app.py', 'import leaf\n')
        self.put('leaf.py', '')
        before, _ = tool.snapshot(self.root)
        self.put('app.py', '')
        after, _ = tool.snapshot(self.root)
        a = self.put('before.csv', before)
        b = self.put('after.csv', after)
        report = tool.compare(a,b)
        self.assertFalse(report['equal'])
        self.assertTrue(tool.compare(a,a)['equal'])
    def test_cycles_and_selection(self):
        self.put('a.py', 'import b\n')
        self.put('b.py', 'import a\n')
        self.put('spare.py', '')
        text, evidence = tool.snapshot(self.root, ['a'])
        rows = list(csv.DictReader(io.StringIO(text)))
        self.assertEqual(len(rows), 2)
        self.assertEqual({r['cyclic'] for r in rows}, {'true'})
        self.assertEqual({r['group'] for r in rows}, {'a'})
        self.assertTrue(evidence['cycles'])
    def test_bad_keys_and_columns_refused(self):
        empty = self.put('empty.csv', ','.join(tool.COLUMNS)+'\n')
        self.assertTrue(tool.compare(empty, empty)['equal'])
        bad = self.put('bad.csv', 'wrong\n')
        with self.assertRaises(ValueError): tool.compare(empty,bad)
        duplicate = self.put('duplicate.csv', ','.join(tool.COLUMNS)+'\na,p,a,1,false,[],hash\na,p,a,1,false,[],hash\n')
        with self.assertRaises(ValueError): tool.compare(empty,duplicate)
    def test_refusal_and_empty_plan(self):
        text, _ = tool.snapshot(self.root)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(text)))),0)
        with self.assertRaises(ValueError): tool.snapshot(self.root,['missing'])
        self.put('a.py', 'import b\n')
        with self.assertRaises((ValueError,RuntimeError)): tool.snapshot(self.root,limits={'files':0})

if __name__ == '__main__': unittest.main()
