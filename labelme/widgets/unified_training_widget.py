# -*- coding: utf-8 -*-
"""
综合训练面板组件

将训练配置和训练任务监控合并到一个面板中
包含：
- 服务器连接
- 训练参数配置
- 任务列表
- 训练进度
- 日志输出
"""

import os
import json
import weakref
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List
from loguru import logger

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt


class CollapsibleGroupBox(QtWidgets.QWidget):
    """可折叠的分组框"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self._is_collapsed = False

        # 标题按钮
        self.toggle_button = QtWidgets.QPushButton(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #D4605A;
                color: white;
                border: none;
                text-align: left;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:checked {
                background-color: #D4605A;
            }
        """)
        self.toggle_button.clicked.connect(self._toggle)

        # 折叠指示器
        self.indicator = QtWidgets.QLabel("\u25BC")
        self.indicator.setStyleSheet("color: white; font-size: 10px;")
        self.indicator.setFixedWidth(16)

        # 标题栏布局
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        header_layout.addWidget(self.toggle_button, 1)
        header_layout.addWidget(self.indicator)
        self.indicator.setStyleSheet("""
            QLabel {
                background-color: #D4605A;
                color: white;
                padding: 4px 6px;
                font-size: 10px;
            }
        """)

        self.header_widget = QtWidgets.QWidget()
        self.header_widget.setLayout(header_layout)

        # 内容区域
        self.content_widget = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QFormLayout()
        self.content_layout.setContentsMargins(8, 6, 8, 6)
        self.content_layout.setSpacing(6)
        self.content_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.content_widget.setLayout(self.content_layout)

        # 主布局
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.header_widget)
        main_layout.addWidget(self.content_widget)
        self.setLayout(main_layout)

    def _toggle(self):
        self._is_collapsed = not self.toggle_button.isChecked()
        self.content_widget.setVisible(self.toggle_button.isChecked())
        self.indicator.setText("\u25B6" if self._is_collapsed else "\u25BC")

    def addRow(self, label_text, widget):
        label = QtWidgets.QLabel(label_text)
        label.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.content_layout.addRow(label, widget)

    def getContentLayout(self):
        return self.content_layout


class UnifiedTrainingWidget(QtWidgets.QWidget):
    """综合训练面板主组件"""

    # 信号定义
    create_remote_task_requested = QtCore.pyqtSignal(dict)
    start_training_requested = QtCore.pyqtSignal()
    stop_training_requested = QtCore.pyqtSignal()
    server_connect_requested = QtCore.pyqtSignal(str, int)
    server_disconnect_requested = QtCore.pyqtSignal()
    training_progress_updated = QtCore.pyqtSignal(str, int, int, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = None
        self._current_task_id = None
        self._tasks = {}
        self._refresh_timer = None  # 用于防抖的定时器
        self._auto_refresh_timer = None  # 自动刷新定时器
        self._is_monitoring = False
        self._monitor_target_task_id = None
        
        # 训练历史数据
        self._training_history = {
            'epochs': [],
            'losses': [],
            'accuracies': []
        }
        
        self._setup_ui()

    def _get_default_dataset_path(self):
        """获取默认数据集路径"""
        try:
            if getattr(sys, "frozen", False):
                app_dir = os.path.dirname(sys.executable)
            else:
                package_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                app_dir = os.path.dirname(package_dir)
            config_path = os.path.join(app_dir, 'labelme_config.json')

            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        default_path = config.get('default_images_folder', '')
                        if default_path and os.path.exists(default_path):
                            return default_path
                except (json.JSONDecodeError, IOError):
                    pass
        except Exception as e:
            print(f"读取默认数据集路径失败：{e}")
        return None

    def _on_browse_dataset(self):
        """浏览数据集文件夹"""
        try:
            current_path = self.dataset_edit.text()
            if not current_path or not os.path.exists(current_path):
                current_path = self._get_default_dataset_path() or ""

            folder = QtWidgets.QFileDialog.getExistingDirectory(
                self,
                "选择数据集文件夹",
                current_path,
                QtWidgets.QFileDialog.ShowDirsOnly | QtWidgets.QFileDialog.DontResolveSymlinks
            )
            if folder:
                self.dataset_edit.setText(folder)
        except Exception as e:
            self._log(f"浏览数据集异常：{str(e)}", "error")

    def _setup_ui(self):
        # 创建主布局
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建滚动区域
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        # 创建内容容器
        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)

        # ==================== 服务器连接配置 ====================
        self.server_group = CollapsibleGroupBox("服务器连接")

        # 服务器地址
        self.server_host_edit = QtWidgets.QLineEdit("127.0.0.1")
        self.server_host_edit.setPlaceholderText("例如：127.0.0.1")
        self.server_group.addRow("服务器 IP：", self.server_host_edit)

        # 服务器端口
        self.server_port_spin = QtWidgets.QSpinBox()
        self.server_port_spin.setRange(1, 65535)
        self.server_port_spin.setValue(8888)
        self.server_group.addRow("端口号：", self.server_port_spin)

        # 连接状态
        self.server_status_layout = QtWidgets.QHBoxLayout()
        self.server_status_label = QtWidgets.QLabel("未连接")
        self.server_status_label.setStyleSheet("color: #f44336; font-weight: bold;")
        self.server_connect_btn = QtWidgets.QPushButton("连接")
        self.server_connect_btn.setFixedWidth(60)
        self.server_connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.server_status_layout.addWidget(self.server_status_label)
        self.server_status_layout.addWidget(self.server_connect_btn)
        self.server_status_layout.addStretch()
        status_widget = QtWidgets.QWidget()
        status_widget.setLayout(self.server_status_layout)
        self.server_group.addRow("状态：", status_widget)

        content_layout.addWidget(self.server_group)

        # ==================== 基本信息 ====================
        self.basic_group = CollapsibleGroupBox("基本信息")

        self.task_type_combo = QtWidgets.QComboBox()
        self.task_type_combo.addItems(["目标检测 (detect)", "图像分类 (classify)", "语义分割 (segment)"])
        self.basic_group.addRow("任务类型：", self.task_type_combo)

        # 数据集路径选择
        dataset_layout = QtWidgets.QHBoxLayout()
        dataset_layout.setSpacing(4)

        self.dataset_edit = QtWidgets.QLineEdit()
        self.dataset_edit.setPlaceholderText("请选择数据集文件夹路径")

        default_dataset = self._get_default_dataset_path()
        if default_dataset:
            self.dataset_edit.setText(default_dataset)

        self.dataset_browse_btn = QtWidgets.QPushButton("浏览...")
        self.dataset_browse_btn.setFixedWidth(50)
        self.dataset_browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                padding: 2px 6px;
                border-radius: 2px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.dataset_browse_btn.clicked.connect(self._on_browse_dataset)

        dataset_layout.addWidget(self.dataset_edit, 1)
        dataset_layout.addWidget(self.dataset_browse_btn)

        dataset_widget = QtWidgets.QWidget()
        dataset_widget.setLayout(dataset_layout)
        self.basic_group.addRow("数据集：", dataset_widget)

        content_layout.addWidget(self.basic_group)

        # ==================== 训练参数 ====================
        self.param_group = CollapsibleGroupBox("训练参数")

        # 图像尺寸
        self.image_size_combo = QtWidgets.QComboBox()
        self.image_size_combo.addItems(["320", "416", "512", "640", "768", "1024"])
        self.image_size_combo.setCurrentText("320")
        self.param_group.addRow("图像尺寸：", self.image_size_combo)

        # 训练轮次
        self.epochs_spin = QtWidgets.QSpinBox()
        self.epochs_spin.setRange(10, 500)
        self.epochs_spin.setValue(50)
        self.epochs_spin.setSingleStep(10)
        self.param_group.addRow("训练轮次：", self.epochs_spin)

        # 批次大小
        self.batch_combo = QtWidgets.QComboBox()
        self.batch_combo.addItems(["8", "16", "32", "64", "128"])
        self.batch_combo.setCurrentText("32")
        self.param_group.addRow("批次大小：", self.batch_combo)

        # 学习率
        self.lr_combo = QtWidgets.QComboBox()
        self.lr_combo.addItems(["0.0001", "0.0005", "0.001", "0.005", "0.01"])
        self.lr_combo.setCurrentText("0.001")
        self.param_group.addRow("学习率：", self.lr_combo)

        # 训练集比例
        self.train_ratio_combo = QtWidgets.QComboBox()
        self.train_ratio_combo.addItems(["0.7", "0.8", "0.9", "0.95"])
        self.train_ratio_combo.setCurrentText("0.9")
        self.param_group.addRow("训练集比例：", self.train_ratio_combo)

        content_layout.addWidget(self.param_group)

        # ==================== 训练操作区域 ====================
        self.action_group = CollapsibleGroupBox("训练操作")

        # 创建任务按钮
        btn_layout = QtWidgets.QHBoxLayout()

        self.create_task_btn = QtWidgets.QPushButton("创建任务")
        self.create_task_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.create_task_btn.setEnabled(False)

        self.start_btn = QtWidgets.QPushButton("启动训练")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.start_btn.setEnabled(False)

        self.stop_btn = QtWidgets.QPushButton("停止训练")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_btn.setEnabled(False)

        btn_layout.addWidget(self.create_task_btn)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)

        self.action_group.getContentLayout().addRow(btn_layout)

        # 状态标签
        self.training_status_label = QtWidgets.QLabel("就绪")
        self.training_status_label.setStyleSheet("color: #666; font-size: 11px;")
        self.training_status_label.setAlignment(Qt.AlignCenter)
        self.action_group.getContentLayout().addRow(self.training_status_label)

        content_layout.addWidget(self.action_group)

        # ==================== 任务列表区域 ====================
        self.task_list_group = CollapsibleGroupBox("训练任务列表")

        # 任务表格
        self.task_table = QtWidgets.QTableWidget()
        self.task_table.setColumnCount(5)
        self.task_table.setHorizontalHeaderLabels(["任务 ID", "状态", "进度", "模型类型", "创建时间"])
        self.task_table.horizontalHeader().setStretchLastSection(True)
        self.task_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.task_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.task_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setMinimumHeight(100)
        self.task_table.setMaximumHeight(150)
        self.task_table.itemSelectionChanged.connect(self._on_task_selected)

        # 设置表头样式
        self.task_table.setStyleSheet("""
            QHeaderView::section {
                background-color: #2196F3;
                color: white;
                padding: 4px;
                border: none;
                font-weight: bold;
                font-size: 11px;
            }
            QTableWidget {
                border: 1px solid #ccc;
                gridline-color: #ddd;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
        """)

        self.task_list_group.getContentLayout().addRow(self.task_table)

        # 任务操作按钮
        task_btn_layout = QtWidgets.QHBoxLayout()

        self.refresh_btn = QtWidgets.QPushButton("刷新列表")
        self.refresh_btn.setEnabled(False)

        self.get_status_btn = QtWidgets.QPushButton("获取状态")
        self.get_status_btn.setEnabled(False)
        self.get_status_btn.setToolTip("获取当前选中任务的详细状态")

        self.monitor_btn = QtWidgets.QPushButton("监控训练")
        self.monitor_btn.setEnabled(False)
        self.monitor_btn.setToolTip("持续监控训练进度（阻塞式）")
        self.monitor_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        self.delete_task_btn = QtWidgets.QPushButton("删除任务")
        self.delete_task_btn.setEnabled(False)
        self.delete_task_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        # 刷新间隔控制
        refresh_interval_layout = QtWidgets.QHBoxLayout()
        refresh_interval_layout.setSpacing(4)
        refresh_interval_layout.addWidget(QtWidgets.QLabel("刷新间隔:"))
        self.refresh_interval_spin = QtWidgets.QSpinBox()
        self.refresh_interval_spin.setRange(1, 10)
        self.refresh_interval_spin.setValue(2)
        self.refresh_interval_spin.setSuffix(" 秒")
        self.refresh_interval_spin.setFixedWidth(70)
        self.refresh_interval_spin.setToolTip("设置自动刷新任务列表的间隔时间(1-10秒)")
        refresh_interval_layout.addWidget(self.refresh_interval_spin)

        task_btn_layout.addLayout(refresh_interval_layout)
        task_btn_layout.addWidget(self.refresh_btn)
        task_btn_layout.addWidget(self.get_status_btn)
        task_btn_layout.addWidget(self.monitor_btn)
        task_btn_layout.addWidget(self.delete_task_btn)
        task_btn_layout.addStretch()

        self.task_list_group.getContentLayout().addRow(task_btn_layout)

        content_layout.addWidget(self.task_list_group)

        # ==================== 当前任务进度区域 ====================
        self.progress_group = CollapsibleGroupBox("当前任务进度")

        # 任务信息
        info_layout = QtWidgets.QFormLayout()
        self.current_task_label = QtWidgets.QLabel("无")
        self.current_status_label = QtWidgets.QLabel("-")
        self.current_epoch_label = QtWidgets.QLabel("-")
        self.current_loss_label = QtWidgets.QLabel("-")
        self.current_accuracy_label = QtWidgets.QLabel("-")

        info_layout.addRow("任务 ID:", self.current_task_label)
        info_layout.addRow("状态:", self.current_status_label)
        info_layout.addRow("轮次:", self.current_epoch_label)
        info_layout.addRow("损失:", self.current_loss_label)
        info_layout.addRow("准确率:", self.current_accuracy_label)

        self.progress_group.getContentLayout().addRow(info_layout)

        # 进度条
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        self.progress_group.getContentLayout().addRow(self.progress_bar)

        content_layout.addWidget(self.progress_group)

        # ==================== 日志输出区域 ====================
        self.log_group = CollapsibleGroupBox("日志输出")

        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumBlockCount(100)
        self.log_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, Monaco, monospace;
                font-size: 11px;
                border: 1px solid #ccc;
            }
        """)

        self.log_group.getContentLayout().addRow(self.log_text)

        # 清空日志按钮
        clear_btn_layout = QtWidgets.QHBoxLayout()
        self.clear_log_btn = QtWidgets.QPushButton("清空日志")
        self.clear_log_btn.setFixedWidth(80)
        clear_btn_layout.addStretch()
        clear_btn_layout.addWidget(self.clear_log_btn)
        self.log_group.getContentLayout().addRow(clear_btn_layout)

        content_layout.addWidget(self.log_group)

        # 底部弹性空间
        content_layout.addStretch()

        content_widget.setLayout(content_layout)
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

        # 连接信号
        self.create_task_btn.clicked.connect(self._on_create_task_clicked)
        self.start_btn.clicked.connect(self._on_start_clicked)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.server_connect_btn.clicked.connect(self._on_server_connect_clicked)
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        self.get_status_btn.clicked.connect(self._on_get_status_clicked)
        self.monitor_btn.clicked.connect(self._on_monitor_clicked)
        self.delete_task_btn.clicked.connect(self._on_delete_clicked)
        self.clear_log_btn.clicked.connect(self._on_clear_log_clicked)
        self.refresh_interval_spin.valueChanged.connect(self._on_refresh_interval_changed)

    # ==================== 训练配置相关方法 ====================

    def get_training_params(self):
        """获取训练参数"""
        try:
            task_type_text = self.task_type_combo.currentText()
            if "detect" in task_type_text:
                model_type = "detect"
            elif "classify" in task_type_text:
                model_type = "classify"
            elif "segment" in task_type_text:
                model_type = "segment"
            else:
                model_type = "detect"

            image_size = int(self.image_size_combo.currentText())
            epochs = self.epochs_spin.value()
            batch_size = int(self.batch_combo.currentText())
            learning_rate = float(self.lr_combo.currentText())
            trainset_ratio = float(self.train_ratio_combo.currentText())

            params = {
                "model_type": model_type,
                "image_size": image_size,
                "dataset": self.dataset_edit.text() or "data",
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "trainset_ratio": trainset_ratio
            }
            return params
        except Exception as e:
            self._log(f"获取训练参数异常：{str(e)}", "error")
            return {
                "model_type": "detect",
                "image_size": 640,
                "dataset": "data",
                "epochs": 50,
                "batch_size": 32,
                "learning_rate": 0.001,
                "trainset_ratio": 0.9
            }

    def get_server_config(self):
        """获取服务器配置"""
        host = self.server_host_edit.text().strip() or "127.0.0.1"
        port = self.server_port_spin.value()
        return host, port

    def set_connection_status(self, connected, message=None):
        """设置连接状态显示"""
        try:
            if connected:
                self.server_status_label.setText(message or "已连接")
                self.server_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                self.server_connect_btn.setText("断开")
            else:
                self.server_status_label.setText(message or "未连接")
                self.server_status_label.setStyleSheet("color: #f44336; font-weight: bold;")
                self.server_connect_btn.setText("连接")
        except Exception:
            pass

    def enable_server_edit(self, enabled):
        """启用/禁用服务器配置编辑"""
        try:
            self.server_host_edit.setEnabled(enabled)
            self.server_port_spin.setEnabled(enabled)
        except Exception:
            pass

    # ==================== 事件处理 ====================

    def _on_server_connect_clicked(self):
        """服务器连接按钮点击"""
        try:
            if self._manager and self._manager.is_connected():
                self.server_disconnect_requested.emit()
            else:
                host, port = self.get_server_config()
                self.server_connect_requested.emit(host, port)
                self.set_connection_status(False, "连接中...")
        except Exception as e:
            self._log(f"服务器连接异常：{str(e)}", "error")

    def _on_create_task_clicked(self):
        """创建远程任务按钮点击"""
        try:
            params = self.get_training_params()
            self.create_remote_task_requested.emit(params)
            self.training_status_label.setText("正在创建任务...")
        except Exception as e:
            self._log(f"创建任务异常：{str(e)}", "error")
            self.training_status_label.setText("创建任务失败")

    def _on_start_clicked(self):
        """启动训练按钮点击"""
        if self._current_task_id and self._manager:
            if not self._manager.is_connected():
                self._log("未连接到服务器", "error")
                return
            try:
                self._manager.start_training(self._current_task_id)
            except Exception as e:
                self._log(f"启动训练异常：{str(e)}", "error")
        else:
            self.start_training_requested.emit()

    def _on_stop_clicked(self):
        """停止训练按钮点击"""
        if self._current_task_id and self._manager:
            if not self._manager.is_connected():
                self._log("未连接到服务器", "error")
                return
            try:
                self._manager.stop_training(self._current_task_id)
            except Exception as e:
                self._log(f"停止训练异常：{str(e)}", "error")
        else:
            self.stop_training_requested.emit()

    def _on_refresh_clicked(self):
        """刷新列表按钮点击（带防抖）"""
        if not self._manager:
            return
        
        try:
            # 取消之前的定时器（如果存在）
            if self._refresh_timer and self._refresh_timer.isActive():
                self._refresh_timer.stop()
            
            # 立即刷新
            self._manager.list_tasks()
            self._log("正在刷新任务列表...")
        except Exception as e:
            self._log(f"刷新列表异常：{str(e)}", "error")

    def refresh_task_list(self):
        """公共方法：刷新任务列表（用于外部调用）"""
        self._on_refresh_clicked()

    def _delayed_refresh(self, delay_ms=500):
        """延迟刷新（用于防抖）- 复用定时器对象"""
        if not self._manager:
            return

        # 复用定时器对象，避免内存泄漏
        if not hasattr(self, '_refresh_timer') or self._refresh_timer is None:
            self._refresh_timer = QtCore.QTimer(self)
            self._refresh_timer.setSingleShot(True)
            self._refresh_timer.timeout.connect(self._on_refresh_clicked)

        # 取消之前的定时器
        if self._refresh_timer.isActive():
            self._refresh_timer.stop()

        # 重新启动定时器
        self._refresh_timer.start(delay_ms)

    def _start_auto_refresh(self):
        """启动自动刷新 - 复用定时器对象"""
        # 复用定时器对象，避免内存泄漏
        if not hasattr(self, '_auto_refresh_timer') or self._auto_refresh_timer is None:
            self._auto_refresh_timer = QtCore.QTimer(self)
            self._auto_refresh_timer.timeout.connect(self._on_refresh_clicked)

        # 停止之前的定时器
        if self._auto_refresh_timer.isActive():
            self._auto_refresh_timer.stop()

        # 获取当前设置的刷新间隔（秒转毫秒）
        interval_ms = self.refresh_interval_spin.value() * 1000
        self._auto_refresh_timer.start(interval_ms)
        self._log(f"自动刷新已启动，间隔 {self.refresh_interval_spin.value()} 秒")

    def _stop_auto_refresh(self):
        """停止自动刷新"""
        if hasattr(self, '_auto_refresh_timer') and self._auto_refresh_timer and self._auto_refresh_timer.isActive():
            self._auto_refresh_timer.stop()
            self._log("自动刷新已停止")

    def _restart_auto_refresh(self):
        """重新启动自动刷新（间隔改变时调用）"""
        if hasattr(self, '_auto_refresh_timer') and self._auto_refresh_timer and self._auto_refresh_timer.isActive():
            self._start_auto_refresh()

    def _on_get_status_clicked(self):
        """获取状态按钮点击"""
        if not self._current_task_id or not self._manager:
            self._log("请先选择一个任务", "warning")
            return

        # 检查管理器是否已连接
        if not self._manager.is_connected():
            self._log("未连接到服务器", "error")
            return

        try:
            self._log(f"正在获取任务 {self._current_task_id[:16]}... 的状态")
            self._manager.get_task_status(self._current_task_id)
        except Exception as e:
            self._log(f"获取状态异常：{str(e)}", "error")

    def _on_monitor_clicked(self):
        """监控训练按钮点击 - 在独立线程中调用 monitor_training"""
        if not self._current_task_id or not self._manager:
            self._log("请先选择一个任务", "warning")
            return

        # 检查管理器是否已连接
        if not self._manager.is_connected():
            self._log("未连接到服务器", "error")
            return

        try:
            self._start_monitoring_task(self._current_task_id, auto_started=False)
        except Exception as e:
            self._log(f"启动监控线程异常：{str(e)}", "error")
            self._on_monitor_finished()

    def _start_monitoring_task(self, task_id, auto_started=False):
        """启动后台监控线程。"""
        if not task_id or not self._manager:
            return

        if self._is_monitoring and self._monitor_target_task_id == task_id:
            self._log(f"任务 {task_id[:16]}... 已在监控中")
            return

        self._is_monitoring = True
        self._monitor_target_task_id = task_id
        self.monitor_btn.setVisible(True)
        self.monitor_btn.setEnabled(False)
        self.monitor_btn.setText("监控中...")

        log_prefix = "自动开始监控" if auto_started else "开始监控"
        self._log(f"{log_prefix}任务 {task_id[:16]}... 的训练进度")

        import threading

        def _on_progress_callback(epoch, total_epochs, loss, accuracy, progress_data):
            """进度回调 - 在主线程中更新 UI"""
            try:
                if self._training_history['epochs'] and self._training_history['epochs'][-1] == epoch:
                    self._training_history['losses'][-1] = loss
                    self._training_history['accuracies'][-1] = accuracy
                else:
                    self._training_history['epochs'].append(epoch)
                    self._training_history['losses'].append(loss)
                    self._training_history['accuracies'].append(accuracy)
                self.training_progress_updated.emit(
                    task_id,
                    int(epoch),
                    int(total_epochs),
                    float(loss),
                    float(accuracy),
                )

                QtCore.QMetaObject.invokeMethod(
                    self, "_update_monitor_progress",
                    QtCore.Qt.QueuedConnection,
                    QtCore.Q_ARG(int, int(epoch)),
                    QtCore.Q_ARG(int, int(total_epochs)),
                    QtCore.Q_ARG(float, float(loss)),
                    QtCore.Q_ARG(float, float(accuracy))
                )
            except Exception as e:
                logger.error(f"回调函数执行异常：{e}")

        def _monitor_thread():
            try:
                client = self._manager._client
                if client:
                    self._log(f"监控线程开始执行 monitor_training: {task_id[:8]}...")
                    client.monitor_training(task_id, poll_interval=2.0, callback=_on_progress_callback)
                    self._log(f"monitor_training 已返回：{task_id[:8]}...")
                else:
                    self._log("训练客户端未初始化", "error")
            except Exception as e:
                self._log(f"监控训练异常：{str(e)}", "error")
            finally:
                try:
                    QtCore.QMetaObject.invokeMethod(
                        self, "_on_monitor_finished",
                        QtCore.Qt.QueuedConnection
                    )
                except Exception as e:
                    logger.error(f"恢复按钮失败：{e}")
                    self._on_monitor_finished()

        thread = threading.Thread(target=_monitor_thread, daemon=True)
        thread.start()

    @QtCore.pyqtSlot(int, int, float, float)
    def _update_monitor_progress(self, epoch, total_epochs, loss, accuracy):
        """更新监控进度到 UI（在主线程执行）"""
        try:
            # 计算进度百分比
            if total_epochs and total_epochs > 0:
                progress_percent = int((epoch / total_epochs) * 100)
            else:
                progress_percent = 0

            # 更新进度条
            self.progress_bar.setValue(progress_percent)

            # 更新标签
            self.current_epoch_label.setText(f"{epoch}/{total_epochs}")
            self.current_loss_label.setText(f"{loss:.4f}")
            self.current_accuracy_label.setText(f"{accuracy:.2f}%")

            # 更新当前任务 ID 显示
            if self._current_task_id:
                self.current_task_label.setText(self._current_task_id[:16] + "...")

            # 同步更新任务列表中的进度
            if self._current_task_id:
                # 更新内存中的任务数据
                if self._current_task_id in self._tasks:
                    self._tasks[self._current_task_id]["progress"] = progress_percent / 100.0
                    self._tasks[self._current_task_id]["epoch"] = epoch
                    self._tasks[self._current_task_id]["total_epochs"] = total_epochs

                # 更新表格中的进度列
                for row in range(self.task_table.rowCount()):
                    item = self.task_table.item(row, 0)
                    if item and item.data(Qt.UserRole) == self._current_task_id:
                        self.task_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{progress_percent}%"))
                        break

            if total_epochs and total_epochs > 0 and epoch == total_epochs:
                self.training_status_label.setText("训练已完成")
                self.monitor_btn.setVisible(False)
        except Exception as e:
            logger.warning(f"更新监控进度失败: {e}")

    @QtCore.pyqtSlot()
    def _on_monitor_finished(self):
        """监控结束回调"""
        self._is_monitoring = False
        self._monitor_target_task_id = None

        should_hide_button = False
        if self._current_task_id in self._tasks:
            task_info = self._tasks.get(self._current_task_id, {})
            epoch = task_info.get("epoch", 0)
            total_epochs = task_info.get("total_epochs", 0)
            should_hide_button = total_epochs and epoch == total_epochs

        self.monitor_btn.setVisible(not should_hide_button)
        self.monitor_btn.setEnabled(not should_hide_button)
        self.monitor_btn.setText("监控训练")
        self._log("监控训练结束")
        
        # 清除训练历史
        self._training_history = {
            'epochs': [],
            'losses': [],
            'accuracies': []
        }

    def _on_delete_clicked(self):
        """删除任务按钮点击"""
        if not self._current_task_id or not self._manager:
            return

        # 检查管理器是否已连接
        if not self._manager.is_connected():
            self._log("未连接到服务器", "error")
            return

        try:
            # 检查父窗口是否有效
            if not self.window() or not self.window().isVisible():
                return

            reply = QtWidgets.QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除任务 {self._current_task_id[:16]}... 吗？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                self._manager.delete_task(self._current_task_id)
        except Exception as e:
            self._log(f"删除任务异常：{str(e)}", "error")

    def _on_clear_log_clicked(self):
        """清空日志"""
        try:
            self.log_text.clear()
        except Exception:
            pass

    def _on_refresh_interval_changed(self, value):
        """刷新间隔改变"""
        try:
            self._log(f"刷新间隔已设置为 {value} 秒")
            # 如果正在自动刷新，重新启动以应用新间隔
            if self._auto_refresh_timer and self._auto_refresh_timer.isActive():
                self._start_auto_refresh()
        except Exception:
            pass

    def _on_task_selected(self):
        """任务选择变化"""
        try:
            selected = self.task_table.selectedItems()
            if not selected:
                self._current_task_id = None
                self.delete_task_btn.setEnabled(False)
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                return

            row = selected[0].row()
            item = self.task_table.item(row, 0)
            if not item:
                self._current_task_id = None
                self.delete_task_btn.setEnabled(False)
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                return

            task_id = item.data(Qt.UserRole)
            if not task_id:
                self._current_task_id = None
                self.delete_task_btn.setEnabled(False)
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                return

            self._current_task_id = task_id
            self.delete_task_btn.setEnabled(True)

            task = self._tasks.get(task_id, {})
            status = task.get("status", "unknown")
            epoch = task.get("epoch", 0)
            total_epochs = task.get("total_epochs", 0)

            if status == "running":
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
            elif status in ["pending", "stopped", "failed"]:
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
            else:
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)

            # 安全截取任务 ID 字符串
            display_id = task_id[:16] + "..." if len(task_id) > 16 else task_id
            self.current_task_label.setText(display_id)
            self.current_status_label.setText(status)
            self.monitor_btn.setVisible(not (total_epochs and epoch == total_epochs))
        except Exception as e:
            self._log(f"任务选择异常：{str(e)}", "error")
            self._current_task_id = None
            self.delete_task_btn.setEnabled(False)
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

    # ==================== Manager 相关 ====================

    def set_manager(self, manager):
        """设置训练客户端管理器"""
        self._manager = manager

        # 连接管理器信号
        manager.connected.connect(self._on_manager_connected)
        manager.connection_error.connect(self._on_connection_error)

        manager.task_created.connect(self._on_task_created)
        manager.task_creation_failed.connect(self._on_task_creation_failed)

        manager.training_started.connect(self._on_training_started)
        manager.training_start_failed.connect(self._on_training_start_failed)

        manager.training_stopped.connect(self._on_training_stopped)
        manager.training_stop_failed.connect(self._on_training_stop_failed)

        manager.task_deleted.connect(self._on_task_deleted)
        manager.task_deletion_failed.connect(self._on_task_deletion_failed)

        manager.progress_updated.connect(self._on_progress_updated)
        manager.status_changed.connect(self._on_status_changed)

        manager.task_list_updated.connect(self._on_task_list_updated)
        manager.task_list_failed.connect(self._on_task_list_failed)

        manager.error_occurred.connect(self._on_error)
        manager.log_message.connect(self._on_log_message)

    # ==================== Manager 信号回调 ====================

    def _on_manager_connected(self, success):
        """管理器连接状态变化"""
        try:
            self.set_connection_status(success)
            self.enable_server_edit(not success)
            if success:
                self.create_task_btn.setEnabled(True)
                self.refresh_btn.setEnabled(True)
                self.get_status_btn.setEnabled(True)
                self.monitor_btn.setEnabled(True)
                self.monitor_btn.setVisible(True)
                self._log("已连接到服务器")
                self._on_refresh_clicked()
                # 连接成功时不启动自动刷新，等训练启动后再启动
            else:
                self.create_task_btn.setEnabled(False)
                self.refresh_btn.setEnabled(False)
                self.get_status_btn.setEnabled(False)
                self.monitor_btn.setEnabled(False)
                self.delete_task_btn.setEnabled(False)
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                self.task_table.setRowCount(0)
                self._tasks.clear()
                # 停止自动刷新
                self._stop_auto_refresh()
        except Exception as e:
            self._log(f"连接状态更新异常：{str(e)}", "error")

    def _on_connection_error(self, error_msg):
        """连接错误"""
        try:
            self.set_connection_status(False, "连接失败")
            self._log(f"连接错误：{error_msg}", "error")
        except Exception:
            pass

    def _on_task_created(self, task_id):
        """任务创建成功"""
        try:
            if task_id:
                self.training_status_label.setText(f"任务已创建：{task_id[:8]}...")
                self._log(f"任务创建成功：{task_id[:16]}...")
                self._on_refresh_clicked()
        except Exception:
            pass

    def _on_task_creation_failed(self, error_msg):
        """任务创建失败"""
        try:
            self.training_status_label.setText("创建任务失败")
            self._log(f"创建任务失败：{error_msg}", "error")
        except Exception:
            pass

    def _on_training_started(self, task_id):
        """训练启动成功"""
        try:
            if task_id:
                self._current_task_id = task_id
                self.training_status_label.setText("训练中...")
                self.training_status_label.setVisible(True)
                self._log(f"训练已启动：{task_id[:16]}...")
                self.monitor_btn.setVisible(True)
                self.monitor_btn.setText("监控训练")
                # 延迟刷新任务列表（训练刚启动时服务器可能还未更新状态）
                QtCore.QTimer.singleShot(500, self._on_refresh_clicked)
                # 立即获取当前任务状态
                if self._manager:
                    self._manager.get_task_status(task_id)
                self._start_monitoring_task(task_id, auto_started=True)
        except Exception:
            pass

    def _on_training_start_failed(self, task_id, error_msg):
        """训练启动失败"""
        try:
            self._log(f"启动训练失败：{error_msg}", "error")
        except Exception:
            pass

    def _on_training_stopped(self, task_id):
        """训练停止成功"""
        try:
            if task_id:
                self.training_status_label.setText("训练已停止")
                self._log(f"训练已停止：{task_id[:16]}...")
                self.monitor_btn.setVisible(True)
                self.monitor_btn.setEnabled(True)
                self.monitor_btn.setText("监控训练")
                self._on_refresh_clicked()
                # 3秒后隐藏状态标签
                QtCore.QTimer.singleShot(3000, lambda: self.training_status_label.setVisible(False))
                # 停止自动刷新
                self._stop_auto_refresh()
        except Exception:
            pass

    def _on_training_stop_failed(self, task_id, error_msg):
        """训练停止失败"""
        try:
            self._log(f"停止训练失败：{error_msg}", "error")
        except Exception:
            pass

    def _on_task_deleted(self, task_id):
        """任务删除成功"""
        try:
            if task_id:
                self._log(f"任务已删除：{task_id[:16]}...")
                self._on_refresh_clicked()
        except Exception:
            pass

    def _on_task_deletion_failed(self, task_id, error_msg):
        """任务删除失败"""
        try:
            self._log(f"删除任务失败：{error_msg}", "error")
        except Exception:
            pass

    def _on_task_list_updated(self, tasks):
        """任务列表更新"""
        try:
            cached_task_progress = {
                task_id: {
                    "epoch": task.get("epoch", 0),
                    "total_epochs": task.get("total_epochs", 0),
                    "progress": task.get("progress", 0),
                    "status": task.get("status", "unknown"),
                }
                for task_id, task in self._tasks.items()
            }
            self.task_table.setRowCount(0)
            self._tasks.clear()

            for task in tasks:
                try:
                    task_id = task.get("task_id", "unknown")
                    if not task_id or task_id == "unknown":
                        continue

                    merged_task = dict(task)
                    if task_id in cached_task_progress:
                        merged_task.update(cached_task_progress[task_id])
                    self._tasks[task_id] = merged_task

                    row = self.task_table.rowCount()
                    self.task_table.insertRow(row)

                    # 任务 ID
                    id_item = QtWidgets.QTableWidgetItem(task_id[:8] + "...")
                    id_item.setData(Qt.UserRole, task_id)
                    self.task_table.setItem(row, 0, id_item)

                    # 状态
                    status = task.get("status", "unknown")
                    status_item = QtWidgets.QTableWidgetItem(status)
                    if status == "running":
                        status_item.setForeground(QtGui.QColor("#4CAF50"))
                    elif status == "completed":
                        status_item.setForeground(QtGui.QColor("#2196F3"))
                    elif status == "failed":
                        status_item.setForeground(QtGui.QColor("#f44336"))
                    self.task_table.setItem(row, 1, status_item)

                    # 进度 - 优先使用 epoch/total_epochs 计算，与 monitor_training 一致
                    # 先从内存中获取最新的 epoch 和 total_epochs
                    saved_epoch = self._tasks.get(task_id, {}).get("epoch", 0)
                    saved_total_epochs = self._tasks.get(task_id, {}).get("total_epochs", 0)
                    
                    if saved_total_epochs and saved_total_epochs > 0:
                        # 使用内存中保存的最新值
                        progress = int((saved_epoch / saved_total_epochs) * 100)
                    else:
                        # 回退到从服务器获取的数据
                        epoch = task.get("epoch", 0)
                        total_epochs = task.get("total_epochs", 0)
                        if total_epochs and total_epochs > 0:
                            progress = int((epoch / total_epochs) * 100)
                        else:
                            progress = int(task.get("progress", 0) * 100)
                    
                    progress_item = QtWidgets.QTableWidgetItem(f"{progress}%")
                    self.task_table.setItem(row, 2, progress_item)

                    # 模型类型
                    model_type = task.get("params", {}).get("model_type", "unknown")
                    self.task_table.setItem(row, 3, QtWidgets.QTableWidgetItem(model_type))

                    # 创建时间 - 安全处理时间戳
                    start_time = task.get("start_time", 0)
                    if start_time:
                        try:
                            time_str = datetime.fromtimestamp(start_time).strftime("%m-%d %H:%M")
                        except (ValueError, OSError, OverflowError):
                            time_str = "-"
                    else:
                        time_str = "-"
                    self.task_table.setItem(row, 4, QtWidgets.QTableWidgetItem(time_str))
                except Exception:
                    # 单个任务解析失败，继续处理下一个
                    continue

            self._log(f"任务列表已更新，共 {len(tasks)} 个任务")
        except Exception as e:
            self._log(f"任务列表更新异常：{str(e)}", "error")

    def _on_task_list_failed(self, error_msg):
        """获取任务列表失败"""
        try:
            self._log(f"获取任务列表失败：{error_msg}", "error")
        except Exception:
            pass

    def _on_progress_updated(self, task_id, progress_data):
        """进度更新"""
        try:
            if not progress_data:
                return

            progress_info = progress_data.get("progress", {})
            if not progress_info:
                return

            epoch = progress_info.get("epoch", 0)
            total_epochs = progress_info.get("total_epochs", 1)
            loss = progress_info.get("loss", 0)
            accuracy = progress_info.get("accuracy", 0)
            self.training_progress_updated.emit(
                task_id,
                int(epoch),
                int(total_epochs),
                float(loss),
                float(accuracy),
            )

            # 使用 epoch/total_epochs 计算进度百分比（与 monitor_training 一致）
            if total_epochs and total_epochs > 0:
                progress_percent = int((epoch / total_epochs) * 100)
            else:
                progress_percent = 0

            # 更新当前任务进度条
            if task_id == self._current_task_id:
                self.progress_bar.setValue(progress_percent)

                # 安全格式化数值
                try:
                    self.current_epoch_label.setText(f"{int(epoch)}/{int(total_epochs)}")
                    self.current_loss_label.setText(f"{float(loss):.4f}")
                    self.current_accuracy_label.setText(f"{float(accuracy):.2f}%")
                except (ValueError, TypeError):
                    self.current_epoch_label.setText(f"{epoch}/{total_epochs}")
                    self.current_loss_label.setText(str(loss))
                    self.current_accuracy_label.setText(str(accuracy))

            # 更新任务列表中的进度显示
            if task_id in self._tasks:
                self._tasks[task_id]["progress"] = progress_percent / 100.0
                self._tasks[task_id]["epoch"] = epoch
                self._tasks[task_id]["total_epochs"] = total_epochs

                # 更新表格中的进度列
                for row in range(self.task_table.rowCount()):
                    item = self.task_table.item(row, 0)
                    if item and item.data(Qt.UserRole) == task_id:
                        self.task_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{progress_percent}%"))
                        logger.debug(f"更新任务列表进度：{task_id[:8]}... = {progress_percent}%")
                        break
        except Exception:
            # 进度更新失败不影响主程序
            pass

    def _on_status_changed(self, task_id, status_data):
        """状态变化"""
        try:
            status = status_data.get("status", "unknown")
            progress = status_data.get("progress", 0)
            
            # 打印状态到日志
            self._log(f"任务 {task_id[:16]}... 状态：{status}，进度：{progress*100:.1f}%")
            
            if task_id == self._current_task_id:
                self.current_status_label.setText(status)

            if task_id in self._tasks:
                self._tasks[task_id]["status"] = status
                # 不覆盖 progress，因为 progress_updated 已经更新了
                
                # 如果任务完成或失败，延迟刷新任务列表（防抖）
                if status in ["completed", "failed", "stopped"]:
                    self._log(f"任务 {task_id[:8]}... 状态变为 {status}，准备刷新列表...")
                    self._delayed_refresh(500)  # 延迟500ms刷新
                    
                    # 隐藏训练状态标签
                    if status == "completed":
                        self.training_status_label.setText("训练已完成")
                    elif status == "failed":
                        self.training_status_label.setText("训练失败")
                    elif status == "stopped":
                        self.training_status_label.setText("训练已停止")
                    # 3秒后隐藏状态标签
                    QtCore.QTimer.singleShot(3000, lambda: self.training_status_label.setVisible(False))

                    task_info = self._tasks.get(task_id, {})
                    epoch = task_info.get("epoch", 0)
                    total_epochs = task_info.get("total_epochs", 0)
                    if status == "completed" and total_epochs and epoch == total_epochs:
                        self.monitor_btn.setVisible(False)
                    elif status in ["failed", "stopped"]:
                        self.monitor_btn.setVisible(True)
                        self.monitor_btn.setEnabled(True)
                        self.monitor_btn.setText("监控训练")
                    
                    # 停止自动刷新（训练已结束）
                    self._stop_auto_refresh()
        except Exception:
            pass

    def _on_error(self, error_msg):
        """错误发生"""
        try:
            self._log(f"错误：{error_msg}", "error")
        except Exception:
            pass

    def _on_log_message(self, message):
        """日志消息"""
        try:
            self._log(message)
        except Exception:
            pass

    def _log(self, message, level="info"):
        """添加日志"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")

            if level == "error":
                prefix = "[错误]"
            elif level == "warning":
                prefix = "[警告]"
            else:
                prefix = "[信息]"

            self.log_text.appendPlainText(f"[{timestamp}] {prefix} {message}")
        except Exception:
            # 日志系统本身出错，静默处理
            pass

    def get_current_task_id(self):
        """获取当前选中的任务 ID"""
        return self._current_task_id

    def cleanup(self):
        """清理资源"""
        try:
            if self._manager:
                self._manager.cleanup()
            self._manager = None
            self._tasks.clear()
            self._current_task_id = None
        except Exception:
            pass
