import json
import time

import numpy as np
import numpy.typing as npt
from loguru import logger

try:
    import osam
except ImportError:
    osam = None

# 文件头部说明:
# 本模块是Labelme自动化标注模块，用于从文本提示生成边界框标注。
# 主要功能包括：调用AI模型生成边界框、非极大值抑制（NMS）处理、
# 将边界框转换为Labelme形状格式等。
# 这是AI辅助标注功能的核心实现，支持基于文本提示的自动目标检测。

def get_bboxes_from_texts(
    model: str, image: np.ndarray, texts: list[str]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    从文本提示生成边界框
    
    调用OSAM模型，根据文本提示在图像中检测目标并生成边界框。
    如果osam模块不可用，则返回空数组。
    
    Args:
        model: AI模型名称
        image: 输入图像数组
        texts: 文本提示列表
        
    Returns:
        tuple: (边界框数组, 置信度分数数组, 标签数组)
    """
    if osam is None:
        logger.warning("osam module not available, skipping bbox generation")
        return np.empty((0, 4), dtype=np.float32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.int32)
    
    # 图像数据验证和预处理
    if image is None or image.size == 0:
        logger.warning("Invalid image data: empty or None")
        return np.empty((0, 4), dtype=np.float32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.int32)
    
    # 检查图像形状，确保至少是2D
    if len(image.shape) < 2:
        logger.warning(f"Invalid image shape: {image.shape}")
        return np.empty((0, 4), dtype=np.float32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.int32)
    
    # 如果图像是单通道且形状为(1, 1, 1)，转换为(1, 1)
    if len(image.shape) == 3 and image.shape[2] == 1 and image.shape[0] == 1 and image.shape[1] == 1:
        image = image.squeeze()
    
    # 如果图像是单通道，转换为RGB格式
    if len(image.shape) == 2:
        image = np.stack([image, image, image], axis=-1)
    
    # 确保图像是3通道RGB格式
    if len(image.shape) == 3 and image.shape[2] == 1:
        image = np.repeat(image, 3, axis=2)
    
    # 检查图像尺寸，确保足够大
    if image.shape[0] < 10 or image.shape[1] < 10:
        logger.warning(f"Image too small for processing: {image.shape}")
        return np.empty((0, 4), dtype=np.float32), np.empty((0,), dtype=np.float32), np.empty((0,), dtype=np.int32)
    
    # 确保数据类型正确
    if image.dtype != np.uint8:
        image = image.astype(np.uint8)
    
    logger.debug(f"Processed image shape: {image.shape}, dtype: {image.dtype}")
    
    # 构建生成请求
    request: osam.types.GenerateRequest = osam.types.GenerateRequest(
        model=model,
        image=image,
        prompt=osam.types.Prompt(
            texts=texts,              # 文本提示
            iou_threshold=1.0,        # IoU阈值
            score_threshold=0.01,     # 分数阈值
            max_annotations=1000,     # 最大标注数量
        ),
    )
    
    # 记录调试信息
    logger.debug(
        f"Requesting with model={model!r}, image={(image.shape, image.dtype)}, "
        f"prompt={request.prompt!r}"
    )
    
    # 记录请求开始时间
    t_start: float = time.time()
    
    # 调用AI模型生成标注
    response: osam.types.GenerateResponse = osam.apis.generate(request=request)

    num_annotations: int = len(response.annotations)
    logger.debug(
        f"Response: num_annotations={num_annotations}, "
        f"elapsed_time={time.time() - t_start:.3f} [s]"
    )

    # 初始化输出数组
    boxes: npt.NDArray[np.float32] = np.empty((num_annotations, 4), dtype=np.float32)
    scores: npt.NDArray[np.float32] = np.empty((num_annotations,), dtype=np.float32)
    labels: npt.NDArray[np.float32] = np.empty((num_annotations,), dtype=np.int32)
    
    # 解析模型响应
    for i, annotation in enumerate(response.annotations):
        boxes[i] = [
            annotation.bounding_box.xmin,  # 左上角x坐标
            annotation.bounding_box.ymin,  # 左上角y坐标
            annotation.bounding_box.xmax,  # 右下角x坐标
            annotation.bounding_box.ymax,  # 右下角y坐标
        ]
        scores[i] = annotation.score      # 置信度分数
        labels[i] = texts.index(annotation.text)  # 标签索引

    return boxes, scores, labels


def nms_bboxes(
    boxes: np.ndarray,
    scores: np.ndarray,
    labels: np.ndarray,
    iou_threshold: float,
    score_threshold: float,
    max_num_detections: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    对边界框进行非极大值抑制（NMS）
    
    过滤重叠的边界框，保留置信度最高的检测结果。
    如果osam模块不可用，则返回原始数据。
    
    Args:
        boxes: 边界框数组
        scores: 置信度分数数组
        labels: 标签数组
        iou_threshold: IoU阈值
        score_threshold: 分数阈值
        max_num_detections: 最大检测数量
        
    Returns:
        tuple: (过滤后的边界框, 过滤后的分数, 过滤后的标签)
    """
    if osam is None:
        logger.warning("osam module not available, skipping NMS processing")
        return boxes, scores, labels
    
    # 计算类别数量
    num_classes: int = max(labels) + 1
    
    # 创建多类别分数数组
    scores_of_all_classes: npt.NDArray[np.float32] = np.zeros(
        (len(boxes), num_classes), dtype=np.float32
    )
    
    # 填充分数数组
    for i, (score, label) in enumerate(zip(scores, labels)):
        scores_of_all_classes[i, label] = score
    
    logger.debug(f"Input: num_boxes={len(boxes)}")
    
    # 调用NMS算法
    boxes, scores, labels = osam.apis.non_maximum_suppression(
        boxes=boxes,
        scores=scores_of_all_classes,
        iou_threshold=iou_threshold,
        score_threshold=score_threshold,
        max_num_detections=max_num_detections,
    )
    
    logger.debug(f"Output: num_boxes={len(boxes)}")
    return boxes, scores, labels


def get_shapes_from_bboxes(
    boxes: np.ndarray, scores: np.ndarray, labels: np.ndarray, texts: list[str]
) -> list[dict]:
    """
    将边界框转换为Labelme形状格式
    
    将AI模型生成的边界框转换为Labelme标准的形状数据格式。
    
    Args:
        boxes: 边界框数组
        scores: 置信度分数数组
        labels: 标签数组
        texts: 文本提示列表
        
    Returns:
        list: Labelme形状数据列表
    """
    shapes: list[dict] = []
    
    # 遍历每个检测结果
    for box, score, label in zip(boxes.tolist(), scores.tolist(), labels.tolist()):
        text: str = texts[label]
        xmin, ymin, xmax, ymax = box
        
        # 创建Labelme形状数据
        shape: dict = {
            "label": text,                    # 标签文本
            "points": [[xmin, ymin], [xmax, ymax]],  # 矩形顶点
            "group_id": None,                 # 组ID
            "shape_type": "rectangle",        # 形状类型
            "flags": {},                      # 标志字典
            "description": json.dumps(dict(score=score, text=text)),  # 描述信息
        }
        shapes.append(shape)
    
    return shapes
