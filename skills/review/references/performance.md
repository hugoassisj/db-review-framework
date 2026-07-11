# Knowledge: Performance

Distilled query and access-path performance. Sources **[UTIL]**, **[SPE]**,
**[PG-DOCS]**, **[HPJP]**.

## Access paths

- An index turns a scan of N rows into a traversal of log(N) plus the matched rows.
  Its value is proportional to selectivity: an index on a column where the predicate
  matches most rows is not used and not worth its write cost. [SPE][UTIL]
- An index-only scan (covering index) answers a query entirely from the index without
  touching the heap, when the index contains every column the query needs and the
  visibility map allows it. Adding a rarely-changing column to an index to make a hot
  read index-only is a real win; doing it for a cold read is waste. On PostgreSQL 11+
  attach the payload column with `INCLUDE` so it rides in the index leaf without
  changing the key order (see `postgresql.md`). [UTIL][PG-DOCS]

## The N+1 problem

- N+1 is one query to fetch N parents, then one query per parent for its children:
  1 + N round trips where 2 would do. It is the single most common ORM performance
  defect. In Prisma it appears as a relation fetched in a loop, or `Promise.all` over
  a `map` of queries. The fix is one query with a relation `select`, or a batched
  `where … in`. [HPJP]

## Fetching

- Over-fetch is selecting columns or relations the caller does not use. It inflates
  row width, memory, and network, and can prevent an index-only scan. `SELECT *`
  (and Prisma's default all-fields, and `include` where `select` suffices) is the
  usual culprit. Project only what is used. [UTIL][HPJP]
- Fetching a whole object graph "to be safe" is over-fetch multiplied by relation
  depth.

## Pagination

- Offset pagination (`OFFSET n LIMIT m`) makes the database read and discard n rows
  to reach the page; cost grows with the page number, so deep pages are slow and page
  boundaries shift under concurrent writes. [UTIL]
- Keyset (cursor, "no offset") pagination filters on the last seen sorted key
  (`WHERE (sort_key) > (last) ORDER BY sort_key LIMIT m`) and stays constant-time at
  any depth, given an index on the sort key. Prefer it for large or deep lists and
  for infinite scroll. Offset is acceptable only for small, bounded page counts.
  [UTIL]

## Counting and aggregates

- `COUNT(*)` is a scan, not a lookup. Exact total counts for pagination on a large,
  growing table are expensive; prefer keyset navigation without a total, an approximate
  count, or a maintained counter. Counting inside a loop is the aggregate form of N+1.
  [PG-DOCS][UTIL]

## Joins and sorting

- A Nested Loop join is efficient when the outer side is small and the inner side is
  indexed; it degrades badly when the outer side is large. Hash and merge joins suit
  larger sets. The planner chooses, but a missing inner-side index forces the bad
  shape. [SPE][PG-DOCS]
- A sort that exceeds `work_mem` spills to disk (external sort). An index that already
  provides the required order removes the sort entirely. [PG-DOCS][UTIL]

## Batching and round trips

- Latency is dominated by round trips, not by row math, on a healthy database. Prefer
  set-based operations (one statement over many rows) to row-at-a-time loops; prefer
  `createMany`/batched writes to per-row inserts. [HPJP][RELEASEIT]

## Watch-list

N+1 (loop of queries, `Promise.all(map(query))`); over-fetch (`SELECT *`, `include`
over `select`, whole-graph loads); offset pagination on large or deep lists;
`COUNT(*)` for a total on a large table; count inside a loop; missing index on a join
or filter key; sort with no supporting index; row-at-a-time writes where a batch
would serve.
