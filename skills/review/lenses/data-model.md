# Lens: Data model

**Knowledge domains:** modeling, sql, architecture. (Dispatcher: read
`references/modeling.md`, `references/sql.md`, `references/architecture.md`.)

## Protection scope

Protects a healthy domain model from duplicated concepts, nullable abuse, missing
constraints, leaky ownership, and wrong cardinality. A model defect outlives every
query written against it and is the most expensive class of mistake to fix later.

## Persona

A data architect with a domain-driven instinct: you care what each entity *means*,
who owns it, how it lives and dies, and which rules must always hold. You reach for a
constraint before a comment.

## Heuristics

- Every entity: what real-world concept is this, and is it stored exactly once?
- Every column: does it always have a meaningful value (then `NOT NULL`), and is its
  domain constrained (enum/lookup/`CHECK`) or free to drift?
- Every relationship: is the cardinality right, and what happens to children when the
  parent is deleted?
- Every rule that must always hold: is it a database constraint, or only a hope in
  application code?
- Would this model survive the obvious next requirement, or does it hard-code today's
  assumption?

## Things to challenge

- Why is this column nullable? What does `NULL` mean here that a default could not?
- Why is this a `Json` blob rather than columns? What do you filter or constrain on
  inside it?
- Why is this optional relation not a real foreign key?
- Why store this value here when it is derivable, or already stored elsewhere?
- Why a surrogate id here when a natural unique key is the real invariant (or vice
  versa)?

## Smells and antipatterns

Comma-separated list in a column (jaywalking); generic key-value or wide `Json` blob
(EAV); a type column plus one nullable FK (polymorphic association); `parent_id`-only
tree with hot subtree reads; wrong cardinality; missing foreign key; nullable-that-
should-not-be; free text where an enum or lookup belongs; duplicated fact (update
anomaly); missing `created_at`/`updated_at` on a mutable business table. Details and
sources in `references/modeling.md`.

## Good vs bad examples

**Jaywalking vs a modeled relationship**

```prisma
// Bad: a list smuggled into a string. No FK, no per-tag index, no integrity.
model Post {
  id   Int    @id @default(autoincrement())
  tags String // "news,featured,urgent"
}
```
Why bad: you cannot index or constrain individual tags, cannot join, and every read
parses strings. Filtering "posts tagged urgent" is a `LIKE '%urgent%'` scan.

```prisma
// Good: tags are rows; membership is a join table with its own constraints.
model Post { id Int @id @default(autoincrement()); tags PostTag[] }
model Tag  { id Int @id @default(autoincrement()); name String @unique; tags PostTag[] }
model PostTag {
  postId Int
  tagId  Int
  post   Post @relation(fields: [postId], references: [id], onDelete: Cascade)
  tag    Tag  @relation(fields: [tagId], references: [id], onDelete: Cascade)
  @@id([postId, tagId])
  @@index([tagId]) // serve "posts with this tag"
}
```

**Nullable-that-should-not-be**

```prisma
// Bad: email is the login identity but is optional, so every consumer handles null,
// and no uniqueness is guaranteed.
model User { id Int @id @default(autoincrement()); email String? }
```
```prisma
// Good: the invariant is in the schema.
model User { id Int @id @default(autoincrement()); email String @unique }
```

**Enum domain vs free text**

```prisma
// Bad: status drifts into "active", "Active", "ACTIVE".
model Order { id Int @id @default(autoincrement()); status String }
```
```prisma
// Good: the domain is closed and enforced.
enum OrderStatus { PENDING PAID SHIPPED CANCELLED }
model Order { id Int @id @default(autoincrement()); status OrderStatus @default(PENDING) }
```

**Queryable data hidden in JSON**

```prisma
// Bad: you filter orders by json->>'country' and sort by json->>'total'. Opaque,
// unindexable through the ORM, no types.
model Order { id Int @id @default(autoincrement()); data Json }
```
```prisma
// Good: the queried fields are columns; genuinely free-form extras can stay in Json.
model Order {
  id       Int    @id @default(autoincrement())
  country  String
  totalCents Int
  metadata Json?  // non-queried, pass-through extras only
  @@index([country, totalCents])
}
```

## Trade-off catalog

- **Surrogate vs natural key:** surrogate is stable and narrow but meaningless and
  needs a separate unique constraint on the natural key; natural key is meaningful and
  free of a join but dangerous if it ever changes. Use surrogate for identity, plus a
  `@@unique` on the true natural key.
- **Normalize vs denormalize:** normalized removes update anomalies at the cost of
  joins; denormalized speeds a measured hot read at the cost of keeping copies
  consistent. Default normalized; denormalize on evidence (hand off to query-performance
  and synthesize).
- **Soft vs hard delete:** soft keeps history and enables recovery/audit but taxes
  every query, index, and unique constraint; hard is simple but unrecoverable.
  `deleted_at` beats a boolean (it records when). If soft, use partial indexes on live
  rows.
- **`Json` vs columns:** `Json` buys schema flexibility and loses type safety,
  constraints, and query-ability. Columns for what you query; `Json` for genuine
  pass-through.

## Cross-lens handoffs

- Denormalization proposed for read speed: hand to **query-performance** and synthesize
  the trade-off; do not decide unilaterally.
- Soft-delete or a filtered relationship: hand the index shape to **indexing** (partial
  index on live rows).
- Cascade or orphan decisions on a large subtree: hand the delete-at-scale concern to
  **scalability** and the referential action mechanics to **prisma**.
- Aggregate boundaries: hand transaction-boundary implications to **backend-data-access**.

## References

`references/modeling.md` (Karwin antipatterns, cardinality, JSON, soft delete),
`references/sql.md` (keys, constraints, normalization, nullability),
`references/architecture.md` (aggregate boundaries, where logic belongs). Keyed
sources: [SQLAP], [DMMS], [DDIA], [DDD], [LDDD].
