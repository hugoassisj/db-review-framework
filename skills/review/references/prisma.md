# Knowledge: Prisma

Distilled facts for reviewing Prisma schema and Prisma Client usage. Primary source
**[PRISMA-DOCS]**; engine behavior in `postgresql.md`.

## Fetching

- `select` returns only named fields; `include` returns the full related record.
  Default (neither) returns all scalar fields of the model. Prefer `select` on read
  paths; `include` pulls every column of the relation, which is over-fetch. [PRISMA-DOCS]
- Nested `include`/`select` each add a database round trip or a correlated fetch.
  Prisma resolves relations with separate queries by default, so a nested include on
  a list is a fan-out proportional to the parent count. This is the Prisma shape of
  N+1. [PRISMA-DOCS][HPJP]
- `findMany` with no `take` is an unbounded read. Every list read needs a bound.
- Relation loading in application code inside a loop (calling `prisma.x.findMany`
  per parent) is N+1; use a single query with a relation `select`, or a `where…in`
  batch. [HPJP]

## Relations and referential integrity

- Implicit many-to-many (a bare `A[]` / `B[]` on both sides) makes Prisma manage a
  hidden join table. Explicit many-to-many (a modeled join model) is required the
  moment the relationship carries its own fields (timestamps, role, ordering) or
  needs its own constraints or indexes. [PRISMA-DOCS]
- Referential actions (`onDelete`, `onUpdate`: `Cascade`, `Restrict`, `SetNull`,
  `NoAction`) are a data-integrity decision, not a default. `Cascade` deletes on a
  high-fanout parent can delete large subtrees in one statement; `SetNull` requires
  the FK column to be nullable. State the intent. [PRISMA-DOCS]
- `relationMode = "prisma"` (emulated referential integrity) removes database-level
  foreign keys and enforces relations in the client. It is for databases that lack FK
  support (some PlanetScale/Vitess setups). On PostgreSQL, prefer
  `relationMode = "foreignKeys"` so the database enforces integrity. Emulated mode
  also requires manual indexes on relation scalars. [PRISMA-DOCS]

## Indexes and constraints in the schema

- `@@index([a, b])` and `@@unique([a, b])` are declared in the schema and applied by
  Migrate. Composite column order matters exactly as in raw SQL (see `indexing.md`).
- Prisma does not auto-create an index on a foreign-key scalar. A relation you filter
  or join on needs an explicit `@@index`. [PRISMA-DOCS][UTIL]

## Mapping and naming

- `@map` (field to column) and `@@map` (model to table) reconcile idiomatic Prisma
  names with an existing schema. In an introspected (`db pull`) schema, snake_case
  model and field names are a signal the schema is database-first; drift between the
  Prisma schema and the database is then a real review target.

## JSON, types, and preview features

- `Json` columns are opaque to Prisma's type system and to relational querying. They
  are appropriate for genuinely schemaless or pass-through payloads, not for fields
  you filter, join, aggregate, or constrain. Overuse of `Json` is a modeling smell
  (see `modeling.md`). [PRISMA-DOCS][SQLAP]
- Preview features (`previewFeatures` in the generator) are unstable and can change
  or be removed. Depending on one in a production schema is a risk to call out.
  [PRISMA-DOCS]

## Transactions

- `$transaction([...])` (array form) runs independent writes atomically in one
  round trip; it does not let a later query read an earlier query's result.
- Interactive transactions (`$transaction(async (tx) => …)`) allow read-then-write
  logic but hold a connection and a database transaction open for the callback's
  duration. Long or chatty interactive transactions hold locks and starve the pool.
  Keep them short and side-effect-free. [PRISMA-DOCS][RELEASEIT]

## Connection management

- A `PrismaClient` owns a connection pool. Its size defaults from a formula but is
  set with `connection_limit` in the datasource URL. Multiple `PrismaClient`
  instances (a common mistake in hot-reload or serverless code) multiply pools and
  exhaust the database's `max_connections`. Instantiate once. [PRISMA-DOCS][RELEASEIT]
- In serverless and high-concurrency settings, front the database with a pooler
  (PgBouncer, Prisma Accelerate) and set `pgbouncer=true`/transaction mode
  accordingly. [PRISMA-DOCS]

## Raw SQL

- `$queryRaw`/`$executeRaw` with the tagged-template form parameterize inputs and are
  injection-safe. The `Unsafe` variants and string concatenation are not; treat any
  interpolated `$queryRawUnsafe` as a security finding (see `security.md`).
  [PRISMA-DOCS][OWASP-SQLI]
- Reaching for raw SQL is sometimes correct (a window function, a recursive CTE Prisma
  cannot express) but must be justified against the typed path.

## Watch-list

`findMany` without `take`; `include` where `select` suffices; nested `include` on a
list (fan-out); relation filter with no `@@index` on the FK scalar; per-parent query
in a loop; `Promise.all(items.map(() => prisma…))`; multiple `PrismaClient`
instances; long interactive transactions; `Json` used for queryable data; implicit
m-n that needs to be explicit; missing or unconsidered `onDelete`; `relationMode =
"prisma"` on a database that supports foreign keys; `$queryRawUnsafe` with
interpolation; reliance on a preview feature.
