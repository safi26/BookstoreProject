---
name: bookstore-project-workflow
description: "Use when continuing the Commonplace Books project, especially Angular-to-Django API integration, catalog or cart changes, login behavior, shared page styling, or local run and verification steps."
---

# Bookstore Project Workflow

Use this skill when changing the bookstore app so frontend behavior stays aligned with the Django API and the implementation already in the repository.

## Project Shape

- `backend/` is Django REST Framework. URL registrations are in `backend/config/urls.py` and `backend/bookstore/urls.py`; serializers and behavior are in `backend/bookstore/serializers.py` and `backend/bookstore/views.py`.
- `frontend/` is a standalone-component Angular app. Routes are in `frontend/src/app/app.routes.ts`; shared HTTP calls live in `frontend/src/app/store-api.service.ts`; the store UI is `frontend/src/app/bookstore-dashboard.component.ts` and its template.
- Angular registers `HttpClient` through `provideHttpClient()` in `frontend/src/app/app.config.ts`.
- During `ng serve`, `frontend/proxy.conf.json` forwards `/api` to `http://127.0.0.1:8000`. Frontend services should use relative `/api/...` URLs, not hard-code a separate browser origin.

## API Contract

The root URL configuration exposes:

| Method | Endpoint | Behavior |
|---|---|---|
| GET, POST | `/api/categories/` | List or create categories (`category_name`) |
| GET, PUT, PATCH, DELETE | `/api/categories/{category_id}/` | Retrieve or modify a category |
| GET, POST | `/api/items/` | List or create items |
| GET, PUT, PATCH, DELETE | `/api/items/{item_id}/` | Retrieve or modify an item |
| GET, DELETE | `/api/users/{user_id}/cart/` | Read or clear a user's cart |
| POST | `/api/users/{user_id}/cart/items/` | Add `{ "item": item_id, "quantity": 1 }` |
| PATCH, DELETE | `/api/users/{user_id}/cart/items/{cart_item_id}/` | Set quantity with `{ "quantity": n }`, or remove the line |
| POST | `/api/users/{user_id}/checkout/` | Complete cash or demo-card checkout; returns and persists the itemized receipt |
| GET | `/api/schema/` | OpenAPI schema |
| GET | `/api/docs/`, `/api/redoc/` | Swagger UI and ReDoc |

Item responses contain `item_id`, `item`, `item_quantity`, `item_price`, `author`, `item_code`, `isbn`, `badge`, `cover_url`, `category` (the category ID), and `category_name`. Category is the only shelf/filter classification; there is no separate catalog field. `cover_url` prefers the item's stored URL and otherwise derives an Open Library cover URL from ISBN. Cart responses use `cart_items`, `total_items`, and `total_price`; each cart line includes an `item_details` object matching the full item response. Prices are serialized as decimal strings on item fields; calculated totals may be JSON numbers.

## Frontend Integration Rules

1. Add or update typed request/response interfaces and methods in `StoreApiService` to match the serializer fields and HTTP methods exactly.
2. Load the catalog from categories and items; do not restore the removed hard-coded catalog or browser-local catalog persistence.
3. Convert backend fields at the dashboard boundary. The API stores author, item code, ISBN, badge, and optional cover URL. Use category as the sole classification; do not reintroduce a separate catalog property or selector. The UI uses a designed fallback when a cover URL is absent or unavailable.
4. Item create/update payloads contain `item`, `item_quantity`, `item_price`, `author`, `item_code`, `isbn`, `badge`, and a numeric `category` ID. `cover_url` is read-only through the current item serializer. Category selection maps names to IDs from the category endpoint.
5. Cart endpoints require a numeric Django user primary key. `AuthService` persists the entered demo ID in session storage and exposes `currentUserId` only when it is a positive integer. Cart contents live in Django keyed by that user ID; signing out clears the browser session but not the cart. Re-enter the same Django user ID at the next demo login to restore cart lines and their nested item details. Refresh cart state after successful mutations; surface API errors instead of silently reverting to a local-only cart.
6. The current frontend role check is a presentation guard, not server-side authorization. Do not treat it as a security boundary.

## Authentication And Checkout Limits

- There is no backend login/authentication endpoint. The login screen creates a demo session with a selected role and entered ID; passwords are not verified by Django.
- A real numeric Django user ID is required for API-backed carts. Existing local development users can be inspected with `python3 manage.py shell` and Django's `get_user_model()`.
- Student checkout is persisted by `/api/users/{user_id}/checkout/`: cash is validated and change is calculated on the server, stock is decremented transactionally, cart rows are cleared only on success, and receipt item details are snapshotted in the database.
- Card checkout is a demo authorization only. There is no payment processor, no card data is collected, and no real charge is made. Keep this limitation visible; do not describe the endpoint as processing a real payment.

## Existing UI Conventions

- Global typography is DM Sans for interface text and Playfair Display for editorial headings, configured in `frontend/src/styles.scss`.
- Landing and login pages share the Commonplace wordmark, green/rust palette, and matching heading scale. Preserve those shared styles when changing either page.
- The store stylesheet is `frontend/src/app/bookstore.scss`; retain the existing green/rust bookstore palette and responsive layout.

## Run And Verify

Run the backend from `backend/`:

```sh
python3 -m pip install -r requirements.txt
python3 manage.py runserver 0.0.0.0:8000
```

Run the frontend from `frontend/`:

```sh
npm start -- --port 4200
npm run build
```

Verify `/api/items/` and `/api/categories/` directly on port 8000 or through the Angular proxy on port 4200. The integration has been smoke-tested with catalog loading, manager item POST/DELETE, and cart POST/DELETE. Cart smoke tests should remove their test line item afterward.

Checkout behavior is covered by `python3 manage.py test bookstore.tests.CheckoutApiTests`; keep cash-change, failed-payment rollback, card demo, stock, and receipt assertions in that test suite.

## Generated Files

The root `.gitignore` excludes `node_modules/`, `.angular/`, Python `__pycache__/` and bytecode, virtual environments, and `frontend/dist/`. Previously tracked bytecode and build artifacts were removed from the Git index with local files preserved; do not re-add generated output to source control.