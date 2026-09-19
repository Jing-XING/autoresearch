# Geography-preserving status-flip control

This refinement was designed after observing both the manual Andorra witness
and the failed broad schema-only search. It is a development positive control,
not an independent replication or a new prevalence estimate.

The admissible change is one existing CountryLanguage.IsOfficial value,
flipped between T and F. Every other cell remains fixed. This preserves the
country/city identities and geographical relationships that defeated the
broader search. It does not certify every possible domain constraint.

Among the ten previously eligible target SQL interpretations, only world
tasks 3 and 6 read this column. The generator exhaustively tests 984 flips
per query for changes in the requested SQL projection, yielding four
answer-changing candidates for task 3 and one for task 6. All four
model/prompt arms are replayed. Eight original replays match exactly; fourteen
mutant replays yield witnesses for six episodes, with early stopping at the
first witness. The two remaining episodes have no witness in this limited
single-cell class, not a general sufficiency certificate.

The six include four episodes without final answers, one incorrect answer,
and the previously correct Qwen3 reminder answer to task 3. In that correct
case, the exhaustive status search recovers the exact previously verified
Spanish F-to-T mutation; its complete target-observation digest matches the
manual witness. This is recovery of a known positive control, not a new
independent positive result. The Qwen3 reminder and Qwen2.5 original task-6
trajectories expose the relevant status change and do not receive a witness.

All source files, candidate mutations, query interpretations, replay outcomes
and database hashes are retained. The original database is unchanged.
Reproduce with `scripts/audit_vakra_binary_status.py`, which prepares its
candidate artifact and invokes the shared real-MCP replay validator. The
source hash in the candidate file records the post-outcome refinement.
