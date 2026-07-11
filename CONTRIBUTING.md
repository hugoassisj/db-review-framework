# Contributing to Argus

Thanks for your interest in improving Argus. This project is a Claude Code
plugin: its "code" is structured Markdown (an orchestrator skill, a framework
contract, review lenses, and a tiered knowledge base) plus a validation harness.
Contributions are held to the same evidence-first standard the reviewer itself
enforces.

Please also read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Repository layout

```
skills/review/
  SKILL.md         operational contract: dispatcher, gates, report format
  FRAMEWORK.md     philosophy contract: principles, metrics, protocols
  lenses/          reasoning: how each specialist reviews
  references/      knowledge base: distilled facts, tiered bibliography
  evals/           machine-gradable evaluations (skill-creator schema)
validation/
  golden-project-NN/   a synthetic project seeded with known smells, plus the
                       findings a passing review must surface
docs/                  ARCHITECTURE.md (the flow, with diagrams) and a worked example
```

New here? [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) explains the flow and analytical
approach end to end.

The guiding split: **lenses hold reasoning** (how to review), **references hold
facts** (what is true). Keep them separate. See
[`skills/review/references/README.md`](skills/review/references/README.md).

## Ways to contribute

### Add or change a lens

Follow the section structure of an existing
[`skills/review/lenses/*.md`](skills/review/lenses) and declare its knowledge
domains in the header. See the **"How to add a lens"** section of
[`skills/review/FRAMEWORK.md`](skills/review/FRAMEWORK.md).

When you add or rename a lens you **must** keep these in sync:

- the dispatch table in [`skills/review/SKILL.md`](skills/review/SKILL.md);
- the lens → knowledge-domain dependency map in
  [`skills/review/references/README.md`](skills/review/references/README.md).

The CI structural check fails if these drift apart.

### Add or change knowledge

Knowledge lives in [`skills/review/references/`](skills/review/references), keyed to
the tiered bibliography. Prefer canonical sources (Tier 1: official Prisma /
PostgreSQL / SQL-standard docs) over transient opinion. A digest is a set of rules a
reviewer reasons from, not a link dump. A Critical or High finding may never rest on
the provenance tier alone. See
[`skills/review/references/bibliography.md`](skills/review/references/bibliography.md).

### Add a golden project (benchmark)

Create `validation/golden-project-NN/` with a small, **synthetic** sample project and
an `expected-findings.md` written first, so the fixture is built to prove specific
behavior, and add an entry for it to
[`skills/review/evals/evals.json`](skills/review/evals/evals.json) (the deterministic
eval↔fixture check in CI fails otherwise). See the **"How to add a golden project"**
section of [`skills/review/FRAMEWORK.md`](skills/review/FRAMEWORK.md) and
[`validation/README.md`](validation/README.md). Never commit a real, proprietary
schema.

## Standards for a finding-related change

Any change to reviewer behavior should uphold the contract in `FRAMEWORK.md`:

- Every finding carries the full evidence chain: finding → evidence (`path:line`) →
  reasoning → impact (now and at scale) → recommendation → trade-offs → confidence.
- No generic filler ("follow best practices"). Every sentence must be specific.
- Recommendations name the query/access pattern they serve and state their trade-off.

## Submitting a change

1. Fork and branch from `main`.
2. Make your change; keep the dispatch table and domain map in sync (see above).
3. If behavior changed, update the affected `validation/**/expected-findings.md`.
4. Add a `CHANGELOG.md` entry under an `Unreleased` or the next version heading, and
   bump the version in `.claude-plugin/plugin.json` if you cut a release.
5. Validate locally:
   - `python3 scripts/validate.py` (the same deterministic check CI runs);
   - optionally load the plugin and re-run the golden project:
     `claude --plugin-dir .` then `/argus:review validation/golden-project-01/schema.prisma`.
6. Open a pull request and fill in the template.

## Versioning

The repository follows [Semantic Versioning](https://semver.org). The framework
contract (`FRAMEWORK.md`) carries its own contract version and only changes when the
*reasoning* changes, not when facts are updated. See
[`CHANGELOG.md`](CHANGELOG.md).
