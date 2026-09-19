# Byte identity of research inputs and evidence

Experiment manifests refer to exact file bytes, not a normalized JSON value.
The repository's `.gitattributes` therefore disables Git line-ending conversion
for JSON, JSONL and Python files. Keep these attributes when checking out on
Windows or Linux. Do not reformat frozen cards, registrations or result files
before validating their recorded hashes.

The NK target protocol Markdown file is explicitly covered as well because
its registration pins the protocol's exact bytes. Other prose documents are
not implicitly assumed to have byte-stable line endings.

A 2026-09-19 audit found 86 differences between local tracked-file bytes and
commit `3f4554b`, all attributable solely to CRLF/LF conversion. This could make
a Linux checkout fail a hash check even though the JSON data were identical.
The repair saves the existing local bytes without changing any experimental
input, selection, label, model output or running deployment. After re-staging,
all 218 checked JSON/Python files matched their index blobs. Four representative
files were also actually exported with both `core.autocrlf=true` and `false`;
all eight comparisons matched the original local bytes.

`evidence/git_exact_byte_reproducibility_v1.json` records the before/after audit,
all 86 differing paths and hashes, and the actual checkout checks. This is a
storage-format repair, not a repeat of the scientific experiments. Earlier
commits retain their original Git normalization and are not silently rewritten.
Previously created deployment/run archives retain their own exact bytes and
hashes; they are not reconstructed from a differently normalized source tree.

To audit a later checkout from the repository root:

```text
python scripts/audit_git_byte_identity.py --tree HEAD --output results/git-byte-check.json
```

The command compares every tracked JSON/JSONL/Python file with the requested
Git tree and reports any mismatch. Intentional uncommitted edits will appear
as mismatches too. This check does not fetch ignored raw result archives,
reproduce model inference, validate semantic answer labels or establish that
a manuscript is ready for submission.
