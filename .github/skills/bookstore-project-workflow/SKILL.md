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
| GET, PUT, PATCH, DELETE | `/api/categories/{category_id}/` | Retrieve or modify a category, including tax exemption and its holiday discount |
| GET, POST | `/api/items/` | List or create items |
| GET, PUT, PATCH, DELETE | `/api/items/{item_id}/` | Retrieve or modify an item |
| GET, POST | `/api/items/{item_id}/variants/` | List or add an apparel size/color variant and its stock |
| GET, PATCH, DELETE | `/api/items/{item_id}/variants/{variant_id}/` | Retrieve, update, or remove a variant |
| POST | `/api/auth/login/` | Authenticate `{ "user_id": id, "password": "..." }`; returns a token and server-derived role (`Student`, `Manager`, or `Operator`) |
| POST | `/api/auth/logout/` | Revoke the authenticated token |
| GET, DELETE | `/api/users/{user_id}/cart/` | Read or clear a user's cart; GET accepts optional `student_id` and `use_employee_discount` query params |
| POST | `/api/users/{user_id}/cart/items/` | Add `{ "item": item_id, "quantity": 1 }`; apparel also requires `variant_id` |
| PATCH, DELETE | `/api/users/{user_id}/cart/items/{cart_item_id}/` | Set quantity with `{ "quantity": n }`, or remove the line |
| POST | `/api/users/{user_id}/checkout/` | Complete cash or demo-card checkout with optional `student_id` and `use_employee_discount`; returns and persists the itemized receipt; rejects client-supplied discounts |
| GET | `/api/schema/` | OpenAPI schema |
| GET | `/api/docs/`, `/api/redoc/` | Swagger UI and ReDoc |

Item responses contain `item_id`, `item`, `item_quantity`, `item_price`, `author`, `item_code`, `isbn`, `badge`, `cover_url`, `category` (the category ID), and `category_name`. Category is the only shelf/filter classification; there is no separate catalog field. `cover_url` prefers the item's stored URL and otherwise derives an Open Library cover URL from ISBN. Cart responses use `cart_items`, `total_items`, `subtotal`, `discount_total`, `customer_discount_type`, `customer_discount_percent`, `customer_discount_amount`, `tax_amount`, and `total_price`; each cart line includes an `item_details` object matching the full item response. Prices are serialized as decimal strings on item fields; calculated totals may be JSON numbers.

Apparel item responses also include `variants: [{ "variant_id": id, "size": "M", "color": "Blue", "quantity": 4 }]`. Supported sizes are XS, S, M, L, XL, and XXL; supported colors are Blue, Green, Black, Grey, and Red. Each size/color combination has independent stock. Cart additions for apparel require `variant_id`; cart lines and receipt items snapshot the selected size and color. The item's `item_quantity` is the aggregate across its variants. Existing apparel stock is migrated into an `Unspecified` size/color variant; new apparel should have variants created through the nested endpoint.

Only managers can configure category-level percent-off or dollar-off discounts. They automatically apply to all items in the category, are capped at each line subtotal, and tax is calculated after discount. Students cannot submit or override discounts during checkout. Receipts persist `discount_total` and each line's effective discount type, value, and amount.

## Frontend Integration Rules

1. Add or update typed request/response interfaces and methods in `StoreApiService` to match the serializer fields and HTTP methods exactly.
2. Load the catalog from categories and items; do not restore the removed hard-coded catalog or browser-local catalog persistence.
3. Convert backend fields at the dashboard boundary. The API stores author, item code, ISBN, badge, and optional cover URL. Use category as the sole classification; do not reintroduce a separate catalog property or selector. The UI uses a designed fallback when a cover URL is absent or unavailable.
4. Item create/update payloads contain `item`, `item_quantity`, `item_price`, `author`, `item_code`, `isbn`, `badge`, and a numeric `category` ID. `cover_url` is read-only through the current item serializer. Category selection maps names to IDs from the category endpoint.
5. Login verifies a numeric Django user primary key and password at `/api/auth/login/`; the backend derives Manager from `is_staff`, `is_superuser`, or membership in the `Manager` group, derives Operator from membership in the `Operator` group (checked first), and treats other authenticated users as Students. The token is sent in the `Authorization: Token ...` header and revoked on logout. Login is limited to 10 attempts per minute.
6. Cart endpoints require the authenticated user's numeric Django primary key. `AuthService` persists the server-returned user ID and token in session storage and exposes `currentUserId` only when it is a positive integer. The backend enforces cart ownership, manager-only catalog mutations and sales history, and public read-only catalog access. Frontend role checks are presentation guards only; server permissions are authoritative.
7. Cart contents live in Django keyed by that user ID; signing out clears the browser session but not the cart. Re-enter the same Django user ID at the next login to restore cart lines and their nested item details. Refresh cart state after successful mutations; surface API errors instead of silently reverting to a local-only cart.

## Authentication And Checkout Limits

- Login uses Django's user ID and password; create local accounts through Django admin or `createsuperuser`, and run `python3 manage.py migrate` to install token-auth tables.
- Student checkout is persisted by `/api/users/{user_id}/checkout/`: manager-configured category discounts are applied before tax, cash is validated and change is calculated on the server, stock is decremented transactionally, cart rows are cleared only on success, and receipt item details are snapshotted in the database.
- Card checkout is a demo authorization only. Cardholder name, number, expiry, and CVV are used transiently in the browser and are not sent to the API, stored, or charged. A card number ending in `0000` simulates a decline; other valid details are approved before the API records the card-demo sale. Keep this limitation visible; do not describe the endpoint as processing a real payment.

## Discounts

- Prices are calculated only in `backend/bookstore/pricing.py`. Two discounts stack in this order: the category discount above, then a customer discount (student or employee) taken as a percent of what remains. Customer rates are fixed in `CUSTOMER_DISCOUNT_RATES`: student 10%, employee 20% (placeholder values).
- A Student needs an active `StudentId` from the roster in Django admin. An invalid ID returns 400 with "Enter a valid student ID." and blocks payment until it is corrected or cleared; a blank ID pays full price.
- A Manager gets the employee discount through the "Use Employee Discount?" checkbox at checkout, checked by default. An Operator gets it automatically. Managers and Operators can now check out.
- Tax is calculated on the price after both discounts. `Sale.subtotal` is after the category discount; `Sale` also stores `customer_discount_type`, `customer_discount_percent`, and `customer_discount_amount`, and `total` is `subtotal - customer_discount_amount + tax_amount`. `SaleItem.line_total` is net of both discounts and pre-tax, with `SaleItem.customer_discount_amount` beside the category `discount_amount`.
- The customer discount comes from the signed-in user's server-derived role, never from a role sent by the browser.

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