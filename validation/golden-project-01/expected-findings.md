# Expected findings: golden project 01

The golden file for this fixture. A passing review surfaces every **required** finding
for the artifact under review, dispatches the expected lenses, and honors the contract
(evidence gate, negative constraints, per-lens confidence, an approval decision that
does not approve while a Critical is open). Bonus findings are welcome and do not affect
pass/fail.

Severities below are the expected floor; a reviewer may justify a higher severity with
stated assumptions.

## Reviewing `schema.prisma`

**Expected dispatch:** data-model, indexing, prisma, scalability, security engaged.
query-performance and migrations skipped (no query code or migration in scope), backend-
data-access skipped. The report must state the skips.

**Required findings:**

| # | Lens | Severity | Evidence anchor | The defect |
| --- | --- | --- | --- | --- |
| 1 | security | Critical | `User.password` | Plaintext password; must be a salted, slow hash. |
| 2 | security | High | `ApiCredential.apiSecret` | Plaintext secret; must be encrypted at rest. |
| 3 | data-model | High | `User.email` | Login identity is nullable and not unique; should be `String @unique`. |
| 4 | indexing | High | `Order.@@index([createdAt, customerId])` | Wrong composite order for `WHERE customerId = ? ORDER BY createdAt DESC`; should lead with `customerId`. |
| 5 | indexing | Medium | `Comment.postId` | Foreign key filtered/joined on but not indexed; needs `@@index([postId])`. |
| 6 | data-model | Medium | `Post.tags` | Comma-separated tags (jaywalking); should be modeled as rows + join table. |
| 7 | data-model | Medium | `Order.status` | Free-text status; should be an enum or lookup. |
| 8 | scalability | Medium | `Event` model | Append-only with no retention/partition plan; also no index on `createdAt`. |
| 9 | scalability | Medium | `Artifact.content` | Large binary stored in-row; prefer object storage with a reference. |
| 10 | prisma | Low | `Order.customer` relation | No `onDelete` referential action stated. |

**Bonus:** `Order.metadata Json` flagged for review (is any queried field hiding in it);
implicit vs explicit relation guidance where applicable.

**Expected approval decision:** Do not approve. Blockers: finding 1 (Critical), and the
High findings (2, 3, 4) unless explicitly justified.

## Reviewing `queries.ts`

**Expected dispatch:** query-performance, backend-data-access, prisma engaged (plus
security for the raw query). data-model, indexing, migrations, scalability skipped or
only referenced. The report must state the skips.

**Required findings:**

| # | Lens | Severity | Evidence anchor | The defect |
| --- | --- | --- | --- | --- |
| 1 | security | Critical | `findByEmailUnsafe` `$queryRawUnsafe` | SQL injection via string interpolation; use the tagged-template `$queryRaw` or the typed client. |
| 2 | backend-data-access | High | `debit` | Read-modify-write lost-update race; use an atomic guarded `updateMany` or optimistic lock. |
| 3 | query-performance | High | `listPostAuthors` loop | N+1; fetch authors via a relation `select` in one query. |
| 4 | prisma / backend-data-access | High | `new PrismaClient()` in `listPostAuthors` | New client/pool per call; use one shared instance. |
| 5 | query-performance | Medium | `usersWithOrders` `Promise.all(map)` | Query fan-out; batch with `where: { customerId: { in } }`. |
| 6 | query-performance | Medium | `userDashboard` `include: { orders: true }` | Over-fetch; use `select` for the used fields. |
| 7 | query-performance | Medium | `eventPage` `skip: page * 20` | Offset pagination; use keyset/cursor for a growing list. |

**Expected approval decision:** Do not approve. Blockers: finding 1 (Critical) and the
High findings.

## Reviewing `migration.sql`

**Expected dispatch:** migrations engaged, indexing engaged (the file creates an index),
scalability referenced (the NOT NULL backfill and dropped column touch a populated
table). Others skipped. The report must state the skips.

**Required findings:**

| # | Lens | Severity | Evidence anchor | The defect |
| --- | --- | --- | --- | --- |
| 1 | migrations | High | `CREATE INDEX idx_orders_customer` | Blocking build on a live table; use `CREATE INDEX CONCURRENTLY`. |
| 2 | migrations | High | `ADD COLUMN country text NOT NULL` | Validates all rows under an exclusive lock; add nullable, backfill batched, enforce `NOT VALID` then `VALIDATE`. |
| 3 | migrations | High | `RENAME COLUMN password TO password_hash` | Flag-day rename breaks running old code; use expand/contract. |
| 4 | migrations | Medium | `DROP COLUMN metadata` | Destructive, irreversible, no deprecation period. |

**Expected approval decision:** Do not approve. Blockers: findings 1 to 3 (High)
unless a maintenance window and compatible rollout are explicitly stated.

## Contract checks (all artifacts)

- Every emitted finding carries the full evidence chain (finding, evidence, reasoning,
  impact now and at scale, recommendation, trade-offs, confidence).
- No negative-constraint violation (for example: index recommendations name the query
  they serve; no approval while a Critical is open).
- Per-lens confidence is reported with a reason (static-only here, since no live
  database is attached, so confidence is Medium for size-dependent findings and High for
  size-independent ones like the plaintext password and the injection).
- At least one strength is listed and at least one cross-lens trade-off is synthesized
  where lenses interact (for example the `Order.metadata` Json flexibility vs
  queryability, or denormalization vs the composite index).
