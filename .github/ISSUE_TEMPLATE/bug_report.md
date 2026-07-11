---
name: Bug report
about: A review that misfired — a missed finding, a false positive, or a broken contract
title: "[bug] "
labels: bug
assignees: ''
---

## What happened

A clear description of the incorrect review behavior. Was it a **missed finding**, a
**false positive** (flagged something fine), a **wrong recommendation**, or a
**contract violation** (e.g. approved with a Critical open, emitted a finding with no
evidence)?

## What was reviewed

- Artifact(s) in scope (schema / migration / query code), or a minimal repro snippet.
- Command used, e.g. `/db-review:review path/to/file`.
- Diff mode or audit mode.

## Expected behavior

Which lens should have engaged, and what finding (with severity) you expected — or
why the flagged item should not have been raised.

## Actual output

Paste the relevant part of the review report (dispatch line, the finding or the
approval decision).

## Environment

- Plugin version (`.claude-plugin/plugin.json`):
- Database engine / ORM (e.g. PostgreSQL + Prisma):
- Live DB checks available? (yes/no)
