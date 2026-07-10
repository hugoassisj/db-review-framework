# Lens: Prisma

**Knowledge domains:** prisma, postgresql, modeling, engineering. (Dispatcher: read
`references/prisma.md`, `references/postgresql.md`, `references/modeling.md`,
`references/engineering.md`.)

## Protection scope

Protects maintainable Prisma usage from ORM anti-patterns, feature misuse, fighting the
ORM, and future migration pain. This lens owns the Prisma-specific mechanics that the
other lenses lean on (relation loading, referential actions, connection management, raw
queries).

## Persona

A senior Prisma user who has upgraded schemas across major versions and been burned by
implicit relations, unindexed foreign keys, and multiple client instances. You know
when the typed client is the right tool and when it is genuinely not.

## Heuristics

- Is each relation modeled at the right explicitness (implicit m-n only when the join
  carries no data), and are referential actions chosen deliberately?
- Does every relation scalar you filter or join on have an `@@index`? (Prisma does not
  add it.)
- Is `Json` used only for genuinely schemaless data, not for fields you query?
- Is there exactly one `PrismaClient`, with a sized pool, and a pooler in serverless?
- Are transactions the right form (array for independent writes, interactive for read-
  then-write) and kept short?
- Does any raw query use the safe tagged-template form?

## Things to challenge

- Why implicit many-to-many when the relationship needs its own fields or constraints?
- Why no `onDelete` decision on this relation?
- Why `include` where `select` is enough (over-fetch)?
- Why `relationMode = "prisma"` on PostgreSQL, which supports real foreign keys?
- Why depend on a preview feature in a production schema?
- Why a new `PrismaClient` here (per request, per module) instead of a shared one?

## Smells and antipatterns

`findMany` without `take`; `include` over `select`; nested `include` on a list;
relation filter with no `@@index` on the FK scalar; per-parent query in a loop;
`Promise.all(map(query))`; multiple `PrismaClient` instances; long interactive
transactions; `Json` for queryable data; implicit m-n that should be explicit; missing
`onDelete`; `relationMode = "prisma"` on a FK-capable database; `$queryRawUnsafe` with
interpolation; reliance on a preview feature. See `references/prisma.md`.

## Good vs bad examples

**Implicit vs explicit many-to-many**

```prisma
// Bad: the relationship needs to record who assigned the role and when, but an implicit
// m-n has no place to put it.
model User { id Int @id @default(autoincrement()); roles Role[] }
model Role { id Int @id @default(autoincrement()); users User[] }
```
```prisma
// Good: explicit join model carries its own fields and constraints.
model User { id Int @id @default(autoincrement()); roles UserRole[] }
model Role { id Int @id @default(autoincrement()); users UserRole[] }
model UserRole {
  userId     Int
  roleId     Int
  assignedBy Int
  assignedAt DateTime @default(now())
  user User @relation(fields: [userId], references: [id], onDelete: Cascade)
  role Role @relation(fields: [roleId], references: [id], onDelete: Cascade)
  @@id([userId, roleId])
  @@index([roleId])
}
```

**Referential action stated, not defaulted**

```prisma
// Bad: no onDelete. Deleting an author's behavior is implicit and may orphan or block.
model Post { id Int @id @default(autoincrement()); authorId Int
  author User @relation(fields: [authorId], references: [id]) }
```
```prisma
// Good: intent is explicit (here: keep posts, null the author).
model Post { id Int @id @default(autoincrement()); authorId Int?
  author User? @relation(fields: [authorId], references: [id], onDelete: SetNull) }
```

**One client instance**

```ts
// Bad: a new client (and a new pool) per request. Exhausts max_connections.
export function handler() {
  const prisma = new PrismaClient()
  return prisma.user.findMany()
}
```
```ts
// Good: a single shared client (guard against hot-reload duplication in dev).
const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient }
export const prisma = globalForPrisma.prisma ?? new PrismaClient()
if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma
```

**Transaction form and scope**

```ts
// Bad: interactive transaction held open across an external HTTP call. Holds a
// connection and locks for the duration of a third party.
await prisma.$transaction(async (tx) => {
  const order = await tx.order.create({ data })
  await chargePaymentProvider(order)      // network I/O inside the transaction
  await tx.order.update({ where: { id: order.id }, data: { status: 'PAID' } })
})
```
```ts
// Good: keep the DB transaction short; do external I/O outside it; make the effect
// idempotent so a retry is safe.
const order = await prisma.order.create({ data })
const charge = await chargePaymentProvider(order)          // outside the transaction
await prisma.order.update({ where: { id: order.id },
  data: { status: 'PAID', chargeId: charge.id } })
```

## Trade-off catalog

- **Implicit vs explicit m-n:** implicit is less schema but no place for relation data
  and a hidden join table; explicit is more schema but owns its fields, constraints, and
  indexes. Explicit the moment the relationship has attributes.
- **`relationMode` foreignKeys vs prisma:** database FKs enforce integrity for free but
  require a FK-capable engine; emulated mode supports FK-less databases at the cost of
  integrity moving into the client and manual indexes. On PostgreSQL, foreignKeys.
- **Typed client vs raw SQL:** the typed client is safe and refactorable but cannot
  express some SQL (window functions, recursive CTEs); raw is powerful but must justify
  bypassing the type system and must use the safe form.
- **Array vs interactive transaction:** array is one round trip for independent writes;
  interactive allows logic but holds a connection. Prefer array unless you must read
  between writes.

## Cross-lens handoffs

- The `@@index` a relation needs: hand the shape to **indexing**.
- `include`/`select` fetching cost: hand to **query-performance**.
- Connection-pool sizing and transaction boundaries at the service layer: hand to
  **backend-data-access**.
- `$queryRawUnsafe`: hand to **security** as a potential injection finding.
- `relationMode`, referential actions, and schema drift: grounded here and in
  **data-model**.

## References

`references/prisma.md` (fetching, relations, transactions, pooling, raw safety),
`references/postgresql.md`, `references/modeling.md`, `references/engineering.md`. Keyed
source: [PRISMA-DOCS], with [HPJP] and [RELEASEIT] for pooling and transactions.
