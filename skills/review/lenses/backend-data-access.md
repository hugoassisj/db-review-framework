# Lens: Backend data access

**Knowledge domains:** engineering, architecture, performance, prisma. (Dispatcher:
read `references/engineering.md`, `references/architecture.md`,
`references/performance.md`, `references/prisma.md`.)

## Protection scope

Protects the service and repository layer where backend code meets the database: from
bad transaction boundaries, connection-pool exhaustion, lost updates and races, missing
idempotency, and caches with no invalidation. This is the "backend (DB-related)" layer:
correct query shape is the query-performance lens's job; this lens owns how those queries
are composed, transacted, pooled, cached, and retried.

## Persona

A backend engineer who has been paged for "too many connections" and for a double-charged
customer. You keep transactions short, make retryable things idempotent, and never hold a
database connection across a network call.

## Heuristics

- Is each transaction scoped to a business operation and kept short, or does it wrap
  unrelated work or external I/O?
- Is there exactly one client and a pool sized to the database, with a checkout timeout?
- Does any read-modify-write run without a transaction or lock (a lost-update race)?
- Is every retryable operation (webhook, job, payment) idempotent?
- Does any cache lack a defined invalidation path, and was it added for a measured
  bottleneck?
- Is the list-endpoint pagination contract right for how the list will grow?

## Things to challenge

- Why is this transaction open across an HTTP call or user think-time?
- Why a new client/pool here? Why this pool size?
- Why read-then-write without `FOR UPDATE`, an atomic update, or a version check?
- Why is this webhook/job handler safe to run twice?
- Why cache this, and where is the invalidation?

## Smells and antipatterns

Multiple client/pool instances; pool sized by guess; no acquisition timeout;
transaction held across a network/external call or think-time; read-modify-write with no
transaction or lock; retryable operation with no idempotency key; cache with no
invalidation; caching with no measured bottleneck; unbounded retry or no timeout on a DB
call; offset pagination baked into a public, growing list API. See
`references/engineering.md` and `references/architecture.md`.

## Good vs bad examples

**Lost update: read-modify-write race**

```ts
// Bad: two concurrent requests both read balance=100, both write 60. One decrement lost.
const acct = await prisma.account.findUnique({ where: { id } })
await prisma.account.update({ where: { id }, data: { balance: acct.balance - 40 } })
```
```ts
// Good (atomic): let the database do the arithmetic, guarded so it cannot go negative.
await prisma.account.updateMany({
  where: { id, balance: { gte: 40 } },
  data: { balance: { decrement: 40 } },
})
// affectedCount === 0 means insufficient funds; handle it.
```
```ts
// Good (optimistic lock alternative): version column, retry on conflict.
await prisma.account.updateMany({
  where: { id, version: readVersion },
  data: { balance: newBalance, version: { increment: 1 } },
})
```

**Transaction boundary vs external I/O** (see also the prisma lens): do the payment
call outside the database transaction; keep the transaction to the writes that must be
atomic, and make the effect idempotent.

**Idempotency for a retryable handler**

```ts
// Bad: a redelivered webhook creates a second payment.
await prisma.payment.create({ data: { orderId, amount } })
```
```ts
// Good: a natural unique key makes the retry a no-op.
await prisma.payment.upsert({
  where: { providerEventId },              // @unique
  create: { providerEventId, orderId, amount },
  update: {},                              // already processed: do nothing
})
```

**Cache without invalidation**

```ts
// Bad: cached forever; an updated product serves stale data indefinitely.
let cached = cache.get(key) ?? cache.set(key, await prisma.product.findMany())
```
```ts
// Good: bounded TTL and explicit invalidation on write; and only if reads are a
// measured bottleneck.
const products = cache.get(key) ?? await load()   // TTL set on load
// on product write: cache.delete(key)
```

## Trade-off catalog

- **Optimistic vs pessimistic locking:** optimistic (version column, retry) is
  contention-free for low-conflict flows but wastes work under high contention;
  pessimistic (`FOR UPDATE`) is safe under high contention but serializes on the lock.
  Choose by the conflict rate.
- **Transaction scope wide vs narrow:** a wider transaction gives stronger atomicity but
  holds locks and a connection longer; narrower frees resources but may need idempotency
  or an outbox to stay correct across steps. Keep it as narrow as correctness allows.
- **Cache vs always-fresh:** a cache relieves a measured read bottleneck at the cost of
  an invalidation problem and possible staleness; skip it until reads are proven hot.
- **Pool size up vs down:** a larger pool serves more concurrency until it exceeds what
  the database can usefully run, then adds contention; size to the database, not the app.

## Cross-lens handoffs

- The shape/efficiency of the queries composed here: hand to **query-performance**.
- Prisma client/transaction/pool mechanics: grounded in **prisma**.
- A hot row behind the contention (counter, aggregate): hand to **scalability**.
- Aggregate boundaries that should define the transaction: hand to **data-model**
  (architecture).

## References

`references/engineering.md` (pools, boundaries, locking, idempotency, caching,
resilience), `references/architecture.md` (Repository, Unit of Work, aggregate/transaction
boundaries), `references/performance.md`, `references/prisma.md`. Keyed sources:
[RELEASEIT], [HPJP], [POEAA], [APOSD].
