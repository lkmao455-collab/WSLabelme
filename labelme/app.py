# -*- coding: utf-8 -*-
"""
Labelme 主应用程序模块

这是一个图像标注工具的主应用程序模块，提供了完整的图像标注功能，
包括多边形、矩形、圆形、线条、点等多种标注形状的创建和编辑功能。
支持AI辅助标注、TCP通信、文件管理等功能。

主要功能：
- 图像标注：支持多种形状的标注（多边形、矩形、圆形、线条、点等）
- AI辅助：集成AI模型进行智能标注
- 文件管理：支持图像和标注文件的导入导出
- TCP通信：支持与外部系统的数据交互
- 配置管理：支持用户配置和设置保存
- 文件监控：自动监控配置文件和图像文件夹变化
- 窗口管理：智能屏幕检测和窗口位置调整
- 状态保存：自动保存窗口位置、大小和最近文件列表
"""
# 文件头部说明:
# 本模块是Labelme应用程序的核心主窗口模块，负责管理整个应用程序的
# 生命周期、UI布局、事件处理、文件操作和标注功能。包含了主窗口类
# MainWindow，该类继承自QtWidgets.QMainWindow，实现了完整的图像标注
# 工具的所有核心功能。

import functools
import html
import json
import sys
import math
import os
import os.path as osp
import re
import webbrowser

import imgviz
import natsort
import numpy as np
from loguru import logger
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from labelme import __appname__
from labelme._automation import bbox_from_text
from labelme.config import get_config
from labelme.label_file import LabelFile
from labelme.label_file import LabelFileError
from labelme.shape import Shape
from labelme.tcp_client import TcpClientThread
from labelme.widgets import AiPromptWidget
from labelme.widgets import BrightnessContrastDialog
from labelme.widgets import Canvas
from labelme.widgets import FileDialogPreview
from labelme.widgets import LabelDialog
from labelme.widgets import LabelListWidget
from labelme.widgets import LabelListWidgetItem
from labelme.widgets import ThumbnailFileList
from labelme.widgets import ToolBar
from labelme.widgets import UniqueLabelQListWidget
from labelme.widgets import UnifiedTrainingWidget
from labelme.widgets import ZoomWidget
from labelme.widgets import TrainingCurveDock

from ssh_deploy import DeployDockWidget

from . import utils

# 导入模块说明:
# - functools: 提供高阶函数和可调用对象的工具
# - html: HTML实体处理
# - json: JSON数据处理
# - sys: 系统相关参数和函数
# - math: 数学运算函数
# - os: 操作系统接口
# - os.path: 路径操作工具
# - re: 正则表达式
# - webbrowser: 网页浏览器控制
# - imgviz: 图像可视化工具
# - natsort: 自然排序算法
# - numpy: 数值计算库
# - loguru: 日志记录库
# - PyQt5: GUI框架
# - labelme: 本项目的核心模块
# - utils: 本地工具函数

# FIXME
# - [medium] Set max zoom value to something big enough for FitWidth/Window

# TODO(unknown):
# - Zoom is too "steppy".


LABEL_COLORMAP = imgviz.label_colormap()


def _get_app_dir():
    if getattr(sys, "frozen", False):
        return osp.dirname(sys.executable)
    return osp.dirname(osp.dirname(osp.abspath(__file__)))


class MainWindow(QtWidgets.QMainWindow):
    """
    Labelme 主窗口类
    
    这是Labelme应用程序的主窗口类，继承自QtWidgets.QMainWindow。
    负责管理整个应用程序的UI布局、事件处理、文件操作、标注功能等核心功能。
    
    主要功能：
    - 窗口布局管理（工具栏、菜单栏、停靠窗口等）
    - 图像和标注文件的加载与保存
    - 标注工具的创建和管理（多边形、矩形、圆形等）
    - AI辅助标注功能
    - TCP通信客户端
    - 文件系统监控
    - 配置管理和状态保存
    """
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = 0, 1, 2

    def __init__(
        self,
        config=None,
        filename=None,
        output=None,
        output_file=None,
        output_dir=None,
    ):
        """
        初始化主窗口
        
        Args:
            config: 应用程序配置字典
            filename: 要加载的文件路径
            output: 输出路径（已废弃，使用output_file）
            output_file: 输出文件路径
            output_dir: 输出目录路径
        """
        if output is not None:
            logger.warning("argument output is deprecated, use output_file instead")
            if output_file is None:
                output_file = output

        # see labelme/config/default_config.yaml for valid configuration
        if config is None:
            config = get_config()
        self._config = config

        # set default shape colors
        Shape.line_color = QtGui.QColor(*self._config["shape"]["line_color"])
        Shape.fill_color = QtGui.QColor(*self._config["shape"]["fill_color"])
        Shape.select_line_color = QtGui.QColor(
            *self._config["shape"]["select_line_color"]
        )
        Shape.select_fill_color = QtGui.QColor(
            *self._config["shape"]["select_fill_color"]
        )
        Shape.vertex_fill_color = QtGui.QColor(
            *self._config["shape"]["vertex_fill_color"]
        )
        Shape.hvertex_fill_color = QtGui.QColor(
            *self._config["shape"]["hvertex_fill_color"]
        )

        # Set point size from config file
        Shape.point_size = self._config["shape"]["point_size"]

        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)

        # Whether we need to save or not.
        self.dirty = False

        self._noSelectionSlot = False

        self._copied_shapes = None

        # Main widgets and related state.
        self.labelDialog = LabelDialog(
            parent=self,
            labels=self._config["labels"],
            sort_labels=self._config["sort_labels"],
            show_text_field=self._config["show_label_text_field"],
            completion=self._config["label_completion"],
            fit_to_content=self._config["fit_to_content"],
            flags=self._config["label_flags"],
        )

        self.labelList = LabelListWidget()
        self.lastOpenDir = None
        
        # Load default images folder from config
        self.defaultImagesFolder = self._loadDefaultImagesFolder()
        
        # Setup file system watcher for config file and images folder
        self.fileWatcher = QtCore.QFileSystemWatcher(self)
        self._setupFileWatcher()

        self.flag_dock = self.flag_widget = None
        self.flag_dock = QtWidgets.QDockWidget(self.tr("Flags"), self)
        self.flag_dock.setObjectName("Flags")
        self.flag_widget = QtWidgets.QListWidget()
        if config["flags"]:
            self.loadFlags({k: False for k in config["flags"]})
        self.flag_dock.setWidget(self.flag_widget)
        self.flag_widget.itemChanged.connect(self.setDirty)

        self.labelList.itemSelectionChanged.connect(self.labelSelectionChanged)
        self.labelList.itemDoubleClicked.connect(self._edit_label)
        self.labelList.itemChanged.connect(self.labelItemChanged)
        self.labelList.itemDropped.connect(self.labelOrderChanged)
        self.shape_dock = QtWidgets.QDockWidget(self.tr("Polygon Labels"), self)
        self.shape_dock.setObjectName("Labels")
        self.shape_dock.setWidget(self.labelList)

        self.uniqLabelList = UniqueLabelQListWidget()
        self.uniqLabelList.setToolTip(
            self.tr(
                "Select label to start annotating for it. " "Press 'Esc' to deselect."
            )
        )
        if self._config["labels"]:
            for label in self._config["labels"]:
                item = self.uniqLabelList.createItemFromLabel(label)
                self.uniqLabelList.addItem(item)
                rgb = self._get_rgb_by_label(label)
                self.uniqLabelList.setItemLabel(item, label, rgb)
        self.label_dock = QtWidgets.QDockWidget(self.tr("Label List"), self)
        self.label_dock.setObjectName("Label List")
        self.label_dock.setWidget(self.uniqLabelList)

        self.fileSearch = QtWidgets.QLineEdit()
        self.fileSearch.setPlaceholderText(self.tr("Search Filename"))
        self.fileSearch.textChanged.connect(self.fileSearchChanged)
        self.fileListWidget = ThumbnailFileList()
        self.fileListWidget.fileSelected.connect(self.fileSelectionChanged)
        fileListLayout = QtWidgets.QVBoxLayout()
        fileListLayout.setContentsMargins(0, 0, 0, 0)
        fileListLayout.setSpacing(0)
        fileListLayout.addWidget(self.fileSearch)
        fileListLayout.addWidget(self.fileListWidget)
        self.file_dock = QtWidgets.QDockWidget(self.tr("File List"), self)
        self.file_dock.setObjectName("Files")
        fileListWidget = QtWidgets.QWidget()
        fileListWidget.setLayout(fileListLayout)
        self.file_dock.setWidget(fileListWidget)

        # 创建综合训练管理 Dock
        self.training_dock = QtWidgets.QDockWidget(self.tr("训练管理"), self)
        self.training_dock.setObjectName("TrainingManager")
        self.training_widget = UnifiedTrainingWidget(self)
        self.training_dock.setWidget(self.training_widget)
        
        # 当训练面板显示时，自动刷新任务列表
        self.training_dock.visibilityChanged.connect(self._on_training_dock_visibility_changed)

        # 创建训练曲线 Dock
        self.loss_curve_dock = TrainingCurveDock(self.tr("损失曲线"), self, curve_type='loss')
        self.acc_curve_dock = TrainingCurveDock(self.tr("准确率曲线"), self, curve_type='accuracy')
        
        # 默认显示曲线 dock，并设置最小尺寸
        self.loss_curve_dock.setMinimumSize(300, 200)
        self.acc_curve_dock.setMinimumSize(300, 200)
        self.loss_curve_dock.setVisible(True)
        self.acc_curve_dock.setVisible(True)
        self.loss_curve_dock.show()
        self.acc_curve_dock.show()

        # 创建 SSH 模型部署 Dock
        self.deploy_dock = DeployDockWidget(self)
        self.deploy_dock.setMinimumSize(350, 400)

        self.zoomWidget = ZoomWidget()
        self.setAcceptDrops(True)

        self.canvas = self.labelList.canvas = Canvas(
            epsilon=self._config["epsilon"],
            double_click=self._config["canvas"]["double_click"],
            num_backups=self._config["canvas"]["num_backups"],
            crosshair=self._config["canvas"]["crosshair"],
        )
        self.canvas.zoomRequest.connect(self.zoomRequest)
        self.canvas.mouseMoved.connect(
            lambda pos: self.status(f"Mouse is at: x={pos.x()}, y={pos.y()}")
        )

        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setWidget(self.canvas)
        scrollArea.setWidgetResizable(True)
        self.scrollBars = {
            Qt.Vertical: scrollArea.verticalScrollBar(),
            Qt.Horizontal: scrollArea.horizontalScrollBar(),
        }
        self.canvas.scrollRequest.connect(self.scrollRequest)

        self.canvas.newShape.connect(self.newShape)
        self.canvas.shapeMoved.connect(self.setDirty)
        self.canvas.selectionChanged.connect(self.shapeSelectionChanged)
        self.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)

        self.setCentralWidget(scrollArea)

        # 设置各个 dock 的特性
        # 注意：强制覆盖配置，确保这些 dock 不可关闭（即使配置文件设置了 closable: true）
        for dock in ["flag_dock", "label_dock", "shape_dock", "file_dock"]:
            features = QtWidgets.QDockWidget.DockWidgetFeatures()
            # 强制设置 closable 为 False，忽略配置文件中的设置
            # if self._config[dock]["closable"]:
            #     features = features | QtWidgets.QDockWidget.DockWidgetClosable
            if self._config[dock]["floatable"]:
                features = features | QtWidgets.QDockWidget.DockWidgetFloatable
            if self._config[dock]["movable"]:
                features = features | QtWidgets.QDockWidget.DockWidgetMovable
            getattr(self, dock).setFeatures(features)
            if self._config[dock]["show"] is False:
                getattr(self, dock).setVisible(False)

        # 设置训练管理 dock 不可关闭
        training_features = QtWidgets.QDockWidget.DockWidgetFloatable | QtWidgets.QDockWidget.DockWidgetMovable
        self.training_dock.setFeatures(training_features)
        
        # 设置训练曲线 dock 不可关闭
        loss_curve_features = QtWidgets.QDockWidget.DockWidgetFloatable | QtWidgets.QDockWidget.DockWidgetMovable
        self.loss_curve_dock.setFeatures(loss_curve_features)
        
        acc_curve_features = QtWidgets.QDockWidget.DockWidgetFloatable | QtWidgets.QDockWidget.DockWidgetMovable
        self.acc_curve_dock.setFeatures(acc_curve_features)

        # 设置模型部署 dock 不可关闭
        deploy_features = QtWidgets.QDockWidget.DockWidgetFloatable | QtWidgets.QDockWidget.DockWidgetMovable
        self.deploy_dock.setFeatures(deploy_features)

        self.addDockWidget(Qt.RightDockWidgetArea, self.flag_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.label_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.shape_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.file_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.training_dock)
        
        # 添加模型部署 dock 到右侧区域
        self.addDockWidget(Qt.RightDockWidgetArea, self.deploy_dock)
        
        # 添加训练曲线 dock 到底部区域（默认显示）
        self.addDockWidget(Qt.BottomDockWidgetArea, self.loss_curve_dock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.acc_curve_dock)
        
        # 使用 splitDockWidget 水平分割两个曲线 dock（左右并排显示）
        self.splitDockWidget(self.loss_curve_dock, self.acc_curve_dock, Qt.Horizontal)
        
        # 确保曲线 dock 显示在最前面
        self.loss_curve_dock.show()
        self.acc_curve_dock.show()
        self.loss_curve_dock.raise_()
        self.acc_curve_dock.raise_()

        # Actions
        action = functools.partial(utils.newAction, self)
        shortcuts = self._config["shortcuts"]
        quit = action(
            self.tr("&Quit"),
            self.close,
            shortcuts["quit"],
            "quit",
            self.tr("Quit application"),
        )
        open_ = action(
            self.tr("&Open\n"),
            self.openFile,
            shortcuts["open"],
            "open",
            self.tr("Open image or label file"),
        )
        opendir = action(
            self.tr("Open Dir"),
            self.openDirDialog,
            shortcuts["open_dir"],
            "open",
            self.tr("Open Dir"),
        )
        openNextImg = action(
            self.tr("&Next Image"),
            self.openNextImg,
            shortcuts["open_next"],
            "next",
            self.tr("Open next (hold Ctl+Shift to copy labels)"),
            enabled=False,
        )
        openPrevImg = action(
            self.tr("&Prev Image"),
            self.openPrevImg,
            shortcuts["open_prev"],
            "prev",
            self.tr("Open prev (hold Ctl+Shift to copy labels)"),
            enabled=False,
        )

        # 隐藏工具栏上的打开、打开目录、上一幅、下一幅按钮
        # open_.setVisible(False)
        # opendir.setVisible(False)
        # openNextImg.setVisible(False)
        # openPrevImg.setVisible(False)

        save = action(
            self.tr("&Save\n"),
            self.saveFile,
            shortcuts["save"],
            "save",
            self.tr("Save labels to file"),
            enabled=False,
        )
        saveAs = action(
            self.tr("&Save As"),
            self.saveFileAs,
            shortcuts["save_as"],
            "save-as",
            self.tr("Save labels to a different file"),
            enabled=False,
        )

        deleteFile = action(
            self.tr("&Delete File"),
            self.deleteFile,
            shortcuts["delete_file"],
            "delete",
            self.tr("Delete current label file"),
            enabled=False,
        )

        changeOutputDir = action(
            self.tr("&Change Output Dir"),
            slot=self.changeOutputDirDialog,
            shortcut=shortcuts["save_to"],
            icon="open",
            tip=self.tr("Change where annotations are loaded/saved"),
        )

        saveAuto = action(
            text=self.tr("Save &Automatically"),
            slot=lambda x: self.actions.saveAuto.setChecked(x),
            icon="save",
            tip=self.tr("Save automatically"),
            checkable=True,
            enabled=True,
        )
        saveAuto.setChecked(self._config["auto_save"])

        saveWithImageData = action(
            text=self.tr("Save With Image Data"),
            slot=self.enableSaveImageWithData,
            tip=self.tr("Save image data in label file"),
            checkable=True,
            checked=self._config["store_data"],
        )

        close = action(
            self.tr("&Close"),
            self.closeFile,
            shortcuts["close"],
            "close",
            self.tr("Close current file"),
        )

        toggle_keep_prev_mode = action(
            self.tr("Keep Previous Annotation"),
            self.toggleKeepPrevMode,
            shortcuts["toggle_keep_prev_mode"],
            None,
            self.tr('Toggle "keep previous annotation" mode'),
            checkable=True,
        )
        toggle_keep_prev_mode.setChecked(self._config["keep_prev"])

        createMode = action(
            self.tr("Create Polygons"),
            lambda: self.toggleDrawMode(False, createMode="polygon"),
            shortcuts["create_polygon"],
            "objects",
            self.tr("Start drawing polygons"),
            enabled=False,
        )
        createRectangleMode = action(
            self.tr("Create Rectangle"),
            lambda: self.toggleDrawMode(False, createMode="rectangle"),
            shortcuts["create_rectangle"],
            "objects",
            self.tr("Start drawing rectangles"),
            enabled=False,
        )
        createCircleMode = action(
            self.tr("Create Circle"),
            lambda: self.toggleDrawMode(False, createMode="circle"),
            shortcuts["create_circle"],
            "objects",
            self.tr("Start drawing circles"),
            enabled=False,
        )
        createLineMode = action(
            self.tr("Create Line"),
            lambda: self.toggleDrawMode(False, createMode="line"),
            shortcuts["create_line"],
            "objects",
            self.tr("Start drawing lines"),
            enabled=False,
        )
        createPointMode = action(
            self.tr("Create Point"),
            lambda: self.toggleDrawMode(False, createMode="point"),
            shortcuts["create_point"],
            "objects",
            self.tr("Start drawing points"),
            enabled=False,
        )
        createLineStripMode = action(
            self.tr("Create LineStrip"),
            lambda: self.toggleDrawMode(False, createMode="linestrip"),
            shortcuts["create_linestrip"],
            "objects",
            self.tr("Start drawing linestrip. Ctrl+LeftClick ends creation."),
            enabled=False,
        )
        createAiPolygonMode = action(
            self.tr("Create AI-Polygon"),
            lambda: self.toggleDrawMode(False, createMode="ai_polygon"),
            None,
            "objects",
            self.tr("Start drawing ai_polygon. Ctrl+LeftClick ends creation."),
            enabled=False,
        )
        createAiPolygonMode.changed.connect(
            lambda: self.canvas.initializeAiModel(
                model_name=self._selectAiModelComboBox.itemData(
                    self._selectAiModelComboBox.currentIndex()
                )
            )
            if self.canvas.createMode == "ai_polygon"
            else None
        )
        createAiMaskMode = action(
            self.tr("Create AI-Mask"),
            lambda: self.toggleDrawMode(False, createMode="ai_mask"),
            None,
            "objects",
            self.tr("Start drawing ai_mask. Ctrl+LeftClick ends creation."),
            enabled=False,
        )
        createAiMaskMode.changed.connect(
            lambda: self.canvas.initializeAiModel(
                model_name=self._selectAiModelComboBox.itemData(
                    self._selectAiModelComboBox.currentIndex()
                )
            )
            if self.canvas.createMode == "ai_mask"
            else None
        )
        editMode = action(
            self.tr("Edit Polygons"),
            self.setEditMode,
            shortcuts["edit_polygon"],
            "edit",
            self.tr("Move and edit the selected polygons"),
            enabled=False,
        )

        delete = action(
            self.tr("Delete Polygons"),
            self.deleteSelectedShape,
            shortcuts["delete_polygon"],
            "cancel",
            self.tr("Delete the selected polygons"),
            enabled=False,
        )
        duplicate = action(
            self.tr("Duplicate Polygons"),
            self.duplicateSelectedShape,
            shortcuts["duplicate_polygon"],
            "copy",
            self.tr("Create a duplicate of the selected polygons"),
            enabled=False,
        )
        copy = action(
            self.tr("Copy Polygons"),
            self.copySelectedShape,
            shortcuts["copy_polygon"],
            "copy_clipboard",
            self.tr("Copy selected polygons to clipboard"),
            enabled=False,
        )
        paste = action(
            self.tr("Paste Polygons"),
            self.pasteSelectedShape,
            shortcuts["paste_polygon"],
            "paste",
            self.tr("Paste copied polygons"),
            enabled=False,
        )
        undoLastPoint = action(
            self.tr("Undo last point"),
            self.canvas.undoLastPoint,
            shortcuts["undo_last_point"],
            "undo",
            self.tr("Undo last drawn point"),
            enabled=False,
        )
        removePoint = action(
            text=self.tr("Remove Selected Point"),
            slot=self.removeSelectedPoint,
            shortcut=shortcuts["remove_selected_point"],
            icon="edit",
            tip=self.tr("Remove selected point from polygon"),
            enabled=False,
        )

        undo = action(
            self.tr("Undo\n"),
            self.undoShapeEdit,
            shortcuts["undo"],
            "undo",
            self.tr("Undo last add and edit of shape"),
            enabled=False,
        )

        hideAll = action(
            self.tr("&Hide\nPolygons"),
            functools.partial(self.togglePolygons, False),
            shortcuts["hide_all_polygons"],
            icon="eye",
            tip=self.tr("Hide all polygons"),
            enabled=False,
        )
        showAll = action(
            self.tr("&Show\nPolygons"),
            functools.partial(self.togglePolygons, True),
            shortcuts["show_all_polygons"],
            icon="eye",
            tip=self.tr("Show all polygons"),
            enabled=False,
        )
        toggleAll = action(
            self.tr("&Toggle\nPolygons"),
            functools.partial(self.togglePolygons, None),
            shortcuts["toggle_all_polygons"],
            icon="eye",
            tip=self.tr("Toggle all polygons"),
            enabled=False,
        )

        help = action(
            self.tr("&Tutorial"),
            self.tutorial,
            icon="help",
            tip=self.tr("Show tutorial page"),
        )
        
        about = action(
            self.tr("&About"),
            self.showAbout,
            icon="help",
            tip=self.tr("Show about dialog"),
        )

        zoom = QtWidgets.QWidgetAction(self)
        zoomBoxLayout = QtWidgets.QVBoxLayout()
        zoomLabel = QtWidgets.QLabel(self.tr("Zoom"))
        zoomLabel.setAlignment(Qt.AlignCenter)
        zoomBoxLayout.addWidget(zoomLabel)
        zoomBoxLayout.addWidget(self.zoomWidget)
        zoom.setDefaultWidget(QtWidgets.QWidget())
        zoom.defaultWidget().setLayout(zoomBoxLayout)
        self.zoomWidget.setWhatsThis(
            str(
                self.tr(
                    "Zoom in or out of the image. Also accessible with "
                    "{} and {} from the canvas."
                )
            ).format(
                utils.fmtShortcut(
                    "{},{}".format(shortcuts["zoom_in"], shortcuts["zoom_out"])
                ),
                utils.fmtShortcut(self.tr("Ctrl+Wheel")),
            )
        )
        self.zoomWidget.setEnabled(False)

        zoomIn = action(
            self.tr("Zoom &In"),
            functools.partial(self.addZoom, 1.1),
            shortcuts["zoom_in"],
            "zoom-in",
            self.tr("Increase zoom level"),
            enabled=False,
        )
        zoomOut = action(
            self.tr("&Zoom Out"),
            functools.partial(self.addZoom, 0.9),
            shortcuts["zoom_out"],
            "zoom-out",
            self.tr("Decrease zoom level"),
            enabled=False,
        )
        zoomOrg = action(
            self.tr("&Original size"),
            functools.partial(self.setZoom, 100),
            shortcuts["zoom_to_original"],
            "zoom",
            self.tr("Zoom to original size"),
            enabled=False,
        )
        keepPrevScale = action(
            self.tr("&Keep Previous Scale"),
            self.enableKeepPrevScale,
            tip=self.tr("Keep previous zoom scale"),
            checkable=True,
            checked=self._config["keep_prev_scale"],
            enabled=True,
        )
        fitWindow = action(
            self.tr("&Fit Window"),
            self.setFitWindow,
            shortcuts["fit_window"],
            "fit-window",
            self.tr("Zoom follows window size"),
            checkable=True,
            enabled=False,
        )
        fitWidth = action(
            self.tr("Fit &Width"),
            self.setFitWidth,
            shortcuts["fit_width"],
            "fit-width",
            self.tr("Zoom follows window width"),
            checkable=True,
            enabled=False,
        )
        brightnessContrast = action(
            self.tr("&Brightness Contrast"),
            self.brightnessContrast,
            None,
            "color",
            self.tr("Adjust brightness and contrast"),
            enabled=False,
        )
        # Group zoom controls into a list for easier toggling.
        zoomActions = (
            self.zoomWidget,
            zoomIn,
            zoomOut,
            zoomOrg,
            fitWindow,
            fitWidth,
        )
        self.zoomMode = self.FIT_WINDOW
        fitWindow.setChecked(Qt.Checked)
        self.scalers = {
            self.FIT_WINDOW: self.scaleFitWindow,
            self.FIT_WIDTH: self.scaleFitWidth,
            # Set to one to scale to 100% when loading files.
            self.MANUAL_ZOOM: lambda: 1,
        }

        edit = action(
            self.tr("&Edit Label"),
            self._edit_label,
            shortcuts["edit_label"],
            "edit",
            self.tr("Modify the label of the selected polygon"),
            enabled=False,
        )

        fill_drawing = action(
            self.tr("Fill Drawing Polygon"),
            self.canvas.setFillDrawing,
            None,
            "color",
            self.tr("Fill polygon while drawing"),
            checkable=True,
            enabled=True,
        )
        if self._config["canvas"]["fill_drawing"]:
            fill_drawing.trigger()

        # Label list context menu.
        labelMenu = QtWidgets.QMenu()
        utils.addActions(labelMenu, (edit, delete))
        self.labelList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelList.customContextMenuRequested.connect(self.popLabelListMenu)

        # Store actions for further handling.
        self.actions = utils.struct(
            saveAuto=saveAuto,
            saveWithImageData=saveWithImageData,
            changeOutputDir=changeOutputDir,
            save=save,
            saveAs=saveAs,
            open=open_,
            close=close,
            deleteFile=deleteFile,
            toggleKeepPrevMode=toggle_keep_prev_mode,
            delete=delete,
            edit=edit,
            duplicate=duplicate,
            copy=copy,
            paste=paste,
            undoLastPoint=undoLastPoint,
            undo=undo,
            removePoint=removePoint,
            createMode=createMode,
            editMode=editMode,
            createRectangleMode=createRectangleMode,
            createCircleMode=createCircleMode,
            createLineMode=createLineMode,
            createPointMode=createPointMode,
            createLineStripMode=createLineStripMode,
            createAiPolygonMode=createAiPolygonMode,
            createAiMaskMode=createAiMaskMode,
            zoom=zoom,
            zoomIn=zoomIn,
            zoomOut=zoomOut,
            zoomOrg=zoomOrg,
            keepPrevScale=keepPrevScale,
            fitWindow=fitWindow,
            fitWidth=fitWidth,
            brightnessContrast=brightnessContrast,
            zoomActions=zoomActions,
            openNextImg=openNextImg,
            openPrevImg=openPrevImg,
            fileMenuActions=(open_, opendir, save, saveAs, close, quit),
            tool=(),
            # XXX: need to add some actions here to activate the shortcut
            editMenu=(
                edit,
                duplicate,
                copy,
                paste,
                delete,
                None,
                undo,
                undoLastPoint,
                None,
                removePoint,
                None,
                toggle_keep_prev_mode,
            ),
            # menu shown at right click
            menu=(
                createMode,
                createRectangleMode,
                createCircleMode,
                createLineMode,
                createPointMode,
                createLineStripMode,
                createAiPolygonMode,
                createAiMaskMode,
                editMode,
                edit,
                duplicate,
                copy,
                paste,
                delete,
                undo,
                undoLastPoint,
                removePoint,
            ),
            onLoadActive=(
                close,
                createMode,
                createRectangleMode,
                createCircleMode,
                createLineMode,
                createPointMode,
                createLineStripMode,
                createAiPolygonMode,
                createAiMaskMode,
                editMode,
                brightnessContrast,
            ),
            onShapesPresent=(saveAs, hideAll, showAll, toggleAll),
        )

        self.canvas.vertexSelected.connect(self.actions.removePoint.setEnabled)

        self.menus = utils.struct(
            file=self.menu(self.tr("&File")),
            edit=self.menu(self.tr("&Edit")),
            view=self.menu(self.tr("&View")),
            help=self.menu(self.tr("&Help")),  # 显示帮助菜单
            recentFiles=QtWidgets.QMenu(self.tr("Open &Recent")),
            labelList=labelMenu,
        )

        utils.addActions(
            self.menus.file,
            (
                open_,
                openNextImg,
                openPrevImg,
                opendir,
                self.menus.recentFiles,
                save,
                saveAs,
                saveAuto,
                changeOutputDir,
                saveWithImageData,
                close,
                deleteFile,
                None,
                quit,
            ),
        )
        # 帮助菜单：只显示关于，不显示帮助子菜单
        utils.addActions(self.menus.help, (about,))
        utils.addActions(
            self.menus.view,
            (
                self.flag_dock.toggleViewAction(),
                self.label_dock.toggleViewAction(),
                self.shape_dock.toggleViewAction(),
                self.file_dock.toggleViewAction(),
                self.training_dock.toggleViewAction(),
                self.deploy_dock.toggleViewAction(),
                self.loss_curve_dock.toggleViewAction(),
                self.acc_curve_dock.toggleViewAction(),
                None,
                fill_drawing,
                None,
                hideAll,
                showAll,
                toggleAll,
                None,
                zoomIn,
                zoomOut,
                zoomOrg,
                keepPrevScale,
                None,
                fitWindow,
                fitWidth,
                None,
                brightnessContrast,
            ),
        )

        self.menus.file.aboutToShow.connect(self.updateFileMenu)

        # Custom context menu for the canvas widget:
        utils.addActions(self.canvas.menus[0], self.actions.menu)
        utils.addActions(
            self.canvas.menus[1],
            (
                action("&Copy here", self.copyShape),
                action("&Move here", self.moveShape),
            ),
        )

        selectAiModel = QtWidgets.QWidgetAction(self)
        selectAiModel.setDefaultWidget(QtWidgets.QWidget())
        selectAiModel.defaultWidget().setLayout(QtWidgets.QVBoxLayout())
        # 隐藏AI Mask Model控件
        selectAiModel.setVisible(False)
        #
        selectAiModelLabel = QtWidgets.QLabel(self.tr("AI Mask Model"))
        selectAiModelLabel.setAlignment(QtCore.Qt.AlignCenter)
        selectAiModel.defaultWidget().layout().addWidget(selectAiModelLabel)
        #
        self._selectAiModelComboBox = QtWidgets.QComboBox()
        selectAiModel.defaultWidget().layout().addWidget(self._selectAiModelComboBox)
        MODEL_NAMES: list[tuple[str, str]] = [
            ("efficientsam:10m", "EfficientSam (speed)"),
            ("efficientsam:latest", "EfficientSam (accuracy)"),
            ("sam:100m", "SegmentAnything (speed)"),
            ("sam:300m", "SegmentAnything (balanced)"),
            ("sam:latest", "SegmentAnything (accuracy)"),
            ("sam2:small", "Sam2 (speed)"),
            ("sam2:latest", "Sam2 (balanced)"),
            ("sam2:large", "Sam2 (accuracy)"),
        ]
        for model_name, model_ui_name in MODEL_NAMES:
            self._selectAiModelComboBox.addItem(model_ui_name, userData=model_name)
        model_ui_names: list[str] = [model_ui_name for _, model_ui_name in MODEL_NAMES]
        if self._config["ai"]["default"] in model_ui_names:
            model_index = model_ui_names.index(self._config["ai"]["default"])
        else:
            logger.warning(
                "Default AI model is not found: %r",
                self._config["ai"]["default"],
            )
            model_index = 0
        self._selectAiModelComboBox.setCurrentIndex(model_index)
        self._selectAiModelComboBox.currentIndexChanged.connect(
            lambda index: self.canvas.initializeAiModel(
                model_name=self._selectAiModelComboBox.itemData(index)
            )
            if self.canvas.createMode in ["ai_polygon", "ai_mask"]
            else None
        )

        self._ai_prompt_widget: QtWidgets.QWidget = AiPromptWidget(
            on_submit=self._submit_ai_prompt, parent=self
        )
        ai_prompt_action = QtWidgets.QWidgetAction(self)
        ai_prompt_action.setDefaultWidget(self._ai_prompt_widget)

        self.tools = self.toolbar("Tools")
        self.actions.tool = (
            open_,
            opendir,
            openPrevImg,
            openNextImg,
            save,
            deleteFile,
            None,
            createMode,
            editMode,
            duplicate,
            delete,
            undo,
            brightnessContrast,
            None,
            fitWindow,
            zoom,
            None,
            selectAiModel,
            None,
            ai_prompt_action,
        )

        self.statusBar().showMessage(str(self.tr("%s started.")) % __appname__)
        self.statusBar().show()

        if output_file is not None and self._config["auto_save"]:
            logger.warning(
                "If `auto_save` argument is True, `output_file` argument "
                "is ignored and output filename is automatically "
                "set as IMAGE_BASENAME.json."
            )
        self.output_file = output_file
        self.output_dir = output_dir

        # Application state.
        self.image = QtGui.QImage()
        self.imagePath = None
        self.recentFiles = []
        self.maxRecent = 7
        self.otherData = None
        self.zoom_level = 100
        self.fit_window = False
        self.zoom_values = {}  # key=filename, value=(zoom_mode, zoom_value)
        self.brightnessContrast_values = {}
        self.scroll_values = {
            Qt.Horizontal: {},
            Qt.Vertical: {},
        }  # key=filename, value=scroll_value

        if filename is not None and osp.isdir(filename):
            self.importDirImages(filename, load=False)
        else:
            self.filename = filename

        if config["file_search"]:
            self.fileSearch.setText(config["file_search"])
            self.fileSearchChanged()

        # XXX: Could be completely declarative.
        # Restore application settings.
        QtCore.QSettings.setPath(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            _get_app_dir(),
        )
        self.settings = QtCore.QSettings(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "labelme",
            "labelme",
        )
        self.recentFiles = self.settings.value("recentFiles", []) or []
        size = self.settings.value("window/size", QtCore.QSize(600, 500))
        position = self.settings.value("window/position", QtCore.QPoint(0, 0))
        state = self.settings.value("window/state", QtCore.QByteArray())
        
        # 智能屏幕检测：检查窗口位置是否在有效屏幕上
        adjusted_position = self._adjustWindowPosition(position, size)
        
        self.resize(size)
        self.move(adjusted_position)
        # or simply:
        # self.restoreGeometry(settings['window/geometry']
        self.restoreState(state)
        # 确保工具栏始终可见，避免 restoreState 恢复隐藏状态导致工具栏消失
        if hasattr(self, 'tools') and self.tools is not None:
            self.tools.setVisible(True)
        # 修复曲线 dock 被历史状态隐藏的问题
        self._ensure_training_curve_docks()

        # Populate the File menu dynamically.
        self.updateFileMenu()
        # Since loading the file may take some time,
        # make sure it runs in the background.
        if self.filename is not None:
            self.queueEvent(functools.partial(self.loadFile, self.filename))
        elif self.defaultImagesFolder and osp.exists(self.defaultImagesFolder) and osp.isdir(self.defaultImagesFolder):
            # Automatically load images from the default folder
            self.queueEvent(functools.partial(self.importDirImages, self.defaultImagesFolder, load=True))

        # Callbacks:
        self.zoomWidget.valueChanged.connect(self.paintCanvas)

        self.populateModeActions()

        # Initialize and start TCP client thread
        self.tcp_client = TcpClientThread(self)
        self.tcp_client.connection_status_changed.connect(self._on_tcp_status_changed)
        self.tcp_client.start()
        logger.info("TCP client thread started")

        # Initialize TrainingClientManager and connect to training widget
        from labelme.training_client_manager import TrainingClientManager
        self.training_client_manager = TrainingClientManager()
        self.training_widget.set_manager(self.training_client_manager)
        self._training_curve_history = {}

        # Connect training widget signals to slots
        self.training_widget.create_remote_task_requested.connect(self._on_create_remote_task_requested)
        self.training_widget.start_training_requested.connect(self._on_start_training_requested)
        self.training_widget.stop_training_requested.connect(self._on_stop_training_requested)
        self.training_widget.server_connect_requested.connect(self._on_server_connect_requested)
        self.training_widget.server_disconnect_requested.connect(self._on_server_disconnect_requested)
        self.training_widget.training_progress_updated.connect(self._on_training_progress_updated)

        logger.info("TrainingClientManager initialized")
        logger.info("TCP客户端线程已启动")
        QtCore.QTimer.singleShot(0, self._ensure_training_curve_docks)

        # self.firstStart = True
        # if self.firstStart:
        #    QWhatsThis.enterWhatsThisMode()

    def _adjustWindowPosition(self, position, size):
        """
        智能屏幕检测：检查窗口位置是否在有效屏幕上
        
        当应用程序启动时，检查指定的窗口位置是否在任何可用屏幕上。
        如果不在任何屏幕上，则将窗口移动到主屏幕的中心位置。
        
        Args:
            position: 窗口位置的QPoint对象
            size: 窗口大小的QSize对象
            
        Returns:
            QtCore.QPoint: 调整后的窗口位置
        """
        # 获取可用屏幕列表
        screens = QtWidgets.QApplication.screens()
        
        # 如果没有屏幕，使用默认位置
        if not screens:
            return position
        
        # 检查当前窗口位置是否在任何屏幕上
        window_rect = QtCore.QRect(position, size)
        screen_found = False
        
        for screen in screens:
            screen_geometry = screen.availableGeometry()
            # 检查窗口是否与屏幕有交集
            if window_rect.intersects(screen_geometry):
                screen_found = True
                break
        
        # 如果窗口位置不在任何屏幕上，移动到主屏幕中心
        if not screen_found:
            logger.info("窗口位置不在有效屏幕上，调整到主屏幕中心")
            main_screen = QtWidgets.QApplication.primaryScreen()
            if main_screen:
                screen_geometry = main_screen.availableGeometry()
                # 计算居中位置
                x = screen_geometry.center().x() - size.width() // 2
                y = screen_geometry.center().y() - size.height() // 2
                # 确保窗口不会超出屏幕边界
                x = max(screen_geometry.left(), min(x, screen_geometry.right() - size.width()))
                y = max(screen_geometry.top(), min(y, screen_geometry.bottom() - size.height()))
                return QtCore.QPoint(x, y)
        
        return position

    def _on_tcp_status_changed(self, connected: bool, message: str):
        """TCP 连接状态改变时的回调函数"""
        if connected:
            logger.info(f"TCP 状态：{message}")
        else:
            pass
            # logger.warning(f"TCP 状态：{message}")

    # ==================== Training Dock Signal Handlers ====================

    def _normalize_training_dataset_path(self, dataset_path):
        """校验并归一化训练数据集目录。"""
        dataset_path = (dataset_path or "").strip()
        if not dataset_path:
            return False, "请选择训练数据集目录", None

        normalized_path = osp.abspath(osp.normpath(dataset_path))
        if not osp.isdir(normalized_path):
            return False, f"数据集目录不存在：{normalized_path}", None

        candidate_dirs = [
            normalized_path,
            osp.join(normalized_path, "annotations"),
        ]
        for candidate_dir in candidate_dirs:
            train_json = osp.join(candidate_dir, "train.json")
            val_json = osp.join(candidate_dir, "val.json")
            if osp.isfile(train_json) and osp.isfile(val_json):
                return True, "", candidate_dir

        json_files = [
            name for name in os.listdir(normalized_path)
            if name.lower().endswith(".json")
        ]
        raw_labelme_jsons = [
            name for name in json_files
            if name.lower() not in {"train.json", "val.json"}
        ]
        if raw_labelme_jsons:
            return (
                False,
                "当前选择的是原始 Labelme 标注目录，缺少训练所需的 train.json 和 val.json。"
                " 请先将数据集转换并切分为训练格式，或选择包含这两个文件的目录。",
                None,
            )

        return (
            False,
            "数据集目录结构不正确。需要满足以下任一结构：\n"
            "1. <dataset>/train.json 和 <dataset>/val.json\n"
            "2. <dataset>/annotations/train.json 和 <dataset>/annotations/val.json",
            None,
        )

    def _on_create_remote_task_requested(self, params):
        """创建远程训练任务请求"""
        if self.training_client_manager:
            is_valid, error_message, normalized_dataset = self._normalize_training_dataset_path(
                params.get("dataset")
            )
            if not is_valid:
                logger.warning(f"训练任务创建被拦截：{error_message}")
                QtWidgets.QMessageBox.warning(self, "训练数据集错误", error_message)
                if hasattr(self, "training_widget") and self.training_widget:
                    self.training_widget.training_status_label.setText("数据集无效")
                    self.training_widget._log(error_message, "error")
                return

            params = dict(params)
            params["dataset"] = normalized_dataset
            self.training_client_manager.create_task(params)

    def _on_start_training_requested(self):
        """启动训练请求"""
        if self.training_client_manager:
            task_id = self.training_client_manager.get_current_task_id()
            if task_id:
                # 清除旧的曲线数据
                self.clear_training_curves()
                self.training_client_manager.start_training(task_id)

    def _on_stop_training_requested(self):
        """停止训练请求"""
        if self.training_client_manager:
            task_id = self.training_client_manager.get_current_task_id()
            if task_id:
                self.training_client_manager.stop_training(task_id)

    def _on_server_connect_requested(self, host, port):
        """连接服务器请求"""
        if self.training_client_manager:
            self.training_client_manager.connect_server(host, port)

    def _on_training_dock_visibility_changed(self, visible):
        """训练面板可见性变化"""
        if visible and hasattr(self, 'training_widget') and self.training_widget:
            # 面板显示时自动刷新任务列表
            logger.info("训练面板显示，自动刷新任务列表")
            self.training_widget.refresh_task_list()
    
    def _ensure_training_curve_docks(self):
        """确保训练曲线 dock 可见并处于可停靠区域"""
        for dock in (self.loss_curve_dock, self.acc_curve_dock):
            if not dock:
                continue
            if self.dockWidgetArea(dock) == Qt.NoDockWidgetArea and not dock.isFloating():
                self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        
        if (
            self.dockWidgetArea(self.loss_curve_dock) != Qt.NoDockWidgetArea
            and self.dockWidgetArea(self.acc_curve_dock) != Qt.NoDockWidgetArea
        ):
            self.splitDockWidget(self.loss_curve_dock, self.acc_curve_dock, Qt.Horizontal)
        
        self.show_training_curves(True)
        try:
            if self.loss_curve_dock.height() < 40 or self.acc_curve_dock.height() < 40:
                self.removeDockWidget(self.loss_curve_dock)
                self.removeDockWidget(self.acc_curve_dock)
                self.addDockWidget(Qt.BottomDockWidgetArea, self.loss_curve_dock)
                self.addDockWidget(Qt.BottomDockWidgetArea, self.acc_curve_dock)
                self.splitDockWidget(self.loss_curve_dock, self.acc_curve_dock, Qt.Horizontal)
            self.resizeDocks(
                [self.loss_curve_dock, self.acc_curve_dock],
                [220, 220],
                Qt.Vertical,
            )
        except Exception:
            pass
        self.loss_curve_dock.raise_()
        self.acc_curve_dock.raise_()
    
    def update_training_curves(self, epochs, losses, accuracies):
        """
        更新训练曲线
        
        Args:
            epochs: 轮次列表
            losses: 损失列表
            accuracies: 准确率列表
        """
        if hasattr(self, 'loss_curve_dock') and self.loss_curve_dock:
            self.loss_curve_dock.update_curve(epochs, losses)
        
        if hasattr(self, 'acc_curve_dock') and self.acc_curve_dock:
            self.acc_curve_dock.update_curve(epochs, accuracies)

    def _on_training_progress_updated(self, task_id, epoch, total_epochs, loss, accuracy):
        """训练进度更新时同步曲线"""
        history = self._training_curve_history.setdefault(
            task_id,
            {"epochs": [], "losses": [], "accuracies": []},
        )
        if history["epochs"] and history["epochs"][-1] == epoch:
            history["losses"][-1] = loss
            history["accuracies"][-1] = accuracy
        else:
            history["epochs"].append(epoch)
            history["losses"].append(loss)
            history["accuracies"].append(accuracy)

        short_id = task_id[:8] + "..." if task_id and len(task_id) > 8 else task_id
        if hasattr(self, 'loss_curve_dock') and self.loss_curve_dock:
            self.loss_curve_dock.update_task_curve(task_id, history["epochs"], history["losses"], label=short_id)

        if hasattr(self, 'acc_curve_dock') and self.acc_curve_dock:
            self.acc_curve_dock.update_task_curve(task_id, history["epochs"], history["accuracies"], label=short_id)
    
    def show_training_curves(self, show=True):
        """
        显示或隐藏训练曲线 dock
        
        Args:
            show: True 显示，False 隐藏
        """
        if hasattr(self, 'loss_curve_dock'):
            self.loss_curve_dock.setVisible(show)
        
        if hasattr(self, 'acc_curve_dock'):
            self.acc_curve_dock.setVisible(show)
    
    def clear_training_curves(self):
        """清除训练曲线"""
        if hasattr(self, 'loss_curve_dock') and self.loss_curve_dock:
            self.loss_curve_dock.clear_curve()
        
        if hasattr(self, 'acc_curve_dock') and self.acc_curve_dock:
            self.acc_curve_dock.clear_curve()
        self._training_curve_history = {}

    def _on_server_disconnect_requested(self):
        """断开服务器连接请求"""
        if self.training_client_manager:
            self.training_client_manager.disconnect_server()

    def menu(self, connected: bool, message: str):
        """
        TCP连接状态改变时的回调函数
        
        处理TCP客户端连接状态变化事件，记录连接状态信息。
        
        Args:
            connected: 布尔值，表示是否连接成功
            message: 连接状态的描述信息
        """
        if connected:
            logger.info(f"TCP状态: {message}")
        else:
            logger.warning(f"TCP状态: {message}")

    def menu(self, title, actions=None):
        """
        创建并返回一个菜单对象
        
        Args:
            title: 菜单标题
            actions: 菜单项列表
            
        Returns:
            QtWidgets.QMenu: 创建的菜单对象
        """
        menu = self.menuBar().addMenu(title)
        if actions:
            utils.addActions(menu, actions)
        return menu

    def toolbar(self, title, actions=None):
        """
        创建并返回一个工具栏对象
        
        Args:
            title: 工具栏标题
            actions: 工具栏按钮列表
            
        Returns:
            ToolBar: 创建的工具栏对象
        """
        toolbar = ToolBar(title)
        toolbar.setObjectName("%sToolBar" % title)
        # toolbar.setOrientation(Qt.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if actions:
            utils.addActions(toolbar, actions)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        return toolbar

    # Support Functions

    def noShapes(self):
        """
        检查是否没有任何标注形状
        
        Returns:
            bool: 如果没有标注形状返回True，否则返回False
        """
        return not len(self.labelList)

    def populateModeActions(self):
        """
        根据当前模式填充工具栏和菜单项
        
        根据当前的标注模式（多边形、矩形、圆形等）动态更新工具栏和编辑菜单，
        确保用户界面与当前操作模式保持一致。
        """
        tool, menu = self.actions.tool, self.actions.menu
        self.tools.clear()
        utils.addActions(self.tools, tool)
        self.canvas.menus[0].clear()
        utils.addActions(self.canvas.menus[0], menu)
        self.menus.edit.clear()
        actions = (
            self.actions.createMode,
            self.actions.createRectangleMode,
            self.actions.createCircleMode,
            self.actions.createLineMode,
            self.actions.createPointMode,
            self.actions.createLineStripMode,
            self.actions.createAiPolygonMode,
            self.actions.createAiMaskMode,
            self.actions.editMode,
        )
        utils.addActions(self.menus.edit, actions + self.actions.editMenu)

    def setDirty(self):
        """
        设置文件为未保存状态
        
        当文件内容发生变化时调用此方法，启用撤销功能和保存按钮，
        并更新窗口标题显示未保存状态。
        """
        # Even if we autosave the file, we keep the ability to undo
        self.actions.undo.setEnabled(self.canvas.isShapeRestorable)

        if self._config["auto_save"] or self.actions.saveAuto.isChecked():
            label_file = osp.splitext(self.imagePath)[0] + ".json"
            if self.output_dir:
                label_file_without_path = osp.basename(label_file)
                label_file = osp.join(self.output_dir, label_file_without_path)
            self.saveLabels(label_file)
            return
        self.dirty = True
        self.actions.save.setEnabled(True)
        title = __appname__
        if self.filename is not None:
            title = "{} - {}*".format(title, self.filename)
        self.setWindowTitle(title)

    def setClean(self):
        """
        设置文件为已保存状态
        
        当文件保存后调用此方法，禁用保存按钮，启用所有标注工具，
        并更新窗口标题显示已保存状态。
        """
        self.dirty = False
        self.actions.save.setEnabled(False)
        self.actions.createMode.setEnabled(True)
        self.actions.createRectangleMode.setEnabled(True)
        self.actions.createCircleMode.setEnabled(True)
        self.actions.createLineMode.setEnabled(True)
        self.actions.createPointMode.setEnabled(True)
        self.actions.createLineStripMode.setEnabled(True)
        self.actions.createAiPolygonMode.setEnabled(True)
        self.actions.createAiMaskMode.setEnabled(True)
        title = __appname__
        if self.filename is not None:
            title = "{} - {}".format(title, self.filename)
        self.setWindowTitle(title)

        if self.hasLabelFile():
            self.actions.deleteFile.setEnabled(True)
        else:
            self.actions.deleteFile.setEnabled(False)

    def toggleActions(self, value=True):
        """
        启用/禁用依赖于已打开图像的控件
        
        根据图像是否已加载来启用或禁用相关的工具栏按钮和菜单项，
        确保用户界面状态与当前操作环境保持一致。
        
        Args:
            value: 布尔值，True表示启用，False表示禁用
        """
        for z in self.actions.zoomActions:
            z.setEnabled(value)
        for action in self.actions.onLoadActive:
            action.setEnabled(value)

    def queueEvent(self, function):
        """
        将函数调用排队到事件循环中
        
        使用QTimer.singleShot(0, function)将函数调用延迟到下一个事件循环迭代，
        这样可以确保当前事件处理完成后才执行该函数。
        
        Args:
            function: 要排队执行的函数
        """
        QtCore.QTimer.singleShot(0, function)

    def status(self, message, delay=5000):
        """
        在状态栏显示消息
        
        在应用程序状态栏中显示指定的消息，可设置显示时间。
        
        Args:
            message: 要显示的消息文本
            delay: 消息显示的延迟时间（毫秒），默认5000ms
        """
        self.statusBar().showMessage(message, delay)

    def _submit_ai_prompt(self, _) -> None:
        """
        处理AI提示词提交事件
        
        使用YOLO World模型根据文本提示检测图像中的对象，并将检测结果转换为标注形状。
        支持非极大值抑制(NMS)来过滤重叠的检测框。
        
        Args:
            _: 未使用的参数，保持与回调函数签名一致
        """
        texts = self._ai_prompt_widget.get_text_prompt().split(",")
        boxes, scores, labels = bbox_from_text.get_bboxes_from_texts(
            model="yoloworld",
            image=utils.img_qt_to_arr(self.image)[:, :, :3],
            texts=texts,
        )

        for shape in self.canvas.shapes:
            if shape.shape_type != "rectangle" or shape.label not in texts:
                continue
            box = np.array(
                [
                    shape.points[0].x(),
                    shape.points[0].y(),
                    shape.points[1].x(),
                    shape.points[1].y(),
                ],
                dtype=np.float32,
            )
            boxes = np.r_[boxes, [box]]
            scores = np.r_[scores, [1.01]]
            labels = np.r_[labels, [texts.index(shape.label)]]

        boxes, scores, labels = bbox_from_text.nms_bboxes(
            boxes=boxes,
            scores=scores,
            labels=labels,
            iou_threshold=self._ai_prompt_widget.get_iou_threshold(),
            score_threshold=self._ai_prompt_widget.get_score_threshold(),
            max_num_detections=100,
        )

        keep = scores != 1.01
        boxes = boxes[keep]
        scores = scores[keep]
        labels = labels[keep]

        shape_dicts: list[dict] = bbox_from_text.get_shapes_from_bboxes(
            boxes=boxes,
            scores=scores,
            labels=labels,
            texts=texts,
        )

        shapes: list[Shape] = []
        for shape_dict in shape_dicts:
            shape = Shape(
                label=shape_dict["label"],
                shape_type=shape_dict["shape_type"],
                description=shape_dict["description"],
            )
            for point in shape_dict["points"]:
                shape.addPoint(QtCore.QPointF(*point))
            shapes.append(shape)

        self.canvas.storeShapes()
        self.loadShapes(shapes, replace=False)
        self.setDirty()

    def resetState(self):
        """
        重置应用程序状态
        
        清空所有标注数据和文件信息，将应用程序恢复到初始状态。
        用于文件切换或错误恢复时的状态重置。
        """
        self.labelList.clear()
        self.filename = None
        self.imagePath = None
        self.imageData = None
        self.labelFile = None
        self.otherData = None
        self.canvas.resetState()

    def currentItem(self):
        """
        获取当前选中的标注项
        
        Returns:
            LabelListWidgetItem: 当前选中的标注项，如果没有选中则返回None
        """
        items = self.labelList.selectedItems()
        if items:
            return items[0]
        return None

    def addRecentFile(self, filename):
        """
        添加文件到最近文件列表
        
        将指定的文件路径添加到最近打开文件列表的开头，如果文件已存在则移动到开头，
        如果列表长度超过最大限制则移除最旧的文件。
        
        Args:
            filename: 要添加的文件路径
        """
        if filename in self.recentFiles:
            self.recentFiles.remove(filename)
        elif len(self.recentFiles) >= self.maxRecent:
            self.recentFiles.pop()
        self.recentFiles.insert(0, filename)

    # Callbacks

    def undoShapeEdit(self):
        """
        撤销形状编辑操作
        
        恢复到上一次的形状状态，清空标注列表，重新加载画布中的形状，
        并根据是否可以撤销来启用或禁用撤销按钮。
        """
        self.canvas.restoreShape()
        self.labelList.clear()
        self.loadShapes(self.canvas.shapes)
        self.actions.undo.setEnabled(self.canvas.isShapeRestorable)

    def tutorial(self):
        """
        打开教程页面
        
        在默认浏览器中打开Labelme的官方教程页面，提供使用指导和帮助信息。
        """
        url = "https://github.com/labelmeai/labelme/tree/main/examples/tutorial"  # NOQA
        webbrowser.open(url)
    
    def showAbout(self):
        """显示关于窗口"""
        from labelme import __version__, __publish_time__
        # 原值: "<h2>Labelme</h2>"
        about_text = (
            "<h2>Heyfocus Label</h2>"
            "<p><b>版本号:</b> V{}</p>"
            "<p><b>发布时间:</b> {}</p>"
            "<p><b>公司:</b> 唯视智能信息科技(广州)有限公司</p>"
            "<p><b>官网:</b> https://www.heyfocustech.com/</p>"
            "<p>图像标注工具</p>"
        ).format(__version__, __publish_time__)
        QtWidgets.QMessageBox.about(self, self.tr("关于"), about_text)

    def toggleDrawingSensitive(self, drawing=True):
        """
        切换绘图敏感度
        
        在绘图过程中，禁用某些操作模式之间的切换，防止用户在绘制时意外改变操作模式。
        当正在绘图时，禁用编辑模式、撤销最后一点、撤销和删除操作。
        
        Args:
            drawing: 布尔值，True表示正在绘图，False表示不在绘图
        """
        self.actions.editMode.setEnabled(not drawing)
        self.actions.undoLastPoint.setEnabled(drawing)
        self.actions.undo.setEnabled(not drawing)
        self.actions.delete.setEnabled(not drawing)

    def toggleDrawMode(self, edit=True, createMode="polygon"):
        """
        切换绘图模式
        
        在编辑模式和各种绘图模式之间切换。支持的绘图模式包括：
        - 多边形 (polygon)
        - 矩形 (rectangle) 
        - 圆形 (circle)
        - 点 (point)
        - 线条 (line)
        - 线条带 (linestrip)
        - AI多边形 (ai_polygon)
        - AI掩码 (ai_mask)
        
        Args:
            edit: 布尔值，True表示切换到编辑模式，False表示切换到绘图模式
            createMode: 字符串，指定要创建的形状类型
        """
        draw_actions = {
            "polygon": self.actions.createMode,
            "rectangle": self.actions.createRectangleMode,
            "circle": self.actions.createCircleMode,
            "point": self.actions.createPointMode,
            "line": self.actions.createLineMode,
            "linestrip": self.actions.createLineStripMode,
            "ai_polygon": self.actions.createAiPolygonMode,
            "ai_mask": self.actions.createAiMaskMode,
        }

        self.canvas.setEditing(edit)
        self.canvas.createMode = createMode
        if edit:
            for draw_action in draw_actions.values():
                draw_action.setEnabled(True)
        else:
            for draw_mode, draw_action in draw_actions.items():
                draw_action.setEnabled(createMode != draw_mode)
        self.actions.editMode.setEnabled(not edit)

    def setEditMode(self):
        """
        设置为编辑模式
        
        切换到编辑模式，允许用户移动和编辑已选择的多边形。
        """
        self.toggleDrawMode(True)

    def updateFileMenu(self):
        """
        更新文件菜单中的最近文件列表
        
        动态更新文件菜单中的最近打开文件列表，显示最近访问的文件，
        并为每个文件创建一个快捷操作，点击后可以快速打开该文件。
        """
        current = self.filename

        def exists(filename):
            return osp.exists(str(filename))

        menu = self.menus.recentFiles
        menu.clear()
        files = [f for f in self.recentFiles if f != current and exists(f)]
        for i, f in enumerate(files):
            icon = utils.newIcon("labels")
            action = QtWidgets.QAction(
                icon, "&%d %s" % (i + 1, QtCore.QFileInfo(f).fileName()), self
            )
            action.triggered.connect(functools.partial(self.loadRecent, f))
            menu.addAction(action)

    def popLabelListMenu(self, point):
        """
        在标注列表上弹出上下文菜单
        
        在标注列表的指定位置弹出上下文菜单，提供编辑和删除等操作选项。
        
        Args:
            point: 弹出菜单的位置坐标
        """
        self.menus.labelList.exec_(self.labelList.mapToGlobal(point))

    def validateLabel(self, label):
        """
        验证标签的有效性
        
        根据配置的验证类型检查标签是否有效。支持的验证类型包括：
        - None: 不进行验证
        - "exact": 标签必须与预定义标签完全匹配
        
        Args:
            label: 要验证的标签文本
            
        Returns:
            bool: 如果标签有效返回True，否则返回False
        """
        # no validation
        if self._config["validate_label"] is None:
            return True

        for i in range(self.uniqLabelList.count()):
            label_i = self.uniqLabelList.item(i).data(Qt.UserRole)
            if self._config["validate_label"] in ["exact"]:
                if label_i == label:
                    return True
        return False

    def _edit_label(self, value=None):
        """
        编辑选中标注的标签信息
        
        打开标签编辑对话框，允许用户修改选中标注的标签文本、标志位、组ID和描述信息。
        支持批量编辑多个标注，只有当所有选中标注的对应属性相同时才会启用编辑。
        
        Args:
            value: 未使用的参数，保持与回调函数签名一致
        """
        if not self.canvas.editing():
            return

        items = self.labelList.selectedItems()
        if not items:
            logger.warning("No label is selected, so cannot edit label.")
            return

        shape = items[0].shape()

        if len(items) == 1:
            edit_text = True
            edit_flags = True
            edit_group_id = True
            edit_description = True
        else:
            edit_text = all(item.shape().label == shape.label for item in items[1:])
            edit_flags = all(item.shape().flags == shape.flags for item in items[1:])
            edit_group_id = all(
                item.shape().group_id == shape.group_id for item in items[1:]
            )
            edit_description = all(
                item.shape().description == shape.description for item in items[1:]
            )

        if not edit_text:
            self.labelDialog.edit.setDisabled(True)
            self.labelDialog.labelList.setDisabled(True)
        if not edit_flags:
            for i in range(self.labelDialog.flagsLayout.count()):
                self.labelDialog.flagsLayout.itemAt(i).setDisabled(True)
        if not edit_group_id:
            self.labelDialog.edit_group_id.setDisabled(True)
        if not edit_description:
            self.labelDialog.editDescription.setDisabled(True)

        text, flags, group_id, description = self.labelDialog.popUp(
            text=shape.label if edit_text else "",
            flags=shape.flags if edit_flags else None,
            group_id=shape.group_id if edit_group_id else None,
            description=shape.description if edit_description else None,
        )

        if not edit_text:
            self.labelDialog.edit.setDisabled(False)
            self.labelDialog.labelList.setDisabled(False)
        if not edit_flags:
            for i in range(self.labelDialog.flagsLayout.count()):
                self.labelDialog.flagsLayout.itemAt(i).setDisabled(False)
        if not edit_group_id:
            self.labelDialog.edit_group_id.setDisabled(False)
        if not edit_description:
            self.labelDialog.editDescription.setDisabled(False)

        if text is None:
            assert flags is None
            assert group_id is None
            assert description is None
            return

        if not self.validateLabel(text):
            self.errorMessage(
                self.tr("Invalid label"),
                self.tr("Invalid label '{}' with validation type '{}'").format(
                    text, self._config["validate_label"]
                ),
            )
            return

        self.canvas.storeShapes()
        for item in items:
            shape: Shape = item.shape()

            if edit_text:
                shape.label = text
            if edit_flags:
                shape.flags = flags
            if edit_group_id:
                shape.group_id = group_id
            if edit_description:
                shape.description = description

            self._update_shape_color(shape)
            if shape.group_id is None:
                item.setText(
                    '{} <font color="#{:02x}{:02x}{:02x}">●</font>'.format(
                        html.escape(shape.label), *shape.fill_color.getRgb()[:3]
                    )
                )
            else:
                item.setText("{} ({})".format(shape.label, shape.group_id))
            self.setDirty()
            if self.uniqLabelList.findItemByLabel(shape.label) is None:
                item = self.uniqLabelList.createItemFromLabel(shape.label)
                self.uniqLabelList.addItem(item)
                rgb = self._get_rgb_by_label(shape.label)
                self.uniqLabelList.setItemLabel(item, shape.label, rgb)

    def fileSearchChanged(self):
        """
        处理文件搜索框文本变化事件
        
        当用户在文件搜索框中输入文本时，根据搜索模式筛选并重新加载文件列表。
        支持正则表达式搜索，允许用户快速找到特定的文件。
        """
        self.importDirImages(
            self.lastOpenDir,
            pattern=self.fileSearch.text(),
            load=False,
        )

    def fileSelectionChanged(self):
        """
        处理文件列表选择变化事件

        当用户在文件列表中选择不同的文件时，加载选中的图像文件。
        确保在加载新文件前检查是否需要保存当前文件的更改。
        """
        file_path = self.fileListWidget.current_file
        if not file_path:
            return

        if not self.mayContinue():
            return

        currIndex = self.imageList.index(str(file_path))
        if currIndex < len(self.imageList):
            filename = self.imageList[currIndex]
            if filename:
                self.loadFile(filename)

    # React to canvas signals.
    def shapeSelectionChanged(self, selected_shapes):
        """
        处理画布上形状选择变化事件
        
        当用户在画布上选择或取消选择形状时，更新标注列表的选择状态，
        并根据选择的形状数量启用或禁用相应的操作按钮。
        
        Args:
            selected_shapes: 当前选中的形状列表
        """
        self._noSelectionSlot = True
        for shape in self.canvas.selectedShapes:
            shape.selected = False
        self.labelList.clearSelection()
        self.canvas.selectedShapes = selected_shapes
        for shape in self.canvas.selectedShapes:
            shape.selected = True
            item = self.labelList.findItemByShape(shape)
            self.labelList.selectItem(item)
            self.labelList.scrollToItem(item)
        self._noSelectionSlot = False
        n_selected = len(selected_shapes)
        self.actions.delete.setEnabled(n_selected)
        self.actions.duplicate.setEnabled(n_selected)
        self.actions.copy.setEnabled(n_selected)
        self.actions.edit.setEnabled(n_selected)

    def addLabel(self, shape):
        """
        向标注列表添加一个新的标注项
        
        创建标注列表项，设置颜色和文本显示，将标注添加到画布中，
        并更新相关的UI状态和操作按钮。
        
        Args:
            shape: 要添加的Shape对象
        """
        if shape.group_id is None:
            text = shape.label
        else:
            text = "{} ({})".format(shape.label, shape.group_id)
        label_list_item = LabelListWidgetItem(text, shape)
        self.labelList.addItem(label_list_item)
        if self.uniqLabelList.findItemByLabel(shape.label) is None:
            item = self.uniqLabelList.createItemFromLabel(shape.label)
            self.uniqLabelList.addItem(item)
            rgb = self._get_rgb_by_label(shape.label)
            self.uniqLabelList.setItemLabel(item, shape.label, rgb)
        self.labelDialog.addLabelHistory(shape.label)
        for action in self.actions.onShapesPresent:
            action.setEnabled(True)

        self._update_shape_color(shape)
        label_list_item.setText(
            '{} <font color="#{:02x}{:02x}{:02x}">●</font>'.format(
                html.escape(text), *shape.fill_color.getRgb()[:3]
            )
        )

    def _update_shape_color(self, shape):
        """
        更新形状的颜色属性
        
        根据标签名称获取对应的颜色，并设置形状的各种颜色属性，
        包括线条颜色、顶点颜色、填充颜色等。
        
        Args:
            shape: 要更新颜色的Shape对象
        """
        r, g, b = self._get_rgb_by_label(shape.label)
        shape.line_color = QtGui.QColor(r, g, b)
        shape.vertex_fill_color = QtGui.QColor(r, g, b)
        shape.hvertex_fill_color = QtGui.QColor(255, 255, 255)
        shape.fill_color = QtGui.QColor(r, g, b, 128)
        shape.select_line_color = QtGui.QColor(255, 255, 255)
        shape.select_fill_color = QtGui.QColor(r, g, b, 155)

    def _get_rgb_by_label(self, label):
        """
        根据标签名称获取对应的颜色值
        
        根据配置的颜色模式获取标签对应的颜色：
        1. 自动模式：使用预定义的颜色映射表
        2. 手动模式：使用配置文件中指定的颜色
        3. 默认模式：使用全局默认颜色
        
        Args:
            label: 标签名称字符串
            
        Returns:
            tuple: RGB颜色值 (r, g, b)
        """
        if self._config["shape_color"] == "auto":
            item = self.uniqLabelList.findItemByLabel(label)
            if item is None:
                item = self.uniqLabelList.createItemFromLabel(label)
                self.uniqLabelList.addItem(item)
                rgb = self._get_rgb_by_label(label)
                self.uniqLabelList.setItemLabel(item, label, rgb)
            label_id = self.uniqLabelList.indexFromItem(item).row() + 1
            label_id += self._config["shift_auto_shape_color"]
            return LABEL_COLORMAP[label_id % len(LABEL_COLORMAP)]
        elif (
            self._config["shape_color"] == "manual"
            and self._config["label_colors"]
            and label in self._config["label_colors"]
        ):
            return self._config["label_colors"][label]
        elif self._config["default_shape_color"]:
            return self._config["default_shape_color"]
        return (0, 255, 0)

    def remLabels(self, shapes):
        """
        从标注列表中移除指定的标注项
        
        遍历给定的形状列表，从标注列表中找到对应的列表项并移除。
        通常在删除标注时调用此方法。
        
        Args:
            shapes: 要移除的Shape对象列表
        """
        for shape in shapes:
            item = self.labelList.findItemByShape(shape)
            self.labelList.removeItem(item)

    def loadShapes(self, shapes, replace=True):
        """
        加载形状列表到画布和标注列表
        
        将给定的形状列表添加到标注列表中，并加载到画布上。
        可选择是否替换现有的形状。
        
        Args:
            shapes: Shape对象列表
            replace: 布尔值，True表示替换现有形状，False表示追加
        """
        self._noSelectionSlot = True
        for shape in shapes:
            self.addLabel(shape)
        self.labelList.clearSelection()
        self._noSelectionSlot = False
        self.canvas.loadShapes(shapes, replace=replace)

    def loadLabels(self, shapes):
        """
        从形状数据列表加载标注信息
        
        将字典格式的形状数据转换为Shape对象并加载到画布中。
        处理形状的各种属性，包括标签、点坐标、形状类型、标志位等。
        
        Args:
            shapes: 包含形状数据的字典列表
        """
        s = []
        for shape in shapes:
            label = shape["label"]
            points = shape["points"]
            shape_type = shape["shape_type"]
            flags: dict = shape["flags"] or {}
            description = shape.get("description", "")
            group_id = shape["group_id"]
            other_data = shape["other_data"]

            if not points:
                # skip point-empty shape
                continue

            shape = Shape(
                label=label,
                shape_type=shape_type,
                group_id=group_id,
                description=description,
                mask=shape["mask"],
            )
            for x, y in points:
                shape.addPoint(QtCore.QPointF(x, y))
            shape.close()

            default_flags = {}
            if self._config["label_flags"]:
                for pattern, keys in self._config["label_flags"].items():
                    if re.match(pattern, label):
                        for key in keys:
                            default_flags[key] = False
            shape.flags = default_flags
            shape.flags.update(flags)
            shape.other_data = other_data

            s.append(shape)
        self.loadShapes(s)

    def loadFlags(self, flags):
        self.flag_widget.clear()
        for key, flag in flags.items():
            item = QtWidgets.QListWidgetItem(key)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if flag else Qt.Unchecked)
            self.flag_widget.addItem(item)

    def saveLabels(self, filename):
        """
        保存标注数据到指定文件
        
        将当前的标注形状、标志位和其他数据保存到LabelFile格式的JSON文件中。
        支持保存图像数据（可选）和各种形状属性。
        
        Args:
            filename: 要保存的文件路径
            
        Returns:
            bool: 保存成功返回True，失败返回False
        """
        lf = LabelFile()

        def format_shape(s):
            data = s.other_data.copy()
            data.update(
                dict(
                    label=s.label,
                    points=[(p.x(), p.y()) for p in s.points],
                    group_id=s.group_id,
                    description=s.description,
                    shape_type=s.shape_type,
                    flags=s.flags,
                    mask=None
                    if s.mask is None
                    else utils.img_arr_to_b64(s.mask.astype(np.uint8)),
                )
            )
            return data

        shapes = [format_shape(item.shape()) for item in self.labelList]
        flags = {}
        for i in range(self.flag_widget.count()):
            item = self.flag_widget.item(i)
            key = item.text()
            flag = item.checkState() == Qt.Checked
            flags[key] = flag
        try:
            imagePath = osp.relpath(self.imagePath, osp.dirname(filename))
            imageData = self.imageData if self._config["store_data"] else None
            if osp.dirname(filename) and not osp.exists(osp.dirname(filename)):
                os.makedirs(osp.dirname(filename))
            lf.save(
                filename=filename,
                shapes=shapes,
                imagePath=imagePath,
                imageData=imageData,
                imageHeight=self.image.height(),
                imageWidth=self.image.width(),
                otherData=self.otherData,
                flags=flags,
            )
            self.labelFile = lf
            # 缩略图列表不支持查找，使用 imagePath 直接判断
            if self.imagePath in self.fileListWidget.file_paths:
                pass  # 文件已存在，不需要额外操作
            # disable allows next and previous image to proceed
            # self.filename = filename
            return True
        except LabelFileError as e:
            self.errorMessage(
                self.tr("Error saving label data"), self.tr("<b>%s</b>") % e
            )
            return False

    def duplicateSelectedShape(self):
        self.copySelectedShape()
        self.pasteSelectedShape()

    def pasteSelectedShape(self):
        self.loadShapes(self._copied_shapes, replace=False)
        self.setDirty()

    def copySelectedShape(self):
        self._copied_shapes = [s.copy() for s in self.canvas.selectedShapes]
        self.actions.paste.setEnabled(len(self._copied_shapes) > 0)

    def labelSelectionChanged(self):
        if self._noSelectionSlot:
            return
        if self.canvas.editing():
            selected_shapes = []
            for item in self.labelList.selectedItems():
                selected_shapes.append(item.shape())
            if selected_shapes:
                self.canvas.selectShapes(selected_shapes)
            else:
                self.canvas.deSelectShape()

    def labelItemChanged(self, item):
        shape = item.shape()
        self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)

    def labelOrderChanged(self):
        self.setDirty()
        self.canvas.loadShapes([item.shape() for item in self.labelList])

    # Callback functions:

    def newShape(self):
        """Pop-up and give focus to the label editor.

        position MUST be in global coordinates.
        """
        items = self.uniqLabelList.selectedItems()
        text = None
        if items:
            text = items[0].data(Qt.UserRole)
        flags = {}
        group_id = None
        description = ""
        if self._config["display_label_popup"] or not text:
            previous_text = self.labelDialog.edit.text()
            text, flags, group_id, description = self.labelDialog.popUp(text)
            if not text:
                self.labelDialog.edit.setText(previous_text)

        if text and not self.validateLabel(text):
            self.errorMessage(
                self.tr("Invalid label"),
                self.tr("Invalid label '{}' with validation type '{}'").format(
                    text, self._config["validate_label"]
                ),
            )
            text = ""
        if text:
            self.labelList.clearSelection()
            shape = self.canvas.setLastLabel(text, flags)
            shape.group_id = group_id
            shape.description = description
            self.addLabel(shape)
            self.actions.editMode.setEnabled(True)
            self.actions.undoLastPoint.setEnabled(False)
            self.actions.undo.setEnabled(True)
            self.setDirty()
        else:
            self.canvas.undoLastLine()
            self.canvas.shapesBackups.pop()

    def scrollRequest(self, delta, orientation):
        units = -delta * 0.1  # natural scroll
        bar = self.scrollBars[orientation]
        value = bar.value() + bar.singleStep() * units
        self.setScroll(orientation, value)

    def setScroll(self, orientation, value):
        self.scrollBars[orientation].setValue(int(value))
        self.scroll_values[orientation][self.filename] = value

    def setZoom(self, value):
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)
        self.zoom_values[self.filename] = (self.zoomMode, value)

    def addZoom(self, increment=1.1):
        zoom_value = self.zoomWidget.value() * increment
        if increment > 1:
            zoom_value = math.ceil(zoom_value)
        else:
            zoom_value = math.floor(zoom_value)
        self.setZoom(zoom_value)

    def zoomRequest(self, delta, pos):
        canvas_width_old = self.canvas.width()
        units = 1.1
        if delta < 0:
            units = 0.9
        self.addZoom(units)

        canvas_width_new = self.canvas.width()
        if canvas_width_old != canvas_width_new:
            canvas_scale_factor = canvas_width_new / canvas_width_old

            x_shift = round(pos.x() * canvas_scale_factor) - pos.x()
            y_shift = round(pos.y() * canvas_scale_factor) - pos.y()

            self.setScroll(
                Qt.Horizontal,
                self.scrollBars[Qt.Horizontal].value() + x_shift,
            )
            self.setScroll(
                Qt.Vertical,
                self.scrollBars[Qt.Vertical].value() + y_shift,
            )

    def setFitWindow(self, value=True):
        if value:
            self.actions.fitWidth.setChecked(False)
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):
        if value:
            self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjustScale()

    def enableKeepPrevScale(self, enabled):
        self._config["keep_prev_scale"] = enabled
        self.actions.keepPrevScale.setChecked(enabled)

    def onNewBrightnessContrast(self, qimage):
        self.canvas.loadPixmap(QtGui.QPixmap.fromImage(qimage), clear_shapes=False)

    def brightnessContrast(self, value):
        dialog = BrightnessContrastDialog(
            utils.img_data_to_pil(self.imageData),
            self.onNewBrightnessContrast,
            parent=self,
        )
        brightness, contrast = self.brightnessContrast_values.get(
            self.filename, (None, None)
        )
        if brightness is not None:
            dialog.slider_brightness.setValue(brightness)
        if contrast is not None:
            dialog.slider_contrast.setValue(contrast)
        dialog.exec_()

        brightness = dialog.slider_brightness.value()
        contrast = dialog.slider_contrast.value()
        self.brightnessContrast_values[self.filename] = (brightness, contrast)

    def togglePolygons(self, value):
        flag = value
        for item in self.labelList:
            if value is None:
                flag = item.checkState() == Qt.Unchecked
            item.setCheckState(Qt.Checked if flag else Qt.Unchecked)

    def loadFile(self, filename=None):
        """Load the specified file, or the last opened file if None."""
        # changing fileListWidget loads file
        if filename in self.imageList and (
            self.fileListWidget.current_file != filename
        ):
            self.fileListWidget.setCurrentFile(filename)
            return

        self.resetState()
        self.canvas.setEnabled(False)
        if filename is None:
            filename = self.settings.value("filename", "")
        filename = str(filename)
        if not QtCore.QFile.exists(filename):
            self.errorMessage(
                self.tr("Error opening file"),
                self.tr("No such file: <b>%s</b>") % filename,
            )
            return False
        # assumes same name, but json extension
        self.status(str(self.tr("Loading %s...")) % osp.basename(str(filename)))
        label_file = osp.splitext(filename)[0] + ".json"
        if self.output_dir:
            label_file_without_path = osp.basename(label_file)
            label_file = osp.join(self.output_dir, label_file_without_path)
        if QtCore.QFile.exists(label_file) and LabelFile.is_label_file(label_file):
            try:
                self.labelFile = LabelFile(label_file)
            except LabelFileError as e:
                self.errorMessage(
                    self.tr("Error opening file"),
                    self.tr(
                        "<p><b>%s</b></p>"
                        "<p>Make sure <i>%s</i> is a valid label file."
                    )
                    % (e, label_file),
                )
                self.status(self.tr("Error reading %s") % label_file)
                return False
            self.imageData = self.labelFile.imageData
            self.imagePath = osp.join(
                osp.dirname(label_file),
                self.labelFile.imagePath,
            )
            self.otherData = self.labelFile.otherData
        else:
            self.imageData = LabelFile.load_image_file(filename)
            if self.imageData:
                self.imagePath = filename
            self.labelFile = None

        # 检查 imageData 是否为 None，避免崩溃
        if self.imageData is None:
            self.errorMessage(
                self.tr("Error opening file"),
                self.tr("无法读取图像数据：<b>%s</b>") % filename,
            )
            self.status(self.tr("Error reading %s") % filename)
            return False

        try:
            image = QtGui.QImage.fromData(self.imageData)
        except Exception as e:
            logger.error(f"从数据创建图像失败：{e}")
            self.errorMessage(
                self.tr("Error opening file"),
                self.tr("图像数据格式错误：<b>%s</b>") % filename,
            )
            self.status(self.tr("Error reading %s") % filename)
            return False

        if image.isNull():
            formats = [
                "*.{}".format(fmt.data().decode())
                for fmt in QtGui.QImageReader.supportedImageFormats()
            ]
            self.errorMessage(
                self.tr("Error opening file"),
                self.tr(
                    "<p>Make sure <i>{0}</i> is a valid image file.<br/>"
                    "Supported image formats: {1}</p>"
                ).format(filename, ",".join(formats)),
            )
            self.status(self.tr("Error reading %s") % filename)
            return False
        self.image = image
        self.filename = filename
        if self._config["keep_prev"]:
            prev_shapes = self.canvas.shapes
        self.canvas.loadPixmap(QtGui.QPixmap.fromImage(image))
        flags = {k: False for k in self._config["flags"] or []}
        if self.labelFile:
            self.loadLabels(self.labelFile.shapes)
            if self.labelFile.flags is not None:
                flags.update(self.labelFile.flags)
        self.loadFlags(flags)
        if self._config["keep_prev"] and self.noShapes():
            self.loadShapes(prev_shapes, replace=False)
            self.setDirty()
        else:
            self.setClean()
        self.canvas.setEnabled(True)
        # set zoom values
        is_initial_load = not self.zoom_values
        if self.filename in self.zoom_values:
            self.zoomMode = self.zoom_values[self.filename][0]
            self.setZoom(self.zoom_values[self.filename][1])
        elif is_initial_load or not self._config["keep_prev_scale"]:
            self.adjustScale(initial=True)
        # set scroll values
        for orientation in self.scroll_values:
            if self.filename in self.scroll_values[orientation]:
                self.setScroll(
                    orientation, self.scroll_values[orientation][self.filename]
                )
        # set brightness contrast values
        try:
            dialog = BrightnessContrastDialog(
                utils.img_data_to_pil(self.imageData),
                self.onNewBrightnessContrast,
                parent=self,
            )
        except Exception as e:
            logger.warning(f"创建亮度对比度对话框失败：{e}")
            dialog = None

        brightness, contrast = self.brightnessContrast_values.get(
            self.filename, (None, None)
        )
        if self._config["keep_prev_brightness"] and self.recentFiles:
            brightness, _ = self.brightnessContrast_values.get(
                self.recentFiles[0], (None, None)
            )
        if self._config["keep_prev_contrast"] and self.recentFiles:
            _, contrast = self.brightnessContrast_values.get(
                self.recentFiles[0], (None, None)
            )
        if dialog is not None:
            if brightness is not None:
                dialog.slider_brightness.setValue(brightness)
            if contrast is not None:
                dialog.slider_contrast.setValue(contrast)
            self.brightnessContrast_values[self.filename] = (brightness, contrast)
        if brightness is not None or contrast is not None:
            dialog.onNewValue(None)
        self.paintCanvas()
        self.addRecentFile(self.filename)
        self.toggleActions(True)
        self.canvas.setFocus()
        self.status(str(self.tr("Loaded %s")) % osp.basename(str(filename)))
        return True

    def resizeEvent(self, event):
        if (
            self.canvas
            and not self.image.isNull()
            and self.zoomMode != self.MANUAL_ZOOM
        ):
            self.adjustScale()
        super(MainWindow, self).resizeEvent(event)

    def paintCanvas(self):
        assert not self.image.isNull(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoomWidget.value()
        self.canvas.adjustSize()
        self.canvas.update()

    def adjustScale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        value = int(100 * value)
        self.zoomWidget.setValue(value)
        self.zoom_values[self.filename] = (self.zoomMode, value)

    def scaleFitWindow(self):
        """Figure out the size of the pixmap to fit the main widget."""
        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scaleFitWidth(self):
        # The epsilon does not seem to work too well here.
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def enableSaveImageWithData(self, enabled):
        self._config["store_data"] = enabled
        self.actions.saveWithImageData.setChecked(enabled)

    def closeEvent(self, event):
        if not self.mayContinue():
            event.ignore()
            return
        
        # Stop TCP client thread before closing
        if hasattr(self, 'tcp_client') and self.tcp_client is not None:
            logger.info("正在停止TCP客户端...")
            self.tcp_client.stop()
            self.tcp_client = None
        
        # 保存窗口位置和大小
        self.settings.setValue("filename", self.filename if self.filename else "")
        self.settings.setValue("window/size", self.size())
        self.settings.setValue("window/position", self.pos())
        self.settings.setValue("window/state", self.saveState())
        self.settings.setValue("recentFiles", self.recentFiles)
        # ask the use for where to save the labels
        # self.settings.setValue('window/geometry', self.saveGeometry())

    def dragEnterEvent(self, event):
        extensions = [
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]
        if event.mimeData().hasUrls():
            items = [i.toLocalFile() for i in event.mimeData().urls()]
            if any([i.lower().endswith(tuple(extensions)) for i in items]):
                event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not self.mayContinue():
            event.ignore()
            return
        items = [i.toLocalFile() for i in event.mimeData().urls()]
        self.importDroppedImageFiles(items)

    # User Dialogs #

    def loadRecent(self, filename):
        if self.mayContinue():
            self.loadFile(filename)

    def openPrevImg(self, _value=False):
        keep_prev = self._config["keep_prev"]
        if QtWidgets.QApplication.keyboardModifiers() == (
            Qt.ControlModifier | Qt.ShiftModifier
        ):
            self._config["keep_prev"] = True

        if not self.mayContinue():
            return

        if len(self.imageList) <= 0:
            return

        if self.filename is None:
            return

        currIndex = self.imageList.index(self.filename)
        if currIndex - 1 >= 0:
            filename = self.imageList[currIndex - 1]
            if filename:
                self.loadFile(filename)

        self._config["keep_prev"] = keep_prev

    def openNextImg(self, _value=False, load=True):
        keep_prev = self._config["keep_prev"]
        if QtWidgets.QApplication.keyboardModifiers() == (
            Qt.ControlModifier | Qt.ShiftModifier
        ):
            self._config["keep_prev"] = True

        if not self.mayContinue():
            return

        if len(self.imageList) <= 0:
            return

        filename = None
        if self.filename is None:
            filename = self.imageList[0]
        else:
            currIndex = self.imageList.index(self.filename)
            if currIndex + 1 < len(self.imageList):
                filename = self.imageList[currIndex + 1]
            else:
                filename = self.imageList[-1]
        self.filename = filename

        if self.filename and load:
            self.loadFile(self.filename)

        self._config["keep_prev"] = keep_prev

    def openFile(self, _value=False):
        if not self.mayContinue():
            return
        path = osp.dirname(str(self.filename)) if self.filename else "."
        formats = [
            "*.{}".format(fmt.data().decode())
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]
        filters = self.tr("Image & Label files (%s)") % " ".join(
            formats + ["*%s" % LabelFile.suffix]
        )
        fileDialog = FileDialogPreview(self)
        fileDialog.setFileMode(FileDialogPreview.ExistingFile)
        fileDialog.setNameFilter(filters)
        fileDialog.setWindowTitle(
            self.tr("%s - Choose Image or Label file") % __appname__,
        )
        fileDialog.setWindowFilePath(path)
        fileDialog.setViewMode(FileDialogPreview.Detail)
        if fileDialog.exec_():
            fileName = fileDialog.selectedFiles()[0]
            if fileName:
                self.loadFile(fileName)

    def changeOutputDirDialog(self, _value=False):
        default_output_dir = self.output_dir
        if default_output_dir is None and self.filename:
            default_output_dir = osp.dirname(self.filename)
        if default_output_dir is None:
            default_output_dir = self.currentPath()

        output_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            self.tr("%s - Save/Load Annotations in Directory") % __appname__,
            default_output_dir,
            QtWidgets.QFileDialog.ShowDirsOnly
            | QtWidgets.QFileDialog.DontResolveSymlinks,
        )
        output_dir = str(output_dir)

        if not output_dir:
            return

        self.output_dir = output_dir

        self.statusBar().showMessage(
            self.tr("%s . Annotations will be saved/loaded in %s")
            % ("Change Annotations Dir", self.output_dir)
        )
        self.statusBar().show()

        current_filename = self.filename
        self.importDirImages(self.lastOpenDir, load=False)

        if current_filename in self.imageList:
            # retain currently selected file
            self.fileListWidget.setCurrentFile(current_filename)

    def saveFile(self, _value=False):
        assert not self.image.isNull(), "cannot save empty image"
        if self.labelFile:
            # DL20180323 - overwrite when in directory
            self._saveFile(self.labelFile.filename)
        elif self.output_file:
            self._saveFile(self.output_file)
            self.close()
        else:
            self._saveFile(self.saveFileDialog())

    def saveFileAs(self, _value=False):
        assert not self.image.isNull(), "cannot save empty image"
        self._saveFile(self.saveFileDialog())

    def saveFileDialog(self):
        caption = self.tr("%s - Choose File") % __appname__
        filters = self.tr("Label files (*%s)") % LabelFile.suffix
        if self.output_dir:
            dlg = QtWidgets.QFileDialog(self, caption, self.output_dir, filters)
        else:
            dlg = QtWidgets.QFileDialog(self, caption, self.currentPath(), filters)
        dlg.setDefaultSuffix(LabelFile.suffix[1:])
        dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dlg.setOption(QtWidgets.QFileDialog.DontConfirmOverwrite, False)
        dlg.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, False)
        basename = osp.basename(osp.splitext(self.filename)[0])
        if self.output_dir:
            default_labelfile_name = osp.join(
                self.output_dir, basename + LabelFile.suffix
            )
        else:
            default_labelfile_name = osp.join(
                self.currentPath(), basename + LabelFile.suffix
            )
        filename = dlg.getSaveFileName(
            self,
            self.tr("Choose File"),
            default_labelfile_name,
            self.tr("Label files (*%s)") % LabelFile.suffix,
        )
        if isinstance(filename, tuple):
            filename, _ = filename
        return filename

    def _saveFile(self, filename):
        if filename and self.saveLabels(filename):
            self.addRecentFile(filename)
            self.setClean()

    def closeFile(self, _value=False):
        if not self.mayContinue():
            return
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)

    def getLabelFile(self):
        if self.filename.lower().endswith(".json"):
            label_file = self.filename
        else:
            label_file = osp.splitext(self.filename)[0] + ".json"

        return label_file

    def deleteFile(self):
        mb = QtWidgets.QMessageBox
        msg = self.tr(
            "You are about to permanently delete this label file, " "proceed anyway?"
        )
        answer = mb.warning(self, self.tr("Attention"), msg, mb.Yes | mb.No)
        if answer != mb.Yes:
            return

        label_file = self.getLabelFile()
        if osp.exists(label_file):
            os.remove(label_file)
            logger.info("Label file is removed: {}".format(label_file))

            # 缩略图列表不支持 currentItem，使用 current_file
            if self.fileListWidget.current_file:
                pass  # 不需要额外的检查状态操作

            self.resetState()

    # Message Dialogs. #
    def hasLabels(self):
        if self.noShapes():
            self.errorMessage(
                "No objects labeled",
                "You must label at least one object to save the file.",
            )
            return False
        return True

    def hasLabelFile(self):
        if self.filename is None:
            return False

        label_file = self.getLabelFile()
        return osp.exists(label_file)

    def mayContinue(self):
        if not self.dirty:
            return True
        mb = QtWidgets.QMessageBox
        msg = self.tr('Save annotations to "{}" before closing?').format(self.filename)
        answer = mb.question(
            self,
            self.tr("Save annotations?"),
            msg,
            mb.Save | mb.Discard | mb.Cancel,
            mb.Save,
        )
        if answer == mb.Discard:
            return True
        elif answer == mb.Save:
            self.saveFile()
            return True
        else:  # answer == mb.Cancel
            return False

    def errorMessage(self, title, message):
        return QtWidgets.QMessageBox.critical(
            self, title, "<p><b>%s</b></p>%s" % (title, message)
        )

    def currentPath(self):
        return osp.dirname(str(self.filename)) if self.filename else "."

    def _loadDefaultImagesFolder(self):
        """Load default images folder path from JSON config file."""
        # Try to find config file in application directory
        app_dir = _get_app_dir()
        config_file = osp.join(app_dir, "labelme_config.json")
        default_folder = "images"
        
        try:
            if osp.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if "default_images_folder" in config:
                        folder_path = config["default_images_folder"]
                        # If it's a relative path, make it relative to project root
                        if not osp.isabs(folder_path):
                            folder_path = osp.join(project_root, folder_path)
                        default_folder = folder_path
        except Exception as e:
            logger.warning("Failed to load config file: %s", e)
        
        return default_folder

    def _saveDefaultImagesFolder(self, folder_path):
        """Save default images folder path to JSON config file."""
        app_dir = _get_app_dir()
        config_file = osp.join(app_dir, "labelme_config.json")
        
        try:
            # Temporarily remove watcher to avoid triggering on our own save
            if config_file in self.fileWatcher.files():
                self.fileWatcher.removePath(config_file)
            
            config = {}
            if osp.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
            
            # Try to save as relative path if possible
            try:
                relative_path = osp.relpath(folder_path, app_dir)
                # Only use relative path if it doesn't go outside project root
                if not relative_path.startswith(".."):
                    config["default_images_folder"] = relative_path
                else:
                    config["default_images_folder"] = folder_path
            except ValueError:
                # If relative path calculation fails, use absolute path
                config["default_images_folder"] = folder_path
            
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.defaultImagesFolder = folder_path
            logger.info("Saved default images folder to config: %s", folder_path)
            
            # Re-add watcher
            if osp.exists(config_file):
                self.fileWatcher.addPath(config_file)
        except Exception as e:
            logger.warning("Failed to save config file: %s", e)
    
    def _setupFileWatcher(self):
        """Setup file system watcher for config file and images folder."""
        app_dir = _get_app_dir()
        config_file = osp.join(app_dir, "labelme_config.json")
        
        # Watch config file. If it doesn't exist, watch its parent directory.
        if osp.exists(config_file):
            self.fileWatcher.addPath(config_file)
            logger.info("Watching config file: %s", config_file)
        else:
            # If the file doesn't exist, watch the directory it should be in.
            # This allows us to detect when it's created.
            config_dir = osp.dirname(config_file)
            if osp.exists(config_dir):
                self.fileWatcher.addPath(config_dir)
                logger.info("Config file not found. Watching directory: %s", config_dir)
        
        # Watch images folder if it exists
        if self.defaultImagesFolder and osp.exists(self.defaultImagesFolder) and osp.isdir(self.defaultImagesFolder):
            self.fileWatcher.addPath(self.defaultImagesFolder)
            logger.info("Watching images folder: %s", self.defaultImagesFolder)
        
        # Connect signals
        self.fileWatcher.fileChanged.connect(self._onConfigFileChanged)
        self.fileWatcher.directoryChanged.connect(self._onDirectoryChanged)
    
    def _onConfigFileChanged(self, path):
        """Handle config file changes."""
        logger.info("Config file changed: %s", path)
        
        # Reload config
        new_folder = self._loadDefaultImagesFolder()
        
        # If folder path changed, update watcher and reload images
        if new_folder != self.defaultImagesFolder:
            # Remove old folder from watcher
            if self.defaultImagesFolder and osp.exists(self.defaultImagesFolder):
                try:
                    self.fileWatcher.removePath(self.defaultImagesFolder)
                except Exception:
                    pass
            
            # Update folder path
            self.defaultImagesFolder = new_folder
            
            # Add new folder to watcher
            if new_folder and osp.exists(new_folder) and osp.isdir(new_folder):
                try:
                    self.fileWatcher.addPath(new_folder)
                    logger.info("Now watching new images folder: %s", new_folder)
                except Exception as e:
                    logger.warning("Failed to watch new folder: %s", e)
            
            # Reload images from new folder if it's the current directory
            if self.lastOpenDir == self.defaultImagesFolder or (
                not self.lastOpenDir and new_folder and osp.exists(new_folder) and osp.isdir(new_folder)
            ):
                self.queueEvent(functools.partial(self.importDirImages, new_folder, load=False))
                self.status(self.tr("Config updated, reloaded images from: %s") % new_folder)
    
    def _onDirectoryChanged(self, path):
        """Handle directory changes for both config and images folder."""
        app_dir = _get_app_dir()
        config_file = osp.join(app_dir, "labelme_config.json")
        config_dir = osp.dirname(config_file)

        # Case 1: The config directory changed, check if the config file was created.
        if path == config_dir and osp.exists(config_file):
            logger.info("Config file created: %s", config_file)
            # Stop watching the directory and start watching the file.
            self.fileWatcher.removePath(config_dir)
            self.fileWatcher.addPath(config_file)
            # Process the newly created config file.
            self._onConfigFileChanged(config_file)
            return

        # Case 2: The images folder changed.
        if path == self.defaultImagesFolder or path == self.lastOpenDir:
            logger.info("Images folder changed: %s", path)
            # Use a small delay to avoid multiple rapid updates
            QtCore.QTimer.singleShot(500, functools.partial(self._refreshFileList, path))
    
    def _refreshFileList(self, folder_path):
        """Refresh the file list for the given folder and select the newest file."""
        if not folder_path or not osp.exists(folder_path) or not osp.isdir(folder_path):
            return

        # Only refresh if this is the current directory
        if folder_path == self.lastOpenDir:
            logger.info("Refreshing file list for: %s", folder_path)

            # Get list of files before refresh to find the new one
            old_files = set(self.imageList)

            # Reload the file list but don't load any image yet
            self.importDirImages(folder_path, load=False)

            # Get the new list of files
            new_files = set(self.imageList)

            # Find the newest file by modification time among all files
            newest_file_path = None
            latest_mtime = 0
            if self.imageList:
                try:
                    # Sort files by modification time to find the latest one
                    sorted_files = sorted(self.imageList, key=osp.getmtime, reverse=True)
                    newest_file_path = sorted_files[0]
                except (OSError, IndexError) as e:
                    logger.error("Could not determine newest file: %s", e)
                    return

            if newest_file_path:
                logger.info("Newest file detected: %s", newest_file_path)
                # 缩略图列表不支持 findItems，直接使用 setCurrentFile
                if newest_file_path in self.fileListWidget.file_paths:
                    self.fileListWidget.setCurrentFile(newest_file_path)
                    self.status(self.tr("New file detected, loading: %s") % osp.basename(newest_file_path))
            else:
                self.status(self.tr("File list updated"))

    def toggleKeepPrevMode(self):
        self._config["keep_prev"] = not self._config["keep_prev"]

    def removeSelectedPoint(self):
        self.canvas.removeSelectedPoint()
        self.canvas.update()
        if not self.canvas.hShape.points:
            self.canvas.deleteShape(self.canvas.hShape)
            self.remLabels([self.canvas.hShape])
            if self.noShapes():
                for action in self.actions.onShapesPresent:
                    action.setEnabled(False)
        self.setDirty()

    def deleteSelectedShape(self):
        yes, no = QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
        msg = self.tr(
            "You are about to permanently delete {} polygons, " "proceed anyway?"
        ).format(len(self.canvas.selectedShapes))
        if yes == QtWidgets.QMessageBox.warning(
            self, self.tr("Attention"), msg, yes | no, yes
        ):
            self.remLabels(self.canvas.deleteSelected())
            self.setDirty()
            if self.noShapes():
                for action in self.actions.onShapesPresent:
                    action.setEnabled(False)

    def copyShape(self):
        self.canvas.endMove(copy=True)
        for shape in self.canvas.selectedShapes:
            self.addLabel(shape)
        self.labelList.clearSelection()
        self.setDirty()

    def moveShape(self):
        self.canvas.endMove(copy=False)
        self.setDirty()

    def openDirDialog(self, _value=False, dirpath=None):
        if not self.mayContinue():
            return

        defaultOpenDirPath = dirpath if dirpath else "."
        if self.lastOpenDir and osp.exists(self.lastOpenDir):
            defaultOpenDirPath = self.lastOpenDir
        elif self.filename:
            defaultOpenDirPath = osp.dirname(self.filename)
        elif self.defaultImagesFolder and osp.exists(self.defaultImagesFolder):
            defaultOpenDirPath = self.defaultImagesFolder
        else:
            defaultOpenDirPath = "."

        targetDirPath = str(
            QtWidgets.QFileDialog.getExistingDirectory(
                self,
                self.tr("%s - Open Directory") % __appname__,
                defaultOpenDirPath,
                QtWidgets.QFileDialog.ShowDirsOnly
                | QtWidgets.QFileDialog.DontResolveSymlinks,
            )
        )
        if targetDirPath:
            self.importDirImages(targetDirPath)
            # Save the selected folder as default
            self._saveDefaultImagesFolder(targetDirPath)

    @property
    def imageList(self):
        """获取文件列表中的图像路径列表"""
        return self.fileListWidget.file_paths[:]  # 返回副本

    def importDroppedImageFiles(self, imageFiles):
        """
        导入拖放的图像文件

        处理用户拖放操作中的图像文件，将它们添加到文件列表中。

        Args:
            imageFiles: 拖放的图像文件路径列表
        """
        extensions = [
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]

        self.filename = None
        for file in imageFiles:
            if file in self.imageList or not file.lower().endswith(tuple(extensions)):
                continue
            self.fileListWidget.addFile(file)

        if len(self.imageList) > 1:
            self.actions.openNextImg.setEnabled(True)
            self.actions.openPrevImg.setEnabled(True)

        self.openNextImg()

    def importDirImages(self, dirpath, pattern=None, load=True):
        """
        导入指定目录中的图像文件
        
        扫描指定目录中的所有图像文件，将它们添加到文件列表中，并可选择性地加载第一个图像。
        支持文件名模式过滤，自动更新文件系统监视器。
        
        Args:
            dirpath: 要导入图像的目录路径
            pattern: 文件名过滤模式（支持正则表达式）
            load: 是否自动加载第一个图像
        """
        self.actions.openNextImg.setEnabled(True)
        self.actions.openPrevImg.setEnabled(True)

        if not self.mayContinue() or not dirpath:
            return

        self.lastOpenDir = dirpath
        self.filename = None
        self.fileListWidget.clear()

        # Update file watcher for the new directory
        if dirpath and osp.exists(dirpath) and osp.isdir(dirpath):
            # Remove old watched folder if different
            watched_dirs = self.fileWatcher.directories()
            for watched_dir in watched_dirs:
                if watched_dir != dirpath:
                    try:
                        self.fileWatcher.removePath(watched_dir)
                    except Exception:
                        pass

            # Add new folder to watcher if not already watching
            if dirpath not in watched_dirs:
                try:
                    self.fileWatcher.addPath(dirpath)
                    logger.info("Now watching folder: %s", dirpath)
                except Exception as e:
                    logger.warning("Failed to watch folder: %s", e)

        filenames = self.scanAllImages(dirpath)
        if pattern:
            try:
                filenames = [f for f in filenames if re.search(pattern, f)]
            except re.error:
                pass
        for filename in filenames:
            self.fileListWidget.addFile(filename)
        # If the monitored directory becomes empty, close the currently displayed image.
        if self.fileListWidget.count() == 0:
            self.closeFile()
            self.actions.openNextImg.setEnabled(False)
            self.actions.openPrevImg.setEnabled(False)
            return

        self.openNextImg(load=load)

    def scanAllImages(self, folderPath):
        """
        扫描目录中的所有图像文件
        
        递归扫描指定目录中的所有图像文件，返回按自然排序的文件路径列表。
        支持所有Qt支持的图像格式。
        
        Args:
            folderPath: 要扫描的目录路径
            
        Returns:
            list: 按自然排序的图像文件路径列表
        """
        extensions = [
            ".%s" % fmt.data().decode().lower()
            for fmt in QtGui.QImageReader.supportedImageFormats()
        ]

        images = []
        for root, dirs, files in os.walk(folderPath):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    relativePath = os.path.normpath(osp.join(root, file))
                    images.append(relativePath)
        images = natsort.os_sorted(images)
        return images
