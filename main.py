#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI图像标注与训练系统主程序
基于Labelme重构的UI界面，符合AI软件UI设计文档要求
"""

# 导入系统相关模块
import sys
import os
# 导入PyQt5库，用于GUI开发
from PyQt5 import QtCore, QtGui, QtWidgets, uic
# 导入PyQt5核心Qt枚举值
from PyQt5.QtCore import Qt

# 添加labelme到Python路径，以便导入labelme模块
# 这样可以从相对路径导入labelme包中的模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'labelme'))

# 导入 labelme 的核心模块
# LabelmeMainWindow: labelme 的主窗口类，我们将嵌入这个窗口到我们的 UI 中
# get_config: 获取 labelme 的配置
from labelme.app import MainWindow as LabelmeMainWindow
from labelme.config import get_config
from labelme.widgets import TrainingCurveDock
# 导入本地模块：模型训练和模型使用管理
from model_training import ModelTrainer
from model_usage import ModelUsageManager


# ============================================
# 单实例检测 - 使用QSharedMemory实现
# ============================================
class SingleApplication(QtWidgets.QApplication):
    """
    单实例应用程序类
    使用QSharedMemory确保只有一个应用程序实例在运行
    通过共享内存机制检测是否已有实例运行
    """

    # 唯一标识符，用于共享内存
    # 这个UUID字符串作为共享内存的键值，必须唯一
    SHARED_MEMORY_KEY = "B2E8F272-34FB-4465-8618-AC5619782F68"

    def __init__(self, *args, **kwargs):
        # 调用父类构造函数
        super().__init__(*args, **kwargs)

        # 创建共享内存对象
        # QSharedMemory是Qt的共享内存类，用于进程间通信
        self.shared_memory = QtCore.QSharedMemory(self.SHARED_MEMORY_KEY)

        # 尝试附加到现有的共享内存
        # 如果成功attach()，说明已经有实例在运行
        if self.shared_memory.attach():
            # 已经有实例在运行
            self._is_running = True
            # 分离共享内存（只是断开连接，不删除）
            self.shared_memory.detach()
        else:
            # 尝试创建共享内存
            # 创建一个1字节的共享内存块
            # 如果create成功，说明我们是第一个实例
            if self.shared_memory.create(1):
                self._is_running = False  # 可以启动新实例
            else:
                # 创建失败，可能已有实例或其他错误
                # 再次尝试附加确认
                if self.shared_memory.attach():
                    self._is_running = True
                    self.shared_memory.detach()
                else:
                    # 其他错误，允许启动
                    self._is_running = False

    def is_running(self):
        """检查是否已有实例在运行"""
        return self._is_running


def check_single_instance():
    """
    检查是否已有实例在运行
    如果已有实例，显示警告并返回False

    Returns:
        bool: True 如果可以启动新实例，False 如果已有实例在运行
    """
    # 创建共享内存对象，使用与SingleApplication相同的键
    shared_memory = QtCore.QSharedMemory(SingleApplication.SHARED_MEMORY_KEY)

    # 尝试附加到现有的共享内存
    if shared_memory.attach():
        # 已有实例在运行，分离共享内存
        shared_memory.detach()
        # 显示警告消息框
        QtWidgets.QMessageBox.critical(
            None,
            "警告",
            "应用程序已经在运行中！\n\n同一时间只能运行一个应用程序实例。",
            QtWidgets.QMessageBox.Ok
        )
        return False

    # 尝试创建共享内存
    if shared_memory.create(1):
        # 成功创建，这是第一个实例
        return True

    # 创建失败，尝试再次附加确认
    if shared_memory.attach():
        shared_memory.detach()
        return False

    # 其他错误，允许启动
    return True


class AIAnnotationMainWindow(QtWidgets.QMainWindow):
    """AI图像标注与训练系统主窗口"""

    def __init__(self, debug_log=None):
        # 如果提供了debug_log回调函数，记录初始化开始
        if debug_log:
            debug_log("  AIAnnotationMainWindow.__init__() 开始")

        # 在创建窗口前设置属性，确保窗口不会自动显示
        # 这可以避免窗口闪烁问题
        super().__init__()

        # 立即设置属性防止闪烁
        # WA_DontShowOnScreen: 创建时不立即显示在屏幕上
        self.setAttribute(Qt.WA_DontShowOnScreen, True)

        if debug_log:
            debug_log("  super().__init__() 完成")

        # 设置窗口标题
        self.setWindowTitle("AI图像标注与训练系统")
        # 设置窗口默认大小
        self.resize(1200, 800)

        # 加载UI文件
        # 从UI文件动态加载界面布局
        if debug_log:
            debug_log("  加载 UI 文件...")
        # 构建UI文件的完整路径（与main.py同目录）
        ui_path = os.path.join(os.path.dirname(__file__), 'mainform.ui')
        # 使用PyQt5的uic模块加载UI定义
        uic.loadUi(ui_path, self)
        if debug_log:
            debug_log("  UI 文件加载完成")

        # 彻底隐藏菜单栏
        # 某些环境下菜单栏可能显示，设置多个属性确保隐藏
        self.menuBar().setNativeMenuBar(False)
        self.menuBar().setVisible(False)
        self.menuBar().setFixedHeight(0)

        # 初始化各个页面
        if debug_log:
            debug_log("  初始化图像标注页面...")
        self.init_image_annotation_page(debug_log)
        if debug_log:
            debug_log("  初始化模型训练页面...")
        self.init_model_training_page()
        if debug_log:
            debug_log("  初始化模型使用页面...")
        self.init_model_usage_page()
        if debug_log:
            debug_log("  初始化系统设置页面...")
        self.init_system_settings_page()

        # 连接信号槽
        # 将按钮点击信号与对应的处理函数连接
        if debug_log:
            debug_log("  连接信号槽...")
        self.connect_signals()

        # 设置窗口标志为普通窗口（无边框窗口控制）
        # 注意：我们使用自定义的窗口控制按钮，但保留系统标题栏
        # 如果需要完全自定义标题栏，可以设置 Qt.FramelessWindowHint
        # self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)

        # 初始化模型训练器
        if debug_log:
            debug_log("  初始化模型训练器...")
        # 创建模型训练器实例
        self.model_trainer = ModelTrainer()
        # 连接训练相关信号到槽函数
        self.model_trainer.training_started.connect(self.on_training_started)
        self.model_trainer.training_stopped.connect(self.on_training_stopped)
        self.model_trainer.training_log_updated.connect(self.on_training_log_updated)
        self.model_trainer.training_finished.connect(self.on_training_finished)
        self.model_trainer.training_error.connect(self.on_training_error)

        # 初始化模型使用管理器
        if debug_log:
            debug_log("  初始化模型使用管理器...")
        self.model_usage = ModelUsageManager()
        # 连接模型下载相关信号
        self.model_usage.model_download_started.connect(self.on_model_download_started)
        self.model_usage.model_download_finished.connect(self.on_model_download_finished)
        self.model_usage.model_download_error.connect(self.on_model_download_error)
        self.model_usage.model_download_progress.connect(self.on_model_download_progress)
        self.model_usage.model_info_updated.connect(self.on_model_info_updated)

        # 初始化模型信息显示
        if debug_log:
            debug_log("  更新模型信息显示...")
        self.update_model_info_display()

        if debug_log:
            debug_log("  AIAnnotationMainWindow.__init__() 完成")

    def show(self):
        """
        重写 show 方法，取消 WA_DontShowOnScreen 属性后显示窗口
        """
        # 取消 WA_DontShowOnScreen 属性
        # 这样窗口才会真正显示出来
        self.setAttribute(Qt.WA_DontShowOnScreen, False)
        # 调用父类的 show 方法
        super().show()
        # 在 super().show() 之后再次隐藏菜单栏，
        # 因为 QMainWindow.show() 可能会重新显示菜单栏
        self.menuBar().setNativeMenuBar(False)
        self.menuBar().setVisible(False)
        self.menuBar().setFixedHeight(0)
        # 同时确保 labelme 窗口的菜单栏也被隐藏
        # BUG修复: 先检查属性是否存在，避免AttributeError
        if hasattr(self, 'labelme_window') and self.labelme_window is not None:
            self.labelme_window.menuBar().setNativeMenuBar(False)
            self.labelme_window.menuBar().setVisible(False)
            self.labelme_window.menuBar().setFixedHeight(0)

    def init_image_annotation_page(self, debug_log=None):
        """初始化图像标注页面"""
        if debug_log:
            debug_log("    init_image_annotation_page() 开始")

        # 创建Labelme主窗口实例
        # Labelme是开源的图像标注工具，我们将它嵌入到我们的应用中
        if debug_log:
            debug_log("    创建 LabelmeMainWindow...")
        # 导入loguru日志库
        from loguru import logger
        logger.info("开始创建 LabelmeMainWindow...")
        # 创建 Labelme 主窗口，传入配置
        self.labelme_window = LabelmeMainWindow(config=get_config())
        logger.info("LabelmeMainWindow 创建完成")
        if debug_log:
            debug_log("    LabelmeMainWindow 创建完成")

        # 将Labelme的中央部件添加到我们的画布容器中
        # 查找画布容器布局
        canvas_layout = self.findChild(QtWidgets.QVBoxLayout, 'layout_canvas')
        if not canvas_layout:
            canvas_layout = self.findChild(QtWidgets.QVBoxLayout, 'verticalLayout_canvas')
        if canvas_layout:
            # 清除占位符（UI设计时添加的临时占位widget）
            placeholder = self.findChild(QtWidgets.QLabel, 'label_canvasPlaceholder')
            if placeholder:
                canvas_layout.removeWidget(placeholder)
                placeholder.deleteLater()

            # 添加Labelme的中央部件到我们的布局中
            canvas_layout.addWidget(self.labelme_window.centralWidget())

            # 隐藏 Labelme 的菜单栏和工具栏，因为我们有自己的 UI
            self.labelme_window.menuBar().hide()
            # 隐藏所有工具栏
            for toolbar in self.labelme_window.findChildren(QtWidgets.QToolBar):
                toolbar.hide()

        # 创建训练曲线 dock 并添加到主窗口
        self.loss_curve_dock = TrainingCurveDock(self.tr("损失曲线"), self, curve_type='loss')
        self.acc_curve_dock = TrainingCurveDock(self.tr("准确率曲线"), self, curve_type='accuracy')
                    
        # 设置最小尺寸
        self.loss_curve_dock.setMinimumSize(300, 200)
        self.acc_curve_dock.setMinimumSize(300, 200)
                    
        # 添加 dock 到底部区域
        self.addDockWidget(Qt.BottomDockWidgetArea, self.loss_curve_dock)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.acc_curve_dock)
                    
        # 水平分割两个 dock
        self.splitDockWidget(self.loss_curve_dock, self.acc_curve_dock, Qt.Horizontal)
                    
        # 确保 dock 显示
        self.loss_curve_dock.show()
        self.acc_curve_dock.show()
        self.loss_curve_dock.raise_()
        self.acc_curve_dock.raise_()
        self._training_curve_history = {}

        training_widget = getattr(self.labelme_window, "training_widget", None)
        if training_widget and hasattr(training_widget, "training_progress_updated"):
            training_widget.training_progress_updated.connect(self._on_training_progress_updated)
            training_widget.start_training_requested.connect(self._on_remote_training_started)

        # 连接图像标注页面的工具按钮到事件处理函数
        self.btn_editMode.clicked.connect(self.on_edit_mode_clicked)
        self.btn_rectangleMode.clicked.connect(self.on_rectangle_mode_clicked)
        self.btn_polygonMode.clicked.connect(self.on_polygon_mode_clicked)
        self.btn_deleteSingle.clicked.connect(self.on_delete_single_clicked)
        self.btn_undo.clicked.connect(self.on_undo_clicked)
        self.btn_redo.clicked.connect(self.on_redo_clicked)

        # 连接文件操作按钮
        self.btn_importImages.clicked.connect(self.on_import_images_clicked)
        self.btn_connectCamera.clicked.connect(self.on_connect_camera_clicked)
        self.btn_addLabel.clicked.connect(self.on_add_label_clicked)

        if debug_log:
            debug_log("    init_image_annotation_page() 完成")

    def init_model_training_page(self):
        """初始化模型训练页面"""
        # 连接训练控制按钮
        self.btn_trainRun.clicked.connect(self.on_train_run_clicked)
        self.btn_trainStop.clicked.connect(self.on_train_stop_clicked)

    def init_model_usage_page(self):
        """初始化模型使用页面"""
        # 连接模型使用按钮
        self.btn_downloadToCamera.clicked.connect(self.on_download_to_camera_clicked)
        self.btn_downloadToLocal.clicked.connect(self.on_download_to_local_clicked)

    def init_system_settings_page(self):
        """初始化系统设置页面"""
        # 连接设置选项的信号
        # 自动保存复选框
        self.checkBox_autoSave.stateChanged.connect(self.on_auto_save_changed)
        # 显示标签弹窗复选框
        self.checkBox_showLabelPopup.stateChanged.connect(self.on_show_label_popup_changed)

    def connect_signals(self):
        """连接信号槽 - 将UI信号与处理函数关联"""
        # 页面切换信号 - 使用toggle按钮实现页面切换
        self.btn_imageAnnotation.toggled.connect(self.on_page_switched)
        self.btn_modelTraining.toggled.connect(self.on_page_switched)
        self.btn_modelUsage.toggled.connect(self.on_page_switched)
        self.btn_systemSettings.toggled.connect(self.on_page_switched)

        # 窗口控制按钮信号 - 最小化、最大化、关闭
        self.btn_minimize.clicked.connect(self.showMinimized)
        self.btn_maximize.clicked.connect(self.toggle_maximize)
        self.btn_close.clicked.connect(self.close)

        # 左侧全局工具栏按钮信号
        self.btn_toolEdit.clicked.connect(self.on_tool_edit_clicked)
        self.btn_toolRectangle.clicked.connect(self.on_tool_rectangle_clicked)
        self.btn_toolPolygon.clicked.connect(self.on_tool_polygon_clicked)
        self.btn_toolDelete.clicked.connect(self.on_tool_delete_clicked)
        self.btn_toolUndo.clicked.connect(self.on_tool_undo_clicked)
        self.btn_toolRedo.clicked.connect(self.on_tool_redo_clicked)

    def on_page_switched(self, checked):
        """
        页面切换处理函数
        当侧边栏的导航按钮被点击时触发
        Args:
            checked: 按钮是否被选中
        """
        # 如果按钮未被选中，不做处理
        if not checked:
            return

        # 获取信号的发送者（哪个按钮点击的）
        sender = self.sender()
        # 根据不同按钮切换到对应的页面
        if sender == self.btn_imageAnnotation:
            self.stackedWidget_content.setCurrentIndex(0)  # 图像标注页面
        elif sender == self.btn_modelTraining:
            self.stackedWidget_content.setCurrentIndex(1)  # 模型训练页面
        elif sender == self.btn_modelUsage:
            self.stackedWidget_content.setCurrentIndex(2)  # 模型使用页面
        elif sender == self.btn_systemSettings:
            self.stackedWidget_content.setCurrentIndex(3)  # 系统设置页面

    def toggle_maximize(self):
        """切换窗口最大化/还原"""
        # 检查当前窗口状态
        if self.isMaximized():
            # 如果已最大化，则恢复正常大小
            self.showNormal()
        else:
            # 如果未最大化，则最大化
            self.showMaximized()

    # 左侧全局工具栏的事件处理
    def on_tool_edit_clicked(self):
        """编辑模式工具按钮点击"""
        # 检查labelme_window是否存在
        if hasattr(self, 'labelme_window'):
            # 触发labelme的编辑模式动作
            self.labelme_window.actions.editMode.trigger()
            # 更新左侧工具栏按钮状态
            self.btn_toolEdit.setChecked(True)
            self.btn_toolRectangle.setChecked(False)
            self.btn_toolPolygon.setChecked(False)
            # 更新页面内工具栏按钮状态
            self.btn_editMode.setChecked(True)
            self.btn_rectangleMode.setChecked(False)
            self.btn_polygonMode.setChecked(False)

    def on_tool_rectangle_clicked(self):
        """矩形标注工具按钮点击"""
        if hasattr(self, 'labelme_window'):
            # 触发labelme的矩形标注模式
            self.labelme_window.actions.createRectangleMode.trigger()
            # 更新按钮状态
            self.btn_toolEdit.setChecked(False)
            self.btn_toolRectangle.setChecked(True)
            self.btn_toolPolygon.setChecked(False)
            self.btn_editMode.setChecked(False)
            self.btn_rectangleMode.setChecked(True)
            self.btn_polygonMode.setChecked(False)

    def on_tool_polygon_clicked(self):
        """多边形标注工具按钮点击"""
        if hasattr(self, 'labelme_window'):
            # 触发labelme的多边形标注模式
            self.labelme_window.actions.createMode.trigger()
            # 更新按钮状态
            self.btn_toolEdit.setChecked(False)
            self.btn_toolRectangle.setChecked(False)
            self.btn_toolPolygon.setChecked(True)
            self.btn_editMode.setChecked(False)
            self.btn_rectangleMode.setChecked(False)
            self.btn_polygonMode.setChecked(True)

    def on_tool_delete_clicked(self):
        """清除单个工具按钮点击"""
        if hasattr(self, 'labelme_window'):
            # 触发labelme的删除动作
            self.labelme_window.actions.delete.trigger()

    def on_tool_undo_clicked(self):
        """撤销工具按钮点击"""
        if hasattr(self, 'labelme_window'):
            # 触发labelme的撤销动作
            self.labelme_window.actions.undo.trigger()

    def on_tool_redo_clicked(self):
        """重做工具按钮点击"""
        if hasattr(self, 'labelme_window'):
            # 检查redo动作是否存在（有些版本可能没有）
            if hasattr(self.labelme_window.actions, 'redo'):
                self.labelme_window.actions.redo.trigger()

    # 图像标注页面的事件处理
    def on_edit_mode_clicked(self):
        """编辑模式按钮点击"""
        if hasattr(self, 'labelme_window'):
            self.labelme_window.actions.editMode.trigger()
            # 更新按钮状态
            self.btn_editMode.setChecked(True)
            self.btn_rectangleMode.setChecked(False)
            self.btn_polygonMode.setChecked(False)

    def on_rectangle_mode_clicked(self):
        """矩形标注模式按钮点击"""
        if hasattr(self, 'labelme_window'):
            self.labelme_window.actions.createRectangleMode.trigger()
            # 更新按钮状态
            self.btn_editMode.setChecked(False)
            self.btn_rectangleMode.setChecked(True)
            self.btn_polygonMode.setChecked(False)

    def on_polygon_mode_clicked(self):
        """多边形标注模式按钮点击"""
        if hasattr(self, 'labelme_window'):
            self.labelme_window.actions.createMode.trigger()
            # 更新按钮状态
            self.btn_editMode.setChecked(False)
            self.btn_rectangleMode.setChecked(False)
            self.btn_polygonMode.setChecked(True)

    def on_delete_single_clicked(self):
        """清除单个按钮点击"""
        if hasattr(self, 'labelme_window'):
            self.labelme_window.actions.delete.trigger()

    def on_undo_clicked(self):
        """撤销按钮点击"""
        if hasattr(self, 'labelme_window'):
            self.labelme_window.actions.undo.trigger()

    def on_redo_clicked(self):
        """重做按钮点击"""
        if hasattr(self, 'labelme_window'):
            if hasattr(self.labelme_window.actions, 'redo'):
                self.labelme_window.actions.redo.trigger()

    def on_import_images_clicked(self):
        """导入图片文件夹按钮点击"""
        # 调用labelme的导入文件夹功能
        if hasattr(self, 'labelme_window'):
            self.labelme_window.importDirImages()

    def on_connect_camera_clicked(self):
        """连接相机实时采图按钮点击"""
        # BUG: 相机连接功能尚未实现
        # 这里需要实现相机连接功能
        QtWidgets.QMessageBox.information(self, "提示", "相机连接功能将在后续版本中实现")

    def on_add_label_clicked(self):
        """添加新标签按钮点击"""
        if hasattr(self, 'labelme_window'):
            self.labelme_window.addLabel()

    # 模型训练页面的事件处理
    def on_train_run_clicked(self):
        """训练运行按钮点击"""
        # 检查是否已经在训练，避免重复启动
        if not self.model_trainer.is_training():
            self.btn_trainRun.setChecked(True)
            self.btn_trainStop.setChecked(False)
            self.model_trainer.start_training()

    def on_train_stop_clicked(self):
        """训练停止按钮点击"""
        if self.model_trainer.is_training():
            self.btn_trainRun.setChecked(False)
            self.btn_trainStop.setChecked(True)
            self.model_trainer.stop_training()

    # 模型训练信号处理 - 当训练状态改变时更新UI
    def on_training_started(self):
        """训练开始信号处理"""
        self.textEdit_trainingLog.append("开始模型训练...")
        self.textEdit_trainingLog.append("=" * 50)

    def on_training_stopped(self):
        """训练停止信号处理"""
        self.textEdit_trainingLog.append("正在停止训练...")

    def on_training_log_updated(self, log_message):
        """训练日志更新信号处理"""
        self.textEdit_trainingLog.append(log_message)

    def on_training_finished(self):
        """训练完成信号处理"""
        self.textEdit_trainingLog.append("=" * 50)
        self.textEdit_trainingLog.append("模型训练完成！")
        self.btn_trainRun.setChecked(False)
        self.btn_trainStop.setChecked(False)

    def on_training_error(self, error_message):
        """训练错误信号处理"""
        self.textEdit_trainingLog.append(f"错误: {error_message}")
        self.btn_trainRun.setChecked(False)
        self.btn_trainStop.setChecked(False)

    # 模型使用页面的事件处理
    def on_download_to_camera_clicked(self):
        """下载模型到智能相机按钮点击"""
        self.model_usage.download_to_camera()

    def on_download_to_local_clicked(self):
        """下载模型到本地电脑按钮点击"""
        self.model_usage.download_to_local()

    # 模型使用信号处理
    def on_model_download_started(self, target):
        """模型下载开始信号处理"""
        self.textEdit_trainingLog.append(f"开始下载模型到{target}...")

    def on_model_download_finished(self, target):
        """模型下载完成信号处理"""
        QtWidgets.QMessageBox.information(self, "下载完成", f"模型已成功下载到{target}！")
        self.textEdit_trainingLog.append(f"模型下载到{target}完成！")

    def on_model_download_error(self, error_message):
        """模型下载错误信号处理"""
        QtWidgets.QMessageBox.critical(self, "下载错误", f"下载过程中发生错误: {error_message}")
        self.textEdit_trainingLog.append(f"下载错误: {error_message}")

    def on_model_download_progress(self, progress):
        """模型下载进度信号处理"""
        # BUG: 检查progressBar_download是否存在，有些版本可能没有这个控件
        if hasattr(self, 'progressBar_download'):
            self.progressBar_download.setValue(progress)

    def on_model_info_updated(self, model_info):
        """模型信息更新信号处理"""
        self.update_model_info_display()

    def update_model_info_display(self):
        """更新模型信息显示"""
        try:
            # 获取当前模型信息
            model_info = self.model_usage.get_current_model_info()
            if not model_info:
                self.textEdit_modelInfo.setPlainText("暂无模型信息")
                return
            # 格式化显示文本，使用 get 方法避免 KeyError
            info_text = f"""模型名称：{model_info.get('model_name', '未知')}
版本：{model_info.get('version', '未知')}
创建日期：{model_info.get('created_date', '未知')}
文件大小：{model_info.get('file_size', '未知')}
准确率：{model_info.get('accuracy', '未知')}
支持设备：{', '.join(model_info.get('supported_devices', []))}
类别：{', '.join(model_info.get('classes', []))}"""
            # 显示到文本框
            self.textEdit_modelInfo.setPlainText(info_text)
        except Exception as e:
            from loguru import logger
            logger.error(f"更新模型信息显示失败：{e}")
            self.textEdit_modelInfo.setPlainText(f"加载模型信息失败：{str(e)}")

    def on_auto_save_changed(self, state):
        """自动保存设置改变"""
        if hasattr(self, 'labelme_window'):
            # 同步到labelme的自动保存设置
            self.labelme_window.actions.saveAuto.setChecked(state == Qt.Checked)

    def on_show_label_popup_changed(self, state):
        """显示标签弹窗设置改变"""
        # BUG: 这个功能尚未实现，应该保存设置到配置文件
        # 这里需要更新配置
        pass
    
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

    def _on_remote_training_started(self):
        """远程训练开始时清空曲线"""
        if hasattr(self, 'loss_curve_dock') and self.loss_curve_dock:
            self.loss_curve_dock.clear_curve()
        if hasattr(self, 'acc_curve_dock') and self.acc_curve_dock:
            self.acc_curve_dock.clear_curve()
        self._training_curve_history = {}

    def _on_training_progress_updated(self, task_id, epoch, total_epochs, loss, accuracy):
        """训练进度更新时同步曲线"""
        if not hasattr(self, '_training_curve_history'):
            self._training_curve_history = {}

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


def _show_already_running_message():
    """显示应用程序已在运行的消息提示"""
    # 注释掉 user32 相关代码，避免可能的闪烁问题
    # 原本使用Windows原生API显示消息框，现已改用Qt消息框

    # 使用 Qt 弹窗替代 Windows 原生弹窗
    # 显示错误级别消息框
    QtWidgets.QMessageBox.critical(
        None,
        "警告",
        "应用程序已经在运行中！\n\n同一时间只能运行一个应用程序实例。",
        QtWidgets.QMessageBox.Ok
    )
    return QtWidgets.QMessageBox.Ok


def main():
    """主函数 - 应用程序入口点"""
    # 记录启动时间用于调试日志
    import time
    start_time = time.time()

    # 调试日志回调函数
    def debug_log(msg):
        # 计算经过的时间
        elapsed = time.time() - start_time
        # 打印带时间戳的日志
        print(f"[{elapsed:.3f}s] {msg}", flush=True)

    debug_log("=== main() 开始 ===")

    # 创建应用程序（必须在QSharedMemory之前创建）
    # QApplication是PyQt5应用程序的基础，每个应用只需要一个
    debug_log("创建 QApplication...")
    app = QtWidgets.QApplication(sys.argv)
    debug_log("QApplication 创建完成")
    
    # 加载翻译器（用于Qt原生控件的中文显示）
    debug_log("加载翻译器...")
    translator = QtCore.QTranslator()
    translator.load(
        QtCore.QLocale.system().name(),
        osp.dirname(osp.abspath(__file__)) + "/labelme/translate",
    )
    app.installTranslator(translator)
    debug_log("翻译器加载完成")

    # 检查是否已有实例在运行（必须在QApplication创建之后）
    # 因为QSharedMemory需要QCoreApplication存在
    # 检查是否已有实例在运行（必须在 QApplication 创建之后）
    debug_log("检查单实例...")
    try:
        shared_memory = QtCore.QSharedMemory(SingleApplication.SHARED_MEMORY_KEY)

        if shared_memory.attach():
            shared_memory.detach()
            _show_already_running_message()
            return 1

        if not shared_memory.create(1):
            if shared_memory.attach():
                shared_memory.detach()
                _show_already_running_message()
                return 1
    except Exception as e:
        print(f"警告：单实例检测失败：{e}")

    # 设置应用程序信息
    app.setApplicationName("AI图像标注与训练系统")
    app.setOrganizationName("WSLabelme")

    # 创建并显示主窗口
    debug_log("创建 AIAnnotationMainWindow...")
    main_window = AIAnnotationMainWindow(debug_log)
    debug_log("AIAnnotationMainWindow 创建完成")

    debug_log("显示主窗口...")
    # 调用show方法显示窗口
    main_window.show()
    debug_log("主窗口已显示")

    debug_log("=== 进入事件循环 ===")
    # 进入Qt事件循环，等待用户操作
    # 返回退出码
    return app.exec_()


if __name__ == "__main__":
    # 这是Python程序的入口点
    try:
        # 调用主函数
        exit_code = main()
        # 使用 os._exit 避免触发 SystemExit 异常
        # os._exit()会立即终止进程，不执行清理
        # 但只在显式返回错误码时使用
        if exit_code != 0:
            import os
            os._exit(exit_code)
    except SystemExit:
        # 重新抛出SystemExit，让Python正常处理
        raise
    except:
        # 捕获所有其他异常，打印堆栈跟踪
        import traceback
        traceback.print_exc()
        import os
        os._exit(1)
