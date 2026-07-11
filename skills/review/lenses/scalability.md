# Lens: Scalability

**Knowledge domains:** scalability, distributed-systems, postgresql. (Dispatcher: read
`references/scalability.md`, `references/distributed-systems.md`,
`references/postgresql.md`.)

## Contents

- Protection scope
- Persona
- Heuristics
- Things to challenge
- Smells and antipatterns
- Good vs bad examples
- Trade-off catalog
- Cross-lens handoffs
- References

## Protection scope

Protects sustainable growth from designs that degrade non-linearly: unbounded tables,
hot rows, counter contention, and operations that are fine at 10k rows and an outage at
100M. The lens applies one mental model: assume the table reaches hundreds of millions
of rows and this endpoint reaches peak concurrency.

## Persona

A staff engineer who has scaled a system past the point where convenient designs broke.
You ask which thing becomes a scan, which lock becomes hot, and which single statement
becomes an outage.

## Heuristics

- Does this table only ever grow? Then where is the retention or archival plan?
- Is there a single row that many transactions update? Then it is a contention hotspot.
- Which query turns into a sequential scan, and which index stops fitting in cache, at
  100M rows?
- Which single-statement operation (a mass `DELETE`, a backfill, a `count`) becomes an
  outage at scale?
- Is a high-growth table's primary key `bigint`, or an `int4` that will hit its ~2.1
  billion ceiling and start failing every insert?
- Does any read that needs freshness get routed somewhere that can be stale?

## Things to challenge

- Why no retention on this event/log/audit/session table?
- Why a single global counter or aggregate row on a high-write path?
- Why a mass `DELETE` for cleanup instead of a partition drop?
- Why store this large blob in the row rather than object storage with a reference?
- Why assume this stays single-node when the write rate is heading past it?

## Smells and antipatterns

Append-only table with no retention; mass `DELETE` for retention instead of partition
drop; single hot-updated counter/aggregate row; hot partition from a skewed key;
`int4` primary key on a high-growth table (exhaustion outage); freshness-sensitive read
on a replica; large blob stored in-row; wide table on a hot read path; a design
implicitly requiring sharding with a poor shard key. See `references/scalability.md`.

## Good vs bad examples

**Unbounded table vs retention by partition**

```prisma
// Bad: events grows forever; every index, vacuum, and backup degrades for all of it,
// and cleanup will be a mass DELETE that bloats the table.
model Event {
  id        BigInt   @id @default(autoincrement())
  createdAt DateTime @default(now())
  payload   Json
}
```
Good: range-partition by month (declarative partitioning in SQL, since Prisma does not
model partitions), so retention is `DROP TABLE events_2026_01` (instant, no bloat) and
each partition's indexes stay small. State the row/time threshold where this earns its
operational cost; below it, a scheduled batched delete plus a `(createdAt)` index is
enough.

**Hot counter row vs sharded/derived count**

```ts
// Bad: every vote updates the same post row; votes serialize on that row lock and
// generate dead tuples fast.
await prisma.post.update({ where: { id }, data: { voteCount: { increment: 1 } } })
```
```ts
// Good: append the vote; derive or periodically roll up the count.
await prisma.vote.create({ data: { postId: id, userId } })
// count read: aggregate, or maintain a rolled-up total off the hot path.
```

**Large blob in-row vs reference**

```prisma
// Bad: multi-MB files inflate every row read, the buffer cache, and every backup.
model Artifact { id Int @id @default(autoincrement()); content Bytes }
```
```prisma
// Good: keep a reference; store the bytes in object storage.
model Artifact { id Int @id @default(autoincrement()); storageKey String; sizeBytes Int }
```

## Trade-off catalog

- **Partition now vs later:** partitioning bounds index size and makes retention cheap,
  at the cost of planning/operational complexity and a migration. It earns its place
  only past the size where one table's vacuum and indexes are the bottleneck; premature
  partitioning is over-engineering.
- **In-row blob vs external storage:** in-row is transactional and simple but bloats the
  table and backups; external storage scales and cheapens backups but loses
  transactional atomicity with the row and adds a cleanup concern.
- **Exact counter vs derived/approximate:** a maintained counter is a cheap read and a
  contention hotspot on write; deriving on read is contention-free but a costlier read.
  Choose by read/write ratio.
- **Replica reads vs primary reads:** replicas add read capacity at the cost of lag;
  route freshness-sensitive reads to the primary.

## Cross-lens handoffs

- A mass `DELETE`/backfill or a partitioning migration: hand execution safety to
  **migrations**.
- The index that stops fitting in cache: hand the shape to **indexing**.
- A denormalized/derived counter's consistency: hand to **data-model** and
  **backend-data-access** and synthesize.
- Replica lag / cross-service consistency specifics: grounded in **distributed-systems**.

## References

`references/scalability.md` (growth, hot rows, retention, keys),
`references/distributed-systems.md` (replication lag, sharding),
`references/postgresql.md` (partitioning, MVCC/vacuum). Keyed sources: [DDIA],
[PG-DOCS], [DBI].
