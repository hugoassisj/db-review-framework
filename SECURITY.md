# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 1.x     | ✅        |
| < 1.0   | ❌        |

## Reporting a vulnerability

Please report suspected vulnerabilities **privately**. Do not open a public issue for
a security problem.

- Email: **hugo.assis.j@gmail.com** with a subject beginning `[SECURITY] Argus`.
- Include a description, affected files or behavior, and reproduction steps.

You can expect an acknowledgement within a few days. Once a fix is available, we will
credit reporters who wish to be named.

## What this plugin does and does not do

Argus is a Claude Code plugin made of Markdown instructions. It ships no
executable service and stores no secrets. It uses `Read`, `Grep`, `Glob`, and
`WebFetch`; `Task` for the optional `--board` mode; and `Bash` only for the
change under review (see [`skills/review/SKILL.md`](skills/review/SKILL.md)).

Per the Claude Code Skills spec, a skill's `allowed-tools` frontmatter **grants
pre-approval** for the listed tools while the skill is active; it does **not**
restrict the tool set. Argus deliberately pre-approves only **read-only git
inspection** — `git diff`, `git status`, `git log`, `git show`, `git rev-parse`,
`git ls-files` — so reviewing a diff needs no per-command prompt. Everything
else, **including any database access (`psql`, `prisma`, `EXPLAIN`)**, is not
pre-approved and still requires your approval through your normal permission
settings.

Its optional live-database checks are **read-only and consent-gated** by design
(`SKILL.md` §9), and the scoped `allowed-tools` grant above is what backs that
guarantee rather than merely asserting it:

- It runs live checks only when a database URL and `psql`/`prisma` are available
  **and the user permits it** (the tool is not pre-approved, so it prompts).
- It never runs destructive or write statements, and never runs `EXPLAIN ANALYZE`
  against production without explicit consent.
- If no database is available it stays static and says so.

The sample code under [`validation/`](validation) is **intentionally insecure**. It
seeds known smells (plaintext passwords, SQL injection, etc.) as test fixtures for the
reviewer to catch. Do not treat those fixtures as example production code, and do not
copy them into a real project.
