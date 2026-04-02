import imgviz
import numpy as np
import numpy.typing as npt
import skimage
from loguru import logger

# 文件头部说明:
# 本模块是Labelme自动化标注模块，用于从掩码图像生成多边形标注。
# 主要功能包括：轮廓检测、多边形近似、坐标转换等。
# 这是AI辅助标注功能的重要组成部分，支持将分割掩码转换为多边形标注格式。

def _get_contour_length(contour: npt.NDArray[np.float32]) -> float:
    """
    计算轮廓长度
    
    计算给定轮廓的总长度。
    
    Args:
        contour: 轮廓点数组
        
    Returns:
        float: 轮廓总长度
    """
    # 获取轮廓的起始点和结束点
    contour_start: npt.NDArray[np.float32] = contour
    contour_end: npt.NDArray[np.float32] = np.r_[contour[1:], contour[0:1]]
    
    # 计算相邻点之间的距离并求和
    return np.linalg.norm(contour_end - contour_start, axis=1).sum()


def compute_polygon_from_mask(mask: npt.NDArray[np.bool_]) -> npt.NDArray[np.float32]:
    """
    从掩码图像计算多边形
    
    将二值掩码图像转换为多边形轮廓。
    
    Args:
        mask: 二值掩码图像数组
        
    Returns:
        npt.NDArray[np.float32]: 多边形顶点数组
    """
    # 检测掩码的轮廓
    contours: npt.NDArray[np.float32] = skimage.measure.find_contours(
        np.pad(mask, pad_width=1)  # 填充掩码以确保边界检测
    )
    
    # 如果没有检测到轮廓，返回空多边形
    if len(contours) == 0:
        logger.warning("No contour found, so returning empty polygon.")
        return np.empty((0, 2), dtype=np.float32)

    # 选择最长的轮廓
    contour: npt.NDArray[np.float32] = max(contours, key=_get_contour_length)
    
    # 设置多边形近似容差
    POLYGON_APPROX_TOLERANCE: float = 0.004
    polygon: npt.NDArray[np.float32] = skimage.measure.approximate_polygon(
        coords=contour,  # 轮廓坐标
        tolerance=np.ptp(contour, axis=0).max() * POLYGON_APPROX_TOLERANCE,  # 近似容差
    )
    
    # 将多边形坐标限制在图像范围内
    polygon = np.clip(polygon, (0, 0), (mask.shape[0] - 1, mask.shape[1] - 1))
    
    # 移除最后一个重复的点（与第一个点相同）
    polygon = polygon[:-1]

    # 调试代码：可视化轮廓（默认关闭）
    if 0:
        import PIL.Image

        image_pil = PIL.Image.fromarray(imgviz.gray2rgb(imgviz.bool2ubyte(mask)))
        imgviz.draw.line_(image_pil, yx=polygon, fill=(0, 255, 0))
        for point in polygon:
            imgviz.draw.circle_(image_pil, center=point, diameter=10, fill=(0, 255, 0))
        imgviz.io.imsave("contour.jpg", np.asarray(image_pil))

    # 将坐标从yx格式转换为xy格式
    return polygon[:, ::-1]  # yx -> xy
