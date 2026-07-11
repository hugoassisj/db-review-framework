# Bibliography

Master citation list. Digests and lenses cite by the short key in brackets. Sources
are grouped by authority tier; recommendations prefer higher tiers, and a Critical
or High finding is never based on the provenance tier alone.

## Tier 1: Canonical (official docs and standards)

- **[PRISMA-DOCS]** Prisma ORM documentation. https://www.prisma.io/docs
  Key areas: Prisma Schema reference, Prisma Client API, relation queries (`select`
  vs `include`), relations and referential actions, `relationMode`, indexes
  (`@@index`, `@@unique`), connection management and `connection_limit`, transactions
  (`$transaction` and interactive transactions), Prisma Migrate, raw queries and
  `$queryRaw` tagged-template safety, upgrade guides, and release notes.
- **[PG-DOCS]** PostgreSQL documentation. https://www.postgresql.org/docs/current/
  Key areas: indexes and index types (B-tree, GIN, GiST, BRIN, Hash), the query
  planner and `EXPLAIN`, MVCC and VACUUM, HOT updates, the visibility map, locking
  and lock levels, WAL, table partitioning, JSONB, row-level security, `CREATE INDEX
  CONCURRENTLY`, and DDL locking behavior.
- **[SQL-STD]** ANSI/ISO SQL standard (conceptual). Isolation levels, constraints,
  window functions, CTEs, and the relational model as the vendor-neutral baseline.

## Security references (Tier 1-equivalent)

Canonical, vendor-neutral security guidance. Treated as Tier-1-equivalent for the
security domain (see the domain-to-source map in `README.md`).

- **[OWASP-SQLI]** OWASP SQL Injection Prevention Cheat Sheet.
  https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
  Parameterized queries, safe handling of dynamic identifiers (allowlisting), and why
  string-built SQL is unsafe.
- **[OWASP-CRYPTO]** OWASP Cryptographic Storage Cheat Sheet.
  https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
  Password hashing (slow, salted), secrets and PII encryption at rest, and envelope
  encryption with a KMS-managed master key.
- **[OWASP-ASVS]** OWASP Application Security Verification Standard.
  https://owasp.org/www-project-application-security-verification-standard/
  Access control and mass-assignment defenses, least privilege, and logging of
  sensitive data.

## Tier 2: Essential books

- **[DBI]** Alex Petrov, *Database Internals* (O'Reilly, 2019). Storage engines,
  B-trees and LSM-trees, MVCC, transactions, WAL, distributed systems.
- **[DDIA]** Martin Kleppmann, *Designing Data-Intensive Applications* (O'Reilly,
  2017). Data models, storage and retrieval, replication, partitioning, transactions,
  consistency, batch and stream processing.
- **[SPE]** Markus Winand, *SQL Performance Explained* (2012). Indexes, execution
  plans, joins, predicates, clustering, sorting and grouping, pagination.
- **[UTIL]** Markus Winand, *Use The Index, Luke!* https://use-the-index-luke.com
  The web companion to SPE; keyset ("no offset") pagination, index-only scans,
  composite index column order.
- **[MPG]** Hans-Jürgen Schönig, *Mastering PostgreSQL* (Packt). Advanced PostgreSQL:
  planner behavior, indexing strategy, partitioning, and administration.

## Tier 3: Modeling

- **[SQLAP]** Bill Karwin, *SQL Antipatterns* (Pragmatic Bookshelf, 2010). Jaywalking,
  Entity-Attribute-Value, polymorphic associations, naive trees (adjacency list),
  ID-required, and reference antipatterns.
- **[DMMS]** Steve Hoberman, *Data Modeling Made Simple*. Entities, relationships,
  normalization, keys, and cardinality for practitioners.
- **[REFDB]** Scott Ambler and Pramod Sadalage, *Refactoring Databases: Evolutionary
  Database Design* (Addison-Wesley, 2006). Database refactorings, the expand/contract
  (parallel-change) pattern, transition periods, and safe schema evolution.

## Tier 4: Domain and architecture

- **[DDD]** Eric Evans, *Domain-Driven Design* (Addison-Wesley, 2003). Entities,
  value objects, aggregates, aggregate boundaries, invariants.
- **[LDDD]** Vlad Khononov, *Learning Domain-Driven Design* (O'Reilly, 2021). A
  modern, practical treatment of the same.
- **[APOSD]** John Ousterhout, *A Philosophy of Software Design* (2018). Complexity,
  deep vs shallow modules, information hiding; used to detect unnecessary complexity.
- **[POEAA]** Martin Fowler, *Patterns of Enterprise Application Architecture*
  (Addison-Wesley, 2002). Repository, Unit of Work, Identity Map, Data Mapper,
  optimistic and pessimistic offline lock.
- **[RELEASEIT]** Michael Nygard, *Release It!* (Pragmatic Bookshelf, 2nd ed. 2018).
  Connection-pool sizing, timeouts, bulkheads, circuit breakers, stability
  antipatterns.
- **[HPJP]** Vlad Mihalcea, *High-Performance Java Persistence*. ORM-agnostic
  treatment of N+1, batching, connection-pool sizing, isolation levels, optimistic
  locking. Concepts transfer directly to Prisma.

## Provenance tier (further reading; never a sole basis for High or Critical)

- **[PLANETSCALE]** PlanetScale engineering blog. Online schema change, indexing at
  scale. https://planetscale.com/blog
- **[CRUNCHY]** Crunchy Data blog. PostgreSQL indexing, partitioning, `EXPLAIN`.
  https://www.crunchydata.com/blog
- **[DEPESZ]** explain.depesz.com and the depesz blog. Reading PostgreSQL query
  plans.
- **[GITHUB-ENG]** GitHub, Stripe, Shopify engineering blogs. Large-scale online
  migrations, expand/contract in production.
- **Papers** (conceptual grounding): the B-tree (Bayer and McCreight), the
  Log-Structured Merge-Tree (O'Neil et al.), ARIES (Mohan et al.), Dynamo (DeCandia
  et al.), Spanner (Corbett et al.).
