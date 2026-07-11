# Expected findings: golden project 02

The golden file for the approve-case fixture. Golden project 01 proves Argus finds real
smells and refuses to approve. This one proves the opposite half of the job: on clean,
well-built code Argus stays quiet, flags none of the deliberate traps, recognizes the
strengths, and approves.

A passing review, for each artifact:

- dispatches the expected lenses and states its skips;
- emits nothing above **Info** or **Low** severity;
- flags **none** of the items in the "Must NOT flag" table (those are false-positive
  traps: constructs that look like smells but are correct in context);
- names at least the listed strengths;
- ends in **Approve**, or **Approve with conditions** limited to the conditions allowed
  below.

Inventing a finding to look useful is itself a failure here. The negative constraint
"premature optimization is a finding against the reviewer" applies in full.

## Reviewing `schema.prisma`

**Expected dispatch:** data-model, indexing, prisma, scalability, security engaged.
query-performance and migrations skipped (no query code or migration in scope),
backend-data-access skipped (no service code). The report must state the skips.

**Required observations (Info only, non-blocking):**

| # | Lens | Severity | Evidence anchor | The observation |
| --- | --- | --- | --- | --- |
| 1 | scalability | Info | `Event` model | Retention is described in a comment but cannot be verified from the schema. Approval is conditional on the prune job actually being scheduled. |

Any finding above Info on this artifact is a failure unless it is a genuine defect the
fixture did not intend (report it as a bonus, with full evidence).

**Must NOT flag (false-positive traps):**

| Construct | Why it is correct | Lens that might wrongly fire |
| --- | --- | --- |
| `Order.totalCents` denormalized | A cached sum of the line items, written in the same transaction as those items (`createOrder` in `queries.ts`), so it cannot drift. | data-model (normalization) |
| `Order.metadata Json` | Opaque payment-provider payload; nothing is ever filtered or sorted on a nested field, so it does not need to be promoted to columns. | data-model |
| `Country` with only its PK | A ~250-row static lookup; the primary key is the only index it needs, and nothing filters on `name`. Adding an index would be write cost for no read. | indexing |

**Strengths the review must recognize (at least two):** `User.email` is `@unique` and
required; the credential is `passwordHash`, not a plaintext password; `Order.status` is
an enum; every relation states an explicit `onDelete`; the composite
`@@index([customerId, createdAt(sort: Desc)])` leads with the equality column and matches
the access pattern; the country and line-item FKs are indexed because they are queried;
`Event.createdAt` is indexed for the prune and time-range reads.

**Expected approval decision:** **Approve with conditions.** The only allowed condition
is confirming the `Event` retention job is scheduled. Approving unconditionally without
noting the retention assumption is acceptable only if the reviewer states it assumed the
job exists.

## Reviewing `queries.ts`

**Expected dispatch:** query-performance, backend-data-access, prisma engaged, plus
security for the raw query. data-model, indexing, migrations, scalability skipped or only
referenced. The report must state the skips.

**Required findings:** none. A passing review emits nothing above Info here.

**Must NOT flag (false-positive traps):**

| Construct | Why it is correct | Lens that might wrongly fire |
| --- | --- | --- |
| `ordersByCountry` `$queryRaw` | A tagged template; `country` is bound as a parameter, not concatenated into the SQL string, so it is not injectable. | security (injection) |
| `debit` `updateMany` with `balanceCents: { gte: cents }` | The balance check and decrement are one atomic statement; concurrent debits cannot both pass and overdraw. No lost-update race. | backend-data-access |
| module-level `new PrismaClient()` | One shared client and pool for the process, reused across calls, not created per request. | prisma / backend-data-access |
| `eventPage` with `cursor` | Keyset pagination that seeks to the boundary; not offset pagination. | query-performance |

**Strengths the review must recognize (at least two):** single shared client; author
fetched via a relation `select` in one query (no N+1); `select` limited to used columns
(no over-fetch); batched `in` query instead of fan-out; keyset pagination; atomic guarded
debit; the order total computed and persisted in one transaction with its line items.

**Expected approval decision:** **Approve.**

## Reviewing `migration.sql`

**Expected dispatch:** migrations engaged, indexing engaged (the file creates an index),
scalability referenced (the backfill touches a populated table). Others skipped. The
report must state the skips.

**Required findings:** none. A passing review emits nothing above Info here.

**Must NOT flag (false-positive traps):**

| Construct | Why it is correct | Lens that might wrongly fire |
| --- | --- | --- |
| `CREATE INDEX CONCURRENTLY` | Builds without blocking writes, and the comment notes it runs in its own migration outside a transaction block. | migrations |
| `ADD COLUMN "countryCode" text` (nullable) then `NOT VALID` + `VALIDATE CONSTRAINT` | Avoids the full-table rewrite and long lock of a direct `NOT NULL` add; the constraint is validated without blocking writes. | migrations |
| `ADD COLUMN "displayName"` alongside the old `name` | Expand/contract rename: dual-write now, backfill and drop the old column in a later migration. No flag-day break. | migrations |

**Strengths the review must recognize (at least two):** non-blocking index build; the
add-nullable then validate-separately pattern; the batched out-of-band backfill note;
expand/contract instead of an in-place rename.

**Expected approval decision:** **Approve.**

## Contract checks (all artifacts)

- Every emitted observation, even at Info, still carries the evidence chain (finding,
  evidence, reasoning, impact, recommendation where applicable, confidence).
- No invented findings. The review does not manufacture a Medium or High to look
  thorough. Restraint on clean code is the behavior under test.
- Per-lens confidence is reported with a reason. It is High for size-independent
  correctness (the parameterized query, the atomic debit, the composite index order) and
  may be Medium where an impact estimate would need production row counts.
- At least one strength is named per artifact.
- The approval decision is present, and it approves because no Critical and no unresolved
  High finding is open.
