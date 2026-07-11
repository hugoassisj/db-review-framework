-- Golden project 02: a deliberately SAFE migration. This is the approve-case fixture.
-- Each statement is the safe form of a change that is commonly done unsafely. See
-- expected-findings.md for the traps a passing review must NOT flag.

-- GOOD(migrations, indexing): build the index without blocking writes on a live table.
-- CREATE INDEX CONCURRENTLY cannot run inside a transaction block, so it runs in its own
-- migration, separate from the DDL below.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_customer_created
  ON "Order" ("customerId", "createdAt" DESC);

-- GOOD(migrations): add the new column as nullable first. The ADD does not rewrite the
-- table or hold a long ACCESS EXCLUSIVE lock validating every existing row.
ALTER TABLE "User" ADD COLUMN "countryCode" text;

-- Backfill in bounded batches, run out of band (shown here for intent), never one giant
-- UPDATE that locks the table and bloats the WAL:
--   UPDATE "User" SET "countryCode" = 'US' WHERE id BETWEEN :lo AND :hi;

-- GOOD(migrations): enforce NOT NULL in two steps. NOT VALID adds the constraint without
-- scanning existing rows under lock; VALIDATE then checks them without blocking writes.
ALTER TABLE "User"
  ADD CONSTRAINT user_country_not_null CHECK ("countryCode" IS NOT NULL) NOT VALID;
ALTER TABLE "User" VALIDATE CONSTRAINT user_country_not_null;

-- GOOD(migrations): expand/contract rename. Add the new column and dual-write from the
-- application. Only after every deployed instance writes both columns do we backfill and
-- drop the old one, in a LATER migration. No flag-day break for running code.
ALTER TABLE "User" ADD COLUMN "displayName" text;
-- The old "name" column stays until a later contract-phase migration removes it.
