<p align="center">
  <picture>
    <img <img src="https://github.com/user-attachments/assets/66923b92-55e5-4a18-a088-672e949082b8" width="250" alt="Argus, the many-eyed AI Database Architect.">
  </picture>
</p>

<h1 align="center">ARGUS</h1>

<p align="center">
  <em>The many-eyed AI Database reviewer. Sees everything. Never guesses.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/github/stars/hugoassisj/argus-db?style=flat-square&color=111111&label=stars" alt="Stars">
  <img src="https://img.shields.io/github/v/release/hugoassisj/argus-db?style=flat-square&color=111111&label=release" alt="Release">
  <img src="https://img.shields.io/badge/license-MIT-111111?style=flat-square" alt="MIT license">
</p>

<sub>Argus reviews the database layer of a change the way a principal engineer would, and tells you plainly whether it is safe to ship. Not a linter. Every finding carries evidence, reasoning, impact now and at scale, a concrete fix, the trade-off, and a confidence level. The review ends with a real approval decision, the kind a staff engineer would put their name on.</sub>

## Review your database like a Staff Engineer.

Deep AI-assisted reviews of:

- ✓ Prisma Schema
- ✓ PostgreSQL
- ✓ Indexes
- ✓ Relations
- ✓ Migrations
- ✓ Performance
- ✓ Big-O complexity
- ✓ Security
- ✓ Scalability
- ✓ Architecture

Generates:
- Executive summary
- Risk assessment
- Mermaid diagrams
- Performance analysis
- Actionable improvements

## Why this exists

Most database reviews are a rubber stamp. The schema diff looks fine, the migration
applies cleanly in staging, someone types "LGTM," and it merges. Then:

- The query that returned in 3ms at 10k rows starts timing out at 10M, because the
  index everyone assumed was there is in the wrong column order and never drove the
  filter.
- The migration that ran instantly on an empty table takes an `ACCESS EXCLUSIVE` lock
  and freezes writes for eleven minutes at 2am, because it added a `NOT NULL` column to
  a populated table.
- The `password` column ships as plaintext, because the review was looking at Prisma
  syntax, not at what the data layer will still owe you five years from now.

None of these are typos. A linter cannot catch them, because catching them takes
reasoning about access patterns, data growth, lock behavior, and blast radius. That
reasoning is exactly what Argus brings to the review.

## See it in action

Point Argus at a schema and it does not say "consider adding an index." It says this:

> **Finding.** The composite index on `Order` leads with `createdAt`, so the equality
> filter on `customerId` cannot use it.
>
> **Evidence.** `schema.prisma`, `model Order`: `@@index([createdAt, customerId])`,
> serving `WHERE customerId = ? ORDER BY createdAt DESC`.
>
> **Reasoning.** A B-tree composite index is only seekable on a leading prefix. With
> `createdAt` first, PostgreSQL cannot jump to one customer's rows; it scans and then
> filters. The index looks present but does nothing for this query.
>
> **Impact.** Today, at a few thousand orders, the scan is invisible. At 10M orders
> across 100k customers, every customer's order page reads the whole index instead of
> roughly a hundred rows, turning an `O(log n)` seek into an `O(n)` scan on one of your
> hottest read paths.
>
> **Recommendation.** Lead with the equality column:
> `@@index([customerId, createdAt(sort: Desc)])`. The index now seeks to the customer
> and returns rows already ordered, so the `ORDER BY` needs no sort step.
>
> **Trade-off.** One more index to maintain on write, negligible against the read win.
> If orders are never queried by customer, drop the index rather than reorder it.
>
> **Confidence.** High on the defect (it follows from B-tree mechanics, independent of
> data size). Medium on the magnitude without production row counts.

That is one finding. A full review ranks every finding by severity, lists what the
change gets right, surfaces where two specialists disagree, and ends with a verdict.

## What makes the reviews senior-level

- **Evidence-first, or it is dropped.** A finding ships only if it carries the full
  chain: finding, evidence at a concrete location, reasoning, impact, recommendation,
  trade-off, confidence. "Consider adding an index" with no query behind it does not
  make the cut.
- **It reviews only what changed.** A dispatcher decides which specialists to wake based
  on the actual artifacts. A migration file does not wake the query-performance lens; a
  repository method does not wake the migration lens. The report says which lenses ran,
  which it skipped, and why.
- **Grounded in canonical sources.** Recommendations lean on official docs and standard
  references (PostgreSQL and Prisma docs, Kleppmann, Petrov, Winand, Karwin, Ambler and
  Sadalage, Fowler, Nygard) over passing opinion. See
  [`skills/review/references/bibliography.md`](skills/review/references/bibliography.md).
- **Reasoning and facts are kept apart.** Lenses hold *how to review*. A tiered
  knowledge base holds *what is true*. The knowledge base tracks new Prisma and
  PostgreSQL releases without rewriting a single lens.
- **Honest when the specialists disagree.** When performance says denormalize and
  data-model says do not, Argus presents both and synthesizes one recommendation with
  the condition under which each is right, instead of pretending there is a single
  answer.

## How it works

A dispatcher wakes only the lenses a change needs, each lens reasons over a shared,
source-keyed knowledge base, every finding passes a hard evidence gate (and names the rule it
rests on), and a synthesis step reconciles the lenses into one verdict. The full flow, with
diagrams, is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md); a complete worked review is in
[`docs/example-review.md`](docs/example-review.md).

## How Argus differs from other database-review tools

Most community database agents are a single-file persona prompt. Argus is a dispatched review
board with a contract behind it.

| Capability | Typical single-file DB agent | Argus |
| --- | --- | --- |
| Form | one persona prompt | multi-file dispatched board |
| Evidence gate per finding | — | ✓ |
| Cited, tiered knowledge base | — | ✓ (every source actually used) |
| Grounding key on each Critical/High finding | — | ✓ |
| Severity rubric + explicit approval verdict | — | ✓ |
| False-positive / golden-project validation | — | ✓ (reject, approve, and approve-with-conditions cases) |
| Independent per-lens review mode | — | ✓ (`--board`) |

The trade-off is deliberate: Argus is focused (PostgreSQL/Prisma) and deep, rather than broad
and shallow.

## Meet the board

Eight specialists, each with a narrow mandate and a persona:

| Lens | Reviews | Protects against |
| --- | --- | --- |
| data-model | Normalization, cardinality, constraints, ownership | Duplicated concepts, nullable abuse, leaky models |
| indexing | Index presence, order, coverage, cost | Missing, redundant, and write-amplifying indexes |
| query-performance | Query shape, fetching, pagination | N+1, over-fetch, offset pagination, fan-out |
| migrations | Migration safety and rollout | Locks, table rewrites, breaking changes, no rollback |
| scalability | Growth behavior | Designs that degrade non-linearly as data grows |
| security | DB-facing security | Injection, PII exposure, missing RLS, secrets in the DB |
| prisma | Prisma idioms and API usage | ORM anti-patterns, misuse, future migration pain |
| backend-data-access | The service and repository layer | Bad transaction boundaries, pool exhaustion, races |

The engine is portable and project-agnostic. Drop it into any project on a relational
database. The core lenses work for any SQL project; Prisma and backend specifics live in
their own lenses, and Argus lowers its own confidence and says so when it meets an engine
it knows less well.

## Install

From this GitHub repository:

```
/plugin marketplace add hugoassisj/db-review-framework
/plugin install argus@argus
```

Or try it locally without installing:

```
claude --plugin-dir /path/to/db-review-framework
```

After installing, the skill is available as `/argus:review`.

## Usage

```
/argus:review
```

- **Diff mode (default).** With no argument, it reviews the current uncommitted or
  branch changes, dispatching lenses per changed artifact.
- **Audit mode.** Pass a path to review a whole schema or module, for example
  `/argus:review prisma/schema.prisma` or `/argus:review src/orders`.
- **Board mode.** Add `--board` to run each engaged lens as an independent reviewer and
  synthesize their findings — slower and costlier, for high-stakes changes. Example:
  `/argus:review --board prisma/schema.prisma`.

If a database connection and `psql` or `prisma` are available and you allow it, Argus
can raise its confidence with read-only `EXPLAIN` and index-existence checks. It never
runs destructive or write statements. With no database attached it stays static and
tells you so in the confidence reason.

## How it is organized

```
skills/review/
  SKILL.md         operational contract: dispatcher, modes, gates, report format
  FRAMEWORK.md     philosophy contract: principles, metrics, synthesis protocol
  lenses/          reasoning: how each specialist reviews
  references/      knowledge base: distilled facts, tiered bibliography
  evals/           machine-gradable evaluations (skill-creator schema)
validation/
  golden-project-01/   a broken project seeded with known smells (must be rejected)
  golden-project-02/   a clean, well-built project (must be approved)
  golden-project-03/   a correct-but-conditional project (approve with conditions)
docs/
  ARCHITECTURE.md      the flow and analytical approach, with diagrams
  example-review.md    a full worked review
```

## Validation

Argus is validated against golden projects: small, synthetic samples with a declared
list of what a passing review must (and must not) find. Three ship today, holding Argus to
all three verdict branches:

- **`golden-project-01`** seeds known smells across schema, queries, and a migration.
  A passing review surfaces every one and refuses to approve.
- **`golden-project-02`** is genuinely well-built, with traps that look like smells but are
  correct in context (a parameterized raw query, a tiny lookup table with no extra index, a
  justified denormalization). A passing review flags none and approves — the false-positive
  guard that proves Argus has the restraint to say "ship it."
- **`golden-project-03`** is correct-but-conditional: well built, but its safety depends on
  runtime facts a static review cannot confirm (RLS wiring, a denormalized total's writer, a
  retention job). A passing review approves *with named conditions* — the third verdict branch.

Two layers check this. `scripts/validate.py` runs in CI and checks structure
deterministically (manifests, the citation graph, the lens/domain and cross-lens handoff maps,
and that the evals stay bound to the fixtures). The reviews themselves are graded against
[`skills/review/evals/evals.json`](skills/review/evals/evals.json) — a machine-gradable set in
the [skill-creator](https://github.com/anthropics/claude-plugins-official) schema — with that
plugin, or locally with `python3 scripts/run_evals.py`.

See [`validation/README.md`](validation/README.md) to run the checks or add your own golden
project.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. In short:

- Add a **lens** by following the section structure in an existing
  `skills/review/lenses/*.md` and declaring its knowledge domains. See the "How to add a
  lens" section of `FRAMEWORK.md`. Keep the dispatch table in `SKILL.md` and the
  lens-to-domain map in `references/README.md` in sync (CI enforces this).
- Add a **benchmark** by creating `validation/golden-project-NN/` with a sample project
  and an `expected-findings.md`. See `validation/README.md`.
- Knowledge lives in `references/`, keyed to the tiered bibliography. Prefer canonical
  sources.

Run the deterministic checks locally with `python3 scripts/validate.py` (the same check
CI runs). Participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Security

To report a vulnerability, or to understand the plugin's read-only, consent-gated
database access, see [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).
