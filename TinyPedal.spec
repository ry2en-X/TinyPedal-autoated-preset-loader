# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


# PySide2-Daten und TinyPedal-Ressourcen sammeln.
datas = collect_data_files("PySide2")
datas += [
    (directory, directory)
    for directory in (
        "images",
        "settings",
        "brandlogo",
        "carsetups",
        "deltabest",
        "pacenotes",
        "trackmap",
        "tracknotes",
    )
]

# Keine collect_all() und KEINE collect_dynamic_libs().
# Genau diese automatische DLL-Analyse verursacht bei PySide2
# den Absturz im PyInstaller-Isolated-Process.

hiddenimports = [
    "PySide2.QtCore",
    "PySide2.QtGui",
    "PySide2.QtWidgets",
    "PySide2.QtNetwork",
    "PySide2.QtMultimedia",
]
hiddenimports += collect_submodules("tinypedal.module")
hiddenimports += collect_submodules("tinypedal.widget")


a = Analysis(
    ["run.py"],
    pathex=[
        os.path.abspath(SPECPATH)
    ],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide2.Qt3DAnimation",
        "PySide2.Qt3DCore",
        "PySide2.Qt3DExtras",
        "PySide2.Qt3DInput",
        "PySide2.Qt3DLogic",
        "PySide2.Qt3DRender",
        "PySide2.QtAxContainer",
        "PySide2.QtCharts",
        "PySide2.QtDataVisualization",
        "PySide2.QtHelp",
        "PySide2.QtLocation",
        "PySide2.QtOpenGL",
        "PySide2.QtOpenGLFunctions",
        "PySide2.QtPositioning",
        "PySide2.QtPrintSupport",
        "PySide2.QtQml",
        "PySide2.QtQuick",
        "PySide2.QtQuickControls2",
        "PySide2.QtQuickWidgets",
        "PySide2.QtRemoteObjects",
        "PySide2.QtScript",
        "PySide2.QtScriptTools",
        "PySide2.QtScxml",
        "PySide2.QtSensors",
        "PySide2.QtSerialPort",
        "PySide2.QtSql",
        "PySide2.QtSvg",
        "PySide2.QtTest",
        "PySide2.QtTextToSpeech",
        "PySide2.QtUiTools",
        "PySide2.QtWebChannel",
        "PySide2.QtWebEngine",
        "PySide2.QtWebEngineCore",
        "PySide2.QtWebEngineWidgets",
        "PySide2.QtWebSockets",
        "PySide2.QtWinExtras",
        "PySide2.QtXml",
        "PySide2.QtXmlPatterns",
    ],
    noarchive=False,
)


pyz = PYZ(
    a.pure,
    a.zipped_data,
)


exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TinyPedal",
    icon=r"images\icon.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)


coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="TinyPedal",
)