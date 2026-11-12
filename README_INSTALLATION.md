# Installing Bookstore Management System

## Install and launch

1. Download `BookstoreSetup.exe` from the delivery location supplied by the
   development team.
2. On 64-bit Windows 10/11, double-click the installer and follow the prompts.
   No separate installation of Python, Node.js, Angular, or project
   dependencies is needed.
3. Use the **Bookstore Management System** desktop shortcut or Start Menu entry
   to launch the application. The launcher starts its local web service and
   opens the application in your default browser.
4. On a new installation, create the first manager account when prompted. Keep
   the numeric user ID shown after setup; the sign-in page uses that ID and the
   password you chose.
5. Keep the launcher window open while using the application. Close that
   window to stop the local service.

The application listens only on the local computer and chooses an available
local port when it starts. It does not expose the bookstore service to the
network.

## Application data and upgrades

The SQLite database and generated Django secret key are stored in:

```text
%LOCALAPPDATA%\CommonplaceBooks\
```

The database file is `bookstore.sqlite3`. Application upgrades leave this data
in place and Django applies pending migrations at startup. Uninstalling removes
the application and its shortcuts, but does not remove this user data. Back up
the database before reinstalling Windows or moving to another computer.

Uninstall from **Settings > Apps > Installed apps**. To remove bookstore data,
first uninstall the application, then manually remove the
`%LOCALAPPDATA%\CommonplaceBooks\` folder. This deliberate manual step avoids
accidentally deleting the database during an ordinary uninstall.

## Troubleshooting

- If startup fails, the launcher displays a message and the log is at
  `%LOCALAPPDATA%\CommonplaceBooks\logs\bookstore.log`.
- If the browser does not open automatically, use **Open Bookstore** in the
  launcher window.
- A new installation creates a manager account only when the local database
  has no users. Existing accounts and passwords are not changed during an
  upgrade.
- The packaged app requires permission to write to the current Windows user's
  Local AppData directory.

The card checkout in this project is a demo authorization only; it does not
charge a payment card.
