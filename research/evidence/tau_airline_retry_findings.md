# Native retry census: contract satisfaction versus state idempotence

Executed 19 September 2026 after recording `native_airline_retry_protocol.md`.
This is a direct-call native input census, not a model benchmark or an MCP
framework comparison. Source revision and database are those of the pinned
tau2 study. The report's `metadata.profile` refers to the source-verification
loader's construction fixture; the experiment then replaces that database with
the full native `get_db()` database, as the script and database digest record.

Every one of the 2,000 original reservations is included. All have one payment
entry and unset status; 965 use gift cards and 1,035 credit cards. These are
public benchmark records. They provide a finite input census but little
variation in initial ledger structure, and are not independent agent tasks.

| Diagnostic policy | Native cancels per record | Native reads | Final ledger entries | Status / net contract | Exact target state equals single cancellation |
|---|---:|---:|---:|---|---|
| Single cancellation | 1 | 0 | 2 | 2,000 / 2,000 | Reference |
| Three cancellations, each followed by imposed acknowledgement error | 3 | 0 | 8 | 2,000 / 2,000 | 0 / 2,000 |
| One cancellation with acknowledgement error, followed by authoritative read | 1 | 1 | 2 | 2,000 / 2,000 | 2,000 / 2,000 |

All 10,000 cancellation snapshots have cancelled status and zero signed ledger
net. The three-call policy has 2, 4 and 8 entries after successive calls. Each
native call appends the negation of every existing entry, including prior
negative entries. The observation supports ledger growth, not a claim of
duplicated external refunds or financial loss: no external payment execution
occurs. The unchanged native method does not promise strict state idempotence.

The read control calls native `get_reservation_details`, checks status and
signed net, and stops on the satisfied contract. Its final target state equals
the normal single-call control for every record. This illustrates what an
authoritative synchronous read can establish; it does not validate stale,
eventually consistent, unauthenticated or concurrently modified observations.
It is not a novel recovery policy and does not attribute retries to any tested
framework. The acknowledgement exceptions are imposed by our direct-call
harness after native returns; there is no network or transport failure.

A separate standard-library validator recomputes each expected append-negation
transition from the original database without importing native tool code or
the probe's measurement function. It checks every field, original population
coverage, native payload/state equality, all 10,000 ledger nets, 2,000 reads and
8,000 imposed exceptions. The shared in-memory database's final hash equals
its initial hash after reservation resets. No model or external connection
was used. These are internal validations by the same research process.

Raw JSONL: 27,702,472 bytes, SHA-256
`540c43d53cc0c4533209b663295bc02eca59ae9817c2e16d0211e94d0e2f4a6d`.
Validated archive: 832,348 bytes, SHA-256
`776dbaf5144d83ef7ec2f653cc2f8fcb03102324b7cbc28eaee05c66f2af836b`.
The initial validator completed all scientific checks but failed at archive
member verification because an absolute Windows script path lost its drive
prefix inside ZIP. Version 2 fixes only archive path handling, revalidates the
same immutable raw run and preserves the first validator/report. No experiment
was rerun or added to the population count.
