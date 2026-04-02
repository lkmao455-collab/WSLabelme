import copy

import numpy as np
import skimage.measure
from loguru import logger
from PyQt5 import QtCore
from PyQt5 import QtGui

import labelme.utils

# TODO(unknown):
# - [opt] Store paths instead of creating new ones at each paint.

# 文件头部说明:
# 本模块定义了Shape类，这是Labelme中所有标注形状的基础类。
# 支持多种形状类型：多边形、矩形、圆形、线条、点、线条带、点集、掩码等。
# 负责形状的绘制、编辑、顶点管理、边界检测等核心功能。

class Shape(object):
    """
    标注形状基类
    
    这是Labelme中所有标注形状的基础类，支持多种形状类型：
    - 多边形 (polygon): 任意多边形
    - 矩形 (rectangle): 矩形框
    - 圆形 (circle): 圆形标注
    - 线条 (line): 单线条
    - 点 (point): 单个点
    - 线条带 (linestrip): 连续线条
    - 点集 (points): 多个点的集合
    - 掩码 (mask): 像素级掩码标注
    
    主要功能：
    - 形状的创建和编辑
    - 顶点的添加、删除、移动
    - 形状的绘制和渲染
    - 边界检测和包含点检测
    - 形状的复制和变换
    """
    # Render handles as squares
    P_SQUARE = 0

    # Render handles as circles
    P_ROUND = 1

    # Flag for the handles we would move if dragging
    MOVE_VERTEX = 0

    # Flag for all other handles on the current shape
    NEAR_VERTEX = 1

    PEN_WIDTH = 2

    # The following class variables influence the drawing of all shape objects.
    line_color = None
    fill_color = None
    select_line_color = None
    select_fill_color = None
    vertex_fill_color = None
    hvertex_fill_color = None
    point_type = P_ROUND
    point_size = 8
    scale = 1.0

    def __init__(
        self,
        label=None,
        line_color=None,
        shape_type=None,
        flags=None,
        group_id=None,
        description=None,
        mask=None,
    ):
        """
        初始化Shape对象
        
        Args:
            label: 标签文本
            line_color: 线条颜色（可选，用于覆盖类级别的线条颜色）
            shape_type: 形状类型（polygon, rectangle, circle, line, point, linestrip, points, mask）
            flags: 标志位字典
            group_id: 组ID，用于将多个形状分组
            description: 描述信息
            mask: 掩码数据（用于mask类型形状）
        """
        self.label = label
        self.group_id = group_id
        self.points = []
        self.point_labels = []
        self.shape_type = shape_type
        self._shape_raw = None
        self._points_raw = []
        self._shape_type_raw = None
        self.fill = False
        self.selected = False
        self.flags = flags
        self.description = description
        self.other_data = {}
        self.mask = mask

        # 高亮相关属性
        self._highlightIndex = None  # 当前高亮的顶点索引
        self._highlightMode = self.NEAR_VERTEX  # 高亮模式
        # 高亮设置：NEAR_VERTEX模式放大4倍圆形，MOVE_VERTEX模式放大1.5倍方形
        self._highlightSettings = {
            self.NEAR_VERTEX: (4, self.P_ROUND),
            self.MOVE_VERTEX: (1.5, self.P_SQUARE),
        }

        self._closed = False  # 形状是否闭合

        if line_color is not None:
            # 覆盖类级别的线条颜色属性
            # 使用对象级别的属性。目前这用于绘制待定线条的不同颜色。
            self.line_color = line_color

    def _scale_point(self, point: QtCore.QPointF) -> QtCore.QPointF:
        """
        缩放点坐标
        
        根据当前的缩放比例对点坐标进行缩放，用于在不同缩放级别下正确显示形状。
        
        Args:
            point: 要缩放的QPointF对象
            
        Returns:
            QtCore.QPointF: 缩放后的点坐标
        """
        return QtCore.QPointF(point.x() * self.scale, point.y() * self.scale)

    def setShapeRefined(self, shape_type, points, point_labels, mask=None):
        """
        设置精炼后的形状数据
        
        保存当前形状的原始状态，然后设置新的形状类型、顶点和标签。
        用于形状的精炼和优化过程。
        
        Args:
            shape_type: 新的形状类型
            points: 新的顶点列表
            point_labels: 新的顶点标签列表
            mask: 新的掩码数据（可选）
        """
        self._shape_raw = (self.shape_type, self.points, self.point_labels)
        self.shape_type = shape_type
        self.points = points
        self.point_labels = point_labels
        self.mask = mask

    def restoreShapeRaw(self):
        """
        恢复原始形状数据
        
        如果存在原始形状数据，则恢复到原始状态，丢弃精炼后的修改。
        用于撤销形状精炼操作。
        """
        if self._shape_raw is None:
            return
        self.shape_type, self.points, self.point_labels = self._shape_raw
        self._shape_raw = None

    @property
    def shape_type(self):
        """
        获取形状类型属性
        
        Returns:
            str: 当前形状类型
        """
        return self._shape_type

    @shape_type.setter
    def shape_type(self, value):
        """
        设置形状类型属性
        
        验证并设置形状类型，支持的类型包括：
        polygon, rectangle, point, line, circle, linestrip, points, mask
        
        Args:
            value: 要设置的形状类型
            
        Raises:
            ValueError: 当形状类型不支持时抛出异常
        """
        if value is None:
            value = "polygon"
        if value not in [
            "polygon",
            "rectangle",
            "point",
            "line",
            "circle",
            "linestrip",
            "points",
            "mask",
        ]:
            raise ValueError("Unexpected shape_type: {}".format(value))
        self._shape_type = value

    def close(self):
        """
        关闭形状
        
        将形状标记为闭合状态，用于多边形等需要闭合的形状类型。
        """
        self._closed = True

    def addPoint(self, point, label=1):
        """
        添加顶点到形状
        
        向形状添加一个新的顶点。如果添加的点与第一个点相同，则自动关闭形状。
        
        Args:
            point: 要添加的QPointF对象
            label: 顶点标签，默认为1（正样本）
        """
        if self.points and point == self.points[0]:
            self.close()
        else:
            self.points.append(point)
            self.point_labels.append(label)

    def canAddPoint(self):
        """
        检查是否可以添加顶点
        
        只有在多边形和线条带模式下才允许添加顶点。
        
        Returns:
            bool: 如果可以添加顶点返回True，否则返回False
        """
        return self.shape_type in ["polygon", "linestrip"]

    def popPoint(self):
        """
        移除最后一个顶点
        
        移除并返回形状的最后一个顶点，同时移除对应的标签。
        
        Returns:
            QtCore.QPointF: 被移除的顶点，如果没有顶点则返回None
        """
        if self.points:
            if self.point_labels:
                self.point_labels.pop()
            return self.points.pop()
        return None

    def insertPoint(self, i, point, label=1):
        """
        在指定位置插入顶点
        
        在形状的指定索引位置插入一个新的顶点。
        
        Args:
            i: 插入位置的索引
            point: 要插入的QPointF对象
            label: 顶点标签，默认为1
        """
        self.points.insert(i, point)
        self.point_labels.insert(i, label)

    def removePoint(self, i):
        """
        移除指定索引的顶点
        
        从形状中移除指定索引位置的顶点。对于多边形，至少需要3个顶点；
        对于线条带，至少需要2个顶点。
        
        Args:
            i: 要移除的顶点索引
            
        Returns:
            bool: 移除成功返回True，失败返回False
        """
        if not self.canAddPoint():
            logger.warning(
                "Cannot remove point from: shape_type=%r",
                self.shape_type,
            )
            return

        if self.shape_type == "polygon" and len(self.points) <= 3:
            logger.warning(
                "Cannot remove point from: shape_type=%r, len(points)=%d",
                self.shape_type,
                len(self.points),
            )
            return

        if self.shape_type == "linestrip" and len(self.points) <= 2:
            logger.warning(
                "Cannot remove point from: shape_type=%r, len(points)=%d",
                self.shape_type,
                len(self.points),
            )
            return

        self.points.pop(i)
        self.point_labels.pop(i)

    def isClosed(self):
        """
        检查形状是否闭合
        
        Returns:
            bool: 如果形状已闭合返回True，否则返回False
        """
        return self._closed

    def setOpen(self):
        """
        设置形状为开放状态
        
        将形状标记为未闭合状态，允许继续添加顶点。
        """
        self._closed = False

    def paint(self, painter):
        """
        绘制形状
        
        根据形状类型和状态在画布上绘制形状。支持多种形状类型的绘制：
        掩码、矩形、圆形、线条带、点集、多边形等。
        
        Args:
            painter: QPainter对象，用于绘制形状
        """
        if self.mask is None and not self.points:
            return

        color = self.select_line_color if self.selected else self.line_color
        pen = QtGui.QPen(color)
        # Try using integer sizes for smoother drawing(?)
        pen.setWidth(self.PEN_WIDTH)
        painter.setPen(pen)

        if self.mask is not None:
            # 绘制掩码形状
            image_to_draw = np.zeros(self.mask.shape + (4,), dtype=np.uint8)
            fill_color = (
                self.select_fill_color.getRgb()
                if self.selected
                else self.fill_color.getRgb()
            )
            image_to_draw[self.mask] = fill_color
            qimage = QtGui.QImage.fromData(labelme.utils.img_arr_to_data(image_to_draw))
            qimage = qimage.scaled(
                qimage.size() * self.scale,
                QtCore.Qt.IgnoreAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )

            painter.drawImage(self._scale_point(point=self.points[0]), qimage)

            line_path = QtGui.QPainterPath()
            contours = skimage.measure.find_contours(np.pad(self.mask, pad_width=1))
            for contour in contours:
                contour += [self.points[0].y(), self.points[0].x()]
                line_path.moveTo(
                    self._scale_point(QtCore.QPointF(contour[0, 1], contour[0, 0]))
                )
                for point in contour[1:]:
                    line_path.lineTo(
                        self._scale_point(QtCore.QPointF(point[1], point[0]))
                    )
            painter.drawPath(line_path)

        if self.points:
            # 绘制基于顶点的形状
            line_path = QtGui.QPainterPath()
            vrtx_path = QtGui.QPainterPath()
            negative_vrtx_path = QtGui.QPainterPath()

            if self.shape_type in ["rectangle", "mask"]:
                # 绘制矩形或掩码
                assert len(self.points) in [1, 2]
                if len(self.points) == 2:
                    rectangle = QtCore.QRectF(
                        self._scale_point(self.points[0]),
                        self._scale_point(self.points[1]),
                    )
                    line_path.addRect(rectangle)
                if self.shape_type == "rectangle":
                    for i in range(len(self.points)):
                        self.drawVertex(vrtx_path, i)
            elif self.shape_type == "circle":
                # 绘制圆形
                assert len(self.points) in [1, 2]
                if len(self.points) == 2:
                    raidus = labelme.utils.distance(
                        self._scale_point(self.points[0] - self.points[1])
                    )
                    line_path.addEllipse(
                        self._scale_point(self.points[0]), raidus, raidus
                    )
                for i in range(len(self.points)):
                    self.drawVertex(vrtx_path, i)
            elif self.shape_type == "linestrip":
                # 绘制线条带
                line_path.moveTo(self._scale_point(self.points[0]))
                for i, p in enumerate(self.points):
                    line_path.lineTo(self._scale_point(p))
                    self.drawVertex(vrtx_path, i)
            elif self.shape_type == "points":
                # 绘制点集
                assert len(self.points) == len(self.point_labels)
                for i, point_label in enumerate(self.point_labels):
                    if point_label == 1:
                        self.drawVertex(vrtx_path, i)
                    else:
                        self.drawVertex(negative_vrtx_path, i)
            else:
                # 绘制多边形
                line_path.moveTo(self._scale_point(self.points[0]))
                # Uncommenting the following line will draw 2 paths
                # for the 1st vertex, and make it non-filled, which
                # may be desirable.
                # self.drawVertex(vrtx_path, 0)

                for i, p in enumerate(self.points):
                    line_path.lineTo(self._scale_point(p))
                    self.drawVertex(vrtx_path, i)
                if self.isClosed():
                    line_path.lineTo(self._scale_point(self.points[0]))

            painter.drawPath(line_path)
            if vrtx_path.length() > 0:
                painter.drawPath(vrtx_path)
                painter.fillPath(vrtx_path, self._vertex_fill_color)
            if self.fill and self.mask is None:
                color = self.select_fill_color if self.selected else self.fill_color
                painter.fillPath(line_path, color)

            pen.setColor(QtGui.QColor(255, 0, 0, 255))
            painter.setPen(pen)
            painter.drawPath(negative_vrtx_path)
            painter.fillPath(negative_vrtx_path, QtGui.QColor(255, 0, 0, 255))

    def drawVertex(self, path, i):
        """
        绘制顶点
        
        在指定的路径上绘制形状的顶点。根据顶点是否被高亮显示来调整大小和形状。
        
        Args:
            path: QPainterPath对象，用于绘制顶点
            i: 顶点索引
        """
        d = self.point_size
        shape = self.point_type
        point = self._scale_point(self.points[i])
        if i == self._highlightIndex:
            size, shape = self._highlightSettings[self._highlightMode]
            d *= size
        if self._highlightIndex is not None:
            self._vertex_fill_color = self.hvertex_fill_color
        else:
            self._vertex_fill_color = self.vertex_fill_color
        if shape == self.P_SQUARE:
            path.addRect(point.x() - d / 2, point.y() - d / 2, d, d)
        elif shape == self.P_ROUND:
            path.addEllipse(point, d / 2.0, d / 2.0)
        else:
            assert False, "unsupported vertex shape"

    def nearestVertex(self, point, epsilon):
        """
        查找最近的顶点
        
        在给定的容差范围内查找距离指定点最近的顶点。
        
        Args:
            point: 要查找的QPointF对象
            epsilon: 查找容差范围
            
        Returns:
            int: 最近顶点的索引，如果没有找到返回None
        """
        min_distance = float("inf")
        min_i = None
        point = QtCore.QPointF(point.x() * self.scale, point.y() * self.scale)
        for i, p in enumerate(self.points):
            p = QtCore.QPointF(p.x() * self.scale, p.y() * self.scale)
            dist = labelme.utils.distance(p - point)
            if dist <= epsilon and dist < min_distance:
                min_distance = dist
                min_i = i
        return min_i

    def nearestEdge(self, point, epsilon):
        """
        查找最近的边
        
        在给定的容差范围内查找距离指定点最近的边。
        
        Args:
            point: 要查找的QPointF对象
            epsilon: 查找容差范围
            
        Returns:
            int: 最近边的后一个顶点索引，如果没有找到返回None
        """
        min_distance = float("inf")
        post_i = None
        point = QtCore.QPointF(point.x() * self.scale, point.y() * self.scale)
        for i in range(len(self.points)):
            start = self.points[i - 1]
            end = self.points[i]
            start = QtCore.QPointF(start.x() * self.scale, start.y() * self.scale)
            end = QtCore.QPointF(end.x() * self.scale, end.y() * self.scale)
            line = [start, end]
            dist = labelme.utils.distancetoline(point, line)
            if dist <= epsilon and dist < min_distance:
                min_distance = dist
                post_i = i
        return post_i

    def containsPoint(self, point):
        """
        检查点是否在形状内部
        
        判断指定的点是否位于形状的内部。对于掩码类型，直接检查掩码数组；
        对于其他类型，使用路径的contains方法。
        
        Args:
            point: 要检查的QPointF对象
            
        Returns:
            bool: 如果点在形状内部返回True，否则返回False
        """
        if self.mask is not None:
            y = np.clip(
                int(round(point.y() - self.points[0].y())),
                0,
                self.mask.shape[0] - 1,
            )
            x = np.clip(
                int(round(point.x() - self.points[0].x())),
                0,
                self.mask.shape[1] - 1,
            )
            return self.mask[y, x]
        return self.makePath().contains(point)

    def makePath(self):
        """
        创建形状的路径对象
        
        根据形状类型创建对应的QPainterPath对象，用于绘制和边界检测。
        
        Returns:
            QtGui.QPainterPath: 形状的路径对象
        """
        if self.shape_type in ["rectangle", "mask"]:
            path = QtGui.QPainterPath()
            if len(self.points) == 2:
                path.addRect(QtCore.QRectF(self.points[0], self.points[1]))
        elif self.shape_type == "circle":
            path = QtGui.QPainterPath()
            if len(self.points) == 2:
                raidus = labelme.utils.distance(self.points[0] - self.points[1])
                path.addEllipse(self.points[0], raidus, raidus)
        else:
            path = QtGui.QPainterPath(self.points[0])
            for p in self.points[1:]:
                path.lineTo(p)
        return path

    def boundingRect(self):
        """
        获取形状的边界矩形
        
        计算并返回包含整个形状的最小边界矩形。
        
        Returns:
            QtCore.QRectF: 边界矩形
        """
        return self.makePath().boundingRect()

    def moveBy(self, offset):
        """
        移动整个形状
        
        将形状的所有顶点按照指定的偏移量进行移动。
        
        Args:
            offset: 偏移量QPointF对象
        """
        self.points = [p + offset for p in self.points]

    def moveVertexBy(self, i, offset):
        """
        移动指定的顶点
        
        将形状的指定索引位置的顶点按照指定的偏移量进行移动。
        
        Args:
            i: 顶点索引
            offset: 偏移量QPointF对象
        """
        self.points[i] = self.points[i] + offset

    def highlightVertex(self, i, action):
        """
        高亮指定的顶点
        
        根据指定的动作模式高亮显示形状的某个顶点。
        
        Args:
            i (int): 顶点索引
            action (int): 动作类型（NEAR_VERTEX或MOVE_VERTEX）
        """
        self._highlightIndex = i
        self._highlightMode = action

    def highlightClear(self):
        """
        清除顶点高亮状态
        
        清除当前高亮显示的顶点，恢复到正常状态。
        """
        self._highlightIndex = None

    def copy(self):
        """
        复制形状对象
        
        创建当前形状对象的深拷贝。
        
        Returns:
            Shape: 形状对象的副本
        """
        return copy.deepcopy(self)

    def __len__(self):
        """
        获取形状的顶点数量
        
        Returns:
            int: 顶点数量
        """
        return len(self.points)

    def __getitem__(self, key):
        """
        获取指定索引的顶点
        
        Args:
            key: 顶点索引
            
        Returns:
            QtCore.QPointF: 指定索引的顶点
        """
        return self.points[key]

    def __setitem__(self, key, value):
        """
        设置指定索引的顶点
        
        Args:
            key: 顶点索引
            value: 新的顶点QPointF对象
        """
        self.points[key] = value
