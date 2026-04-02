# MIT License
# Copyright (c) Kentaro Wada

# 文件头部说明:
# 本模块提供了Labelme中形状处理和转换的核心工具函数。
# 主要功能包括：多边形转掩码、形状转掩码、形状转标签、掩码转边界框等。
# 这些函数是Labelme形状标注数据处理的基础，用于将用户绘制的形状转换为
# 计算机视觉算法可以使用的格式（如掩码、标签数组、边界框等）。

import math
import uuid
from typing import Optional

import numpy as np
import numpy.typing as npt
import PIL.Image
import PIL.ImageDraw
from loguru import logger


def polygons_to_mask(img_shape, polygons, shape_type=None):
    """
    将多边形转换为掩码（已废弃）
    
    注意：此函数已废弃，请使用shape_to_mask函数。
    
    Args:
        img_shape: 图像形状 (height, width, channels)
        polygons: 多边形顶点列表
        shape_type: 形状类型
        
    Returns:
        numpy.ndarray: 掩码数组
    """
    logger.warning(
        "The 'polygons_to_mask' function is deprecated, " "use 'shape_to_mask' instead."
    )
    return shape_to_mask(img_shape, points=polygons, shape_type=shape_type)


def shape_to_mask(
    img_shape: tuple[int, ...],
    points: list[list[float]],
    shape_type: Optional[str] = None,
    line_width: int = 10,
    point_size: int = 5,
) -> npt.NDArray[np.bool_]:
    """
    将形状转换为二值掩码
    
    根据给定的点和形状类型，在指定图像尺寸上创建对应的二值掩码。
    支持多种形状类型：多边形、矩形、圆形、线条、线条带、点等。
    
    Args:
        img_shape: 目标图像形状 (height, width, ...)
        points: 形状的顶点坐标列表 [[x1, y1], [x2, y2], ...]
        shape_type: 形状类型，可选值：
            - "polygon": 多边形（默认）
            - "rectangle": 矩形
            - "circle": 圆形
            - "line": 线条
            - "linestrip": 线条带
            - "point": 点
        line_width: 线条宽度（用于line和linestrip类型）
        point_size: 点大小（用于point类型）
        
    Returns:
        numpy.ndarray: 二值掩码数组，形状为(img_shape[:2])
        
    Raises:
        ValueError: 当shape_type不支持时
        AssertionError: 当点数不符合形状要求时
    """
    # 创建空白掩码图像
    mask = PIL.Image.fromarray(np.zeros(img_shape[:2], dtype=np.uint8))
    draw = PIL.ImageDraw.Draw(mask)
    xy = [tuple(point) for point in points]
    
    # 根据形状类型绘制不同的图形
    if shape_type == "circle":
        # 圆形：需要2个点（圆心和圆周上的点）
        assert len(xy) == 2, "Shape of shape_type=circle must have 2 points"
        (cx, cy), (px, py) = xy
        d = math.sqrt((cx - px) ** 2 + (cy - py) ** 2)
        draw.ellipse([cx - d, cy - d, cx + d, cy + d], outline=1, fill=1)
    elif shape_type == "rectangle":
        # 矩形：需要2个点（对角线的两个端点）
        assert len(xy) == 2, "Shape of shape_type=rectangle must have 2 points"
        draw.rectangle(xy, outline=1, fill=1)
    elif shape_type == "line":
        # 线条：需要2个点（起点和终点）
        assert len(xy) == 2, "Shape of shape_type=line must have 2 points"
        draw.line(xy=xy, fill=1, width=line_width)
    elif shape_type == "linestrip":
        # 线条带：需要多个点连接成线
        draw.line(xy=xy, fill=1, width=line_width)
    elif shape_type == "point":
        # 点：需要1个点
        assert len(xy) == 1, "Shape of shape_type=point must have 1 points"
        cx, cy = xy[0]
        r = point_size
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=1, fill=1)
    elif shape_type in [None, "polygon"]:
        # 多边形：需要至少3个点
        assert len(xy) > 2, "Polygon must have points more than 2"
        draw.polygon(xy=xy, outline=1, fill=1)
    else:
        raise ValueError(f"shape_type={shape_type!r} is not supported.")
    
    return np.array(mask, dtype=bool)


def shapes_to_label(img_shape, shapes, label_name_to_value):
    """
    将形状列表转换为标签数组
    
    将多个形状转换为两个标签数组：
    1. 类别标签数组（每个像素的类别ID）
    2. 实例标签数组（每个像素的实例ID）
    
    Args:
        img_shape: 图像形状 (height, width, channels)
        shapes: 形状列表，每个形状包含points、label、group_id等信息
        label_name_to_value: 标签名称到数值的映射字典
        
    Returns:
        tuple: (类别标签数组, 实例标签数组)
    """
    # 初始化标签数组
    cls = np.zeros(img_shape[:2], dtype=np.int32)  # 类别标签
    ins = np.zeros_like(cls)                       # 实例标签
    instances = []                                 # 实例列表
    
    for shape in shapes:
        points = shape["points"]
        label = shape["label"]
        group_id = shape.get("group_id")
        if group_id is None:
            group_id = uuid.uuid1()  # 生成唯一ID
        shape_type = shape.get("shape_type", None)

        cls_name = label
        instance = (cls_name, group_id)

        # 记录新的实例
        if instance not in instances:
            instances.append(instance)
        ins_id = instances.index(instance) + 1
        cls_id = label_name_to_value[cls_name]

        mask: npt.NDArray[np.bool_]
        if shape_type == "mask":
            # 掩码类型：直接使用提供的掩码数据
            if not isinstance(shape["mask"], np.ndarray):
                raise ValueError("shape['mask'] must be numpy.ndarray")
            mask = np.zeros(img_shape[:2], dtype=bool)
            (x1, y1), (x2, y2) = np.asarray(points).astype(int)
            mask[y1 : y2 + 1, x1 : x2 + 1] = shape["mask"]
        else:
            # 其他类型：通过形状生成掩码
            mask = shape_to_mask(img_shape[:2], points, shape_type)

        # 填充标签数组
        cls[mask] = cls_id
        ins[mask] = ins_id

    return cls, ins


def labelme_shapes_to_label(img_shape, shapes):
    """
    将Labelme形状转换为标签（已废弃）
    
    注意：此函数已废弃，请使用shapes_to_label函数。
    
    Args:
        img_shape: 图像形状
        shapes: Labelme格式的形状列表
        
    Returns:
        tuple: (标签数组, 标签名称到数值的映射)
    """
    logger.warning(
        "labelme_shapes_to_label is deprecated, so please use " "shapes_to_label."
    )

    # 构建标签名称到数值的映射
    label_name_to_value = {"_background_": 0}
    for shape in shapes:
        label_name = shape["label"]
        if label_name in label_name_to_value:
            label_value = label_name_to_value[label_name]
        else:
            label_value = len(label_name_to_value)
            label_name_to_value[label_name] = label_value

    lbl, _ = shapes_to_label(img_shape, shapes, label_name_to_value)
    return lbl, label_name_to_value


def masks_to_bboxes(masks):
    """
    将掩码数组转换为边界框
    
    将多个二值掩码转换为对应的边界框坐标。
    
    Args:
        masks: 掩码数组，形状为(N, height, width)，N为掩码数量
        
    Returns:
        numpy.ndarray: 边界框数组，形状为(N, 4)，每行格式为(y1, x1, y2, x2)
        
    Raises:
        ValueError: 当输入维度或数据类型不正确时
    """
    if masks.ndim != 3:
        raise ValueError("masks.ndim must be 3, but it is {}".format(masks.ndim))
    if masks.dtype != bool:
        raise ValueError(
            "masks.dtype must be bool type, but it is {}".format(masks.dtype)
        )
    
    bboxes = []
    for mask in masks:
        # 找到掩码中所有非零像素的位置
        where = np.argwhere(mask)
        # 计算边界框坐标
        (y1, x1), (y2, x2) = where.min(0), where.max(0) + 1
        bboxes.append((y1, x1, y2, x2))
    
    bboxes = np.asarray(bboxes, dtype=np.float32)
    return bboxes
