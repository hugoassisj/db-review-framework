# Changelog

All notable changes to the db-review framework are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The framework contract (`skills/review/FRAMEWORK.md`) carries its own contract
version. Individual lenses and knowledge-base digests do not version separately;
they move with the repository version below.

## [1.0.0] - 2026-07-10

### Added

- Initial release. Framework contract v1.0.0.
- Orchestrator skill `db-review:review` with a first-class lens dispatcher,
  evidence gate, negative constraints, per-lens confidence, quality gates, and
  an approval decision.
- Eight review lenses: data-model, indexing, query-performance, migrations,
  scalability, security, prisma, backend-data-access.
- Tiered knowledge base (11 domain digests plus a tiered bibliography) that the
  dispatcher loads per lens, keeping reasoning and facts separate.
- Validation harness with `golden-project-01` (synthetic Prisma + PostgreSQL
  project seeded with known smells) and a golden `expected-findings.md`.
