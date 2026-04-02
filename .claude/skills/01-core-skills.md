# 核心开发技能 (Core Development Skills)

## 1. 项目架构理解

### 1.1 项目结构
```
WSLabelme/
├── main.py                      # 应用程序入口（新 UI）
├── mainform.ui                  # Qt Designer UI 文件
├── model_training.py            # 模型训练管理器
├── model_usage.py               # 模型使用管理器
├── labelme/                     # Labelme 核心模块
│   ├── __main__.py              # Labelme 原始入口
│   ├── app.py                   # Labelme 主窗口
│   ├── label_file.py            # 标注文件处理
│   ├── shape.py                 # 形状类定义
│   ├── tcp_client.py            # TCP 客户端
│   ├── tcp_config.py            # TCP 配置管理
│   ├── config/                  # 配置管理
│   │   ├── __init__.py          # 配置加载
│   │   └── default_config.yaml  # 默认配置
│   └── widgets/                 # UI 组件
│       ├── canvas.py            # 画布组件
│       ├── label_dialog.py      # 标签对话框
│       ├── label_list_widget.py # 标签列表
│       ├── tool_bar.py          # 工具栏
│       └── ...
└── tests/                       # 测试目录
```

### 1.2 核心模块职责

| 模块 | 职责 | 关键类/函数 |
|------|------|------------|
| main.py | 新 UI 入口，整合标注/训练/模型使用 | AIAnnotationMainWindow |
| labelme/app.py | Labelme 主窗口，标注核心逻辑 | MainWindow |
| labelme/widgets/canvas.py | 画布绘制，形状编辑 | Canvas |
| labelme/shape.py | 形状数据结构和渲染 | Shape |
| labelme/label_file.py | JSON 标注文件读写 | LabelFile |
| model_training.py | 模型训练流程控制 | ModelTrainer |
| model_usage.py | 模型下载和使用 | ModelUsageManager |

## 2. PyQt5 开发规范

### 2.1 信号与槽

```python
# 定义信号
class MyWidget(QtWidgets.QWidget):
    dataChanged = QtCore.pyqtSignal(object)
    processingFinished = QtCore.pyqtSignal(bool, str)

# 发送信号
self.dataChanged.emit(data)

# 连接信号
self.widget.dataChanged.connect(self.on_data_changed)
```

### 2.2 内存管理

```python
# 正确删除 Qt 对象
widget.deleteLater()  # 安全删除

# 避免循环引用
# 使用 weakref 或及时断开信号连接
```

### 2.3 线程安全

```python
# 后台线程不能直接操作 UI
# 必须通过信号传递到主线程
class WorkerThread(QtCore.QThread):
    resultReady = QtCore.pyqtSignal(object)

    def run(self):
        result = heavy_computation()
        self.resultReady.emit(result)  # 通过信号传递
```

## 3. 标注功能开发

### 3.1 形状类型

| 形状类型 | 说明 | 使用场景 |
|----------|------|----------|
| polygon | 多边形 | 不规则物体标注 |
| rectangle | 矩形框 | 目标检测 |
| circle | 圆形 | 圆形物体 |
| line | 线条 | 线性特征 |
| point | 点 | 关键点标注 |
| linestrip | 连续线 | 道路、边界 |
| ai_polygon | AI 辅助多边形 | 智能标注 |
| ai_mask | AI 辅助掩码 | 语义分割 |

### 3.2 标注数据格式

```json
{
  "version": "5.0.0",
  "flags": {},
  "shapes": [
    {
      "label": "person",
      "points": [[x1,y1], [x2,y2], ...],
      "group_id": null,
      "shape_type": "polygon",
      "flags": {},
      "description": "optional"
    }
  ],
  "imagePath": "image.jpg",
  "imageData": "base64_encoded_string",
  "imageHeight": 1080,
  "imageWidth": 1920
}
```

### 3.3 关键 API

```python
# 加载文件
mainwindow.loadFile(filename)

# 保存标注
mainwindow.saveFile()

# 切换绘制模式
canvas.createMode = "polygon"  # 或 rectangle, circle, etc.

# 设置编辑模式
canvas.setEditing(True)

# 撤销/重做
canvas.undoLastPoint()
canvas.restoreShape()
canvas.redoShape()
```

## 4. AI 集成开发

### 4.1 SAM 模型集成

```python
# 初始化 AI 模型
canvas.initializeAiModel(model_name="sam_vit_h")

# 图像嵌入缓存
canvas._compute_and_cache_image_embedding()

# AI 形状更新
_update_shape_with_sam(
    shape=current_shape,
    createMode="ai_polygon",
    model_name="sam_vit_h",
    image_embedding=embedding
)
```

### 4.2 模型训练集成

```python
# 训练器使用
trainer = ModelTrainer()
trainer.training_started.connect(on_start)
trainer.training_log_updated.connect(on_log)
trainer.training_finished.connect(on_finish)
trainer.start_training()
```

## 5. 数据管理

### 5.1 文件操作

```python
from labelme.label_file import LabelFile

# 加载标注文件
label_file = LabelFile("annotation.json")
image_data = label_file.imageData
shapes = label_file.shapes

# 保存标注
LabelFile.save_file("annotation.json", shapes, image_data)
```

### 5.2 配置管理

```python
from labelme.config import get_config

# 加载配置
config = get_config(config_file="~/.labelmerc")

# 配置项
config["labels"]           # 预定义标签
config["auto_save"]        # 自动保存
config["validate_label"]   # 标签验证
config["shortcuts"]        # 快捷键
```

## 6. 技能检查清单

### L1 - 基础
- [ ] 理解项目目录结构
- [ ] 能够运行应用程序
- [ ] 了解基本的 PyQt5 组件
- [ ] 能够修改简单 UI 文本

### L2 - 熟练
- [ ] 理解信号槽机制
- [ ] 能够添加新 UI 组件
- [ ] 理解标注数据格式
- [ ] 能够修改配置项
- [ ] 能够添加新快捷键

### L3 - 精通
- [ ] 深入理解 Canvas 绘制机制
- [ ] 能够开发自定义形状类型
- [ ] 理解 AI 辅助标注原理
- [ ] 能够优化性能问题
- [ ] 能够调试复杂问题

### L4 - 专家
- [ ] 能够设计新架构模块
- [ ] 能够整合新的 AI 模型
- [ ] 能够进行代码重构
- [ ] 能够制定开发规范
- [ ] 能够指导团队成员
