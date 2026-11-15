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
| GET, POST | `/api/bundles/` | List course supply bundles or create one with a name and catalog item IDs; managers can also update or delete bundles |
| GET, POST | `/api/items/{item_id}/variants/` | List or add an apparel size/color variant and its stock |
| GET, PATCH, DELETE | `/api/items/{item_id}/variants/{variant_id}/` | Retrieve, update, or remove a variant |
| POST | `/api/auth/login/` | Authenticate `{ "user_id": id, "password": "..." }`; returns a token and server-derived role (`Student`, `Manager`, or `Operator`) |
| POST | `/api/auth/staff/verify-pin/` | Verify `{ "staff_id": id, "pin": "..." }` for a signed-in shopper; returns a short-lived staff authorization token |
| POST | `/api/auth/logout/` | Revoke the authenticated token |
| GET | `/api/cash-drawer/` | Read shared cash drawer balance, manager-set low-change threshold, and low-balance status; Managers and Operators, or a shopper with valid staff-PIN authorization |
| PATCH | `/api/cash-drawer/` | Set cash drawer opening/current balance and warning threshold; Managers only |
| GET | `/api/reports/daily-sales/?date=YYYY-MM-DD` | Return a date's completed sales, total collected sales, and discounted/taxed totals by category; date defaults to server-local today; Managers only |
| GET | `/api/reports/best-selling-items/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` | Return items ranked by quantity sold over an inclusive date range; apparel variants are combined; Managers only |
| GET, DELETE | `/api/users/{user_id}/cart/` | Read or clear a user's cart; GET accepts optional `student_id` and `use_employee_discount` query params and requires `X-Staff-Authorization` for discount overrides |
| POST | `/api/users/{user_id}/cart/items/` | Add `{ "item": item_id, "quantity": 1 }`; apparel also requires `variant_id` |
| PATCH, DELETE | `/api/users/{user_id}/cart/items/{cart_item_id}/` | Set quantity with `{ "quantity": n }`, or remove the line |
| POST | `/api/users/{user_id}/cart/items/{cart_item_id}/staff-remove/` | Remove a line from the signed-in shopper's cart after staff PIN verification; persist item, quantity, staff ID, shopper ID, and timestamp |
| POST | `/api/users/{user_id}/cart/items/{cart_item_id}/staff-price-change/` | After staff PIN verification, update the catalog price used by the shopper's current cart and future sales; require a reason and audit original/new price, staff ID, shopper ID, and timestamp |
| POST | `/api/users/{user_id}/checkout/` | Complete cash or demo-card checkout with optional `student_id` and `use_employee_discount`; requires `X-Staff-Authorization` for discount overrides; returns and persists the itemized receipt; rejects client-supplied discounts |
| GET | `/api/schema/` | OpenAPI schema |
| GET | `/api/docs/`, `/api/redoc/` | Swagger UI and ReDoc |

Item responses contain `item_id`, `item`, `item_quantity`, `item_price`, `author`, `item_code`, `isbn`, `badge`, `cover_url`, `category` (the category ID), and `category_name`. Category is the only shelf/filter classification; there is no separate catalog field. `cover_url` prefers the item's stored URL and otherwise derives an Open Library cover URL from ISBN. Cart responses use `cart_items`, `total_items`, `subtotal`, `discount_total`, `customer_discount_type`, `customer_discount_percent`, `customer_discount_amount`, `tax_amount`, and `total_price`; each cart line includes an `item_details` object matching the full item response. Prices are serialized as decimal strings on item fields; calculated totals may be JSON numbers.

Apparel item responses also include `variants: [{ "variant_id": id, "size": "M", "color": "Blue", "quantity": 4 }]`. Supported sizes are XS, S, M, L, XL, and XXL; supported colors are Blue, Green, Black, Grey, and Red. Each size/color combination has independent stock. Cart additions for apparel require `variant_id`; cart lines and receipt items snapshot the selected size and color. The item's `item_quantity` is the aggregate across its variants. Existing apparel stock is migrated into an `Unspecified` size/color variant; new apparel should have variants created through the nested endpoint.

Only managers can configure category-level percent-off or dollar-off discounts. They automatically apply to all items in the category, are capped at each line subtotal, and tax is calculated after discount. Students cannot submit or override discounts during checkout. Receipts persist `discount_total` and each line's effective discount type, value, and amount.

Managers can create named course supply bundles from non-apparel catalog items. Selecting a bundle adds one of each component as individual cart lines; out-of-stock or otherwise unavailable items are reported by name while available components are still added. Items referenced by a bundle cannot be deleted until they are removed from the bundle.

## Frontend Integration Rules

1. Add or update typed request/response interfaces and methods in `StoreApiService` to match the serializer fields and HTTP methods exactly.
2. Load the catalog from categories and items; do not restore the removed hard-coded catalog or browser-local catalog persistence.
3. Convert backend fields at the dashboard boundary. The API stores author, item code, ISBN, badge, and optional cover URL. Use category as the sole classification; do not reintroduce a separate catalog property or selector. The UI uses a designed fallback when a cover URL is absent or unavailable.
4. Item create/update payloads contain `item`, `item_quantity`, `item_price`, `author`, `item_code`, `isbn`, `badge`, and a numeric `category` ID. `cover_url` is read-only through the current item serializer. Category selection maps names to IDs from the category endpoint.
5. Login verifies a numeric Django user primary key and password at `/api/auth/login/`; the backend derives Manager from `is_staff`, `is_superuser`, or membership in the `Manager` group, derives Operator from membership in the `Operator` group (checked first), and treats other authenticated users as Students. The token is sent in the `Authorization: Token ...` header and revoked on logout. Login is limited to 10 attempts per minute.
6. Cart endpoints require the authenticated user's numeric Django primary key. `AuthService` persists the server-returned user ID and token in session storage and exposes `currentUserId` only when it is a positive integer. The backend enforces cart ownership, manager-only catalog mutations and sales history, and public read-only catalog access. Frontend role checks are presentation guards only; server permissions are authoritative.
7. The manager daily sales report uses the requested `YYYY-MM-DD` date (defaulting to server-local today) and completed persisted sales. Total collected sales sum each receipt total (after discounts and including tax); category totals sum each receipt item's final line amount plus its tax.
8. The manager best-selling-items report requires an inclusive start/end date and ranks receipt-line item snapshots by summed quantity sold; item variants roll up under the item's name and code.
9. Cart contents live in Django keyed by that user ID; signing out clears the browser session but not the cart. Re-enter the same Django user ID at the next login to restore cart lines and their nested item details. Refresh cart state after successful mutations; surface API errors instead of silently reverting to a local-only cart.

## Authentication And Checkout Limits

- Login uses Django's user ID and password; create local accounts through Django admin or `createsuperuser`, and run `python3 manage.py migrate` to install token-auth tables.
- Configure a separate 4–12 digit hashed PIN for active Manager or Operator accounts in Django admin. A signed-in shopper must verify a staff ID and PIN through `/api/auth/staff/verify-pin/` before applying a student-ID or employee-discount override; the returned `X-Staff-Authorization` value is valid for five minutes. PIN verification is limited to five attempts per minute per IP. The staff verification does not change the shopper/cart identity.
- Removing an item from a student cart requires a valid staff PIN authorization. The backend records a durable removal audit with student/staff user IDs, item and variant snapshot, quantity, and server timestamp before deleting the cart line.
- A staff price change on a student cart requires a valid staff PIN authorization and a non-empty reason. It updates the catalog price (and thus the active cart and future sales), leaves completed receipt snapshots unchanged, and stores the original/new price, reason, student/staff IDs, item snapshot, and server timestamp in a read-only audit.
- The cash drawer has one shared balance and low-change threshold. Managers configure the opening/current balance and threshold in the store UI. Cash sales increase the balance by cash received minus change returned; card sales do not affect it. Managers and Operators can see a warning when the balance is below the threshold. On a student checkout, display the projected post-sale low-balance warning only after student-ID override staff PIN verification; the drawer endpoint requires that valid short-lived staff authorization for student access.
- Student checkout is persisted by `/api/users/{user_id}/checkout/`: manager-configured category discounts are applied before tax, cash is validated and change is calculated on the server, stock is decremented transactionally, cart rows are cleared only on success, and receipt item details are snapshotted in the database.
- Card checkout is a demo authorization only. Cardholder name, number, expiry, and CVV are used transiently in the browser and are not sent to the API, stored, or charged. A card number ending in `0000` simulates a decline; other valid details are approved before the API records the card-demo sale. Keep this limitation visible; do not describe the endpoint as processing a real payment.

## Discounts

- Prices are calculated only in `backend/bookstore/pricing.py`. Two discounts stack in this order: the category discount above, then a customer discount (student or employee) taken as a percent of what remains. Customer rates are fixed in `CUSTOMER_DISCOUNT_RATES`: student 10%, employee 20% (placeholder values).
- A Student needs an active `StudentId` from the roster in Django admin. An invalid ID returns 400 with "Enter a valid student ID." and blocks payment until it is corrected or cleared; a blank ID pays full price. Applying the ID requires a recent staff PIN verification.
- A Manager can request the employee discount with the "Use Employee Discount?" checkbox; it is unchecked by default and requires staff PIN verification. An Operator gets the employee discount automatically, but must verify staff PIN before checkout. Managers and Operators can check out.
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