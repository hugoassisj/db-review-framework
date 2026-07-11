# Knowledge: PostgreSQL

Distilled engine facts. Primary source **[PG-DOCS]**; mechanisms in **[DBI]**,
**[MPG]**.

## MVCC, dead tuples, and VACUUM

- PostgreSQL is MVCC: an `UPDATE` writes a new row version and marks the old one
  dead; a `DELETE` marks dead. Dead tuples accumulate until VACUUM reclaims them.
  High-churn tables (status flips, counters, queues) bloat and slow scans if
  autovacuum cannot keep up. [PG-DOCS][DBI]
- A HOT (heap-only tuple) update avoids updating indexes, but only when no indexed
  column changes and the page has room. Indexing a frequently-updated column forfeits
  HOT and raises write cost. This is why "every index pays rent." [PG-DOCS]
- `VACUUM` reclaims space and updates the visibility map (which enables index-only
  scans); `ANALYZE` refreshes planner statistics. Stale statistics cause bad plans.

## The planner and EXPLAIN

- The planner is cost-based and statistics-driven. It chooses sequential scan vs
  index scan by estimated selectivity: for a low-selectivity predicate (matches many
  rows) a sequential scan is correct, so "seq scan" is not automatically a bug.
  [PG-DOCS][SPE]
- `EXPLAIN` shows the estimated plan; `EXPLAIN (ANALYZE, BUFFERS)` runs it and shows
  actual rows, timing, and buffer reads. A large gap between estimated and actual rows
  signals stale or insufficient statistics. Read plans bottom-up. [PG-DOCS][DEPESZ]
- Sequential scan on a large table for a selective predicate, a Nested Loop over many
  outer rows, or an external (disk) Sort are the usual smells in a plan.
- A CTE (`WITH`) is inlined into the surrounding plan on PostgreSQL 12+ when referenced
  once and not marked `MATERIALIZED`; before 12, or with `MATERIALIZED`, it is an
  optimization fence that is always materialized to a temp result, which can force a
  worse plan than the equivalent subquery. Know which behavior applies before blaming
  the CTE or the planner. [PG-DOCS]

## Index types

- **B-tree**: default; equality and range (`=`, `<`, `>`, `BETWEEN`), sorting, and
  prefix `LIKE 'abc%'`. Composite B-tree column order follows the equality-first,
  range-last rule (see `indexing.md`). [PG-DOCS][UTIL]
- **GIN**: multi-value columns; JSONB containment (`@>`), arrays, full-text.
- **GiST / SP-GiST**: geometric, range, nearest-neighbor.
- **BRIN**: very large, naturally-ordered tables (append-only time series); tiny and
  cheap, effective only when physical order correlates with the indexed value.
- **Hash**: equality only; rarely worth choosing over B-tree.
- Partial index (`WHERE`) indexes only matching rows (for example
  `WHERE deleted = false`), shrinking the index and its write cost. Expression index
  indexes a computed value (for example `lower(email)`) to serve
  `WHERE lower(email) = …`. [PG-DOCS][UTIL]
- Covering index with `INCLUDE` (PostgreSQL 11+): non-key payload columns are stored
  in the index leaf so a hot query can be answered index-only without a heap fetch,
  without those columns affecting the B-tree order or uniqueness. Prefer `INCLUDE` over
  widening the key when the extra column is only needed in the output, not the search.
  [PG-DOCS][UTIL]
- A leading-wildcard predicate (`LIKE '%term%'`, `ILIKE`) cannot use a plain B-tree.
  Serve substring/fuzzy search with a `pg_trgm` GIN index, or use full-text search
  (`tsvector`/`tsquery` + GIN) for word search. Do not "just add a B-tree" to a
  leading-wildcard column; it will not be used. [PG-DOCS]
- Indexes bloat under churn just as tables do; a bloated index is larger and slower.
  `REINDEX CONCURRENTLY` rebuilds it without an exclusive lock. Bloat, not just
  presence, is part of an index's real cost. [PG-DOCS]

## Data types

- Store timestamps as `timestamptz` (timezone-aware), not naive `timestamp`.
  `timestamptz` records an absolute instant; naive `timestamp` silently depends on the
  session time zone and misreads data across zones and DST. A correctness footgun, not a
  style preference. [PG-DOCS]
- A high-growth table keyed by `int4` (`serial`/`integer`) exhausts its ~2.1-billion
  range and then fails every insert. Use `bigint`/`bigserial` (or a `bigint` identity)
  for any table that can grow large; widening the primary key later is a full-table
  rewrite. [PG-DOCS][DBI]
- Money is not `float`/`double`: binary floating point cannot hold decimal fractions
  exactly and drifts under arithmetic. Store currency as integer minor units or
  `numeric` (see `sql.md`). [SQL-STD]
- `GENERATED ALWAYS AS (…) STORED` computes a derived column from other columns in the
  same row, keeping the value correct by construction instead of by application
  discipline. Prefer it over a trigger for pure row-local derivations. [PG-DOCS]

## Locking and DDL

- DDL takes locks. `ALTER TABLE` that rewrites the table (some type changes, adding a
  column with a volatile default on older versions) holds an `ACCESS EXCLUSIVE` lock
  and blocks reads and writes for the rewrite's duration. Adding a column with no
  default, or a constant default on modern PostgreSQL, is fast (metadata-only).
  [PG-DOCS][REFDB]
- `CREATE INDEX` locks writes on the table for the build. `CREATE INDEX CONCURRENTLY`
  does not block writes but runs outside a transaction, is slower, and can leave an
  invalid index if it fails (which must then be dropped and retried). [PG-DOCS]
- Adding a `NOT NULL` constraint or a foreign key validates existing rows under lock
  unless added `NOT VALID` and validated separately. [PG-DOCS]
- **The lock queue is the hidden hazard.** A statement waiting for `ACCESS EXCLUSIVE`
  queues behind the transactions currently holding the table, *and* every query that
  arrives after it queues behind the waiter. So even a fast, metadata-only `ALTER` can
  freeze a table if one long-running transaction holds a conflicting lock: the ALTER
  waits, and all new traffic waits behind the ALTER. Set a short `lock_timeout` (e.g.
  a few seconds) and retry, so a blocked DDL aborts instead of stalling production.
  [PG-DOCS][GITHUB-ENG]
- Adding a foreign key takes a `SHARE ROW EXCLUSIVE` lock on **both** the referencing
  and referenced tables and validates existing rows. Add it `NOT VALID`, then
  `VALIDATE CONSTRAINT` in a separate step (a weaker lock) to avoid a long validation
  under the heavier lock. [PG-DOCS]
- Enum evolution is rigid: `ALTER TYPE … ADD VALUE` cannot run inside a transaction
  block on older PostgreSQL and the new value is unusable until committed, and enum
  values cannot be removed or reordered at all. A lookup table with a foreign key is
  the more evolvable choice when the domain will change (see `modeling.md`). [PG-DOCS]

## JSONB

- `JSONB` supports containment and path queries and can be indexed with GIN. Prefer
  `jsonb` over `json` for anything queried. Data you filter, join, or constrain
  belongs in columns, not JSONB. [PG-DOCS]

## Partitioning and scale

- Declarative partitioning (range, list, hash) helps very large tables by pruning
  partitions and bounding index size, and makes retention cheap (drop a partition
  instead of a mass `DELETE`). It adds planning and operational cost, so it earns its
  place only past the size where a single table's indexes and vacuum become the
  bottleneck. [PG-DOCS][DDIA]

## Row-level security

- RLS (`ENABLE ROW LEVEL SECURITY` plus policies) enforces per-row visibility in the
  database, the durable way to enforce tenant isolation. Enforcing tenancy only in
  application `where` clauses is one forgotten filter away from a cross-tenant leak.
  [PG-DOCS] (see `security.md`).
- **RLS is silently bypassed by the table owner, by roles with `BYPASSRLS`, and by
  superusers.** If the application connects as the table owner — a common default —
  the policies do nothing and the isolation is illusory. Enable
  `FORCE ROW LEVEL SECURITY` and run the app as a dedicated non-owner role without
  `BYPASSRLS`. [PG-DOCS]
- A policy that keys off a session variable (`current_setting('app.tenant_id')`) must
  have that variable set with `SET LOCAL` **inside the transaction** when a
  transaction-mode pooler (PgBouncer, Prisma Accelerate) sits in front; a plain `SET`
  leaks the value to whatever session next reuses the pooled connection. [PG-DOCS]

## Concurrency primitives

- `SELECT … FOR UPDATE SKIP LOCKED` lets each worker claim rows no other worker has
  locked, the standard way to build a correct, contention-free job/queue claim on
  PostgreSQL instead of a hand-rolled status flag with a race. [PG-DOCS]
- Advisory locks (`pg_advisory_xact_lock`) provide application-defined mutual exclusion
  (a singleton job, a critical section keyed by an id) without a lock row; they are held
  for the transaction (the `xact` form) and never touch table data. [PG-DOCS]

## Watch-list

Unbounded churn without autovacuum headroom; indexing a hot-updated column (HOT
loss); seq scan on a large table for a selective predicate; Nested Loop over a large
outer set; external Sort; estimated-vs-actual row skew (stale stats); `json` where
`jsonb` is meant; blocking `CREATE INDEX` in a migration; table-rewriting
`ALTER TABLE`; `NOT NULL`/FK added without `NOT VALID`; DDL run without a
`lock_timeout` (lock-queue pileup); naive `timestamp` instead of `timestamptz`;
`int4` primary key on a high-growth table; money stored in `float`; leading-wildcard
`LIKE`/`ILIKE` on a plain B-tree; index bloat left unaddressed; tenant isolation
without RLS, RLS with the app connecting as the table owner or without
`FORCE ROW LEVEL SECURITY`, or a tenant session variable set without `SET LOCAL`
behind a transaction-mode pooler.
