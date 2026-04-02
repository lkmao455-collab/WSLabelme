# 文件头部说明:
# 本模块是Labelme自动化标注包的初始化文件。
# 主要功能包括：导入和导出所有自动化标注模块，提供统一的访问接口。
# 这是Labelme AI辅助标注功能的统一入口，包含了所有自动化标注相关的功能模块。

# 导入自动化标注模块
from .bbox_from_text import get_bboxes_from_texts  # 从文本生成边界框
from .bbox_from_text import nms_bboxes            # 非极大值抑制处理
from .bbox_from_text import get_shapes_from_bboxes # 边界框转形状格式
from .polygon_from_mask import compute_polygon_from_mask  # 从掩码生成多边形
