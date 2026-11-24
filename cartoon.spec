# PyInstaller spec -> one file: dist/Cartoon.exe (Windows) / dist/Cartoon (Linux test build)
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hidden = [], [], []
d, b, h = collect_all("imageio_ffmpeg")      # bundles the FFmpeg program itself
datas += d; binaries += b; hidden += h
hidden += collect_submodules("keyring.backends")   # Windows Credential Manager backend
hidden += ["certifi"]

icon = "assets/cartoon.ico" if os.path.exists("assets/cartoon.ico") else None

a = Analysis(
    ["run_cartoon.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
              "PySide6.QtQml", "PySide6.QtQuick", "PySide6.Qt3DCore", "PySide6.QtCharts",
              "PySide6.QtDataVisualization", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtPdf"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="Cartoon",
    console=False,          # no black console window
    upx=False,
    icon=icon,
)
