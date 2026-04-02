# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# 获取osam路径
try:
    import osam
    OSAM_PATH = os.path.dirname(osam.__file__)
except ImportError:
    OSAM_PATH = None

# 获取onnxruntime路径
try:
    import onnxruntime
    ONNXRUNTIME_PATH = os.path.dirname(onnxruntime.__file__)
except ImportError:
    ONNXRUNTIME_PATH = None

# 获取labelme路径（spec文件所在目录）
LABELME_PATH = os.path.dirname(os.path.abspath(SPEC))

block_cipher = None

# 收集数据文件
datas = []

# 添加osam模型的vocab文件
if OSAM_PATH:
    vocab_file = os.path.join(OSAM_PATH, '_models', 'yoloworld', 'clip', 'bpe_simple_vocab_16e6.txt.gz')
    if os.path.exists(vocab_file):
        datas.append((vocab_file, 'osam/_models/yoloworld/clip'))

# 添加labelme配置文件
config_file = os.path.join(LABELME_PATH, 'labelme', 'config', 'default_config.yaml')
if os.path.exists(config_file):
    datas.append((config_file, 'labelme/config'))

# 添加labelme图标文件
icons_dir = os.path.join(LABELME_PATH, 'labelme', 'icons')
if os.path.exists(icons_dir):
    for icon_file in os.listdir(icons_dir):
        icon_path = os.path.join(icons_dir, icon_file)
        if os.path.isfile(icon_path):
            datas.append((icon_path, 'labelme/icons'))

# 添加翻译文件
translate_dir = os.path.join(LABELME_PATH, 'labelme', 'translate')
if os.path.exists(translate_dir):
    for trans_file in os.listdir(translate_dir):
        trans_path = os.path.join(translate_dir, trans_file)
        if os.path.isfile(trans_path):
            datas.append((trans_path, 'translate'))

# 添加图标路径
icon_path = os.path.join(LABELME_PATH, 'gsv_icon.ico')
if not os.path.exists(icon_path):
    # 如果 gsv_icon.ico 不存在，尝试使用默认图标
    icon_path = os.path.join(LABELME_PATH, 'labelme', 'icons', 'icon.ico')
    if not os.path.exists(icon_path):
        icon_path = os.path.join(LABELME_PATH, 'labelme', 'icons', 'icon.png')

# 收集onnxruntime的二进制文件
binaries = []

# 收集Python的DLL文件（特别是_ctypes相关的）
try:
    import sys
    python_dll_dir = os.path.dirname(sys.executable)
    python_dlls = ['python311.dll', 'python3.dll', 'python311_d.dll', 'python3_d.dll']
    for dll_name in python_dlls:
        dll_path = os.path.join(python_dll_dir, dll_name)
        if os.path.exists(dll_path):
            binaries.append((dll_path, '.'))
    
    # 收集DLLs目录下的所有DLL和PYD
    dlls_dir = os.path.join(python_dll_dir, 'DLLs')
    if os.path.exists(dlls_dir):
        for root, dirs, files in os.walk(dlls_dir):
            for file in files:
                if file.endswith(('.dll', '.pyd')):
                    dll_path = os.path.join(root, file)
                    rel_path = os.path.relpath(dll_path, dlls_dir)
                    binaries.append((dll_path, 'DLLs'))
    
    # 收集conda环境的Library/bin目录下的DLL（这些是扩展模块的依赖）
    # 如果是在conda环境中，查找Library/bin
    if 'conda' in python_dll_dir.lower() or 'anaconda' in python_dll_dir.lower():
        # 向上查找找到conda根目录（envs/labelme -> envs -> conda根目录）
        current_path = python_dll_dir
        conda_root = None
        
        # 查找conda根目录（包含envs目录的目录）
        for _ in range(5):  # 最多向上查找5级
            if os.path.basename(current_path) == 'envs':
                conda_root = os.path.dirname(current_path)
                break
            current_path = os.path.dirname(current_path)
            if not current_path or current_path == os.path.dirname(current_path):
                break
        
        # 如果找到了conda根目录，查找Library/bin
        if conda_root:
            lib_bin = os.path.join(conda_root, 'Library', 'bin')
            if os.path.exists(lib_bin):
                print(f"Found conda Library/bin: {lib_bin}")
                # 收集所有DLL文件
                try:
                    for file in os.listdir(lib_bin):
                        if file.endswith('.dll'):
                            dll_path = os.path.join(lib_bin, file)
                            if os.path.isfile(dll_path):
                                # 避免重复添加
                                if not any(b[0] == dll_path for b in binaries):
                                    binaries.append((dll_path, '.'))  # 放在根目录，更容易找到
                                    print(f"  Added DLL: {file}")
                except Exception as e:
                    print(f"Warning: Could not list DLLs in {lib_bin}: {e}")
        
        # 也尝试环境自己的Library/bin（如果有）
        env_lib_bin = os.path.join(python_dll_dir, 'Library', 'bin')
        if os.path.exists(env_lib_bin):
            print(f"Found env Library/bin: {env_lib_bin}")
            try:
                for file in os.listdir(env_lib_bin):
                    if file.endswith('.dll'):
                        dll_path = os.path.join(env_lib_bin, file)
                        if os.path.isfile(dll_path):
                            if not any(b[0] == dll_path for b in binaries):
                                binaries.append((dll_path, '.'))
                                print(f"  Added DLL: {file}")
            except Exception as e:
                print(f"Warning: Could not list DLLs in {env_lib_bin}: {e}")
    
except Exception as e:
    print(f"Warning: Could not collect Python DLLs: {e}")

# 收集onnxruntime的二进制文件
if ONNXRUNTIME_PATH:
    # 收集onnxruntime目录下的所有DLL和PYD文件
    for root, dirs, files in os.walk(ONNXRUNTIME_PATH):
        # 跳过__pycache__目录
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for file in files:
            if file.endswith(('.dll', '.pyd', '.so')):
                dll_path = os.path.join(root, file)
                # 保持相对路径结构
                rel_path = os.path.relpath(dll_path, ONNXRUNTIME_PATH)
                target_dir = os.path.dirname(rel_path) if os.path.dirname(rel_path) else '.'
                binaries.append((dll_path, target_dir))

a = Analysis(
    [os.path.join(LABELME_PATH, 'labelme', '__main__.py')],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'labelme',
        'labelme.app',
        'labelme.config',
        'labelme.utils',
        'labelme.widgets',
        'labelme.cli',
        'osam',
        'onnxruntime',
        'onnxruntime.capi',
        'onnxruntime.capi._pybind_state',
        'onnxruntime.capi.onnxruntime_pybind11_state',
        'loguru',
        'yaml',
        'numpy',
        'PIL',
        'matplotlib',
        'skimage',
        'skimage.io',
        'skimage.color',
        'skimage.transform',
        'skimage.util',
        'skimage.filters',
        'skimage.segmentation',
        'skimage.measure',
        'skimage.morphology',
        'skimage.feature',
        'imgviz',
        'ctypes',
        '_ctypes',
        'ctypes.util',
    ],
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
    name='Labelme',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 禁用UPX压缩，避免破坏DLL文件
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.exists(icon_path) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Labelme',
)
