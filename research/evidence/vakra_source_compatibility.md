# VAKRA source compatibility audit

This is a reference-program replay, not an agent evaluation or an official
benchmark score. No generated model response, external judge, or paid API was
used. The small `world` database was selected for its download size before any
performance observation.

## Pinned inputs

- [IBM VAKRA](https://github.com/IBM/vakra), commit
  `c9e82dfe46aee016d2bfe3a0c8fed652760e4c0c`, CC-BY-NC-SA-4.0.
- [IBM LiveAPIbench](https://github.com/IBM/live-api-bench), commit
  `1ac53495fa9088919583c06fcff98a4b411b4a69`, Apache-2.0.
- [VAKRA dataset](https://huggingface.co/datasets/ibm-research/VAKRA), revision
  `1388b9f1aaed887a73957eba651a6c2034010476`, CC-BY-NC-SA-4.0.
- Database SHA256:
  `813faade795b875f6d46cf81d9651e2400524b414a407aa9d473aa9a8c142861`.
- Reference output JSON SHA256:
  `6343f50f91995a6c82a41b4280be69d919e0ee26ea3636772ba28e411e47a67d`.

The inspected dataset tree contains 274 train files and no test directory at
this revision. README test statistics do not establish that a test split has
been downloaded. VAKRA and the earlier LiveAPIbench release are related but
cannot be treated as interchangeable evaluation protocols.

## Procedure and observations

The audit invokes the unmodified VAKRA selection functions, relocates the
database path, resolves reference variables, and disables transport/Pydantic
wrappers for direct Python invocation. Gold initialization and gold tool calls
are allowed in this compatibility control. They must not become a blind
agent's input. The SQLite file hash is unchanged after replay.

All 52 reference sequences execute without an exception. Direct serialized
JSON comparison matches 16 of 52. Normalizing terminal outputs with the
earlier LiveAPIbench serializer/comparator gives 50 of 52 matches. The two
remaining differences are integer/float representations (55 versus 55.0 and
3538 versus 3538.0) inside lists; that comparator stringifies list elements.
These results diagnose cross-release representation differences, not model
failures and not a demonstrated defect in VAKRA's own evaluator.

The VAKRA evaluator's default policy includes external correctness and
groundedness judges. Its exact-match judge has a deterministic comparison
method but inherits an external-client constructor. Therefore the default
evaluation pipeline was not executed, and this audit cannot be described as
a completed official benchmark run.

Runtime versions: pandas 3.0.1, NumPy 2.3.5, Pydantic 2.13.5, sqlglot 30.18.0.
Full traces, outputs and downloaded data remain in ignored local artifacts.

## Reproduction

Run `python -m autolab.vakra_reference_audit --help` for the explicit source,
database and reference arguments. The optional `--normalization-source` is
the pinned LiveAPIbench checkout; `--dependency-dir` can point to an isolated
sqlglot installation. Without those arguments the script reports direct JSON
comparison only. Never present either comparison as an agent success rate.

## Real MCP compatibility control

The checked-in MCP universe mapping has 2,085 entries, including eight entries
whose domain is exactly `world`, but none of the 52 downloaded train UUIDs.
The upstream generator defaults to a test-output directory absent from this
dataset revision. `autolab.vakra_prepare` invokes that unchanged generator with
the train-output directory and a new destination. It retains all 52 input
queries, their prescribed initial table/join arguments, and upstream-derived
tool family. No answer or reference-program file is copied into the runtime.
The original checkout remains unchanged. The final minimal runtime packages
only capability-1 server code and its license, excluding unrelated BPO data.

An actual MCP stdio replay enables the official Pydantic wrappers and server
handles. In the first pass, five reference programs fail: the startup universe
does not advertise its dynamic getter, two reference column names differ in
case from the schema, and two count calls use an empty column name that the MCP
validator rejects. These are interface compatibility failures, not model errors.

The Router creates getters before its input-model dictionary exists; only a
later universe switch registers their schemas. A public `get_data` call to a
different input universe before the first evaluated task avoids the startup
omission. This setup call is logged separately and is not placed in the model
context. Tool schemas are refreshed after each task's universe switch. The
server's tool behavior is unchanged, and reference parameters are not repaired.
With this documented setup, 48/52 reference programs execute; four retain the
column-validation errors. Direct JSON answer comparison matches 14/52 and is
still not an official score. The database hash remains unchanged. A two-task
preflight confirms the reduced runtime retains the working interface.

`autolab.vakra_native` now connects the existing local native-template model
adapter to this MCP server. It loads the unchanged official system-prompt
method separately from hosted-model imports, permits final text answers, and
records raw generations, actual tool responses, budgets and errors. It has no
reference-answer argument and does not compute a score during interaction.
Three unit tests cover tool-to-answer transitions, rejecting multiple calls
before execution, and preserving a generated trace after transport failure.
A scripted CPU preflight also traverses the real prompt, MCP schema, handle and
getter response. It is not a language-model run. Its first fixture incorrectly
guessed a handle prefix; the corrected fixture reads the actual handle from
the official prompt. Both diagnostic logs are retained.

MCP runtime used here: mcp 1.30.0, pandas 3.0.1, NumPy 2.3.5,
Pydantic 2.13.5, PyYAML 6.0.3. Generated 52-query mapping SHA256:
`c692d4a77426d18ff8c422469aa914cde2ffc7f5846c56f9a9540b9dedcd1ec5`.
No GPU model result or external judge result is claimed by these controls.
