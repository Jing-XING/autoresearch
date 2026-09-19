# Executable-output baseline: pinned source audit

Repository: https://github.com/LongFuncEval/toolJSONprocessing

Inspected commit: `2662547b5b82dd638ac06df2dbc4e70b764137fc`.
The Git object download succeeded, but Windows checkout rejected a dataset
filename containing `?`. Source inspection used `git show` against the pinned
object; no upstream module, generated program or hosted API was executed.
This is not a reproduction of the paper's results.

In [general_code_generation.py](https://github.com/LongFuncEval/toolJSONprocessing/blob/2662547b5b82dd638ac06df2dbc4e70b764137fc/codegen_scripts/general_code_generation.py),
the schema-only and compact-response settings alter the model prompt while
the generated function is executed on the original full API response.
Prompt visibility and runtime data access are therefore different quantities.
The compact representation selects list elements that introduce new keys;
it is not a guarantee of coverage of all values. Its executor uses ordinary
Python execution, so reproducing it requires an isolated execution environment
rather than importing it into this workspace process.

In [qa_inference.py](https://github.com/LongFuncEval/toolJSONprocessing/blob/2662547b5b82dd638ac06df2dbc4e70b764137fc/experimental_scripts/qa_inference.py),
the `cfx2` reduction derives relevant JSON paths from the task's gold-answer
function. That oracle simplification is a separate experimental condition,
not an implementable query-only retrieval policy. The published settings also
use a 1,000-token generation allowance; our existing 512-token tool-interaction
grid is not a budget-matched reproduction.

Implication for this project: a full-data code baseline must disclose its
additional access to materialized data, and an observed-history code baseline
must execute only on responses actually acquired. These answer different
questions. Neither should be mislabeled as the other, and no hidden SQL card,
reference program or answer-derived selector may enter the agent's prompt.
This audit establishes a baseline-design constraint, not a novel algorithm.
