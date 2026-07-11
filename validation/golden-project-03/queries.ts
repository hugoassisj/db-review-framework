// Golden project 03 — data access for multi-tenant billing. Correct-but-conditional.
// Every query is tenant-scoped, projected, and (where it writes) atomic and idempotent.
// Synthetic. Do not copy into a real project.

import { PrismaClient } from '@prisma/client'

// One shared client and pool for the process, reused across calls.
const prisma = new PrismaClient()

// Tenant-scoped list with keyset pagination, projecting only the columns the caller uses.
export function listInvoices(tenantId: bigint, cursorId?: bigint) {
  return prisma.invoice.findMany({
    where: { tenantId },
    orderBy: { issuedAt: 'desc' },
    ...(cursorId ? { cursor: { id: cursorId }, skip: 1 } : {}),
    take: 20,
    select: { id: true, totalCents: true, status: true, issuedAt: true },
  })
}

// Invoice, its line items, and the denormalized total are written in ONE transaction, so
// the cached total cannot drift from the line items it sums.
export async function createInvoice(
  tenantId: bigint,
  items: { description: string; amountCents: number }[],
) {
  const totalCents = items.reduce((sum, i) => sum + i.amountCents, 0)
  return prisma.$transaction(async (tx) => {
    const invoice = await tx.invoice.create({
      data: { tenantId, totalCents, status: 'open' },
    })
    await tx.lineItem.createMany({
      data: items.map((i) => ({ invoiceId: invoice.id, ...i })),
    })
    return invoice
  })
}

// Idempotent payment: a redelivered provider webhook is a no-op, not a double charge.
export function recordPayment(
  invoiceId: bigint,
  amountCents: number,
  providerEventId: string,
) {
  return prisma.payment.upsert({
    where: { providerEventId },
    create: { invoiceId, amountCents, providerEventId },
    update: {},
  })
}

// Parameterized raw aggregate: the tagged-template form binds tenantId, it is not
// concatenated into the SQL, so it is not injectable.
export function revenueByTenant(tenantId: bigint) {
  return prisma.$queryRaw`
    SELECT COALESCE(SUM(p."amountCents"), 0) AS cents
    FROM "Payment" p
    JOIN "Invoice" i ON i."id" = p."invoiceId"
    WHERE i."tenantId" = ${tenantId}`
}
