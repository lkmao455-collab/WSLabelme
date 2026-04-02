# 构建与发布技能 (Build & Release Skills)

## 1. PyInstaller 打包

### 1.1 spec 文件配置

```python
# labelme.spec 配置说明
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],  # 入口文件
    pathex=[],
    binaries=[],
    datas=[
        # 包含数据文件（UI、图标、配置等）
        ('mainform.ui', '.'),
        ('labelme/resources', 'labelme/resources'),
        ('labelme/config', 'labelme/config'),
    ],
    hiddenimports=[
        # 显式包含隐式导入的模块
        'pkg_resources.py2_warn',
        'numpy',
        'PIL',
        'PyQt5',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Labelme',  # 输出文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 启用压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False=GUI 程序，True=控制台程序
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',  # 应用图标
)
```

### 1.2 打包命令

```bash
# 使用 spec 文件打包
pyinstaller labelme.spec

# 单文件打包（启动较慢）
pyinstaller --onefile main.py

# 带控制台窗口（便于调试）
pyinstaller --console main.py

# 指定图标
pyinstaller --icon=icon.ico main.py

# 排除不必要的模块
pyinstaller --exclude-module=matplotlib main.py
```

### 1.3 打包优化

```python
# 在 spec 文件中排除不必要的模块
a = Analysis(
    ...
    excludes=[
        'matplotlib',
        'scipy',
        'pandas',
        'tkinter',
        'IPython',
        'jupyter',
    ]
)

# 减少包大小
# 1. 启用 UPX 压缩 (upx=True)
# 2. 排除不必要的数据文件
# 3. 使用 --onefile 而不是 --onedir
```

## 2. 版本管理

### 2.1 版本号规范

```python
# labelme/__init__.py
__version__ = '5.2.1'  # MAJOR.MINOR.PATCH

# 版本号规则：
# MAJOR: 重大变更（不兼容的 API 修改）
# MINOR: 功能更新（向后兼容的新功能）
# PATCH: Bug 修复（向后兼容的问题修复）
```

### 2.2 自动更新版本号

```python
# update_version.py
import re
from datetime import datetime

def update_version():
    with open('labelme/__init__.py', 'r') as f:
        content = f.read()

    # 获取当前版本
    match = re.search(r"__version__ = '(\d+)\.(\d+)\.(\d+)'", content)
    if match:
        major, minor, patch = map(int, match.groups())
        # 增加补丁版本
        new_version = f"{major}.{minor}.{patch + 1}"
        content = re.sub(
            r"__version__ = '[\d.]+'",
            f"__version__ = '{new_version}'",
            content
        )

    # 更新发布时间
    publish_date = datetime.now().strftime('%Y-%m-%d')

    with open('labelme/__init__.py', 'w') as f:
        f.write(content)

    print(f"版本已更新为：{new_version}")
    print(f"发布日期：{publish_date}")

if __name__ == '__main__':
    update_version()
```

### 2.3 发布说明

```markdown
# 发布说明模板

## [5.2.1] - 2026-03-23

### 修复
- 修复模型信息显示时可能的 KeyError
- 修复 canvas.py 中 AI 模型处理的异常捕获
- 修复配置文件加载时缺少异常处理的问题
- 修复 label_dialog.py 中 completer 空值问题

### 优化
- 改进异常处理，避免应用闪退
- 增强日志输出，便于问题排查

### 新增
- 添加完整的 skills 技能体系文档
```

## 3. 配置文件管理

### 3.1 默认配置

```yaml
# labelme/config/default_config.yaml
auto_save: false
display_label_popup: true
store_data: true
show_labels: true
show_confidence: true
validate_label: null
sort_labels: true
labels: null
keep_prev: false
keep_prev_scale: false
epsilon: 10.0

# 形状颜色配置
shape_color: auto
shape_label_colors:
  - text: '#000000'
  - background: '#FFFFFF'

# Canvas 配置
canvas:
  double_click: close
  num_backups: 10
  crosshair:
    polygon: false
    rectangle: true
    circle: false
    line: false
    point: false
    linestrip: false
    ai_polygon: false
    ai_mask: false

# Dock 窗口配置
flag_dock:
  show: true
  closable: false
  movable: false
  floatable: false

label_dock:
  show: true
  closable: false
  movable: false
  floatable: false

shape_dock:
  show: true
  closable: false
  movable: false
  floatable: false

file_dock:
  show: true
  closable: false
  movable: false
  floatable: false

# 快捷键配置
shortcuts:
  quit: Ctrl+Q
  open: Ctrl+O
  open_dir: Ctrl+U
  open_next: [D, Ctrl+Shift+D]
  open_prev: [A, Ctrl+Shift+A]
  save: Ctrl+S
  save_as: Ctrl+Shift+S
  delete_file: Ctrl+Delete
  close: Ctrl+W
  toggle_keep_prev_mode: Ctrl+P
  create_polygon: [N, Ctrl+N]
  create_rectangle: [R, Ctrl+R]
  edit_polygon: Ctrl+J
  delete_polygon: Delete
  duplicate_polygon: Ctrl+D
  copy_polygon: Ctrl+C
  paste_polygon: Ctrl+V
  undo: Ctrl+Z
  undo_last_point: Ctrl+Backspace
  zoom_in: [Ctrl++, Ctrl+=]
  zoom_out: Ctrl+-
  zoom_to_original: Ctrl+0
  fit_window: Ctrl+F
  fit_width: Ctrl+Shift+F
```

### 3.2 用户配置

```python
# 用户配置文件位置：~/.labelmerc
# 加载配置优先级：
# 1. 默认配置 (labelme/config/default_config.yaml)
# 2. 用户配置 (~/.labelmerc)
# 3. 命令行参数

from labelme.config import get_config

# 加载配置
config = get_config(
    config_file_or_yaml="~/.labelmerc",
    config_from_args={'auto_save': True}
)
```

### 3.3 TCP 配置

```python
# TCP 配置文件位置：~/.labelme_tcp_config.yaml
# 配置内容示例：
# host: 127.0.0.1
# port: 10012
# message: labelme
# interval: 2
# reconnect_interval: 5

from labelme.tcp_config import load_tcp_config

config = load_tcp_config()
host = config.get('host', '127.0.0.1')
port = config.get('port', 10012)
```

## 4. 依赖管理

### 4.1 requirements.txt

```
# 核心依赖
PyQt5>=5.15.0
numpy>=1.20.0
Pillow>=8.0.0
PyYAML>=5.4.0
imgviz>=1.5.0
natsort>=7.1.0
termcolor>=1.1.0
onnxruntime>=1.9.0
opencv-python>=4.5.0
scikit-image>=0.18.0
loguru>=0.6.0

# 可选依赖
osam>=0.2.0  # AI 辅助标注
```

### 4.2 pyproject.toml

```toml
[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "labelme"
version = "5.2.1"
description = "Polygonal Image Annotation Tool using PyQt5"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "GPL-3.0"}
authors = [
    {name = "WSLabelme Team"}
]
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: GNU General Public License v3",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
]

dependencies = [
    "PyQt5>=5.15.0",
    "numpy>=1.20.0",
    "Pillow>=8.0.0",
    "PyYAML>=5.4.0",
    "imgviz>=1.5.0",
    "natsort>=7.1.0",
    "loguru>=0.6.0",
]

[project.optional-dependencies]
ai = [
    "osam>=0.2.0",
    "onnxruntime>=1.9.0",
]
dev = [
    "pytest>=6.0",
    "black>=21.0",
    "flake8>=3.8",
]

[project.scripts]
labelme = "labelme.__main__:main"
```

## 5. 发布流程

### 5.1 PowerShell 发布脚本

```powershell
# build.ps1
param(
    [string]$Version = "5.2.1",
    [switch]$Release
)

Write-Host "=== WSLabelme 构建脚本 ===" -ForegroundColor Green
Write-Host "版本：$Version"

# 1. 清理旧构建
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue

# 2. 运行测试
Write-Host "运行测试..." -ForegroundColor Yellow
python -m pytest tests/ -v

# 3. 更新版本
Write-Host "更新版本号..." -ForegroundColor Yellow
python update_publish_time.py

# 4. PyInstaller 打包
Write-Host "PyInstaller 打包..." -ForegroundColor Yellow
pyinstaller labelme.spec

# 5. 复制额外文件
Write-Host "复制额外文件..." -ForegroundColor Yellow
Copy-Item README.md dist/Labelme/
Copy-Item LICENSE dist/Labelme/

# 6. 创建发布包
if ($Release) {
    Write-Host "创建发布包..." -ForegroundColor Yellow
    $zipName = "WSLabelme-$Version.zip"
    Compress-Archive -Path dist/Labelme/* -DestinationPath dist/$zipName -Force
    Write-Host "发布包已创建：dist/$zipName" -ForegroundColor Green
}

Write-Host "=== 构建完成 ===" -ForegroundColor Green
```

### 5.2 发布检查清单

- [ ] 运行所有测试
- [ ] 更新版本号
- [ ] 更新发布说明
- [ ] 构建发布包
- [ ] 测试安装包
- [ ] 创建 Git 标签
- [ ] 推送发布

## 6. 技能检查清单

### L1 - 基础
- [ ] 了解 PyInstaller 基本使用
- [ ] 能够运行打包命令
- [ ] 理解版本号规则
- [ ] 了解配置文件位置

### L2 - 熟练
- [ ] 能够配置 spec 文件
- [ ] 能够处理打包依赖问题
- [ ] 能够管理用户配置
- [ ] 能够创建发布包
- [ ] 理解依赖管理

### L3 - 精通
- [ ] 能够优化打包体积
- [ ] 能够处理复杂依赖
- [ ] 能够自动化发布流程
- [ ] 能够解决打包运行问题
- [ ] 能够管理多版本发布

### L4 - 专家
- [ ] 能够设计构建架构
- [ ] 能够优化构建性能
- [ ] 能够制定发布规范
- [ ] 能够管理 CI/CD 流程
- [ ] 能够指导团队发布工作
