# 测试技能 (Testing Skills)

## 1. 单元测试编写

### 1.1 pytest 基础

```python
# tests/test_label_file.py
import pytest
from labelme.label_file import LabelFile

def test_load_label_file(test_json_file):
    """测试加载标注文件"""
    label_file = LabelFile(test_json_file)
    assert label_file.imageData is not None
    assert len(label_file.shapes) > 0

def test_save_label_file(tmp_path):
    """测试保存标注文件"""
    output_file = tmp_path / "test.json"
    shapes = [
        {
            "label": "person",
            "points": [[0, 0], [10, 10]],
            "shape_type": "polygon"
        }
    ]
    LabelFile.save_file(str(output_file), shapes, image_data=None)
    assert output_file.exists()
```

### 1.2 测试夹具 (Fixtures)

```python
# tests/conftest.py
import pytest
import json
from pathlib import Path

@pytest.fixture
def test_json_file(tmp_path):
    """创建测试用的 JSON 标注文件"""
    data = {
        "version": "5.0.0",
        "flags": {},
        "shapes": [
            {
                "label": "person",
                "points": [[100, 100], [200, 200]],
                "shape_type": "polygon"
            }
        ],
        "imagePath": "test.jpg",
        "imageData": None,
        "imageHeight": 480,
        "imageWidth": 640
    }
    file_path = tmp_path / "annotation.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return str(file_path)

@pytest.fixture
def sample_image(tmp_path):
    """创建测试用的示例图像"""
    from PIL import Image
    import numpy as np

    img = Image.fromarray(np.zeros((480, 640, 3), dtype=np.uint8))
    img_path = tmp_path / "test.jpg"
    img.save(img_path)
    return str(img_path)
```

### 1.3 参数化测试

```python
import pytest
from labelme.shape import Shape

@pytest.mark.parametrize("shape_type,points,expected", [
    ("polygon", [[0, 0], [10, 0], [10, 10], [0, 10]], True),
    ("rectangle", [[0, 0], [10, 10]], True),
    ("circle", [[5, 5], [10, 5]], True),
    ("point", [[5, 5]], True),
    ("line", [[0, 0], [10, 10]], True),
])
def test_shape_creation(shape_type, points, expected):
    """测试各种形状的创建"""
    shape = Shape(label="test", shape_type=shape_type)
    for point in points:
        shape.addPoint(point)
    assert len(shape.points) == len(points)
```

### 1.4 Mock 测试

```python
from unittest.mock import Mock, patch
from labelme.tcp_client import TCPClient

def test_tcp_client_connect():
    """测试 TCP 客户端连接（使用 Mock）"""
    mock_socket = Mock()
    mock_socket.connect.return_value = None

    with patch('socket.socket', return_value=mock_socket):
        client = TCPClient(host='127.0.0.1', port=10012)
        client.connect()
        mock_socket.connect.assert_called_once_with(('127.0.0.1', 10012))

def test_tcp_client_send_message():
    """测试 TCP 消息发送（使用 Mock）"""
    mock_socket = Mock()
    mock_socket.send.return_value = 10

    client = TCPClient()
    client.socket = mock_socket
    client.send_message("test")
    mock_socket.send.assert_called_once()
```

## 2. UI 自动化测试

### 2.1 Qt Test 基础

```python
# tests/test_main_window.py
import pytest
from PyQt5 import QtWidgets, QtTest
from main import AIAnnotationMainWindow

@pytest.fixture
def app():
    """创建 QApplication 实例"""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app
    app.quit()

@pytest.fixture
def main_window(app):
    """创建主窗口实例"""
    window = AIAnnotationMainWindow()
    window.show()
    yield window
    window.close()

def test_window_title(main_window):
    """测试窗口标题"""
    assert main_window.windowTitle() == "WSLabelme"

def test_menu_bar_exists(main_window):
    """测试菜单栏存在"""
    menu_bar = main_window.menuBar()
    assert menu_bar is not None
    assert len(menu_bar.actions()) > 0
```

### 2.2 模拟用户交互

```python
def test_open_image_dialog(main_window, qtbot):
    """测试打开图像对话框"""
    # 找到导入按钮
    btn_import = main_window.findChild(QtWidgets.QPushButton, "btn_importImages")
    assert btn_import is not None

    # 模拟点击
    qtbot.mouseClick(btn_import, QtCore.Qt.LeftButton)

    # 验证对话框打开（可能需要等待）
    qtbot.waitUntil(lambda: len(QtWidgets.QApplication.activeModalWidgets()) > 0)

def test_label_list_selection(main_window, qtbot):
    """测试标签列表选择"""
    label_list = main_window.findChild(QtWidgets.QListWidget, "lst_labels")
    assert label_list is not None

    # 添加测试项
    label_list.addItem("person")
    label_list.addItem("car")

    # 选择第一项
    qtbot.mouseClick(label_list.visualItemRect(label_list.item(0)).center(),
                     QtCore.Qt.LeftButton)

    assert label_list.currentRow() == 0
```

### 2.3 截图对比测试

```python
import pytest
from PyQt5 import QtGui, QtTest

def test_thumbnail_display(main_window, tmp_path):
    """测试缩略图显示"""
    # 等待 UI 渲染完成
    QtTest.QTest.qWait(500)

    # 截取缩略图区域
    thumbnail_widget = main_window.findChild(QtWidgets.QWidget, "thumbnailContainer")
    if thumbnail_widget:
        screenshot = thumbnail_widget.grab()
        assert not screenshot.isNull()

        # 保存截图用于人工验证
        screenshot.save(str(tmp_path / "thumbnail.png"))
```

## 3. 功能测试

### 3.1 标注功能测试

```python
# tests/test_annotation.py
import pytest
from labelme.shape import Shape
from labelme.label_file import LabelFile

class TestAnnotation:
    """标注功能测试类"""

    def test_create_polygon(self):
        """测试创建多边形"""
        shape = Shape(label="object", shape_type="polygon")
        shape.addPoint([100, 100])
        shape.addPoint([200, 100])
        shape.addPoint([200, 200])
        shape.addPoint([100, 200])

        assert shape.shape_type == "polygon"
        assert len(shape.points) == 4
        assert shape.closed  # 多边形应自动闭合

    def test_create_rectangle(self):
        """测试创建矩形"""
        shape = Shape(label="box", shape_type="rectangle")
        shape.addPoint([50, 50])
        shape.addPoint([150, 150])

        assert shape.shape_type == "rectangle"
        assert len(shape.points) == 2

    def test_add_flag(self):
        """测试添加标志"""
        shape = Shape(label="test")
        shape.flags["occluded"] = True
        shape.flags["difficult"] = False

        assert shape.flags["occluded"] == True
        assert shape.flags["difficult"] == False
```

### 3.2 文件操作测试

```python
# tests/test_file_operations.py
import pytest
import json
import os
from labelme.label_file import LabelFile

class TestFileOperations:
    """文件操作测试类"""

    def test_load_valid_json(self, test_json_file):
        """测试加载有效的 JSON 文件"""
        label_file = LabelFile(test_json_file)

        assert label_file.imagePath == "test.jpg"
        assert label_file.imageHeight == 480
        assert label_file.imageWidth == 640
        assert len(label_file.shapes) == 1
        assert label_file.shapes[0]["label"] == "person"

    def test_save_and_reload(self, tmp_path):
        """测试保存后重新加载"""
        output_file = tmp_path / "test.json"

        # 保存
        shapes = [
            {"label": "cat", "points": [[0, 0], [50, 50]], "shape_type": "rectangle"}
        ]
        LabelFile.save_file(str(output_file), shapes, image_data=None)

        # 重新加载
        loaded_file = LabelFile(str(output_file))

        assert len(loaded_file.shapes) == 1
        assert loaded_file.shapes[0]["label"] == "cat"

    def test_invalid_json_format(self, tmp_path):
        """测试无效 JSON 格式处理"""
        invalid_file = tmp_path / "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("not valid json {")

        with pytest.raises(Exception):
            LabelFile(str(invalid_file))
```

### 3.3 配置测试

```python
# tests/test_config.py
import pytest
import yaml
from labelme.config import get_config, get_default_config

class TestConfig:
    """配置测试类"""

    def test_default_config_exists(self):
        """测试默认配置存在"""
        config = get_default_config()

        assert config is not None
        assert "auto_save" in config
        assert "labels" in config
        assert "shortcuts" in config

    def test_config_auto_save_default(self):
        """测试自动保存默认值"""
        config = get_default_config()
        assert config["auto_save"] == False

    def test_custom_config_merge(self, tmp_path):
        """测试自定义配置合并"""
        custom_config = tmp_path / "custom.yaml"
        with open(custom_config, 'w') as f:
            yaml.dump({"auto_save": True}, f)

        config = get_config(config_file_or_yaml=str(custom_config))

        assert config["auto_save"] == True
        # 其他默认值应保留
        assert "labels" in config
```

## 4. 回归测试

### 4.1 Bug 复现测试

```python
# tests/test_regression.py
import pytest

class TestRegression:
    """回归测试类"""

    def test_model_info_key_error_fix(self, main_window):
        """测试模型信息 KeyError 修复（Bug #123）"""
        # 确保 update_model_info_display 不会抛出 KeyError
        main_window.model_usage._model_info = {}  # 空模型信息

        # 不应该抛出异常
        try:
            main_window.update_model_info_display()
        except KeyError:
            pytest.fail("KeyError 未修复")

    def test_canvas_paint_sam_none(self, canvas):
        """测试 Canvas paintEvent SAM None 处理（Bug #124）"""
        # 确保 AI 模式下 SAM 为 None 时不会崩溃
        canvas.createMode = "ai_polygon"
        canvas._sam = None

        # 不应该抛出异常
        from PyQt5 import QtGui
        paint_event = QtGui.QPaintEvent(QtGui.QRegion())
        try:
            canvas.paintEvent(paint_event)
        except Exception as e:
            pytest.fail(f"paintEvent 异常：{e}")
```

### 4.2 边界条件测试

```python
class TestBoundaryConditions:
    """边界条件测试类"""

    def test_empty_label_list(self):
        """测试空标签列表"""
        from labelme.widgets.label_list_widget import LabelListWidget

        widget = LabelListWidget()
        assert widget.count() == 0

        # 不应该崩溃
        widget.clear()
        assert widget.count() == 0

    def test_very_long_label_name(self):
        """测试超长标签名"""
        from labelme.shape import Shape

        long_name = "a" * 1000
        shape = Shape(label=long_name)
        assert shape.label == long_name

    def test_zero_size_image(self):
        """测试零尺寸图像处理"""
        from labelme import utils
        import numpy as np

        # 创建零尺寸数组
        zero_img = np.zeros((0, 0, 3), dtype=np.uint8)

        # 应该正确处理或抛出有意义的异常
        try:
            result = utils.img_arr_to_b64(zero_img)
        except Exception as e:
            assert "size" in str(e).lower() or "empty" in str(e).lower()
```

## 5. 性能测试

### 5.1 加载时间测试

```python
# tests/test_performance.py
import pytest
import time
from labelme.label_file import LabelFile

def test_load_large_annotation(benchmark):
    """测试加载大标注文件的性能"""
    # 创建大标注文件
    shapes = [
        {"label": "obj", "points": [[i, i], [i+10, i+10]], "shape_type": "rectangle"}
        for i in range(1000)
    ]

    def load_test_file():
        # 模拟加载
        result = []
        for shape in shapes:
            result.append(Shape(label=shape["label"]))
        return result

    # 使用 pytest-benchmark
    result = benchmark(load_test_file)
    assert len(result) == 1000

# 运行性能测试：pytest tests/test_performance.py --benchmark
```

### 5.2 内存泄漏测试

```python
import pytest
import tracemalloc
from PyQt5 import QtWidgets

def test_no_memory_leak_widget_create(main_window):
    """测试 Widget 创建无内存泄漏"""
    tracemalloc.start()

    # 记录初始内存
    initial, _ = tracemalloc.get_traced_memory()

    # 创建和销毁多个 Widget
    for _ in range(100):
        widget = QtWidgets.QWidget(main_window)
        widget.deleteLater()

    # 处理事件队列
    QtWidgets.QApplication.processEvents()

    # 检查内存增长
    current, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # 允许 10% 的波动
    assert current - initial < initial * 0.1
```

### 5.3 响应时间测试

```python
def test_ui_response_time(main_window):
    """测试 UI 响应时间"""
    import time

    start = time.time()

    # 模拟一系列 UI 操作
    main_window.show()
    QtWidgets.QApplication.processEvents()

    # 切换页面
    if hasattr(main_window, 'stackedWidget_content'):
        main_window.stackedWidget_content.setCurrentIndex(1)
        QtWidgets.QApplication.processEvents()

    elapsed = time.time() - start

    # UI 操作应在 1 秒内完成
    assert elapsed < 1.0
```

## 6. 测试运行与报告

### 6.1 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_label_file.py -v

# 运行特定测试类
pytest tests/test_annotation.py::TestAnnotation -v

# 运行特定测试函数
pytest tests/test_config.py::TestConfig::test_default_config_exists -v

# 生成覆盖率报告
pytest --cov=labelme --cov-report=html

# 生成 JUnit XML 报告
pytest --junitxml=report.xml
```

### 6.2 CI/CD 集成

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: windows-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10']

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-qt pytest-cov pytest-benchmark

    - name: Run tests
      run: |
        xvfb-run pytest tests/ -v --cov=labelme --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

### 6.3 测试检查清单

```python
# tests/__init__.py
"""
测试检查清单

功能测试:
- [ ] 标注文件加载
- [ ] 标注文件保存
- [ ] 形状创建/编辑/删除
- [ ] 图像加载/显示
- [ ] 撤销/重做功能
- [ ] 快捷键功能
- [ ] 配置加载/保存

UI 测试:
- [ ] 窗口显示
- [ ] 菜单栏功能
- [ ] 工具栏功能
- [ ] 对话框交互
- [ ] 状态栏显示
- [ ] 主题切换

性能测试:
- [ ] 大文件加载时间
- [ ] UI 响应时间
- [ ] 内存使用
- [ ] 启动时间

回归测试:
- [ ] 已修复 Bug 不复现
- [ ] 边界条件处理
- [ ] 异常情况处理
"""
```

## 7. 技能检查清单

### L1 - 基础
- [ ] 了解 pytest 基本使用
- [ ] 能够编写简单测试用例
- [ ] 理解测试断言
- [ ] 能够运行测试套件

### L2 - 熟练
- [ ] 能够使用测试夹具
- [ ] 理解参数化测试
- [ ] 能够 Mock 外部依赖
- [ ] 能够测试 UI 组件
- [ ] 理解覆盖率概念

### L3 - 精通
- [ ] 能够设计测试架构
- [ ] 能够编写 UI 自动化测试
- [ ] 能够进行性能测试
- [ ] 能够排查内存泄漏
- [ ] 能够集成 CI/CD

### L4 - 专家
- [ ] 能够制定测试策略
- [ ] 能够优化测试性能
- [ ] 能够设计测试框架
- [ ] 能够指导团队测试
- [ ] 能够平衡测试覆盖率与效率
