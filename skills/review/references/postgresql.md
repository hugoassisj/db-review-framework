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

## Watch-list

Unbounded churn without autovacuum headroom; indexing a hot-updated column (HOT
loss); seq scan on a large table for a selective predicate; Nested Loop over a large
outer set; external Sort; estimated-vs-actual row skew (stale stats); `json` where
`jsonb` is meant; blocking `CREATE INDEX` in a migration; table-rewriting
`ALTER TABLE`; `NOT NULL`/FK added without `NOT VALID`; tenant isolation without RLS.
