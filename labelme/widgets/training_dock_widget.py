# -*- coding: utf-8 -*-
"""
训练配置停靠窗口组件

提供训练任务的参数配置界面，包含：
- 基本信息：任务类型、工程名
- 参数：网络类别、批次数量、步数、学习率、训练/验证集比例、训练算法库
- 训练样本：标签 - 模型库名 - 时间 表格
"""

import os
import json
import sys

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from loguru import logger


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


class TrainingDockWidget(QtWidgets.QWidget):
    """训练配置面板主组件"""

    # 信号定义
    create_remote_task_requested = QtCore.pyqtSignal(dict)  # 请求创建远程任务，携带参数字典
    start_training_requested = QtCore.pyqtSignal()  # 请求启动训练
    stop_training_requested = QtCore.pyqtSignal()  # 请求停止训练
    server_connect_requested = QtCore.pyqtSignal(str, int)  # 请求连接服务器 (host, port)
    server_disconnect_requested = QtCore.pyqtSignal()  # 请求断开服务器连接

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = None
        self._setup_ui()

    def _get_default_dataset_path(self):
        """
        获取默认数据集路径

        从 labelme_config.json 文件中读取 default_images_folder 配置

        Returns:
            str: 默认路径，如果读取失败则返回 None
        """
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
            logger.warning(f"读取默认数据集路径失败：{e}")

        return None

    def _on_browse_dataset(self):
        """浏览数据集文件夹"""
        try:
            current_path = self.dataset_edit.text()

            # 如果当前路径无效，使用默认路径
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
            logger.warning(f"浏览数据集异常：{e}")

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
        self.server_status_layout.addStretch()
        self.server_status_layout.addWidget(self.server_connect_btn)
        status_widget = QtWidgets.QWidget()
        status_widget.setLayout(self.server_status_layout)
        self.server_group.addRow("状态：", status_widget)

        main_layout.addWidget(self.server_group)

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

        # 加载默认路径
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

        main_layout.addWidget(self.basic_group)

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

        # ==================== 训练样本 (已隐藏) ====================
        # 训练样本部分暂时隐藏
        self.sample_group = None
        self.sample_table = None
        self.add_button = None

        # ==================== 远程训练操作区域 ====================
        self.remote_group = CollapsibleGroupBox("远程训练")

        # 训练模式选择（已隐藏，默认远程训练）
        self.mode_local_radio = None
        self.mode_remote_radio = None

        # 操作按钮
        btn_layout = QtWidgets.QHBoxLayout()

        self.create_task_btn = QtWidgets.QPushButton("创建远程任务")
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
        self.create_task_btn.setEnabled(False)  # 默认禁用，连接到服务器后启用

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

        self.remote_group.getContentLayout().addRow(btn_layout)

        # 状态标签
        self.training_status_label = QtWidgets.QLabel("就绪")
        self.training_status_label.setStyleSheet("color: #666; font-size: 11px;")
        self.training_status_label.setAlignment(Qt.AlignCenter)
        self.remote_group.getContentLayout().addRow(self.training_status_label)

        content_layout.addWidget(self.remote_group)

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

    # ==================== 远程训练相关方法 ====================

    def set_manager(self, manager):
        """
        设置训练客户端管理器

        Args:
            manager: TrainingClientManager 实例
        """
        # 检查 manager 是否为 None，避免空指针异常
        if manager is None:
            logger.warning("[TrainingDock] 管理器为None，跳过设置")
            self._manager = None
            return
        
        self._manager = manager
        logger.info(f"[TrainingDock] 设置训练管理器: {type(manager).__name__}")

        # 连接管理器信号
        try:
            manager.connected.connect(self._on_manager_connected)
            manager.connection_error.connect(self._on_connection_error)
            manager.task_created.connect(self._on_task_created)
            manager.task_creation_failed.connect(self._on_task_creation_failed)
            manager.training_started.connect(self._on_training_started)
            manager.training_stopped.connect(self._on_training_stopped)
            manager.status_changed.connect(self._on_status_changed)
            logger.info("[TrainingDock] 管理器信号连接完成")
        except AttributeError as e:
            logger.error(f"[TrainingDock] 管理器信号连接失败，缺少必要属性: {e}")
            self._manager = None

    def _on_manager_connected(self, success):
        """管理器连接状态变化"""
        try:
            logger.info(f"[TrainingDock] 管理器连接状态变化: success={success}")
            self.set_connection_status(success)
            self.enable_server_edit(not success)
            # 默认远程训练模式，连接成功后启用创建任务按钮
            if success:
                self.create_task_btn.setEnabled(True)
                logger.info("[TrainingDock] 连接成功，已启用创建任务按钮")
            else:
                self.create_task_btn.setEnabled(False)
                logger.warning("[TrainingDock] 连接失败，创建任务按钮已禁用")
        except Exception as e:
            logger.error(f"[TrainingDock] 处理连接状态变化异常: {e}")

    def _on_connection_error(self, error_msg: str):
        """连接错误处理"""
        try:
            logger.error(f"[TrainingDock] 连接错误: {error_msg}")
            self.set_connection_status(False, "连接失败")
            self.training_status_label.setText(f"连接失败: {error_msg}")
        except Exception as e:
            logger.error(f"[TrainingDock] 处理连接错误异常: {e}")

    def _on_task_creation_failed(self, error_msg: str):
        """任务创建失败处理"""
        try:
            logger.error(f"[TrainingDock] 任务创建失败: {error_msg}")
            self.training_status_label.setText(f"创建失败: {error_msg}")
        except Exception as e:
            logger.error(f"[TrainingDock] 处理任务创建失败异常: {e}")

    def _on_create_task_clicked(self):
        """创建远程任务按钮点击"""
        try:
            # 收集参数
            params = self.get_training_params()
            logger.info(f"[TrainingDock] 发起创建任务请求: {params}")
            self.create_remote_task_requested.emit(params)
            self.training_status_label.setText("正在创建任务...")
        except Exception as e:
            self.training_status_label.setText("创建任务失败")
            logger.error(f"[TrainingDock] 创建任务异常: {e}")

    def _on_start_clicked(self):
        """启动训练按钮点击"""
        try:
            self.start_training_requested.emit()
        except Exception as e:
            logger.error(f"启动训练异常：{e}")

    def _on_stop_clicked(self):
        """停止训练按钮点击"""
        try:
            self.stop_training_requested.emit()
        except Exception as e:
            logger.error(f"停止训练异常：{e}")

    def _on_server_connect_clicked(self):
        """服务器连接按钮点击"""
        try:
            if self._manager and self._manager.is_connected():
                # 如果已连接，则断开
                logger.info("[TrainingDock] 发起断开服务器连接请求")
                self.server_disconnect_requested.emit()
            else:
                # 未连接，发起连接
                host, port = self.get_server_config()
                logger.info(f"[TrainingDock] 发起服务器连接请求: {host}:{port}")
                self.server_connect_requested.emit(host, port)
                self.set_connection_status(False, "连接中...")
                logger.info("[TrainingDock] UI状态已更新为'连接中...'")
        except Exception as e:
            logger.error(f"[TrainingDock] 服务器连接操作异常: {e}")

    def _on_task_created(self, task_id):
        """任务创建成功"""
        try:
            if task_id:
                # 确保 task_id 是字符串类型，避免切片异常
                task_id_str = str(task_id) if not isinstance(task_id, str) else task_id
                self.training_status_label.setText(f"任务已创建：{task_id_str[:8]}...")
                self.start_btn.setEnabled(True)
        except Exception as e:
            logger.error(f"[TrainingDock] 处理任务创建成功异常: {e}")

    def _on_training_started(self, task_id):
        """训练启动成功"""
        try:
            if task_id:
                self.training_status_label.setText("训练中...")
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
        except Exception as e:
            logger.error(f"[TrainingDock] 处理训练启动成功异常: {e}")

    def _on_training_stopped(self, task_id):
        """训练停止成功"""
        try:
            if task_id:
                self.training_status_label.setText("训练已停止")
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
        except Exception as e:
            logger.error(f"[TrainingDock] 处理训练停止成功异常: {e}")

    def _on_status_changed(self, task_id, status_data):
        """任务状态变化"""
        try:
            # 检查 status_data 是否为 None，避免空指针异常
            if status_data is None:
                logger.warning(f"[TrainingDock] 任务状态变化收到 None status_data")
                return
            
            status = status_data.get("status", "unknown")
            
            # 确保 task_id 是字符串类型，避免切片异常
            task_id_str = str(task_id) if task_id and not isinstance(task_id, str) else (task_id or "unknown")
            logger.info(f"[TrainingDock] 任务 {task_id_str[:8]}... 状态变化: {status}")
            
            if status == "completed":
                self.training_status_label.setText("训练已完成")
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                logger.info(f"[TrainingDock] 训练完成: {task_id_str}")
            elif status == "failed":
                self.training_status_label.setText("训练失败")
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                logger.error(f"[TrainingDock] 训练失败: {task_id_str}")
            elif status == "stopped":
                # 已由 _on_training_stopped 处理
                pass
        except Exception as e:
            logger.error(f"[TrainingDock] 处理状态变化异常: {e}")

    def get_training_params(self):
        """
        获取训练参数

        Returns:
            dict: 训练参数字典
        """
        try:
            # 从任务类型文本中提取模型类型
            task_type_text = self.task_type_combo.currentText()
            if "detect" in task_type_text:
                model_type = "detect"
            elif "classify" in task_type_text:
                model_type = "classify"
            elif "segment" in task_type_text:
                model_type = "segment"
            else:
                model_type = "detect"

            # 获取图像尺寸
            try:
                image_size = int(self.image_size_combo.currentText())
            except (ValueError, TypeError):
                image_size = 640

            # 获取训练轮次
            epochs = self.epochs_spin.value()

            # 获取批次大小
            try:
                batch_size = int(self.batch_combo.currentText())
            except (ValueError, TypeError):
                batch_size = 32

            # 获取学习率
            try:
                learning_rate = float(self.lr_combo.currentText())
            except (ValueError, TypeError):
                learning_rate = 0.001

            # 获取训练集比例
            try:
                trainset_ratio = float(self.train_ratio_combo.currentText())
            except (ValueError, TypeError):
                trainset_ratio = 0.9

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
            logger.error(f"获取训练参数异常：{e}")
            # 返回默认参数
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
        """
        获取服务器配置

        Returns:
            tuple: (host, port)
        """
        try:
            host = self.server_host_edit.text().strip() or "127.0.0.1"
            port = self.server_port_spin.value()
            return host, port
        except Exception:
            return "127.0.0.1", 8888

    def set_connection_status(self, connected, message=None):
        """
        设置连接状态显示

        Args:
            connected: 是否已连接
            message: 状态消息
        """
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
        """
        启用/禁用服务器配置编辑

        Args:
            enabled: 是否启用
        """
        try:
            self.server_host_edit.setEnabled(enabled)
            self.server_port_spin.setEnabled(enabled)
        except Exception:
            pass

    def set_training_status(self, status_text):
        """
        设置训练状态文本

        Args:
            status_text: 状态文本
        """
        try:
            self.training_status_label.setText(status_text)
        except Exception:
            pass

    def enable_start_button(self, enabled):
        """
        启用/禁用启动按钮

        Args:
            enabled: 是否启用
        """
        try:
            self.start_btn.setEnabled(enabled)
        except Exception:
            pass

    def enable_stop_button(self, enabled):
        """
        启用/禁用停止按钮

        Args:
            enabled: 是否启用
        """
        try:
            self.stop_btn.setEnabled(enabled)
        except Exception:
            pass

    def cleanup(self):
        """清理资源"""
        try:
            if self._manager:
                try:
                    self._manager.cleanup()
                except Exception as e:
                    logger.warning(f"[TrainingDock] 管理器清理异常: {e}")
            self._manager = None
        except Exception as e:
            logger.error(f"[TrainingDock] 清理资源异常: {e}")
