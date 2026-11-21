# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

block_cipher = None
project_root = Path.cwd()

datas = [
    (str(project_root / "configs" / "*.yaml"), "configs"),
    (str(project_root / "ai" / "prompts" / "*.txt"), "ai/prompts"),
    (str(project_root / "document" / "templates" / "latex" / "*"), "document/templates/latex"),
    (str(project_root / "app" / "ui" / "styles.qss"), "app/ui"),
]

hiddenimports = [
    "pyside6",
    "sqlmodel",
    "sqlite3",
    "chromadb",
    "googleapiclient",
    "google_auth_oauthlib",
    "jinja2",
    "tenacity",
    "docx",
    "fitz",
    "yaml",
]

a = Analysis(
    ["app/main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="academic-ai",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="academic-ai",
)
