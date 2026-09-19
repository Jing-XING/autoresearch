# Completed-domain audit while the third domain is running

This is an interim diagnostic record, not the complete registered result.
The 160 completed computer_student/cars episodes were exported only after
all eight workers exited with code zero. The remaining publishing wave was
still running. No prompt, budget, task, or runtime was changed in response.

Archive: `results/remote/vakra-crossdomain-first160-v1.zip`, 1,209,649 bytes,
185 files, SHA-256
`f3162f7796064bef9e0af3b3093f48bdb7c2dc70b9bb163b87e5061ba716457f`.
The bounded transfer verified the digest before exclusive creation; extraction
checked every path. Original artifacts remain intact.

All 160 final answers were read against the previously frozen SQL cards and
policy. Explicit labels, reasons and raw hashes are in
`vakra_crossdomain_first160_answer_annotations.json`. These are assistant
annotations, not independent human labels or official VAKRA scores.

| Domain | Checkpoint | Original correct | Reminder correct | Interpretable tasks | Gains / losses |
|---|---|---:|---:|---:|---:|
| computer_student | Qwen3 | 4 | 4 | 17 | 0 / 0 |
| computer_student | Qwen2.5 | 4 | 4 | 17 | 0 / 0 |
| cars | Qwen3 | 10 | 15 | 18 | 5 / 0 |
| cars | Qwen2.5 | 9 | 9 | 18 | 1 / 1 |

The five ambiguous task identities remain in execution reporting. Field
descriptions used for the offline SQL interpretation were not added to model
prompts. Thus glossary-dependent errors and uncertainty are not automatically
evidence of avoidable reasoning failure. Two student questions additionally
have the previously documented initialization insufficiency.

The car-name enumeration question requires 187 distinct names. All three
generated final lists in that task are incomplete and end at the configured
512-token ceiling; the fourth episode reaches the protocol-error limit.
This demonstrates a material output-budget limitation in the experiment,
not a formal proof that every possible answer representation exceeds 512 tokens.

Across these 160 episodes, 65 recorded protocol errors are local rejections of
multiple tool calls, four are incomplete blocks, and four are unknown tool
names. A separate CPU audit replays each affected episode up to its first
multiple-call rejection, then executes that fixed call sequence unchanged.
All original prefix responses match. Of 20 such sequences, seven execute all
calls; 22 of 57 calls produce execution errors across the other sequences.
No generated argument, handle, tool name or result was repaired.

Executable is not correct: one fully executable car sequence computes the
unrestricted maximum acceleration 24.8 instead of the requested price-filtered
maximum 21.7. Another successfully counts the six course-18 teachers, but the
original agent already recovered the right answer after its protocol retry.
These diagnostics do not determine the outcome of a hypothetical batch-enabled
agent. That requires fresh model continuation and separate budget accounting.

The frozen full-grid execution/answer audits remain pending until all 240
episodes and the terminal manifest are recovered. The snapshot will then be
checked byte-for-byte against the corresponding final artifacts.
