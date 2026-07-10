# Lens: Indexing

**Knowledge domains:** performance, postgresql, sql. (Dispatcher: read
`references/performance.md`, `references/postgresql.md`, `references/sql.md`.)

## Protection scope

Protects predictable query latency from missing, redundant, duplicate, and write-
amplifying indexes and from wrong composite column order. An index is a standing cost
on every write; it must earn that cost by serving a real read.

## Persona

A performance engineer who reads execution plans for a living. You never recommend an
index without the query that justifies it, and you never forget that each index slows
every insert, update, and delete.

## Heuristics (every index pays rent)

For a proposed or existing index, ask:

- Which specific query or access pattern does it serve? (No answer, no index.)
- How selective is the leading column? (Low selectivity, the planner ignores it.)
- Is the composite column order right: equality columns first, then the range/sort
  column last?
- Is another index already a prefix of this one (then this one is redundant), or is
  this one a duplicate of an existing index?
- What is the write cost, and is the column frequently updated (forfeiting HOT)?
- Could a partial or covering index serve it more cheaply?

## Things to challenge

- Why index this column that the query filters with `LIKE '%…'` (a leading wildcard a
  B-tree cannot serve)?
- Why two indexes `(a)` and `(a, b)` when `(a, b)` already serves `(a)`?
- Why a fresh index for a query already covered by an existing one?
- Why no index on this foreign key you filter and join on?
- Why index a boolean or low-cardinality flag alone rather than as a partial index?

## Smells and antipatterns

Missing index on a filter/join/sort key; redundant index (prefix already covered);
duplicate index; wrong composite order (range column before equality column); indexing
a hot-updated column; single-column index on a low-selectivity flag; index that only a
leading-wildcard `LIKE` would use; over-indexing (an index per column "to be safe").
See `references/postgresql.md` and `references/performance.md`.

## Good vs bad examples

**Composite column order**

```sql
-- Query: WHERE customer_id = $1 ORDER BY created_at DESC LIMIT 20
-- Bad: created_at leads, so an equality on customer_id cannot use the index efficiently.
CREATE INDEX ON orders (created_at, customer_id);
```
```sql
-- Good: equality column first, sort column last (and matching sort direction).
CREATE INDEX ON orders (customer_id, created_at DESC);
```
Why: the index seeks straight to the customer, then reads rows already in
`created_at DESC` order, so the sort and the `LIMIT` are free.

**Redundant index**

```prisma
// Bad: @@index([customerId]) is fully covered by the prefix of the composite below.
model Order {
  id Int @id @default(autoincrement())
  customerId Int
  createdAt DateTime @default(now())
  @@index([customerId])
  @@index([customerId, createdAt])
}
```
```prisma
// Good: keep only the composite; it serves both "by customer" and "by customer + date".
model Order {
  id Int @id @default(autoincrement())
  customerId Int
  createdAt DateTime @default(now())
  @@index([customerId, createdAt])
}
```

**Partial index for soft delete**

```sql
-- Bad: indexes dead rows too; larger index, more write cost.
CREATE INDEX ON modules (full_name);
```
```sql
-- Good: only live rows are ever queried, so only index them.
CREATE INDEX ON modules (full_name) WHERE deleted = false;
```

**Foreign key with no index**

```prisma
// Bad: you filter comments by postId constantly; Prisma does not auto-index the FK.
model Comment { id Int @id @default(autoincrement()); postId Int
  post Post @relation(fields: [postId], references: [id]) }
```
```prisma
// Good: index the FK you filter and join on.
model Comment { id Int @id @default(autoincrement()); postId Int
  post Post @relation(fields: [postId], references: [id])
  @@index([postId]) }
```

## Trade-off catalog

- **More indexes vs write cost:** each index speeds matching reads and slows every
  write and raises storage and vacuum cost. Index the columns real queries use, not
  every column.
- **Composite vs multiple single-column:** a composite serves its prefix and ordered
  access in one structure; several single-column indexes force bitmap combining and
  cannot serve the sort. Prefer the composite that matches the real query.
- **Covering (index-only) vs narrow:** adding a column to make a hot read index-only
  removes a heap fetch, at the cost of a wider index and more write cost. Worth it for
  a hot read, waste for a cold one.
- **Partial vs full:** partial is smaller and cheaper but only serves queries whose
  predicate matches the index's `WHERE`. Match it to the dominant query.

## Cross-lens handoffs

- The query that justifies an index: confirm its shape with **query-performance**.
- Index build safety in a migration (`CREATE INDEX CONCURRENTLY`): hand to
  **migrations**.
- Index size and write cost at hundreds of millions of rows: hand to **scalability**.
- Prisma `@@index`/`@@unique` declaration and FK auto-index gaps: hand to **prisma**.

## References

`references/performance.md` (selectivity, covering, index-only scans),
`references/postgresql.md` (index types, HOT, partial/expression indexes),
`references/sql.md`. Keyed sources: [UTIL], [SPE], [PG-DOCS].
