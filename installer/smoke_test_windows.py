import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "installer-output" / "BookstoreSetup.exe"


def run():
    if os.name != "nt":
        raise OSError("The installer smoke test must run on Windows.")
    if not INSTALLER.is_file():
        raise FileNotFoundError(f"Installer not found: {INSTALLER}")

    with tempfile.TemporaryDirectory(prefix="bookstore-installer-test-") as temporary_dir:
        test_root = Path(temporary_dir)
        install_dir = test_root / "installed"
        data_dir = test_root / "user-data"
        env = os.environ.copy()
        env["BOOKSTORE_DATA_DIR"] = str(data_dir)

        subprocess.run(
            [
                str(INSTALLER),
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
                f"/DIR={install_dir}",
            ],
            check=True,
        )

        app_executable = install_dir / "Bookstore.exe"
        if not app_executable.is_file():
            raise RuntimeError("The installer did not install Bookstore.exe.")

        start_menu = (
            Path(os.environ["APPDATA"])
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Bookstore Management System.lnk"
        )
        desktop = Path(os.environ["USERPROFILE"]) / "Desktop" / "Bookstore Management System.lnk"
        if not start_menu.is_file():
            raise RuntimeError(f"The Start Menu shortcut is missing: {start_menu}")
        if not desktop.is_file():
            raise RuntimeError(f"The desktop shortcut is missing: {desktop}")

        for launch_number in (1, 2):
            subprocess.run(
                [str(app_executable), "--smoke-test"],
                check=True,
                env=env,
                timeout=120,
            )
            if not (data_dir / "bookstore.sqlite3").is_file():
                raise RuntimeError(f"SQLite data was not created on launch {launch_number}.")

        database_path = data_dir / "bookstore.sqlite3"
        if not database_path.is_file():
            raise RuntimeError("The persistent SQLite database is missing before uninstall.")

        subprocess.run(
            [
                str(install_dir / "unins000.exe"),
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
            ],
            check=True,
        )
        if not database_path.is_file():
            raise RuntimeError("Uninstall unexpectedly removed the user database.")

    print("Windows installer install, launch, API, database, shortcuts, and uninstall smoke tests passed.")


if __name__ == "__main__":
    run()
