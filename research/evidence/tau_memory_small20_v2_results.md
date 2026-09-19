# Complete developmental memory transfer comparison

All 200 registered episodes are present. All 20 worker processes exited zero;
five episode-level protocol exceptions remain non-success in denominators.
Analysis checks bank, tasks, runtime/checkpoint fingerprints and actual
retrieved-source identity across arms. This is development, not confirmation.

| Condition | Qwen3 success/20 | Qwen2.5 success/20 | Qwen2.5 exceptions |
|---|---:|---:|---:|
| none | 13 | 7 | 0 |
| raw | 11 | 11 | 0 |
| outcome_only | 10 | 7 | 4 |
| full_metadata | 10 | 11 | 1 |
| boundary_aware | 10 | 8 | 0 |

Qwen3 has no exceptions. Primary paired boundary/full comparison: Qwen3 0 wins,
0 losses; Qwen2.5 0 wins, 3 losses. Thus no demonstrated benefit for the
additional boundary instruction. Raw/full each improve five Qwen2.5 tasks
and lose one against none, but results differ by checkpoint. Twenty task
identities and four source memories do not justify population-wide claims.

Strict prefix-state replay: raw 40 audited/22 ever satisfied; outcome 36/17;
full 39/21; boundary 40/18. No reversal or satisfied-but-official-failed case.
All five exception histories remain unsatisfied before their malformed call.
Three outcome-only errors emit check_status_bar without arguments; the fourth
outcome-only and the full-metadata error emit done without arguments. No
repair, re-scoring or exclusion was applied. Reconstruction matches the
recorded simulation prefix for all 195 normally completed episodes.

The three early outcome-only failures share the same native input hash,
although they are different benchmark task IDs. This is another reason to
avoid treating related task identities as independent observations.

Target generation time: 7,160.2284 seconds. Sum of worker wall times:
7,870.2754 seconds. Batch elapsed: 2,320.1058 seconds. These are different
timing quantities, not energy or GPU utilization measurements. Curation
generation seconds, once per complete bank: outcome 248.3183; full 249.2858;
boundary 247.7904. Source collection is additional. Premature protocol failure
can reduce runtime; lower runtime alone does not establish greater efficiency.

Machine-readable evidence: `tau_memory_small20_v2_analysis.json`, four
`tau_memory_v2_*_state_audit.json` files and
`tau_memory_v2_protocol_failure_audit.json`.

All raw artifacts are retained under the ignored results directory. Four
return archives were SHA256 verified and extracted without overwriting:

- none: d776635604a6d948f7d87c935588e8bcb49578050482f0d1b0128d5229666a5b
- boundary: 84727af04840bd96608b3267b396a459d4a7673eb3735568e85e8723b5803e69
- mid60: 597ca30bfe9f07eff35b5b52c8311bfa9ef19a8479213518e3d3eaa2038e0723
- tail60: 229890e34d477f9021d6d7b7865db8784ae50460de81a71cfabb1861f7ec2457
