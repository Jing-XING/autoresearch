# A feasible complete retrieval through the existing cookbook interface

This post-outcome control follows the [frozen diagnostic scope](../cookbook_acquisition_control.md).
It uses the six completed trajectories of cookbook task 015; it is one question,
not six independent tasks and not an additional model experiment.

All six original trajectories eventually select the recipe with maximal cooking
time, then give incomplete or incorrect ingredients. We replayed each worker's
warmup and fifteen prior episodes through the unchanged native stdio MCP server.
All 224 preceding calls, target initial observations, ordered schemas and selected
prefix responses match. The official runtime files and database match their
preparation hashes. Local dependencies are retained in the execution report;
they are not assumed identical merely because source hashes match.

An evaluator-authored routine sorts the selected table by `Ingredient_name` and
filters subsequent pages with `greater_than` using the last visible value. It
receives no database or reference card. Actual MCP responses expose ten, seven,
four and one remaining rows. The ten distinct visible names reconstruct the
complete reference answer, including butter or margarine, lemon juice, pine nuts
and ripe olives. This ordinary keyset-pagination control takes four additional
calls in every history, totaling six calls in four histories and seven in two.

All six raw results were saved before loading the SQL card. A separate validator
then checked response-by-response cursor arguments, the observed ingredients,
the frozen card and freshly executed read-only SQL. All match, and the original
database hash is unchanged. Four boundary tests pass, covering repeated values,
empty versus unqueried data, budget exhaustion and invalid/nonprogressing input.

The result narrows the interpretation of the original failure: the missing
full-column getter does not prevent complete acquisition in this example under
the twenty-call budget. It does not establish that any model discovers the
sequence or correctly interprets other queries. The chosen predicate checkpoint
and output column are evaluator supplied after inspecting the example. No model
continuation, prompt change, independent prevalence estimate or novel pagination
algorithm is claimed. The controller assumes non-null strings, consistent
sort/filter order, stable data and truthful row counts; previews alone do not
certify those assumptions for arbitrary tables.

Raw archive: `results/remote/vakra-cookbook-acquisition-v1-evidence.zip`, 39,185
bytes, 18 entries, SHA-256
`7264cfefdf4a2f0cf332b995292255c09c61bb2d6a5f87a39dcdfae5d2a1cfdc`.
The report and validation retain source, protocol, implementation and raw hashes.
