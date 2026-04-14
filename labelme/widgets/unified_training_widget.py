"""
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
import time
import subprocess
import socket
import threading
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
        self._selected_task_ids = set()  # 存储选中的任务ID
        self._task_action_states = {}  # 记录任务瞬时状态：starting/stopping
        self._task_retry_until = {}  # 记录任务失败后的重试冷却截止时间
        self._task_server_check_pending = set()  # 记录正在查询服务端状态的任务
        self._is_auto_refresh = False  # 标记是否为自动刷新
        self._server_process = None  # 训练服务器进程句柄
        self._is_starting_server = False  # 标记是否正在启动服务器，防止重复启动
        self._server_start_lock = threading.Lock()  # 用于防止并发启动的锁
        
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
        # self.task_type_combo.addItems(["目标检测 (detect)", "图像分类 (classify)", "语义分割 (segment)"])
        self.task_type_combo.addItems(["目标检测 (detect)"])
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

        # 添加跳过数据集格式检测复选框
        self.skip_dataset_check_checkbox = QtWidgets.QCheckBox("跳过数据集格式检测（原始Labelme标注目录）")
        self.skip_dataset_check_checkbox.setChecked(True)  # 默认选中
        self.skip_dataset_check_checkbox.setToolTip("勾选此项将跳过 train.json 和 val.json 的格式检测，允许直接使用原始Labelme标注目录进行训练")
        self.basic_group.addRow("", self.skip_dataset_check_checkbox)

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
        self.batch_combo.setCurrentText("16")
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
        self.task_table.setHorizontalHeaderLabels(["", "任务 ID", "进度", "模型类型", "创建时间"])
        self.task_table.horizontalHeader().setStretchLastSection(True)
        self.task_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.task_table.horizontalHeader().resizeSection(0, 40)  # 复选框列固定宽度
        self.task_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # 禁止行选中，只通过复选框选择
        self.task_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        # 允许复选框编辑
        self.task_table.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setMinimumHeight(100)
        self.task_table.setMaximumHeight(150)

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
            QTableWidget::item {
                padding: 2px;
            }
        """)

        self.task_list_group.getContentLayout().addRow(self.task_table)

        # 任务操作按钮
        task_btn_layout = QtWidgets.QHBoxLayout()

        # 全选/取消全选按钮
        self.select_all_btn = QtWidgets.QPushButton("全选")
        self.select_all_btn.setFixedWidth(50)
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
        """)
        self.select_all_btn.clicked.connect(self._on_select_all_clicked)

        self.refresh_btn = QtWidgets.QPushButton("刷新列表")
        self.refresh_btn.setEnabled(False)

        self.get_status_btn = QtWidgets.QPushButton("获取状态")
        self.get_status_btn.setEnabled(False)
        self.get_status_btn.setToolTip("获取选中任务的详细状态")

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
        self.delete_task_btn.setEnabled(True)
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

        # 批量操作按钮
        self.batch_start_btn = QtWidgets.QPushButton("批量启动")
        self.batch_start_btn.setEnabled(False)
        self.batch_start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.batch_start_btn.clicked.connect(self._on_batch_start_clicked)

        self.batch_stop_btn = QtWidgets.QPushButton("批量停止")
        self.batch_stop_btn.setEnabled(False)
        self.batch_stop_btn.setStyleSheet("""
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
        self.batch_stop_btn.clicked.connect(self._on_batch_stop_clicked)

        self.batch_delete_btn = QtWidgets.QPushButton("批量删除")
        self.batch_delete_btn.setEnabled(False)
        self.batch_delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.batch_delete_btn.clicked.connect(self._on_batch_delete_clicked)

        # 刷新间隔控制
        refresh_interval_layout = QtWidgets.QHBoxLayout()
        refresh_interval_layout.setSpacing(4)
        self.refresh_label = QtWidgets.QLabel("刷新间隔:")
        refresh_interval_layout.addWidget(self.refresh_label)
        self.refresh_interval_spin = QtWidgets.QSpinBox()
        self.refresh_interval_spin.setRange(1, 10)
        self.refresh_interval_spin.setValue(2)
        self.refresh_interval_spin.setSuffix(" 秒")
        self.refresh_interval_spin.setFixedWidth(70)
        self.refresh_interval_spin.setToolTip("设置自动刷新任务列表的间隔时间(1-10秒)")
        refresh_interval_layout.addWidget(self.refresh_interval_spin)

        task_btn_layout.addWidget(self.select_all_btn)
        task_btn_layout.addLayout(refresh_interval_layout)
        task_btn_layout.addWidget(self.refresh_btn)
        task_btn_layout.addWidget(self.get_status_btn)
        task_btn_layout.addWidget(self.monitor_btn)
        task_btn_layout.addWidget(self.delete_task_btn)
        # 批量操作按钮已隐藏
        # task_btn_layout.addWidget(self.batch_start_btn)
        # task_btn_layout.addWidget(self.batch_stop_btn)
        # task_btn_layout.addWidget(self.batch_delete_btn)
        task_btn_layout.addStretch()

        self.task_list_group.getContentLayout().addRow(task_btn_layout)

        content_layout.addWidget(self.task_list_group)

        # ==================== 当前任务进度区域 ====================
        self.progress_group = CollapsibleGroupBox("当前任务进度")

        # 任务信息
        info_layout = QtWidgets.QFormLayout()
        self.current_task_label = QtWidgets.QLabel("无")
        self.current_epoch_label = QtWidgets.QLabel("-")
        self.current_loss_label = QtWidgets.QLabel("-")
        self.current_accuracy_label = QtWidgets.QLabel("-")

        info_layout.addRow("任务 ID:", self.current_task_label)
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
        self.task_table.itemChanged.connect(self._on_checkbox_changed)
        self.get_status_btn.setVisible(False)
        self.refresh_btn.setVisible(False)
        self.monitor_btn.setVisible(False)
        self.refresh_label.setVisible(False)
        self.refresh_interval_spin.setVisible(False)

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
            skip_dataset_check = self.skip_dataset_check_checkbox.isChecked()

            params = {
                "model_type": model_type,
                "image_size": image_size,
                "dataset": self.dataset_edit.text() or "data",
                "epochs": epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "trainset_ratio": trainset_ratio,
                "skip_dataset_check": skip_dataset_check
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
                "trainset_ratio": 0.9,
                "skip_dataset_check": False
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

    def _find_training_server_exe(self):
        """查找 training_server.exe 的路径"""
        exe_name = "TrainServer\\training_server.exe"  # Changed from training_server.exe to TrainServer\\training_server.exe
        
        # 1. 如果是打包环境，在 exe 所在目录查找
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            exe_path = os.path.join(exe_dir, exe_name)
            if os.path.exists(exe_path):
                return exe_path
        
        # 2. 在项目根目录查找（labelme 包的上两级）
        current_file = os.path.abspath(__file__)
        # labelme/widgets/unified_training_widget.py -> 上两级是项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        exe_path = os.path.join(project_root, exe_name)
        if os.path.exists(exe_path):
            return exe_path
        
        # 3. 检查 training_client/training_server.exe
        exe_path = os.path.join(project_root, "training_client", exe_name)
        if os.path.exists(exe_path):
            self._log(f"找到 {exe_name}：{exe_path}", "info")
            return exe_path
        else:
            self._log(f"未找到 {exe_name}", "warning")
        return None

    def _is_training_server_running(self):
        """检查 training_server.exe 是否正在运行（Windows）"""
        try:
            # 方法1: 使用 tasklist 检测
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq training_server.exe"],
                capture_output=True,
                text=True,
                encoding="gbk",
                errors="ignore",
                timeout=5
            )
            tasklist_found = "training_server.exe" in result.stdout
            
            # 方法2: 检查我们记录的进程是否还在运行
            process_found = False
            if self._server_process is not None:
                try:
                    poll_result = self._server_process.poll()
                    if poll_result is None:
                        process_found = True
                except Exception:
                    pass
            
            is_running = tasklist_found or process_found
            self._log(f"[进程检测] tasklist: {tasklist_found}, 进程句柄: {process_found}, 最终结果: {is_running}")
            return is_running
        except Exception as e:
            self._log(f"[进程检测] 检测异常: {e}", "error")
            return False

    def _ensure_server_running(self, host, port):
        """
        确保训练服务器正在运行并可连接
        如果未运行则启动它并显示进度对话框等待
        返回 True 表示服务器已就绪，False 表示失败

        注意：此对话框会保持打开直到 manager 真正连接成功，
        因为训练服务器可能需要3-5分钟时间才能完全启动
        """
        server_started_by_us = False
        server_pid = None  # 记录启动的服务器进程ID

        # 使用锁防止并发调用导致重复启动
        # 锁保护范围：从进程检测到进程启动的整个关键路径
        with self._server_start_lock:
            if self._is_starting_server:
                self._log("[服务器启动检查] 服务器正在启动中，忽略重复请求")
                return False
            self._is_starting_server = True

            try:
                # 先检查是否已经在运行（进程级别）
                process_was_running = self._is_training_server_running()
                self._log(f"[服务器启动检查] 进程检查: {'正在运行' if process_was_running else '未运行'}")

                # 如果 tasklist 检测到进程存在，进一步验证端口是否可达
                # 防止僵尸进程或残留进程导致误判
                if process_was_running and self._server_process is None:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        port_result = sock.connect_ex((host, port))
                        sock.close()
                        if port_result != 0:
                            self._log(f"[服务器启动检查] 进程存在但端口 {port} 不可达，判定为残留进程，尝试清理并重启", "warning")
                            # 杀掉残留进程
                            try:
                                subprocess.run(
                                    ["taskkill", "/F", "/IM", "training_server.exe"],
                                    capture_output=True, timeout=5
                                )
                                time.sleep(0.5)
                                self._log("[服务器启动检查] 已清理残留进程")
                            except Exception as kill_e:
                                self._log(f"[服务器启动检查] 清理残留进程失败: {kill_e}", "warning")
                            process_was_running = False
                        else:
                            self._log(f"[服务器启动检查] 端口 {port} 可达，进程正常运行")
                    except Exception as sock_e:
                        self._log(f"[服务器启动检查] 端口验证异常: {sock_e}，按进程不可用处理", "warning")
                        process_was_running = False

                need_start = True  # 是否需要启动新进程

                if not process_was_running:
                    # 检查是否已有我们启动的进程还在运行（tasklist 可能检测不到刚启动的进程）
                    if self._server_process is not None:
                        try:
                            poll_result = self._server_process.poll()
                            if poll_result is None:
                                # 进程仍在运行
                                self._log(f"[服务器启动检查] 已有服务器进程正在启动中（PID: {self._server_process.pid}），等待就绪...")
                                server_started_by_us = True
                                server_pid = self._server_process.pid
                                need_start = False
                            else:
                                self._log(f"[服务器启动检查] 之前的服务器进程已退出（返回码: {poll_result}）")
                                self._server_process = None
                        except Exception:
                            self._server_process = None

                    if need_start:
                        # 查找 exe 路径
                        exe_path = self._find_training_server_exe()
                        self._log(f"[服务器启动检查] 查找可执行文件: {exe_path if exe_path else '未找到'}")

                        if not exe_path:
                            # 获取当前目录信息用于提示
                            if getattr(sys, 'frozen', False):
                                exe_dir = os.path.dirname(sys.executable)
                                search_locations = f"程序所在目录: {exe_dir}"
                            else:
                                current_file = os.path.abspath(__file__)
                                project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
                                search_locations = f"项目根目录: {project_root}\n或 {project_root}\\training_client\\"

                            QtWidgets.QMessageBox.critical(
                                self,
                                "错误",
                                f"找不到 training_server.exe 文件！\n\n"
                                f"已搜索以下位置:\n{search_locations}\n\n"
                                f"请确保 training_server.exe 存在于上述位置之一。\n"
                                f"如果文件不存在，请重新安装或从官方渠道获取该文件。"
                            )
                            self._is_starting_server = False
                            return False

                        # 启动服务器进程
                        try:
                            self._log(f"[服务器启动检查] 启动服务器进程: {exe_path}")
                            self._server_process = subprocess.Popen(
                                [exe_path],
                                creationflags=subprocess.CREATE_NO_WINDOW
                            )
                            server_started_by_us = True
                            server_pid = self._server_process.pid
                            self._log(f"[服务器启动检查] 服务器进程已启动，PID: {server_pid}")
                            
                            # 等待短暂时间确保进程能被系统识别
                            time.sleep(0.5)
                            self._log(f"[服务器启动检查] 启动后进程检测: {self._is_training_server_running()}")
                        except Exception as e:
                            self._log(f"[服务器启动检查] 启动服务器进程失败: {str(e)}", "error")
                            QtWidgets.QMessageBox.critical(
                                self,
                                "启动失败",
                                f"无法启动训练服务器：{str(e)}"
                            )
                            self._is_starting_server = False
                            return False
            except Exception as e:
                # 确保异常情况下也能重置标志
                self._log(f"[服务器启动检查] 锁内操作异常: {str(e)}", "error")
                self._is_starting_server = False
                return False
        # 锁在这里释放，后续的连接等待、事件循环等不需要在锁内

        # 创建进度对话框
        progress = QtWidgets.QProgressDialog(self)
        progress.setWindowTitle("启动服务器")
        if server_started_by_us:
            progress.setLabelText("启动训练服务器...  用时: 00:00")
        else:
            progress.setLabelText("连接训练服务器...  用时: 00:00")
        progress.setRange(0, 0)  # 不确定进度（繁忙状态）
        progress.setCancelButtonText("取消")
        progress.setWindowModality(Qt.WindowModal)
        progress.setFixedWidth(400)

        # 设置蓝色进度条样式
        progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)

        # 用于跟踪状态的变量
        start_time = time.time()
        elapsed = 0
        last_log_time = 0  # 上次输出日志的时间
        max_wait = 600  # 最长等待5分钟（300秒）
        port_available = False  # 端口是否可用
        connection_established = False  # manager 是否真正连接成功
        user_cancelled = False

        # 状态统计
        port_check_count = 0  # 端口检测次数
        port_check_success = 0  # 端口检测成功次数
        manager_connect_attempts = 0  # manager 连接尝试次数
        manager_connect_success = 0  # manager 连接成功次数（通过信号）

        # 创建事件循环用于阻塞等待
        loop = QtCore.QEventLoop(self)

        # 创建定时器更新计时显示
        timer_label = QtCore.QTimer(self)

        def update_label():
            nonlocal elapsed, last_log_time
            elapsed = int(time.time() - start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60

            if not port_available:
                if server_started_by_us:
                    progress.setLabelText(f"启动训练服务器...  用时: {minutes:02d}:{seconds:02d}")
                else:
                    progress.setLabelText(f"等待服务器端口就绪...  用时: {minutes:02d}:{seconds:02d}")
            else:
                progress.setLabelText(f"连接训练服务器...  用时: {minutes:02d}:{seconds:02d}")

            # 每10秒输出一次详细日志
            if elapsed - last_log_time >= 10:
                last_log_time = elapsed
                self._log(f"[服务器启动检查] 状态报告 (已运行 {minutes:02d}:{seconds:02d}):")
                self._log(f"  - 进程状态: {'运行中' if self._is_training_server_running() else '未运行'}")
                self._log(f"  - 端口状态: {'可用' if port_available else '检测中'}")
                self._log(f"  - 端口检测: {port_check_count} 次尝试, {port_check_success} 次成功")
                self._log(f"  - Manager连接: {manager_connect_attempts} 次尝试, {manager_connect_success} 次成功信号")
                self._log(f"  - 当前manager状态: {'已连接' if self._manager and self._manager.is_connected() else '未连接'}")
                self._log(f"  - 用户取消: {user_cancelled}")

            # 检查是否超时
            if elapsed >= max_wait:
                timer_label.stop()
                if 'timer_socket' in locals():
                    timer_socket.stop()
                if 'timer_check' in locals():
                    timer_check.stop()
                loop.quit()

        timer_label.timeout.connect(update_label)
        timer_label.start(1000)  # 每秒更新

        # 创建定时器尝试检测端口
        timer_socket = QtCore.QTimer(self)

        def try_detect_port():
            nonlocal port_available, port_check_count, port_check_success
            if port_available:
                return  # 已经检测到端口，不再检测

            port_check_count += 1
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                sock.close()

                if result == 0:
                    port_check_success += 1
                    # 端口可用，停止端口检测，开始尝试 manager 连接
                    port_available = True
                    timer_socket.stop()
                    self._log(f"[服务器启动检查] 端口检测成功 (第{port_check_count}次检测)")
                    self._log(f"[服务器启动检查] 端口 {port} 已开放，开始尝试 manager 连接")
                    # 端口可用后开始尝试 manager 连接
                    try_manager_connect()
                else:
                    # 端口未开放，记录日志（每5次检测记录一次）
                    if port_check_count % 5 == 0:
                        self._log(f"[服务器启动检查] 端口 {port} 仍未开放 (已检测{port_check_count}次)")
            except Exception as e:
                if port_check_count % 5 == 0:
                    self._log(f"[服务器启动检查] 端口检测异常: {e} (已检测{port_check_count}次)")

        timer_socket.timeout.connect(try_detect_port)
        timer_socket.start(500)  # 每500ms检测一次

        # 创建定时器检查 manager 连接结果
        timer_check = QtCore.QTimer(self)
        connect_result = None  # None=等待中, True=成功, False=失败
        max_manager_attempts = 10  # manager 最大重试次数

        # 临时信号处理函数
        def on_temp_connected(success):
            nonlocal connect_result, manager_connect_success
            if not user_cancelled:
                connect_result = success
                if success:
                    manager_connect_success += 1
                    self._log(f"[服务器启动检查] 收到 connected 信号: success=True")

        def on_temp_error(msg):
            nonlocal connect_result
            if not user_cancelled:
                connect_result = False
                self._log(f"[服务器启动检查] 收到 connection_error 信号: {msg}")

        def check_connection_result():
            nonlocal connection_established, manager_connect_attempts, connect_result
            if connection_established:
                return  # 已经连接成功

            # 修复：优先检查 manager 实际连接状态，解决信号可能已发出但槽未执行的问题
            if self._manager and self._manager.is_connected():
                self._log(f"[服务器启动检查] 通过 is_connected() 检测到连接成功")
                connection_established = True
                timer_check.stop()
                timer_label.stop()
                loop.quit()
                return

            if connect_result is True:
                self._log(f"[服务器启动检查] 通过信号变量检测到连接成功")
                connection_established = True
                timer_check.stop()
                timer_label.stop()
                loop.quit()
            elif connect_result is False:
                # 连接失败，检查是否还有重试次数
                manager_connect_attempts += 1
                self._log(f"[服务器启动检查] Manager 连接失败 (第{manager_connect_attempts}/{max_manager_attempts}次尝试)")

                if manager_connect_attempts >= max_manager_attempts:
                    # 超过最大重试次数
                    self._log(f"[服务器启动检查] 超过最大重试次数 ({max_manager_attempts})，放弃连接")
                    timer_check.stop()
                    timer_label.stop()
                    loop.quit()
                else:
                    # 重试
                    connect_result = None
                    self._log(f"[服务器启动检查] 准备第{manager_connect_attempts + 1}次连接尝试...")
                    try_manager_connect()

        timer_check.timeout.connect(check_connection_result)

        def try_manager_connect():
            """尝试使用 manager 连接服务器"""
            nonlocal connect_result
            if not self._manager:
                self._log("[服务器启动检查] Manager 未初始化，无法连接")
                connect_result = False
                return

            # 修复：先检查是否已经连接，避免重复连接
            if self._manager.is_connected():
                self._log("[服务器启动检查] Manager 已经连接，无需重复连接")
                connect_result = True
                return

            # 发起连接
            self._log(f"[服务器启动检查] 发起 manager 连接: {host}:{port}")
            self._manager.connect_server(host, port)

            # 启动检查定时器（如果还没启动）
            if not timer_check.isActive():
                timer_check.start(500)  # 每500ms检查一次结果

        # 连接临时信号（只连接一次）
        # 修复：确保信号连接在调用 connect_server 之前建立
        self._manager.connected.connect(on_temp_connected)
        self._manager.connection_error.connect(on_temp_error)

        # 处理取消按钮
        def on_cancel():
            nonlocal user_cancelled
            user_cancelled = True
            self._log("[服务器启动检查] 用户取消操作")
            timer_label.stop()
            timer_socket.stop()
            timer_check.stop()
            loop.quit()

        progress.canceled.connect(on_cancel)

        # 在进入事件循环前，先尝试一次端口检测
        # 如果服务器已经在运行且端口已就绪，可以立即开始连接
        self._log("[服务器启动检查] 进入事件循环前进行首次端口检测...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                # 端口已可用，标记为可用并立即开始 manager 连接
                port_available = True
                port_check_success += 1
                self._log(f"[服务器启动检查] 首次端口检测成功，端口 {port} 已开放")
                try_manager_connect()
            else:
                self._log(f"[服务器启动检查] 首次端口检测失败，端口 {port} 未开放，等待服务器启动...")
        except Exception as e:
            self._log(f"[服务器启动检查] 首次端口检测异常: {e}")

        # 显示对话框并进入事件循环
        self._log("[服务器启动检查] 进入事件循环等待服务器就绪...")
        progress.show()
        loop.exec_()

        # 清理
        self._log("[服务器启动检查] 事件循环结束，开始清理...")
        try:
            progress.canceled.disconnect(on_cancel)
        except Exception:
            pass
        # 断开临时信号连接
        try:
            self._manager.connected.disconnect(on_temp_connected)
        except Exception:
            pass
        try:
            self._manager.connection_error.disconnect(on_temp_error)
        except Exception:
            pass
        timer_label.stop()
        timer_socket.stop()
        timer_check.stop()
        progress.close()

        if user_cancelled:
            self._log("[服务器启动检查] 用户取消，返回 False")
            self._is_starting_server = False
            return False

        # 修复：再次检查 manager 实际连接状态，因为信号可能在 cleanup 之后才发出
        if not connection_established and self._manager and self._manager.is_connected():
            self._log("[服务器启动检查] cleanup 后发现 manager 已连接")
            connection_established = True

        # 输出最终状态报告
        elapsed_final = int(time.time() - start_time)
        minutes_final = elapsed_final // 60
        seconds_final = elapsed_final % 60
        self._log(f"[服务器启动检查] 最终状态报告:")
        self._log(f"  - 总耗时: {minutes_final:02d}:{seconds_final:02d}")
        self._log(f"  - 端口检测: {port_check_count} 次")
        self._log(f"  - Manager连接尝试: {manager_connect_attempts} 次")
        self._log(f"  - 连接成功: {connection_established}")
        self._log(f"  - 进程仍在运行: {self._is_training_server_running()}")

        if connection_established:
            self._log("训练服务器已启动并成功连接")
            self._is_starting_server = False
            return True

        self._log(f"[服务器启动检查] 服务器启动超时（{max_wait//60}分钟），请手动检查服务器状态")
        QtWidgets.QMessageBox.warning(
            self,
            "启动超时",
            f"训练服务器启动超时（{max_wait//60}分钟），请手动检查服务器状态。\n\n"
            f"注意：首次启动训练服务器可能需要3-5分钟下载依赖。"
        )
        self._is_starting_server = False
        return False

    def _connect_with_retry(self, host, port):
        """
        带重试的连接方法，显示进度对话框

        Args:
            host: 服务器地址
            port: 服务器端口

        Returns:
            bool: 连接是否成功
        """
        self._log(f"[连接重试] 开始连接: {host}:{port}")

        # 创建进度对话框
        progress = QtWidgets.QProgressDialog(self)
        progress.setWindowTitle("连接服务器")
        progress.setLabelText("连接训练服务器...  第1次尝试  用时: 00:00")
        progress.setRange(0, 0)
        progress.setCancelButtonText("取消")
        progress.setWindowModality(Qt.WindowModal)
        progress.setFixedWidth(400)
        progress.setMinimumDuration(0)

        # 蓝色进度条样式
        progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)

        # 连接参数
        max_attempts = 3
        attempt_timeout = 5

        # 状态变量
        attempt = 1
        connect_result = None  # None=等待中, True=成功, False=失败
        attempt_start_time = time.time()
        last_log_time = 0  # 上次输出日志的时间
        user_cancelled = False
        finished = False  # 防止重复退出

        loop = QtCore.QEventLoop(self)

        # 临时信号处理
        def on_connected(success):
            nonlocal connect_result
            if not finished and not user_cancelled:
                connect_result = success
                self._log(f"[连接重试] 收到 connected 信号: success={success}")

        def on_error(msg):
            nonlocal connect_result
            if not finished and not user_cancelled:
                connect_result = False
                self._log(f"[连接重试] 收到 connection_error 信号: {msg}")

        # 修复：确保信号连接在调用 connect_server 之前建立
        self._manager.connected.connect(on_connected)
        self._manager.connection_error.connect(on_error)

        # 定时器：更新标签
        timer_label = QtCore.QTimer(self)

        def update_label():
            nonlocal connect_result, last_log_time
            if finished or user_cancelled:
                return
            elapsed = int(time.time() - attempt_start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            progress.setLabelText(
                f"连接训练服务器...  第{attempt}次尝试  用时: {minutes:02d}:{seconds:02d}"
            )

            # 每10秒输出一次详细日志
            total_elapsed = int(time.time() - attempt_start_time + (attempt - 1) * attempt_timeout)
            if total_elapsed - last_log_time >= 10:
                last_log_time = total_elapsed
                self._log(f"[连接重试] 状态报告 (第{attempt}次尝试, 已运行 {minutes:02d}:{seconds:02d}):")
                self._log(f"  - connect_result: {connect_result}")
                self._log(f"  - manager.is_connected(): {self._manager.is_connected() if self._manager else 'N/A'}")
                self._log(f"  - user_cancelled: {user_cancelled}")
                self._log(f"  - finished: {finished}")

            # 超时标记为失败，让 check_result 处理重试
            if elapsed >= attempt_timeout and connect_result is None:
                self._log(f"[连接重试] 第{attempt}次尝试超时 ({attempt_timeout}秒)")
                connect_result = False

        timer_label.timeout.connect(update_label)
        timer_label.start(1000)

        # 定时器：检查结果
        timer_check = QtCore.QTimer(self)

        def check_result():
            nonlocal connect_result, attempt, attempt_start_time, finished
            if finished or user_cancelled:
                return

            # 修复：优先检查 manager 实际连接状态，解决信号可能已发出但槽未执行的问题
            if self._manager and self._manager.is_connected():
                self._log(f"[连接重试] 通过 is_connected() 检测到连接成功")
                finished = True
                timer_label.stop()
                timer_check.stop()
                loop.quit()
                return

            if connect_result is True:
                # 连接成功
                self._log(f"[连接重试] 通过信号变量检测到连接成功")
                finished = True
                timer_label.stop()
                timer_check.stop()
                loop.quit()
            elif connect_result is False:
                # 当前尝试失败
                if attempt < max_attempts:
                    attempt += 1
                    self._log(f"[连接重试] 第{attempt-1}次连接失败，开始第{attempt}次尝试...")
                    connect_result = None
                    attempt_start_time = time.time()
                    self._manager.connect_server(host, port)
                else:
                    # 所有尝试都失败
                    self._log(f"[连接重试] 所有 {max_attempts} 次尝试都失败")
                    finished = True
                    timer_label.stop()
                    timer_check.stop()
                    loop.quit()

        timer_check.timeout.connect(check_result)
        timer_check.start(500)

        # 取消按钮处理
        def on_cancel():
            nonlocal user_cancelled, finished
            if finished:
                return  # 已经完成了，忽略取消
            user_cancelled = True
            finished = True
            self._log("[连接重试] 用户取消连接")
            timer_label.stop()
            timer_check.stop()
            loop.quit()

        progress.canceled.connect(on_cancel)

        # 发起第一次连接
        self._log(f"[连接重试] 发起第1次连接...")
        self._manager.connect_server(host, port)

        # 显示对话框并进入事件循环
        progress.show()
        loop.exec_()

        # 先断开 canceled 信号，防止 close() 触发假取消
        try:
            progress.canceled.disconnect(on_cancel)
        except Exception:
            pass

        # 断开临时 manager 信号连接
        try:
            self._manager.connected.disconnect(on_connected)
        except Exception:
            pass
        try:
            self._manager.connection_error.disconnect(on_error)
        except Exception:
            pass

        timer_label.stop()
        timer_check.stop()
        progress.close()

        # 修复：再次检查 manager 实际连接状态，因为信号可能在 cleanup 之后才发出
        if not finished and self._manager and self._manager.is_connected():
            self._log("[连接重试] cleanup 后发现 manager 已连接")
            finished = True

        # 输出最终状态报告
        self._log(f"[连接重试] 最终状态: finished={finished}, user_cancelled={user_cancelled}, connect_result={connect_result}")

        # 成功优先判断（即使 canceled 被意外触发，只要连接成功就返回 True）
        if finished and self._manager and self._manager.is_connected():
            self._log("已成功连接到训练服务器")
            return True

        if connect_result is True:
            self._log("已成功连接到训练服务器")
            return True

        if user_cancelled:
            self._log("用户取消连接", "warning")
            return False

        self._log(f"连接失败，已尝试 {max_attempts} 次", "error")
        return False

    # ==================== 事件处理 ====================

    def _on_server_connect_clicked(self):
        """服务器连接按钮点击"""
        try:
            if self._manager and self._manager.is_connected():
                self.server_disconnect_requested.emit()
            else:
                # 禁用连接按钮防止重复点击
                self.server_connect_btn.setEnabled(False)
                self.server_connect_btn.setText("连接中...")
                try:
                    host, port = self.get_server_config()

                    # 确保服务器正在运行（此方法会在内部完成 manager 连接）
                    if not self._ensure_server_running(host, port):
                        return

                    # 检查 manager 是否已连接（_ensure_server_running 可能已完成连接）
                    if self._manager and self._manager.is_connected():
                        # 已经连接成功，UI 更新由 manager.connected 信号自动触发
                        self._log("已连接到训练服务器")
                    else:
                        # 服务器已在运行，但需要建立 manager 连接
                        if self._connect_with_retry(host, port):
                            # 连接成功 - UI更新由 manager.connected 信号自动触发
                            pass
                        else:
                            # 连接失败 - 检查 manager 实际状态，避免状态不一致
                            if self._manager and self._manager.is_connected():
                                # manager 实际已连接（可能信号已触发了UI更新），不要覆盖
                                pass
                            else:
                                self.set_connection_status(False, "连接失败")
                                self._log("连接训练服务器失败", "error")
                finally:
                    # 恢复按钮状态
                    if not (self._manager and self._manager.is_connected()):
                        self.server_connect_btn.setEnabled(True)
                        self.server_connect_btn.setText("连接")
                    else:
                        self.server_connect_btn.setEnabled(True)
                        self.server_connect_btn.setText("断开")
        except Exception as e:
            self.server_connect_btn.setEnabled(True)
            self.server_connect_btn.setText("连接")
            self._log(f"服务器连接异常：{str(e)}", "error")

    def _on_create_task_clicked(self):
        """创建远程任务按钮点击"""
        try:
            # 检查当前是否已有任务
            task_count = len(self._tasks)
            if task_count > 0:
                reply = QtWidgets.QMessageBox.question(
                    self,
                    "确认创建新任务",
                    f"当前已有 {task_count} 个任务，是否删除当前任务并创建新任务？",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No
                )
                if reply != QtWidgets.QMessageBox.Yes:
                    return

                # 用户确认删除，先停止运行中的任务，然后删除所有任务
                running_tasks = []
                non_running_tasks = []
                for task_id in list(self._tasks.keys()):
                    status = self._get_effective_task_status(task_id)
                    if status == "running":
                        running_tasks.append(task_id)
                    else:
                        non_running_tasks.append(task_id)

                # 先停止运行中的任务
                for task_id in running_tasks:
                    try:
                        self._set_task_action_state(task_id, "stopping")
                        self._manager.stop_training(task_id)
                        self._log(f"正在停止任务：{task_id[:16]}...")
                    except Exception as e:
                        self._clear_task_action_state(task_id)
                        self._log(f"停止任务 {task_id[:16]}... 失败：{str(e)}", "error")

                # 等待一小段时间让停止操作生效
                if running_tasks:
                    QtCore.QThread.msleep(500)

                # 删除所有任务
                for task_id in list(self._tasks.keys()):
                    try:
                        self._manager.delete_task(task_id)
                    except Exception as e:
                        self._log(f"删除任务 {task_id[:16]}... 失败：{str(e)}", "error")

                self._log(f"已删除 {task_count} 个现有任务")
                self._selected_task_ids.clear()
                self._update_batch_buttons_state()

            params = self.get_training_params()
            self.create_remote_task_requested.emit(params)
            self.training_status_label.setText("正在创建任务...")
        except Exception as e:
            self._log(f"创建任务异常：{str(e)}", "error")
            self.training_status_label.setText("创建任务失败")

    def _on_start_clicked(self):
        """启动训练按钮点击 - 启动选中的复选框任务"""
        if not self._manager:
            self._log("未初始化训练管理器", "error")
            return
        
        if not self._manager.is_connected():
            self._log("未连接到服务器", "error")
            return
        
        # 获取选中的任务ID列表
        selected_tasks = list(self._selected_task_ids)
        if not selected_tasks:
            self._log("请先选择要启动的任务", "warning")
            return
        
        try:
            requested_count = 0
            for task_id in selected_tasks:
                status = self._get_effective_task_status(task_id)
                # 只启动处于 pending、stopped 或 failed 状态的任务
                if status in ["pending", "stopped", "failed", "unknown"]:
                    self._set_task_action_state(task_id, "starting")
                    self._manager.start_training(task_id)
                    requested_count += 1
                    self._log(f"正在启动任务：{task_id[:16]}...")
                elif status == "start_checking":
                    self._log(f"任务 {task_id[:16]}... 正在校验服务端状态，请稍后再试", "warning")
                elif status == "start_cooldown":
                    self._log(f"任务 {task_id[:16]}... 启动失败后冷却中，请稍后再试", "warning")
                else:
                    self._log(f"任务 {task_id[:16]}... 状态为 {status}，跳过启动", "warning")
            
            self._update_batch_buttons_state()
            if requested_count > 0:
                self._log(f"已发送 {requested_count} 个任务的启动请求")
            else:
                self._log("没有可启动的任务", "warning")
        except Exception as e:
            self._log(f"启动训练异常：{str(e)}", "error")

    def _on_stop_clicked(self):
        """停止训练按钮点击 - 停止选中的复选框任务"""
        if not self._manager:
            self._log("未初始化训练管理器", "error")
            return
        
        if not self._manager.is_connected():
            self._log("未连接到服务器", "error")
            return
        
        # 获取选中的任务ID列表
        selected_tasks = list(self._selected_task_ids)
        if not selected_tasks:
            self._log("请先选择要停止的任务", "warning")
            return
        
        try:
            requested_count = 0
            failed_tasks = []
            
            for task_id in selected_tasks:
                task = self._tasks.get(task_id, {})
                status = self._get_effective_task_status(task_id)
                # 只停止处于 running 状态的任务
                if status == "running":
                    try:
                        self._set_task_action_state(task_id, "stopping")
                        self._manager.stop_training(task_id)
                        requested_count += 1
                        self._log(f"正在停止任务：{task_id[:16]}...")
                    except Exception as e:
                        self._clear_task_action_state(task_id)
                        self._log(f"停止任务 {task_id[:16]}... 失败：{str(e)}", "error")
                        failed_tasks.append(task_id)
                else:
                    self._log(f"任务 {task_id[:16]}... 状态为 {status}，跳过停止", "warning")
            
            self._update_batch_buttons_state()
            if requested_count > 0:
                self._log(f"已发送 {requested_count} 个任务的停止请求")
            
            # 处理停止失败的任务
            if failed_tasks:
                self._log(f"有 {len(failed_tasks)} 个任务停止失败，尝试查询服务器状态...")
                self._handle_failed_stop_tasks(failed_tasks)
        except Exception as e:
            self._log(f"停止训练异常：{str(e)}", "error")

    def _handle_failed_stop_tasks(self, failed_tasks):
        """处理停止失败的任务 - 查询服务器并尝试删除"""
        if not self._manager or not self._manager.is_connected():
            return
        
        for task_id in failed_tasks:
            try:
                # 查询服务器是否存在该任务
                self._log(f"查询任务 {task_id[:16]}... 在服务器上的状态...")
                
                # 刷新任务列表以获取最新状态
                self._manager.list_tasks()
                
                # 等待一小段时间让列表更新
                QtCore.QTimer.singleShot(500, lambda tid=task_id: self._check_and_delete_task(tid))
            except Exception as e:
                self._log(f"查询任务 {task_id[:16]}... 状态失败：{str(e)}", "error")

    def _check_and_delete_task(self, task_id, retry_count=0):
        """检查任务状态并尝试删除"""
        if not self._manager:
            return
        
        # 检查任务是否还在本地列表中
        if task_id not in self._tasks:
            self._log(f"任务 {task_id[:16]}... 已从本地列表中移除")
            # 从选中集合中移除
            self._selected_task_ids.discard(task_id)
            self._update_batch_buttons_state()
            return
        
        # 检查任务是否还在服务器上
        task_in_server = False
        for tid in self._tasks.keys():
            if tid == task_id:
                task_in_server = True
                break
        
        if not task_in_server:
            # 任务不在服务器上，直接从本地列表删除
            self._log(f"任务 {task_id[:16]}... 不在服务器上，从本地列表删除")
            self._remove_task_from_list(task_id)
        else:
            # 任务在服务器上，尝试删除（最多3次）
            if retry_count < 3:
                self._log(f"尝试删除任务 {task_id[:16]}... (第 {retry_count + 1} 次)")
                try:
                    self._manager.delete_task(task_id)
                    # 删除后再次检查
                    QtCore.QTimer.singleShot(1000, lambda tid=task_id, rc=retry_count + 1: self._check_and_delete_task(tid, rc))
                except Exception as e:
                    self._log(f"删除任务 {task_id[:16]}... 失败：{str(e)}", "error")
                    # 继续重试
                    QtCore.QTimer.singleShot(1000, lambda tid=task_id, rc=retry_count + 1: self._check_and_delete_task(tid, rc))
            else:
                self._log(f"任务 {task_id[:16]}... 删除失败，已达到最大重试次数", "error")

    def _remove_task_from_list(self, task_id):
        """从任务列表中移除任务"""
        try:
            # 从本地数据中移除
            if task_id in self._tasks:
                del self._tasks[task_id]
            
            # 从选中集合中移除
            self._selected_task_ids.discard(task_id)
            self._clear_task_action_state(task_id)
            self._clear_task_retry_state(task_id)
            
            # 如果当前任务是该任务，清空当前任务
            if self._current_task_id == task_id:
                self._current_task_id = None
            
            # 刷新表格
            self._on_refresh_clicked()
            self._update_batch_buttons_state()
            
            self._log(f"任务 {task_id[:16]}... 已从列表中移除")
        except Exception as e:
            self._log(f"移除任务 {task_id[:16]}... 失败：{str(e)}", "error")

    def _on_refresh_clicked(self, is_auto_refresh=False):
        """刷新列表按钮点击（带防抖）
        
        Args:
            is_auto_refresh: 是否为自动刷新调用，自动刷新时不输出日志
        """
        if not self._manager:
            return
        
        # 记录是否为自动刷新，供后续回调使用
        self._is_auto_refresh = is_auto_refresh
        
        try:
            # 取消之前的定时器（如果存在）
            if self._refresh_timer and self._refresh_timer.isActive():
                self._refresh_timer.stop()
            
            # 立即刷新
            self._manager.list_tasks()
            # 只在手动刷新时输出日志
            if not is_auto_refresh:
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
            # 自动刷新时传入 is_auto_refresh=True
            self._auto_refresh_timer.timeout.connect(lambda: self._on_refresh_clicked(is_auto_refresh=True))

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
            final_status = "unknown"
            error_message = ""
            try:
                client = self._manager._client
                if client:
                    self._log(f"监控线程开始执行 monitor_training: {task_id[:8]}...")
                    client.monitor_training(task_id, poll_interval=2.0, callback=_on_progress_callback)
                    self._log(f"monitor_training 已返回：{task_id[:8]}...")

                    # 监控结束后获取任务最终状态和错误信息
                    try:
                        status_data = client.get_task_status(task_id)
                        if status_data:
                            final_status = status_data.get("status", "unknown")
                            # 获取错误信息（如果任务失败）
                            if final_status == "failed":
                                error_message = status_data.get("error", "")
                                # 也尝试从 metrics 中获取错误信息
                                if not error_message:
                                    metrics = status_data.get("metrics", {})
                                    if metrics:
                                        error_message = metrics.get("error", "")
                                # 如果仍然没有错误信息，使用默认信息
                                if not error_message:
                                    error_message = "训练过程中发生错误，请检查服务器日志"
                            self._log(f"任务最终状态: {final_status}")
                    except Exception as e:
                        logger.warning(f"获取任务最终状态失败: {e}")
                else:
                    self._log("训练客户端未初始化", "error")
                    error_message = "训练客户端未初始化"
            except Exception as e:
                self._log(f"监控训练异常：{str(e)}", "error")
                error_message = str(e)
            finally:
                # 将状态和错误信息传递给主线程
                try:
                    QtCore.QMetaObject.invokeMethod(
                        self, "_on_monitor_finished_with_status",
                        QtCore.Qt.QueuedConnection,
                        QtCore.Q_ARG(str, final_status),
                        QtCore.Q_ARG(str, error_message)
                    )
                except Exception as e:
                    logger.error(f"调用监控结束回调失败：{e}")
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
                    # 更新内存中的任务数据（如果不存在则创建）
                    if self._current_task_id not in self._tasks:
                        self._tasks[self._current_task_id] = {}
                    self._tasks[self._current_task_id]["progress"] = progress_percent / 100.0
                    self._tasks[self._current_task_id]["epoch"] = epoch
                    self._tasks[self._current_task_id]["total_epochs"] = total_epochs
                    self._tasks[self._current_task_id]["status"] = "running"

                    # 更新表格中的进度列（任务ID在第1列，进度在第2列）
                    row_found = False
                    for row in range(self.task_table.rowCount()):
                        item = self.task_table.item(row, 1)  # 任务ID在第1列
                        if item and item.data(Qt.UserRole) == self._current_task_id:
                            self.task_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{progress_percent}%"))
                            row_found = True
                            break
                
                # 如果表格中没有找到该任务的行，触发任务列表刷新
                if not row_found and self._manager and self._manager.is_connected():
                    logger.debug(f"表格中未找到任务 {self._current_task_id[:8]}...，触发任务列表刷新")
                    self._delayed_refresh(100)  # 100ms后刷新，避免频繁请求

            if total_epochs and total_epochs > 0 and epoch == total_epochs:
                self.training_status_label.setText("训练已完成")
                self.monitor_btn.setVisible(False)
                
                # 更新任务状态为 completed
                if self._current_task_id:
                    # 更新内存中的任务状态
                    if self._current_task_id in self._tasks:
                        self._tasks[self._current_task_id]["status"] = "completed"
                        self._tasks[self._current_task_id]["progress"] = 1.0
                    
                    # 更新表格中的进度为100%（列索引2，因为复选框在第0列，任务ID在第1列）
                    for row in range(self.task_table.rowCount()):
                        item = self.task_table.item(row, 1)  # 任务ID在第1列
                        if item and item.data(Qt.UserRole) == self._current_task_id:
                            self.task_table.setItem(row, 2, QtWidgets.QTableWidgetItem("100%"))  # 进度在第2列
                            break
                    
                    self._log(f"任务 {self._current_task_id[:16]}... 训练已完成")
        except Exception as e:
            logger.warning(f"更新监控进度失败: {e}")

    @QtCore.pyqtSlot(str, str)
    def _on_monitor_finished_with_status(self, final_status, error_message):
        """
        监控结束回调（带状态信息）

        Args:
            final_status: 任务最终状态 (completed/failed/stopped/running/pending/unknown)
            error_message: 错误信息（如果任务失败）
        """
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

        # 根据任务最终状态更新UI和显示消息
        status_display = {
            "completed": "已完成",
            "failed": "已失败",
            "stopped": "已停止",
            "running": "运行中",
            "pending": "等待中",
            "unknown": "未知"
        }

        display_status = status_display.get(final_status, final_status)

        if final_status == "completed":
            self.training_status_label.setText(f"训练{display_status}")
            self._log(f"任务 {self._current_task_id[:16]}... 训练{display_status}")
        elif final_status == "failed":
            self.training_status_label.setText(f"训练{display_status}")
            self._log(f"任务 {self._current_task_id[:16]}... 训练{display_status}", "error")
            # 显示详细的错误信息
            if error_message:
                self._log(f"错误详情: {error_message}", "error")
                # 弹出错误对话框显示报错信息
                QtWidgets.QMessageBox.critical(
                    self,
                    "训练失败",
                    f"任务训练失败！\n\n任务ID: {self._current_task_id[:16]}...\n\n错误信息:\n{error_message}"
                )
            else:
                QtWidgets.QMessageBox.critical(
                    self,
                    "训练失败",
                    f"任务训练失败！\n\n任务ID: {self._current_task_id[:16]}...\n\n请检查服务器日志获取详细信息。"
                )
        elif final_status == "stopped":
            self.training_status_label.setText(f"训练{display_status}")
            self._log(f"任务 {self._current_task_id[:16]}... 训练{display_status}", "warning")
        else:
            self._log(f"任务 {self._current_task_id[:16]}... 最终状态: {display_status}")

        # 更新内存中的任务状态
        if self._current_task_id and self._current_task_id in self._tasks:
            self._tasks[self._current_task_id]["status"] = final_status
            if error_message:
                self._tasks[self._current_task_id]["error"] = error_message

        # 刷新任务列表以更新状态
        if self._manager and self._manager.is_connected():
            self._manager.list_tasks()

        # 清除训练历史
        self._training_history = {
            'epochs': [],
            'losses': [],
            'accuracies': []
        }


    @QtCore.pyqtSlot()
    def _on_monitor_finished(self):
        """监控结束回调（旧版本，保持兼容性）"""
        # 调用新版本，使用未知状态
        self._on_monitor_finished_with_status("unknown", "")

    def _on_delete_clicked(self):
        """删除任务按钮点击 - 支持批量删除选中的任务"""
        # 首先检查是否已连接服务器
        if not self._manager or not self._manager.is_connected():
            QtWidgets.QMessageBox.warning(
                self,
                "未连接服务器",
                "请先连接服务器"
            )
            return

        try:
            # 检查父窗口是否有效
            if not self.window() or not self.window().isVisible():
                return

            # 检查是否有选中的任务
            if not self._selected_task_ids:
                QtWidgets.QMessageBox.information(
                    self,
                    "提示",
                    "请先勾选要删除的任务"
                )
                return

            # 将选中任务分为运行中和非运行中两类
            running_tasks = []
            non_running_tasks = []
            for task_id in list(self._selected_task_ids):
                status = self._get_effective_task_status(task_id)
                if status == "running":
                    running_tasks.append(task_id)
                else:
                    non_running_tasks.append(task_id)

            # 如果有运行中的任务，先询问是否停止
            if running_tasks:
                reply = QtWidgets.QMessageBox.warning(
                    self,
                    "确认删除",
                    f"选中的任务中有 {len(running_tasks)} 个正在运行，删除前需要先停止这些任务。是否继续？",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No
                )
                if reply != QtWidgets.QMessageBox.Yes:
                    return

                # 用户确认，先停止运行中的任务
                for task_id in running_tasks:
                    try:
                        self._set_task_action_state(task_id, "stopping")
                        self._manager.stop_training(task_id)
                        self._log(f"正在停止任务：{task_id[:16]}...")
                    except Exception as e:
                        self._clear_task_action_state(task_id)
                        self._log(f"停止任务 {task_id[:16]}... 失败：{str(e)}", "error")

                # 等待一小段时间让停止操作生效
                QtCore.QThread.msleep(500)

                # 删除所有选中的任务（包括运行中和非运行中）
                count = 0
                for task_id in list(self._selected_task_ids):
                    try:
                        self._manager.delete_task(task_id)
                        count += 1
                    except Exception as e:
                        self._log(f"删除任务 {task_id[:16]}... 失败：{str(e)}", "error")

                self._log(f"批量删除 {count} 个任务")
                self._selected_task_ids.clear()
                self._update_batch_buttons_state()
            else:
                # 没有运行中的任务，走正常的确认删除流程
                reply = QtWidgets.QMessageBox.question(
                    self,
                    "确认批量删除",
                    f"确定要删除选中的 {len(self._selected_task_ids)} 个任务吗？",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                    QtWidgets.QMessageBox.No
                )
                if reply == QtWidgets.QMessageBox.Yes:
                    count = 0
                    for task_id in list(self._selected_task_ids):
                        try:
                            self._manager.delete_task(task_id)
                            count += 1
                        except Exception as e:
                            self._log(f"删除任务 {task_id[:16]}... 失败：{str(e)}", "error")

                    self._log(f"批量删除 {count} 个任务")
                    self._selected_task_ids.clear()
                    self._update_batch_buttons_state()
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
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                return

            row = selected[0].row()
            # 注意：现在任务ID在第1列（索引1），复选框在第0列
            item = self.task_table.item(row, 1)
            if not item:
                self._current_task_id = None
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                return

            task_id = item.data(Qt.UserRole)
            if not task_id:
                self._current_task_id = None
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                return

            self._current_task_id = task_id

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
            self.monitor_btn.setVisible(not (total_epochs and epoch == total_epochs))
        except Exception as e:
            self._log(f"任务选择异常：{str(e)}", "error")
            self._current_task_id = None
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

    def _on_checkbox_changed(self, item):
        """复选框状态变化处理"""
        try:
            # 只处理第0列（复选框列）
            if item.column() != 0:
                return
            
            row = item.row()
            checkbox_item = self.task_table.item(row, 0)
            if not checkbox_item:
                return
            
            # 获取任务ID
            task_id_item = self.task_table.item(row, 1)
            if not task_id_item:
                return
            
            task_id = task_id_item.data(Qt.UserRole)
            if not task_id:
                return
            
            # 根据复选框状态更新选中集合
            if checkbox_item.checkState() == Qt.Checked:
                self._selected_task_ids.add(task_id)
            else:
                self._selected_task_ids.discard(task_id)
            
            # 更新批量操作按钮状态
            self._update_batch_buttons_state()
        except Exception as e:
            logger.error(f"复选框状态变化处理异常：{e}")

    def _update_batch_buttons_state(self):
        """更新按钮状态 - 基于复选框选中的任务"""
        has_selection = len(self._selected_task_ids) > 0
        is_connected = self._manager and self._manager.is_connected()
        
        # 检查选中的任务中是否有可启动的（pending、stopped、failed 状态）
        has_startable = False
        # 检查选中的任务中是否有可停止的（running 状态）
        has_stoppable = False
        
        for task_id in self._selected_task_ids:
            task = self._tasks.get(task_id, {})
            status = self._get_effective_task_status(task_id)
            if status in ["pending", "stopped", "failed", "unknown"]:
                has_startable = True
            if status == "running":
                has_stoppable = True
        
        # 更新启动按钮状态（有选中任务且至少有一个可启动的任务）
        self.start_btn.setEnabled(has_selection and is_connected and has_startable)
        
        # 更新停止按钮状态（有选中任务且至少有一个可停止的任务）
        self.stop_btn.setEnabled(has_selection and is_connected and has_stoppable)
        
        # 更新批量操作按钮状态（已隐藏但保留功能）
        self.batch_start_btn.setEnabled(has_selection and is_connected)
        self.batch_stop_btn.setEnabled(has_selection and is_connected)
        self.batch_delete_btn.setEnabled(has_selection and is_connected)
        
        # 删除按钮始终保持激活，点击时在槽函数中检查
        
        # 更新全选按钮文本
        if self.task_table.rowCount() > 0 and len(self._selected_task_ids) == self.task_table.rowCount():
            self.select_all_btn.setText("取消")
        else:
            self.select_all_btn.setText("全选")

    def _on_select_all_clicked(self):
        """全选/取消全选按钮点击"""
        try:
            if self.select_all_btn.text() == "全选":
                # 全选
                self._selected_task_ids.clear()
                for row in range(self.task_table.rowCount()):
                    checkbox_item = self.task_table.item(row, 0)
                    if checkbox_item:
                        checkbox_item.setCheckState(Qt.Checked)
                    task_id_item = self.task_table.item(row, 1)
                    if task_id_item:
                        task_id = task_id_item.data(Qt.UserRole)
                        if task_id:
                            self._selected_task_ids.add(task_id)
                self.select_all_btn.setText("取消")
            else:
                # 取消全选
                for row in range(self.task_table.rowCount()):
                    checkbox_item = self.task_table.item(row, 0)
                    if checkbox_item:
                        checkbox_item.setCheckState(Qt.Unchecked)
                self._selected_task_ids.clear()
                self.select_all_btn.setText("全选")
            
            self._update_batch_buttons_state()
        except Exception as e:
            logger.error(f"全选操作异常：{e}")

    def _on_batch_start_clicked(self):
        """批量启动任务"""
        if not self._selected_task_ids or not self._manager:
            return
        
        if not self._manager.is_connected():
            self._log("未连接到服务器", "error")
            return
        
        try:
            count = 0
            for task_id in self._selected_task_ids:
                task = self._tasks.get(task_id, {})
                status = task.get("status", "unknown")
                # 只启动处于 pending、stopped 或 failed 状态的任务
                if status in ["pending", "stopped", "failed"]:
                    self._manager.start_training(task_id)
                    count += 1
            
            self._log(f"批量启动 {count} 个任务")
        except Exception as e:
            self._log(f"批量启动任务异常：{str(e)}", "error")

    def _on_batch_stop_clicked(self):
        """批量停止任务"""
        if not self._selected_task_ids or not self._manager:
            return
        
        if not self._manager.is_connected():
            self._log("未连接到服务器", "error")
            return
        
        try:
            count = 0
            for task_id in self._selected_task_ids:
                task = self._tasks.get(task_id, {})
                status = task.get("status", "unknown")
                # 只停止处于 running 状态的任务
                if status == "running":
                    self._manager.stop_training(task_id)
                    count += 1
            
            self._log(f"批量停止 {count} 个任务")
        except Exception as e:
            self._log(f"批量停止任务异常：{str(e)}", "error")

    def _on_batch_delete_clicked(self):
        """批量删除任务"""
        if not self._selected_task_ids or not self._manager:
            return
        
        if not self._manager.is_connected():
            self._log("未连接到服务器", "error")
            return
        
        try:
            # 确认删除
            reply = QtWidgets.QMessageBox.question(
                self,
                "确认批量删除",
                f"确定要删除选中的 {len(self._selected_task_ids)} 个任务吗？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            
            if reply == QtWidgets.QMessageBox.Yes:
                count = 0
                for task_id in list(self._selected_task_ids):
                    self._manager.delete_task(task_id)
                    count += 1
                
                self._log(f"批量删除 {count} 个任务")
                self._selected_task_ids.clear()
                self._update_batch_buttons_state()
        except Exception as e:
            self._log(f"批量删除任务异常：{str(e)}", "error")

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
                self._clear_task_action_state(task_id)
                self._clear_task_retry_state(task_id)
                if task_id not in self._tasks:
                    self._tasks[task_id] = {}
                self._tasks[task_id]["status"] = "running"
                self._current_task_id = task_id
                self.training_status_label.setText("训练中...")
                self.training_status_label.setVisible(True)
                self._log(f"训练已启动：{task_id[:16]}...")
                self.monitor_btn.setVisible(True)
                self.monitor_btn.setText("监控训练")
                self._update_batch_buttons_state()
                # 延迟刷新任务列表（训练刚启动时服务器可能还未更新状态）
                QtCore.QTimer.singleShot(500, self._on_refresh_clicked)
                # 立即获取当前任务状态
                if self._manager:
                    self._manager.get_task_status(task_id)
                self._start_monitoring_task(task_id, auto_started=True)
                # 启动自动刷新任务列表（确保表格进度与监控进度同步）
                self._start_auto_refresh()
        except Exception:
            pass

    def _on_training_start_failed(self, task_id, error_msg):
        """训练启动失败"""
        try:
            self._clear_task_action_state(task_id)
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = "stopped"
            self._task_retry_until[task_id] = time.monotonic() + 2.0
            self._update_batch_buttons_state()
            self._log(f"启动训练失败：{error_msg}", "error")
            self._handle_failed_start_tasks([task_id])
        except Exception:
            pass

    def _on_training_stopped(self, task_id):
        """训练停止成功"""
        try:
            if task_id:
                self._clear_task_action_state(task_id)
                self._clear_task_retry_state(task_id)
                if task_id not in self._tasks:
                    self._tasks[task_id] = {}
                self._tasks[task_id]["status"] = "stopped"
                self.training_status_label.setText("训练已停止")
                self._log(f"训练已停止：{task_id[:16]}...")
                self.monitor_btn.setVisible(True)
                self.monitor_btn.setEnabled(True)
                self.monitor_btn.setText("监控训练")
                self._update_batch_buttons_state()
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
            # 保存当前任务的进度信息到缓存（包括监控中的最新数据）
            cached_task_progress = {
                task_id: {
                    "epoch": task.get("epoch", 0),
                    "total_epochs": task.get("total_epochs", 0),
                    "progress": task.get("progress", 0),
                    "status": task.get("status", "unknown"),
                }
                for task_id, task in self._tasks.items()
            }
            
            # 如果当前有监控中的任务，确保使用最新的监控数据
            if self._is_monitoring and self._monitor_target_task_id:
                monitor_task_id = self._monitor_target_task_id
                if monitor_task_id in self._tasks:
                    monitor_task = self._tasks[monitor_task_id]
                    cached_task_progress[monitor_task_id] = {
                        "epoch": monitor_task.get("epoch", 0),
                        "total_epochs": monitor_task.get("total_epochs", 0),
                        "progress": monitor_task.get("progress", 0),
                        "status": monitor_task.get("status", "unknown"),
                    }
            
            valid_task_ids = {
                task.get("task_id")
                for task in tasks
                if task.get("task_id") and task.get("task_id") != "unknown"
            }
            self._selected_task_ids.intersection_update(valid_task_ids)
            if self._current_task_id and self._current_task_id not in valid_task_ids:
                self._current_task_id = None

            self.task_table.blockSignals(True)
            self.task_table.setRowCount(0)
            self._tasks.clear()

            for task in tasks:
                try:
                    task_id = task.get("task_id", "unknown")
                    if not task_id or task_id == "unknown":
                        continue

                    merged_task = dict(task)
                    # 优先使用缓存中的数据（包含监控的最新进度）
                    if task_id in cached_task_progress:
                        cached_data = cached_task_progress[task_id]
                        # 只有当缓存中有有效的 epoch/total_epochs 时才使用
                        if cached_data.get("total_epochs", 0) > 0:
                            merged_task["epoch"] = cached_data["epoch"]
                            merged_task["total_epochs"] = cached_data["total_epochs"]
                            merged_task["progress"] = cached_data["progress"]
                        # 状态总是使用最新的
                        if cached_data.get("status", "unknown") != "unknown":
                            merged_task["status"] = cached_data["status"]
                    self._tasks[task_id] = merged_task

                    row = self.task_table.rowCount()
                    self.task_table.insertRow(row)

                    # 复选框列（第0列）
                    checkbox_item = QtWidgets.QTableWidgetItem()
                    checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    # 如果该任务之前被选中，保持选中状态
                    if task_id in self._selected_task_ids:
                        checkbox_item.setCheckState(Qt.Checked)
                    else:
                        checkbox_item.setCheckState(Qt.Unchecked)
                    checkbox_item.setTextAlignment(Qt.AlignCenter)
                    self.task_table.setItem(row, 0, checkbox_item)

                    # 任务 ID（第1列）
                    id_item = QtWidgets.QTableWidgetItem(task_id[:8] + "...")
                    id_item.setData(Qt.UserRole, task_id)
                    self.task_table.setItem(row, 1, id_item)

                    # 进度 - 优先使用 epoch/total_epochs 计算，与 monitor_training 一致
                    # 使用合并后的任务数据（包含缓存的最新进度）
                    saved_epoch = merged_task.get("epoch", 0)
                    saved_total_epochs = merged_task.get("total_epochs", 0)
                    
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

                    # 模型类型（第3列）
                    model_type = task.get("params", {}).get("model_type", "unknown")
                    self.task_table.setItem(row, 3, QtWidgets.QTableWidgetItem(model_type))

                    # 创建时间 - 安全处理时间戳（第4列）
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

            # 只在手动刷新时输出日志
            if not self._is_auto_refresh:
                self._log(f"任务列表已更新，共 {len(tasks)} 个任务")
            
            # 更新按钮状态（基于复选框选中的任务）
            self._update_batch_buttons_state()
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

                # 更新表格中的进度列（列索引2，因为复选框在第0列，任务ID在第1列）
                for row in range(self.task_table.rowCount()):
                    item = self.task_table.item(row, 1)  # 任务ID在第1列
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

            if task_id in self._tasks:
                self._tasks[task_id]["status"] = status
                if status in ["running", "pending", "stopped", "failed", "completed"]:
                    self._clear_task_retry_state(task_id)
                self._clear_task_action_state(task_id)
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

    def _handle_failed_stop_tasks(self, failed_tasks):
        """处理停止失败的任务，刷新列表并清理服务端已不存在的任务"""
        if not failed_tasks or not self._manager or not self._manager.is_connected():
            return

        try:
            for task_id in failed_tasks:
                self._log(f"查询任务 {task_id[:16]}... 在服务端的状态...")

            self._manager.list_tasks()
            QtCore.QTimer.singleShot(
                500,
                lambda task_ids=list(failed_tasks): self._cleanup_missing_tasks_after_stop_failure(task_ids),
            )
        except Exception as e:
            self._log(f"查询停止失败任务状态异常：{str(e)}", "error")

    def _cleanup_missing_tasks_after_stop_failure(self, task_ids):
        """停止失败后，移除服务端已不存在任务的本地选中/详情状态"""
        if not task_ids:
            return

        removed_count = 0
        for task_id in task_ids:
            if task_id in self._tasks:
                continue

            removed_count += 1
            self._selected_task_ids.discard(task_id)

            if self._current_task_id == task_id:
                self._current_task_id = None
                self.current_task_label.setText("无")
                self.current_epoch_label.setText("-")
                self.current_loss_label.setText("-")
                self.current_accuracy_label.setText("-")
                self.progress_bar.setValue(0)

            self._log(f"任务 {task_id[:16]}... 在服务端不存在，已从任务列表移除", "warning")

        if removed_count:
            self._update_batch_buttons_state()

    def _handle_failed_start_tasks(self, failed_tasks):
        """处理启动失败的任务，刷新列表并清理服务端已不存在的任务"""
        if not failed_tasks or not self._manager or not self._manager.is_connected():
            return

        try:
            pending_tasks = []
            for task_id in failed_tasks:
                if task_id in self._task_server_check_pending:
                    continue
                self._task_server_check_pending.add(task_id)
                pending_tasks.append(task_id)
                self._log(f"查询任务 {task_id[:16]}... 在服务端的状态...", "warning")

            if not pending_tasks:
                return

            self._update_batch_buttons_state()
            self._manager.list_tasks()
            QtCore.QTimer.singleShot(
                500,
                lambda task_ids=list(pending_tasks): self._cleanup_missing_tasks_after_start_failure(task_ids),
            )
        except Exception as e:
            for task_id in failed_tasks:
                self._task_server_check_pending.discard(task_id)
            self._log(f"查询启动失败任务状态异常：{str(e)}", "error")

    def _cleanup_missing_tasks_after_start_failure(self, task_ids):
        """启动失败后，移除服务端已不存在的任务并提示用户"""
        if not task_ids:
            return

        removed_task_ids = []
        for task_id in task_ids:
            self._task_server_check_pending.discard(task_id)
            if task_id in self._tasks:
                continue

            removed_task_ids.append(task_id)
            self._task_action_states.pop(task_id, None)
            self._selected_task_ids.discard(task_id)

            if self._current_task_id == task_id:
                self._current_task_id = None
                self.current_task_label.setText("无")
                self.current_epoch_label.setText("-")
                self.current_loss_label.setText("-")
                self.current_accuracy_label.setText("-")
                self.progress_bar.setValue(0)

            self._log(f"任务 {task_id[:16]}... 在服务端不存在，已从任务列表移除", "warning")

        if removed_task_ids:
            self._update_batch_buttons_state()
            task_text = "、".join(
                [f"{task_id[:8]}..." if len(task_id) > 8 else task_id for task_id in removed_task_ids]
            )
            QtWidgets.QMessageBox.warning(
                self,
                "任务已删除",
                f"任务 {task_text} 已被服务器删除，已从任务列表中移除。",
            )
        else:
            self._update_batch_buttons_state()

    def _on_training_stop_failed(self, task_id, error_msg):
        """训练停止失败"""
        try:
            self._clear_task_retry_state(task_id)
            self._clear_task_action_state(task_id)
            if task_id in self._tasks and self._tasks[task_id].get("status") == "stopping":
                self._tasks[task_id]["status"] = "running"
            self._update_batch_buttons_state()
            self._log(f"停止训练失败：{error_msg}", "error")
            self._handle_failed_stop_tasks([task_id])
        except Exception:
            pass

    def _update_batch_buttons_state(self):
        """\u66f4\u65b0\u6309\u94ae\u72b6\u6001 - \u57fa\u4e8e\u590d\u9009\u6846\u9009\u4e2d\u7684\u4efb\u52a1"""
        self.task_table.blockSignals(False)
        has_selection = len(self._selected_task_ids) > 0
        is_connected = self._manager and self._manager.is_connected()

        has_startable = False
        has_stoppable = False

        for task_id in self._selected_task_ids:
            task = self._tasks.get(task_id, {})
            status = task.get("status", "unknown")
            if status in ["pending", "stopped", "failed", "unknown"]:
                has_startable = True
            if status == "running":
                has_stoppable = True

        self.start_btn.setEnabled(has_selection and is_connected and has_startable)
        self.stop_btn.setEnabled(has_selection and is_connected and has_stoppable)
        self.batch_start_btn.setEnabled(has_selection and is_connected)
        self.batch_stop_btn.setEnabled(has_selection and is_connected)
        self.batch_delete_btn.setEnabled(has_selection and is_connected)

        if self.task_table.rowCount() > 0 and len(self._selected_task_ids) == self.task_table.rowCount():
            self.select_all_btn.setText("\u53d6\u6d88")
        else:
            self.select_all_btn.setText("\u5168\u9009")

    def _get_effective_task_status(self, task_id):
        """获取任务当前有效状态，优先使用本地瞬时状态"""
        if task_id in self._task_server_check_pending:
            return "start_checking"

        retry_until = self._task_retry_until.get(task_id)
        if retry_until and retry_until > time.monotonic():
            return "start_cooldown"
        if retry_until and retry_until <= time.monotonic():
            self._task_retry_until.pop(task_id, None)

        transient_status = self._task_action_states.get(task_id)
        if transient_status:
            return transient_status
        return self._tasks.get(task_id, {}).get("status", "unknown")

    def _set_task_action_state(self, task_id, state):
        """设置任务瞬时操作状态"""
        self._task_action_states[task_id] = state
        if task_id not in self._tasks:
            self._tasks[task_id] = {}
        self._tasks[task_id]["status"] = state

    def _clear_task_action_state(self, task_id):
        """清理任务瞬时操作状态"""
        self._task_action_states.pop(task_id, None)

    def _clear_task_retry_state(self, task_id):
        """清理任务失败后的重试限制状态"""
        self._task_retry_until.pop(task_id, None)
        self._task_server_check_pending.discard(task_id)

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
            # 停止定时器
            if hasattr(self, '_refresh_timer') and self._refresh_timer:
                self._refresh_timer.stop()
            if hasattr(self, '_auto_refresh_timer') and self._auto_refresh_timer:
                self._auto_refresh_timer.stop()
            
            # 清理管理器
            if self._manager:
                self._manager.cleanup()
            self._manager = None
            self._tasks.clear()
            self._current_task_id = None
            
            # 关闭训练服务器进程
            self._terminate_training_server()
        except Exception:
            pass

    def _terminate_training_server(self):
        """终止训练服务器进程"""
        try:
            if self._server_process is not None:
                # 先尝试优雅终止
                self._server_process.terminate()
                try:
                    self._server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 超时则强制杀死
                    self._server_process.kill()
                    self._server_process.wait(timeout=3)
                self._server_process = None
                logger.info("训练服务器进程已关闭")
        except Exception as e:
            logger.warning(f"关闭训练服务器进程时出错: {e}")
            # 如果通过句柄关闭失败，尝试用 taskkill 强制结束
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "training_server.exe"],
                    capture_output=True,
                    timeout=5
                )
            except Exception:
                pass
            self._server_process = None
