# Hotpot snapshot state-flow pilot v1

Purpose: establish an executable matched model comparison and inspect feasibility
of a narrower measurement question. This eight-task pilot is development, not
confirmation of a new speculative scheduler or a fourth completed paper.

Use all eight frozen pilot IDs in `hotpot_snapshot_selection_v1.json`. The forty
evaluation IDs remain untouched. All 94 previously inspected archive questions
were excluded before the hash-based selection. No answer-dependent replacement.

The grid is eight tasks × two fixed local checkpoints (Qwen3-4B-Instruct-2507,
Qwen2.5-7B-Instruct) × three conditions, totaling 48 episodes:

1. Baseline: authoritative environment actions only.
2. Shared: after each nonterminal authoritative action, run the same action
   through the pinned native `simulate` method on the same state.
3. Isolated: the same simulation with authoritative fields restored afterward;
   preserve only the explicit simulated-observation output slot separately.

Simulation uses the authoritative action, as in the inspected upstream flow.
Only native simulated search invokes the predictor; simulated lookup still
advances the native cursor in the shared condition. Terminal actions are not
simulated. No candidate-action prediction loop, parallel execution, promotion,
commit mechanism or latency-saving claim is included in this pilot.

The predictor and actor use the same checkpoint within an episode, greedy
decoding and the existing native chat-template backend with an empty tool list.
This is an adaptation, not reproduction of the authors' hosted-model setup.
Actor responses use one Search/Lookup/Finish action per generation. Every
episode has eight actor-generation attempts, 512 new tokens per actor call,
100 per prediction call and a 32,768-token input limit without truncation.
Native search prediction retries empty output at most three times. Three
malformed actor outputs stop the episode, and count toward its eight attempts.
Model or tool exceptions retain a failed episode; no answer or output is dropped.
Empty Finish is retained and scored according to the separate offline scorer.

Initial prompts, public candidate passages and task identity match across all
conditions. Agent observations contain only authoritative returns. Guessed
pages do not directly enter that prompt. A shared-state intervention can still
affect later returns. No reference answer or supporting-fact label is deployed.
The fixed snapshot contains all ten distractor contexts and exposes candidate
titles, differing from live full-Wikipedia retrieval. No method infers hidden
answers from evaluation files.

Each checkpoint has two stride shards of four tasks, one visible A40 per worker.
Each task executes all three conditions in order rotated by its original pilot
index modulo three. All model files are checked against the prior fixed-model
manifest before loading. Seed 20260919; no sampled decoding, quantization,
remote model API, new weight download or gradient update.

Retain all actor and predictor input messages, decoded replies, token IDs and
usage, authoritative state before/after, simulated results and post-simulation
state. Audit initial input equality, baseline/isolated trajectory agreement,
same-input generation agreement and shared-condition divergence. Report all
exceptions and failures. Any disagreement between equal-input greedy model
outputs is retained as a determinism limitation, not attributed to state flow.
Offline answer EM/F1 uses the pinned official answer scorer; these pilot results
are not the full benchmark score or a latency comparison. A null effect or
performance floor is an eligible outcome, not a reason to change the denominator.

Deployment waits for the registered `tau-nk-test40-v2` predecessor to finish
successfully and for all GPUs to be idle. It does not restart or modify earlier
experiments. A predecessor failure or the explicit 36-hour waiting bound ends
this registration as failed before launching workers. Four-hour worker deadline;
all outputs and exact source hashes are retained if anything fails. This pilot
does not authorize an automatic full evaluation on the forty reserved tasks.
