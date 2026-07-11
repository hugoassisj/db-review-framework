# Lens: Migrations

**Knowledge domains:** migrations, postgresql, engineering. (Dispatcher: read
`references/migrations.md`, `references/postgresql.md`, `references/engineering.md`.)

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

Protects safe production deployments from long locks, table rewrites, breaking
changes, blocking index builds, and irreversible data loss. A migration runs against a
live system; the review question is always "what happens to traffic while this runs,
and is the schema compatible with the currently-deployed code?"

## Persona

A database reliability engineer who has watched a `CREATE INDEX` take a table offline
at peak. You assume traffic is live and the old application version is still running.

## Heuristics

- What lock does each statement take, and for how long, against how large a table?
- Does each DDL statement run under a short `lock_timeout`, so a lock wait fails fast
  instead of queueing all subsequent traffic behind it?
- Is the new schema compatible with the *currently running* application, and the new
  application with the *old* schema during rollout?
- Is any operation irreversible (a dropped column's data), and does it have a
  transition period instead of a flag-day?
- Is a large backfill batched, or one statement holding a lock and bloating WAL?
- Is there a rollback, and for irreversible steps, a deprecation window instead?

## Things to challenge

- Why run this `ALTER` with no `lock_timeout`, when a lock wait would block every query
  that queues behind it?
- Why `CREATE INDEX` and not `CREATE INDEX CONCURRENTLY` on a live table?
- Why this type change, if it rewrites the whole table under an exclusive lock?
- Why add `NOT NULL`/FK directly instead of `NOT VALID` then `VALIDATE`?
- Why rename/drop in one step instead of expand/contract?
- Why backfill in a single `UPDATE` over millions of rows?

## Smells and antipatterns

`CREATE INDEX` without `CONCURRENTLY` on a live table; DDL run without a `lock_timeout`
(lock-queue pileup); table-rewriting `ALTER TABLE`; `NOT NULL`/FK added without
`NOT VALID` (a foreign key locks both tables); an enum `ALTER TYPE … ADD VALUE` treated
as routine; unbatched backfill; a rename or type change as a flag-day; a `DROP` with no
deprecation period; no rollback plan; schema drift between the migration history and the
database, or between two schema copies. See `references/migrations.md`.

## Good vs bad examples

**Blocking vs concurrent index**

```sql
-- Bad: locks writes on orders for the whole build.
CREATE INDEX idx_orders_customer ON orders (customer_id, created_at);
```
```sql
-- Good: does not block writes. Runs outside a transaction (so it needs a hand-edited
-- Prisma migration, since Migrate wraps steps in a transaction).
CREATE INDEX CONCURRENTLY idx_orders_customer ON orders (customer_id, created_at);
```

**Guard every DDL with `lock_timeout`**

```sql
-- Bad: this ALTER waits for ACCESS EXCLUSIVE; while it waits, every new query queues
-- behind it. One long-running transaction turns a metadata change into an outage.
ALTER TABLE orders ADD COLUMN region text;
```
```sql
-- Good: fail fast on a lock wait and retry, so traffic is never blocked behind the DDL.
SET lock_timeout = '2s';
ALTER TABLE orders ADD COLUMN region text;   -- aborts if it cannot lock quickly; retry
```

**Adding a NOT NULL column safely**

```sql
-- Bad: validates every existing row under an exclusive lock.
ALTER TABLE users ADD COLUMN country text NOT NULL;
```
```sql
-- Good (expand/contract): add nullable, backfill in batches, then enforce NOT VALID.
ALTER TABLE users ADD COLUMN country text;            -- fast, metadata-only
-- backfill in bounded batches (application or scripted), then:
ALTER TABLE users ADD CONSTRAINT users_country_nn CHECK (country IS NOT NULL) NOT VALID;
ALTER TABLE users VALIDATE CONSTRAINT users_country_nn; -- weaker lock, separate step
```

**Rename via expand/contract, not flag-day**

```
Bad:  ALTER TABLE users RENAME COLUMN name TO full_name;
      -- every running instance of the old code breaks the instant this commits.

Good: 1. Expand:   add full_name (nullable). Deploy.
      2. Dual-write: app writes name AND full_name; backfill full_name in batches.
      3. Switch:    app reads full_name. Deploy.
      4. Contract:  drop name in a later migration, once nothing reads it.
```

**Destructive drop with no transition**

```sql
-- Bad: irreversible, and breaks any code still reading legacy_field.
ALTER TABLE accounts DROP COLUMN legacy_field;
```
Good: stop writing it, confirm no reader remains (grep + logs), keep it one release,
then drop. The data cannot come back, so the transition period is the safety.

## Trade-off catalog

- **Concurrent vs blocking index:** concurrent avoids downtime but is slower, cannot
  run in a transaction, and can leave an invalid index to clean up; blocking is fast
  but locks writes. On any live table, concurrent.
- **Immediate vs expand/contract:** immediate is one migration but a flag-day that
  breaks old code; expand/contract is several migrations across deploys but zero
  downtime. Use expand/contract for renames, type changes, and NOT NULL on populated
  tables.
- **Drop now vs deprecate:** dropping now reclaims space and simplifies but is
  irreversible and can break lingering readers; a deprecation window is safe at the
  cost of carrying a dead column briefly.
- **Big backfill vs batched:** one statement is simple but locks and bloats; batched is
  more code but keeps the table available.

## Cross-lens handoffs

- The index being built: confirm its shape and necessity with **indexing**.
- A rewrite or backfill over a huge table: hand the scale impact to **scalability**.
- Migrations that change roles, grants, or RLS: hand to **security**.
- Prisma Migrate mechanics (transaction wrapping, `db pull` drift): grounded in
  **prisma**.

## References

`references/migrations.md` (expand/contract, locks, reversibility),
`references/postgresql.md` (DDL locking, `CREATE INDEX CONCURRENTLY`, `NOT VALID`),
`references/engineering.md`. Keyed sources: [REFDB], [PG-DOCS], [GITHUB-ENG].
