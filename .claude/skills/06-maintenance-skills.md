# 维护与优化技能 (Maintenance & Optimization Skills)

## 1. 代码重构

### 1.1 代码异味识别

```python
# 异味 1: 过长的函数
# ❌ 重构前
def load_and_process_image(filename):
    # 100 行代码...
    # 加载文件
    # 解析 JSON
    # 加载图像
    # 处理数据
    # 更新 UI
    # 保存状态
    pass

# ✅ 重构后
def load_and_process_image(filename):
    """加载并处理图像"""
    try:
        image_data = load_image_file(filename)
        annotation_data = parse_annotation(filename)
        image = process_image_data(image_data, annotation_data)
        update_ui(image, annotation_data)
        save_state(filename, annotation_data)
        return True
    except Exception as e:
        logger.error(f"加载图像失败：{e}")
        return False

def load_image_file(filename):
    """加载图像文件"""
    ...

def parse_annotation(filename):
    """解析标注数据"""
    ...

def process_image_data(image_data, annotation_data):
    """处理图像数据"""
    ...

def update_ui(image, annotation_data):
    """更新 UI 显示"""
    ...

def save_state(filename, annotation_data):
    """保存状态"""
    ...
```

```python
# 异味 2: 重复代码
# ❌ 重构前
def save_image():
    if not current_image:
        return False
    filename = get_save_filename()
    if not filename:
        return False
    # 保存逻辑...
    return True

def save_annotation():
    if not current_annotation:
        return False
    filename = get_save_filename()
    if not filename:
        return False
    # 保存逻辑...
    return True

# ✅ 重构后
def save_current_data(data, data_type):
    """通用保存函数"""
    if not data:
        logger.warning(f"没有要保存的{data_type}")
        return False

    filename = get_save_filename()
    if not filename:
        return False

    return do_save(filename, data, data_type)
```

```python
# 异味 3: 过深的嵌套
# ❌ 重构前
def process_shape(shape):
    if shape is not None:
        if shape.shape_type == "polygon":
            if len(shape.points) >= 3:
                if shape.label is not None:
                    if validate_label(shape.label):
                        return create_polygon(shape)
                    else:
                        return None
                else:
                    return None
            else:
                return None
        else:
            return None
    else:
        return None

# ✅ 重构后
def process_shape(shape):
    if shape is None:
        return None
    if shape.shape_type != "polygon":
        return None
    if len(shape.points) < 3:
        return None
    if shape.label is None:
        return None
    if not validate_label(shape.label):
        return None

    return create_polygon(shape)

# 或使用提前返回
def process_shape(shape):
    if not shape or shape.shape_type != "polygon":
        return None
    if len(shape.points) < 3:
        return None
    if not shape.label or not validate_label(shape.label):
        return None
    return create_polygon(shape)
```

### 1.2 SOLID 原则应用

```python
# 单一职责原则 (SRP)
# ❌ 重构前 - 一个类做太多事
class ImageManager:
    def load_image(self, path): ...
    def save_image(self, path): ...
    def display_image(self): ...
    def export_image(self, path): ...
    def print_image(self): ...
    def upload_image(self, url): ...

# ✅ 重构后 - 职责分离
class ImageLoader:
    def load(self, path): ...
    def save(self, path, data): ...

class ImageViewer:
    def display(self, image): ...

class ImageExporter:
    def export(self, image, path): ...
    def print(self, image): ...
    def upload(self, image, url): ...
```

```python
# 开闭原则 (OCP) - 对扩展开放，对修改关闭
# ❌ 重构前
class ShapeDrawer:
    def draw(self, shape_type):
        if shape_type == "polygon":
            self._draw_polygon()
        elif shape_type == "rectangle":
            self._draw_rectangle()
        elif shape_type == "circle":
            self._draw_circle()
        # 每添加新形状都要修改这里

# ✅ 重构后
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def draw(self, painter):
        pass

class Polygon(Shape):
    def draw(self, painter):
        # 绘制多边形逻辑
        pass

class Rectangle(Shape):
    def draw(self, painter):
        # 绘制矩形逻辑
        pass

class ShapeDrawer:
    def draw(self, shape: Shape):
        shape.draw(self.painter)
    # 添加新形状只需创建新类，无需修改 ShapeDrawer
```

```python
# 依赖倒置原则 (DIP)
# ❌ 重构前 - 依赖具体实现
class LabelDialog:
    def __init__(self):
        self.label_list = QListWidget()  # 强耦合具体类

# ✅ 重构后 - 依赖抽象
class LabelProvider(ABC):
    @abstractmethod
    def get_labels(self):
        pass

class LabelDialog:
    def __init__(self, provider: LabelProvider):
        self.provider = provider

    def setup(self):
        labels = self.provider.get_labels()
        # 使用 labels
```

### 1.3 重构工具

```bash
# 使用 rope 进行重构
pip install rope

# 重命名
rope-rename -f labelme/app.py -n MainWindow LabelmeMainWindow

# 提取方法
rope-extract-method -f labelme/app.py -r 100-150 new_method_name

# 使用 black 格式化代码
black labelme/

# 使用 isort 排序导入
isort labelme/

# 使用 pyupgrade 升级语法
pyupgrade --py38-plus labelme/
```

### 1.4 重构检查清单

- [ ] 函数长度是否超过 50 行
- [ ] 类是否承担过多职责
- [ ] 是否存在重复代码
- [ ] 命名是否清晰表达意图
- [ ] 是否有过度复杂的条件
- [ ] 是否遵循单一职责原则
- [ ] 是否对扩展开放
- [ ] 是否依赖抽象而非具体实现

## 2. 性能优化

### 2.1 图像加载优化

```python
# ❌ 重构前 - 每次加载完整图像
def load_image(self, path):
    image = QImage(path)
    self.pixmap = QPixmap.fromImage(image)
    self.update()

# ✅ 重构后 - 使用缩略图缓存
from functools import lru_cache

class ImageLoader:
    def __init__(self, max_cache_size=10):
        self.max_cache_size = max_cache_size

    @lru_cache(maxsize=100)
    def load_thumbnail(self, path, size=(256, 256)):
        """加载缩略图并缓存"""
        image = QImage(path)
        return image.scaled(*size, Qt.KeepAspectRatio)

    def load_full_image(self, path):
        """仅在需要时加载完整图像"""
        # 延迟加载
        pass
```

### 2.2 大量数据渲染优化

```python
# ❌ 重构前 - 逐个添加 items
def populate_label_list(self, labels):
    for label in labels:
        item = QtWidgets.QListWidgetItem(label)
        self.label_list.addItem(item)
        # 每次 addItem 都会触发 UI 更新

# ✅ 重构后 - 批量添加
def populate_label_list(self, labels):
    self.label_list.setUpdatesEnabled(False)  # 禁用更新
    self.label_list.blockSignals(True)         # 阻止信号

    items = [QtWidgets.QListWidgetItem(label) for label in labels]
    for item in items:
        self.label_list.addItem(item)

    self.label_list.blockSignals(False)
    self.label_list.setUpdatesEnabled(True)
    self.label_list.viewport().update()
```

### 2.3 异步加载优化

```python
from PyQt5.QtCore import QThread, pyqtSignal

# ❌ 重构前 - 阻塞主线程
def load_large_dataset(self):
    data = []
    for file in self.files:  # 可能几千个文件
        data.append(self.load_file(file))
    self.update_ui(data)  # UI 卡死直到完成

# ✅ 重构后 - 后台线程加载
class DatasetLoader(QThread):
    progress = pyqtSignal(int, str)  # 进度信号
    finished = pyqtSignal(list)       # 完成信号
    error = pyqtSignal(str)           # 错误信号

    def __init__(self, files):
        super().__init__()
        self.files = files

    def run(self):
        try:
            data = []
            for i, file in enumerate(self.files):
                data.append(self.load_file(file))
                self.progress.emit(i + 1, file)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

# 使用
loader = DatasetLoader(files)
loader.progress.connect(self.update_progress)
loader.finished.connect(self.on_load_complete)
loader.error.connect(self.on_load_error)
loader.start()  # 不阻塞 UI
```

### 2.4 内存优化

```python
# ❌ 重构前 - 持有所有图像数据
class ImageManager:
    def __init__(self):
        self.all_images = {}  # 可能占用大量内存

    def load_all(self, paths):
        for path in paths:
            self.all_images[path] = QImage(path)

# ✅ 重构后 - 使用 LRU 缓存
from collections import OrderedDict

class ImageManager:
    def __init__(self, max_cached=20):
        self.max_cached = max_cached
        self.cache = OrderedDict()

    def get_image(self, path):
        if path in self.cache:
            # 移到最近使用
            self.cache.move_to_end(path)
            return self.cache[path]

        # 加载新图像
        image = QImage(path)

        # 超出缓存限制，移除最旧的
        if len(self.cache) >= self.max_cached:
            self.cache.popitem(last=False)

        self.cache[path] = image
        return image

    def clear_cache(self):
        self.cache.clear()
```

### 2.5 性能分析工具

```python
# 使用 cProfile 分析
import cProfile
import pstats
from pstats import SortKey

def profile_function(func, *args):
    profiler = cProfile.Profile()
    profiler.enable()

    result = func(*args)

    profiler.disable()

    stats = pstats.Stats(profiler)
    stats.sort_stats(SortKey.CUMULATIVE)
    stats.print_stats(20)  # 打印前 20 个最耗时的函数

    return result

# 使用 memory_profiler
from memory_profiler import profile

@profile
def memory_intensive_function():
    data = []
    for i in range(10000):
        data.append([0] * 1000)
    return data

# 运行：python -m memory_profiler script.py
```

## 3. 安全问题处理

### 3.1 输入验证

```python
# ❌ 重构前 - 未验证输入
def load_annotation_file(self, filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    # 直接使用 data，可能存在恶意数据

# ✅ 重构后 - 验证输入
import re

def load_annotation_file(self, filename):
    # 验证文件路径
    if not self.is_safe_path(filename):
        raise SecurityError("Invalid file path")

    # 验证文件扩展名
    if not filename.endswith('.json'):
        raise SecurityError("Invalid file type")

    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 验证 JSON 结构
    self.validate_annotation_structure(data)

    return data

def is_safe_path(self, path):
    """防止路径遍历攻击"""
    # 规范化路径
    normalized = os.path.normpath(path)
    # 检查是否包含..
    if '..' in normalized:
        return False
    # 检查是否在允许目录内
    allowed_dirs = [self.workspace_dir]
    for allowed in allowed_dirs:
        if normalized.startswith(os.path.normpath(allowed)):
            return True
    return False

def validate_annotation_structure(self, data):
    """验证标注数据结构"""
    required_keys = ['version', 'shapes', 'imagePath']
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Missing required key: {key}")

    # 验证 shapes
    if not isinstance(data['shapes'], list):
        raise ValueError("shapes must be a list")

    for shape in data['shapes']:
        if not isinstance(shape.get('label'), str):
            raise ValueError("shape label must be string")
        # 验证标签长度
        if len(shape['label']) > 255:
            raise ValueError("label too long")
```

### 3.2 命令注入防护

```python
import subprocess

# ❌ 重构前 - 命令注入风险
def run_external_tool(tool_name, user_input):
    # 危险！用户输入直接拼接到命令
    os.system(f"{tool_name} --input {user_input}")
    subprocess.call(f"{tool_name} {user_input}", shell=True)

# ✅ 重构后 - 安全执行
def run_external_tool(tool_name, user_input):
    # 验证输入
    if not self.validate_input(user_input):
        raise SecurityError("Invalid input")

    # 不使用 shell，传递参数列表
    cmd = [tool_name, "--input", user_input]

    # 限制超时
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30,  # 30 秒超时
            check=True
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        logger.error("命令执行超时")
        raise

def validate_input(self, user_input):
    """验证用户输入"""
    # 只允许字母、数字、下划线、点、斜杠
    if not re.match(r'^[\w./-]+$', user_input):
        return False
    # 防止路径遍历
    if '..' in user_input:
        return False
    return True
```

### 3.3 敏感信息处理

```python
# ❌ 重构前 - 硬编码密钥
class TCPClient:
    def __init__(self):
        self.password = "admin123"  # 硬编码密码
        self.api_key = "sk-xxx"     # 硬编码 API 密钥

# ✅ 重构后 - 从环境变量或配置文件读取
import os
from pathlib import Path

class TCPClient:
    def __init__(self):
        self.password = os.getenv('LABELME_PASSWORD')
        self.api_key = self.load_secure_config('api_key')

    def load_secure_config(self, key):
        """从安全配置加载"""
        config_path = Path.home() / '.labelme' / 'secure_config.yaml'
        if config_path.exists():
            # 应该加密存储
            import yaml
            with open(config_path) as f:
                config = yaml.safe_load(f)
                return config.get(key)
        return None
```

### 3.4 安全扫描工具

```bash
# 使用 bandit 扫描安全漏洞
pip install bandit
bandit -r labelme/

# 使用 safety 检查依赖漏洞
pip install safety
safety check

# 使用 pip-audit
pip install pip-audit
pip-audit
```

## 4. 文档维护

### 4.1 代码文档规范

```python
"""模块级文档字符串"""
from typing import Optional, List, Dict

class LabelDialog(QtWidgets.QDialog):
    """
    标签编辑对话框

    用于创建、编辑和选择图像标注标签。

    Attributes:
        label_list (QListWidget): 预定义标签列表
        edit (QLineEdit): 标签输入框
        text (str): 当前选中的标签文本

    Example:
        >>> dialog = LabelDialog(parent=mainwindow)
        >>> if dialog.exec_():
        ...     print(f"Selected: {dialog.text}")
    """

    def __init__(self, parent=None, labels=None):
        """
        初始化标签对话框

        Args:
            parent (QtWidgets.QWidget): 父窗口
            labels (List[str], optional): 预定义标签列表

        Raises:
            ValueError: 当 labels 包含空字符串时
        """
        super().__init__(parent)
        if labels and any(not l for l in labels):
            raise ValueError("Labels cannot contain empty strings")

    def get_text(self) -> Optional[str]:
        """
        获取当前选中的标签文本

        Returns:
            Optional[str]: 选中的标签，如果未选择则返回 None
        """
        return self._text
```

### 4.2 API 文档生成

```bash
# 使用 Sphinx 生成文档
pip install sphinx sphinx-rtd-theme
sphinx-quickstart docs/

# 配置 docs/conf.py
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

# 生成文档
sphinx-build -b html docs/ docs/_build/

# 使用 pydoc-markdown
pip install pydoc-markdown
pydoc-markdown
```

### 4.3 CHANGELOG 维护

```markdown
# Changelog

## [5.2.2] - 2026-03-23

### 修复
- 修复模型信息显示时可能的 KeyError (#123)
- 修复 canvas.py 中 AI 模型处理的异常捕获 (#124)
- 修复配置文件加载时缺少异常处理的问题
- 修复 label_dialog.py 中 completer 空值问题

### 优化
- 改进异常处理，避免应用闪退
- 增强日志输出，便于问题排查
- 创建完整的 skills 技能体系文档

### 新增
- 添加测试技能文档 (05-test-skills.md)
- 添加维护优化技能文档 (06-maintenance-skills.md)

## [5.2.1] - 2026-03-20

### 修复
- 修复保存标注时 image_data 为 None 的问题
- 修复高 DPI 屏幕下图标显示模糊

### 优化
- 优化大文件加载性能
- 优化缩略图缓存机制
```

### 4.4 README 维护

```markdown
# WSLabelme

AI 图像标注与训练系统，基于 Labelme 重构。

## 功能特性

- ✅ 多边形、矩形、圆形、线条、点标注
- ✅ AI 辅助标注（SAM 模型）
- ✅ 模型训练与管理
- ✅ 智能缩略图浏览
- ✅ 训练配置面板
- ✅ 模型使用界面

## 快速开始

### 安装

```bash
pip install -r requirements.txt
python main.py
```

### 打包

```bash
pyinstaller labelme.spec
```

## 开发

### 运行测试

```bash
pytest tests/ -v
```

### 代码风格

```bash
black labelme/
isort labelme/
flake8 labelme/
```

## 贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request
```

## 5. 问题追踪

### 5.1 日志分析

```python
from loguru import logger
import re

# 分析日志文件
def analyze_log_file(log_path):
    """分析日志文件，识别常见问题"""
    error_counts = {}
    warning_counts = {}

    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if 'ERROR' in line:
                # 提取错误信息
                match = re.search(r'ERROR\s+(.+)', line)
                if match:
                    error = match.group(1).strip()
                    error_counts[error] = error_counts.get(error, 0) + 1

            if 'WARNING' in line:
                match = re.search(r'WARNING\s+(.+)', line)
                if match:
                    warning = match.group(1).strip()
                    warning_counts[warning] = warning_counts.get(warning, 0) + 1

    # 输出统计
    print("=== Top Errors ===")
    for error, count in sorted(error_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"{count}x: {error}")

    print("\n=== Top Warnings ===")
    for warning, count in sorted(warning_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"{count}x: {warning}")
```

### 5.2 问题追踪模板

```markdown
## Bug 报告模板

### 问题描述
简要描述问题...

### 复现步骤
1. 打开应用
2. 点击 '...'
3. 选择 '...'
4. 看到错误

### 期望行为
应该发生什么...

### 实际行为
实际发生了什么...

### 环境信息
- OS: Windows 10
- Python: 3.9
- WSLabelme: 5.2.1

### 日志
```
[时间] [级别] 错误信息
...
```

### 截图
如有必要，添加截图...
```

### 5.3 问题分类

```python
ISSUE_LABELS = {
    'bug': '确认的缺陷',
    'enhancement': '功能增强',
    'feature': '新功能请求',
    'documentation': '文档改进',
    'performance': '性能问题',
    'security': '安全问题',
    'question': '问题咨询',
    'wontfix': '不会修复',
    'duplicate': '重复问题',
    'invalid': '无效问题',
}

ISSUE_PRIORITIES = {
    'critical': '严重 - 应用崩溃、数据丢失',
    'high': '高 - 主要功能不可用',
    'medium': '中 - 部分功能受影响',
    'low': '低 - 小问题或不影响使用',
}
```

## 6. 持续集成

### 6.1 GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Install lint tools
      run: |
        pip install black flake8 isort mypy

    - name: Run black
      run: black --check labelme/

    - name: Run flake8
      run: flake8 labelme/ --count --select=E9,F63,F7,F82 --show-source

    - name: Run isort
      run: isort --check-only labelme/

  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [windows-latest, ubuntu-latest]
        python-version: ['3.8', '3.9', '3.10']

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-qt pytest-cov

    - name: Run tests
      run: pytest tests/ -v --cov=labelme --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2

  build:
    needs: [lint, test]
    runs-on: windows-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pyinstaller

    - name: Build executable
      run: pyinstaller labelme.spec

    - name: Upload artifact
      uses: actions/upload-artifact@v2
      with:
        name: WSLabelme
        path: dist/Labelme/
```

### 6.2 发布自动化

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  release:
    runs-on: windows-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pyinstaller

    - name: Build
      run: pyinstaller labelme.spec

    - name: Create Release
      uses: softprops/action-gh-release@v1
      with:
        files: dist/WSLabelme-*.zip
        body_path: CHANGELOG.md
        draft: false
        prerelease: false
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## 7. 技能检查清单

### L1 - 基础
- [ ] 理解代码异味基本概念
- [ ] 能够识别简单重复代码
- [ ] 了解基本重构技巧
- [ ] 能够编写基础文档

### L2 - 熟练
- [ ] 能够进行函数提取重构
- [ ] 理解 SOLID 原则
- [ ] 能够使用性能分析工具
- [ ] 能够处理常见安全问题
- [ ] 能够维护 CHANGELOG

### L3 - 精通
- [ ] 能够进行大规模重构
- [ ] 能够优化复杂性能问题
- [ ] 能够设计安全架构
- [ ] 能够建立文档体系
- [ ] 能够设计 CI/CD 流程

### L4 - 专家
- [ ] 能够制定维护策略
- [ ] 能够优化系统架构
- [ ] 能够建立安全规范
- [ ] 能够指导团队重构
- [ ] 能够设计自动化流程
