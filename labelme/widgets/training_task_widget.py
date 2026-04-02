# -*- coding: utf-8 -*-
"""
训练任务监控面板组件

提供训练任务的实时监控界面，包含：
- 服务器连接设置
- 任务列表显示
- 训练进度监控
- 日志输出显示

主要类：
    TrainingTaskWidget - 训练任务监控面板
"""

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from datetime import datetime
from typing import Optional, Dict, Any, List


class TrainingTaskWidget(QtWidgets.QWidget):
    """
    训练任务监控面板

    显示训练任务列表、状态和进度，提供任务管理操作界面。

    Attributes:
        _manager: TrainingClientManager 实例
        _current_task_id: 当前选中的任务 ID
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = None
        self._current_task_id = None
        self._tasks = {}  # task_id -> task_info
        self._setup_ui()

    def _setup_ui(self):
        """设置 UI 界面"""
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # ==================== 服务器连接区域 ====================
        connection_group = QtWidgets.QGroupBox("服务器连接")
        connection_layout = QtWidgets.QHBoxLayout()
        connection_layout.setSpacing(8)

        # 主机地址
        host_label = QtWidgets.QLabel("主机:")
        self.host_edit = QtWidgets.QLineEdit("127.0.0.1")
        self.host_edit.setFixedWidth(100)

        # 端口
        port_label = QtWidgets.QLabel("端口:")
        self.port_edit = QtWidgets.QSpinBox()
        self.port_edit.setRange(1, 65535)
        self.port_edit.setValue(8888)
        self.port_edit.setFixedWidth(80)

        # 连接按钮
        self.connect_btn = QtWidgets.QPushButton("连接")
        self.connect_btn.setFixedWidth(60)
        self.connect_btn.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        # 连接状态
        self.status_label = QtWidgets.QLabel("未连接")
        self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")

        connection_layout.addWidget(host_label)
        connection_layout.addWidget(self.host_edit)
        connection_layout.addWidget(port_label)
        connection_layout.addWidget(self.port_edit)
        connection_layout.addWidget(self.connect_btn)
        connection_layout.addWidget(self.status_label)
        connection_layout.addStretch()

        connection_group.setLayout(connection_layout)
        main_layout.addWidget(connection_group)

        # ==================== 任务列表区域 ====================
        task_group = QtWidgets.QGroupBox("训练任务列表")
        task_layout = QtWidgets.QVBoxLayout()

        # 任务表格
        self.task_table = QtWidgets.QTableWidget()
        self.task_table.setColumnCount(5)
        self.task_table.setHorizontalHeaderLabels(["任务 ID", "状态", "进度", "模型类型", "创建时间"])
        self.task_table.horizontalHeader().setStretchLastSection(True)
        self.task_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.task_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.task_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.setMinimumHeight(150)
        self.task_table.setMaximumHeight(200)
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

        task_layout.addWidget(self.task_table)

        # 操作按钮
        btn_layout = QtWidgets.QHBoxLayout()

        self.refresh_btn = QtWidgets.QPushButton("刷新列表")
        self.refresh_btn.setEnabled(False)

        self.delete_btn = QtWidgets.QPushButton("删除任务")
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("""
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

        self.start_btn = QtWidgets.QPushButton("启动训练")
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("""
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

        self.stop_btn = QtWidgets.QPushButton("停止训练")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)

        task_layout.addLayout(btn_layout)
        task_group.setLayout(task_layout)
        main_layout.addWidget(task_group)

        # ==================== 当前任务进度区域 ====================
        progress_group = QtWidgets.QGroupBox("当前任务进度")
        progress_layout = QtWidgets.QVBoxLayout()

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

        progress_layout.addLayout(info_layout)

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
        progress_layout.addWidget(self.progress_bar)

        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

        # ==================== 日志输出区域 ====================
        log_group = QtWidgets.QGroupBox("日志输出")
        log_layout = QtWidgets.QVBoxLayout()

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

        log_layout.addWidget(self.log_text)

        # 清空日志按钮
        clear_btn_layout = QtWidgets.QHBoxLayout()
        self.clear_log_btn = QtWidgets.QPushButton("清空日志")
        self.clear_log_btn.setFixedWidth(80)
        clear_btn_layout.addStretch()
        clear_btn_layout.addWidget(self.clear_log_btn)
        log_layout.addLayout(clear_btn_layout)

        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        self.setLayout(main_layout)

        # 连接按钮信号
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        self.start_btn.clicked.connect(self._on_start_clicked)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.clear_log_btn.clicked.connect(self._on_clear_log_clicked)

    def set_manager(self, manager):
        """
        设置训练客户端管理器

        Args:
            manager: TrainingClientManager 实例
        """
        self._manager = manager

        # 连接信号
        manager.connected.connect(self._on_connected)
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

    def _on_connect_clicked(self):
        """连接按钮点击"""
        try:
            if self._manager:
                host = self.host_edit.text()
                port = self.port_edit.value()
                self._manager.connect_server(host, port)
                self.connect_btn.setEnabled(False)
                self._log(f"正在连接服务器 {host}:{port}...")
        except Exception as e:
            self._log(f"连接按钮点击异常：{str(e)}", "error")

    def _on_connected(self, success: bool):
        """连接结果"""
        try:
            self.connect_btn.setEnabled(True)
            if success:
                self.status_label.setText("已连接")
                self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
                self.connect_btn.setText("断开")
                try:
                    self.connect_btn.clicked.disconnect()
                except TypeError:
                    pass  # 没有连接任何信号时忽略
                self.connect_btn.clicked.connect(self._on_disconnect_clicked)
                self.refresh_btn.setEnabled(True)
                self.host_edit.setEnabled(False)
                self.port_edit.setEnabled(False)
                # 自动刷新任务列表
                self._on_refresh_clicked()
            else:
                self.status_label.setText("连接失败")
                self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
        except Exception as e:
            self._log(f"连接结果处理异常：{str(e)}", "error")

    def _on_disconnect_clicked(self):
        """断开连接按钮点击"""
        try:
            if self._manager:
                self._manager.disconnect_server()
                self.status_label.setText("未连接")
                self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
                self.connect_btn.setText("连接")
                try:
                    self.connect_btn.clicked.disconnect()
                except TypeError:
                    pass
                self.connect_btn.clicked.connect(self._on_connect_clicked)
                self.refresh_btn.setEnabled(False)
                self.delete_btn.setEnabled(False)
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                self.host_edit.setEnabled(True)
                self.port_edit.setEnabled(True)
                self.task_table.setRowCount(0)
                self._tasks.clear()
        except Exception as e:
            self._log(f"断开连接异常：{str(e)}", "error")

    def _on_connection_error(self, error_msg: str):
        """连接错误"""
        try:
            self.connect_btn.setEnabled(True)
            self.status_label.setText("连接失败")
            self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
            self._log(f"连接错误：{error_msg}", "error")
        except Exception:
            pass

    def _on_refresh_clicked(self):
        """刷新列表按钮点击"""
        try:
            if self._manager:
                self._manager.list_tasks()
                self._log("正在刷新任务列表...")
        except Exception as e:
            self._log(f"刷新列表异常：{str(e)}", "error")

    def _on_task_list_updated(self, tasks: List[Dict]):
        """任务列表更新"""
        try:
            self.task_table.setRowCount(0)
            self._tasks.clear()

            for task in tasks:
                try:
                    task_id = task.get("task_id", "unknown")
                    if not task_id or task_id == "unknown":
                        continue

                    self._tasks[task_id] = task

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

                    # 进度
                    progress = task.get("progress", 0) * 100
                    progress_item = QtWidgets.QTableWidgetItem(f"{progress:.1f}%")
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

    def _on_task_list_failed(self, error_msg: str):
        """获取任务列表失败"""
        try:
            self._log(f"获取任务列表失败：{error_msg}", "error")
        except Exception:
            pass

    def _on_task_selected(self):
        """任务选择变化"""
        try:
            selected = self.task_table.selectedItems()
            if not selected:
                self._current_task_id = None
                self.delete_btn.setEnabled(False)
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                return

            row = selected[0].row()
            item = self.task_table.item(row, 0)
            if not item:
                self._current_task_id = None
                self.delete_btn.setEnabled(False)
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                return

            task_id = item.data(Qt.UserRole)
            if not task_id:
                self._current_task_id = None
                self.delete_btn.setEnabled(False)
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                return

            self._current_task_id = task_id
            self.delete_btn.setEnabled(True)

            # 根据任务状态启用/禁用按钮
            task = self._tasks.get(task_id, {})
            status = task.get("status", "unknown")

            if status == "running":
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(True)
            elif status in ["pending", "stopped", "failed"]:
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
            else:  # completed
                self.start_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)

            # 安全截取任务 ID 字符串
            display_id = task_id[:16] + "..." if len(task_id) > 16 else task_id
            self.current_task_label.setText(display_id)
            self.current_status_label.setText(status)
        except Exception as e:
            self._log(f"任务选择异常：{str(e)}", "error")
            self._current_task_id = None
            self.delete_btn.setEnabled(False)
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

    def _on_delete_clicked(self):
        """删除任务按钮点击"""
        try:
            if not self._current_task_id or not self._manager:
                return

            # 检查管理器是否已连接
            if not self._manager.is_connected():
                self._log("未连接到服务器", "error")
                return

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

    def _on_task_deleted(self, task_id: str):
        """任务删除成功"""
        try:
            if task_id:
                self._log(f"任务已删除：{task_id[:16]}...")
                self._on_refresh_clicked()
        except Exception:
            pass

    def _on_task_deletion_failed(self, task_id: str, error_msg: str):
        """任务删除失败"""
        try:
            self._log(f"删除任务失败：{error_msg}", "error")
        except Exception:
            pass

    def _on_start_clicked(self):
        """启动训练按钮点击"""
        try:
            if self._current_task_id and self._manager:
                if not self._manager.is_connected():
                    self._log("未连接到服务器", "error")
                    return
                self._manager.start_training(self._current_task_id)
        except Exception as e:
            self._log(f"启动训练异常：{str(e)}", "error")

    def _on_training_started(self, task_id: str):
        """训练启动成功"""
        try:
            if task_id:
                self._log(f"训练已启动：{task_id[:16]}...")
                self._on_refresh_clicked()
        except Exception:
            pass

    def _on_training_start_failed(self, task_id: str, error_msg: str):
        """训练启动失败"""
        try:
            self._log(f"启动训练失败：{error_msg}", "error")
        except Exception:
            pass

    def _on_stop_clicked(self):
        """停止训练按钮点击"""
        try:
            if self._current_task_id and self._manager:
                if not self._manager.is_connected():
                    self._log("未连接到服务器", "error")
                    return
                self._manager.stop_training(self._current_task_id)
        except Exception as e:
            self._log(f"停止训练异常：{str(e)}", "error")

    def _on_training_stopped(self, task_id: str):
        """训练停止成功"""
        try:
            if task_id:
                self._log(f"训练已停止：{task_id[:16]}...")
                self._on_refresh_clicked()
        except Exception:
            pass

    def _on_training_stop_failed(self, task_id: str, error_msg: str):
        """训练停止失败"""
        try:
            self._log(f"停止训练失败：{error_msg}", "error")
        except Exception:
            pass

    def _on_task_created(self, task_id: str):
        """任务创建成功"""
        try:
            if task_id:
                self._log(f"任务创建成功：{task_id[:16]}...")
                self._on_refresh_clicked()
        except Exception:
            pass

    def _on_task_creation_failed(self, error_msg: str):
        """任务创建失败"""
        try:
            self._log(f"创建任务失败：{error_msg}", "error")
        except Exception:
            pass

    def _on_progress_updated(self, task_id: str, progress_data: Dict):
        """进度更新"""
        try:
            if task_id != self._current_task_id:
                return

            progress_info = progress_data.get("progress", {})
            if not progress_info:
                return

            epoch = progress_info.get("epoch", 0)
            total_epochs = progress_info.get("total_epochs", 1)
            loss = progress_info.get("loss", 0)
            accuracy = progress_info.get("accuracy", 0)

            # 安全处理除以零
            if total_epochs and total_epochs > 0:
                progress_percent = int((epoch / total_epochs) * 100)
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
        except Exception:
            # 进度更新失败不影响主程序
            pass

    def _on_status_changed(self, task_id: str, status_data: Dict):
        """状态变化"""
        try:
            status = status_data.get("status", "unknown")
            
            if task_id == self._current_task_id:
                self.current_status_label.setText(status)

            # 更新任务列表中的状态
            if task_id in self._tasks:
                self._tasks[task_id]["status"] = status
                self._tasks[task_id]["progress"] = status_data.get("progress", 0)
                
                # 如果任务完成或失败，自动刷新任务列表以更新显示
                if status in ["completed", "failed", "stopped"]:
                    self._log(f"任务 {task_id[:8]}... 状态变为 {status}，刷新列表...")
                    self._on_refresh_clicked()
        except Exception:
            pass

    def _on_error(self, error_msg: str):
        """错误发生"""
        try:
            self._log(f"错误：{error_msg}", "error")
        except Exception:
            pass

    def _on_log_message(self, message: str):
        """日志消息"""
        try:
            self._log(message)
        except Exception:
            pass

    def _on_clear_log_clicked(self):
        """清空日志"""
        try:
            self.log_text.clear()
        except Exception:
            pass

    def _log(self, message: str, level: str = "info"):
        """
        添加日志

        Args:
            message: 日志消息
            level: 日志级别 (info, error, warning)
        """
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

    def get_current_task_id(self) -> Optional[str]:
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
