# Lens: Security

**Knowledge domains:** security, postgresql, prisma. (Dispatcher: read
`references/security.md`, `references/postgresql.md`, `references/prisma.md`.)

## Contents

- Protection scope
- Persona
- Heuristics
- Things to challenge
- Smells and antipatterns
- Good vs bad examples
- Trade-off catalog
- Cross-lens handoffs
- References

## Protection scope

Protects a defensible data layer from SQL injection, PII exposure, missing least-
privilege, missing tenant isolation, and secrets stored or logged in the clear. A data-
layer security defect is often Critical, because it exposes or corrupts the source of
truth.

## Persona

An application-security engineer who assumes every input is hostile and every query may
one day run with an attacker-controlled value. You prefer the database to enforce
isolation and integrity, because application code forgets.

## Heuristics

- Does any query build SQL from input by concatenation or `Unsafe` interpolation?
- Is tenant isolation enforced in the database (RLS), or only by an application filter
  a query can forget?
- Is any sensitive value (password, token, secret, PII) stored in the clear, or logged?
- Does the runtime database role hold more privilege than request handling needs?
- Can a caller set fields they should not by passing extra body keys into a write?
- If RLS is used, is it actually in force: `FORCE ROW LEVEL SECURITY` on, the app
  connecting as a non-owner role, and the tenant variable set with `SET LOCAL` behind a
  pooler?
- Does any read return secret columns (`passwordHash`, tokens) by default instead of
  projecting with `select`/`omit`?

## Things to challenge

- Why `$queryRawUnsafe` (or string-built SQL) here, and is the input a trusted constant?
- Why is this tenant-scoped read missing a tenant predicate, and where is RLS?
- Why is this token/secret/PII column plaintext?
- Why does the app connect with a role that can run DDL or read every table?
- Why does the app connect as the table owner, which bypasses its own RLS policies?
- Why is the request body spread straight into `data`?

## Smells and antipatterns

`$queryRawUnsafe` or concatenated SQL; runtime identifier interpolated without an
allowlist; tenant-scoped read with no tenant predicate; tenancy without RLS; RLS present
but the app connects as the table owner or without `FORCE ROW LEVEL SECURITY`; a tenant
session variable set without `SET LOCAL` behind a transaction pooler; a `SECURITY
DEFINER` function without a pinned `search_path`; secret columns (`passwordHash`,
tokens) returned by a default select; plaintext password (should be hashed), token,
secret, or PII column; secrets or decrypted values in logs; over-privileged runtime
role; migration and runtime sharing one high-privilege credential; unvalidated request
body spread into a create/update. See `references/security.md`.

## Good vs bad examples

**Injection: unsafe vs parameterized**

```ts
// Bad: attacker-controlled `email` is concatenated into SQL. Classic injection.
prisma.$queryRawUnsafe(`SELECT * FROM users WHERE email = '${email}'`)
```
```ts
// Good: the tagged-template form parameterizes the value.
prisma.$queryRaw`SELECT * FROM users WHERE email = ${email}`
// (or stay on the typed client: prisma.user.findUnique({ where: { email } }))
```

**Tenant isolation: app filter vs RLS**

```ts
// Bad: isolation depends on every query remembering the tenant filter. One omission
// (or one raw query) leaks across tenants.
prisma.invoice.findMany({ where: { tenantId, status: 'OPEN' } })
```
```sql
-- Good: enforce it in the database, in force even for the table owner, and set the
-- tenant per transaction so it stays correct behind a connection pooler.
ALTER TABLE invoice ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice FORCE ROW LEVEL SECURITY;         -- the owner is not exempt
CREATE POLICY tenant_isolation ON invoice
  USING (tenant_id = current_setting('app.tenant_id')::int);
-- per request, inside the transaction:  SET LOCAL app.tenant_id = '<id>';
-- and the app connects as a non-owner role that lacks BYPASSRLS.
```

**Secrets at rest: plaintext vs hashed/encrypted**

```prisma
// Bad: reversible/plaintext secrets.
model User    { id Int @id @default(autoincrement()); password String }        // plaintext
model ApiCred { id Int @id @default(autoincrement()); apiSecret String }       // plaintext
```
```prisma
// Good: passwords hashed (slow, salted); secrets encrypted at rest (envelope), with
// only a key id stored alongside the ciphertext.
model User    { id Int @id @default(autoincrement()); passwordHash String }
model ApiCred { id Int @id @default(autoincrement()); secretCiphertext Bytes; keyId String }
```

**Mass assignment**

```ts
// Bad: caller can send { role: "ADMIN" } and escalate.
prisma.user.update({ where: { id }, data: req.body })
```
```ts
// Good: allowlist the writable fields.
prisma.user.update({ where: { id }, data: { name: req.body.name, bio: req.body.bio } })
```

## Trade-off catalog

- **RLS vs application filter:** RLS is defense-in-depth enforced by the database and
  hard to bypass, at the cost of setup and a per-request session variable; application
  filters are simple but one omission from a leak. For multi-tenant data, RLS.
- **Encryption at rest vs queryability:** encrypting a column protects it but makes it
  unindexable and unsearchable in the clear; hash when you only need equality/lookup,
  encrypt when you must recover the plaintext, leave it clear only when it is not
  sensitive.
- **Least-privilege roles vs operational convenience:** separate, narrow roles limit
  blast radius but add credential management; one powerful role is convenient and
  dangerous.

## Cross-lens handoffs

- A migration that adds RLS, roles, or grants: hand execution to **migrations**.
- An encrypted column that a query needs to filter on: hand the index/model impact to
  **indexing** and **data-model**.
- `$queryRaw` safety mechanics and Prisma raw APIs: grounded in **prisma**.

## References

`references/security.md` (injection, RLS, PII, least privilege, mass assignment),
`references/postgresql.md` (RLS, roles), `references/prisma.md` (raw-query safety).
Keyed sources: [OWASP-SQLI], [OWASP-CRYPTO], [OWASP-ASVS], [PG-DOCS], [PRISMA-DOCS].
