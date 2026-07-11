# Knowledge base

This directory is the framework's shared, evolving **facts**. Lenses hold the
*reasoning* (how to review); these digests hold *what is true* (about Prisma,
PostgreSQL, SQL, performance, modeling, and so on). The split lets the knowledge
base track new Prisma and PostgreSQL releases without rewriting a single lens.

Each `<domain>.md` file is a **distilled digest**: the rules, mechanisms, and
gotchas a reviewer must know, each keyed to a source in `bibliography.md`. A digest
is not a link dump. If a claim cannot be reduced to a rule the reviewer reasons
from, it does not belong here; it belongs in the provenance tier of the
bibliography as further reading.

## Tiering policy

Recommendations prefer higher tiers. When sources conflict, the higher tier wins.

- **Tier 1, Canonical.** Official documentation and standards: Prisma docs,
  PostgreSQL docs, ANSI/ISO SQL. Highest authority for behavior of the specific
  tools.
- **Tier 2, Essential books.** Petrov, Kleppmann, Winand, Schönig. The mechanisms
  behind the behavior.
- **Tier 3, Modeling.** Karwin, Hoberman, Ambler and Sadalage.
- **Tier 4, Domain and architecture.** Evans, Vernon, Khononov, Ousterhout, Fowler,
  Nygard, Mihalcea.
- **Provenance tier.** Respected engineering write-ups and seminal papers. Cited for
  authority and further reading only; never the sole basis for a Critical or High
  finding.

## Lens to knowledge-domain dependency map

The dispatcher loads a lens's declared domains alongside the lens. Keep this in sync
with each lens header.

| Lens | Knowledge domains loaded |
| --- | --- |
| data-model | modeling, sql, architecture |
| indexing | performance, postgresql, sql |
| query-performance | performance, postgresql, sql, prisma |
| migrations | migrations, postgresql, engineering |
| scalability | scalability, distributed-systems, postgresql |
| security | security, postgresql, prisma |
| prisma | prisma, postgresql, modeling, engineering |
| backend-data-access | engineering, architecture, performance, prisma |

## Domain to source-tier map

| Domain digest | Primary sources |
| --- | --- |
| prisma | PRISMA-DOCS (T1) |
| postgresql | PG-DOCS (T1), MPG, DBI |
| sql | SQL-STD (T1), SPE, UTIL |
| performance | UTIL, SPE (T2), PG-DOCS, HPJP |
| modeling | SQLAP, DMMS (T3), DDIA |
| migrations | REFDB (T3), PG-DOCS, provenance (zero-downtime write-ups) |
| security | OWASP-SQLI, OWASP-CRYPTO, OWASP-ASVS (T1-equivalent), PG-DOCS (RLS) |
| scalability | DDIA (T2), PG-DOCS (partitioning) |
| distributed-systems | DDIA (T2), papers (provenance) |
| architecture | POEAA, DDD, LDDD, APOSD (T4) |
| engineering | RELEASEIT, HPJP, APOSD (T4) |

## Updating on new releases

When Prisma or PostgreSQL ship a release that changes reviewer-relevant behavior:

1. Update the affected `<domain>.md` digest rule and its source key.
2. Add the release note or doc page to `bibliography.md` if it is a new canonical
   reference.
3. Bump the repository version in `CHANGELOG.md`. Lenses only change if the
   *reasoning* changed, not the facts.
