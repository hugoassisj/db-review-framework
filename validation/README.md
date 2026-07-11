# Validation

Argus is validated against golden projects, not against any real repository.
A golden project is a small, self-contained, synthetic sample, plus an
`expected-findings.md` that declares what a passing review must (and must not) surface.
This keeps the framework portable and shippable: no real, proprietary schema is ever
committed here.

Three golden projects ship today, exercising all three verdict branches:

- `golden-project-01` seeds known smells. A passing review finds them all and refuses
  to approve.
- `golden-project-02` is clean and well-built, with deliberate traps that look like
  smells but are correct in context. A passing review flags none of them and approves.
  This is the false-positive guard: it proves the reviewer has the restraint to say
  "ship it."
- `golden-project-03` is correct-but-conditional: well built, but its safety rests on
  runtime facts a static review cannot confirm (RLS wiring, a denormalized total's writer,
  a retention job). A passing review approves *with named conditions*, exercising the
  third approval branch.

## Layout

```
validation/
  golden-project-01/       seeded smells (must be rejected)
    schema.prisma          # seeded schema-layer smells
    queries.ts             # seeded query and data-access smells
    migration.sql          # seeded migration-safety smells
    expected-findings.md   # the golden file: what a passing review must find
  golden-project-02/       clean and well-built (must be approved)
    schema.prisma          # correct schema, with false-positive traps
    queries.ts             # correct data access, with false-positive traps
    migration.sql          # a safe migration
    expected-findings.md   # the golden file: findings, traps to NOT flag, verdict
  golden-project-03/       correct-but-conditional (approve with conditions)
    schema.prisma          # well-built multi-tenant billing schema
    queries.ts             # correct, tenant-scoped data access
    migration.sql          # safe migration with lock_timeout + RLS (FORCE)
    expected-findings.md   # the golden file: findings, conditions, traps, verdict
```

## Running the checks

Two layers, deliberately separate.

**Structural checks (deterministic, CI).** `python3 scripts/validate.py` verifies the
manifests, the citation graph, the lens/domain and cross-lens handoff maps, and that the
evals stay bound to the fixtures. It runs no LLM and grades no review.

**Grading the reviews (the LLM output).** The assertions a passing review must satisfy live,
machine-readable, in [`../skills/review/evals/evals.json`](../skills/review/evals/evals.json)
(the [skill-creator](https://github.com/anthropics/claude-plugins-official) schema: `query`,
`files`, `expected_behavior`). Grade them one of three ways:

- **skill-creator (recommended, automated).** `/plugin install skill-creator@claude-plugins-official`,
  then ask it to evaluate the `review` skill. It runs each case in an isolated subagent, grades
  each assertion, and benchmarks with-skill versus without.
- **Local end-to-end.** `python3 scripts/run_evals.py` drives the review over every fixture via
  the Claude CLI and writes transcripts to `skills/review/evals/out/` for you to grade against
  the `expected_behavior` assertions. Needs the `claude` CLI; not run in CI.
- **By hand.** Load the plugin (`claude --plugin-dir /path/to/db-review-framework`) and run each
  fixture, checking the output against its `expected-findings.md`:
   - `/argus:review validation/golden-project-01/schema.prisma`
   - `/argus:review validation/golden-project-01/queries.ts`
   - `/argus:review validation/golden-project-01/migration.sql`
   - `/argus:review validation/golden-project-02/schema.prisma`
   - `/argus:review validation/golden-project-02/queries.ts`
   - `/argus:review validation/golden-project-02/migration.sql`
   - `/argus:review validation/golden-project-03/schema.prisma`
   - `/argus:review validation/golden-project-03/queries.ts`
   - `/argus:review validation/golden-project-03/migration.sql`

A `golden-project-01` (reject) run passes when:

- it dispatches the lenses the golden file expects for that artifact, and names which
  it skipped and why;
- it surfaces every finding listed as required in `expected-findings.md`;
- every emitted finding satisfies the evidence gate (no bare assertions);
- it violates none of the negative constraints;
- it reports per-lens confidence, includes at least one strength, synthesizes any
  cross-lens trade-off, and ends with an approval decision that does not approve while
  a Critical is open.

A `golden-project-02` (approve) run passes when:

- it dispatches the expected lenses and still names its skips;
- it emits no finding above Info or Low, and in particular flags none of the items in
  the "must NOT flag" table (the false-positive traps);
- it recognizes the listed strengths;
- it ends in Approve, or Approve with conditions limited to the conditions the golden
  file allows.

A `golden-project-03` (approve-with-conditions) run passes when:

- it dispatches the expected lenses and names its skips and the execution mode;
- it emits no Critical and no unresolved High, and flags none of the false-positive traps
  (integer-cents money, `timestamptz`, `BigInt` PKs, the transactionally-written total);
- it surfaces the RLS-wiring, denormalized-total-consistency, and retention assumptions as
  explicit conditions, not as blockers and not silently assumed;
- it ends in Approve with conditions, naming those conditions.

The golden file lists required findings (must appear) separately from bonus findings
(good to catch, not required), so grading tolerates a reviewer that finds more without
failing on strictness.

## Adding a golden project

Create `golden-project-NN/` for a new domain (for example ecommerce, fintech,
healthcare). Seed a spread of smells, keep it synthetic, and write the
`expected-findings.md` first, so the fixture is built to prove specific behavior.
Adding a benchmark never requires changing the framework.
