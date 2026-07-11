# Knowledge: Data modeling

Distilled modeling facts and named antipatterns. Sources **[SQLAP]**, **[DMMS]**,
**[DDIA]**, with aggregate boundaries from **[DDD]**/**[LDDD]**.

## Named antipatterns (Karwin)

- **Jaywalking:** storing a comma-separated list in one column instead of a related
  table. Breaks joins, constraints, and indexing on the members. Model it as rows.
  [SQLAP]
- **Entity-Attribute-Value (EAV):** a generic `(entity, attribute, value)` table to
  avoid defining columns. Destroys type safety, constraints, and query-ability; every
  read reassembles a row from many. Sometimes justified for truly open user-defined
  fields, but never as the default. A wide `Json` blob is the modern EAV; the same
  trade-off applies. [SQLAP]
- **Polymorphic association:** one nullable FK column plus a "type" column pointing at
  different parent tables, which no foreign key can enforce. Prefer separate FK columns
  or a join table per relationship. [SQLAP]
- **Naive trees (adjacency list only):** `parent_id` alone makes subtree queries
  require recursion or many round trips. On PostgreSQL use a recursive CTE, or a
  materialized path / closure table when subtree reads are hot. [SQLAP]
- **ID-required / keyless confusion:** a surrogate `id` on every table by reflex, even
  where a natural key is the correct unique constraint; or, conversely, no unique
  constraint at all. Keys express meaning; choose deliberately. [SQLAP][DMMS]

## Cardinality and ownership

- Get the cardinality right: one-to-one, one-to-many, many-to-many. A relationship
  modeled at the wrong cardinality (a one-to-many that is really many-to-many)
  forces duplication or loses data. [DMMS]
- Ownership and lifecycle: which entity owns the row, and what happens to children
  when the parent dies (cascade, restrict, orphan). This drives referential actions
  and is a modeling decision, not an ORM default. [DDD]
- Aggregate boundaries: a cluster of objects that must stay consistent together is an
  aggregate with one root; keep transactional invariants inside one aggregate, and
  reference other aggregates by id. This maps directly to transaction boundaries in
  `backend-data-access.md`. [DDD][LDDD]

## Nullability, defaults, and constraints

- A column marked optional should mean genuinely-sometimes-absent, not "we were unsure."
  Nullable-that-should-not-be pushes ambiguity onto every reader. Prefer `NOT NULL`
  with a sensible default. [DMMS][SQL-STD]
- Enumerated domains belong in an enum or a lookup table with a FK, not a free-text
  column that drifts into "active", "Active", "ACTIVE". Between the two: a database
  `enum` is compact and self-documenting but rigid to evolve (values cannot be removed
  or reordered, and adding one has transaction limits on PostgreSQL); a lookup table
  with a FK costs a join but lets you add, deprecate, and annotate values freely and can
  carry metadata. Prefer the enum for a small, stable, closed set; the lookup table when
  the domain will change or needs attributes. [PG-DOCS][DMMS]

## JSON columns

- `Json` is right for genuinely schemaless, pass-through, or rarely-read payloads. It
  is wrong for data you filter, join, aggregate, sort, or constrain; that data wants
  columns. Heavy `Json` use (many models, many fields) is a modeling smell to weigh
  against the flexibility it buys. [SQLAP][PG-DOCS]

## Soft delete and audit

- Soft delete (a `deleted` boolean or a `deleted_at` timestamp) keeps rows for
  recovery and audit but taxes every query, index, and unique constraint (which must
  now be partial). `deleted_at` carries more information (when) than a boolean and
  supports retention. Decide deliberately and index for it (partial index on the live
  rows). [REFDB][PG-DOCS]
- Audit fields (`created_at`, `updated_at`, and often `created_by`) are cheap and
  widely expected; their absence on a mutable business table is worth flagging.

## Watch-list

Comma-separated list in a column (jaywalking); generic key-value or wide `Json` blob
(EAV); type-column plus single nullable FK (polymorphic); `parent_id`-only tree with
hot subtree reads; wrong cardinality; missing ownership or cascade decision; nullable
that should be `NOT NULL`; free-text where an enum or lookup belongs; `Json` holding
queryable data; soft delete without partial indexes; missing audit fields.
