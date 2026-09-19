# Pre-model compatibility findings for the registered replication

The selected datasets contain 27, 46 and 26 input queries respectively. The
first twenty in each domain register 60 distinct questions and 240 episodes.
Their identities are frozen in `vakra_crossdomain_setup_audit.json`.
All nine source files were downloaded at the registered revision and hashed;
SQLite content matches the official Git object or LFS content hash. The
download manifest remains in `results/third_party/vakra-data/`.

All 99 available reference sequences were replayed through the real MCP
interface on CPU, with the same startup warmup as development. No database
changed. Reference execution errors are 7/27 computer_student, 8/46 cars,
0/26 book_publishing_company. Within the selected twenty-task subsets these
are 5, 2 and 0. They are empty-key count validation incompatibilities, not
model failures, and are not repaired or used to exclude tasks. The model can
still choose another valid operation on such inputs. Raw JSON match counts
are not official evaluator scores and are not interpreted as task correctness.

Independent inspection of question/reference pairs also exposes semantic
conflicts that must be handled before scoring model answers:

- book_publishing_company question `5661cd917583-3c3392e57062` asks for the
  Chief Executive Officer. Its reference filters `Chief Financial Officier`
  and supplies Francisco Chang. A read-only join of employee with jobs for
  `Chief Executive Officer` instead gives Philip Cramer. This is a literal
  role mismatch, not a name-format normalization issue.
- computer_student question `39a28b2592a2-178d76a262a8` asks about advisors of
  student 376, while the reference filters `advisedBy_p_id` to 141. The role
  of each foreign-key column and the correct alternative answer require an
  additional schema-description audit; the conflicting constants are already
  directly observable.
- Some course-count questions have references counting teaching-assignment
  rows in a join. Whether the question means distinct courses must be examined
  separately; a reference count is not automatically a semantic gold label.

These are pre-model findings on the registered pool, not a measured benchmark
error prevalence. They do not justify silently correcting the live environment
or dropping inconvenient tasks. The original frozen prompts and all selected
questions remain intact. Subsequent reporting must separate reference
compatibility, independently checked interpretations, ambiguous questions,
and unsupported conclusions. No official VAKRA judge result is claimed.
