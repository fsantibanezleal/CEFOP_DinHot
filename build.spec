# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for CEFOP_DinHot.

Build with:
    pyinstaller build.spec --clean --noconfirm

Or use the PowerShell script:
    .\\Build_PyInstaller.ps1
"""
from pathlib import Path

APP_NAME = "CEFOP_DinHot"
ENTRY_POINT = "run_app.py"

hidden_imports = [
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "uvicorn.lifespan",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
]

datas = []
static_dir = Path("app/static")
if static_dir.exists():
    datas.append((str(static_dir), "app/static"))

a = Analysis(
    [ENTRY_POINT],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "IPython", "jupyter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
