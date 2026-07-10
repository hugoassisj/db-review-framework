# Knowledge: Architecture

Distilled facts for where the data model meets application structure. Sources
**[POEAA]**, **[DDD]**/**[LDDD]**, **[APOSD]**.

## Persistence patterns

- **Repository** mediates between the domain and the data mapper, exposing a
  collection-like interface and keeping query logic in one place. It is worth having
  when query logic would otherwise scatter across services; it is over-engineering
  when it is a one-line pass-through wrapper around the ORM that hides nothing. Judge
  by whether it removes duplication or just adds a layer. [POEAA][APOSD]
- **Unit of Work** tracks the objects touched in a business transaction and commits
  them together, giving one transactional boundary per use case rather than per
  statement. In Prisma this maps to scoping an interactive transaction around the use
  case. [POEAA]
- **Data Mapper vs Active Record:** Prisma is a data-mapper-style client (models are
  plain data, the client persists them), which keeps domain objects free of
  persistence concerns. Pushing business logic into query middleware or model hooks
  reintroduces the coupling data mapper avoids. [POEAA]

## Aggregate boundaries drive transaction boundaries

- An aggregate (a cluster that must stay consistent together, one root) is the unit of
  a transaction: enforce invariants inside one aggregate in one transaction, and
  reference other aggregates by id, updating them in separate transactions or via
  events. A transaction that spans many aggregates to hold an invariant is a signal
  the boundaries are drawn wrong. [DDD][LDDD]

## Complexity

- Deep modules (a simple interface over real functionality) hide complexity; shallow
  modules (an interface as wide as their implementation) just move it around. A
  persistence abstraction that forces the caller to understand both it and the
  underlying ORM is shallow and a net loss. [APOSD]
- Every abstraction must pay rent: it must reduce complexity for its callers or it is
  a cost with no return. Prefer deleting a shallow wrapper over keeping it. [APOSD]

## Where logic belongs

- Data integrity rules that must always hold belong in the database (constraints), not
  only in a service, because a constraint cannot be bypassed by another writer or a
  raw query. Business orchestration belongs in the application. Do not push complex
  business logic into database triggers or ORM middleware where it becomes invisible.
  [POEAA][DDD]

## Watch-list

Repository that is a pass-through wrapper hiding nothing; transaction scoped per
statement instead of per use case; business logic buried in query middleware, model
hooks, or triggers; a persistence abstraction that leaks the ORM it wraps; an invariant
enforced only in a service that a constraint could enforce; a transaction spanning
many aggregates.
