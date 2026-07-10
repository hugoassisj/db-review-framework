# db-review

A principal-engineer **database review board** for Claude Code.

`db-review` reviews the database layer of a change the way an experienced staff
engineer would: relational schema design, Prisma models, migrations, indexing,
query performance, scalability, DB security, and the DB-related backend code that
sits on top. It is not a linter. Every finding carries evidence, reasoning,
impact, a concrete recommendation, trade-offs, and a confidence level, and the
review ends with an explicit approval decision.

The engine is portable and project-agnostic. Drop it into any project that uses a
relational database. The core lenses work for any SQL project; Prisma and backend
specifics live in their own lenses.

## What makes the reviews senior-level

- **Evidence-first.** A finding is only emitted if it carries the full chain:
  finding, evidence (a concrete code location), reasoning, impact (now and at
  scale), recommendation, trade-offs, confidence. "Consider adding an index" with
  no query behind it is dropped, not shown.
- **Intelligent dispatch.** A dispatcher decides which specialists to engage based
  on what actually changed. A migration file does not wake the query-performance
  lens; a repository method does not wake the migration lens. The report says
  which lenses ran and which it skipped and why.
- **Grounded in canonical sources.** Recommendations prefer official docs and
  standard references (PostgreSQL and Prisma docs, Kleppmann, Petrov, Winand,
  Karwin, Ambler and Sadalage, Fowler, Nygard) over transient opinion. See
  [`skills/review/references/bibliography.md`](skills/review/references/bibliography.md).
- **Reasoning and facts are separate.** Lenses hold *how to review*; a tiered
  knowledge base holds *what is true*. The knowledge base evolves as Prisma and
  PostgreSQL ship new releases without rewriting a single lens.
- **Honest about disagreement.** When two lenses conflict (performance says
  denormalize, data-model says do not), the report presents both and synthesizes
  a recommendation instead of pretending there is one answer.

## Install

From a hosted GitHub repository:

```
/plugin marketplace add your-github-username/db-review-framework
/plugin install db-review@db-review-framework
```

Or test locally without installing:

```
claude --plugin-dir /path/to/db-review-framework
```

After installing, the skill is available as `/db-review:review`.

## Usage

```
/db-review:review
```

- **Diff mode (default).** With no argument, it reviews the current uncommitted or
  branch changes, dispatching lenses per changed artifact.
- **Audit mode.** Pass a path to review a whole schema or module, for example
  `/db-review:review prisma/schema.prisma` or `/db-review:review src/orders`.

If a database connection and `psql` or `prisma` are available and permitted, the
review can opt into live `EXPLAIN` and index-existence checks to raise its
confidence. Otherwise it stays static and says so.

## The lenses

| Lens | Reviews | Protects against |
| --- | --- | --- |
| data-model | Normalization, cardinality, constraints, ownership | Duplicated concepts, nullable abuse, leaky models |
| indexing | Index presence, order, coverage, cost | Missing, redundant, and write-amplifying indexes |
| query-performance | Query shape, fetching, pagination | N+1, over-fetch, offset pagination, fan-out |
| migrations | Migration safety and rollout | Locks, table rewrites, breaking changes, no rollback |
| scalability | Growth behavior | Designs that degrade non-linearly as data grows |
| security | DB-facing security | Injection, PII exposure, missing RLS, secrets in DB |
| prisma | Prisma idioms and API usage | ORM anti-patterns, misuse, future migration pain |
| backend-data-access | The service and repository layer | Bad transaction boundaries, pool exhaustion, races |

## How it is organized

```
skills/review/
  SKILL.md         operational contract: dispatcher, gates, report format
  FRAMEWORK.md     philosophy contract: principles, metrics, protocols
  lenses/          reasoning: how each specialist reviews
  references/      knowledge base: distilled facts, tiered bibliography
validation/
  golden-project-01/   a synthetic project seeded with known smells, plus the
                       findings a passing review must surface
```

## Contributing

- Add a **lens** by following the section structure in an existing
  `skills/review/lenses/*.md` and declaring its knowledge domains. See the "How to
  add a lens" section of `FRAMEWORK.md`.
- Add a **benchmark** by creating `validation/golden-project-NN/` with a sample
  project and an `expected-findings.md`. See `validation/README.md`.
- Knowledge lives in `references/`, keyed to the tiered bibliography. Prefer
  canonical sources.

## License

MIT. See [LICENSE](LICENSE).
