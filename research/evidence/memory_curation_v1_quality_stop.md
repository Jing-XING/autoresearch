# Shared output-contract revision before memory treatment

The v1 source bank contains all 74 source tasks in each of three conditions.
All 222 generations completed technically, and the bank was reconstructed
exactly from its archived inputs and curation records. Technical completion
was insufficient: inspection found lessons ending mid-sentence or before their
recommendation/applicability sections were complete.

| Condition | Records | Input tokens | Output tokens | At 256-token ceiling |
|---|---:|---:|---:|---:|
| outcome_only | 74 | 508773 | 16272 | 57 |
| full_metadata | 74 | 510914 | 18944 | 74 |
| boundary_aware | 74 | 514318 | 18944 | 74 |

A ceiling hit alone does not prove truncation, but the recorded text includes
directly observable unfinished lessons. The instructions requested several
components without an adequate common brevity contract. Interpreting target
differences as evidence-boundary effects under this condition would be weak.

The target grid `tau-memory-small20-v1` was therefore interrupted. Only its
no-memory workers had started; no memory-treatment worker had been launched.
The decision used curation artifacts, not a treatment-performance comparison.
The supervisor and its four identified child processes were terminated; raw
partial baseline outputs and a quality-stop record are retained. This aborted
grid is neither a completed comparison nor a failed-method result.

V2 adds the same three-sentence, at-most-90-word instruction to every curated
condition while retaining the 256-token hard ceiling. It explicitly marks a
ceiling hit as ineligible for bank compilation, preserves the actual text and
counts, and refuses to compile a bank with a missing/failed condition. The
source pool, cutoff, evidence contrast, checkpoint and target retrieval do not
change. Word/sentence compliance remains an observable quality check rather
than evidence that every generated claim is supported.

V1 curation archive: 677 files, 4,340,766 bytes, SHA256
`9708967d4451c7a5ae73fc46d7132e9fcc0f64ad6993a7c6a165176461531d2a`.
V1 bank SHA256:
`71fba4c4f7c2432b6fa9a0d31febba63f3c80be85c5752b30506249713238951`.

The independently rebuilt cutoff manifests differ in CRLF versus LF byte
encoding only. Their parsed values are identical. Canonical JSON SHA256 is
`dab9080d960f80d62e938b3951359b2d6a69ccb222caf66067ffca2b042f7704`.
The remote LF byte hash is
`f427192d6fb9d3bcfd65910df18a946574748d361ddd8e989aacde99e8b6bd70`.
