#!/usr/bin/env python3
"""Bounded current CLI trials; only gathering evidence and scratch are written."""
import json
from pathlib import Path
import subprocess
import sys


def main():
    scratch = Path('test/scratch/gathering37/current')
    scratch.mkdir(parents=True, exist_ok=True)
    results = []

    def run(name, script, args, expected, outcome=None, save=None):
        command = [sys.executable, '-B', script, *map(str, args)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=20)
        try:
            value = json.loads(result.stdout)
        except ValueError:
            value = result.stdout[:500]
        passed = result.returncode == expected
        if outcome is not None:
            passed &= isinstance(value, dict) and value.get('outcome') == outcome
        results.append({'name': name, 'command': command, 'exit_code': result.returncode,
                        'expected_exit_code': expected, 'passed': passed,
                        'output': value, 'stderr': result.stderr[:1000]})
        if save and result.stdout:
            Path(save).write_text(result.stdout)
        return value

    failure = 'line-1/tools/failure-map/failure_map.py'
    run('Failure Map real retained healthy report', failure,
        ['line-1/tools/failure-map/observed-live36.json'], 0, 'healthy-observation')
    run('Failure Map real retained HTTP 404', failure,
        ['line-1/tools/endpoint-sentry/live-failure.json'], 1, 'http-failure')
    watchdog = scratch / 'watchdog.json'
    watchdog.write_text(json.dumps({'schema':'deadline-sentry/v1','ok':False,
                                    'error':{'kind':'deadline','message':'worker killed'}}))
    run('Failure Map repaired watchdog phase', failure, [watchdog], 1, 'watchdog-failure')
    check = scratch / 'check.json'
    check.write_text(json.dumps({'schema':'endpoint-sentry/v1','ok':False,
                                 'hops':[{'status':200}],
                                 'checks':[{'name':'status','ok':True},
                                           {'name':'json_value','ok':False}]}))
    run('Failure Map repaired failed JSON check', failure, [check], 1, 'check-failure')

    run('CSV Multiplicity documented duplicate demo',
        'line-2/tools/csv-multiplicity/multiplicity.py',
        ['line-2/tools/csv-multiplicity/demo-before.csv',
         'line-2/tools/csv-multiplicity/demo-after.csv',
         '--key','item','--key','location'], 1)
    run('Import Lineage repaired symbol import',
        'line-3/tools/import-lineage/lineage.py',
        ['line-3/tools/import-lineage/examples','app','service'], 0)
    run('Call Inspector constructed ZTO argument',
        'line-4/tools/call-inspector/call_inspector.py',
        ['--abi','line-4/tools/selector-audit/erc20.json',
         '--data','0xa9059cbb000000000000000000000000d782bdea4ef02a0bd391eb9089470c8080f0a68e000000000000000000000000000000000000000000000000000000000000000c'], 0)
    run('Calldata Rehearsal unsigned ZTO balance argument',
        'line-4/tools/calldata-rehearsal/calldata_rehearsal.py',
        ['--selector','0x70a08231','--types','address','--values',
         '0xd782bdea4ef02a0bd391eb9089470c8080f0a68e'], 0)
    run('Shared repeated HTTP evidence row review',
        'shared/http-evidence/multiplicity_review.py',
        ['shared/http-evidence/demo-multiplicity-before36.csv',
         'shared/http-evidence/demo-multiplicity-after36.csv'], 1)

    live = 'gathering/live-http37.json'
    run('Deadline Sentry bounded public GET',
        'line-1/tools/deadline-sentry/deadline_sentry.py',
        ['--deadline','8','https://api.imd.fun/launches',
         '--timeout','5','--max-bytes','262144','--max-redirects','0','--json'],
        0, save=live)
    report = {'round':37,'ok':all(item['passed'] for item in results),
              'results':results}
    Path('gathering/current-checks37.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'ok':report['ok'],'checks':len(results),
                      'failed':[item['name'] for item in results if not item['passed']]},indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
