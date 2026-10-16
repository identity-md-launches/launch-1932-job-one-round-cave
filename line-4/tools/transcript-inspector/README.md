# Transcript Inspector

Interpret a saved Ethereum `eth_call` request and response entirely offline.
The tool checks the request and response IDs, validates canonical calldata,
identifies a unique function from a supplied ABI, and strictly decodes its
return bytes. It reuses Line 4's standard-library Call Inspector and ABI
Workbench; keep their sibling folders alongside this one. It never contacts a
node, reads a wallet or environment, signs, sends, pays, or posts anything.

From the repository root, this **one command** runs the included ZTO example:

```sh
python3 -B line-4/tools/transcript-inspector/transcript_inspector.py --abi line-4/tools/transcript-inspector/zto-total-supply-abi.json --transcript line-4/tools/transcript-inspector/zto-total-supply-transcript.json
```

Tried here: exit 0, `totalSupply()` selector `0x18160ddd`, zero arguments,
one `uint256` output equal to `1000000000000000000000000000` raw units. The
fixture contains a read-only response from `ethereum-rpc.publicnode.com` for
ZTO (`0xd782bdea4ef02a0bd391eb9089470c8080f0a68e`) on Ethereum mainnet,
block `0x18fd343`, whose reported hash was
`0xc1e6be32b6281c7afa1a427dbf9f4cd7b70ab79637131913721f0c14438dd286`.
The separately captured chain ID was `0x1`. This is a saved observation, not a
live balance or price. The tool does not verify the RPC source or block hash,
nor infer token decimals. The ABI is an explicit interface for this example;
the tool cannot establish the deployed contract's true ABI.

For another transcript, supply a workspace-contained ABI JSON path and a JSON
file containing `request` and `response` objects. The request must be JSON-RPC
2.0 `eth_call` with `[ {"to":"0x...","data":"0x..."}, "0xBLOCK" ]` parameters;
only `to` and `data` are accepted in the call object. The response must have
the same ID and either `result` hex or a JSON-RPC `error` with integer `code`
and string `message`. Block tags are also accepted. Any `observation` field is
ignored by the interpreter. It cannot authenticate that request and response
were ever exchanged; keep independent provenance when that matters.

Exit 0 means the supplied bytes decoded under exactly one ABI function. Exit 1
prints JSON for an RPC error, unknown or ambiguous selector, noncanonical
calldata, or invalid return bytes. Exit 2 writes `error:` to stderr for invalid
JSON, input shape, unsupported ABI types, malformed hex, file errors or limits.
No values are claimed when the call is ambiguous or its return is invalid.

The transcript file is limited to 2 MiB, the ABI file to 1 MiB, and each ABI
byte sequence to 1 MiB plus a four-byte call selector. The inherited limits on
function count, tuple depth, parameter count, and array size also apply.
Inputs must stay inside the current workspace, including resolved symlinks.
Only the selected function's supported outputs are decoded. Unsupported
unrelated output schemas do not prevent selector inventory; unsupported inputs
do, because skipping one could conceal a collision. Saved RPC errors are
reported but revert bytes within them are not interpreted here.

The focused regression suite passed all 10 tests, including the pinned fixture,
selector collision, invalid call and return layouts, RPC errors, malformed
request/response pairs, reader limits, and CLI exits:

```sh
python3 -B -m unittest discover -s line-4/tools/transcript-inspector -v
```
