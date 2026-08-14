# PyInstaller spec — builds a single-file PlanMyTrip.exe from desktop.py.
# Build with:  pyinstaller PlanMyTrip.spec   (see build-exe.bat)
from PyInstaller.utils.hooks import collect_submodules

# uvicorn/anyio load some workers dynamically; pull them in explicitly.
hiddenimports = (
    collect_submodules("uvicorn")
    + ["anyio._backends._asyncio"]
)

a = Analysis(
    ["desktop.py"],
    pathex=["."],
    binaries=[],
    datas=[("app/web", "app/web")],   # bundle the wired UI so the .exe can serve it
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PlanMyTrip",
    debug=False,
    strip=False,
    upx=True,
    console=True,          # show a console so first-run logs/errors are visible
    disable_windowed_traceback=False,
)
