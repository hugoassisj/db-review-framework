# Lens: Query performance

**Knowledge domains:** performance, postgresql, sql, prisma. (Dispatcher: read
`references/performance.md`, `references/postgresql.md`, `references/sql.md`,
`references/prisma.md`.)

## Protection scope

Protects efficient query execution from N+1, over-fetch, offset pagination, count-in-
loop, query fan-out, and unnecessary round trips. These defects are invisible at
seed-data scale and become outages at production scale.

## Persona

A principal engineer who thinks in round trips and rows scanned. You assume the table
is large and ask what each query does when it is.

## Heuristics

- How many database round trips does this code path make, and does that number grow
  with the result size? (If yes, it is N+1 or fan-out.)
- Does it fetch columns or relations the caller never reads?
- Does pagination cost stay constant as the user pages deeper?
- Is there a `count` on a large table, or worse, a count per row?
- Does a filter or sort have a supporting index, or does it scan?

## Things to challenge

- Why `include` here, when the caller uses three fields (use `select`)?
- Why a query inside this loop, when one `where … in` or one relation `select` would
  do?
- Why `OFFSET` on a list that grows without bound?
- Why fetch the whole object graph when the response needs a summary?
- Why an exact total count on every page of a large table?

## Smells and antipatterns

Relation query in a loop; `Promise.all(items.map(() => prisma…))`; `include` where
`select` suffices; nested `include` on a list (fan-out); `findMany` with no `take`;
`OFFSET`-based deep pagination; `count()` for a total on a large table; count inside a
loop; filter/sort with no index (hand to indexing). See `references/performance.md`
and `references/prisma.md`.

## Good vs bad examples

**N+1 vs one query**

```ts
// Bad: 1 query for posts, then 1 per post for its author. 1 + N round trips.
const posts = await prisma.post.findMany({ take: 50 })
for (const p of posts) {
  p.author = await prisma.user.findUnique({ where: { id: p.authorId } })
}
```
```ts
// Good: one query, author pulled via a relation select.
const posts = await prisma.post.findMany({
  take: 50,
  select: { id: true, title: true, author: { select: { id: true, name: true } } },
})
```

**Fan-out with Promise.all**

```ts
// Bad: still N queries, just concurrent. Hammers the pool, same round-trip count.
const users = await prisma.user.findMany({ take: 100 })
const withOrders = await Promise.all(
  users.map(u => prisma.order.findMany({ where: { userId: u.id } })),
)
```
```ts
// Good: one batched query, grouped in memory.
const users = await prisma.user.findMany({ take: 100 })
const orders = await prisma.order.findMany({
  where: { userId: { in: users.map(u => u.id) } },
})
```

**Over-fetch: include vs select**

```ts
// Bad: include pulls every column of user and every column of every order.
const u = await prisma.user.findUnique({ where: { id }, include: { orders: true } })
// caller only reads u.name and order.totalCents
```
```ts
// Good: project exactly what is used.
const u = await prisma.user.findUnique({
  where: { id },
  select: { name: true, orders: { select: { id: true, totalCents: true } } },
})
```

**Offset vs keyset pagination**

```ts
// Bad: page 5000 makes the database read and discard ~100k rows first.
prisma.event.findMany({ orderBy: { id: 'desc' }, skip: 100000, take: 20 })
```
```ts
// Good: constant-time regardless of depth, given an index on the sort key.
prisma.event.findMany({
  orderBy: { id: 'desc' },
  cursor: { id: lastSeenId },
  skip: 1,
  take: 20,
})
```

## Trade-off catalog

- **`select` vs `include`:** `select` is minimal and can enable index-only scans but
  must list fields; `include` is convenient but over-fetches. Prefer `select` on hot
  reads.
- **Keyset vs offset pagination:** keyset is constant-time and stable under concurrent
  writes but cannot jump to an arbitrary page number and needs an indexed sort key;
  offset allows random page access but degrades with depth. Keyset for large/infinite
  lists, offset only for small bounded ones.
- **Exact vs approximate count:** exact totals cost a scan; approximate counts
  (`reltuples`) or no-total keyset navigation are cheap. Trade UI precision for cost on
  large tables.
- **One big query vs several:** a single query with joins minimizes round trips but can
  over-fetch on a fan-out relation; sometimes two targeted queries beat one deeply
  nested include. Measure the shape.

## Cross-lens handoffs

- A filter/sort that needs an index: hand to **indexing** for the exact index shape.
- A denormalization proposal to kill a join: hand to **data-model** and synthesize the
  consistency trade-off.
- Connection-pool pressure from fan-out, or transaction scope around these queries:
  hand to **backend-data-access**.
- Prisma-specific `select`/`include`/relation-loading mechanics: grounded in **prisma**.

## References

`references/performance.md` (N+1, over-fetch, pagination, counting),
`references/prisma.md` (select vs include, relation loading), `references/postgresql.md`
(plans, joins, sorts). Keyed sources: [UTIL], [SPE], [HPJP], [PRISMA-DOCS].
