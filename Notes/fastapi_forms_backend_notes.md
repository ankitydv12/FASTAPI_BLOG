# FastAPI Backend Concepts — From "Front-End Forms" Video
(Front-end/JavaScript details skipped — backend/API concepts only)

---

## 🧠 Concept Briefing (Read This First)

This video was mostly about JavaScript/HTML, but a few important **backend/API design concepts** came up along the way:

1. **Sorting belongs on the backend, not the frontend.** Even though the symptom (posts appearing oldest-first) showed up in the UI, the fix was a backend query change (`order_by`), not JavaScript sorting.
2. **PATCH vs PUT is a semantic choice.** Partial updates (only some fields sent) should use `PATCH`; full replacement should use `PUT`.
3. **204 No Content is a real, meaningful status code** — it tells the client "success, but there's nothing to send back," which matters for how the client should react (e.g. redirect since the resource is gone).
4. **A JSON API is client-agnostic.** The same backend endpoints work for a browser, a mobile app, a desktop app, or a script — because the API doesn't know or care what's calling it, it just deals in JSON in/out.
5. **Hardcoded IDs are a temporary security hole.** Anything the "current user" should control (like `user_id`) needs to eventually come from **verified authentication**, not a value the client just sends — otherwise anyone can impersonate anyone.

---

## 1. Backend Fix: Ordering Query Results (`order_by`)

**Problem:** By default, SQLAlchemy/the DB returns rows in the order they were created (oldest → newest). For a blog/feed, users expect **newest first**.

**Fix:** Add `.order_by(...)` with `.desc()` to any query that returns a **list of posts**:

```python
result = await db.execute(
    select(model.Post).order_by(model.Post.date_posted.desc())
)
```

- `.desc()` → descending order (newest first).
- Without it → ascending order (oldest first) is the default.
- **Where this needed to be added** (any query returning a *list* of posts):
  1. `GET /api/posts` (get all posts)
  2. Home page route (list of posts for the homepage)
  3. User's posts page (all posts by a specific user, template route)
  4. `GET /api/users/{user_id}/posts` (API route — same idea)
- **Not needed** for single-post queries (e.g. `GET /api/post/{post_id}`) since there's no ordering to do on one row.

**Key backend principle:** Business logic (like sort order) belongs in the backend/database layer, not the client:
- DB-level `ORDER BY` is more efficient than sorting in JavaScript after the fact.
- Keeps behavior **consistent across all clients** (web, mobile, etc.) — the DB is the single source of truth, so no client has to duplicate that sorting logic itself.

**How to find every place you need a fix like this:** search your codebase for however you run queries (e.g. `db.execute`) to locate every spot that needs updating — useful general technique when a schema/behavior change needs to ripple across multiple endpoints.

---

## 2. PATCH vs PUT — Why It Matters

- **PUT** = full replacement — client sends the *entire* resource, all fields expected.
- **PATCH** = partial update — client sends only the fields being changed.
- In the edit-post flow: only `title` and `content` are sent (not `user_id`) → this is a **partial** update → correctly uses `PATCH`, not `PUT`.
- Takeaway: choosing the right HTTP method isn't arbitrary — it should reflect what's actually being sent/changed. Using `PATCH` here is "semantically correct" given only a subset of fields is updated.

---

## 3. Meaning of HTTP Status Codes in Practice

- **200 OK** → successful response *with* a body (e.g. returning the updated post after a PATCH).
- **204 No Content** → successful response with **no body** — used for DELETE, since there's nothing left to return once a resource is gone.
  - Client-side implication: since there's no content to show, the natural reaction is to navigate away (e.g. redirect to the home page) rather than try to re-render the now-nonexistent resource.
- Matching status codes to the *actual outcome* (not just always returning 200) helps clients react correctly without extra guesswork.

---

## 4. Why a JSON API Is Reusable Across Clients

- Because the backend only deals in **JSON in, JSON out**, it doesn't matter who's calling it — browser JavaScript, a mobile app, a desktop client, or a CLI script can all consume the exact same endpoints identically.
- This is the payoff of building a clean API layer separate from the presentation layer: **one backend, many possible front ends**, with zero duplication of business logic.

---

## 5. Separation of Concerns (Backend vs Frontend Responsibilities)

| Backend's job | Frontend's job |
|---|---|
| Data storage & retrieval | Presentation / UI |
| Validation | User interaction |
| Business logic (e.g. sort order) | Displaying success/error feedback |
| Returning consistent JSON + correct status codes | Deciding what to do with the response |

- The backend should be the **single source of truth** for behavior/logic; the frontend's job is just to call the API and react to what it gets back.

---

## 6. Security Note: Hardcoded User ID Is Temporary Scaffolding

- Right now, `user_id` is sent by the client itself (hardcoded in the JS for testing) — meaning **anyone calling the API directly could create/edit/delete posts as any user.**
- This is called out explicitly as **not secure** and purely a placeholder until authentication exists.
- **Planned real fix (future tutorial):** proper authentication using **JSON Web Tokens (JWT)**:
  - User registers/logs in.
  - The authenticated user's ID comes from their **verified token**, not from a client-supplied field.
  - The API will **verify ownership** server-side before allowing edit/delete operations on a post (i.e. check that the logged-in user actually owns the post being modified).
- **General principle to remember:** never trust a client-supplied identity field (like `user_id` in a request body) for authorization decisions — identity should come from a verified, server-side source (like a validated auth token), not from user input.

---

## 7. Quick Recap (Backend-Only Takeaways)

1. Sorting/business logic changes belong in backend queries (`order_by(...).desc()`), applied consistently everywhere a list of that resource is returned.
2. Use `PATCH` for partial updates, `PUT` for full replacements — pick the HTTP method that matches what's actually being sent.
3. Use `204 No Content` for successful deletes (or any response with nothing to return).
4. A well-designed JSON API is inherently reusable across any client type — this is the value of separating backend from frontend.
5. Never rely on client-provided identity (e.g. hardcoded/user-supplied `user_id`) for security — that's exactly the gap that real authentication (JWT, ownership checks) is meant to close, which is the next topic in the series.
