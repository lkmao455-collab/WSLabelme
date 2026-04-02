# 调试与异常处理技能 (Debugging & Exception Handling Skills)

## 1. 日志系统使用 (loguru)

### 1.1 日志级别

```python
from loguru import logger

logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
logger.exception("异常信息（带堆栈）")
```

### 1.2 异常捕获日志

```python
# 使用装饰器捕获异常
@logger.catch
def risky_function():
    result = 1 / 0
    return result

# 使用上下文管理器
with logger.catch("操作失败", reraise=True):
    do_something()

# 在 main 中设置全局异常钩子
def exception_hook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.exception("未处理的异常", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = exception_hook
```

### 1.3 日志配置

```python
from loguru import logger
import sys

# 移除默认处理器
logger.remove(handler_id=0)

# 添加控制台输出
logger.add(sys.stderr, level="DEBUG")

# 添加文件输出（带轮转）
logger.add(
    "logs/app.log",
    rotation="10 MB",      # 文件大小达到 10MB 时轮转
    retention="30 days",   # 保留 30 天
    compression="gz",      # 压缩旧日志
    level="DEBUG",
    backtrace=True,        # 显示完整堆栈
    diagnose=True,         # 显示局部变量
    enqueue=True,          # 线程安全
)
```

## 2. 常见异常类型及处理

### 2.1 PyQt5 相关异常

```python
# RuntimeError: Wrapped C/C++ object has been deleted
# 原因：访问已删除的 Qt 对象
try:
    if hasattr(self, 'widget') and self.widget is not None:
        self.widget.setText("new text")
except RuntimeError as e:
    logger.error(f"访问已删除对象：{e}")
    self.widget = None

# 解决方案：使用 sip 检查对象有效性
import sip
if not sip.isdeleted(self.widget):
    self.widget.setText("new text")
```

```python
# AttributeError: 'NoneType' object has no attribute
# 原因：对象未初始化或已被删除
# 解决方案：添加空值检查
if hasattr(self, 'labelme_window') and self.labelme_window is not None:
    self.labelme_window.some_method()
```

### 2.2 文件操作异常

```python
import os.path as osp

# 文件加载异常处理
try:
    if not osp.exists(filename):
        logger.error(f"文件不存在：{filename}")
        self.errorMessage("文件不存在", filename)
        return False

    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
except json.JSONDecodeError as e:
    logger.error(f"JSON 格式错误：{e}")
    self.errorMessage("文件格式错误", f"无法解析 JSON: {e}")
except UnicodeDecodeError as e:
    logger.error(f"编码错误：{e}")
    self.errorMessage("编码错误", f"文件编码问题：{e}")
except Exception as e:
    logger.exception(f"未知错误：{e}")
    self.errorMessage("未知错误", str(e))
```

### 2.3 图像加载异常

```python
from PyQt5 import QtGui

def load_image(self, filename):
    try:
        image = QtGui.QImage.fromData(self.load_image_file(filename))
        if image.isNull():
            logger.warning(f"无法加载图像：{filename}")
            formats = [
                f"*.{fmt.data().decode()}"
                for fmt in QtGui.QImageReader.supportedImageFormats()
            ]
            self.errorMessage(
                "无效的图像文件",
                f"支持的格式：{', '.join(formats)}"
            )
            return False
        return image
    except Exception as e:
        logger.exception(f"图像加载失败：{e}")
        return False
```

## 3. 内存泄漏排查

### 3.1 常见内存泄漏场景

```python
# 1. 信号槽未断开导致的泄漏
class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        # 错误：没有保存引用，无法断开连接
        timer = QtCore.QTimer()
        timer.timeout.connect(self.on_timeout)
        timer.start()

    # 正确：保存引用，在删除时停止
    def __init__(self):
        super().__init__()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.on_timeout)
        self.timer.start()

    def closeEvent(self, event):
        self.timer.stop()
        self.timer.timeout.disconnect(self.on_timeout)
        event.accept()
```

```python
# 2. 循环引用
class Parent:
    def __init__(self):
        self.child = Child(self)  # Child 持有 Parent 引用

class Child:
    def __init__(self, parent):
        self.parent = parent  # 循环引用

# 解决：使用 weakref
import weakref
class Child:
    def __init__(self, parent):
        self.parent_ref = weakref.ref(parent)
```

### 3.2 内存分析工具

```bash
# 使用 memory_profiler
pip install memory_profiler
python -m memory_profiler script.py

# 使用 objgraph 查找对象引用
import objgraph
objgraph.show_most_common_types()
objgraph.show_backrefs([suspicious_object], filename='refs.png')
```

## 4. 性能问题分析

### 4.1 性能分析工具

```python
import cProfile
import pstats

# 性能分析
profiler = cProfile.Profile()
profiler.enable()

# 执行代码
run_heavy_task()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative').print_stats(20)
```

```python
# 使用装饰器分析函数执行时间
from loguru import logger
import time
from functools import wraps

def timing(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logger.debug(f"{func.__name__} 执行时间：{end - start:.4f}s")
        return result
    return wrapper

@timing
def slow_function():
    time.sleep(1)
```

### 4.2 UI 性能优化

```python
# 1. 批量更新时禁用信号
class MyListWidget(QtWidgets.QListWidget):
    def batch_add_items(self, items):
        self.blockSignals(True)
        self.setUpdatesEnabled(False)
        try:
            for item in items:
                self.addItem(item)
        finally:
            self.setUpdatesEnabled(True)
            self.blockSignals(False)
```

```python
# 2. 延迟加载大文件
def load_large_file(filename):
    # 使用 QThread 后台加载
    class LoadThread(QtCore.QThread):
        finished = QtCore.pyqtSignal(object)

        def run(self):
            data = heavy_load(filename)
            self.finished.emit(data)

    thread = LoadThread()
    thread.finished.connect(self.on_load_finished)
    thread.start()
```

## 5. 常见错误解决方案

### 5.1 Labelme 常见错误

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `Label list has duplicate` | 标签列表有重复项 | 检查标签配置文件 |
| `No such file or directory` | 文件路径错误 | 检查路径是否存在 |
| `Invalid image file` | 图像格式不支持 | 转换为支持的格式 |
| `QSharedMemory create failed` | 实例检测失败 | 检查共享内存权限 |
| `SAM model not set` | AI 模型未初始化 | 先初始化 AI 模型 |

### 5.2 Windows 特定问题

```python
# 高 DPI 支持
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

# 中文路径问题
import os
os.environ['PYTHONUTF8'] = '1'
```

## 6. 调试技巧

### 6.1 断点调试

```python
# 使用 pdb 调试
import pdb; pdb.set_trace()

# 使用 breakpoint() (Python 3.7+)
breakpoint()

# 在 Qt 应用中调试
# 使用 Qt Creator 或 VS Code 的 Python 调试器
```

### 6.2 运行时检查

```python
# 检查对象状态
def debug_object(obj):
    print(f"Type: {type(obj)}")
    print(f"ID: {id(obj)}")
    print(f"Attributes: {dir(obj)}")
    for attr in ['isVisible', 'isEnabled', 'isHidden']:
        if hasattr(obj, attr):
            print(f"{attr}: {getattr(obj, attr)()}")
```

### 6.3 日志辅助调试

```python
# 在关键位置添加日志
logger.debug(f"进入函数：{func.__name__}, 参数：{args}, {kwargs}")
try:
    result = func(*args, **kwargs)
    logger.debug(f"函数返回：{result}")
    return result
except Exception as e:
    logger.exception(f"函数异常：{func.__name__}, 错误：{e}")
    raise
```

## 7. 技能检查清单

### L1 - 基础
- [ ] 了解日志级别和使用
- [ ] 能够添加基本异常处理
- [ ] 理解常见错误信息
- [ ] 能够使用 print 调试

### L2 - 熟练
- [ ] 能够配置 loguru 日志
- [ ] 理解信号槽异常处理
- [ ] 能够处理文件操作异常
- [ ] 能够使用断点调试
- [ ] 理解 Qt 对象生命周期

### L3 - 精通
- [ ] 能够排查内存泄漏
- [ ] 能够分析性能问题
- [ ] 能够处理复杂异常场景
- [ ] 能够设置全局异常钩子
- [ ] 能够调试多线程问题

### L4 - 专家
- [ ] 能够设计异常处理框架
- [ ] 能够优化系统稳定性
- [ ] 能够制定调试规范
- [ ] 能够指导团队解决问题
- [ ] 能够预防潜在问题
