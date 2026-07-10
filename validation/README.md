# Validation

The framework is validated against golden projects, not against any real repository.
A golden project is a small, self-contained, synthetic sample that seeds known smells
across the lenses, plus an `expected-findings.md` that declares the findings a passing
review must surface. This keeps the framework portable and shippable: no real,
proprietary schema is ever committed here.

## Layout

```
validation/
  golden-project-NN/
    schema.prisma          # seeded schema-layer smells
    queries.ts             # seeded query and data-access smells
    migration.sql          # seeded migration-safety smells
    expected-findings.md   # the golden file: what a passing review must find
```

## Running the harness

1. Load the plugin without installing:
   `claude --plugin-dir /path/to/db-review-framework`
2. Run the review in audit mode against a fixture and check the output against the
   golden file:
   - `/db-review:review validation/golden-project-01/schema.prisma`
   - `/db-review:review validation/golden-project-01/queries.ts`
   - `/db-review:review validation/golden-project-01/migration.sql`

A run passes when:

- it dispatches the lenses the golden file expects for that artifact, and names which
  it skipped and why;
- it surfaces every finding listed as required in `expected-findings.md`;
- every emitted finding satisfies the evidence gate (no bare assertions);
- it violates none of the negative constraints;
- it reports per-lens confidence, includes at least one strength, synthesizes any
  cross-lens trade-off, and ends with an approval decision that does not approve while
  a Critical is open.

The golden file lists required findings (must appear) separately from bonus findings
(good to catch, not required), so the harness tolerates a reviewer that finds more
without failing on strictness.

## Adding a golden project

Create `golden-project-NN/` for a new domain (for example ecommerce, fintech,
healthcare). Seed a spread of smells, keep it synthetic, and write the
`expected-findings.md` first, so the fixture is built to prove specific behavior.
Adding a benchmark never requires changing the framework.
