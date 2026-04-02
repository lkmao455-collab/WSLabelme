import collections
from typing import Optional

import imgviz
from loguru import logger
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

try:
    import osam
except ImportError:
    osam = None

import numpy as np
from labelme._automation import polygon_from_mask
import labelme.utils
from labelme.shape import Shape

# TODO(unknown):
# - [maybe] Find optimal epsilon value.

# 文件头部说明:
# 本模块定义了Canvas类，这是Labelme中负责绘图和交互的核心组件。
# 提供了完整的绘图功能，包括多边形、矩形、圆形、线条、点、线条带、
# AI多边形、AI掩码等多种形状的创建和编辑功能。
# 支持鼠标交互、键盘操作、形状选择、移动、编辑等核心功能。

# 光标定义常量
CURSOR_DEFAULT = QtCore.Qt.ArrowCursor  # 默认光标
CURSOR_POINT = QtCore.Qt.PointingHandCursor  # 指向手型光标
CURSOR_DRAW = QtCore.Qt.CrossCursor  # 绘图十字光标
CURSOR_MOVE = QtCore.Qt.ClosedHandCursor  # 移动握紧手型光标
CURSOR_GRAB = QtCore.Qt.OpenHandCursor  # 抓取张开手型光标

MOVE_SPEED = 5.0  # 键盘移动速度


class Canvas(QtWidgets.QWidget):
    """
    画布组件类
    
    这是Labelme中负责绘图和交互的核心组件，继承自QtWidgets.QWidget。
    提供了完整的绘图功能和用户交互处理，支持多种形状类型的创建和编辑。
    
    主要功能：
    - 多种形状的创建和编辑（多边形、矩形、圆形、线条、点、线条带、AI形状）
    - 鼠标交互处理（点击、拖拽、双击等）
    - 键盘快捷键支持
    - 形状选择、移动、缩放、删除等操作
    - 撤销/重做功能
    - AI辅助标注功能
    - 缩放和平移功能
    """
    zoomRequest = QtCore.pyqtSignal(int, QtCore.QPoint)
    scrollRequest = QtCore.pyqtSignal(int, int)
    newShape = QtCore.pyqtSignal()
    selectionChanged = QtCore.pyqtSignal(list)
    shapeMoved = QtCore.pyqtSignal()
    drawingPolygon = QtCore.pyqtSignal(bool)
    vertexSelected = QtCore.pyqtSignal(bool)
    mouseMoved = QtCore.pyqtSignal(QtCore.QPointF)

    CREATE, EDIT = 0, 1

    # polygon, rectangle, line, or point
    _createMode = "polygon"

    _fill_drawing = False

    def __init__(self, *args, **kwargs):
        """
        初始化Canvas对象
        
        设置画布的各种参数和状态，包括绘图模式、光标样式、形状管理等。
        
        Args:
            *args: 父类构造参数
            **kwargs: 关键字参数，包括：
                - epsilon: 顶点选择容差，默认10.0
                - double_click: 双击行为，默认"close"
                - num_backups: 撤销备份数量，默认10
                - crosshair: 十字准星配置字典
        """
        # 提取并设置各种参数
        self.epsilon = kwargs.pop("epsilon", 10.0)  # 顶点选择容差
        self.double_click = kwargs.pop("double_click", "close")  # 双击行为
        if self.double_click not in [None, "close"]:
            raise ValueError(
                "Unexpected value for double_click event: {}".format(self.double_click)
            )
        self.num_backups = kwargs.pop("num_backups", 10)  # 撤销备份数量
        self._crosshair = kwargs.pop(
            "crosshair",
            {
                "polygon": False,      # 多边形模式是否显示十字准星
                "rectangle": True,     # 矩形模式是否显示十字准星
                "circle": False,       # 圆形模式是否显示十字准星
                "line": False,         # 线条模式是否显示十字准星
                "point": False,        # 点模式是否显示十字准星
                "linestrip": False,    # 线条带模式是否显示十字准星
                "ai_polygon": False,   # AI多边形模式是否显示十字准星
                "ai_mask": False,      # AI掩码模式是否显示十字准星
            },
        )
        super(Canvas, self).__init__(*args, **kwargs)
        
        # 初始化本地状态
        self.mode = self.EDIT        # 当前模式：编辑或创建
        self.shapes = []             # 所有形状列表
        self.shapesBackups = []      # 形状备份列表（用于撤销）
        self.redoBackups = []        # 形状备份列表（用于重做）
        self.current = None          # 当前正在创建的形状
        self.selectedShapes = []     # 选中的形状列表
        self.selectedShapesCopy = [] # 选中形状的副本（用于移动）
        
        # self.line代表：
        #   - createMode == 'polygon': 从最后一点到当前点的边
        #   - createMode == 'rectangle': 矩形的对角线
        #   - createMode == 'line': 线条
        #   - createMode == 'point': 点
        self.line = Shape()
        self.prevPoint = QtCore.QPoint()        # 上一个鼠标位置
        self.prevMovePoint = QtCore.QPoint()    # 上一个移动位置
        self.offsets = QtCore.QPoint(), QtCore.QPoint()  # 选中形状的偏移量
        self.scale = 1.0                        # 缩放比例
        self.pixmap = QtGui.QPixmap()           # 图像数据
        self.visible = {}                       # 形状可见性字典
        self._hideBackround = False             # 是否隐藏背景
        self.hideBackround = False              # 隐藏背景标志
        self.hShape = None                      # 高亮的形状
        self.prevhShape = None                  # 之前的高亮形状
        self.hVertex = None                     # 高亮的顶点
        self.prevhVertex = None                 # 之前的高亮顶点
        self.hEdge = None                       # 高亮的边
        self.prevhEdge = None                   # 之前的高亮边
        self.movingShape = False                # 是否正在移动形状
        self.snapping = True                    # 是否启用吸附功能
        self.hShapeIsSelected = False           # 高亮形状是否被选中
        self._painter = QtGui.QPainter()        # 绘图画家对象
        self._cursor = CURSOR_DEFAULT           # 当前光标样式
        
        # 菜单：0-无选择时的右键菜单，1-有选择时的右键菜单
        self.menus = (QtWidgets.QMenu(), QtWidgets.QMenu())
        
        # 设置组件选项
        self.setMouseTracking(True)             # 启用鼠标跟踪
        self.setFocusPolicy(QtCore.Qt.WheelFocus)  # 设置焦点策略

        # AI模型相关
        self._sam: Optional[osam.types.Model] = None  # SAM模型实例
        self._sam_embedding: collections.OrderedDict[
            bytes, osam.types.ImageEmbedding
        ] = collections.OrderedDict()  # 图像嵌入缓存

    def fillDrawing(self):
        return self._fill_drawing

    def setFillDrawing(self, value):
        self._fill_drawing = value

    @property
    def createMode(self):
        return self._createMode

    @createMode.setter
    def createMode(self, value):
        if value not in [
            "polygon",
            "rectangle",
            "circle",
            "line",
            "point",
            "linestrip",
            "ai_polygon",
            "ai_mask",
        ]:
            raise ValueError("Unsupported createMode: %s" % value)
        self._createMode = value

    def _compute_and_cache_image_embedding(self) -> None:
        """
        计算并缓存图像嵌入
        
        为当前图像计算SAM模型的嵌入向量，并缓存以避免重复计算。
        嵌入向量用于AI辅助标注功能，可以显著提高标注效率。
        """
        if self._sam is None:
            logger.warning("SAM model is not set yet")
            return

        sam: osam.types.Model = self._sam

        # 将Qt图像转换为numpy数组
        image: np.ndarray = labelme.utils.img_qt_to_arr(self.pixmap.toImage())
        # 检查是否已缓存该图像的嵌入
        if image.tobytes() in self._sam_embedding:
            return

        logger.debug("Computing image embeddings for model {!r}", sam.name)
        # 计算图像嵌入并缓存
        self._sam_embedding[image.tobytes()] = sam.encode_image(
            image=imgviz.asrgb(image)
        )

    def initializeAiModel(self, model_name):
        """
        初始化AI模型
        
        设置指定名称的AI模型，并清空之前的图像嵌入缓存。
        如果模型名称与当前模型不同，则重新初始化模型。
        
        Args:
            model_name: AI模型名称
        """
        if self.pixmap is None:
            logger.warning("Pixmap is not set yet")
            return

        # 如果模型不存在或模型名称不同，则重新初始化
        if self._sam is None or self._sam.name != model_name:
            logger.debug("Initializing AI model {!r}", model_name)
            self._sam = osam.apis.get_model_type_by_name(model_name)()
            self._sam_embedding.clear()  # 清空之前的缓存

        # 计算并缓存当前图像的嵌入
        self._compute_and_cache_image_embedding()

    def storeShapes(self):
        """
        存储形状备份
        
        创建当前所有形状的副本并存储到备份列表中，用于撤销操作。
        如果备份数量超过限制，则删除最旧的备份。
        """
        shapesBackup = []
        for shape in self.shapes:
            shapesBackup.append(shape.copy())
        # 如果备份数量超过限制，删除最旧的备份
        if len(self.shapesBackups) > self.num_backups:
            self.shapesBackups = self.shapesBackups[-self.num_backups - 1 :]
        self.shapesBackups.append(shapesBackup)
        # 清空重做备份，因为新操作会使之前的重做历史无效
        self.redoBackups.clear()

    @property
    def isShapeRestorable(self):
        """
        检查是否可以恢复形状
        
        判断是否有足够的备份用于撤销操作。
        我们在每次编辑后保存状态（而不是之前），所以要使编辑可撤销，
        我们期望当前状态和之前状态都在撤销栈中。
        
        Returns:
            bool: 如果可以撤销返回True，否则返回False
        """
        # We save the state AFTER each edit (not before) so for an
        # edit to be undoable, we expect the CURRENT and the PREVIOUS state
        # to be in the undo stack.
        if len(self.shapesBackups) < 2:
            return False
        return True

    @property
    def isShapeRedoable(self):
        """
        检查是否可以重做形状
        
        判断是否有重做备份可用于重做操作。
        
        Returns:
            bool: 如果可以重做返回True，否则返回False
        """
        return len(self.redoBackups) > 0

    def restoreShape(self):
        """
        恢复形状
        
        从备份中恢复形状状态，实现撤销功能。
        这只是恢复形状的一部分工作，完整的恢复过程还包括
        app.py::undoShapeEdit和Canvas::loadShapes函数。
        """
        # This does _part_ of the job of restoring shapes.
        # The complete process is also done in app.py::undoShapeEdit
        # and app.py::loadShapes and our own Canvas::loadShapes function.
        if not self.isShapeRestorable:
            return
        # 保存当前状态到重做备份
        currentBackup = []
        for shape in self.shapes:
            currentBackup.append(shape.copy())
        self.redoBackups.append(currentBackup)
        
        self.shapesBackups.pop()  # 删除最新的备份

        # 应用恢复的形状数据
        shapesBackup = self.shapesBackups.pop()
        self.shapes = shapesBackup
        self.selectedShapes = []

    def redoShape(self):
        """
        重做形状
        
        从重做备份中恢复形状状态，实现重做功能。
        """
        if not self.isShapeRedoable:
            return
        # 保存当前状态到撤销备份
        shapesBackup = []
        for shape in self.shapes:
            shapesBackup.append(shape.copy())
        # 如果备份数量超过限制，删除最旧的备份
        if len(self.shapesBackups) > self.num_backups:
            self.shapesBackups = self.shapesBackups[-self.num_backups - 1 :]
        self.shapesBackups.append(shapesBackup)
        
        # 应用重做的形状数据
        shapesBackup = self.redoBackups.pop()
        self.shapes = shapesBackup
        self.selectedShapes = []
        for shape in self.shapes:
            shape.selected = False
        self.update()

    def enterEvent(self, ev):
        self.overrideCursor(self._cursor)

    def leaveEvent(self, ev):
        self.unHighlight()
        self.restoreCursor()

    def focusOutEvent(self, ev):
        self.restoreCursor()

    def isVisible(self, shape):
        return self.visible.get(shape, True)

    def drawing(self):
        return self.mode == self.CREATE

    def editing(self):
        return self.mode == self.EDIT

    def setEditing(self, value=True):
        self.mode = self.EDIT if value else self.CREATE
        if self.mode == self.EDIT:
            # CREATE -> EDIT
            self.repaint()  # clear crosshair
        else:
            # EDIT -> CREATE
            self.unHighlight()
            self.deSelectShape()

    def unHighlight(self):
        if self.hShape:
            self.hShape.highlightClear()
            self.update()
        self.prevhShape = self.hShape
        self.prevhVertex = self.hVertex
        self.prevhEdge = self.hEdge
        self.hShape = self.hVertex = self.hEdge = None

    def selectedVertex(self):
        return self.hVertex is not None

    def selectedEdge(self):
        return self.hEdge is not None

    def mouseMoveEvent(self, ev):
        """Update line with last point and current coordinates."""
        try:
            pos = self.transformPos(ev.localPos())
        except AttributeError:
            return

        self.mouseMoved.emit(pos)

        self.prevMovePoint = pos
        self.restoreCursor()

        is_shift_pressed = ev.modifiers() & QtCore.Qt.ShiftModifier

        # Polygon drawing.
        if self.drawing():
            if self.createMode in ["ai_polygon", "ai_mask"]:
                self.line.shape_type = "points"
            else:
                self.line.shape_type = self.createMode

            self.overrideCursor(CURSOR_DRAW)
            if not self.current:
                self.repaint()  # draw crosshair
                return

            if self.outOfPixmap(pos):
                # Don't allow the user to draw outside the pixmap.
                # Project the point to the pixmap's edges.
                pos = self.intersectionPoint(self.current[-1], pos)
            elif (
                self.snapping
                and len(self.current) > 1
                and self.createMode == "polygon"
                and self.closeEnough(pos, self.current[0])
            ):
                # Attract line to starting point and
                # colorise to alert the user.
                pos = self.current[0]
                self.overrideCursor(CURSOR_POINT)
                self.current.highlightVertex(0, Shape.NEAR_VERTEX)
            if self.createMode in ["polygon", "linestrip"]:
                self.line.points = [self.current[-1], pos]
                self.line.point_labels = [1, 1]
            elif self.createMode in ["ai_polygon", "ai_mask"]:
                self.line.points = [self.current.points[-1], pos]
                self.line.point_labels = [
                    self.current.point_labels[-1],
                    0 if is_shift_pressed else 1,
                ]
            elif self.createMode == "rectangle":
                self.line.points = [self.current[0], pos]
                self.line.point_labels = [1, 1]
                self.line.close()
            elif self.createMode == "circle":
                self.line.points = [self.current[0], pos]
                self.line.point_labels = [1, 1]
                self.line.shape_type = "circle"
            elif self.createMode == "line":
                self.line.points = [self.current[0], pos]
                self.line.point_labels = [1, 1]
                self.line.close()
            elif self.createMode == "point":
                self.line.points = [self.current[0]]
                self.line.point_labels = [1]
                self.line.close()
            assert len(self.line.points) == len(self.line.point_labels)
            self.repaint()
            self.current.highlightClear()
            return

        # Polygon copy moving.
        if QtCore.Qt.RightButton & ev.buttons():
            if self.selectedShapesCopy and self.prevPoint:
                self.overrideCursor(CURSOR_MOVE)
                self.boundedMoveShapes(self.selectedShapesCopy, pos)
                self.repaint()
            elif self.selectedShapes:
                self.selectedShapesCopy = [s.copy() for s in self.selectedShapes]
                self.repaint()
            return

        # Polygon/Vertex moving.
        if QtCore.Qt.LeftButton & ev.buttons():
            if self.selectedVertex():
                self.boundedMoveVertex(pos)
                self.repaint()
                self.movingShape = True
            elif self.selectedShapes and self.prevPoint:
                self.overrideCursor(CURSOR_MOVE)
                self.boundedMoveShapes(self.selectedShapes, pos)
                self.repaint()
                self.movingShape = True
            return

        # Just hovering over the canvas, 2 possibilities:
        # - Highlight shapes
        # - Highlight vertex
        # Update shape/vertex fill and tooltip value accordingly.
        self.setToolTip(self.tr("Image"))
        for shape in reversed([s for s in self.shapes if self.isVisible(s)]):
            # Look for a nearby vertex to highlight. If that fails,
            # check if we happen to be inside a shape.
            index = shape.nearestVertex(pos, self.epsilon)
            index_edge = shape.nearestEdge(pos, self.epsilon)
            if index is not None:
                if self.selectedVertex():
                    self.hShape.highlightClear()
                self.prevhVertex = self.hVertex = index
                self.prevhShape = self.hShape = shape
                self.prevhEdge = self.hEdge
                self.hEdge = None
                shape.highlightVertex(index, shape.MOVE_VERTEX)
                self.overrideCursor(CURSOR_POINT)
                self.setToolTip(
                    self.tr(
                        "Click & Drag to move point\n"
                        "ALT + SHIFT + Click to delete point"
                    )
                )
                self.setStatusTip(self.toolTip())
                self.update()
                break
            elif index_edge is not None and shape.canAddPoint():
                if self.selectedVertex():
                    self.hShape.highlightClear()
                self.prevhVertex = self.hVertex
                self.hVertex = None
                self.prevhShape = self.hShape = shape
                self.prevhEdge = self.hEdge = index_edge
                self.overrideCursor(CURSOR_POINT)
                self.setToolTip(self.tr("ALT + Click to create point"))
                self.setStatusTip(self.toolTip())
                self.update()
                break
            elif shape.containsPoint(pos):
                if self.selectedVertex():
                    self.hShape.highlightClear()
                self.prevhVertex = self.hVertex
                self.hVertex = None
                self.prevhShape = self.hShape = shape
                self.prevhEdge = self.hEdge
                self.hEdge = None
                self.setToolTip(
                    self.tr("Click & drag to move shape '%s'") % shape.label
                )
                self.setStatusTip(self.toolTip())
                self.overrideCursor(CURSOR_GRAB)
                self.update()
                break
        else:  # Nothing found, clear highlights, reset state.
            self.unHighlight()
        self.vertexSelected.emit(self.hVertex is not None)

    def addPointToEdge(self):
        shape = self.prevhShape
        index = self.prevhEdge
        point = self.prevMovePoint
        if shape is None or index is None or point is None:
            return
        shape.insertPoint(index, point)
        shape.highlightVertex(index, shape.MOVE_VERTEX)
        self.hShape = shape
        self.hVertex = index
        self.hEdge = None
        self.movingShape = True

    def removeSelectedPoint(self):
        shape = self.prevhShape
        index = self.prevhVertex
        if shape is None or index is None:
            return
        shape.removePoint(index)
        shape.highlightClear()
        self.hShape = shape
        self.prevhVertex = None
        self.movingShape = True  # Save changes

    def mousePressEvent(self, ev):
        pos = self.transformPos(ev.localPos())

        is_shift_pressed = ev.modifiers() & QtCore.Qt.ShiftModifier

        if ev.button() == QtCore.Qt.LeftButton:
            if self.drawing():
                if self.current:
                    # Add point to existing shape.
                    if self.createMode == "polygon":
                        self.current.addPoint(self.line[1])
                        self.line[0] = self.current[-1]
                        if self.current.isClosed():
                            self.finalise()
                    elif self.createMode in ["rectangle", "circle", "line"]:
                        assert len(self.current.points) == 1
                        self.current.points = self.line.points
                        self.finalise()
                    elif self.createMode == "linestrip":
                        self.current.addPoint(self.line[1])
                        self.line[0] = self.current[-1]
                        if int(ev.modifiers()) == QtCore.Qt.ControlModifier:
                            self.finalise()
                    elif self.createMode in ["ai_polygon", "ai_mask"]:
                        self.current.addPoint(
                            self.line.points[1],
                            label=self.line.point_labels[1],
                        )
                        self.line.points[0] = self.current.points[-1]
                        self.line.point_labels[0] = self.current.point_labels[-1]
                        if ev.modifiers() & QtCore.Qt.ControlModifier:
                            self.finalise()
                elif not self.outOfPixmap(pos):
                    # Create new shape.
                    self.current = Shape(
                        shape_type="points"
                        if self.createMode in ["ai_polygon", "ai_mask"]
                        else self.createMode
                    )
                    self.current.addPoint(pos, label=0 if is_shift_pressed else 1)
                    if self.createMode == "point":
                        self.finalise()
                    elif (
                        self.createMode in ["ai_polygon", "ai_mask"]
                        and ev.modifiers() & QtCore.Qt.ControlModifier
                    ):
                        self.finalise()
                    else:
                        if self.createMode == "circle":
                            self.current.shape_type = "circle"
                        self.line.points = [pos, pos]
                        if (
                            self.createMode in ["ai_polygon", "ai_mask"]
                            and is_shift_pressed
                        ):
                            self.line.point_labels = [0, 0]
                        else:
                            self.line.point_labels = [1, 1]
                        self.setHiding()
                        self.drawingPolygon.emit(True)
                        self.update()
            elif self.editing():
                if self.selectedEdge() and ev.modifiers() == QtCore.Qt.AltModifier:
                    self.addPointToEdge()
                elif self.selectedVertex() and ev.modifiers() == (
                    QtCore.Qt.AltModifier | QtCore.Qt.ShiftModifier
                ):
                    self.removeSelectedPoint()

                group_mode = int(ev.modifiers()) == QtCore.Qt.ControlModifier
                self.selectShapePoint(pos, multiple_selection_mode=group_mode)
                self.prevPoint = pos
                self.repaint()
        elif ev.button() == QtCore.Qt.RightButton and self.editing():
            group_mode = int(ev.modifiers()) == QtCore.Qt.ControlModifier
            if not self.selectedShapes or (
                self.hShape is not None and self.hShape not in self.selectedShapes
            ):
                self.selectShapePoint(pos, multiple_selection_mode=group_mode)
                self.repaint()
            self.prevPoint = pos

    def mouseReleaseEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            menu = self.menus[len(self.selectedShapesCopy) > 0]
            self.restoreCursor()
            if not menu.exec_(self.mapToGlobal(ev.pos())) and self.selectedShapesCopy:
                # Cancel the move by deleting the shadow copy.
                self.selectedShapesCopy = []
                self.repaint()
        elif ev.button() == QtCore.Qt.LeftButton:
            if self.editing():
                if (
                    self.hShape is not None
                    and self.hShapeIsSelected
                    and not self.movingShape
                ):
                    self.selectionChanged.emit(
                        [x for x in self.selectedShapes if x != self.hShape]
                    )

        if self.movingShape and self.hShape:
            index = self.shapes.index(self.hShape)
            if self.shapesBackups[-1][index].points != self.shapes[index].points:
                self.storeShapes()
                self.shapeMoved.emit()

            self.movingShape = False

    def endMove(self, copy):
        assert self.selectedShapes and self.selectedShapesCopy
        assert len(self.selectedShapesCopy) == len(self.selectedShapes)
        if copy:
            for i, shape in enumerate(self.selectedShapesCopy):
                self.shapes.append(shape)
                self.selectedShapes[i].selected = False
                self.selectedShapes[i] = shape
        else:
            for i, shape in enumerate(self.selectedShapesCopy):
                self.selectedShapes[i].points = shape.points
        self.selectedShapesCopy = []
        self.repaint()
        self.storeShapes()
        return True

    def hideBackroundShapes(self, value):
        self.hideBackround = value
        if self.selectedShapes:
            # Only hide other shapes if there is a current selection.
            # Otherwise the user will not be able to select a shape.
            self.setHiding(True)
            self.update()

    def setHiding(self, enable=True):
        self._hideBackround = self.hideBackround if enable else False

    def canCloseShape(self):
        return self.drawing() and (
            (self.current and len(self.current) > 2)
            or self.createMode in ["ai_polygon", "ai_mask"]
        )

    def mouseDoubleClickEvent(self, ev):
        if self.double_click != "close":
            return

        if (
            self.createMode == "polygon" and self.canCloseShape()
        ) or self.createMode in ["ai_polygon", "ai_mask"]:
            self.finalise()

    def selectShapes(self, shapes):
        self.setHiding()
        self.selectionChanged.emit(shapes)
        self.update()

    def selectShapePoint(self, point, multiple_selection_mode):
        """Select the first shape created which contains this point."""
        if self.selectedVertex():  # A vertex is marked for selection.
            index, shape = self.hVertex, self.hShape
            shape.highlightVertex(index, shape.MOVE_VERTEX)
        else:
            for shape in reversed(self.shapes):
                if self.isVisible(shape) and shape.containsPoint(point):
                    self.setHiding()
                    if shape not in self.selectedShapes:
                        if multiple_selection_mode:
                            self.selectionChanged.emit(self.selectedShapes + [shape])
                        else:
                            self.selectionChanged.emit([shape])
                        self.hShapeIsSelected = False
                    else:
                        self.hShapeIsSelected = True
                    self.calculateOffsets(point)
                    return
        self.deSelectShape()

    def calculateOffsets(self, point):
        left = self.pixmap.width() - 1
        right = 0
        top = self.pixmap.height() - 1
        bottom = 0
        for s in self.selectedShapes:
            rect = s.boundingRect()
            if rect.left() < left:
                left = rect.left()
            if rect.right() > right:
                right = rect.right()
            if rect.top() < top:
                top = rect.top()
            if rect.bottom() > bottom:
                bottom = rect.bottom()

        x1 = left - point.x()
        y1 = top - point.y()
        x2 = right - point.x()
        y2 = bottom - point.y()
        self.offsets = QtCore.QPointF(x1, y1), QtCore.QPointF(x2, y2)

    def boundedMoveVertex(self, pos):
        index, shape = self.hVertex, self.hShape
        point = shape[index]
        if self.outOfPixmap(pos):
            pos = self.intersectionPoint(point, pos)
        shape.moveVertexBy(index, pos - point)

    def boundedMoveShapes(self, shapes, pos):
        if self.outOfPixmap(pos):
            return False  # No need to move
        o1 = pos + self.offsets[0]
        if self.outOfPixmap(o1):
            pos -= QtCore.QPointF(min(0, o1.x()), min(0, o1.y()))
        o2 = pos + self.offsets[1]
        if self.outOfPixmap(o2):
            pos += QtCore.QPointF(
                min(0, self.pixmap.width() - o2.x()),
                min(0, self.pixmap.height() - o2.y()),
            )
        # XXX: The next line tracks the new position of the cursor
        # relative to the shape, but also results in making it
        # a bit "shaky" when nearing the border and allows it to
        # go outside of the shape's area for some reason.
        # self.calculateOffsets(self.selectedShapes, pos)
        dp = pos - self.prevPoint
        if dp:
            for shape in shapes:
                shape.moveBy(dp)
            self.prevPoint = pos
            return True
        return False

    def deSelectShape(self):
        if self.selectedShapes:
            self.setHiding(False)
            self.selectionChanged.emit([])
            self.hShapeIsSelected = False
            self.update()

    def deleteSelected(self):
        deleted_shapes = []
        if self.selectedShapes:
            for shape in self.selectedShapes:
                self.shapes.remove(shape)
                deleted_shapes.append(shape)
            self.storeShapes()
            self.selectedShapes = []
            self.update()
        return deleted_shapes

    def deleteShape(self, shape):
        if shape in self.selectedShapes:
            self.selectedShapes.remove(shape)
        if shape in self.shapes:
            self.shapes.remove(shape)
        self.storeShapes()
        self.update()

    def paintEvent(self, event: Optional[QtGui.QPaintEvent]) -> None:
        """
        绘制事件处理
        
        处理画布的绘制操作，包括图像显示、形状绘制、十字准星、选中状态等。
        这是Canvas类的核心方法，负责所有的视觉呈现。
        
        Args:
            event: 绘制事件对象，如果为None则进行完整重绘
        """
        if not self.pixmap:
            return super(Canvas, self).paintEvent(event)

        p = self._painter
        p.begin(self)
        # 设置高质量渲染选项
        p.setRenderHint(QtGui.QPainter.Antialiasing)              # 抗锯齿
        p.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)   # 高质量抗锯齿
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)     # 平滑图像变换

        # 应用缩放和平移变换
        p.scale(self.scale, self.scale)
        p.translate(self.offsetToCenter())

        # 绘制背景图像
        p.drawPixmap(0, 0, self.pixmap)

        # 恢复缩放变换
        p.scale(1 / self.scale, 1 / self.scale)

        # 绘制十字准星
        if (
            self._crosshair[self._createMode]  # 当前模式启用十字准星
            and self.drawing()                 # 正在绘图模式
            and self.prevMovePoint             # 有鼠标移动位置
            and not self.outOfPixmap(self.prevMovePoint)  # 鼠标在图像内
        ):
            p.setPen(QtGui.QColor(0, 0, 0))  # 设置黑色画笔
            # 绘制水平线
            p.drawLine(
                0,
                int(self.prevMovePoint.y() * self.scale),
                self.width() - 1,
                int(self.prevMovePoint.y() * self.scale),
            )
            # 绘制垂直线
            p.drawLine(
                int(self.prevMovePoint.x() * self.scale),
                0,
                int(self.prevMovePoint.x() * self.scale),
                self.height() - 1,
            )

        # 设置形状缩放比例
        Shape.scale = self.scale
        
        # 绘制所有形状
        for shape in self.shapes:
            if (shape.selected or not self._hideBackround) and self.isVisible(shape):
                shape.fill = shape.selected or shape == self.hShape
                shape.paint(p)
        
        # 绘制当前正在创建的形状
        if self.current:
            self.current.paint(p)
            assert len(self.line.points) == len(self.line.point_labels)
            self.line.paint(p)
        
        # 绘制选中形状的副本（用于移动操作）
        if self.selectedShapesCopy:
            for s in self.selectedShapesCopy:
                s.paint(p)

        if not self.current:
            p.end()
            return

        # 处理多边形填充绘制
        if (
            self.createMode == "polygon"
            and self.fillDrawing()
            and len(self.current.points) >= 2
        ):
            drawing_shape = self.current.copy()
            # 确保填充颜色不透明
            if drawing_shape.fill_color.getRgb()[3] == 0:
                logger.warning(
                    "fill_drawing=true, but fill_color is transparent,"
                    " so forcing to be opaque."
                )
                drawing_shape.fill_color.setAlpha(64)
            drawing_shape.addPoint(self.line[1])

        # 跳过非AI模式的处理
        if self.createMode not in ["ai_polygon", "ai_mask"]:
            p.end()
            return

        # AI模式下的形状处理
        drawing_shape = self.current.copy()
        drawing_shape.addPoint(
            point=self.line.points[1],
            label=self.line.point_labels[1],
        )
        if self.createMode in ["ai_polygon", "ai_mask"]:
            if self._sam is None:
                logger.warning("SAM model is not set yet")
                p.end()
                return
            # 使用 SAM 模型更新形状，添加异常处理
            try:
                image_bytes = labelme.utils.img_qt_to_arr(self.pixmap.toImage()).tobytes()
                if image_bytes in self._sam_embedding:
                    _update_shape_with_sam(
                        shape=drawing_shape,
                        createMode=self.createMode,
                        model_name=self._sam.name,
                        image_embedding=self._sam_embedding[image_bytes],
                    )
                else:
                    logger.warning(
                        "Image embedding not found in cache for createMode {!r}. "
                        "Skipping SAM processing.",
                        self.createMode
                    )
            except Exception as e:
                logger.exception(
                    "Error in SAM processing during paintEvent for createMode {!r}: {}",
                    self.createMode,
                    e
                )
        # 设置绘制形状的属性
        drawing_shape.fill = self.fillDrawing()  # 填充设置
        drawing_shape.selected = True           # 选中状态
        drawing_shape.paint(p)                  # 绘制形状
        p.end()

    def transformPos(self, point):
        """Convert from widget-logical coordinates to painter-logical ones."""
        return point / self.scale - self.offsetToCenter()

    def offsetToCenter(self):
        s = self.scale
        area = super(Canvas, self).size()
        w, h = self.pixmap.width() * s, self.pixmap.height() * s
        aw, ah = area.width(), area.height()
        x = (aw - w) / (2 * s) if aw > w else 0
        y = (ah - h) / (2 * s) if ah > h else 0
        return QtCore.QPointF(x, y)

    def outOfPixmap(self, p):
        w, h = self.pixmap.width(), self.pixmap.height()
        return not (0 <= p.x() <= w - 1 and 0 <= p.y() <= h - 1)

    def finalise(self):
        assert self.current
        # Only call _update_shape_with_sam for AI modes (ai_polygon, ai_mask)
        # For regular polygon mode, skip SAM processing
        if self.createMode in ["ai_polygon", "ai_mask"]:
            if self._sam is None:
                logger.warning(
                    "SAM model is not initialized for createMode {!r}. "
                    "Skipping SAM processing.",
                    self.createMode
                )
            else:
                try:
                    image_bytes = labelme.utils.img_qt_to_arr(self.pixmap.toImage()).tobytes()
                    if image_bytes in self._sam_embedding:
                        _update_shape_with_sam(
                            shape=self.current,
                            createMode=self.createMode,
                            model_name=self._sam.name,
                            image_embedding=self._sam_embedding[image_bytes],
                        )
                    else:
                        logger.warning(
                            "Image embedding not found in cache for createMode {!r}. "
                            "Skipping SAM processing.",
                            self.createMode
                        )
                except Exception as e:
                    logger.exception(
                        "Error in SAM processing for createMode {!r}: {}",
                        self.createMode,
                        e
                    )
        self.current.close()

        self.shapes.append(self.current)
        self.storeShapes()
        self.current = None
        self.setHiding(False)
        self.newShape.emit()
        self.update()

    def closeEnough(self, p1, p2):
        # d = distance(p1 - p2)
        # m = (p1-p2).manhattanLength()
        # print "d %.2f, m %d, %.2f" % (d, m, d - m)
        # divide by scale to allow more precision when zoomed in
        return labelme.utils.distance(p1 - p2) < (self.epsilon / self.scale)

    def intersectionPoint(self, p1, p2):
        # Cycle through each image edge in clockwise fashion,
        # and find the one intersecting the current line segment.
        # http://paulbourke.net/geometry/lineline2d/
        size = self.pixmap.size()
        points = [
            (0, 0),
            (size.width() - 1, 0),
            (size.width() - 1, size.height() - 1),
            (0, size.height() - 1),
        ]
        # x1, y1 should be in the pixmap, x2, y2 should be out of the pixmap
        x1 = min(max(p1.x(), 0), size.width() - 1)
        y1 = min(max(p1.y(), 0), size.height() - 1)
        x2, y2 = p2.x(), p2.y()
        d, i, (x, y) = min(self.intersectingEdges((x1, y1), (x2, y2), points))
        x3, y3 = points[i]
        x4, y4 = points[(i + 1) % 4]
        if (x, y) == (x1, y1):
            # Handle cases where previous point is on one of the edges.
            if x3 == x4:
                return QtCore.QPointF(x3, min(max(0, y2), max(y3, y4)))
            else:  # y3 == y4
                return QtCore.QPointF(min(max(0, x2), max(x3, x4)), y3)
        return QtCore.QPointF(x, y)

    def intersectingEdges(self, point1, point2, points):
        """Find intersecting edges.

        For each edge formed by `points', yield the intersection
        with the line segment `(x1,y1) - (x2,y2)`, if it exists.
        Also return the distance of `(x2,y2)' to the middle of the
        edge along with its index, so that the one closest can be chosen.
        """
        (x1, y1) = point1
        (x2, y2) = point2
        for i in range(4):
            x3, y3 = points[i]
            x4, y4 = points[(i + 1) % 4]
            denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
            nua = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
            nub = (x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)
            if denom == 0:
                # This covers two cases:
                #   nua == nub == 0: Coincident
                #   otherwise: Parallel
                continue
            ua, ub = nua / denom, nub / denom
            if 0 <= ua <= 1 and 0 <= ub <= 1:
                x = x1 + ua * (x2 - x1)
                y = y1 + ua * (y2 - y1)
                m = QtCore.QPointF((x3 + x4) / 2, (y3 + y4) / 2)
                d = labelme.utils.distance(m - QtCore.QPointF(x2, y2))
                yield d, i, (x, y)

    # These two, along with a call to adjustSize are required for the
    # scroll area.
    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        if self.pixmap:
            return self.scale * self.pixmap.size()
        return super(Canvas, self).minimumSizeHint()

    def wheelEvent(self, ev):
        mods = ev.modifiers()
        delta = ev.angleDelta()
        if QtCore.Qt.ControlModifier == int(mods):
            # with Ctrl/Command key
            # zoom
            self.zoomRequest.emit(delta.y(), ev.pos())
        else:
            # scroll
            self.scrollRequest.emit(delta.x(), QtCore.Qt.Horizontal)
            self.scrollRequest.emit(delta.y(), QtCore.Qt.Vertical)
        ev.accept()

    def moveByKeyboard(self, offset):
        if self.selectedShapes:
            self.boundedMoveShapes(self.selectedShapes, self.prevPoint + offset)
            self.repaint()
            self.movingShape = True

    def keyPressEvent(self, ev):
        modifiers = ev.modifiers()
        key = ev.key()
        if self.drawing():
            if key == QtCore.Qt.Key_Escape and self.current:
                self.current = None
                self.drawingPolygon.emit(False)
                self.update()
            elif key == QtCore.Qt.Key_Return and self.canCloseShape():
                self.finalise()
            elif modifiers == QtCore.Qt.AltModifier:
                self.snapping = False
        elif self.editing():
            if key == QtCore.Qt.Key_Up:
                self.moveByKeyboard(QtCore.QPointF(0.0, -MOVE_SPEED))
            elif key == QtCore.Qt.Key_Down:
                self.moveByKeyboard(QtCore.QPointF(0.0, MOVE_SPEED))
            elif key == QtCore.Qt.Key_Left:
                self.moveByKeyboard(QtCore.QPointF(-MOVE_SPEED, 0.0))
            elif key == QtCore.Qt.Key_Right:
                self.moveByKeyboard(QtCore.QPointF(MOVE_SPEED, 0.0))

    def keyReleaseEvent(self, ev):
        modifiers = ev.modifiers()
        if self.drawing():
            if int(modifiers) == 0:
                self.snapping = True
        elif self.editing():
            if self.movingShape and self.selectedShapes:
                index = self.shapes.index(self.selectedShapes[0])
                if self.shapesBackups[-1][index].points != self.shapes[index].points:
                    self.storeShapes()
                    self.shapeMoved.emit()

                self.movingShape = False

    def setLastLabel(self, text, flags):
        assert text
        self.shapes[-1].label = text
        self.shapes[-1].flags = flags
        self.shapesBackups.pop()
        self.storeShapes()
        return self.shapes[-1]

    def undoLastLine(self):
        assert self.shapes
        self.current = self.shapes.pop()
        self.current.setOpen()
        self.current.restoreShapeRaw()
        if self.createMode in ["polygon", "linestrip"]:
            self.line.points = [self.current[-1], self.current[0]]
        elif self.createMode in ["rectangle", "line", "circle"]:
            self.current.points = self.current.points[0:1]
        elif self.createMode == "point":
            self.current = None
        self.drawingPolygon.emit(True)

    def undoLastPoint(self):
        if not self.current or self.current.isClosed():
            return
        self.current.popPoint()
        if len(self.current) > 0:
            self.line[0] = self.current[-1]
        else:
            self.current = None
            self.drawingPolygon.emit(False)
        self.update()

    def loadPixmap(self, pixmap, clear_shapes=True):
        """
        加载图像到画布
        
        将指定的图像加载到画布中，并可选择是否清除现有的形状数据。
        如果启用了AI模型，还会计算并缓存图像的嵌入向量。
        
        Args:
            pixmap: 要加载的图像数据（QPixmap对象）
            clear_shapes: 是否清除现有形状，默认为True
        """
        self.pixmap = pixmap
        # 如果启用了AI模型，计算图像嵌入
        if self._sam:
            self._compute_and_cache_image_embedding()
        # 清除现有形状（如果需要）
        if clear_shapes:
            self.shapes = []
        self.update()

    def loadShapes(self, shapes, replace=True):
        """
        加载形状数据
        
        将形状列表加载到画布中，可以选择替换现有形状或追加到现有形状列表。
        加载后会更新形状备份状态。
        
        Args:
            shapes: 要加载的形状列表
            replace: 是否替换现有形状，默认为True
        """
        if replace:
            self.shapes = list(shapes)
        else:
            self.shapes.extend(shapes)
        # 存储当前形状状态到备份
        self.storeShapes()
        # 重置当前状态
        self.current = None
        self.hShape = None
        self.hVertex = None
        self.hEdge = None
        self.update()

    def setShapeVisible(self, shape, value):
        """
        设置形状可见性
        
        控制指定形状是否在画布中显示。
        
        Args:
            shape: 要设置可见性的形状对象
            value: 可见性值，True为显示，False为隐藏
        """
        self.visible[shape] = value
        self.update()

    def overrideCursor(self, cursor):
        """
        覆盖光标样式
        
        临时设置画布的光标样式，并保存当前光标状态以便恢复。
        
        Args:
            cursor: 要设置的光标样式
        """
        self.restoreCursor()
        self._cursor = cursor
        QtWidgets.QApplication.setOverrideCursor(cursor)

    def restoreCursor(self):
        """
        恢复光标样式
        
        恢复之前保存的光标样式，清除光标覆盖状态。
        """
        QtWidgets.QApplication.restoreOverrideCursor()

    def resetState(self):
        """
        重置画布状态
        
        将画布恢复到初始状态，清除所有图像、形状和备份数据。
        这是一个完全重置操作，用于清理画布。
        """
        self.restoreCursor()
        self.pixmap = None
        self.shapesBackups = []
        self.update()


def _update_shape_with_sam(
    shape: Shape,
    createMode: str,
    model_name: str,
    image_embedding,
) -> None:
    if createMode not in ["ai_polygon", "ai_mask"]:
        raise ValueError(
            f"createMode must be 'ai_polygon' or 'ai_mask', not {createMode}"
        )

    # Skip SAM processing if osam is not available
    try:
        import osam
    except ImportError:
        logger.warning("osam module not available, skipping SAM processing")
        return

    response = osam.apis.generate(
        osam.types.GenerateRequest(
            model=model_name,
            image_embedding=image_embedding,
            prompt=osam.types.Prompt(
                points=[[point.x(), point.y()] for point in shape.points],
                point_labels=shape.point_labels,
            ),
        )
    )
    if not response.annotations:
        logger.warning("No annotations returned by model {!r}", model_name)
        return

    if createMode == "ai_mask":
        y1: int
        x1: int
        y2: int
        x2: int
        if response.annotations[0].bounding_box is None:
            y1, x1, y2, x2 = imgviz.instances.mask_to_bbox(
                [response.annotations[0].mask]
            )[0].astype(int)
        else:
            y1 = response.annotations[0].bounding_box.ymin
            x1 = response.annotations[0].bounding_box.xmin
            y2 = response.annotations[0].bounding_box.ymax
            x2 = response.annotations[0].bounding_box.xmax
        shape.setShapeRefined(
            shape_type="mask",
            points=[QtCore.QPointF(x1, y1), QtCore.QPointF(x2, y2)],
            point_labels=[1, 1],
            mask=response.annotations[0].mask[y1 : y2 + 1, x1 : x2 + 1],
        )
    elif createMode == "ai_polygon":
        points = polygon_from_mask.compute_polygon_from_mask(
            mask=response.annotations[0].mask
        )
        if len(points) < 2:
            return
        shape.setShapeRefined(
            shape_type="polygon",
            points=[QtCore.QPointF(point[0], point[1]) for point in points],
            point_labels=[1] * len(points),
        )
