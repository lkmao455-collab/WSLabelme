# flake8: noqa

# 文件头部说明:
# 本模块是Labelme widgets包的初始化文件。
# 主要功能包括：导入和导出所有widgets组件，提供统一的访问接口。
# 这是Labelme用户界面组件的统一入口，包含了所有UI相关的组件类。

# AI相关组件
from .ai_prompt_widget import AiPromptWidget  # AI提示主组件

# 图像处理相关组件
from .brightness_contrast_dialog import BrightnessContrastDialog  # 亮度对比度调整对话框

# 核心绘图组件
from .canvas import Canvas  # 画布组件

# 颜色选择组件
from .color_dialog import ColorDialog  # 颜色选择对话框

# 文件操作相关组件
from .file_dialog_preview import FileDialogPreview  # 文件对话框预览组件

# 标签管理相关组件
from .label_dialog import LabelDialog      # 标签对话框
from .label_dialog import LabelQLineEdit   # 标签输入框

from .label_list_widget import LabelListWidget        # 标签列表组件
from .label_list_widget import LabelListWidgetItem    # 标签列表项

# 工具栏组件
from .tool_bar import ToolBar  # 工具栏组件

# 唯一标签管理组件
from .unique_label_qlist_widget import UniqueLabelQListWidget  # 唯一标签列表组件

# 缩放控制组件
from .zoom_widget import ZoomWidget  # 缩放控件

# 缩略图文件列表组件
from .thumbnail_file_list import ThumbnailFileList  # 缩略图文件列表

# 训练配置停靠窗口组件
from .training_dock_widget import TrainingDockWidget  # 训练配置面板

# 训练任务监控组件
from .training_task_widget import TrainingTaskWidget  # 训练任务监控面板

# 综合训练面板组件（合并训练配置和任务监控）
from .unified_training_widget import UnifiedTrainingWidget  # 综合训练面板

# 训练曲线实时显示组件
from .training_curve_widget import TrainingCurveCanvas  # 训练曲线画布
from .training_curve_widget import TrainingCurveDock  # 训练曲线 Dock
from .training_curve_widget import RealtimeTrainingCurvesWidget  # 实时训练曲线组件
