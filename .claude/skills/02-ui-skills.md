# UI/界面开发技能 (UI Development Skills)

## 1. Qt Designer UI 文件使用

### 1.1 UI 文件加载

```python
from PyQt5 import uic

# 在 QMainWindow 中加载 UI 文件
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('mainform.ui', self)
        # 现在可以直接访问 UI 中定义的组件
        # 如 self.btn_imageAnnotation
```

### 1.2 组件命名规范

| 前缀 | 组件类型 | 示例 |
|------|----------|------|
| btn | QPushButton | btn_importImages |
| lbl | QLabel | lbl_status |
| edt | QLineEdit | edt_search |
| txt | QTextEdit | txt_log |
| lst | QListWidget | lst_labels |
| tbl | QTableWidget | tbl_training |
| cmb | QComboBox | cmb_model |
| chk | QCheckBox | chk_autoSave |
| grp | QGroupBox | grp_parameters |
| tab | QTabWidget | tab_main |
| stk | QStackedWidget | stk_pages |
| spb | QSpinBox | spb_threshold |

### 1.3 页面切换

```python
# QStackedWidget 页面切换
self.stackedWidget_content.setCurrentIndex(0)  # 图像标注页面
self.stackedWidget_content.setCurrentIndex(1)  # 模型训练页面
self.stackedWidget_content.setCurrentIndex(2)  # 模型使用页面
self.stackedWidget_content.setCurrentIndex(3)  # 系统设置页面
```

## 2. 自定义 Widget 开发

### 2.1 继承 Qt 组件

```python
class ThumbnailItem(QtWidgets.QFrame):
    """自定义缩略图项"""

    clicked = QtCore.pyqtSignal(str)  # 自定义信号

    def __init__(self, file_path, index, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        # ... 组件设置

    def mousePressEvent(self, event):
        """重写鼠标事件"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.file_path)
        super().mousePressEvent(event)
```

### 2.2 自定义 Dock Widget

```python
class TrainingDockWidget(QtWidgets.QWidget):
    """训练配置面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout()

        # 可折叠分组
        self.basic_group = CollapsibleGroupBox("基本信息")
        self.param_group = CollapsibleGroupBox("参数")
        self.sample_group = CollapsibleGroupBox("训练样本")

        # 添加到布局
        main_layout.addWidget(self.basic_group)
        main_layout.addWidget(self.param_group)
        main_layout.addWidget(self.sample_group)

        self.setLayout(main_layout)
```

### 2.3 自定义 ToolBar

```python
class ToolBar(QtWidgets.QToolBar):
    """自定义工具栏"""

    def __init__(self, title):
        super().__init__(title)
        layout = self.layout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

    def addAction(self, action):
        """重写 addAction，添加自定义按钮样式"""
        if isinstance(action, QtWidgets.QWidgetAction):
            return super().addAction(action)

        btn = QtWidgets.QToolButton()
        btn.setDefaultAction(action)
        btn.setToolButtonStyle(self.toolButtonStyle())
        self.addWidget(btn)
```

## 3. 样式与主题

### 3.1 内联样式

```python
# 设置按钮样式
self.btn_importImages.setStyleSheet("""
    QPushButton {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #45a049;
    }
    QPushButton:pressed {
        background-color: #3d8b40;
    }
    QPushButton:disabled {
        background-color: #cccccc;
    }
""")
```

### 3.2 全局样式表

```python
# 在 QApplication 中设置全局样式
app.setStyleSheet("""
    QMainWindow {
        background-color: #f5f5f5;
    }
    QDockWidget {
        font-size: 12px;
    }
    QDockWidget::title {
        background-color: #D4605A;
        color: white;
        padding: 4px;
    }
    QMenuBar {
        background-color: white;
    }
    QMenu::item:selected {
        background-color: #e0e0e0;
    }
""")
```

### 3.3 主题切换

```python
def set_dark_theme(self):
    """设置暗色主题"""
    self.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QDockWidget {
            background-color: #3c3f41;
        }
        QDockWidget::title {
            background-color: #D4605A;
        }
    """)

def set_light_theme(self):
    """设置亮色主题"""
    self.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
            color: #000000;
        }
    """)
```

## 4. 响应式布局

### 4.1 布局管理器

```python
# 垂直布局
layout = QtWidgets.QVBoxLayout()
layout.addWidget(widget1)
layout.addWidget(widget2)
layout.addStretch()  # 添加弹性空间

# 水平布局
layout = QtWidgets.QHBoxLayout()
layout.addWidget(widget1)
layout.addWidget(widget2)

# 网格布局
layout = QtWidgets.QGridLayout()
layout.addWidget(widget1, 0, 0)  # 行 0, 列 0
layout.addWidget(widget2, 1, 0)

# 表单布局
layout = QtWidgets.QFormLayout()
layout.addRow("标签：", combo_box)
layout.addRow("批次：", spin_box)
```

### 4.2 尺寸策略

```python
# 设置组件尺寸策略
widget.setSizePolicy(
    QtWidgets.QSizePolicy.Expanding,  # 水平策略
    QtWidgets.QSizePolicy.Fixed       # 垂直策略
)

# 设置最小/最大尺寸
widget.setMinimumSize(200, 100)
widget.setMaximumSize(800, 600)

# 设置固定尺寸
widget.setFixedSize(100, 50)
```

### 4.3 响应式调整

```python
def resizeEvent(self, event):
    """窗口大小改变事件"""
    super().resizeEvent(event)
    # 根据窗口大小调整组件
    if self.width() < 800:
        # 窄窗口模式：隐藏某些组件
        self.sidebar_widget.hide()
    else:
        self.sidebar_widget.show()
```

## 5. 图标与资源管理

### 5.1 图标使用

```python
from labelme import utils

# 使用预定义图标
icon = utils.newIcon('icon_name')

# 设置到按钮
button.setIcon(icon)

# 设置窗口图标
self.setWindowIcon(utils.newIcon('logo'))
```

### 5.2 图标资源

```python
# 在资源文件中定义图标
# resources.qrc
<RCC>
  <qresource prefix="icons">
    <file>icons/save.png</file>
    <file>icons/open.png</file>
    <file>icons/edit.png</file>
  </qresource>
</RCC>

# 编译资源文件
pyrcc5 resources.qrc -o resources_rc.py
```

### 5.3 可用图标列表

| 图标名 | 用途 |
|--------|------|
| icon | 应用图标 |
| save | 保存 |
| open | 打开 |
| edit | 编辑 |
| delete | 删除 |
| undo | 撤销 |
| redo | 重做 |
| copy | 复制 |
| paste | 粘贴 |
| zoom-in | 放大 |
| zoom-out | 缩小 |
| eye | 显示/隐藏 |
| help | 帮助 |

## 6. 常见 UI 模式

### 6.1 单例对话框

```python
class SettingsDialog(QtWidgets.QDialog):
    _instance = None

    @classmethod
    def instance(cls, parent):
        if cls._instance is None:
            cls._instance = cls(parent)
        return cls._instance
```

### 6.2 进度对话框

```python
from PyQt5.QtWidgets import QProgressDialog

def show_progress(self, max_value, title="进度"):
    progress = QProgressDialog(title, "取消", 0, max_value, self)
    progress.setWindowModality(Qt.WindowModal)
    progress.show()
    return progress
```

### 6.3 消息框

```python
# 信息框
QtWidgets.QMessageBox.information(
    self, "提示", "操作成功完成"
)

# 警告框
QtWidgets.QMessageBox.warning(
    self, "警告", "某些数据可能丢失"
)

# 错误框
QtWidgets.QMessageBox.critical(
    self, "错误", "操作失败：" + error_message
)

# 确认框
reply = QtWidgets.QMessageBox.question(
    self, "确认",
    "确定要删除吗？",
    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
)
if reply == QtWidgets.QMessageBox.Yes:
    # 执行删除
    pass
```

## 7. 技能检查清单

### L1 - 基础
- [ ] 了解 Qt Designer 基本使用
- [ ] 能够修改 UI 文本
- [ ] 理解基本布局管理器
- [ ] 能够添加简单按钮

### L2 - 熟练
- [ ] 能够加载和修改 UI 文件
- [ ] 理解信号槽连接
- [ ] 能够设置组件样式
- [ ] 能够创建自定义对话框
- [ ] 理解尺寸策略

### L3 - 精通
- [ ] 能够开发复杂自定义 Widget
- [ ] 理解 Qt 绘图系统
- [ ] 能够优化 UI 性能
- [ ] 能够处理 UI 线程问题
- [ ] 能够实现响应式布局

### L4 - 专家
- [ ] 能够设计 UI 架构
- [ ] 能够制定 UI 规范
- [ ] 能够优化渲染性能
- [ ] 能够解决复杂 UI 问题
- [ ] 能够指导团队 UI 开发
