# Knowledge: Database security

Distilled DB-facing security facts. Sources **[OWASP-SQLI]**, **[OWASP-CRYPTO]**,
**[PG-DOCS]** (RLS), **[PRISMA-DOCS]** (raw-query safety).

## Injection

- SQL injection happens when untrusted input is concatenated into a query string.
  The defense is parameterized queries, always. In Prisma, the `$queryRaw` /
  `$executeRaw` tagged-template form parameterizes inputs and is safe; the `Unsafe`
  variants and any string interpolation are not. Treat interpolated `$queryRawUnsafe`
  as Critical unless the input is proven to be a trusted constant. [OWASP-SQLI][PRISMA-DOCS]
- Dynamic identifiers (table or column names chosen at runtime) cannot be
  parameterized and must be validated against an allowlist, never interpolated raw.

## Tenant isolation

- In a multi-tenant database, isolation enforced only by an application `where
  tenant_id = …` is one forgotten filter (or one raw query) away from a cross-tenant
  data leak. PostgreSQL row-level security enforces it in the database, so the
  isolation holds even when a query forgets the filter. Prefer RLS (or a per-tenant
  schema/database) for hard isolation. [PG-DOCS]
- Any query that reads a tenant-scoped table without a tenant predicate is a finding.

## Data at rest and PII

- Sensitive data (credentials, tokens, personal data, financial data) should be
  encrypted or hashed appropriately: passwords hashed with a slow, salted algorithm
  (never reversible encryption); secrets and tokens encrypted, not stored plaintext.
  [OWASP-CRYPTO]
- Envelope encryption (a per-row data key wrapped by a master key, with the master key
  managed by a KMS and only a key id stored in the row) is the standard pattern for
  encrypting column data at rest. A plaintext secret, token, or PII column is a
  finding; the severity rises with the sensitivity. [OWASP-CRYPTO]
- Do not log sensitive column values, connection strings, or decrypted payloads.
  Secrets in logs are a common leak path.

## Least privilege

- The application's database role should hold only the privileges it needs. A role
  with superuser or broad `DDL` rights used for ordinary request handling widens the
  blast radius of any injection or bug. Separate migration credentials from runtime
  credentials. [PG-DOCS]

## Mass assignment at the data layer

- Passing an unvalidated request body straight into a create/update lets a caller set
  fields they should not (role, ownerId, isAdmin, balance). Select the writable fields
  explicitly; do not spread untrusted input into a write. [OWASP-SQLI]

## Watch-list

`$queryRawUnsafe` or string-concatenated SQL; runtime identifier interpolated without
an allowlist; tenant-scoped read with no tenant predicate; tenancy without RLS;
plaintext password (should be hashed), token, secret, or PII column; secrets or
decrypted values in logs; runtime role with excessive privileges; migration and
runtime sharing one high-privilege credential; unvalidated request body spread into a
create or update (mass assignment).
