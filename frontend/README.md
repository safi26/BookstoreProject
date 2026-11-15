# LibraryUi

This project was generated with [Angular CLI](https://github.com/angular/angular-cli) version 16.2.16.

## Authentication and permissions

Sign in with a numeric Django user ID and that account's password. The backend
returns a token and derives the role from the account: staff, superusers, and
members of the `Manager` group are managers; other accounts are students. The
frontend's role checks only control presentation; the API enforces manager-only
catalog changes and sales history, and restricts cart and checkout access to
the authenticated cart owner. Run `python3 manage.py migrate` in `backend/` to
create the token-auth tables. Create accounts through Django admin or
`python3 manage.py createsuperuser`.

### Staff PIN verification for discount overrides

Managers must configure a separate staff PIN before an account can approve
student-ID or employee-discount overrides. In Django admin, open **Staff
credentials**, choose an active Manager or Operator account, and set a PIN of
4–12 digits. PINs are stored as password hashes and are never displayed again;
leave the PIN field blank when editing to keep the current PIN. To change it,
enter a new PIN and save.

When an override is requested, a staff member enters their numeric Django user
ID and PIN. Invalid credentials are rejected. Successful verification
authorizes override requests for five minutes and is rate-limited to five
attempts per minute per IP address. The authorization is separate from the shopper's account,
so the shopper's cart and checkout identity do not change.

### Local development accounts

These accounts exist in the current local development database and may not be
present in a fresh database:

| User ID | Username | Role |
|---:|---|---|
| 8 | Sarmila | Student |
| 9 | User | Student |
| 1 | safi | Manager |
| 2 | testuser | Manager |
| 3 | testman | Manager |

Use the numeric User ID and the account's locally configured password to sign
in. Passwords are intentionally not stored in this README; set or reset them
locally through Django admin or the Django shell. These development accounts
and their passwords are not suitable for production.

Only manager-configured category discounts are accepted at checkout. Students
cannot submit line discounts themselves.

Managers can create named course supply bundles from non-apparel catalog
items, such as a class kit. Adding a bundle adds one of each component as
individual cart items. Available items are added, and any unavailable items
are called out by name.

### Cash drawer change warning

Managers can set the cash drawer's opening/current balance and the minimum
balance for a low-change warning from the store page. The warning is visible to
Managers and Operators whenever the recorded balance is below that threshold.
Successful cash checkouts add the sale total to the drawer balance (cash
received less change returned); card checkouts do not affect it. Set the opening
balance to the amount physically counted when starting a drawer. Drawer balance
and threshold are shared across the store and persisted in Django.
After a student applies an ID with staff PIN verification, the cash checkout
shows a warning if the projected drawer balance after the sale and change is
below the manager-set threshold. Students cannot read drawer details without a
valid staff verification token.

### Daily sales report

Managers can open **Daily sales report** from the store page and select a date
to see that day's completed sale count, total sales collected (after discounts
and including tax), receipt details, and sales totals by item category.
Category totals include each sold line's tax and reflect its final discounted
selling price.

Managers can open **Best-selling items** and choose an inclusive start and end
date to see items ranked by total quantity sold. Apparel size/color variants
are combined under their catalog item.

Students can request staff removal of a cart item using the **Remove item
(staff)** action. A Manager or Operator must verify their staff ID and PIN;
the removal audit stores the student and staff IDs, item/variant details,
quantity, and server timestamp. The audit is available read-only in Django
admin.

Staff can use **Change price (staff)** on a student's cart item to update the
catalog price used by the current transaction and future sales. The staff
member must verify their ID and PIN and enter a reason. The audit records the
original and new price, reason, student/staff IDs, and timestamp; completed
sales receipts remain unchanged.

### Apparel size and color inventory

Apparel stock is tracked by a distinct size/color variant. Managers can open
**Manage variants** on an apparel item to add or edit XS, S, M, L, XL, or XXL
variants in Blue, Green, Black, Grey, or Red, and set each combination's quantity. Students must
select an in-stock size/color before adding apparel to their cart. Cart lines,
checkout inventory deductions, and receipts retain the selected variant.

On migration, each existing apparel item's stock is preserved in an
`Unspecified` size/color variant. New apparel items begin with no stock; add
their size/color combinations through **Manage variants**.

## Development server

Run `ng serve` for a dev server. Navigate to `http://localhost:4200/`. The application will automatically reload if you change any of the source files.

### Secure local card form

Chrome disables card autofill on insecure HTTP pages. For local HTTPS, install
[`mkcert`](https://github.com/FiloSottile/mkcert) and trust its local development
certificate authority on your machine:

```sh
brew install mkcert
mkcert -install
cd frontend
mkdir -p .certs
mkcert -cert-file .certs/localhost.pem -key-file .certs/localhost-key.pem localhost 127.0.0.1 ::1
npm run start:https
```

Open `https://localhost:4200/` and accept the certificate prompt if the browser
shows one. The certificate files are local-only and excluded from Git. Do not use
these development certificates in production. This HTTPS setup only secures the
demo form; card details are still not sent, stored, or charged.

## Code scaffolding

Run `ng generate component component-name` to generate a new component. You can also use `ng generate directive|pipe|service|class|guard|interface|enum|module`.

## Build

Run `ng build` to build the project. The build artifacts will be stored in the `dist/` directory.

## Catalog categories

The manager catalog is for books and other store items. Django seeds exactly these categories when migrations are applied: Snacks, Drinks, Stationery, Exam Supplies, Art Supplies, Apparel, Course Supplies, and Books. Managers assign each item to one of these categories while adding or editing it.

Managers can add categories from the store interface. New categories appear in
the category filter and can be selected when creating or editing items.
Managers can delete an empty selected category; categories must have their
items moved or removed first.

Managers can toggle tax-exempt status for the selected category or individual
items in the store interface. A category exemption applies to every item in that
category; an item's own exemption can be managed separately. Items are taxed at
the standard 8.25% rate unless their category or item is marked tax-exempt. The
cart and receipt show the subtotal, tax, and tax-inclusive total separately.

Students can cancel an in-progress transaction from the cart or card-payment
dialog. Canceling clears the server-side cart without creating a sale or
changing inventory, then returns to the catalog ready for the next customer.

## Running unit tests

Run `ng test` to execute the unit tests via [Karma](https://karma-runner.github.io).

## Running end-to-end tests

Run `ng e2e` to execute the end-to-end tests via a platform of your choice. To use this command, you need to first add a package that implements end-to-end testing capabilities.

## Further help

To get more help on the Angular CLI use `ng help` or go check out the [Angular CLI Overview and Command Reference](https://angular.io/cli) page.
