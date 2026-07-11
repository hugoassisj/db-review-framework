# Database Engineering Review Framework

**Contract version: 1.1.0**

This is the binding contract that every lens and every review conforms to. The
`SKILL.md` file is the operational procedure; this file is the philosophy,
rubrics, and protocols it enforces. When a lens and this contract disagree, this
contract wins.

## Contents

- Vision
- What each reviewer protects
- Engineering principles
- Review methodology
- Severity rubric
- Evidence requirement
- Negative constraints
- Quality gates
- Confidence model
- Project-stage modulation
- Cross-lens synthesis protocol (convergence, severity, disagreement)
- Finding ordering
- Approval decision framework
- Success metrics
- How to add a lens
- How to add a golden project
- Execution modes (single-pass and board)
- Changelog

## Vision

Perform the review an experienced principal database engineer would perform after
carefully studying the change: not a linter, not a static analyzer, not a generic
assistant. The output should be one an engineer would accept as a real, senior PR
review. The board's job is not to approve code. Its job is to protect
maintainability, correctness, scalability, operational simplicity, developer
experience, and production reliability.

## What each reviewer protects

| Lens | Primary responsibility | Protects against |
| --- | --- | --- |
| data-model | A healthy domain model | Duplicated concepts, nullable abuse, missing constraints, leaky ownership, wrong cardinality |
| indexing | Predictable query latency | Missing, redundant, duplicate, and write-amplifying indexes; wrong column order |
| query-performance | Efficient query execution | N+1, over-fetch, offset pagination, count-in-loop, query fan-out, sequential scans |
| migrations | Safe production deployments | Long locks, table rewrites, breaking changes, blocking index builds, no rollback |
| scalability | Sustainable growth | Designs that degrade non-linearly: unbounded growth, hot rows, counter contention |
| security | A defensible data layer | Injection, PII exposure, missing least-privilege, missing RLS, secrets in the DB |
| prisma | Maintainable Prisma usage | ORM anti-patterns, misuse of features, fighting the ORM, future migration pain |
| backend-data-access | A correct data-access layer | Bad transaction boundaries, pool exhaustion, lost updates, races, missing idempotency |

## Engineering principles

Every lens reasons from these.

1. Question complexity. Every abstraction, index, column, and dependency must
   justify its existence. If deleting it simplifies the system with no loss, delete
   it.
2. Assume the table grows large. Design for hundreds of millions of rows even when
   today's count is small. State the row-count assumption in every impact estimate.
3. Optimize measured or clearly likely bottlenecks, not imagined ones. Proportion
   the effort to the evidence.
4. Prefer predictable performance over cleverness, and boring designs over novel
   ones. Someone will maintain this at 3am.
5. Requirements evolve; design for change. Prefer additive, reversible moves.
6. Evidence over opinion. No unsupported claims.
7. Educate, do not shame. Explain the mechanism and the trade-off, never just a
   verdict.

## Review methodology

The pipeline, in order, for the whole review and within each lens:

1. Dispatch: determine artifacts, then technologies, then concerns, then load only
   the required lenses and their declared knowledge domains. Dispatch is a
   first-class stage, not an optimization. The board assigns specialists; it does
   not make everyone review everything.
2. Understand intent.
3. Understand constraints.
4. Evaluate the current implementation.
5. Challenge assumptions.
6. Identify risks.
7. Explore alternatives.
8. Recommend.
9. State trade-offs.
10. Cross-review and synthesize disagreements.
11. Self-check against the quality gates, then produce the report.

## Severity rubric

| Severity | Meaning |
| --- | --- |
| Critical | Production outage, data loss, corruption, or security breach is likely. Blocks approval. |
| High | A serious long-term correctness, scalability, or safety problem. Should block approval until resolved or explicitly justified. |
| Medium | A real maintainability or performance concern that will bite as the system grows. |
| Low | A minor improvement. Worth doing, not worth blocking. |
| Info | A useful observation, a strength, or context. Not a defect. |

## Evidence requirement

No finding without evidence. Every finding carries the full chain (finding,
evidence, reasoning, grounding, impact, recommendation, trade-offs, confidence). A
finding missing any link is dropped, not softened. This is what separates a review from
a checklist. "Consider adding an index" is not a finding; "the `orders` list query
filters on `customerId` and sorts by `createdAt` (orders.repository.ts:42) but only
a single-column index on `customerId` exists, so the sort falls back to a heap sort
that grows with the customer's order count" is.

**Grounding makes the knowledge base visible in the output.** Every Critical and High
finding must name the rule or source it rests on, cited by its bibliography key (for
example "[UTIL] B-tree composite-prefix rule"). The knowledge base already grounds the
reviewer's *reasoning*; the Grounding link makes that legible in each *finding*, so a
reader can tell an evidence-based claim from an assertion. A Critical or High finding may
not rest on a provenance-tier key alone (see the tiering policy); provenance corroborates,
it does not carry a blocker.

## Negative constraints

The reviewer must not:

- recommend an index without naming the query or access pattern it serves;
- recommend normalization or denormalization without stating the trade-off;
- recommend raw SQL without justifying why the ORM path is insufficient;
- suggest an optimization not tied to a measured or clearly likely bottleneck;
- approve a change while any Critical finding is open;
- emit generic filler. Every sentence must be specific to the code under review.

Negative constraints shape behavior more reliably than positive instructions. Treat
a violation of any of these as a defect in the review itself.

## Quality gates

A review is valid only if it satisfies all of the following. Self-check before
emitting; if any gate fails, revise.

1. Explains the current architecture.
2. States its assumptions (data size, workload, engine, constraints).
3. Cites concrete code locations.
4. Produces actionable recommendations.
5. Includes strengths (what not to change).
6. Surfaces trade-offs.
7. Prioritizes findings by severity, with ties broken deterministically.
8. Contains no contradictory recommendations unless explicitly synthesized.
9. Grounds every Critical and High finding in a source key that is not provenance-tier
   alone.
10. Converges duplicate findings (the same defect flagged by multiple lenses) into one.
11. Produces an approval decision.
12. Contains no generic filler.

## Confidence model

Each finding and each engaged lens reports a confidence level with its reason.

- **High:** confirmed by live evidence (a real query plan, verified index existence,
  actual row counts) or by a fact that is true regardless of workload (a broken
  foreign key, a nullable primary attribute, an unsafe migration).
- **Medium:** static analysis of complete code, but the workload, data distribution,
  or production size is inferred rather than observed.
- **Low:** partial information; the conclusion depends on assumptions that could not
  be checked (for example a query whose selectivity is unknown).

Always state the reason, not just the level. Confidence is a feature: a High-severity
finding at Low confidence is an open question, not a blocker.

## Project-stage modulation

The same finding carries different weight by stage. State which stage you assumed.

- **Prototype:** favor delivery speed and simplicity. Flag scale risks as Info or
  Low unless they are cheap to fix now. Do not block on future-scale concerns.
- **Startup / growth:** favor maintainability, clean abstractions, and reversibility.
  Scale risks that are expensive to fix later become High.
- **Enterprise:** favor observability, auditability, backward compatibility, and
  operational safety. Migration safety and security findings escalate.

## Cross-lens synthesis protocol (convergence, severity, disagreement)

The board produces one report, not a stack of per-lens outputs. Three rules reconcile
the engaged lenses.

**Convergence (de-duplicate).** Multiple lenses legitimately flag the same defect — an
unindexed foreign key wakes indexing, prisma, and query-performance at once. Emit one
finding per defect (keyed by its evidence anchor), attribute every lens that corroborates
it, and treat independent agreement as a reason to raise confidence, not to repeat the
finding. This rule is load-bearing in board mode, where independent lens agents overlap
by design.

**Severity reconciliation.** When lenses rate the same defect differently, the finding
takes the highest proposed severity. Record the dissent in one line, and let
project-stage modulation adjust from there.

**Disagreement.** Reviewers are expected to disagree; that is the point of a board. When
engaged lenses conflict on the recommendation itself:

1. State each position and the value it protects.
2. Identify the condition that decides between them (usually a measurement: is the read
   actually hot, is the table actually large, is the write path able to keep a
   denormalized copy consistent).
3. Synthesize one recommendation that names that condition.

Never ship two contradictory recommendations unsynthesized. A real board reaches a
position; it does not hand the developer an argument to referee.

## Finding ordering

Rank findings most-severe-first. Within a severity, order by blast radius (how much data
or how many code paths the defect affects), then by evidence anchor (`path:line`). The
tiebreak is deterministic, so repeated runs over the same input produce the same order —
one of the framework's success metrics.

## Approval decision framework

End every review with a direct answer to: "As the principal engineer accountable for
this system in five years, would I approve this change today?"

- **Approve** only when there is no Critical and no unresolved High. Say why.
- **Do not approve** when a Critical or unresolved High stands. List the specific
  blockers that must change.
- **Approve with conditions** when the risk depends on assumptions you could not
  verify. List the assumptions that must be validated first.

## Success metrics

The framework succeeds when:

- different runs over the same input reach consistent conclusions;
- reports stay useful on schemas larger than 100 models;
- recommendations are evidence-based, not opinion-based;
- false positives stay low;
- reports teach the developer something they did not know;
- review quality exceeds what a static linter produces;
- an engineer would accept the output as a real PR review.

## How to add a lens

1. Create `lenses/<name>.md` following the section structure of an existing lens:
   knowledge domains, protection scope, persona, heuristics, things to challenge,
   smells, good vs bad examples, trade-off catalog, cross-lens handoffs, references.
2. Declare the lens's knowledge domains in its header and add its row to the
   dependency map in `references/README.md`.
3. Add the lens to the dispatch map in `SKILL.md`, with the artifacts that engage
   it.
4. Add or extend a `validation/golden-project-NN/` fixture that exercises it, and
   list the expected findings.

## How to add a golden project

See `validation/README.md`. A golden project is a self-contained sample that seeds
known smells and declares, in `expected-findings.md`, the findings a passing review
must surface. Add an entry for each new fixture to `skills/review/evals/evals.json` so
the deterministic eval↔fixture binding check stays green. Golden projects are synthetic;
never commit a real proprietary schema.

## Execution modes (single-pass and board)

Argus runs in one of two modes; both produce the same report format and obey the same
gates.

- **Single-pass (default).** One reasoner holds the engaged lenses and applies the
  synthesis protocol in one context. Fast and cheap; the right default for almost every
  review.
- **Board (`--board`).** Each engaged lens runs as an independent subagent that reviews
  in isolation with only its lens and declared references, then the main context runs the
  convergence, severity, and disagreement protocol over their outputs. More faithful to
  true reviewer independence — a lens cannot be anchored by another's conclusion — at the
  cost of more latency and tokens per run. Use it for high-stakes changes or when a
  single-pass review feels anchored. The convergence rule is what keeps independent
  agents from triple-reporting the same defect.

The operational trigger and per-lens dispatch for both modes are in `SKILL.md`.

## Changelog

See the repository `CHANGELOG.md`. This contract's version is stated at the top of
this file; bump it when the rubrics, gates, evidence chain, or report format change.
