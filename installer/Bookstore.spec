import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules


ROOT = Path(SPECPATH).parent
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
BUILD_DIR = ROOT / "installer" / "build"
FRONTEND_BUILD = BUILD_DIR / "frontend"
STATIC_ROOT = BUILD_DIR / "staticfiles"

datas = [
    (str(FRONTEND_BUILD), "frontend"),
    (str(STATIC_ROOT), "staticfiles"),
]
binaries = []
hiddenimports = collect_submodules("bookstore") + collect_submodules("config")

for package in ("django", "rest_framework", "drf_spectacular", "waitress", "whitenoise"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas.extend(package_datas)
    binaries.extend(package_binaries)
    hiddenimports.extend(package_hiddenimports)

analysis = Analysis(
    [str(ROOT / "installer" / "launcher.py")],
    pathex=[str(ROOT / "backend")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Bookstore",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Bookstore",
)
