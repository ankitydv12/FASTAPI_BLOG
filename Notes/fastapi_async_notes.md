# Sync vs Async in FastAPI — Revision Notes

---

## 1. What is Async, Conceptually

- **Async** = handling multiple tasks *concurrently* (not necessarily in parallel).
- Analogy:
  - **Sync = Subway** — one order made start-to-finish before moving to the next customer.
  - **Async = McDonald's** — order taken, then staff moves to next customer while your food is prepared in the background.
- Async helps with **I/O-bound tasks** — situations where the program is *waiting* on something external:
  - Database queries (waiting for DB response)
  - External API calls (waiting for network)
  - File operations (waiting for disk)
- Async does **NOT** help with **CPU-bound tasks** — heavy calculations, image processing, data crunching — because the CPU is actively working, not waiting. There's nothing to overlap.
- **Async isn't automatically faster.** For simple/fast queries or low traffic, the overhead of async machinery can even be slightly slower.
- **Real benefit shows up under concurrent load** — many requests happening at the same time.

---

## 2. How FastAPI Handles `def` vs `async def` Routes

| Route type | How FastAPI runs it |
|---|---|
| `def` (regular/sync function) | Runs automatically in a **separate thread pool** → doesn't block the main event loop. Works well even without changes. |
| `async def` | Runs directly in the **main event loop** → more efficient, but **you must `await` every I/O operation**. |

- ⚠️ If you do blocking I/O inside an `async def` route *without* `await`, you block the entire event loop — this is **worse** than just using a regular `def` route.
- **Both approaches are valid.** Choose based on what the specific route does — sync isn't "wrong" or inherently slow in FastAPI.

---

## 3. Setting Up Async SQLAlchemy (Dependencies)

- Need an **async DB driver**:
  - SQLite → `aiosqlite`
  - PostgreSQL → `psycopg` (async variant)
- Also need **`greenlet`** installed — required internally by SQLAlchemy's async mode (easy to forget; causes `"No module named greenlet"` error if missing).

---

## 4. Converting `database.py` to Async

| Sync version | Async version |
|---|---|
| `from sqlalchemy import create_engine` | `from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker` |
| `sqlite:///./blog.db` | `sqlite+aiosqlite:///./blog.db` (add `+aiosqlite` to the URL to select the async driver) |
| `create_engine(...)` | `create_async_engine(...)` |
| `sessionmaker(...)` → `SessionLocal` | `async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)` → `AsyncSessionLocal` |
| `def get_db(): with SessionLocal() as db: yield db` | `async def get_db(): async with AsyncSessionLocal() as session: yield session` |

- **`expire_on_commit=False`** — important for async: normally after a commit, SQLAlchemy marks objects "expired" and lazily reloads them on next access. Lazy loading isn't allowed in async, so this avoids that failure.
- `get_db()` becomes an **async generator** (same yield-based dependency pattern, just async).

### `async_sessionmaker(...)` params explained

```python
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

- **`class_=AsyncSession`**
  - `async_sessionmaker` is just a factory — it needs to know *which* session class to instantiate.
  - `AsyncSession` (from `sqlalchemy.ext.asyncio`) is the async-aware version of `Session`, with async methods (`await session.execute()`, `await session.commit()`, etc.).
  - Without this, the factory wouldn't produce sessions with those async methods.

- **`expire_on_commit=False`**
  - Default (`True`): after `session.commit()`, SQLAlchemy **expires all objects** — meaning the next attribute access (e.g. `user.username`) triggers a fresh reload from the DB.
  - In **sync** code this "just works" — it silently runs a new query (lazy loading) behind the scenes.
  - In **async** code, that automatic reload can't happen the same way — it would require an implicit/lazy query, which isn't allowed in an async context. Accessing an attribute on an expired object after commit would raise an error instead of silently reloading.
  - Setting `expire_on_commit=False` tells SQLAlchemy: *"don't expire objects after commit — keep their current in-memory values."*
  - Example of why this matters:
    ```python
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
    ```
    Without `expire_on_commit=False`, accessing `new_user.username` after `commit()` (e.g. during response serialization) could fail, since the object would be expired. This setting avoids that — you only refresh explicitly when you actually need updated data (like a DB-generated `id`).

**One-line summary:** `class_=AsyncSession` makes the session async-capable; `expire_on_commit=False` stops SQLAlchemy from auto-invalidating objects after commit, which would otherwise require disallowed lazy reloads in async mode.

---

## 5. Table Creation: Lifespan Instead of `create_all()`

- `Base.metadata.create_all(bind=engine)` is **synchronous** — can't call it directly with an async engine.
- Fix: use a **lifespan function** (modern replacement for deprecated `@app.on_event("startup"/"shutdown")`).

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # shutdown
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
```

- Code **before `yield`** → runs at startup.
- Code **after `yield`** → runs at shutdown.
- `conn.run_sync(...)` → lets you run a sync-only call (like `create_all`) inside an async context.
- This is **idempotent** — safe to run every startup even if tables already exist.
- At shutdown, `engine.dispose()` cleanly closes connections.

---

## 5.5 Why `await` Is Needed (General Rule)

- `await` is used any time you call something that does actual **I/O** — talking to the database, network, or disk — and the function needs to *wait* for a response.
- When execution hits an `await`, Python pauses that function and lets the event loop go handle other requests in the meantime. Once the DB (or whatever) responds, execution resumes right where it left off.
- In this app:
  - `await db.execute(...)` → waits for the DB to actually run the query and return rows
  - `await db.commit()` → waits for the DB to finish writing/saving
  - `await db.refresh(obj)` → waits for the DB to re-fetch the object
  - `await db.delete(obj)` → waits for the delete to register with the session/DB
  - `db.add(obj)` → **no `await`** — just stages the object in the session's in-memory pending list; no DB communication happens yet.
- **Rule of thumb:** if the operation talks to the database (or any external system), it needs `await`. If it's purely in-memory, it doesn't.

---

## 6. The Big Gotcha: Lazy Loading Doesn't Work in Async

- **Sync SQLAlchemy:** accessing `post.author` triggers an automatic ("lazy") query if not already loaded. Just works.
- **Async SQLAlchemy:** lazy loading is **not supported**. Accessing an unloaded relationship raises an error (something like *"greenlet_spawn has not been called"*), because lazy loading would require a sync query inside an async context.

### What Eager Loading Actually Is
- **Lazy loading** (sync default): you access `post.author`, and SQLAlchemy quietly runs a *separate* query right then, on demand, to fetch the author.
- **Eager loading**: instead of waiting until the relationship is accessed, you tell SQLAlchemy upfront — as part of the *original* query — to also fetch the related data (e.g. "load the author for every post you return").
- **Why it matters in async:** lazy loading relies on SQLAlchemy silently firing off a new query the instant you touch `post.author`. That would mean running sync-style, on-the-fly I/O inside an async context, which isn't allowed — so lazy loading is disabled in async mode. Eager loading solves this by loading the relationship data upfront, in the same query, so it's already in memory by the time your code (or template) accesses it.

### Solution: Eager Loading
Explicitly tell SQLAlchemy to load relationships **as part of the main query**, using `selectinload`:

```python
from sqlalchemy.orm import selectinload

result = await db.execute(
    select(model.Post).options(selectinload(model.Post.author))
)
```

- **Rule of thumb:** any route/template that will access a relationship (e.g. `post.author`, or a response schema that nests `author`) needs eager loading.
- Routes that don't touch relationships (e.g. just checking `User` exists) don't need it.

### Alternative: Eager-load on refresh
When creating/updating an object and immediately returning it with a relationship included, use:
```python
await db.refresh(post, attribute_names=["author"])
```
This refreshes the object **and** loads the given relationship in the same call — avoids a separate `selectinload` query.

---

## 7. Converting Routes — The General Pattern

For every route that touches the DB:
1. `def` → `async def`
2. Session dependency: `Session` → `AsyncSession`
3. `db.execute(...)` → `await db.execute(...)`
4. `db.commit()` → `await db.commit()`
5. `db.refresh(...)` → `await db.refresh(...)`
6. `db.delete(...)` → `await db.delete(...)`
7. Add `selectinload(...)` (or `refresh(..., attribute_names=[...])`) wherever a relationship will be accessed afterward

### Important nuance — what needs `await` and what doesn't:
| Operation | Needs `await`? | Why |
|---|---|---|
| `db.add(obj)` | ❌ No | Only stages the object in memory (pending list) — no I/O yet |
| `db.commit()` | ✅ Yes | Actual I/O — writes to DB |
| `db.refresh(obj)` | ✅ Yes | Actual I/O — re-reads from DB |
| `db.delete(obj)` | ✅ Yes | Requires interacting with the session in a way that needs I/O in async mode |
| `db.execute(...)` | ✅ Yes | Runs the query — I/O |

---

## 8. Async Exception Handlers

- Old approach: manually build `JSONResponse` in a sync exception handler.
- Better approach in async apps: use **FastAPI's built-in default async handlers**:
```python
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
```
- Inside your custom handler (still async), for API paths just delegate:
```python
if request.url.path.startswith("/api"):
    return await http_exception_handler(request, exception)
```
- Same idea for `RequestValidationError` → `await request_validation_exception_handler(request, exception)`.
- Benefit: consistent behavior with the rest of FastAPI + less code to maintain.
- The custom message string is now only needed for the HTML/template branch, not the API/JSON branch.

---

## 9. When to Use Async vs Sync — Decision Guide

**Use async when:**
- Making multiple independent I/O operations
- Calling external APIs (best use case)
- DB operations under high concurrency
- Long-running I/O operations

**Use sync (`def`) when:**
- Simple, fast operations
- CPU-heavy work (calculations, image processing)
- Code clarity matters more than marginal performance gains
- You're relying on sync-only libraries

**Key takeaway:** You don't have to pick one for the whole app. **Mixed async/sync routes are fine** — FastAPI handles both gracefully. Choose per-route based on what that route actually does.

---

## 10. Common Mistakes to Avoid

- ❌ Doing blocking I/O inside an `async def` route (e.g. using the synchronous `requests` library instead of `httpx`, or using a sync DB session in an async route).
- ❌ Forgetting to install `greenlet` — required for SQLAlchemy async mode even though not imported directly.
- ❌ Accessing a relationship without eager loading (`selectinload` or `refresh(attribute_names=...)`) in an async context → causes a runtime error.
- ❌ Expecting a big performance boost for single/simple requests — async gains mainly appear **under concurrent load**, not in casual dev testing.
- ❌ Premature optimization — for learning/small projects, sync is perfectly fine; only convert to async once you actually need to handle load.

---

## 11. Quick Recap of the Whole Migration

1. Installed `aiosqlite` (async DB driver) + `greenlet`.
2. `database.py`: async engine, async session maker (`expire_on_commit=False`), async `get_db()` generator.
3. `main.py`: replaced `create_all()` at import time with a **lifespan** function (create tables at startup, dispose engine at shutdown).
4. Converted every DB-touching route to `async def`, using `await` for `execute`, `commit`, `refresh`, `delete` (but not `add`).
5. Added `selectinload(...)` or `refresh(attribute_names=[...])` anywhere relationships are accessed, since **lazy loading is not supported in async**.
6. Swapped custom exception handlers for FastAPI's **built-in async default handlers**.
7. Verified everything still works the same externally — the change is purely internal (better concurrency handling).

**Next planned topics (per the video):** reorganize routes using `APIRouter` (like Flask blueprints) since `main.py` is getting large → then add forms + authentication.
