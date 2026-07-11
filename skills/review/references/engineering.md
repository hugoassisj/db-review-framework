# Knowledge: Backend engineering

Distilled facts for the operational, data-access layer between the application and
the database. Sources **[RELEASEIT]**, **[HPJP]**, **[APOSD]**.

## Connection pools

- The database has a hard `max_connections`; the application reaches it through a
  connection pool. Pool size is not "bigger is better": past the point where active
  connections exceed the database's useful concurrency (roughly bounded by cores and
  disk), more connections add contention and latency, not throughput. Size the pool to
  the database, and account for every process and replica sharing it. [RELEASEIT][HPJP]
- Multiple pools (multiple `PrismaClient` instances, one per serverless invocation)
  multiply against `max_connections` and cause "too many connections" outages.
  Instantiate the client once; in serverless, front the database with a pooler.
  [PRISMA-DOCS][RELEASEIT]
- Every pool checkout needs a timeout. A pool with no acquisition timeout turns a slow
  database into a hung application (threads block forever waiting for a connection).
  [RELEASEIT]

## Transaction boundaries

- Scope a transaction to the business operation, not to each statement, and keep it as
  short as possible. A transaction held open across a network call, an external API, or
  user think-time holds locks and a pooled connection the whole time, starving the pool
  and blocking writers. Do the I/O outside the transaction. [RELEASEIT][HPJP]
- A read-modify-write across two statements without a transaction or lock is a lost-
  update bug under concurrency (see `sql.md`).

## Concurrency control

- **Optimistic locking:** a version column checked on write; the update fails if the
  row changed since it was read, and the application retries. Best for low-contention,
  read-then-write flows. [HPJP][POEAA]
- **Pessimistic locking:** `SELECT … FOR UPDATE` takes the row lock up front. Best for
  high-contention hotspots, at the cost of serializing on the lock. Choose per the
  contention profile; state which and why. [HPJP]
- **Queue and claim patterns:** a worker pool that claims rows should use
  `SELECT … FOR UPDATE SKIP LOCKED`, so each worker takes rows no other worker has
  locked, instead of a status-flag `UPDATE` that races two workers onto the same job.
  For app-level mutual exclusion (a singleton cron, a keyed critical section) use a
  PostgreSQL advisory lock rather than inventing a lock row. [PG-DOCS][HPJP]
- Idempotency: any operation that can be retried (a webhook, a job, a payment) needs an
  idempotency key or a natural unique constraint so a retry does not double-apply.

## Caching

- A cache is a second copy of the truth and introduces an invalidation problem. Read-
  through caching needs a defined invalidation on write; a cache with no invalidation
  path serves stale data indefinitely. State the invalidation strategy and the staleness
  the feature can tolerate before adding a cache. Cache to relieve a measured read
  bottleneck, not by default. [RELEASEIT][APOSD]

## Resilience

- A database call can be slow or fail. Timeouts, bounded retries with backoff (only for
  idempotent operations), and not holding resources while waiting are the difference
  between a slow query and a cascading outage. [RELEASEIT]

## Pagination contracts

- A list endpoint's pagination contract (offset vs cursor) is an API decision with the
  performance consequences in `performance.md`. A public list that will grow should
  expose cursor pagination; retrofitting it later is a breaking API change. [UTIL]

## Watch-list

Multiple client/pool instances; pool sized by guess, not to the database; no pool
acquisition timeout; transaction held across a network/external call or user think-
time; read-modify-write with no transaction or lock; a queue/claim built on a
status-flag `UPDATE` instead of `FOR UPDATE SKIP LOCKED`; retryable operation with no
idempotency key; cache with no invalidation path; caching added without a measured
bottleneck; no timeout or unbounded retry on a database call; offset pagination baked
into a public, growing list API.
