# 训练可视化使用指南

## 功能概述

本系统提供训练过程的可视化功能，包括：

### 1. 实时训练曲线 Dock（新增）
- **损失曲线 Dock**: 实时显示训练过程中损失随轮次的变化
- **准确率曲线 Dock**: 实时显示训练过程中准确率随轮次的变化
- 两个 dock 垂直排列，自动跟随训练进度更新
- dock 不可关闭（符合 UI 设计要求），但可移动和浮动

### 2. 离线绘图工具
- 使用 matplotlib 绘制静态训练曲线图
- 支持多任务对比显示
- 可保存为图片文件

## 目录

1. [实时训练曲线 Dock](#实时训练曲线 dock)
2. [离线绘图工具](#离线绘图工具)
3. [API 参考](#api 参考)
4. [使用示例](#使用示例)

---

## 实时训练曲线 Dock

### 功能特点

✅ **自动显示**: 启动训练时自动显示曲线 dock
✅ **实时更新**: 曲线跟随训练进度实时更新
✅ **自动清除**: 每次新训练开始时清除旧数据
✅ **不可关闭**: dock 没有关闭按钮，符合 UI 规范
✅ **可移动浮动**: 可以拖动调整位置或设为浮动窗口

### 界面布局

```
┌─────────────────────────────────────┐
│  主窗口                              │
│  ┌─────────────────────────────┐   │
│  │  损失曲线 Dock (顶部)        │   │
│  │  纵轴：损失值                │   │
│  │  横轴：轮次                  │   │
│  ├─────────────────────────────┤   │
│  │  准确率曲线 Dock (底部)      │   │
│  │  纵轴：准确率 (0-1)          │   │
│  │  横轴：轮次                  │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

### 使用方法

1. **启动训练**:
   - 在训练管理面板中选择或创建训练任务
   - 点击"启动训练"按钮
   - 曲线 dock 自动显示并开始更新

2. **查看曲线**:
   - 左侧 dock 显示损失曲线
   - 右侧 dock 显示准确率曲线
   - 曲线实时跟随训练进度更新

3. **调整布局**:
   - 拖动 dock 标题栏可移动位置
   - 双击 dock 标题栏可设为浮动窗口
   - 拖动 dock 边缘可调整大小

4. **隐藏曲线**:
   - 在训练管理面板点击其他 dock
   - 曲线 dock 会自动隐藏（但不会关闭）
   - 下次训练时会自动显示

### 技术实现

**组件结构**:
- `TrainingCurveCanvas`: matplotlib 画布组件
- `TrainingCurveDock`: 曲线 dock 窗口
- `RealtimeTrainingCurvesWidget`: 双曲线组合组件

**数据流**:
```
训练任务 → UnifiedTrainingWidget → MainWindow → TrainingCurveDock
    ↓
累积训练数据 → 回调函数 → 更新曲线
```

**关键代码**:
```python
# 在 app.py 中创建 dock
self.loss_curve_dock = TrainingCurveDock("损失曲线", self, curve_type='loss')
self.acc_curve_dock = TrainingCurveDock("准确率曲线", self, curve_type='accuracy')

# 更新曲线
def update_training_curves(self, epochs, losses, accuracies):
    self.loss_curve_dock.update_curve(epochs, losses)
    self.acc_curve_dock.update_curve(epochs, accuracies)
```

---

## 离线绘图工具

### 快速开始

### 方法 1: 使用模拟数据测试

```python
from training_visualization import TrainingVisualizer

# 创建可视化器
visualizer = TrainingVisualizer()

# 准备数据
epochs = [0, 100, 200, 300, 400, 500]
losses = [9.0, 5.2, 3.1, 2.0, 1.5, 1.2]
accuracies = [0.1, 0.45, 0.68, 0.82, 0.89, 0.93]

# 添加任务数据
visualizer.add_task_data('任务 1', epochs, losses, accuracies)

# 绘制图表
visualizer.plot_loss_curves()  # 损失曲线
visualizer.plot_accuracy_curves()  # 准确率曲线
visualizer.plot_both_curves()  # 两个图并排显示
```

### 方法 2: 从训练客户端获取数据

```python
from training_visualization import TrainingVisualizer
from training_client.training_client import TrainingClient

# 创建客户端和可视化器
client = TrainingClient()
visualizer = TrainingVisualizer()

# 获取所有任务
tasks = client.get_all_tasks()

# 为每个任务收集数据
for task in tasks:
    task_id = task.get('id')
    task_name = task.get('name', f'Task {task_id}')
    
    # 获取训练进度
    progress = client.get_progress(task_id)
    
    if progress and 'progress' in progress:
        p = progress['progress']
        
        # 提取数据
        epochs = p.get('epoch', [])
        losses = p.get('loss', [])
        accuracies = p.get('accuracy', [])
        
        visualizer.add_task_data(task_name, epochs, losses, accuracies)

# 绘制图表
visualizer.plot_both_curves(save_path='training_curves.png')
```

### 方法 3: 从日志文件解析

```python
from training_visualization import TrainingVisualizer
import re

visualizer = TrainingVisualizer()

epochs_data = []
losses_data = []
accuracies_data = []

with open('training.log', 'r', encoding='utf-8') as f:
    for line in f:
        # 匹配格式：Epoch 1, Loss: 2.345, Accuracy: 0.567
        match = re.search(r'Epoch[:\s]*(\d+).*?Loss[:\s]*([\d.]+).*?Accuracy[:\s]*([\d.]+)', line)
        if match:
            epochs_data.append(int(match.group(1)))
            losses_data.append(float(match.group(2)))
            accuracies_data.append(float(match.group(3)))

visualizer.add_task_data('训练任务', epochs_data, losses_data, accuracies_data)
visualizer.plot_both_curves(save_path='from_log.png')
```

## API 参考

### TrainingVisualizer 类（离线绘图）

#### 初始化
```python
visualizer = TrainingVisualizer(font_path=None)
```
- `font_path`: 中文字体文件路径（可选）

#### 添加数据
```python
visualizer.add_task_data(task_name, epochs, losses, accuracies)
```
- `task_name`: 任务名称（字符串）
- `epochs`: 轮次列表
- `losses`: 损失值列表
- `accuracies`: 准确率列表

#### 绘制图表

1. **单独绘制损失曲线**
```python
visualizer.plot_loss_curves(save_path='loss.png', show=True, figsize=(12, 6))
```

2. **单独绘制准确率曲线**
```python
visualizer.plot_accuracy_curves(save_path='acc.png', show=True, figsize=(12, 6))
```

3. **并排绘制两个图表**
```python
visualizer.plot_both_curves(save_path='both.png', show=True, figsize=(14, 6))
```

参数说明：
- `save_path`: 保存路径（可选）
- `show`: 是否显示图表（默认 True）
- `figsize`: 图表大小（宽，高）

#### 清除数据
```python
visualizer.clear_data()
```

### TrainingCurveDock 类（实时显示）

#### 初始化
```python
from labelme.widgets import TrainingCurveDock

dock = TrainingCurveDock(title, parent, curve_type='loss')
```
- `title`: Dock 标题
- `parent`: 父窗口
- `curve_type`: 曲线类型 ('loss' 或 'accuracy')

#### 更新数据
```python
dock.update_curve(epochs, values)
```

#### 清除数据
```python
dock.clear_curve()
```

### MainWindow 方法（实时显示控制）

#### 更新曲线
```python
main_window.update_training_curves(epochs, losses, accuracies)
```

#### 显示/隐藏曲线 dock
```python
main_window.show_training_curves(show=True)  # 显示
main_window.show_training_curves(show=False)  # 隐藏
```

#### 清除曲线
```python
main_window.clear_training_curves()
```

## 使用示例

### 示例 1: 运行离线绘图测试

```bash
python plot_training_curves.py
```

这将生成模拟数据的训练曲线图。

### 示例 2: 在训练时查看实时曲线

1. 启动主程序
2. 连接到训练服务器
3. 选择或创建训练任务
4. 点击"启动训练"
5. 观察曲线 dock 自动显示并更新

### 示例 3: 自定义曲线样式

```python
from labelme.widgets import TrainingCurveDock

# 创建 dock
dock = TrainingCurveDock("自定义曲线", parent, curve_type='loss')

# 获取画布对象进行自定义
canvas = dock.canvas
canvas.axes.set_title('自定义标题', fontsize=14)
canvas.axes.grid(True, alpha=0.5)

# 更新数据
dock.update_curve(epochs, losses)
```

## 注意事项

### 实时曲线 Dock

1. **自动行为**:
   - 启动训练时自动显示
   - 新训练开始时自动清除旧数据
   - 训练过程中实时更新

2. **dock 特性**:
   - 不可关闭（没有关闭按钮）
   - 可移动（拖动标题栏）
   - 可浮动（双击标题栏）

3. **性能考虑**:
   - 曲线自动采样显示大量数据点
   - 实时更新频率与训练进度同步

### 离线绘图

1. **中文字体**: 工具会自动检测系统并配置中文字体
   - Windows: SimHei, Microsoft YaHei
   - macOS: Arial Unicode MS, PingFang SC
   - Linux: WenQuanYi Micro Hei

2. **数据格式**: 
   - epochs, losses, accuracies 必须是等长的列表
   - 准确率通常在 0-1 之间

3. **性能**: 
   - 如果数据点很多（如 5000 个轮次），建议采样显示
   - 使用 `epochs[::100]` 每隔 100 个点采样一次

## 故障排除

### 实时曲线 Dock

**问题**: 曲线 dock 不显示
- **解决**: 确保点击了"启动训练"按钮
- **解决**: 检查是否连接到训练服务器

**问题**: 曲线不更新
- **解决**: 检查训练任务是否正常运行
- **解决**: 查看日志是否有错误信息

**问题**: 中文显示为方框
- **解决**: 系统字体配置问题，重启程序

### 离线绘图

**问题**: 中文显示为方框
- **解决**: 指定系统字体路径
```python
visualizer = TrainingVisualizer(font_path='C:/Windows/Fonts/simhei.ttf')
```

**问题**: 图表不显示
- **解决**: 确保 `show=True` 并且安装了 matplotlib

**问题**: 数据点太多图表卡顿
- **解决**: 对数据进行采样
```python
sample_rate = 100
sampled_epochs = epochs[::sample_rate]
sampled_losses = losses[::sample_rate]
```

## 相关文件

- `labelme/widgets/training_curve_widget.py`: 实时曲线组件
- `training_visualization.py`: 离线绘图工具
- `plot_training_curves.py`: 绘图示例
- `labelme/app.py`: 主窗口集成代码
- `labelme/widgets/unified_training_widget.py`: 训练监控组件
