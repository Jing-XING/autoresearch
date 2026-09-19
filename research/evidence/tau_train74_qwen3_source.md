# Complete Qwen3 source pool for memory development

All 74 registered telecom train tasks completed. Qwen3-4B-Instruct-2507
succeeded on 14, with no run or protocol exceptions. There are 71 agent-stop
terminations and three step-limit terminations. These are source-pool
observations, not target-memory results and not an independent test score.

Both source shards are locally archived with their complete manifests, model
audits and official simulations. Each has 114 files:

| Archive | Bytes | SHA256 |
|---|---:|---|
| tau-train74-qwen3-shard-0.zip | 9167961 | e4e1236236ece8abaf3a73677659b92469db51d75e5abc346689b7cf67b14111 |
| tau-train74-qwen3-shard-1.zip | 8897391 | 0c7a64592f3b352206054525363926b3a83084ed1fc5dee0ffc96b4a5524ab92 |

Reconstructed cutoff corpus: 222 prefixes from 74 distinct tasks, no excluded
source runs. This does not provide 222 independent tasks.

An additional replay of the official environment and action assertions over
all complete generation prefixes audits all 74 episodes without an unscored
run. Exactly 14 episodes ever satisfy the complete task requirements, matching
the 14 official successes. No satisfied-to-unsatisfied reversal or final
satisfied-but-officially-unsuccessful episode is observed. The analysis-only
assertions remain unavailable to the curator and target policy.

| Generation cutoff | Externally cut | Later recorded success among externally cut | Observed success by cutoff |
|---|---:|---:|---:|
| 4 | 74 | 14 | 0 |
| 8 | 69 | 10 | 4 |
| 16 | 63 | 7 | 7 |

At cutoff eight, all 74 records enter the curation pool regardless of future
outcome. The ten later successes do not establish that each prefix action was
correct or that any generated lesson improves another task.

The raw-call accounting totals 17,063,473 input tokens and 32,584 generated
output tokens. Summed measured generation latency is 3,270.35 seconds; this is
neither wall-clock batch duration nor full billed GPU time. Model loading,
fingerprinting and other overhead are outside that latency metric.

`tau_train74_qwen3_source_summary.json` verifies manifests, task identities,
prompt hashes and reward consistency. The local cutoff manifest SHA256 is
`ed43dd440e9376c642922f2a1658e95808c4e1e604d381bda4e8368ac77f9cdd`.
