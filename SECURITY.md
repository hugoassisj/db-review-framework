# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 1.x     | ✅        |
| < 1.0   | ❌        |

## Reporting a vulnerability

Please report suspected vulnerabilities **privately**. Do not open a public issue for
a security problem.

- Email: **hugo.assis.j@gmail.com** with a subject beginning `[SECURITY] db-review`.
- Include a description, affected files or behavior, and reproduction steps.

You can expect an acknowledgement within a few days. Once a fix is available, we will
credit reporters who wish to be named.

## What this plugin does and does not do

`db-review` is a Claude Code plugin made of Markdown instructions. It ships no
executable service and stores no secrets. Its declared tools are limited to
`Read, Grep, Glob, Bash, WebFetch` (see
[`skills/review/SKILL.md`](skills/review/SKILL.md)).

Its optional live-database checks are **read-only and consent-gated** by design
(`SKILL.md` §9):

- It runs live checks only when a database URL and `psql`/`prisma` are available
  **and the user permits it**.
- It never runs destructive or write statements, and never runs `EXPLAIN ANALYZE`
  against production without explicit consent.
- If no database is available it stays static and says so.

The sample code under [`validation/`](validation) is **intentionally insecure** — it
seeds known smells (plaintext passwords, SQL injection, etc.) as test fixtures for the
reviewer to catch. Do not treat those fixtures as example production code, and do not
copy them into a real project.
