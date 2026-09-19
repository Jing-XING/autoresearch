# Complete known-task checkpoint extension

The 120-episode Qwen3-30B-A3B-Instruct-2507 extension completed all six workers
with exit code zero. The raw export has 156 members, 1,086,711 bytes and SHA-256
`c3681bff3c71901f2cea9d5d3d85d94db3364cf97847643c97ab462fdae0b9ac`.
It is retained locally as `results/remote/vakra-qwen30b-v1-complete.zip`.
CRC, hash and safe extraction checks passed. The extracted run root is
`results/remote/vakra-qwen30b-v1-complete/runs/vakra-qwen30b-v1`.

The complete-grid audit verifies the registered 120 executions, sixty paired
initial inputs, exact source/model hashes, preparation files and all worker
exit statuses. `vakra_qwen30b_complete_grid_v1.json` is execution evidence,
not an answer score. `vakra_qwen30b_answer_annotations_v1.json` records the
single unblinded assistant's complete review of all 120 answer records against
the existing cards. No official scoring or independent human review occurred.
`vakra_qwen30b_answer_summary_v1.json` joins all annotations back to immutable
raw hashes and the unchanged interpretation mask.

| Domain | Scored per arm | Original | Coverage reminder |
|---|---:|---:|---:|
| computer_student | 17 | 5 | 6 |
| cars | 18 | 13 | 14 |
| book_publishing_company | 20 | 17 | 18 |
| Total | 55 | 35 | 38 |

Across all executions: 73 correct, 35 incorrect, ten ambiguous and two absent
answers. The absent original car answers remain unsuccessful in the fixed
55-task denominator. Five gains and two losses give +5.45 percentage points.
The separately computed 10,000-draw domain-stratified paired interval is
[-3.64, 14.55] points, conditional on these domains and fixed labels.

Important semantic qualifications retained in individual reasons:

- Publishing 007 contains every requested distinct title/YTD pair with
  redundant coauthor rows; no contradictory pair is added. This uses the
  same answer interpretation as the earlier checkpoint audit.
- Publishing 012 under the reminder returns the reference price and title,
  but its individual-sale reasoning does not implement the aggregate-sales
  reference. Correct answer agreement is not a grounding pass.
- Publishing 016 and 019 retain the pre-existing specified interpretations.
  There is no post-prediction expansion of the ambiguous-task mask.
- Student 003, 011, 014 and cars 012, 019 retain the fixed ambiguous label.

Reproduction from the repository root, using new output filenames:

```text
python scripts/analyze_vakra_registered_grid.py --kind capacity --root results/remote/vakra-qwen30b-v1-complete/runs/vakra-qwen30b-v1 --archive results/deploy/vakra-qwen30b-v1.zip --output results/capacity-grid-check.json
python scripts/summarize_vakra_registered_answers.py --root results/remote/vakra-qwen30b-v1-complete/runs/vakra-qwen30b-v1 --summary research/evidence/vakra_qwen30b_complete_grid_v1.json --annotations research/evidence/vakra_qwen30b_answer_annotations_v1.json --output results/capacity-answer-check.json
```

The scripts validate records and aggregate judgments; they do not independently
reproduce semantic labels. Raw archives and checkpoints are ignored by Git and
must be provided separately. The complete-grid file pins execution inputs and
the deployment archive. The answer summary additionally records its aggregation
source hashes. The later archive allow-list amendment permits the disclosed
zero-episode expansion restart and reproduces the capacity grid summary exactly.
