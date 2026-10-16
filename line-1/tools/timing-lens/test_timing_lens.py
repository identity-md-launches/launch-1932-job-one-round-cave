import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('timing_lens', ROOT / 'timing_lens.py')
lens = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lens)


def fixture():
    return {'schema': 'endpoint-sentry/v1', 'ok': True, 'elapsed_ms': 100,
            'hops': [{'headers_ms': 30}, {'headers_ms': 20}],
            'checks': [{'name': 'status', 'ok': True}]}


def item(result, name):
    return next(t for t in result['timings'] if t['name'] == name)


class TimingTests(unittest.TestCase):
    def test_inclusive_budget(self):
        self.assertEqual(lens.analyze(fixture(), 100)['outcome'], 'within-budget')
        self.assertEqual(lens.analyze(fixture(), 99.999)['outcome'], 'over-budget')

    def test_remainder_is_not_body(self):
        result = lens.analyze(fixture(), 100)
        self.assertEqual(item(result, 'unattributed_remainder')['ms'], 50)
        self.assertNotIn('body_time', str(result))
        self.assertTrue(result['breakdown_complete'])

    def test_wrapper_and_provenance(self):
        value = {'schema': 'deadline-sentry/v1', 'ok': True,
                 'elapsed_ms': 125, 'probe': fixture()}
        result = lens.analyze(value, 100)
        self.assertEqual(item(result, 'wrapper_overhead')['ms'], 25)
        self.assertEqual(item(result, 'probe_total')['evidence'], ['/probe/elapsed_ms'])
        self.assertEqual(item(result, 'connect_through_headers')['evidence'], ['/probe/hops/0/headers_ms'])

    def test_no_probe_is_not_a_latency(self):
        value = {'schema': 'deadline-sentry/v1', 'ok': False,
                 'elapsed_ms': 200, 'error': {'kind': 'deadline'}}
        self.assertEqual(lens.analyze(value, 300)['outcome'], 'unobserved')

    def test_failed_but_fast(self):
        value = fixture()
        value.update(ok=False, error={'kind': 'body'})
        result = lens.analyze(value, 100)
        self.assertFalse(result['source_ok'])
        self.assertEqual(result['outcome'], 'within-budget')

    def test_missing_total_unknown(self):
        value = fixture()
        del value['elapsed_ms']
        result = lens.analyze(value, 100)
        self.assertEqual(result['outcome'], 'unknown')
        self.assertNotIn('unattributed_remainder', [t['name'] for t in result['timings']])

    def test_missing_interval_not_zero(self):
        value = fixture()
        del value['hops'][0]['headers_ms']
        result = lens.analyze(value, 100)
        self.assertFalse(result['breakdown_complete'])
        self.assertNotIn('unattributed_remainder', [t['name'] for t in result['timings']])

    def test_no_headers_with_connection_failure(self):
        value = fixture()
        value.update(ok=False, error={'kind': 'connect'}, hops=[])
        self.assertEqual(item(lens.analyze(value, 100), 'unattributed_remainder')['ms'], 100)

    def test_bad_numbers(self):
        for number in (True, '1', -1, float('inf'), float('nan'), 86400001):
            with self.subTest(number=number), self.assertRaises(ValueError):
                lens.analyze(fixture(), number)
            value = fixture()
            value['hops'][0]['headers_ms'] = number
            with self.assertRaises(ValueError):
                lens.analyze(value, 100)

    def test_inconsistent_totals(self):
        value = fixture()
        value['elapsed_ms'] = 40
        with self.assertRaises(ValueError):
            lens.analyze(value, 100)
        with self.assertRaises(ValueError):
            lens.analyze({'schema': 'deadline-sentry/v1', 'ok': True,
                          'elapsed_ms': 90, 'probe': fixture()}, 100)

    def test_rounding(self):
        value = fixture()
        value.update(elapsed_ms=0.001, hops=[{'headers_ms': 0.001}, {'headers_ms': 0.001}])
        self.assertEqual(item(lens.analyze(value, 1), 'unattributed_remainder')['ms'], 0)
        value['hops'][0]['headers_ms'] = 0.003
        with self.assertRaises(ValueError):
            lens.analyze(value, 1)

    def test_invalid_shapes_and_contradiction(self):
        for hops in (None, [4], [{}] * 12):
            value = fixture()
            value['hops'] = hops
            with self.assertRaises(ValueError):
                lens.analyze(value, 100)
        value = fixture()
        value['checks'][0]['ok'] = False
        with self.assertRaises(ValueError):
            lens.analyze(value, 100)

    def test_real_evidence_and_cli(self):
        report = ROOT.parent / 'failure-map' / 'observed-live36.json'
        result = lens.analyze(lens._source.load(report), 100)
        self.assertEqual(item(result, 'probe_total')['ms'], 84.768)
        self.assertEqual(item(result, 'unattributed_remainder')['ms'], 30.722)
        for budget, code in (('100', 0), ('80', 1), ('nan', 2)):
            run = subprocess.run([sys.executable, '-B', str(ROOT / 'timing_lens.py'),
                                  str(report), '--max-ms', budget], capture_output=True, text=True)
            self.assertEqual(run.returncode, code, run.stdout + run.stderr)
            json.loads(run.stdout)

    def test_loader_refusals(self):
        # Existing versioned files suffice; tests create no files anywhere.
        with self.assertRaises(ValueError):
            lens._source.load(Path.cwd().parent)
        with self.assertRaises(ValueError):
            lens._source.unique_object([('x', 1), ('x', 2)])
        with self.assertRaises(ValueError):
            lens._source.nonfinite('NaN')


if __name__ == '__main__':
    unittest.main()
