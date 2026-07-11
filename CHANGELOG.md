# Changelog

All notable changes to Argus are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The framework contract (`skills/review/FRAMEWORK.md`) carries its own contract
version. Individual lenses and knowledge-base digests do not version separately;
they move with the repository version below.

## [Unreleased]

## [1.1.0] - 2026-07-11

### Added

- Coverage: senior checks that were previously absent. Migrations — `lock_timeout` and
  the DDL lock-queue pileup, foreign keys `NOT VALID` (locking both tables), and enum
  evolution limits. Security — RLS bypass by the table owner / `BYPASSRLS`,
  `FORCE ROW LEVEL SECURITY`, `SET LOCAL` behind a transaction pooler, `SECURITY DEFINER`
  `search_path`, and not returning secret columns by default. Data model / SQL —
  `timestamptz` vs naive `timestamp`, integer/`NUMERIC` money, `int4` primary-key
  exhaustion, native-enum-vs-lookup, and generated columns. Indexing / performance —
  `INCLUDE` covering indexes, `pg_trgm` for leading-wildcard `LIKE`, index bloat /
  `REINDEX CONCURRENTLY`, and the CTE materialization fence. Backend data access —
  `FOR UPDATE SKIP LOCKED` and advisory locks.
- Cross-lens synthesis protocol: finding convergence (one finding for a defect flagged by
  several lenses, attributed to all of them), severity reconciliation (take the maximum),
  and deterministic ordering within a severity.
- A "Grounding" link in the evidence chain: every Critical and High finding names the
  rule/source it rests on, and none may rest on the provenance tier alone; new quality
  gates enforce it.
- Opt-in `--board` execution mode: each engaged lens runs as an independent subagent,
  then the main context synthesizes one report.
- `docs/ARCHITECTURE.md` (the flow and analytical approach, with mermaid diagrams) and
  `docs/example-review.md` (a full worked review).
- Machine-gradable evaluations in `skills/review/evals/evals.json` (skill-creator schema)
  and an optional local end-to-end runner `scripts/run_evals.py`.
- `golden-project-03`, a correct-but-conditional fixture that exercises the
  "Approve with conditions" verdict branch.
- `argument-hint` frontmatter on the skill, and a `## Contents` table of contents on
  `FRAMEWORK.md` and every lens.

### Changed

- Scope the skill's `allowed-tools` to read-only git inspection (plus `Task` for board
  mode), so live-database checks (`psql`/`prisma`/`EXPLAIN`) still prompt for consent
  instead of being silently pre-approved. Correct `SECURITY.md`, which had described
  `allowed-tools` as restricting the tool set; per the spec it grants pre-approval and
  does not restrict.
- Dispatch now directs the reviewer to read each engaged lens and its declared reference
  digests in full, avoiding partial reads of the two-hop knowledge base.
- Extend `scripts/validate.py` (and CI) with two more deterministic checks: the cross-lens
  handoff graph resolves to real lenses/domains, and the evals stay bound to the golden
  fixtures.
- Harden `scripts/validate.py` (and therefore CI) with citation-key integrity (every
  `[KEY]` used in a lens or digest resolves to a bibliography entry), lens-header ↔
  dependency-map agreement, and SKILL.md dispatch-table ↔ lens-file agreement.

### Fixed

- Define the previously-missing `[OWASP-SQLI]` and `[OWASP-CRYPTO]` bibliography keys that
  the security lens and `references/security.md` cite, and retag the mass-assignment
  guidance to a new `[OWASP-ASVS]` source (the OWASP SQL-injection sheet did not cover it).
  No lens or digest now cites an undefined source.

## [1.0.0] - 2026-07-11

### Added

- Initial release of Argus. Framework contract v1.0.0.
- Orchestrator skill `argus:review` with a first-class lens dispatcher,
  evidence gate, negative constraints, per-lens confidence, quality gates, and
  an approval decision.
- Eight review lenses: data-model, indexing, query-performance, migrations,
  scalability, security, prisma, backend-data-access.
- Tiered knowledge base (11 domain digests plus a tiered bibliography) that the
  dispatcher loads per lens, keeping reasoning and facts separate.
- Validation harness with two golden projects: `golden-project-01` (seeded with
  known smells, must be rejected) and `golden-project-02` (clean and well-built
  with false-positive traps, must be approved), each with a golden
  `expected-findings.md`.
- Community health files (CONTRIBUTING, CODE_OF_CONDUCT, SECURITY), issue and
  pull-request templates, and a deterministic CI workflow that validates the
  plugin manifests and the lens-to-knowledge-domain map (`scripts/validate.py`).
