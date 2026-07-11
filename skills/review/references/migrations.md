# Knowledge: Migrations

Distilled safe-migration facts. Sources **[REFDB]**, **[PG-DOCS]**, and production
write-ups **[GITHUB-ENG]**/**[PLANETSCALE]** (provenance).

## The core risk

A migration runs against a live database with concurrent traffic. The two failure
modes are **locks** (the migration blocks reads or writes while it runs) and
**breaking changes** (the new schema is incompatible with the currently-deployed
application, or the reverse). Every migration is reviewed for both. [REFDB]

## Locking on PostgreSQL

- `CREATE INDEX` locks the table against writes for the whole build. Use
  `CREATE INDEX CONCURRENTLY` for a live table; it does not block writes but runs
  outside a transaction, is slower, and leaves an invalid index if it fails (drop and
  retry). Note: Prisma Migrate wraps steps in a transaction, so a concurrent index
  usually needs a hand-edited migration or an out-of-band step. [PG-DOCS]
- A table-rewriting `ALTER TABLE` (some type changes; on older PostgreSQL, adding a
  column with a volatile default) holds `ACCESS EXCLUSIVE` and blocks everything for
  the rewrite. Adding a column with no default or a constant default on modern
  PostgreSQL is metadata-only and fast. [PG-DOCS]
- Adding `NOT NULL` or a foreign key validates every existing row under lock. Add the
  constraint `NOT VALID`, then `VALIDATE CONSTRAINT` in a separate step that takes a
  weaker lock. [PG-DOCS]
- Long transactions and large single-statement backfills hold locks and bloat WAL;
  backfill in bounded batches. [PG-DOCS][REFDB]
- **Set a short `lock_timeout` before a DDL statement and retry on timeout.** A statement
  waiting for `ACCESS EXCLUSIVE` blocks every query that queues behind it, so an `ALTER`
  that waits on one long-running transaction can freeze the whole table even when the
  `ALTER` itself is instant. `lock_timeout` makes the migration fail fast and retry
  instead of stalling production traffic. This is the difference between a safe metadata
  change and a self-inflicted outage. [PG-DOCS][GITHUB-ENG]
- Adding a foreign key locks both the referencing and referenced tables and validates
  existing rows. Add it `NOT VALID`, then `VALIDATE CONSTRAINT` in a separate step — the
  same expand-then-validate split used for `NOT NULL`. [PG-DOCS]
- Enum changes are a schema-evolution risk: `ALTER TYPE … ADD VALUE` has transaction
  restrictions and cannot remove or reorder values. Prefer a lookup table when the domain
  churns (see `modeling.md`). [PG-DOCS]

## Expand and contract (parallel change)

The safe pattern for any rename, type change, or restructuring, so the schema is
always compatible with both the old and new application version: [REFDB]

1. **Expand:** add the new column/table/index additively (nullable, no destructive
   change). Deploy.
2. **Migrate data and dual-write:** backfill in batches; have the application write
   both old and new.
3. **Switch reads:** point the application at the new shape once backfill is verified.
4. **Contract:** drop the old column/table in a later migration, after no code reads
   it.

A rename done as a single `RENAME COLUMN` breaks every running instance of the old
code the instant it commits; expand/contract avoids the flag-day.

## Reversibility and destructive operations

- A `DROP COLUMN`/`DROP TABLE` is irreversible with respect to its data. Prefer a
  deprecation period (stop writing, verify unused, then drop) over an immediate drop.
  [REFDB]
- Every migration should have a considered rollback. Some operations (a dropped
  column's data) cannot be rolled back; that is exactly why they need a transition
  period, not a fast path.

## Introspected schemas

- A database-first workflow (`prisma db pull`) can drift from the migration history,
  and two copies of a schema can diverge. Divergence between the schema and the actual
  database, or between two schema copies, is a first-class review target.

## Watch-list

`CREATE INDEX` without `CONCURRENTLY` on a live table; table-rewriting `ALTER TABLE`;
`NOT NULL`/FK added without `NOT VALID`; DDL run without a `lock_timeout` (lock-queue
pileup); unbatched backfill in one statement; a rename or type change done as a
flag-day instead of expand/contract; an enum `ALTER TYPE … ADD VALUE` treated as
routine; a `DROP` with no deprecation period; a migration with no rollback plan; schema
drift from the database or between schema copies.
