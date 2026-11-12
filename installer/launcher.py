import errno
import hmac
import json
import logging
import os
import secrets
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk


APP_NAME = "CommonplaceBooks"
STARTUP_TIMEOUT_SECONDS = 45


def _run_waitress(server, stopping):
    try:
        server.run()
    except OSError as exc:
        if stopping.is_set() and exc.errno in (errno.EBADF, errno.EINVAL, errno.ENOTSOCK):
            return
        raise


if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def _app_data_dir():
    configured_dir = os.environ.get("BOOKSTORE_DATA_DIR")
    if configured_dir:
        return Path(configured_dir)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def _read_or_create_secret(secret_path):
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            file_descriptor = os.open(
                secret_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError:
            secret = secret_path.read_text(encoding="utf-8").strip()
            if secret:
                return secret
            time.sleep(0.05)
            continue

        secret = secrets.token_urlsafe(64)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as secret_file:
            secret_file.write(secret)
        return secret


def _prepare_runtime():
    data_dir = _app_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    log_dir = data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    os.environ["BOOKSTORE_PACKAGED"] = "1"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ["BOOKSTORE_DATA_DIR"] = str(data_dir)
    os.environ["DJANGO_SECRET_KEY"] = _read_or_create_secret(data_dir / "django_secret_key")
    return data_dir / "logs" / "bookstore.log"


def _initial_manager_required():
    from django.contrib.auth import get_user_model

    return not get_user_model().objects.exists()


def _create_initial_manager(root):
    dialog = tk.Toplevel(root)
    dialog.title("Set up your bookstore")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()

    username = tk.StringVar()
    password = tk.StringVar()
    confirmation = tk.StringVar()
    created_user_id = []

    content = ttk.Frame(dialog, padding=18)
    content.grid(sticky="nsew")
    ttk.Label(
        content,
        text="Create the first manager account. Its numeric user ID will be shown after setup.",
        wraplength=360,
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

    fields = (
        ("Username", username, "normal"),
        ("Password", password, "password"),
        ("Confirm password", confirmation, "password"),
    )
    for row, (label, variable, show) in enumerate(fields, start=1):
        ttk.Label(content, text=label).grid(row=row, column=0, sticky="w", pady=5)
        entry = ttk.Entry(content, textvariable=variable, show="*" if show == "password" else "")
        entry.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=5)
        if row == 1:
            entry.focus_set()

    content.columnconfigure(1, weight=1)

    def create_account():
        name = username.get().strip()
        secret = password.get()
        if not name or not secret:
            messagebox.showerror("Account required", "Enter a username and password.", parent=dialog)
            return
        if secret != confirmation.get():
            messagebox.showerror("Passwords do not match", "Re-enter the same password.", parent=dialog)
            return

        from django.contrib.auth import get_user_model, password_validation
        from django.core.exceptions import ValidationError
        from django.db import DatabaseError, IntegrityError

        user_model = get_user_model()
        user = user_model(**{user_model.USERNAME_FIELD: name})
        try:
            password_validation.validate_password(secret, user=user)
            user_model.objects.create_superuser(
                **{user_model.USERNAME_FIELD: name},
                password=secret,
            )
        except ValidationError as exc:
            messagebox.showerror(
                "Choose a stronger password",
                "\n".join(exc.messages),
                parent=dialog,
            )
            return
        except IntegrityError:
            messagebox.showerror(
                "Username already exists",
                "Choose a different username.",
                parent=dialog,
            )
            return
        except DatabaseError:
            messagebox.showerror(
                "Could not create account",
                "The manager account could not be saved. Check the application log and try again.",
                parent=dialog,
            )
            return

        created_user_id.append(user_model.objects.get(**{user_model.USERNAME_FIELD: name}).pk)
        dialog.destroy()

    buttons = ttk.Frame(content)
    buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(14, 0))
    ttk.Button(buttons, text="Exit", command=dialog.destroy).pack(side="right")
    ttk.Button(buttons, text="Create manager", command=create_account).pack(side="right", padx=(0, 8))
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    root.wait_window(dialog)

    if created_user_id:
        messagebox.showinfo(
            "Manager account created",
            f"Your manager user ID is {created_user_id[0]}. Use it with your password to sign in.",
            parent=root,
        )
        return True
    return False


class BookstoreLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Bookstore Management System")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.status = tk.StringVar(value="Starting the bookstore...")
        self.open_button = ttk.Button(
            self.root,
            text="Open Bookstore",
            command=self.open_browser,
            state="disabled",
        )
        frame = ttk.Frame(self.root, padding=20)
        frame.grid(sticky="nsew")
        ttk.Label(frame, text="Bookstore Management System", font=("", 14, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        ttk.Label(frame, textvariable=self.status, wraplength=380).grid(
            row=1, column=0, sticky="w", pady=(0, 14)
        )
        self.open_button.grid(row=2, column=0, sticky="e")
        ttk.Button(frame, text="Exit", command=self.close).grid(row=2, column=1, sticky="e", padx=(8, 0))

        self.server = None
        self.server_thread = None
        self.server_error = None
        self.startup_error = None
        self.stopping = threading.Event()
        self.server_lock = threading.Lock()
        self.health_token = secrets.token_urlsafe(32)
        self.startup_deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
        self.base_url = None
        self.log_path = None
        self._closed = False

        threading.Thread(target=self._start_server, daemon=True).start()
        self.root.after(200, self._check_server)

    def _start_server(self):
        try:
            self.log_path = _prepare_runtime()
            logging.basicConfig(
                filename=self.log_path,
                level=logging.INFO,
                format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                encoding="utf-8",
            )
            os.environ["BOOKSTORE_HEALTH_TOKEN"] = self.health_token

            import django
            from django.core.management import call_command

            django.setup()
            call_command("migrate", interactive=False, verbosity=0)

            if self._closed:
                return
            from config.wsgi import application
            from waitress.server import create_server

            server = create_server(application, host="127.0.0.1", port=0, threads=4)
            with self.server_lock:
                if self._closed:
                    server.close()
                    server.task_dispatcher.shutdown()
                    return
                self.server = server
                self.base_url = f"http://127.0.0.1:{server.effective_port}"
                self.server_thread = threading.Thread(target=self._serve, daemon=True)
                self.server_thread.start()
        except Exception as exc:
            self.startup_error = exc
            logging.exception("Bookstore startup failed")

    def _serve(self):
        try:
            _run_waitress(self.server, self.stopping)
        except Exception as exc:
            self.server_error = exc
            logging.exception("Waitress stopped unexpectedly")

    def _check_server(self):
        if self._closed:
            return
        if self.startup_error or self.server_error:
            error = self.startup_error or self.server_error
            self._show_startup_error(error)
            return

        if self.base_url:
            try:
                with urllib.request.urlopen(
                    f"{self.base_url}/healthz/",
                    timeout=1,
                ) as response:
                    token = response.read().decode("utf-8")
                if hmac.compare_digest(token, self.health_token):
                    self._server_ready()
                    return
            except (OSError, urllib.error.URLError):
                pass

        if time.monotonic() >= self.startup_deadline:
            self._show_startup_error(
                TimeoutError("The local web service did not become ready in time.")
            )
            return
        self.root.after(250, self._check_server)

    def _server_ready(self):
        from django.db import close_old_connections

        try:
            manager_required = _initial_manager_required()
        except Exception as exc:
            close_old_connections()
            self._show_startup_error(exc)
            return
        close_old_connections()

        if manager_required and not _create_initial_manager(self.root):
            self.close()
            return

        self.status.set("Bookstore is running. You can close this window to stop it.")
        self.open_button.configure(state="normal")
        self.open_browser()

    def _show_startup_error(self, error):
        self.status.set("The bookstore could not start.")
        log_location = str(self.log_path) if self.log_path else "No log file was created."
        messagebox.showerror(
            "Bookstore startup failed",
            f"{error}\n\nDetails are available at:\n{log_location}",
            parent=self.root,
        )
        self.close()

    def open_browser(self):
        if not self.base_url:
            return
        try:
            opened = webbrowser.open(self.base_url, new=2)
        except OSError as exc:
            messagebox.showerror("Could not open browser", str(exc), parent=self.root)
            return
        if not opened:
            messagebox.showinfo(
                "Open Bookstore",
                f"Open this address in your browser:\n{self.base_url}",
                parent=self.root,
            )

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.stopping.set()
        with self.server_lock:
            server = self.server
        if server:
            server.close()
            server.task_dispatcher.shutdown()
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def smoke_test():
    log_path = _prepare_runtime()
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        encoding="utf-8",
    )
    health_token = secrets.token_urlsafe(32)
    os.environ["BOOKSTORE_HEALTH_TOKEN"] = health_token

    import django
    from django.core.management import call_command

    django.setup()
    call_command("migrate", interactive=False, verbosity=0)

    from config.wsgi import application
    from waitress.server import create_server

    server = create_server(application, host="127.0.0.1", port=0, threads=4)
    stopping = threading.Event()
    server_errors = []

    def serve():
        try:
            _run_waitress(server, stopping)
        except Exception as exc:
            server_errors.append(exc)

    server_thread = threading.Thread(target=serve, daemon=True)
    server_thread.start()
    base_url = f"http://127.0.0.1:{server.effective_port}"
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    try:
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(f"{base_url}/healthz/", timeout=1) as response:
                    token = response.read().decode("utf-8")
                if hmac.compare_digest(token, health_token):
                    break
            except (OSError, urllib.error.URLError):
                time.sleep(0.1)
        else:
            raise TimeoutError("The packaged web service did not become ready.")

        with urllib.request.urlopen(base_url, timeout=5) as response:
            frontend_html = response.read().decode("utf-8")
        if "<app-root>" not in frontend_html:
            raise RuntimeError("The production Angular frontend was not served.")

        for endpoint in ("/api/categories/", "/api/items/"):
            with urllib.request.urlopen(f"{base_url}{endpoint}", timeout=5) as response:
                if response.status != 200:
                    raise RuntimeError(f"The Django API returned HTTP {response.status} for {endpoint}.")
                if not isinstance(json.loads(response.read()), list):
                    raise RuntimeError(f"The Django API returned an unexpected response for {endpoint}.")

        with urllib.request.urlopen(
            f"{base_url}/static/rest_framework/css/bootstrap.min.css",
            timeout=5,
        ) as response:
            if response.status != 200:
                raise RuntimeError("Django static files were not served.")

        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        username = "bookstore-installer-smoke-test"
        user, created = user_model.objects.get_or_create(
            **{user_model.USERNAME_FIELD: username},
        )
        if created:
            user.set_password(secrets.token_urlsafe(32))
            user.save(update_fields=["password"])
        if not user_model.objects.filter(pk=user.pk).exists():
            raise RuntimeError("A SQLite record could not be saved.")
    finally:
        stopping.set()
        server.close()
        server.task_dispatcher.shutdown()
        server_thread.join(timeout=10)
        if server_thread.is_alive():
            raise RuntimeError("The packaged web service did not shut down cleanly.")
        if server_errors:
            raise RuntimeError("The packaged web service failed.") from server_errors[0]


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--smoke-test":
        smoke_test()
        return
    BookstoreLauncher().run()


if __name__ == "__main__":
    main()
