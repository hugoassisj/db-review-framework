// Golden project 01: seeded query and data-access smells.
// Deliberately flawed test fixture. See expected-findings.md.

import { PrismaClient } from '@prisma/client'

// SMELL(prisma/backend-data-access): a new client (and pool) per call exhausts
// max_connections. Should be a single shared instance.
export async function listPostAuthors() {
  const prisma = new PrismaClient()
  const posts = await prisma.post.findMany({ take: 50 })
  // SMELL(query-performance): N+1. One query per post for its author.
  for (const p of posts) {
    // @ts-expect-error illustrative
    p.author = await prisma.user.findUnique({ where: { id: p.authorId } })
  }
  return posts
}

// SMELL(query-performance): fan-out. N concurrent queries, same round-trip count.
export async function usersWithOrders(prisma: PrismaClient) {
  const users = await prisma.user.findMany({ take: 100 })
  return Promise.all(
    users.map((u) => prisma.order.findMany({ where: { customerId: u.id } })),
  )
}

// SMELL(query-performance): include pulls every column of user and every order,
// though the caller uses only name and totalCents.
export async function userDashboard(prisma: PrismaClient, id: number) {
  return prisma.user.findUnique({ where: { id }, include: { orders: true } })
}

// SMELL(query-performance): offset pagination. Deep pages scan and discard rows.
export async function eventPage(prisma: PrismaClient, page: number) {
  return prisma.event.findMany({
    orderBy: { id: 'desc' },
    skip: page * 20,
    take: 20,
  })
}

// SMELL(backend-data-access): read-modify-write lost-update race on balance.
export async function debit(prisma: any, accountId: number, cents: number) {
  const acct = await prisma.account.findUnique({ where: { id: accountId } })
  await prisma.account.update({
    where: { id: accountId },
    data: { balance: acct.balance - cents },
  })
}

// SMELL(security): attacker-controlled email concatenated into raw SQL (injection).
export async function findByEmailUnsafe(prisma: PrismaClient, email: string) {
  return prisma.$queryRawUnsafe(`SELECT * FROM "User" WHERE email = '${email}'`)
}
