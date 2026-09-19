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
