# flake8: noqa

# 文件头部说明:
# 本模块是Labelme的工具函数集合，提供了图像处理、形状转换、Qt界面组件等核心功能。
# 这些工具函数是Labelme标注工具的基础支撑，被各个核心模块广泛使用。

# 图像处理相关工具函数
from ._io import lblsave  # 标注文件保存工具

# 图像格式转换工具
from .image import apply_exif_orientation  # 应用EXIF方向信息
from .image import img_arr_to_b64           # 数组转Base64编码
from .image import img_arr_to_data          # 数组转图像数据
from .image import img_b64_to_arr           # Base64编码转数组
from .image import img_data_to_arr          # 图像数据转数组
from .image import img_data_to_pil          # 图像数据转PIL图像
from .image import img_data_to_png_data     # 图像数据转PNG数据
from .image import img_pil_to_data          # PIL图像转图像数据
from .image import img_qt_to_arr            # Qt图像转数组

# 形状处理和转换工具
from .shape import labelme_shapes_to_label  # Labelme形状转标签
from .shape import masks_to_bboxes          # 掩码转边界框
from .shape import polygons_to_mask         # 多边形转掩码
from .shape import shape_to_mask            # 形状转掩码
from .shape import shapes_to_label          # 形状转标签

# Qt界面组件和工具
from .qt import newIcon                    # 创建图标
from .qt import newButton                  # 创建按钮
from .qt import newAction                  # 创建动作
from .qt import addActions                 # 添加动作到菜单/工具栏
from .qt import labelValidator             # 标签验证器
from .qt import struct                     # 结构体工具
from .qt import distance                   # 距离计算
from .qt import distancetoline             # 点到线的距离
from .qt import fmtShortcut                # 格式化快捷键
