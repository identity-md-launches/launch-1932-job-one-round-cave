#!/usr/bin/env python3
"""Explain saved Endpoint Sentry timings without making a request."""
import argparse
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import sys

# Reuse the delivered strict, workspace-contained loader and health validator.
_spec = importlib.util.spec_from_file_location(
    'timing_failure_map', Path(__file__).resolve().parent.parent / 'failure-map' / 'failure_map.py')
_source = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_source)
SCHEMA = 'timing-lens/v1'
MAX_MS = Decimal('86400000')


def duration(value):
    if type(value) not in (int, float):
        raise ValueError('duration must be a JSON number')
    result = Decimal(str(value))
    if not result.is_finite() or not 0 <= result <= MAX_MS:
        raise ValueError('duration must be finite and between zero and one day in ms')
    return result


def analyze(source, max_ms):
    budget = duration(max_ms)
    _source.validate(source)
    result = {'schema': SCHEMA, 'source_ok': source['ok'],
              'max_probe_ms': float(budget), 'outcome': 'unknown',
              'timings': [], 'missing': [],
              'interpretation': [
                  'Header intervals include connection setup, request and header receipt; they are not server processing time.',
                  'The remainder includes unmeasured setup, body, validation, cleanup and failed intervals; it is not body time.',
                  'One saved observation does not establish current availability, throughput or a root cause.']}
    wrapper = source['schema'] == 'deadline-sentry/v1'
    if wrapper and 'probe' not in source:
        result.update(outcome='unobserved', missing=['/probe'])
        return result
    probe = source['probe'] if wrapper else source
    prefix = '/probe' if wrapper else ''
    hops = probe.get('hops')
    if not isinstance(hops, list) or len(hops) > 11 or any(not isinstance(h, dict) for h in hops):
        raise ValueError('invalid or excessive hops')
    total = None
    if 'elapsed_ms' in probe:
        total = duration(probe['elapsed_ms'])
        result['timings'].append({'name': 'probe_total', 'ms': float(total),
                                  'evidence': [prefix + '/elapsed_ms']})
        result['outcome'] = 'within-budget' if total <= budget else 'over-budget'
    else:
        result['missing'].append(prefix + '/elapsed_ms')
    intervals = []
    pointers = []
    for index, hop in enumerate(hops):
        pointer = prefix + '/hops/' + str(index) + '/headers_ms'
        if 'headers_ms' not in hop:
            result['missing'].append(pointer)
            continue
        elapsed = duration(hop['headers_ms'])
        intervals.append(elapsed)
        pointers.append(pointer)
        result['timings'].append({'name': 'connect_through_headers', 'hop': index,
                                  'ms': float(elapsed), 'evidence': [pointer]})
    # Each producer duration is rounded independently to three decimal places.
    # Account for at most 0.0005 ms error per summand and total.
    measured = sum(intervals, Decimal(0))
    tolerance = Decimal('0.0005') * (len(intervals) + 1)
    if total is not None and measured > total + tolerance:
        raise ValueError('header intervals exceed recorded probe total')
    if total is not None and len(intervals) == len(hops):
        result['timings'].append({'name': 'unattributed_remainder',
                                  'ms': float(max(Decimal(0), total - measured)),
                                  'evidence': [prefix + '/elapsed_ms'] + pointers,
                                  'rounding_tolerance_ms': float(tolerance)})
    if wrapper:
        if 'elapsed_ms' not in source:
            result['missing'].append('/elapsed_ms')
        else:
            outer = duration(source['elapsed_ms'])
            result['timings'].append({'name': 'wrapper_total', 'ms': float(outer),
                                      'evidence': ['/elapsed_ms']})
            if total is not None:
                if total > outer + Decimal('0.001'):
                    raise ValueError('probe total exceeds wrapper total')
                result['timings'].append({'name': 'wrapper_overhead',
                                          'ms': float(max(Decimal(0), outer - total)),
                                          'evidence': ['/elapsed_ms', '/probe/elapsed_ms'],
                                          'rounding_tolerance_ms': 0.001})
    result['breakdown_complete'] = not result['missing']
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('report')
    parser.add_argument('--max-ms', type=float, required=True,
                        help='inclusive budget for recorded probe total, 0..86400000 ms')
    args = parser.parse_args(argv)
    try:
        # Refuse invalid arguments before touching the supplied file.
        duration(args.max_ms)
        report = _source.load(args.report)
        result = analyze(report, args.max_ms)
    except (ValueError, OSError, UnicodeError, RecursionError):
        print(json.dumps({'schema': SCHEMA, 'error': 'Invalid evidence, budget or workspace path.'}))
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['outcome'] == 'within-budget' else 1


if __name__ == '__main__':
    sys.exit(main())
