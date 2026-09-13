# Organizing FastAPI with APIRouter — Revision Notes

---

## 🧠 Concept Briefing (Read This First)

**The problem:** As a FastAPI app grows, dumping every route into one `main.py` becomes unmanageable — imports, DB logic, template routes, API routes, and exception handlers all mixed together in one giant file.

**The core idea:** `APIRouter` lets you define routes in **separate files/modules**, then plug them into the main app. It's FastAPI's version of what Flask calls "blueprints."

**Mental model:**
- `app` = the whole restaurant.
- Each `router` = one *station* in the kitchen (e.g. "users station," "posts station") — it can prep its own routes independently.
- `app.include_router(...)` = wiring that station into the main restaurant, optionally giving it a shared prefix (e.g. everything from this station is served under `/api/users`) and a label (tag) for the menu (docs page).

**What actually changes vs. what doesn't:**
- ✅ Changes: *where* routes are defined (their own file), the decorator (`router.get` instead of `app.get`), and the path (relative to a prefix, so often becomes `""` or `/{id}`).
- ❌ Doesn't change: the actual logic inside each route — async/await, DB queries, validation, response models — all identical. This is purely an **organizational refactor**, not a functional one. Same URLs, same behavior, from the outside nothing changes.

**Why this matters (the "so what"):**
- Separation of concerns — post logic in `posts.py`, user logic in `users.py`, app config/front-end in `main.py`.
- Easier to navigate — you know exactly which file a given endpoint lives in.
- Scales cleanly — adding a new resource (e.g. "admin") just means adding a new router file following the same pattern.
- Team-friendly — different people can work on different routers with fewer merge conflicts.
- Testable in isolation — routers (and their dependencies) can be tested/mocked independently.
- Auto-organizes the `/docs` page into collapsible sections via tags.

**When to reach for this:** Once your `main.py` starts holding multiple unrelated resources' worth of routes (here: users + posts + templates + exception handlers all in one file) — that's the signal to split by router.

---

## 1. What Is an `APIRouter`?

- A tool for grouping related routes into their own module instead of registering everything directly on the main `app` object.
- Routes are defined the same way as before, just using `router.get`, `router.post`, etc. instead of `app.get`, `app.post`.
- The router is then "mounted" onto the main app using `app.include_router(...)`.

```python
# inside a router file
from fastapi import APIRouter
router = APIRouter()

@router.get("/{user_id}")
def get_user(...):
    ...
```

```python
# in main.py
from routers import users, posts

app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])
```

---

## 2. Project Structure Pattern

```
project/
├── main.py
├── routers/
│   ├── __init__.py      # empty, makes this a proper package
│   ├── users.py
│   └── posts.py
```

- `__init__.py` can stay completely empty. Not strictly required in modern Python, but still best practice — helps linters/type checkers recognize the folder as a package.
- Only **API routes** were moved into routers here. **Template/HTML routes** (home page, post page, user-posts page) stayed in `main.py`, so:
  - `main.py` → front-end views + app configuration + exception handlers
  - `routers/*.py` → pure API logic

---

## 3. How the Path + Prefix Combine

- Each router file uses **relative, empty-feeling paths** — e.g. `""` for the collection route, `"/{user_id}"` for a specific resource.
- The **prefix** is supplied once, when including the router in `main.py`:
```python
app.include_router(users.router, prefix="/api/users", tags=["users"])
```
- The final URL = `prefix + router path`. So:
  - Router path `""` + prefix `/api/users` → `/api/users`
  - Router path `/{user_id}` + prefix `/api/users` → `/api/users/{user_id}`

**Why use `""` instead of `"/"` for the base route?**
- Using `"/"` would create a trailing slash on the final URL (`/api/users/`), which can trigger unwanted 307 redirects.
- Using `""` keeps the final URL clean with no trailing slash.

---

## 4. What Moving a Route Actually Involves

Only **two things** change per route — nothing about the internal logic changes:

| Before (`main.py`) | After (router file) |
|---|---|
| `@app.post("/api/users")` | `@router.post("")` |
| `@app.get("/api/users/{user_id}")` | `@router.get("/{user_id}")` |

Everything else — `async def`, `await db.execute(...)`, validation, response models, business logic — is copy-pasted unchanged.

---

## 5. Per-Router Imports

- Each router file only imports what it actually needs (e.g. `users.py` only imports user-related schemas, not post schemas).
- Benefit: cleaner, more minimal imports per file instead of one bloated import block shared by everything.
- After moving routes out, go back to `main.py` and remove now-unused imports (e.g. schemas that are only used inside the routers now).

---

## 6. `app.include_router(...)` — What Its Arguments Do

```python
app.include_router(users.router, prefix="/api/users", tags=["users"])
```

- **`prefix`** — prepended to every route defined in that router. Lets the router itself stay "unaware" of its final mounted location.
- **`tags`** — purely for documentation (`/docs`). Groups all routes from that router under a labeled, collapsible section in the Swagger UI. Without tags, all routes would appear in one flat list.

---

## 7. Gotcha: Function Name Collisions

- FastAPI uses **function names** as route names internally (used for `url_for`-style lookups).
- If a router function has the **same name** as a template route function in `main.py` (e.g. two functions both named `home`), it can cause a naming conflict.
- **Solution:** always use unique, descriptive function names across the whole app — not just within a single file.

---

## 8. Verifying Nothing Broke

- After the refactor: same URLs, same request/response behavior, same validation — confirmed by testing the homepage, API routes, and Swagger docs.
- The `/docs` page now shows endpoints grouped into collapsible **Users** and **Posts** sections (from `tags`), instead of one long flat list.
- Net result on file size: `main.py` dropped from a large single file to well under 150 lines, with `users.py`/`posts.py` each holding roughly a similar amount — same total code, much better organized.

---

## 9. Alternative Ways to Organize Routers (Not Just by Resource)

The video organized by **resource** (`users.py`, `posts.py`) — common and intuitive — but other valid schemes exist depending on the project:

| Organize by... | Example |
|---|---|
| Resource (most common) | `users.py`, `posts.py` |
| API version | `v1/users.py`, `v2/users.py` |
| Access level | `public.py`, `admin.py` |
| Feature | `billing.py` |

Whichever scheme you pick, the underlying pattern (separate `APIRouter` per file, included with a prefix + tags in `main.py`) stays the same.

---

## 10. Quick Recap

1. Problem: `main.py` becomes bloated as an app grows — routes, imports, and logic for unrelated resources all mixed together.
2. Solution: `APIRouter` — define routes in their own file using `router.get/post/...` instead of `app.get/post/...`.
3. Create a `routers/` package (`__init__.py` + one file per resource).
4. Move only the **API** routes (not template/HTML routes) into their respective router files, each with its own minimal imports.
5. Router paths become relative (`""`, `/{id}`) since the **prefix** is applied once at inclusion time via `app.include_router(...)`.
6. `tags=[...]` organizes the `/docs` page into labeled sections.
7. Watch out for duplicate function names across files.
8. End result: identical external behavior, much better internal organization — same pattern used in virtually all real-world FastAPI projects.

**Next planned topics (per the video):** front-end forms using JavaScript's fetch API to talk to the now-organized API → then authentication (so only users can edit their own posts, enforced both on the front end and in the API).
