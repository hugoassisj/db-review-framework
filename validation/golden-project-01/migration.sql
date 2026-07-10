-- Golden project 01: seeded migration-safety smells.
-- Deliberately unsafe test fixture. See expected-findings.md.

-- SMELL(migrations): blocking index build. Locks writes on orders for the whole build.
-- Should be CREATE INDEX CONCURRENTLY on a live table.
CREATE INDEX idx_orders_customer ON "Order" (customer_id, created_at);

-- SMELL(migrations): adds a NOT NULL column, validating every existing row under an
-- ACCESS EXCLUSIVE lock. Should be: add nullable, backfill in batches, then enforce
-- via a NOT VALID check validated separately.
ALTER TABLE "User" ADD COLUMN country text NOT NULL DEFAULT '';

-- SMELL(migrations): flag-day rename. Every running instance of the old code breaks the
-- instant this commits. Should use expand/contract (add new, dual-write, switch, drop).
ALTER TABLE "User" RENAME COLUMN password TO password_hash;

-- SMELL(migrations): destructive drop with no deprecation period. Irreversible data loss
-- and breaks any lingering reader.
ALTER TABLE "Order" DROP COLUMN metadata;
