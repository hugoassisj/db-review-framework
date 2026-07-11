# Validation

Argus is validated against golden projects, not against any real repository.
A golden project is a small, self-contained, synthetic sample, plus an
`expected-findings.md` that declares what a passing review must (and must not) surface.
This keeps the framework portable and shippable: no real, proprietary schema is ever
committed here.

Two golden projects ship today, and together they exercise both halves of the job:

- `golden-project-01` seeds known smells. A passing review finds them all and refuses
  to approve.
- `golden-project-02` is clean and well-built, with deliberate traps that look like
  smells but are correct in context. A passing review flags none of them and approves.
  This is the false-positive guard: it proves the reviewer has the restraint to say
  "ship it," and it exercises the approval decision branches.

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
```

## Running the harness

1. Load the plugin without installing:
   `claude --plugin-dir /path/to/db-review-framework`
2. Run the review in audit mode against a fixture and check the output against the
   golden file:
   - `/argus:review validation/golden-project-01/schema.prisma`
   - `/argus:review validation/golden-project-01/queries.ts`
   - `/argus:review validation/golden-project-01/migration.sql`
   - `/argus:review validation/golden-project-02/schema.prisma`
   - `/argus:review validation/golden-project-02/queries.ts`
   - `/argus:review validation/golden-project-02/migration.sql`

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

The golden file lists required findings (must appear) separately from bonus findings
(good to catch, not required), so the harness tolerates a reviewer that finds more
without failing on strictness.

## Adding a golden project

Create `golden-project-NN/` for a new domain (for example ecommerce, fintech,
healthcare). Seed a spread of smells, keep it synthetic, and write the
`expected-findings.md` first, so the fixture is built to prove specific behavior.
Adding a benchmark never requires changing the framework.
