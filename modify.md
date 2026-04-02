# 修改记录

本文档记录 Heyfocus Label 项目的所有功能修改和更新内容。文档分为两部分：
- **第一部分：按日期记录** - 按时间顺序记录所有修改（每个功能标注版本号）
- **第二部分：按功能分类** - 按功能模块分类整理修改内容

**当前版本**：0.1.3

**版本号规则**：
- **主版本号（Major）**：不兼容的 API 修改
- **次版本号（Minor）**：向后兼容的功能性新增
- **修订号（Patch）**：向后兼容的问题修正或小改进

---

## 第一部分：按日期记录

### 2026-01-16

#### 功能：关于对话框显示发布时间并支持自动更新

**版本号**：0.1.3

**提交信息**：未提交（本地修改）

**需求背景**：
- 在关于对话框中显示应用的发布时间
- 发布时间应在代码提交时自动更新，无需手动维护
- 发布时间显示在版本号下方，方便用户了解应用版本信息

**实现细节**：

1. **发布时间变量定义**：
   - 在 `labelme/__init__.py` 中新增 `__publish_time__` 变量
   - 与 `__version__` 放在一起，统一管理版本相关信息
   - 格式：`YYYY-MM-DD HH:MM:SS`，如 `2026-01-16 14:30:00`

2. **关于对话框显示**：
   - 修改 `showAbout()` 方法，导入 `__publish_time__`
   - 在版本号下方显示发布时间
   - 使用字符串格式化自动显示时间

3. **自动更新机制**：
   - 创建 `update_publish_time.py` 脚本，用于更新时间
   - 创建 Git pre-commit hook，在每次 commit 前自动运行脚本
   - Hook 会自动将更新后的文件添加到暂存区

**涉及文件**：
- `labelme/__init__.py` - 添加 `__publish_time__` 变量
- `labelme/app.py` - 修改 `showAbout()` 方法显示发布时间
- `update_publish_time.py` - 新增自动更新脚本
- `.git/hooks/pre-commit` - 新增 Git hook

**涉及函数/位置**：
- `MainWindow.showAbout()` - 显示关于对话框（约第 1129 行）

**代码变更示例**：

`labelme/__init__.py`:
```python
__version__ = "0.1.3"

# 发布时间：格式为 YYYY-MM-DD HH:MM:SS
# 此时间会在代码提交时自动更新（通过 Git hook）
__publish_time__ = "2026-01-16 00:00:00"
```

`labelme/app.py`:
```python
def showAbout(self):
    """显示关于窗口"""
    from labelme import __version__, __publish_time__
    about_text = (
        "<h2>Heyfocus Label</h2>"
        "<p><b>版本号:</b> V{}</p>"
        "<p><b>发布时间:</b> {}</p>"  # 新增发布时间显示
        "<p><b>公司:</b> 唯视智能信息科技(广州)有限公司</p>"
        "<p><b>官网:</b> https://www.heyfocustech.com/</p>"
        "<p>图像标注工具</p>"
    ).format(__version__, __publish_time__)
```

**行为变化**：
- 关于对话框中新增"发布时间"条目，显示在版本号下方
- 每次 Git commit 时，发布时间自动更新为当前时间
- 用户可以通过发布时间了解应用的构建/发布时间

**验证步骤**：
1. 运行应用，打开"帮助" -> "关于"
2. 查看是否显示发布时间（在版本号下方）
3. 执行 `git commit`，观察发布时间是否自动更新
4. 或手动运行 `python update_publish_time.py` 测试脚本功能

---

#### 功能：监控目录清空时，自动关闭当前正在显示的图片

**版本号**：0.1.2

**提交信息**：未提交（本地修改）

**需求背景**：
- 当监控的图片目录被清空（目录内不再有任何支持的图片文件）时，界面不应继续显示之前已加载的旧图片
- 需要自动关闭当前显示内容，避免用户看到已不存在的图片

**实现细节**：
- 在 `MainWindow.importDirImages()` 方法中，刷新目录文件列表后增加“空目录兜底”判断
- 判断逻辑：`if self.fileListWidget.count() == 0:`
- 执行操作：
  1. 调用 `self.closeFile()` 关闭当前图片/标注显示
  2. 禁用 `self.actions.openNextImg` 和 `self.actions.openPrevImg` 动作，避免空列表下仍可翻页
  3. 直接 `return`，不再调用 `openNextImg()`

**涉及文件**：
- `labelme/app.py` (第 2472 行附近)

**涉及函数/位置**：
- `MainWindow.importDirImages(self, dirpath, pattern=None, load=True)`

**代码变更示例**：
```python
# 在 importDirImages 方法末尾添加
# If the monitored directory becomes empty, close the currently displayed image.
if self.fileListWidget.count() == 0:
    self.closeFile()
    self.actions.openNextImg.setEnabled(False)
    self.actions.openPrevImg.setEnabled(False)
    return

self.openNextImg(load=load)
```

**行为变化**：
- 目录刷新后若无任何图片条目：
  - 当前画布与图片显示会被清空（通过 `closeFile()`）
  - "上一张/下一张"按钮不可用
- 该逻辑也会在目录监控触发刷新时生效（`_onDirectoryChanged -> _refreshFileList -> importDirImages(load=False)`）

**验证步骤**：
1. 打开某图片目录并正常加载显示一张图片
2. 在外部将该目录内图片删除至空
3. 观察：界面应自动关闭当前图片显示，且无法再点击"上一张/下一张"

---

### 2026-01-13

#### 功能：图片目录动态监控与配置化加载

**版本号**：0.1.0

**提交信息**：`cbcf092` / 2026-01-13 / get images

**需求背景**：
- 应用启动时需要能够自动加载配置文件中指定的默认图片目录
- 需要实时监控图片目录，当有新图片文件添加时自动刷新并加载
- 支持通过配置文件动态修改监控目录，无需重启应用

**实现细节**：

1. **配置文件支持**：
   - 新增 `labelme_config.json` 配置文件
   - 配置项：`default_images_folder` - 指定默认图片目录路径
   - 支持相对路径和绝对路径

2. **文件系统监控**：
   - 使用 `QtCore.QFileSystemWatcher` 实现目录和文件监控
   - 监控配置文件变化：`_onConfigFileChanged()`
   - 监控图片目录变化：`_onDirectoryChanged()`
   - 使用 500ms 延迟避免频繁刷新：`QtCore.QTimer.singleShot(500, ...)`

3. **自动加载机制**：
   - 应用启动时读取配置文件：`_loadDefaultImagesFolder()`
   - 如果配置的目录存在，自动调用 `importDirImages()` 加载图片
   - 位置：`MainWindow.__init__()` 中（第 929-931 行）

4. **目录刷新逻辑**：
   - `_refreshFileList()` 方法实现智能刷新
   - 检测新增文件：通过对比新旧文件列表
   - 自动选择最新文件（按修改时间排序）
   - 自动加载最新文件到界面

**涉及文件**：
- `labelme/app.py` (新增约 229 行代码)
- `labelme_config.json` (新增配置文件)

**涉及函数/位置**：
- `MainWindow._loadDefaultImagesFolder()` - 加载配置文件
- `MainWindow._saveDefaultImagesFolder()` - 保存配置到文件
- `MainWindow._setupFileWatcher()` - 设置文件系统监控
- `MainWindow._onConfigFileChanged()` - 处理配置文件变化
- `MainWindow._onDirectoryChanged()` - 处理目录变化
- `MainWindow._refreshFileList()` - 刷新文件列表并加载最新文件
- `MainWindow.importDirImages()` - 导入目录图片（增强版）

**代码变更统计**：
- `labelme/app.py`: +229 行, -2 行
- `labelme_config.json`: +3 行

**配置文件格式**：
```json
{
  "default_images_folder": "images"
}
```

**行为变化**：
- 应用启动时自动加载配置的图片目录
- 监控目录有新图片时，自动刷新文件列表并加载最新图片
- 修改配置文件后，自动重新加载新的目录
- 打开目录对话框时，自动保存选择的目录为默认目录

**验证步骤**：
1. 创建 `labelme_config.json`，设置 `default_images_folder` 为某个图片目录
2. 启动应用，观察是否自动加载该目录的图片
3. 在监控的目录中添加新图片文件
4. 观察应用是否自动刷新并加载新图片
5. 修改配置文件中的目录路径
6. 观察应用是否自动切换到新目录

---

### 2026-01-09

#### 功能：VSCode F5 调试支持

**版本号**：0.0.2

**提交信息**：`7959716` / 2026-01-09 / 设置F5调试

**需求背景**：
- 需要在 VSCode 中通过 F5 快捷键一键启动和调试应用
- 需要自动检测和配置 Python 环境（特别是 Conda 环境）
- 提供完整的调试配置和辅助脚本

**实现细节**：

1. **VSCode 调试配置**：
   - `.vscode/launch.json` - 调试启动配置
   - `.vscode/settings.json` - VSCode 工作区设置
   - 支持断点调试、变量查看等功能

2. **Python 环境自动检测**：
   - `get_python_path.py` - Python 脚本，检测可用的 Python 解释器
   - `find_conda_python.bat` - Windows 批处理，查找 Conda Python
   - `get_conda_python.bat` - 获取 Conda Python 路径
   - `get_conda_python_path.ps1` - PowerShell 脚本，获取 Conda 路径
   - `find_conda_python.ps1` - PowerShell 脚本，查找 Conda 环境

3. **调试辅助脚本**：
   - `setup_debug.bat` - 设置调试环境
   - `setup_vscode_python.bat` - 配置 VSCode Python 路径
   - `update_vscode_python_path.ps1` - 更新 VSCode Python 路径
   - `run_labelme.bat` - 运行 Labelme 应用
   - `run_labelme.ps1` - PowerShell 运行脚本
   - `check_error_log.bat` - 检查错误日志

4. **文档支持**：
   - `README_DEBUG.md` - 详细的调试说明文档

**涉及文件**：
- `.vscode/conda_python_path.txt` - Conda Python 路径缓存
- `.vscode/find_conda_python.bat` - 查找 Conda Python
- `.vscode/get_conda_python.bat` - 获取 Conda Python
- `.vscode/get_conda_python_path.ps1` - PowerShell 获取 Conda 路径
- `.vscode/get_python_path.py` - Python 路径检测脚本
- `.vscode/launch.json` - 调试配置
- `.vscode/settings.json` - VSCode 设置
- `README_DEBUG.md` - 调试文档
- `check_error_log.bat` - 错误日志检查
- `find_conda_python.ps1` - PowerShell 查找 Conda
- `run_labelme.bat` - 运行脚本
- `run_labelme.ps1` - PowerShell 运行脚本
- `setup_debug.bat` - 调试设置
- `setup_vscode_python.bat` - VSCode Python 设置
- `update_vscode_python_path.ps1` - 更新 Python 路径
- `labelme/__init__.py` - 版本信息（微调）
- `labelme/__main__.py` - 主入口（增强）
- `labelme/app.py` - 应用主文件（微调）
- `labelme/widgets/canvas.py` - 画布组件（增强）

**代码变更统计**：
- 21 个文件变更
- +906 行, -18 行

**使用方法**：
1. 在 VSCode 中打开项目
2. 按 F5 启动调试
3. 或使用 `setup_debug.bat` 配置环境
4. 参考 `README_DEBUG.md` 了解详细说明

**验证步骤**：
1. 在 VSCode 中打开项目
2. 按 F5，观察是否能正常启动应用
3. 设置断点，观察是否能正常断点调试
4. 查看变量值，验证调试功能正常

---

### 2026-01-07

#### 功能：应用基础版本定制（Heyfocus Label）

**版本号**：0.0.1（初始版本）

**提交信息**：`b9efa88` / 2026-01-07 / 修改为heyfocus版本

**需求背景**：
- 将开源 Labelme 项目定制为 Heyfocus Label 版本
- 修改应用名称、图标、关于信息等品牌相关元素
- 保持核心功能不变，仅进行品牌化定制

**实现细节**：

1. **应用名称修改**：
   - `labelme/__init__.py`: `__appname__ = "Heyfocus Label"` (原值: "labelme")

2. **关于窗口定制**：
   - `labelme/app.py`: `showAbout()` 方法
   - 修改标题：`"<h2>Heyfocus Label</h2>"` (原值: "<h2>Labelme</h2>")
   - 添加版本号显示（现从 `__version__` 自动读取，格式：`V{__version__}`）
   - 添加公司信息：`"<p><b>公司:</b> 唯视智能信息科技(广州)有限公司</p>"`
   - 添加官网：`"<p><b>官网:</b> https://www.heyfocustech.com/</p>"`
   - 添加描述：`"<p>图像标注工具</p>"`

3. **图标替换**：
   - `labelme/icons/icon.ico` - 替换为 Heyfocus 图标（从 183KB 压缩到 21KB）
   - `labelme/icons/icon.png` - 替换为 Heyfocus 图标（从 44KB 压缩到 16KB）
   - `labelme/icons/icon_bak.ico` - 备份原图标
   - `labelme/icons/icon_bak.png` - 备份原图标

4. **帮助菜单调整**：
   - 移除教程菜单项
   - 仅保留"关于"菜单项

**涉及文件**：
- `labelme/__init__.py` - 应用名称
- `labelme/app.py` - 关于窗口和菜单
- `labelme/icons/icon.ico` - 应用图标（ICO格式）
- `labelme/icons/icon.png` - 应用图标（PNG格式）
- `labelme/icons/icon_bak.ico` - 原图标备份
- `labelme/icons/icon_bak.png` - 原图标备份

**代码变更统计**：
- 主要变更集中在 `labelme/app.py` 和图标文件
- 图标文件大小优化（压缩）

**行为变化**：
- 应用窗口标题显示 "Heyfocus Label"
- 关于对话框显示定制化的公司信息和版本号
- 应用图标更换为 Heyfocus 品牌图标
- 帮助菜单仅显示"关于"选项

**验证步骤**：
1. 启动应用，观察窗口标题是否为 "Heyfocus Label"
2. 点击"帮助" -> "关于"，查看关于信息是否正确
3. 查看应用图标是否已更换
4. 检查帮助菜单是否仅显示"关于"选项

---

## 第二部分：按功能分类

### 一、目录监控与自动加载功能

#### 1.1 配置文件支持

**实现日期**：2026-01-13

**版本号**：0.1.0

**功能描述**：
- 支持通过 `labelme_config.json` 配置文件指定默认图片目录
- 配置文件支持相对路径和绝对路径
- 应用启动时自动读取并加载配置的目录

**相关函数**：
- `MainWindow._loadDefaultImagesFolder()` - 从配置文件加载默认目录
- `MainWindow._saveDefaultImagesFolder()` - 保存目录到配置文件

**配置文件位置**：项目根目录 `labelme_config.json`

**配置文件格式**：
```json
{
  "default_images_folder": "images"
}
```

#### 1.2 文件系统监控

**实现日期**：2026-01-13

**版本号**：0.1.0

**版本号**：0.1.0

**功能描述**：
- 使用 Qt 的 `QFileSystemWatcher` 监控配置文件和图片目录
- 配置文件变化时自动重新加载配置
- 图片目录变化时自动刷新文件列表并加载最新图片

**相关函数**：
- `MainWindow._setupFileWatcher()` - 初始化文件系统监控
- `MainWindow._onConfigFileChanged()` - 处理配置文件变化
- `MainWindow._onDirectoryChanged()` - 处理目录变化
- `MainWindow._refreshFileList()` - 刷新文件列表

**技术细节**：
- 使用 500ms 延迟避免频繁刷新
- 自动检测新增文件并按修改时间排序
- 自动选择并加载最新文件

#### 1.3 目录清空处理

**实现日期**：2026-01-16

**版本号**：0.1.2

**功能描述**：
- 当监控目录被清空时，自动关闭当前显示的图片
- 禁用翻页功能，避免空列表操作

**相关函数**：
- `MainWindow.importDirImages()` - 在刷新后检查空目录

**技术细节**：
- 检查 `fileListWidget.count() == 0`
- 调用 `closeFile()` 清空显示
- 禁用 `openNextImg` 和 `openPrevImg` 动作

---

### 二、开发调试支持

#### 2.1 VSCode 调试配置

**实现日期**：2026-01-09

**版本号**：0.0.2

**功能描述**：
- 完整的 VSCode 调试配置，支持 F5 一键启动
- 自动检测 Python 环境（包括 Conda）
- 支持断点调试、变量查看等完整调试功能

**相关文件**：
- `.vscode/launch.json` - 调试启动配置
- `.vscode/settings.json` - 工作区设置
- `README_DEBUG.md` - 调试文档

#### 2.2 Python 环境自动检测

**实现日期**：2026-01-09

**版本号**：0.0.2

**功能描述**：
- 自动检测系统中可用的 Python 解释器
- 优先使用 Conda 环境中的 Python
- 支持 Windows 批处理和 PowerShell 脚本

**相关脚本**：
- `get_python_path.py` - Python 路径检测
- `find_conda_python.bat` - 批处理查找 Conda
- `get_conda_python_path.ps1` - PowerShell 获取 Conda 路径

---

### 三、品牌化定制

#### 3.1 应用名称与标识

**实现日期**：2026-01-07

**版本号**：0.0.1

**功能描述**：
- 将应用名称从 "labelme" 改为 "Heyfocus Label"
- 替换应用图标为 Heyfocus 品牌图标
- 优化图标文件大小

**相关文件**：
- `labelme/__init__.py` - 应用名称定义
- `labelme/icons/icon.ico` - ICO 格式图标
- `labelme/icons/icon.png` - PNG 格式图标

#### 3.2 关于信息定制

**实现日期**：2026-01-07（基础定制），2026-01-16（版本号统一、发布时间功能）

**版本号**：0.0.1（基础定制），0.1.1（版本号统一），0.1.3（发布时间功能）

**功能描述**：
- 定制关于对话框，显示公司信息、版本号、发布时间、官网等
- 移除教程菜单，仅保留关于选项
- 版本号和发布时间自动从 `__init__.py` 读取，统一管理

**相关函数**：
- `MainWindow.showAbout()` - 显示关于对话框

**显示内容**：
- 应用名称：Heyfocus Label
- 版本号：V{__version__}（自动从 `__version__` 读取）
- 发布时间：{__publish_time__}（自动从 `__publish_time__` 读取，Git commit 时自动更新）
- 公司：唯视智能信息科技(广州)有限公司
- 官网：https://www.heyfocustech.com/
- 描述：图像标注工具

**自动更新机制**：
- 发布时间通过 Git pre-commit hook 自动更新
- Hook 调用 `update_publish_time.py` 脚本更新时间
- 更新后的文件自动添加到暂存区

---

## 附录：版本号与发布时间管理

### 修改应用版本号

应用版本号在 `labelme/__init__.py` 中定义：

#### 1. 代码中的版本号（`labelme/__init__.py`）

**文件位置**：`labelme/__init__.py`

**修改方法**：
```python
# 第 13 行
__version__ = "0.1.3"  # 修改为你需要的版本号，如 "0.1.4"
```

**说明**：
- 这个版本号遵循语义化版本规范（Semantic Versioning 2.0.0）
- 格式：`主版本号.次版本号.修订号`，如 `1.0.2`
- 这个版本号会在命令行 `--version` 参数时显示
- 关于对话框会自动使用这个版本号（带 "V" 前缀）

#### 2. 关于对话框中的版本号（自动从 `__version__` 读取）

**文件位置**：`labelme/app.py`

**说明**：
- 关于对话框中的版本号现在自动从 `__version__` 读取，无需单独修改
- `showAbout()` 方法中通过 `from labelme import __version__` 导入版本号
- 版本号显示格式：`V{__version__}`，会自动添加 "V" 前缀

**代码实现**：
```python
def showAbout(self):
    """显示关于窗口"""
    from labelme import __version__, __publish_time__
    about_text = (
        "<h2>Heyfocus Label</h2>"
        "<p><b>版本号:</b> V{}</p>"
        "<p><b>发布时间:</b> {}</p>"
        "<p><b>公司:</b> 唯视智能信息科技(广州)有限公司</p>"
        "<p><b>官网:</b> https://www.heyfocustech.com/</p>"
        "<p>图像标注工具</p>"
    ).format(__version__, __publish_time__)
    QtWidgets.QMessageBox.about(self, self.tr("关于"), about_text)
```

**优势**：
- 版本号统一管理，只需修改 `__version__` 一处
- 避免版本号不一致的问题
- 简化版本号维护流程

#### 3. 版本号修改步骤

1. **确定新版本号**：
   - 根据修改内容确定版本号增量
   - 重大功能更新：主版本号 +1（如 0.1.3 -> 1.0.0）
   - 新功能添加：次版本号 +1（如 0.1.3 -> 0.2.0）
   - 问题修复或小改进：修订号 +1（如 0.1.3 -> 0.1.4）

2. **修改版本号（只需修改一处）**：
   - 打开 `labelme/__init__.py`
   - 修改 `__version__` 的值（约第 13 行）
   - 关于对话框会自动使用这个版本号，无需额外修改

3. **发布时间自动更新**：
   - 发布时间 `__publish_time__` 会在 Git commit 时自动更新
   - 通过 Git pre-commit hook 调用 `update_publish_time.py` 脚本
   - 格式：`YYYY-MM-DD HH:MM:SS`，如 `2026-01-16 14:30:00`
   - 如需手动更新，运行：`python update_publish_time.py`

4. **验证修改**：
   - 运行应用，查看"关于"对话框中的版本号（应显示为 `V{__version__}`）
   - 或在命令行运行 `python -m labelme --version` 查看版本号
   - 确保两个地方的版本号一致

### 发布时间管理

#### 1. 发布时间变量（`labelme/__init__.py`）

**文件位置**：`labelme/__init__.py`

**定义**：
```python
# 发布时间：格式为 YYYY-MM-DD HH:MM:SS
# 此时间会在代码提交时自动更新（通过 Git hook）
__publish_time__ = "2026-01-16 00:00:00"
```

**说明**：
- 发布时间显示在关于对话框中，位于版本号下方
- 格式：`YYYY-MM-DD HH:MM:SS`，如 `2026-01-16 14:30:00`
- 此时间会在 Git commit 时自动更新为当前时间

#### 2. 自动更新机制

**实现方式**：
- Git pre-commit hook：在每次 commit 前自动运行 `update_publish_time.py`
- 脚本位置：项目根目录 `update_publish_time.py`
- Hook 位置：`.git/hooks/pre-commit`

**工作原理**：
1. 开发者执行 `git commit` 命令
2. Git 触发 pre-commit hook
3. Hook 运行 `update_publish_time.py` 脚本
4. 脚本读取当前时间并更新 `__init__.py` 中的 `__publish_time__`
5. 将更新后的文件添加到暂存区
6. 继续执行 commit 操作

**手动更新**：
如果 Git hook 未生效或需要手动更新时间，可以运行：
```bash
python update_publish_time.py
```

**注意事项**：
- 确保 `update_publish_time.py` 脚本有执行权限
- 确保 Git hook 文件 `.git/hooks/pre-commit` 有执行权限
- 在 Windows 系统上，可能需要使用 Git Bash 或配置 PowerShell 执行策略

#### 3. 版本号规范建议

- **主版本号（Major）**：不兼容的 API 修改
- **次版本号（Minor）**：向后兼容的功能性新增
- **修订号（Patch）**：向后兼容的问题修正

**示例**：
- `0.0.1` - 初始版本（Heyfocus Label 品牌化定制）
- `0.0.2` - 开发工具支持（VSCode 调试）
- `0.1.0` - 新功能添加（目录监控）
- `0.1.1` - 小改进（版本号统一管理）
- `0.1.2` - 问题修复（目录清空处理）
- `0.1.3` - 小功能添加（发布时间显示）
- `1.0.0` - 正式发布版本
- `2.0.0` - 重大更新，可能不兼容

---

## 更新日志

| 日期 | 版本 | 主要更新 |
|------|------|----------|
| 2026-01-16 | 0.1.3 | 关于对话框显示发布时间并支持自动更新 |
| 2026-01-16 | 0.1.2 | 目录清空时自动关闭当前图片 |
| 2026-01-16 | 0.1.1 | 关于对话框版本号改为从 `__version__` 读取 |
| 2026-01-13 | 0.1.0 | 图片目录动态监控与配置化加载 |
| 2026-01-09 | 0.0.2 | VSCode F5 调试支持 |
| 2026-01-07 | 0.0.1 | 应用品牌化定制（Heyfocus Label）- 初始版本 |

---

**文档维护说明**：
- 每次功能修改后，请及时更新本文档
- 按日期记录修改时，最新的修改放在最前面
- 按功能分类时，相关功能归类在一起
- 版本号修改时，同步更新"更新日志"表格
