# Example review

A full, worked Argus review of [`validation/golden-project-01/schema.prisma`](../validation/golden-project-01/schema.prisma),
run in audit mode. It shows the analytical approach end to end — dispatch, the evidence chain
with grounding, cross-lens synthesis, and a real verdict — not a single finding. This is the
output a passing review must produce; the fixture's [`expected-findings.md`](../validation/golden-project-01/expected-findings.md)
is the golden file it is graded against.

> The schema is a deliberately flawed test fixture. In a real review the same format applies
> to your actual diff.

---

## Executive summary

This schema defines a small commerce/content domain (users, orders, posts, comments, an event
stream, and credentials). It ships two credential-storage defects that are outright unsafe —
a plaintext `password` and a plaintext `apiSecret` — plus a login identity that is nullable
and non-unique, and a composite index that cannot serve the query it exists for. The
event/artifact tables encode growth problems that are cheap now and expensive later.
**Execution mode: single-pass. Posture: Do not approve** — one Critical and three High
findings stand.

## Architecture understanding

`User` owns `Order` and `Post`; `Post` owns `Comment`; `Order` carries a denormalized
`totalCents` and an opaque `metadata` JSON. `Event` is an append-only stream keyed by
`BigInt`. `Artifact` stores a binary blob in-row. `ApiCredential` stores a provider secret.
The access pattern implied by `Order.@@index([createdAt, customerId])` is "one customer's
orders, newest first."

## Assumptions

PostgreSQL (from the datasource). No production row counts or query plans are attached, so
size-dependent impacts are reasoned, not measured; confidence is set accordingly. Stage
assumed **startup/growth**: scale risks that are cheap to fix now are worth raising, and
credential defects escalate regardless of stage.

## Lenses engaged and skipped

**Engaged:** data-model, indexing, prisma, scalability, security. **Skipped:**
query-performance (no query or repository code in scope), backend-data-access (no service
code), migrations (no migration in scope). Single-pass mode.

## Findings

### 1. Critical — plaintext password (security)

- **Finding.** `User.password` stores the login credential in plaintext.
- **Evidence.** `schema.prisma:17`, `password String`.
- **Reasoning.** A password column is reversible if stored as text; any read access, backup
  leak, or log line exposes every user's credential directly.
- **Grounding.** [OWASP-CRYPTO] — passwords must be stored with a slow, salted hash, never
  reversible.
- **Impact.** A single database disclosure compromises every account immediately, at any data
  size. Blast radius is the whole user table.
- **Recommendation.** Store `passwordHash` produced by a slow, salted algorithm (bcrypt,
  scrypt, or Argon2); never persist the plaintext.
- **Trade-offs.** None worth weighing against the risk; hashing is standard and cheap.
- **Confidence.** High — the defect is true regardless of workload.

### 2. High — plaintext API secret (security)

- **Finding.** `ApiCredential.apiSecret` stores a provider secret in plaintext.
- **Evidence.** `schema.prisma:68`, `apiSecret String`.
- **Reasoning.** Unlike a password, a secret must be recoverable to use, so it needs
  encryption at rest, not hashing; plaintext exposes it on any read or leak.
- **Grounding.** [OWASP-CRYPTO] — secrets encrypted at rest, typically envelope encryption
  with a KMS-managed key, storing only ciphertext plus a key id.
- **Impact.** Disclosure hands an attacker a working third-party credential; blast radius
  extends beyond this database.
- **Recommendation.** Store `secretCiphertext Bytes` and `keyId String`; encrypt with a
  KMS-managed key.
- **Trade-offs.** Adds a KMS dependency and a decrypt step on use; unavoidable for a
  recoverable secret.
- **Confidence.** High — size-independent.

### 3. High — login identity nullable and non-unique (data-model)

- **Finding.** `User.email` is the login identity but is optional and not unique.
- **Evidence.** `schema.prisma:16`, `email String?`.
- **Reasoning.** A nullable, non-unique identity forces every consumer to handle `NULL` and
  permits duplicate accounts for the same address; the invariant lives only in hope.
- **Grounding.** [DMMS] nullability; [SQLAP] keys express meaning — an identity belongs in a
  `UNIQUE`, `NOT NULL` constraint.
- **Impact.** Duplicate or null-identity users corrupt authentication and account lookup;
  worsens as the table grows and as more code trusts the field.
- **Recommendation.** `email String @unique` (non-null). Backfill/repair existing rows first.
- **Trade-offs.** Requires cleaning existing nulls/dupes before the constraint can be added.
- **Confidence.** High — the defect follows from the schema.

### 4. High — composite index cannot serve its query (indexing)

- **Finding.** `Order.@@index([createdAt, customerId])` leads with `createdAt`, so the
  equality filter on `customerId` cannot drive it.
- **Evidence.** `schema.prisma:34`, serving `WHERE customerId = ? ORDER BY createdAt DESC`.
- **Reasoning.** A B-tree composite is only seekable on a leading prefix. With `createdAt`
  first, PostgreSQL cannot jump to one customer's rows; it scans and filters.
- **Grounding.** [UTIL] composite-index column order — equality columns first, range/sort last.
- **Impact.** Invisible at a few thousand orders; at 10M orders across 100k customers, each
  customer's order page reads far more of the index than the ~hundred rows it needs, on a hot
  read path.
- **Recommendation.** `@@index([customerId, createdAt(sort: Desc)])`; the index then seeks to
  the customer and returns rows already ordered.
- **Trade-offs.** None — it is the same one index, reordered. If orders are never queried by
  customer, drop it instead.
- **Confidence.** High on the defect (B-tree mechanics); Medium on the magnitude without row
  counts.

### 5. Medium — unindexed foreign key (indexing, corroborated by prisma, query-performance)

- **Finding.** `Comment.postId` is filtered and joined on but has no index. *Raised
  independently by indexing, prisma, and query-performance; reported once.*
- **Evidence.** `schema.prisma:47–48`, the `postId` FK with no `@@index`.
- **Reasoning.** Prisma does not auto-index a relation scalar; without one, "comments for a
  post" scans the comment table.
- **Grounding.** [PRISMA-DOCS] Prisma does not create FK indexes; [UTIL] index the join/filter key.
- **Impact.** Scales with total comments, not with a post's comment count; degrades as the
  table grows.
- **Recommendation.** Add `@@index([postId])`.
- **Trade-offs.** One index's write cost, paid back on every comment-by-post read.
- **Confidence.** High on the defect; Medium on magnitude. Three lenses agree, which raises
  confidence in the call.

### 6. Medium — comma-separated tags, jaywalking (data-model)

- **Finding.** `Post.tags` stores a comma-separated list in one column.
- **Evidence.** `schema.prisma:41`, `tags String`.
- **Grounding.** [SQLAP] Jaywalking.
- **Reasoning.** You cannot index, constrain, or join individual tags; "posts tagged urgent"
  becomes a `LIKE '%urgent%'` scan.
- **Impact.** Every tag query scans and string-parses; worsens with rows and tag count.
- **Recommendation.** Model tags as rows with a `Post`–`Tag` join table (`@@index` on the tag FK).
- **Trade-offs.** More schema and a join, bought back as integrity, indexing, and clean queries.
- **Confidence.** High on the defect; Medium on magnitude.

### 7. Medium — free-text status (data-model)

- **Finding.** `Order.status` is free text and will drift ("active"/"Active"/"ACTIVE").
- **Evidence.** `schema.prisma:27`, `status String`.
- **Grounding.** [SQLAP] enumerated domains belong in an enum or lookup, not free text.
- **Reasoning.** An open text domain has no enforced set of legal values.
- **Impact.** Inconsistent values corrupt filters and reports; grows with data and code paths.
- **Recommendation.** An `enum OrderStatus` for a stable set, or a lookup table with a FK if
  the set will churn.
- **Trade-offs.** An enum is rigid to evolve; a lookup costs a join. Pick per how the set changes.
- **Confidence.** High on the defect.

### 8. Medium — unbounded event stream, unindexed time column (scalability)

- **Finding.** `Event` is append-only with no retention plan and no index on `createdAt`.
- **Evidence.** `schema.prisma:53–58`.
- **Grounding.** [DDIA] unbounded growth / retention; [PG-DOCS] range partitioning and index cost.
- **Reasoning.** A table that only grows degrades every index, vacuum, and backup forever;
  cleanup by mass `DELETE` bloats it further; time-range reads scan without the index.
- **Impact.** Cheap now; at hundreds of millions of rows, retention and time queries become an
  operational burden.
- **Recommendation.** Add a retention plan — range-partition by time so pruning is a partition
  drop — and index `createdAt` (or the partition key) for the time reads.
- **Trade-offs.** Partitioning adds operational cost; it earns its place only past the size
  where one table's vacuum/indexes are the bottleneck. Below that, a scheduled batched delete
  plus the index suffices.
- **Confidence.** Medium — depends on growth rate, which is not attached.

### 9. Medium — large binary stored in-row (scalability)

- **Finding.** `Artifact.content` stores a binary blob in the row.
- **Evidence.** `schema.prisma:63`, `content Bytes`.
- **Grounding.** [DDIA]/[PG-DOCS] large values inflate row reads, buffer cache, and backups
  (TOAST).
- **Reasoning.** Multi-MB values inflate every read of the table and every backup.
- **Impact.** Grows with artifact count and size.
- **Recommendation.** Store the bytes in object storage; keep a `storageKey` and `sizeBytes`
  reference in the row.
- **Trade-offs.** Loses transactional atomicity with the row and adds a cleanup concern, in
  exchange for cheaper reads and backups.
- **Confidence.** Medium — depends on blob size.

### 10. Low — no referential action stated (prisma)

- **Finding.** `Order.customer` declares no `onDelete`.
- **Evidence.** `schema.prisma:26`.
- **Grounding.** [PRISMA-DOCS] referential actions are a data-integrity decision, not a default.
- **Reasoning.** Deleting a user's behavior toward their orders is implicit and may orphan or
  block.
- **Impact.** Latent until a user is deleted; then the behavior is whatever the default was.
- **Recommendation.** State intent explicitly (`onDelete: Restrict`, `Cascade`, or `SetNull`).
- **Trade-offs.** None; it is making an existing implicit choice explicit.
- **Confidence.** High that it is unstated.

## Strengths (do not change)

`Order.totalCents` correctly stores money as integer minor units, not a float. `Event` uses a
`BigInt` primary key, appropriate for a high-growth stream. Ownership via `User → Order/Post →
Comment` is coherent.

## Cross-lens trade-off (synthesized)

`Order.metadata Json` (`schema.prisma:29`) sits between data-model (which warns that queryable
fields hidden in JSON lose types, constraints, and indexability) and the flexibility a
pass-through payment payload genuinely wants. **Synthesis:** keep `metadata` as JSON *only*
for fields nothing filters, joins, or sorts on; the moment a field is queried (a status, a
country, an amount), promote it to a typed column and index it. The deciding condition is
whether any query reaches inside the JSON — an open question below.

## Per-lens confidence

- **security:** High — plaintext credential defects are size-independent facts.
- **data-model:** High on the defects; Medium on scale magnitude.
- **indexing:** High on the index-order and missing-FK defects; Medium on magnitude without
  row counts or plans.
- **scalability:** Medium — impacts depend on growth rate and blob size, which are not attached.
- **prisma:** High that `onDelete` is unstated.

## Open questions

Does any query filter or sort on a field inside `Order.metadata`? What is the growth rate of
`Event` and the typical size of `Artifact.content`? Answers would raise confidence on findings
8, 9, and the JSON trade-off, and could reclassify them.

## Approval decision

**Do not approve.** Blockers: finding 1 (Critical, plaintext password) and findings 2–4 (High:
plaintext secret, nullable non-unique login identity, mis-ordered index) unless explicitly
justified. As the principal engineer accountable for this system in five years, I would not
approve it today: the credential storage alone is a breach waiting to happen.
