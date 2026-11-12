import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER_DIR = ROOT / "installer"
BUILD_DIR = INSTALLER_DIR / "build"
FRONTEND_DIR = ROOT / "frontend"
FRONTEND_BUILD = BUILD_DIR / "frontend"
STATIC_ROOT = BUILD_DIR / "staticfiles"
BUILD_DATA_DIR = BUILD_DIR / "build-data"
PYINSTALLER_DIST = BUILD_DIR / "pyinstaller-dist"
PYINSTALLER_WORK = BUILD_DIR / "pyinstaller-work"


def run(command, *, cwd, env=None):
    print("+", subprocess.list2cmdline([str(part) for part in command]))
    subprocess.run(command, cwd=cwd, env=env, check=True)


def find_inno_compiler():
    compiler = shutil.which("ISCC.exe") or shutil.which("iscc")
    if compiler:
        return Path(compiler)

    program_roots = (
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")),
        Path(os.environ.get("ProgramFiles", "C:/Program Files")),
    )
    for root in program_roots:
        candidate = root / "Inno Setup 6" / "ISCC.exe"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Inno Setup 6 was not found. Install it and make ISCC.exe available."
    )


def build():
    if os.name != "nt":
        raise OSError("The Windows installer must be built on Windows.")

    for generated_dir in (
        FRONTEND_BUILD,
        STATIC_ROOT,
        BUILD_DATA_DIR,
        PYINSTALLER_DIST,
        PYINSTALLER_WORK,
    ):
        if generated_dir.exists():
            shutil.rmtree(generated_dir)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "installer-output").mkdir(parents=True, exist_ok=True)

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        raise FileNotFoundError("Node.js/npm was not found on PATH.")
    run([npm, "ci"], cwd=FRONTEND_DIR)
    run(
        [
            npm,
            "run",
            "build",
            "--",
            "--configuration",
            "production",
            "--output-path",
            str(FRONTEND_BUILD),
        ],
        cwd=FRONTEND_DIR,
    )

    build_env = os.environ.copy()
    build_env["BOOKSTORE_PACKAGED"] = "1"
    build_env["BOOKSTORE_STATIC_ROOT"] = str(STATIC_ROOT)
    build_env["BOOKSTORE_DATA_DIR"] = str(BUILD_DATA_DIR)
    run(
        [sys.executable, "manage.py", "collectstatic", "--noinput", "--clear"],
        cwd=ROOT / "backend",
        env=build_env,
    )

    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(PYINSTALLER_DIST),
            "--workpath",
            str(PYINSTALLER_WORK),
            str(INSTALLER_DIR / "Bookstore.spec"),
        ],
        cwd=ROOT,
        env=build_env,
    )

    run(
        [str(find_inno_compiler()), str(INSTALLER_DIR / "Bookstore.iss")],
        cwd=INSTALLER_DIR,
    )
    installer = ROOT / "installer-output" / "BookstoreSetup.exe"
    if not installer.is_file() or installer.stat().st_size == 0:
        raise RuntimeError(f"Inno Setup did not create the expected installer: {installer}")
    print(f"Installer created: {installer}")


def main():
    parser = argparse.ArgumentParser(description="Build the Windows Bookstore installer.")
    parser.add_argument(
        "--test-installer",
        action="store_true",
        help="Install, smoke-test, and uninstall the generated installer.",
    )
    args = parser.parse_args()

    build()
    if args.test_installer:
        run(
            [sys.executable, str(INSTALLER_DIR / "smoke_test_windows.py")],
            cwd=ROOT,
        )


if __name__ == "__main__":
    main()
