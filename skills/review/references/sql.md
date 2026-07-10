# Knowledge: SQL

Vendor-neutral relational facts. Sources **[SQL-STD]**, **[SPE]**, **[UTIL]**.

## The relational baseline

- A primary key uniquely identifies a row and must be stable; do not key on data that
  changes (email, name). A natural key is fine when it is genuinely immutable and
  narrow; otherwise a surrogate key. [DMMS]
- A foreign key declares and enforces a relationship. Missing FKs let orphan rows and
  referential drift accumulate silently. [DMMS][SQLAP]
- Constraints (`NOT NULL`, `UNIQUE`, `CHECK`, FK) are the cheapest correctness
  guarantee available: enforced by the database, impossible to forget in application
  code. A rule that should always hold belongs in a constraint, not only in code.

## Normalization

- Normal forms remove redundancy so a fact is stored once. 3NF is the practical
  default for OLTP: every non-key attribute depends on the key, the whole key, and
  nothing but the key. [DMMS]
- Under-normalization (the same fact duplicated across rows or tables) creates update
  anomalies: the copies drift. Over-normalization (splitting cohesive attributes
  across many tables) creates join-heavy read paths with no integrity benefit. Both
  are findings; name which one. [DMMS][SQLAP]
- Denormalization is a deliberate, measured trade: faster reads for the cost of
  keeping copies consistent on write. It is justified by a measured hot read, not by
  default (see `performance.md` and the cross-lens protocol).

## Nullability

- `NULL` means "unknown or not applicable," and it is not equal to anything (including
  `NULL`); it changes the truth of predicates and the result of aggregates. A column
  that always has a meaningful value should be `NOT NULL` with a default. A column
  marked optional "just in case" is an ambiguity every consumer must handle. [SQL-STD]

## Isolation levels

- Read Committed (many databases' default) prevents dirty reads but allows non-
  repeatable reads and phantoms; Repeatable Read adds snapshot stability; Serializable
  prevents all anomalies at the cost of possible serialization failures the
  application must retry. Choose per invariant; the read-modify-write of a balance or
  a counter needs more than Read Committed or explicit locking. [SQL-STD][DDIA]
- The lost-update problem (two transactions read then write the same row) is not
  prevented by Read Committed. Use an atomic update, optimistic locking (a version
  column), or `SELECT … FOR UPDATE`. [DDIA][HPJP]

## Query building blocks

- Window functions compute per-row aggregates without collapsing rows; a CTE names a
  subquery; a recursive CTE walks hierarchies (the correct tool for adjacency-list
  trees, see `modeling.md`). These are often where raw SQL is legitimately needed.
  [SQL-STD]
- `COUNT(*)` over a large table is a full scan or full index scan; it is not free.
  Counting inside a loop multiplies that cost (see `performance.md`).

## Watch-list

Mutable or wide primary key; missing foreign key; a rule enforced only in code that a
`CHECK`/`UNIQUE` could enforce; nullable column that should be `NOT NULL`;
duplicated fact (update anomaly) vs excessive joins (over-normalization); read-modify-
write without atomicity or locking; default isolation assumed sufficient for a
balance or counter.
