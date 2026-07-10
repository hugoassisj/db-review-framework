# Knowledge: Scalability

Distilled growth-behavior facts. The question this domain always asks: does this
design degrade linearly or non-linearly as data and traffic grow? Sources
**[DDIA]**, **[PG-DOCS]** (partitioning), **[DBI]**.

## Unbounded growth

- A table that only ever grows (events, logs, audit, notifications, sessions) needs a
  retention or archival plan from day one. Without one, indexes, vacuum, and backups
  degrade for the whole table forever. Range partitioning by time makes retention a
  partition drop instead of a mass `DELETE` (which itself bloats the table). [DDIA][PG-DOCS]

## Hot rows and contention

- A single row that many transactions update (a global counter, an aggregate total, a
  "current" pointer) serializes those transactions on its row lock and, under MVCC,
  generates dead tuples fast. Techniques: sharded counters (N rows summed), append-
  then-aggregate, or moving the count out of the hot path. [DDIA][PG-DOCS]
- A hot partition is the same problem at partition scale: a hash or range key that
  routes most traffic to one partition removes the benefit of partitioning. [DDIA]

## Key choice at scale

- Monotonic keys (bigserial, time-ordered) concentrate inserts at the right edge of
  the index (a hotspot for some engines, though PostgreSQL B-trees handle this well)
  and make ranges cache-friendly. Random keys (UUIDv4) scatter inserts, hurting cache
  locality and index density; UUIDv7 (time-ordered) recovers locality. Weigh
  distributed generation and opacity against index size and locality (see the
  trade-off in `data-model` and `indexing`). [DDIA][DBI]

## Read and write scaling

- Read-heavy systems scale reads with replicas, at the cost of replication lag: a read
  routed to a replica may not see a just-committed write (read-your-writes must route
  to the primary). Do not silently send a read that requires freshness to a replica.
  [DDIA]
- Write scaling eventually needs partitioning/sharding by a key that spreads load and
  keeps related data together; the wrong shard key forces cross-shard queries and
  distributed transactions. This is a large step; flag when a design is heading toward
  needing it, do not prescribe it prematurely. [DDIA]

## Wide tables and large values

- Very wide tables (many columns, large `Text`/`Bytes`/`Json`) make every row read
  heavier and can trigger out-of-line (TOAST) storage. Storing large blobs in the
  database row inflates backups and buffer cache; object storage with a reference is
  often better past a size threshold. [PG-DOCS]

## Applying the mental model

Assume the table reaches hundreds of millions of rows. Ask: which query becomes a
scan, which index stops fitting in cache, which lock becomes hot, which single-
statement operation becomes an outage. State the row count at which the concern bites.

## Watch-list

Append-only table with no retention/archival; mass `DELETE` for retention instead of
partition drop; single hot-updated counter/aggregate row; hot partition from a skewed
key; freshness-sensitive read routed to a replica; a design implicitly requiring
sharding with a poor shard key; large blob stored in-row; wide table on a hot read
path.
