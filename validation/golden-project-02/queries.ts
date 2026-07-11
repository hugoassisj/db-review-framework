// Golden project 02: clean, well-built data access. This is the approve-case fixture.
// The $queryRaw call near the bottom looks like raw SQL but is a parameterized tagged
// template, which is safe; it is a false-positive trap. See expected-findings.md.

import { PrismaClient, Prisma } from '@prisma/client'

// GOOD(prisma, backend-data-access): one shared client (and connection pool) for the
// whole process, not a new client per call.
const prisma = new PrismaClient()

// GOOD(query-performance): each order's customer comes back through a relation select in
// a single query. No N+1, and only the columns the caller uses are selected.
export async function ordersWithCustomer() {
  return prisma.order.findMany({
    take: 50,
    select: {
      id: true,
      totalCents: true,
      customer: { select: { id: true, email: true } },
    },
  })
}

// GOOD(query-performance): one query for many customers, batched with an `in` filter,
// instead of one query per customer in a fan-out.
export async function ordersForCustomers(customerIds: number[]) {
  return prisma.order.findMany({
    where: { customerId: { in: customerIds } },
    orderBy: { createdAt: 'desc' },
  })
}

// GOOD(query-performance): selects only the fields the dashboard renders, so it does not
// pull every column of the order.
export async function orderSummary(id: number) {
  return prisma.order.findUnique({
    where: { id },
    select: { id: true, status: true, totalCents: true, createdAt: true },
  })
}

// GOOD(query-performance): keyset (cursor) pagination. Each page seeks straight to the
// boundary instead of scanning and discarding skipped rows, so deep pages stay fast.
export async function eventPage(afterId?: bigint) {
  return prisma.event.findMany({
    take: 20,
    orderBy: { id: 'desc' },
    ...(afterId ? { cursor: { id: afterId }, skip: 1 } : {}),
  })
}

// GOOD(data-model, backend-data-access): the order total is computed from the line items
// and written in the SAME transaction, so the denormalized Order.totalCents can never
// drift from the rows it caches.
export async function createOrder(
  customerId: number,
  shipToCountryCode: string,
  items: { sku: string; quantity: number; unitPriceCents: number }[],
  metadata: Prisma.InputJsonValue,
) {
  const totalCents = items.reduce((sum, i) => sum + i.quantity * i.unitPriceCents, 0)
  return prisma.$transaction((tx) =>
    tx.order.create({
      data: {
        customerId,
        shipToCountryCode,
        totalCents,
        metadata,
        lineItems: { create: items },
      },
    }),
  )
}

// GOOD(backend-data-access): atomic guarded debit. The balance check and the decrement
// happen in one statement, so two concurrent debits cannot both pass the check and
// overdraw the account. No read-modify-write race, and no explicit lock needed.
export async function debit(accountId: number, cents: number) {
  const result = await prisma.account.updateMany({
    where: { id: accountId, balanceCents: { gte: cents } },
    data: { balanceCents: { decrement: cents } },
  })
  if (result.count === 0) {
    throw new Error('insufficient funds')
  }
}

// GOOD/TRAP(security): this looks like raw SQL, but $queryRaw is a tagged template and
// `country` is bound as a parameter, not interpolated into the string, so it is safe
// from injection. The unsafe form would be $queryRawUnsafe with string concatenation.
export async function ordersByCountry(country: string) {
  return prisma.$queryRaw<{ id: number; totalCents: number }[]>`
    SELECT id, "totalCents"
    FROM "Order"
    WHERE "shipToCountryCode" = ${country}
    ORDER BY "createdAt" DESC
    LIMIT 100
  `
}
