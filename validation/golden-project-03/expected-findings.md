# Expected findings: golden project 03

The golden file for the **conditional-approve** fixture. Project 01 must be rejected,
project 02 must be approved cleanly. This one exercises the third verdict branch: the code
is well built, but its safety rests on runtime facts a static review cannot confirm, so the
correct outcome is **Approve with conditions** — no Critical, no unresolved High, but named
assumptions that must be validated first.

A passing review:

- dispatches the expected lenses and states its skips and the execution mode;
- emits no Critical and no unresolved High;
- flags **none** of the false-positive traps;
- surfaces the conditions below as explicit "Approve with conditions" items, not as
  blockers and not silently assumed away;
- recognizes the strengths.

## Reviewing `schema.prisma`

**Expected dispatch:** data-model, indexing, prisma, scalability, security engaged.
query-performance and migrations skipped for this artifact (no query code or migration in
scope), backend-data-access skipped (no service code). The report must state the skips.

**Required findings:**

| # | Lens | Severity | Evidence anchor | The defect | Grounding |
| --- | --- | --- | --- | --- | --- |
| 1 | data-model | Medium | `Invoice.status` | Free-text status ("open"/"paid"/"void") should be an enum or lookup, exactly like `SubscriptionStatus` already is. | [SQLAP] enumerated domains / [DMMS] |

**Conditions (Approve-with-conditions items, not blockers):**

| # | Lens | Condition to validate |
| --- | --- | --- |
| C1 | security | RLS is actually enforced at runtime: the app connects as a **non-owner** role without `BYPASSRLS`, and sets `app.tenant_id` with `SET LOCAL` per request behind the pooler. The migration enables `FORCE ROW LEVEL SECURITY`, but this wiring is not visible here. |
| C2 | data-model / backend-data-access | The denormalized `Invoice.totalCents` stays consistent because every writer goes through `createInvoice` (which writes it in the same transaction as the line items); confirm no other path mutates line items without updating the total. |
| C3 | scalability | The `UsageEvent` retention/prune job is actually scheduled; the schema only describes it in a comment. |

**Must NOT flag (false-positive traps):**

| Construct | Why it is correct | Lens that might wrongly fire |
| --- | --- | --- |
| `*Cents Int` money columns | Money stored as integer minor units, not float. | data-model |
| `@db.Timestamptz` timestamps | Timezone-aware, correct. | data-model |
| `BigInt` primary keys | Sized for growth; no `int4` exhaustion risk. | scalability |
| `Invoice.totalCents` denormalized | Written in the same transaction as its line items (`createInvoice`), so it cannot drift. | data-model (normalization) |
| `Payment.providerEventId @unique` | Idempotency key; a redelivered webhook is a no-op. | backend-data-access |
| indexed FKs (`tenantId`, `invoiceId`) | Queried and joined on, correctly indexed. | indexing |

**Strengths the review must recognize (at least two):** money as integer cents;
`timestamptz` throughout; `BigInt` PKs on growth tables; `SubscriptionStatus` modeled as an
enum; explicit `onDelete` on every relation; the composite `@@index([tenantId, issuedAt])`
that matches the tenant-scoped list; the payment idempotency key.

**Expected approval decision:** **Approve with conditions** — conditions C1–C3. No Critical
and no unresolved High. Rejecting this, or approving it unconditionally without naming the
RLS-wiring and retention assumptions, is a failure.

## Reviewing `queries.ts`

**Expected dispatch:** query-performance, backend-data-access, prisma engaged, plus security
for the raw query. data-model, indexing, migrations, scalability skipped or only referenced.
The report must state the skips.

**Required findings:** none above Info.

**Must NOT flag (false-positive traps):**

| Construct | Why it is correct | Lens that might wrongly fire |
| --- | --- | --- |
| `revenueByTenant` `$queryRaw` | Tagged template; `tenantId` is a bound parameter, not concatenated. | security |
| module-level `new PrismaClient()` | One shared client and pool, reused. | prisma / backend-data-access |
| `listInvoices` `cursor` | Keyset pagination, not offset. | query-performance |
| `createInvoice` `$transaction` | Invoice, line items, and total written atomically. | backend-data-access |
| `select` on `listInvoices` | Projects only used columns; no over-fetch. | query-performance |

**Strengths:** shared client; keyset pagination; atomic invoice creation; idempotent
payment upsert; projected reads; every query scoped by `tenantId`.

**Expected approval decision:** **Approve.** (The conditions live on the schema/migration.)

## Reviewing `migration.sql`

**Expected dispatch:** migrations engaged, indexing engaged (creates an index), security
engaged (enables RLS). Others skipped. The report must state the skips.

**Required findings:** none above Info.

**Must NOT flag (false-positive traps):**

| Construct | Why it is correct | Lens that might wrongly fire |
| --- | --- | --- |
| `SET lock_timeout` before DDL | Prevents the lock-queue pileup; senior practice. | migrations |
| `CREATE INDEX CONCURRENTLY` | Non-blocking build. | migrations |
| `ENABLE` + `FORCE ROW LEVEL SECURITY` + policy | RLS done correctly; the owner is not exempt. | security |

**Strengths:** the `lock_timeout` guard; the concurrent index; RLS with `FORCE` and a
session-variable policy; the comment naming the non-owner-role and `SET LOCAL` requirements
that the review must carry forward as condition C1.

**Expected approval decision:** **Approve**, with the runtime RLS wiring (C1) carried as the
condition.

## Contract checks (all artifacts)

- Every emitted finding carries the full evidence chain including a Grounding key.
- The conditions are presented as "Approve with conditions" items naming the assumption to
  validate — not as blockers, and not silently ignored.
- No false-positive trap is flagged; inventing a Critical or High here is a failure (the
  restraint constraint from `FRAMEWORK.md` applies in full).
- Per-lens confidence is reported; the RLS and retention conditions are Low/Medium
  confidence by nature, since they depend on runtime facts that cannot be checked statically.
- The final verdict is **Approve with conditions**, and it names conditions C1–C3.
