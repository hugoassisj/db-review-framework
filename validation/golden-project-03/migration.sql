-- Golden project 03 — migration. Demonstrates safe, senior migration practice against a
-- live multi-tenant database. Synthetic. Do not copy blindly.

-- Guard every DDL with a short lock_timeout so a lock wait fails fast and can be retried,
-- instead of queueing all subsequent traffic behind a blocked ALTER.
SET lock_timeout = '3s';

-- Non-blocking index build. Runs in its own migration, outside a transaction block, so it
-- does not lock writes on the table while it builds.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_invoice_tenant_issued
  ON "Invoice" ("tenantId", "issuedAt" DESC);

-- Row-level security for tenant isolation, in force even for the table owner.
ALTER TABLE "Invoice" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Invoice" FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON "Invoice"
  USING ("tenantId" = current_setting('app.tenant_id')::bigint);

-- Runtime wiring this migration cannot enforce and a review cannot verify statically:
--   1. the application must connect as a NON-OWNER role without BYPASSRLS, or the policy
--      is silently ignored;
--   2. each request must run `SET LOCAL app.tenant_id = '<id>'` INSIDE its transaction,
--      so the value is safe behind the transaction-mode pooler (a plain SET would leak
--      to the next tenant that reuses the pooled connection).
-- These are the conditions the review must surface (C1), not silently assume.
