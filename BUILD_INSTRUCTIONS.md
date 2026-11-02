# Building the Windows installer

The installer is built on Windows because PyInstaller must bundle a Windows
Python runtime and Inno Setup must compile a Windows installer. The supported
build runs on Windows 10/11 or the repository's `windows-latest` GitHub Actions
runner.

## Local Windows build

Build and install targets are 64-bit Windows 10/11. Install:

- Python 3.13
- Node.js 20 (npm is included)
- Inno Setup 6

From the repository root, run these commands in PowerShell:

```powershell
py -3.13 -m venv .venv-installer
.\.venv-installer\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r installer\requirements-build.txt
python installer\build_windows.py --test-installer
```

The build script installs the locked Angular packages with `npm ci`, builds the
production frontend, collects Django static files, bundles Django and its
migrations with PyInstaller, and compiles the installer with Inno Setup. The
test option performs a silent install, checks both shortcuts, starts the
packaged application twice against the same SQLite database, verifies the
frontend and API endpoints, uninstalls, and confirms the database remains.

The deliverable is:

```text
installer-output\BookstoreSetup.exe
```

To build without running the install/uninstall smoke test, omit
`--test-installer`. Do not distribute an installer unless the build and smoke
test complete successfully.

## GitHub Actions build

Pushing to or opening a pull request against `sprint-03` runs
`.github/workflows/build-windows-installer.yml`. The job builds and smoke-tests
the installer on a fresh Windows runner. Download `BookstoreSetup-windows`
from the successful workflow run's **Artifacts** section. Manually triggering
the workflow is also supported.

The source build directory is `installer\build\`; it is generated locally and
is not part of the installer deliverable.
