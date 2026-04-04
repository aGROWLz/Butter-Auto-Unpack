# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for Butter Auto Unpack
Butter自动解压打包配置文件

This spec file configures PyInstaller to create a standalone Windows executable
that includes all necessary dependencies and resources.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 定义要打包的数据文件
# 格式: (源路径, 目标目录)
datas = [
    # 7z工具文件 - 必需的解压工具（完整版支持RAR）
    ('resources/7z.exe', 'resources'),
    ('resources/7z.dll', 'resources'),
    
    # Bandizip工具文件 - 可选的解压工具（支持更多格式）
    ('resources/bandizip/bz.exe', 'resources/bandizip'),
    ('resources/bandizip/ark.x64.dll', 'resources/bandizip'),
    ('resources/bandizip/ark.x86.dll', 'resources/bandizip'),
    
    # 配置文件模板
    ('config.template.json', '.'),
]

# 定义要打包的二进制文件（如果有）
binaries = []

# 隐藏导入 - PyInstaller可能无法自动检测的模块
hiddenimports = [
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'watchdog',
    'watchdog.observers',
    'watchdog.events',
    'sqlite3',
]

# Analysis对象 - 分析Python脚本及其依赖
a = Analysis(
    ['main.py'],                    # 主入口文件
    pathex=[],                      # 额外的搜索路径
    binaries=binaries,              # 二进制文件
    datas=datas,                    # 数据文件
    hiddenimports=hiddenimports,    # 隐藏导入
    hookspath=[],                   # 自定义hook路径
    hooksconfig={},                 # hook配置
    runtime_hooks=[],               # 运行时hook
    excludes=[],                    # 排除的模块
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# PYZ对象 - Python字节码归档
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

# EXE对象 - 可执行文件配置
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Butter-Auto-Unpack',       # 可执行文件名称
    debug=False,                    # 不启用调试模式
    bootloader_ignore_signals=False,
    strip=False,                    # 不strip符号（Windows上无效）
    upx=True,                       # 使用UPX压缩（如果可用）
    upx_exclude=[],                 # UPX排除列表
    runtime_tmpdir=None,            # 运行时临时目录
    console=False,                  # 不显示控制台窗口（GUI应用）
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',              # 应用图标
)

# 如果需要创建单目录分发（而不是单文件），可以使用COLLECT
# COLLECT会创建一个包含所有文件的目录
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='Butter-Auto-Unpack'
# )
