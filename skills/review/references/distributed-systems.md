# Knowledge: Distributed systems

Distilled facts for the scalability lens when a design crosses process or node
boundaries. Source **[DDIA]**; papers in the provenance tier.

## Replication and consistency

- Replication trades freshness for read capacity and availability. Asynchronous
  replicas lag; a read from a lagging replica can miss a just-committed write. Common
  guarantees: read-your-writes (route a user's reads to where their writes landed),
  monotonic reads (do not go backward in time), consistent prefix. Name which
  guarantee a feature needs before routing its reads. [DDIA]

## Transactions across boundaries

- A local database transaction is atomic; a "transaction" spanning two systems (the
  database and a message broker, a cache, or another service) is not. The dual-write
  problem (write the database, then publish an event) can leave the two inconsistent
  if the second step fails. The transactional outbox (write the event to an outbox
  table in the same database transaction, relay it separately) restores atomicity for
  the common case. [DDIA]
- Distributed transactions (two-phase commit) exist but are operationally heavy and
  block on the coordinator; prefer the outbox or idempotent, retryable steps. [DDIA]

## Idempotency and exactly-once

- Networks deliver at-least-once: retries and redeliveries happen. "Exactly-once
  effect" is achieved by making the operation idempotent (a natural key, an idempotency
  key, an upsert), not by hoping a message arrives once. Any consumer or webhook
  handler that is not idempotent is a correctness finding. [DDIA]

## Ordering and partitioning

- A partitioned/sharded system only guarantees ordering within a partition, not
  across. Choosing a partition key that co-locates the data that must be read or
  ordered together is the central design decision; the wrong key forces cross-partition
  queries and scatter-gather. [DDIA]

## Applying it

Most single-database Prisma applications do not need this domain; it is engaged by the
scalability lens only when the change introduces replicas, cross-service writes,
message consumers, or sharding. When it does not apply, say so rather than inventing
distributed concerns.

## Watch-list

Freshness-sensitive read on an async replica; dual write to database and broker
without an outbox; non-idempotent consumer or webhook handler; cross-partition
ordering assumed; a partition/shard key that scatters related data.
