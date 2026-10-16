import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import transcript_inspector as tool


ZTO = '0xd782bdea4ef02a0bd391eb9089470c8080f0a68e'
WORD = lambda value: '0x' + value.to_bytes(32, 'big').hex()


def pair(data='0x18160ddd', result=WORD(17)):
    return {'request': {'jsonrpc': '2.0', 'id': 8, 'method': 'eth_call',
                        'params': [{'to': ZTO, 'data': data}, '0x123']},
            'response': {'jsonrpc': '2.0', 'id': 8, 'result': result}}


class TranscriptTests(unittest.TestCase):
    def setUp(self):
        self.abi = [{'type': 'function', 'name': 'totalSupply', 'inputs': [],
                     'outputs': [{'name': 'supply', 'type': 'uint256'}]}]

    def test_independent_total_supply_words(self):
        result = tool.inspect_transcript(self.abi, pair())
        self.assertEqual(result['status'], 'decoded')
        self.assertEqual(result['call']['signature'], 'totalSupply()')
        self.assertEqual(result['outputs'], [{'name': 'supply', 'type': 'uint256', 'value': 17}])
        self.assertEqual(result['to'], ZTO)

    def test_recorded_chain_fixture(self):
        path = 'line-4/tools/transcript-inspector/zto-total-supply-transcript.json'
        recorded = tool.read_transcript(path)
        result = tool.inspect_transcript(self.abi, recorded)
        self.assertEqual(result['status'], 'decoded')
        self.assertEqual(result['block'], '0x18fd343')
        self.assertEqual(result['outputs'][0]['value'],
                         int(recorded['response']['result'], 16))

    def test_selector_collision_stops_before_return(self):
        entries = [{'type': 'function', 'name': 'burn',
                    'inputs': [{'type': 'uint256'}], 'outputs': [{'type': 'uint256'}]},
                   {'type': 'function', 'name': 'collate_propagate_storage',
                    'inputs': [{'type': 'bytes16'}], 'outputs': [{'type': 'uint256'}]}]
        result = tool.inspect_transcript(entries, pair('0x42966c68' + '0'*63 + '1'))
        self.assertEqual(result['status'], 'call-ambiguous-selector')
        self.assertNotIn('outputs', result)

    def test_invalid_calldata_stops_before_return(self):
        result = tool.inspect_transcript(self.abi, pair('0x18160ddd00'))
        self.assertEqual(result['status'], 'call-invalid-calldata')
        self.assertNotIn('outputs', result)

    def test_noncanonical_return_rejected(self):
        result = tool.inspect_transcript(self.abi, pair(result=WORD(17) + '00'*32))
        self.assertEqual(result['status'], 'invalid-return')
        self.assertNotIn('outputs', result)

    def test_response_error_never_decoded(self):
        transcript = pair()
        transcript['response'].pop('result')
        transcript['response']['error'] = {'code': -32000, 'message': 'execution reverted'}
        result = tool.inspect_transcript(self.abi, transcript)
        self.assertEqual(result['status'], 'rpc-error')
        self.assertNotIn('outputs', result)

    def test_request_response_validation(self):
        cases = [
            (('response', 'id'), 9, 'response id'),
            (('request', 'method'), 'eth_sendRawTransaction', 'eth_call'),
            (('request', 'params'), [], 'params'),
            (('response', 'result'), 12, 'result must be'),
        ]
        for keys, value, error in cases:
            with self.subTest(keys=keys):
                transcript = pair()
                transcript[keys[0]][keys[1]] = value
                with self.assertRaisesRegex(ValueError, error):
                    tool.inspect_transcript(self.abi, transcript)
        transcript = pair()
        transcript['request']['params'][0]['from'] = ZTO
        with self.assertRaisesRegex(ValueError, 'only to and data'):
            tool.inspect_transcript(self.abi, transcript)

    def test_malformed_hex_and_output_schema(self):
        transcript = pair()
        transcript['request']['params'][0]['data'] = '0x18160dd'
        with self.assertRaisesRegex(ValueError, 'even-length'):
            tool.inspect_transcript(self.abi, transcript)
        unsupported = copy.deepcopy(self.abi)
        unsupported[0]['outputs'] = [{'type': 'string[]'}]
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            tool.inspect_transcript(unsupported, pair())

    def test_workspace_reader_and_duplicate_fields(self):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir='test/scratch') as folder:
            path = Path(folder) / 'pair.json'
            path.write_text('{"request":{},"request":{},"response":{}}')
            with self.assertRaisesRegex(ValueError, 'duplicate JSON field'):
                tool.read_transcript(path)
            path.write_bytes(b' ' * (tool.MAX_TRANSCRIPT_BYTES+1))
            with self.assertRaisesRegex(ValueError, '2 MiB'):
                tool.read_transcript(path)
        with self.assertRaisesRegex(ValueError, 'inside the current workspace'):
            tool.read_transcript('../pair.json')

    def test_cli_codes(self):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir='test/scratch') as folder:
            transcript = Path(folder) / 'pair.json'
            abi = Path(folder) / 'abi.json'
            abi.write_text(json.dumps(self.abi))
            for body, expected in [(pair(), 0), (pair(result='0x'), 1)]:
                transcript.write_text(json.dumps(body))
                out, err = io.StringIO(), io.StringIO()
                with patch('sys.argv', ['tool', '--abi', str(abi), '--transcript', str(transcript)]), \
                     contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    self.assertEqual(tool.main(), expected)
                self.assertEqual(err.getvalue(), '')
                self.assertEqual(json.loads(out.getvalue())['status'],
                                 'decoded' if expected == 0 else 'invalid-return')


if __name__ == '__main__':
    unittest.main()
