# Native VAKRA development: eight real model episodes

This is an interface and failure audit, not an official benchmark score or
independent replication of the memory intervention. No memory treatment ran.
The fixed first four public world-train queries were selected before model
outcomes. Official MCP tools and system-prompt method were used with the
documented native local model adapter and startup universe switch.

Eight registered episodes completed across two checkpoints. All four worker
processes exited zero. Qwen2.5 produced four final responses and eight tool
error responses; Qwen3 produced three final responses and one retained CUDA
OOM. Qwen2.5 also generated one incomplete tool-call block before recovering.
An agent_finished termination is not an answer correctness score.

## Trace-level observations

1. **Five English-official-language countries.** Both final responses name
   the five countries in the reference answer. Qwen2.5 repeatedly passes a
   handle or string to truncate, whose schema requires a list; six such calls
   return validation errors. It eventually reads a valid getter result.
2. **Cities in England.** Qwen3 filters the City data to 71 rows and answers
   71, matching the reference. Qwen2.5 counts all 4,079 rows and says it cannot
   determine the England count. A valid tool call computes the wrong scope.
3. **Languages in Turkmenistan.** The database and reference contain Kazakh,
   Russian, Turkmenian and Uzbek. Qwen3 filters correctly to four records but
   reads only the peek's first three values and states there are three
   languages, omitting Uzbek. The peek explicitly contains num_records=4.
   Qwen2.5 gives only Turkmenian after reading an unfiltered column. Neither
   answer is complete. This is qualitative inspection, not an external judge.
4. **Highest-life-expectancy country's capital and official language.** Qwen3
   requests the entire life-expectancy column from a 30,670-row join. Its
   184,020-character tool result is retained verbatim; the next generation
   fails with CUDA OOM. Qwen2.5 sorts and filters to Andorra but does not filter
   official-language status, listing four languages instead of Catalan.
   The reference encodes capital as numeric ID 55.0, while the query asks for
   a city; the City database maps ID 55 to Andorra la Vella. This representation
   issue must remain distinct from the model's language-selection error.

The getter-induced OOM and peek-induced omission expose opposite risks of
returning full columns and compact previews. They do not establish a new
method, a causal effect of a revised interface, or a failure rate beyond these
four development queries. Existing research already studies output truncation,
pagination and unsupported final claims; a simple reminder or compression
wrapper cannot be represented as novel without stronger differentiation.

## Provenance

Summary: `vakra_native_first4_v1_summary.json`. Raw input/output, actual native
tokens, MCP results, schemas, manifests and process logs remain in
`results/remote/vakra-native-first4-v1`.
Archive: 169,820 bytes, 27 files, SHA256
`1c3bba5747195ef6e16d1c67271e7e6a997f8cc65773a61ec87ee27a8c659768`.
No old result was overwritten or failure discarded.

## Directly checked adjacent work (2026-09-19)

- [Agents Don't Paginate](https://arxiv.org/abs/2608.26130) studies first-chunk
  selection and a single-turn file-localization probe. It already identifies
  agents' failure to request later chunks. Its abstract reports that improved
  first-item rank does not yield a consistent downstream gain.
- [Fabrication After Tool Failure](https://arxiv.org/abs/2609.14758) studies
  unsupported answers after unusable tool payloads and an explicit retrieval
  status instruction. A generic missing-evidence status prompt overlaps with
  this prior work.
- [How Good Are LLMs at Processing Tool Outputs?](https://aclanthology.org/2026.eacl-long.134/)
  evaluates structured tool-output processing across fifteen models and
  several prompting approaches. Tool-output reasoning is an established
  research problem, not a novel topic by itself.

These descriptions are based on the primary landing-page abstracts. Full
method and artifact comparison remains necessary before claiming novelty.
