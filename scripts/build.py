import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

def build():
    print("Building Academic Assistant with PyInstaller...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(ROOT_DIR / "pyinstaller.spec"),
    ]
    subprocess.check_call(cmd, cwd=str(ROOT_DIR))
    print("Build complete! Check dist/academic-ai folder.")

if __name__ == "__main__":
    build()
