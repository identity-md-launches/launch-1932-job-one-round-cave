#!/usr/bin/env python3
"""Interpret a saved eth_call request and response against a supplied ABI, offline."""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys


INSPECTOR = Path(__file__).resolve().parents[1] / 'call-inspector' / 'call_inspector.py'
spec = importlib.util.spec_from_file_location('line4_call_inspector', INSPECTOR)
calls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calls)
codec = calls.codec
MAX_TRANSCRIPT_BYTES = 2 * 1024 * 1024
ADDRESS = re.compile(r'0x[0-9a-fA-F]{40}\Z')
QUANTITY = re.compile(r'0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)\Z')
BLOCK_TAGS = {'latest', 'pending', 'safe', 'finalized', 'earliest'}


def read_transcript(path):
    source = Path(path).resolve()
    if not source.is_relative_to(Path.cwd().resolve()):
        raise ValueError('transcript path must stay inside the current workspace')
    with source.open('rb') as stream:
        raw = stream.read(MAX_TRANSCRIPT_BYTES + 1)
    if len(raw) > MAX_TRANSCRIPT_BYTES:
        raise ValueError('transcript exceeds the 2 MiB input limit')
    try:
        return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=codec.unique_object)
    except RecursionError as exc:
        raise ValueError('transcript JSON nesting is too deep') from exc


def validate_transcript(transcript):
    if not isinstance(transcript, dict):
        raise ValueError('transcript must be a JSON object')
    request, response = transcript.get('request'), transcript.get('response')
    if not isinstance(request, dict) or not isinstance(response, dict):
        raise ValueError('request and response must be JSON objects')
    if request.get('jsonrpc') != '2.0' or response.get('jsonrpc') != '2.0':
        raise ValueError('request and response must use JSON-RPC 2.0')
    identifier = request.get('id')
    if (isinstance(identifier, bool) or not isinstance(identifier, (int, str)) or
            isinstance(identifier, str) and len(identifier) > 128):
        raise ValueError('request id must be an integer or short string')
    if type(response.get('id')) is not type(identifier) or response['id'] != identifier:
        raise ValueError('response id does not match request id')
    if request.get('method') != 'eth_call':
        raise ValueError('request method must be eth_call')
    params = request.get('params')
    if not isinstance(params, list) or len(params) != 2:
        raise ValueError('eth_call params must contain a call object and block identifier')
    call, block = params
    if not isinstance(call, dict) or set(call) != {'to', 'data'}:
        raise ValueError('call object must contain only to and data')
    if not isinstance(call['to'], str) or not ADDRESS.fullmatch(call['to']):
        raise ValueError('to must be a 20-byte hex address')
    if not isinstance(call['data'], str):
        raise ValueError('call data must be 0x hex')
    if not isinstance(block, str) or not (block in BLOCK_TAGS or QUANTITY.fullmatch(block)):
        raise ValueError('block must be a JSON-RPC block tag or hex quantity')
    calldata = codec.parse_data(call['data'], call=True)
    has_result, has_error = 'result' in response, 'error' in response
    if has_result == has_error:
        raise ValueError('response must have exactly one of result or error')
    if has_error:
        error = response['error']
        if (not isinstance(error, dict) or
                isinstance(error.get('code'), bool) or not isinstance(error.get('code'), int) or
                not isinstance(error.get('message'), str)):
            raise ValueError('response error needs integer code and string message')
        if len(error['message']) > 4096:
            raise ValueError('response error message is too long')
        return call, block, calldata, None, {'code': error['code'], 'message': error['message']}
    if not isinstance(response['result'], str):
        raise ValueError('response result must be 0x hex')
    return call, block, calldata, codec.parse_data(response['result']), None


def inspect_transcript(entries, transcript):
    """Decode bytes only. Neither the ABI nor a saved response proves chain origin."""
    call, block, calldata, returndata, rpc_error = validate_transcript(transcript)
    result = {
        'schema': 'transcript-inspector/v1', 'to': call['to'].lower(),
        'block': block, 'request_id': transcript['request']['id'],
        'calldata_bytes': len(calldata),
    }
    inspected = calls.inspect_call(entries, calldata)
    result['call'] = inspected
    if rpc_error is not None:
        result.update(status='rpc-error', rpc_error=rpc_error)
        return result
    result['return_data_bytes'] = len(returndata)
    if inspected['status'] != 'decoded':
        result['status'] = 'call-' + inspected['status']
        return result
    fn = entries[inspected['abi_index']]
    outputs = fn.get('outputs', [])
    codec.check_type_tree(outputs)
    for output in outputs:
        codec.canonical(output)
    try:
        decoded = codec.decode_tuple(outputs, returndata, strict=True)
    except (ValueError, UnicodeError) as exc:
        result.update(status='invalid-return', error=str(exc))
    else:
        result.update(status='decoded', outputs=decoded)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--abi', required=True, help='workspace-contained ABI JSON file')
    parser.add_argument('--transcript', required=True, help='workspace-contained saved JSON-RPC pair')
    args = parser.parse_args()
    try:
        entries = calls.inventory.read_abi(args.abi)
        result = inspect_transcript(entries, read_transcript(args.transcript))
    except (ValueError, OSError, UnicodeError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'decoded' else 1


if __name__ == '__main__':
    raise SystemExit(main())
