# AI 图像标注系统 UI 重构设计方案

## 📋 文档信息

- **项目名称**: AI 图像标注与训练系统 (WSLabelme)
- **参考项目**: desktopgui-wwp_codebar (条码阅读器配置软件)
- **设计目标**: 将当前主界面改成参考项目 mainform.ui 的风格
- **文档版本**: 2.0
- **创建日期**: 2026-03-09

---

## 📊 需求分析

### 2.1 参考项目 UI 特点分析 (desktopgui-wwp_codebar)

通过研究 `E:\shangweiji\desktopgui-wwp_codebar\Src\CustomWidget\mainform.ui`，总结出以下 UI 特点：

**整体布局结构**:
```
┌─────────────────────────────────────────────────────────────┐
│                    Banner (顶部横幅区域)                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  [导航按钮] [Logo]                    [窗口控制按钮]  │    │
│  └─────────────────────────────────────────────────────┘    │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│ Contents (主内容区)                                          │
│ ┌──────┬────────────────────────────────────────────────┐   │
│ │左侧  │                                                │   │
│ │工具  │            QStackedWidget                      │   │
│ │栏    │            (多页面切换区域)                     │   │
│ │      │                                                │   │
│ │64px  │  ┌──────────┬──────────┬──────────┬──────────┐│   │
│ │      │  │ 页面 1   │ 页面 2   │ 页面 3   │ 页面 4   ││   │
│ │      │  └──────────┴──────────┴──────────┴──────────┘│   │
│ └──────┴────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**核心组件**:
| 组件名称 | 类型 | 尺寸 | 功能 |
|---------|------|------|------|
| `banner` | QFrame | 高度约 70px | 顶部横幅，包含 Logo 和导航 |
| `btn_gettingStarted` | PushButtonEx | 64x70px | 起始页导航按钮 |
| `btn_labelme` | PushButtonEx | 64x70px | Labelme 功能导航按钮 |
| `logo_label` | QLabel | 465x70px | Logo 显示区域 |
| `btn_close/maximize/minimize` | QToolButton | 30x34px | 窗口控制按钮 |
| `stackedWidget_deviceSelection_deviceDetail` | QStackedWidget | 自适应 | 主内容页面切换 |
| `groupBox_LeftMenu` | QGroupBox | 64px 宽 | 左侧工具栏容器 |

**样式特点**:
1. 顶部 Banner 使用渐变紫色背景 (`#667eea` → `#764ba2`)
2. 导航按钮使用图标 + 固定尺寸设计
3. 左侧工具栏垂直排列，按钮为正方形 (64x64px)
4. 窗口控制按钮自定义样式，悬停时有边框效果
5. 底部有 4px 高的指示条

### 2.2 当前项目现状分析 (WSLabelme)

当前项目 `mainform.ui` 已具备基本框架：

**现有结构**:
- 顶部导航栏 (`topNavigationFrame`): 4 个文本按钮（图像标注、模型训练、模型使用、系统设置）
- 中央内容区 (`stackedWidget_content`): 4 个页面
- 图像标注页：左侧工具栏 + 画布 + 右侧面板

**需要改进的地方**:
1. 顶部导航栏需要改成 Banner 风格（渐变背景 + 图标按钮 + Logo）
2. 添加窗口控制按钮（最小化、最大化、关闭）
3. 左侧工具栏需要参考参考项目的样式
4. 整体配色和字体需要统一

---

## 🏗️ UI 重构设计方案

### 3.1 整体布局

```
┌─────────────────────────────────────────────────────────────────────┐
│  Banner (渐变紫色背景 #667eea → #764ba2)                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  [图像标注] [模型训练] [模型使用] [系统设置]     [Logo] [×]  │   │
│  │     64x70px   64x70px   64x70px   64x70px    465x70px        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  └──────────────────────────────────────────────────────────────┘  │
│  4px 指示条                                                         │
├─────────────────────────────────────────────────────────────────────┤
│  Contents (主内容区)                                                 │
│  ┌─────┬────────────────────────────────────────────────────────┐  │
│  │左侧 │  QStackedWidget                                        │  │
│  │工具 │  ┌──────────────────────────────────────────────────┐  │  │
│  │栏   │  │  page_imageAnnotation (图像标注页)                │  │  │
│  │64px │  │  ┌────┬──────────────┬─────────────────────┐     │  │  │
│  │     │  │  │工具│    画布区域    │   右侧面板          │     │  │  │
│  │     │  │  │栏  │  (Labelme)   │  - 标签管理         │     │  │  │
│  │     │  │  │    │              │  - 文件列表         │     │  │  │
│  │     │  │  └────┴──────────────┴─────────────────────┘     │  │  │
│  │     │  └──────────────────────────────────────────────────┘  │  │
│  │     │  ┌──────────────────────────────────────────────────┐  │  │
│  │     │  │  page_modelTraining (模型训练页)                  │  │  │
│  │     │  │  [运行] [停止] + 训练日志                         │  │  │
│  │     │  └──────────────────────────────────────────────────┘  │  │
│  │     │  ┌──────────────────────────────────────────────────┐  │  │
│  │     │  │  page_modelUsage (模型使用页)                     │  │  │
│  │     │  │  [下载相机] [下载本地] + 模型信息                  │  │  │
│  │     │  └──────────────────────────────────────────────────┘  │  │
│  │     │  ┌──────────────────────────────────────────────────┐  │  │
│  │     │  │  page_systemSettings (系统设置页)                 │  │  │
│  │     │  │  [通用设置] [快捷键设置] 选项卡                    │  │  │
│  │     │  └──────────────────────────────────────────────────┘  │  │
│  └─────┴────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 顶部 Banner 设计

**结构**:
```xml
<QFrame name="banner">
  <layout class="QVBoxLayout" stretch="1,0">
    <item>
      <QFrame name="frame_top">  <!-- 70px 高 -->
        <layout class="QHBoxLayout">
          <item>导航按钮组 (PushButtonEx)</item>
          <item>spacer (弹性空间)</item>
          <item>Logo 区域 (QLabel, 465x70px)</item>
          <item>窗口控制按钮组</item>
        </layout>
      </QFrame>
    </item>
    <item>
      <QLabel name="label_up"/>  <!-- 4px 指示条 -->
    </item>
  </layout>
</QFrame>
```

**导航按钮设计**:
| 按钮 | 图标 | 工具提示 | 对应页面 |
|------|------|----------|----------|
| `btn_imageAnnotation` | 图片图标 | 图像标注 | page_imageAnnotation |
| `btn_modelTraining` | 播放图标 | 模型训练 | page_modelTraining |
| `btn_modelUsage` | 下载图标 | 模型使用 | page_modelUsage |
| `btn_systemSettings` | 设置图标 | 系统设置 | page_systemSettings |

**窗口控制按钮**:
| 按钮 | 文本 | 功能 |
|------|------|------|
| `btn_minimize` | ─ | 最小化窗口 |
| `btn_maximize` | □ | 最大化/还原窗口 |
| `btn_close` | × | 关闭窗口 |

### 3.3 左侧工具栏设计

**结构** (仅在图像标注页显示):
```xml
<QFrame name="frame_annotationTools">
  <property name="minimumSize"><size><width>80</width><height>0</height></size></property>
  <property name="maximumSize"><size><width>80</width><height>16777215</height></size></property>
  <layout class="QVBoxLayout">
    <item><QPushButton name="btn_editMode">F1</QPushButton></item>
    <item><QPushButton name="btn_rectangleMode">F2</QPushButton></item>
    <item><QPushButton name="btn_polygonMode">F3</QPushButton></item>
    <item><QPushButton name="btn_deleteSingle">F4</QPushButton></item>
    <item><QPushButton name="btn_undo">Ctrl+Z</QPushButton></item>
    <item><QPushButton name="btn_redo">Ctrl+Y</QPushButton></item>
    <item><spacer/></item>
  </layout>
</QFrame>
```

### 3.4 颜色方案

| 用途 | 颜色值 | 说明 |
|------|--------|------|
| Banner 渐变起始色 | `#667eea` | 紫色 |
| Banner 渐变结束色 | `#764ba2` | 深紫色 |
| 强调色 | `#ff6666` | 选中/激活状态 |
| 背景灰 | `#f0f0f0` | 主背景 |
| 工具栏背景 | `#f8f8f8` | 侧边栏背景 |
| 按钮默认 | `#e0e0e0` | 普通按钮 |
| 按钮悬停 | `#d0d0d0` | 鼠标悬停 |
| 按钮激活 | `#ffcccc` | 选中状态 |
| 窗口控制悬停 | `#e81123` | 关闭按钮悬停红色 |

### 3.5 字体规范

| 元素 | 字体 | 大小 | 字重 |
|------|------|------|------|
| 窗口标题 | Microsoft YaHei | 24px | Bold |
| 导航按钮 | Microsoft YaHei | 14px | Bold |
| 工具按钮 | Microsoft YaHei | 12px | Bold |
| 普通文本 | Microsoft YaHei | 13px | Normal |
| 日志文本 | Consolas | 13px | Normal |

---

## 🔧 技术实现方案

### 4.1 文件修改计划

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `mainform.ui` | 重构 | 重新设计顶部 Banner 和整体布局 |
| `main.py` | 更新 | 适配新的 UI 结构，更新信号槽连接 |
| `labelme/resources/` | 新增 | 添加图标资源文件 |

### 4.2 mainform.ui 关键修改点

1. **添加 Banner 区域**:
   - 在 `centralwidget` 的 `QVBoxLayout` 顶部添加 `banner` QFrame
   - 设置渐变背景样式
   - 添加导航按钮组（使用 PushButtonEx 或 QPushButton + 图标）
   - 添加 Logo 显示区域
   - 添加窗口控制按钮

2. **修改主内容区**:
   - 保留 `QStackedWidget` 结构
   - 调整页面布局以适配新设计

3. **样式表设置**:
   - 为 Banner 设置渐变背景
   - 为导航按钮设置悬停和激活状态样式
   - 为窗口控制按钮设置自定义样式

### 4.3 main.py 关键修改点

1. **窗口控制信号连接**:
```python
self.btn_minimize.clicked.connect(self.showMinimized)
self.btn_maximize.clicked.connect(self.toggleMaximize)
self.btn_close.clicked.connect(self.close)
```

2. **导航按钮信号连接**:
```python
# 使用按钮组实现互斥选择
self.nav_button_group = QButtonGroup(self)
self.nav_button_group.addButton(self.btn_imageAnnotation, 0)
self.nav_button_group.addButton(self.btn_modelTraining, 1)
self.nav_button_group.addButton(self.btn_modelUsage, 2)
self.nav_button_group.addButton(self.btn_systemSettings, 3)
self.nav_button_group.buttonClicked.connect(self.on_nav_button_clicked)
```

---

## ❓ 待确认事项

请在实施前确认以下问题：

1. **左侧工具栏**: 参考项目的左侧工具栏是全局的（所有页面都显示），但当前设计是仅在图像标注页显示。需要确认采用哪种方案？

2. **尺寸调整**: 参考项目的窗口尺寸是 1210x658，当前设计是 1200x800。需要确认采用哪种尺寸？

---

## 📁 可用图标资源

根据参考项目 `E:\shangweiji\desktopgui-wwp_codebar\Src\ui` 目录，可用图标资源如下：

### 导航按钮图标
| 用途 | 图标文件 | 说明 |
|------|----------|------|
| 图像标注 | `labelme_r.svg` / `labelme_w.svg` | 标注功能图标 |
| 模型训练 | `play.svg` / `play-circle.svg` | 播放/运行图标 |
| 模型使用 | `download.svg` / `file-download.svg` | 下载图标 |
| 系统设置 | `tool_r.svg` / `tool_w.svg` 或 `wrench.svg` | 工具/设置图标 |

### 窗口控制图标
| 用途 | 图标文件 |
|------|----------|
| 最小化 | `window-minimize.svg` |
| 最大化 | `window-maximize.svg` |
| 关闭 | `window-close.svg` |
| 还原 | `window-restore.svg` |

### 左侧工具栏图标（图像标注页）
| 用途 | 图标文件 | 备选 |
|------|----------|------|
| 编辑模式 | `penceil_32x32.png` | - |
| 矩形标注 | `tool_box_24_jia.png` | - |
| 多边形标注 | `tool_box_24_jian.png` | - |
| 清除单个 | `eraser_32x32.png` | - |
| 撤销 | `reset.svg` | - |
| 重做 | `refresh.svg` | - |

### Logo 图片
| 用途 | 图标文件 | 尺寸 |
|------|----------|------|
| Banner Logo | `20250324-161340.png` | 465x70px |
| 备用 Logo | `logo.png` | - |
| 背景条 | `bar_660.jpg` | 660px 宽 |

### 其他相关图标
| 用途 | 图标文件 |
|------|----------|
| 导入图片 | `upload.svg` / `file-upload.svg` |
| 连接相机 | `camera-edit.svg` |
| 保存图像 | `imageSave.svg` |

---

## 📋 实施步骤

### 阶段一：UI 文件重构
1. [ ] 修改 mainform.ui，添加 Banner 区域
2. [ ] 添加导航按钮和图标
3. [ ] 添加窗口控制按钮
4. [ ] 调整主内容区布局
5. [ ] 设置样式表

### 阶段二：Python 代码适配
1. [ ] 更新 main.py 中的信号槽连接
2. [ ] 实现窗口控制功能
3. [ ] 实现导航按钮页面切换
4. [ ] 测试各页面功能

### 阶段三：测试与优化
1. [ ] 测试 UI 显示效果
2. [ ] 测试页面切换功能
3. [ ] 测试标注功能
4. [ ] 根据反馈调整细节

---

## 🔗 参考文件

- 参考项目 UI: `E:\shangweiji\desktopgui-wwp_codebar\Src\CustomWidget\mainform.ui`
- 当前项目 UI: `mainform.ui`
- HTML Demo: `ui_understanding.html`
- 原有设计文档: `plans/ui_design_plan.md`
