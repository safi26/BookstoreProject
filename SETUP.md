# Bookstore Management System setup

Use this guide to launch the Angular bookstore app and its Django API from source on Windows 10 or 11. If you have `BookstoreSetup.exe`, follow the [Windows installer guide](README_INSTALLATION.md).

## 1. Install the tools

- Run the 64-bit Windows installer for [Python 3.13](https://www.python.org/downloads/windows/). Keep the Python launcher enabled so you can use `py -3.13`.
- Run the Windows x64 MSI for [Node.js 18.20.8](https://nodejs.org/dist/v18.20.8/node-v18.20.8-x64.msi). It includes npm. This version is for local development with the project's [Angular 16.2 dependencies](https://angular.dev/reference/versions).
- Install [Git for Windows](https://git-scm.com/install/windows) if you need to clone the repository.

Open a new PowerShell window. If you already have the source, open PowerShell in the project folder and skip the clone.

```powershell
git clone https://github.com/safi26/BookstoreProject.git
cd BookstoreProject
```

## 2. Launch the Angular app on port 4200

From the project root, run these commands in PowerShell to install Angular, Angular CLI 16, and the other frontend dependencies from `frontend/package-lock.json`. The CLI is installed locally in `frontend/node_modules`.

```powershell
cd frontend
npm.cmd ci --include=dev
```

From the same `frontend` folder, run `ng serve` using the locally installed CLI.

```powershell
.\node_modules\.bin\ng.cmd serve --port 4200 --open
```

Run either this command or `npm.cmd start -- --port 4200 --open`. The `start` script in `frontend/package.json` calls `ng serve` for you. The local CLI is enough for both commands.

The app is available at [http://localhost:4200/](http://localhost:4200/). Keep this terminal open. Angular's development proxy forwards `/api` requests to Django on port 8000, so start Django before signing in or using the store.

## 3. Start the Django API on port 8000

Open a second PowerShell window in the project root. The requirements file installs Django and the API dependencies into the virtual environment. Django uses the project's local SQLite database at `backend/db.sqlite3`.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py createsuperuser
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

Choose a username and password when prompted. Django listens at `http://127.0.0.1:8000`. Keep this terminal open while using the app.

## 4. Sign in to the bookstore

Open [Django admin](http://127.0.0.1:8000/admin/), sign in with the username and password you created, then open **Users** and select your account. The number in the address ending in `/auth/user/<id>/change/` is your user ID. Open the [bookstore](http://localhost:4200/) and sign in with that numeric ID and the same password.

The [API docs](http://127.0.0.1:8000/api/docs/) are available while Django is running. Press **Ctrl+C** in each terminal to stop the servers.
