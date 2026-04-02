# -*- coding: utf-8 -*-
"""
模型部署 Dock 面板模块

提供完整的 SSH 模型部署 UI 界面，包括：
- 设备连接配置
- 设备类型选择
- 文件选择和传输
- 进度显示
- 设备列表管理
- 日志显示
- 一键部署
"""

import os
import re
from typing import Optional, List

from PyQt5 import QtCore, QtGui, QtWidgets

from .ssh_client import SSHClient, SSHConfig
from .device_manager import DeviceManager, DeviceInfo
from .log_handler import LogHandler, LogLevel, LogEntry
from .recent_device import RecentDeviceStorage, RecentDevice
from .deploy_worker import (
    ConnectionTestWorker,
    FileTransferWorker,
    DeployWorker,
    BatchDeployWorker,
)


class DeviceListWidget(QtWidgets.QWidget):
    """设备列表组件"""
    
    # 设备选择信号
    device_selected = QtCore.pyqtSignal(DeviceInfo)
    # 设备删除信号
    device_deleted = QtCore.pyqtSignal(str)  # 设备ID
    
    def __init__(self, device_manager: DeviceManager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self._setup_ui()
        self._load_devices()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 工具栏
        toolbar = QtWidgets.QHBoxLayout()
        
        self.add_btn = QtWidgets.QPushButton("添加")
        self.add_btn.setToolTip("添加新设备")
        
        self.edit_btn = QtWidgets.QPushButton("编辑")
        self.edit_btn.setToolTip("编辑选中设备")
        self.edit_btn.setEnabled(False)
        
        self.delete_btn = QtWidgets.QPushButton("删除")
        self.delete_btn.setToolTip("删除选中设备")
        self.delete_btn.setEnabled(False)
        
        self.refresh_btn = QtWidgets.QPushButton("刷新")
        self.refresh_btn.setToolTip("刷新设备列表")
        
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.refresh_btn)
        
        layout.addLayout(toolbar)
        
        # 设备列表
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["名称", "IP地址", "类型", "描述"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        
        layout.addWidget(self.table)
        
        # 连接信号
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.refresh_btn.clicked.connect(self._load_devices)
        self.delete_btn.clicked.connect(self._on_delete)
        self.table.doubleClicked.connect(self._on_double_click)
    
    def _load_devices(self):
        """加载设备列表"""
        devices = self.device_manager.get_all_devices()
        self.table.setRowCount(len(devices))
        
        for i, device in enumerate(devices):
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(device.name))
            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(device.host))
            self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(device.device_type))
            self.table.setItem(i, 3, QtWidgets.QTableWidgetItem(device.description))
            
            # 存储设备ID
            for col in range(4):
                item = self.table.item(i, col)
                item.setData(QtCore.Qt.UserRole, device.id)
        
        self.table.resizeColumnsToContents()
    
    def _on_selection_changed(self):
        """选择变化处理"""
        selected = self.table.selectedItems()
        has_selection = len(selected) > 0
        
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        
        if has_selection:
            device_id = selected[0].data(QtCore.Qt.UserRole)
            device = self.device_manager.get_device(device_id)
            if device:
                self.device_selected.emit(device)
    
    def _on_delete(self):
        """删除设备"""
        selected = self.table.selectedItems()
        if not selected:
            return
        
        device_id = selected[0].data(QtCore.Qt.UserRole)
        device = self.device_manager.get_device(device_id)
        
        reply = QtWidgets.QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除设备 '{device.name}' 吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            self.device_manager.delete_device(device_id)
            self.device_deleted.emit(device_id)
            self._load_devices()
    
    def _on_double_click(self):
        """双击编辑"""
        self.edit_btn.click()
    
    def get_selected_device(self) -> Optional[DeviceInfo]:
        """获取选中的设备"""
        selected = self.table.selectedItems()
        if not selected:
            return None
        
        device_id = selected[0].data(QtCore.Qt.UserRole)
        return self.device_manager.get_device(device_id)
    
    def refresh(self):
        """刷新列表"""
        self._load_devices()


class LogPanelWidget(QtWidgets.QWidget):
    """日志面板组件"""
    
    def __init__(self, log_handler: LogHandler, parent=None):
        super().__init__(parent)
        self.log_handler = log_handler
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 工具栏
        toolbar = QtWidgets.QHBoxLayout()
        
        self.clear_btn = QtWidgets.QPushButton("清除")
        self.clear_btn.setToolTip("清除所有日志")
        
        self.export_btn = QtWidgets.QPushButton("导出")
        self.export_btn.setToolTip("导出日志到文件")
        
        self.auto_scroll_cb = QtWidgets.QCheckBox("自动滚动")
        self.auto_scroll_cb.setChecked(True)
        
        toolbar.addWidget(self.clear_btn)
        toolbar.addWidget(self.export_btn)
        toolbar.addStretch()
        toolbar.addWidget(self.auto_scroll_cb)
        
        layout.addLayout(toolbar)
        
        # 日志显示区域
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QtWidgets.QTextEdit.WidgetWidth)
        # 禁用右键菜单（避免显示英文菜单）
        self.log_text.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        
        # 设置等宽字体
        font = QtGui.QFont("Consolas", 9)
        self.log_text.setFont(font)
        
        layout.addWidget(self.log_text)
    
    def _connect_signals(self):
        """连接信号"""
        self.log_handler.log_added.connect(self._on_log_added)
        self.log_handler.logs_cleared.connect(self._on_logs_cleared)
        self.clear_btn.clicked.connect(self.log_handler.clear_logs)
        self.export_btn.clicked.connect(self._on_export)
    
    def _on_log_added(self, entry: LogEntry):
        """日志添加处理"""
        color = self.log_handler.get_level_color(entry.level)
        
        # 构建 HTML 格式的日志
        time_str = entry.timestamp.strftime("%H:%M:%S")
        if entry.source:
            html = f'<span style="color: #666;">[{time_str}]</span> <span style="color: {color};">[{entry.level.value}] [{entry.source}]</span> {entry.message}'
        else:
            html = f'<span style="color: #666;">[{time_str}]</span> <span style="color: {color};">[{entry.level.value}]</span> {entry.message}'
        
        self.log_text.append(html)
        
        # 自动滚动
        if self.auto_scroll_cb.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def _on_logs_cleared(self):
        """日志清除处理"""
        self.log_text.clear()
    
    def _on_export(self):
        """导出日志"""
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "导出日志",
            "deploy_logs.txt",
            "文本文件 (*.txt);;所有文件 (*)",
        )
        
        if filepath:
            if self.log_handler.export_logs(filepath):
                QtWidgets.QMessageBox.information(
                    self,
                    "导出成功",
                    f"日志已导出到:\n{filepath}",
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self,
                    "导出失败",
                    "导出日志时发生错误",
                )
    
    def add_log(self, message: str, level: LogLevel = LogLevel.INFO, source: str = ""):
        """添加日志"""
        self.log_handler.add_log(message, level, source)


class DeployDockWidget(QtWidgets.QDockWidget):
    """
    模型部署 Dock 面板
    
    主 Dock 面板，整合所有功能组件。
    """
    
    def __init__(self, parent=None):
        super().__init__("模型部署", parent)
        self.setObjectName("DeployDock")
        
        # 初始化管理器
        self.device_manager = DeviceManager()
        self.log_handler = LogHandler()
        self.recent_storage = RecentDeviceStorage()
        
        # 工作线程
        self._connection_worker: Optional[ConnectionTestWorker] = None
        self._transfer_worker: Optional[FileTransferWorker] = None
        self._deploy_worker: Optional[DeployWorker] = None
        
        # 当前选中的文件
        self._current_file: Optional[str] = None
        
        # IP自动补全
        self._ip_completer: Optional[QtWidgets.QCompleter] = None
        
        self._setup_ui()
        self._connect_signals()
        self._load_recent_device()
        self._setup_ip_autocomplete()
    
    def _setup_ui(self):
        """设置 UI"""
        # 主容器
        container = QtWidgets.QWidget()
        self.setWidget(container)
        
        main_layout = QtWidgets.QVBoxLayout(container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 创建标签页
        self.tab_widget = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # ========== 部署标签页 ==========
        deploy_tab = QtWidgets.QWidget()
        deploy_layout = QtWidgets.QVBoxLayout(deploy_tab)
        deploy_layout.setContentsMargins(10, 10, 10, 10)
        
        # 连接配置组
        conn_group = QtWidgets.QGroupBox("连接配置")
        conn_layout = QtWidgets.QFormLayout(conn_group)
        
        # IP 地址
        self.ip_input = QtWidgets.QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        conn_layout.addRow("IP 地址:", self.ip_input)
        
        # 端口
        self.port_input = QtWidgets.QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(22)
        conn_layout.addRow("端口:", self.port_input)
        
        # 设备类型
        self.device_type_combo = QtWidgets.QComboBox()
        self.device_type_combo.addItems(self.device_manager.get_device_types())
        conn_layout.addRow("设备类型:", self.device_type_combo)
        
        # 用户名
        self.username_input = QtWidgets.QLineEdit("root")
        self.username_input.setReadOnly(True)
        conn_layout.addRow("用户名:", self.username_input)
        
        # 密码
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.password_input.setReadOnly(True)
        conn_layout.addRow("密码:", self.password_input)
        
        # 连接测试按钮
        self.test_btn = QtWidgets.QPushButton("连接测试")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        conn_layout.addRow("", self.test_btn)
        
        deploy_layout.addWidget(conn_group)
        
        # 文件选择组
        file_group = QtWidgets.QGroupBox("文件选择")
        file_layout = QtWidgets.QHBoxLayout(file_group)
        
        self.file_path_label = QtWidgets.QLabel("未选择文件")
        self.file_path_label.setStyleSheet("color: #666;")
        self.file_path_label.setWordWrap(True)
        
        self.select_file_btn = QtWidgets.QPushButton("选择文件")
        self.select_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        file_layout.addWidget(self.file_path_label, 1)
        file_layout.addWidget(self.select_file_btn)
        
        deploy_layout.addWidget(file_group)
        
        # 目标路径
        path_layout = QtWidgets.QHBoxLayout()
        path_layout.addWidget(QtWidgets.QLabel("目标路径:"))
        self.target_path_input = QtWidgets.QLineEdit("/mmcblk1p2")
        path_layout.addWidget(self.target_path_input)
        deploy_layout.addLayout(path_layout)
        
        # 进度条
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        deploy_layout.addWidget(self.progress_bar)
        
        # 操作按钮
        btn_layout = QtWidgets.QHBoxLayout()
        
        self.upload_btn = QtWidgets.QPushButton("上传文件")
        self.upload_btn.setEnabled(False)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 8px 20px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        
        self.deploy_btn = QtWidgets.QPushButton("一键部署")
        self.deploy_btn.setEnabled(False)
        self.deploy_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 20px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        
        self.pause_btn = QtWidgets.QPushButton("暂停")
        self.pause_btn.setEnabled(False)
        
        btn_layout.addWidget(self.upload_btn)
        btn_layout.addWidget(self.deploy_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addStretch()
        
        deploy_layout.addLayout(btn_layout)
        
        # 部署命令（可选）
        cmd_group = QtWidgets.QGroupBox("部署后命令（可选）")
        cmd_layout = QtWidgets.QVBoxLayout(cmd_group)
        
        self.cmd_text = QtWidgets.QTextEdit()
        self.cmd_text.setPlaceholderText("每行一个命令，例如:\nchmod +x /mmcblk1p2/deploy.sh\n/mmcblk1p2/deploy.sh")
        self.cmd_text.setMaximumHeight(80)
        # 禁用右键菜单（避免显示英文菜单）
        self.cmd_text.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        cmd_layout.addWidget(self.cmd_text)
        
        deploy_layout.addWidget(cmd_group)
        deploy_layout.addStretch()
        
        self.tab_widget.addTab(deploy_tab, "部署")
        
        # ========== 设备管理标签页 ==========
        self.device_list_widget = DeviceListWidget(self.device_manager)
        self.tab_widget.addTab(self.device_list_widget, "设备管理")
        
        # ========== 日志标签页 ==========
        self.log_panel = LogPanelWidget(self.log_handler)
        self.tab_widget.addTab(self.log_panel, "日志")
        
        # ========== 命令执行标签页 ==========
        self._setup_command_tab()
    
    def _setup_command_tab(self):
        """设置命令执行标签页 - 微信风格聊天界面"""
        cmd_tab = QtWidgets.QWidget()
        cmd_layout = QtWidgets.QVBoxLayout(cmd_tab)
        cmd_layout.setContentsMargins(0, 0, 0, 0)
        cmd_layout.setSpacing(0)
        
        # 顶部信息栏（显示当前连接的设备）
        self.cmd_info_bar = QtWidgets.QLabel("未连接设备")
        self.cmd_info_bar.setStyleSheet("""
            QLabel {
                background-color: #ededed;
                color: #333;
                padding: 10px 15px;
                border-bottom: 1px solid #d6d6d6;
                font-size: 13px;
            }
        """)
        self.cmd_info_bar.setAlignment(QtCore.Qt.AlignCenter)
        cmd_layout.addWidget(self.cmd_info_bar)
        
        # 命令历史显示区域（聊天框）
        self.cmd_history = QtWidgets.QTextEdit()
        self.cmd_history.setReadOnly(True)
        self.cmd_history.setLineWrapMode(QtWidgets.QTextEdit.WidgetWidth)
        # 禁用右键菜单（避免显示英文菜单）
        self.cmd_history.setContextMenuPolicy(QtCore.Qt.NoContextMenu)
        
        # 设置微信风格背景色
        self.cmd_history.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: none;
                padding: 10px;
            }
        """)
        
        cmd_layout.addWidget(self.cmd_history, 1)
        
        # 底部输入区域
        input_container = QtWidgets.QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background-color: #f7f7f7;
                border-top: 1px solid #e0e0e0;
            }
        """)
        input_layout = QtWidgets.QHBoxLayout(input_container)
        input_layout.setContentsMargins(15, 10, 15, 10)
        input_layout.setSpacing(10)
        
        # 命令输入框 - 微信风格
        self.cmd_input = QtWidgets.QLineEdit()
        self.cmd_input.setPlaceholderText("输入命令...")
        self.cmd_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                padding: 8px 12px;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                min-height: 20px;
            }
            QLineEdit:focus {
                outline: none;
            }
        """)
        self.cmd_input.returnPressed.connect(self._on_send_command)
        
        # 发送按钮 - 微信绿色风格
        self.send_btn = QtWidgets.QPushButton("发送")
        self.send_btn.setFixedWidth(60)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #07c160;
                color: white;
                padding: 8px 12px;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #06ad56;
            }
            QPushButton:pressed {
                background-color: #059a4c;
            }
            QPushButton:disabled {
                background-color: #c9c9c9;
                color: #888;
            }
        """)
        self.send_btn.clicked.connect(self._on_send_command)
        
        input_layout.addWidget(self.cmd_input, 1)
        input_layout.addWidget(self.send_btn)
        
        cmd_layout.addWidget(input_container)
        
        self.tab_widget.addTab(cmd_tab, "命令执行")
        
        # 添加欢迎信息
        self._add_command_history("欢迎使用命令执行功能", "system")
        self._add_command_history("请先连接设备，然后输入命令执行", "system")
    
    def _connect_signals(self):
        """连接信号"""
        # 设备类型变化
        self.device_type_combo.currentTextChanged.connect(self._on_device_type_changed)
        
        # 连接测试
        self.test_btn.clicked.connect(self._on_test_connection)
        
        # 文件选择
        self.select_file_btn.clicked.connect(self._on_select_file)
        
        # 上传和部署
        self.upload_btn.clicked.connect(self._on_upload)
        self.deploy_btn.clicked.connect(self._on_deploy)
        self.pause_btn.clicked.connect(self._on_pause)
        
        # 设备列表
        self.device_list_widget.device_selected.connect(self._on_device_selected)
        self.device_list_widget.device_deleted.connect(self._on_device_deleted)
        self.device_list_widget.add_btn.clicked.connect(self._on_add_device)
        self.device_list_widget.edit_btn.clicked.connect(self._on_edit_device)
        
        # 初始化设备类型凭据
        self._on_device_type_changed(self.device_type_combo.currentText())
    
    def _on_device_type_changed(self, device_type: str):
        """设备类型变化处理"""
        username, password = self.device_manager.get_device_credentials(device_type)
        self.username_input.setText(username)
        self.password_input.setText(password)
    
    def _validate_ip_address(self, ip: str) -> bool:
        """验证 IP 地址是否有效"""
        # IPv4 地址格式验证
        ipv4_pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        if re.match(ipv4_pattern, ip):
            return True
        
        # 主机名验证（允许字母、数字、连字符和点）
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?))*$'
        if re.match(hostname_pattern, ip):
            return True
        
        return False
    
    def _on_test_connection(self):
        """测试连接"""
        host = self.ip_input.text().strip()
        if not host:
            QtWidgets.QMessageBox.warning(self, "输入错误", "请输入 IP 地址")
            return
        
        # 验证 IP 地址格式
        if not self._validate_ip_address(host):
            QtWidgets.QMessageBox.warning(self, "IP地址无效", f"IP地址 '{host}' 格式无效，请输入有效的IPv4地址或主机名")
            return
        
        # 直接从当前设备类型获取凭据，确保密码正确
        device_type = self.device_type_combo.currentText()
        username, password = self.device_manager.get_device_credentials(device_type)
        
        # 更新输入框显示
        self.username_input.setText(username)
        self.password_input.setText(password)
        
        config = SSHConfig(
            host=host,
            port=self.port_input.value(),
            username=username,
            password=password,
            timeout=10,
        )
        
        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中...")
        self.log_handler.info(f"正在测试连接到 {host}...")
        
        # 创建工作线程
        self._connection_worker = ConnectionTestWorker(config)
        self._connection_worker.connection_tested.connect(self._on_connection_tested)
        self._connection_worker.start()
    
    def _on_connection_tested(self, success: bool, message: str):
        """连接测试结果处理"""
        self.test_btn.setEnabled(True)
        self.test_btn.setText("连接测试")
        
        if success:
            self.test_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
            """)
            self.log_handler.success(message)
            QtWidgets.QMessageBox.information(self, "连接成功", "SSH连接测试成功！")
            
            # 连接成功，保存设备信息
            self._save_connection_success()
            
            # 更新命令执行页面的信息栏
            self._update_cmd_info_bar()
        else:
            self.test_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
            """)
            self.log_handler.error(message)
            QtWidgets.QMessageBox.critical(self, "连接失败", f"SSH连接测试失败：\n{message}")
        
        # 3秒后恢复按钮样式
        QtCore.QTimer.singleShot(3000, self._reset_test_button)
    
    def _reset_test_button(self):
        """重置测试按钮样式"""
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
    
    def _on_select_file(self):
        """选择文件"""
        filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "选择要部署的文件",
            "",
            "所有文件 (*);;模型文件 (*.pt *.pth *.onnx);;压缩文件 (*.zip *.tar *.gz)",
        )
        
        if filepath:
            self._current_file = filepath
            self.file_path_label.setText(os.path.basename(filepath))
            self.file_path_label.setStyleSheet("color: #000;")
            self.upload_btn.setEnabled(True)
            self.deploy_btn.setEnabled(True)
            self.log_handler.info(f"已选择文件: {filepath}")
            
            # 保存文件路径到最近设备记录
            self._save_last_file_path(filepath)
    
    def _on_upload(self):
        """上传文件"""
        if not self._current_file:
            return
        
        host = self.ip_input.text().strip()
        if not host:
            QtWidgets.QMessageBox.warning(self, "输入错误", "请输入 IP 地址")
            return
        
        # 直接从当前设备类型获取凭据，确保密码正确
        device_type = self.device_type_combo.currentText()
        username, password = self.device_manager.get_device_credentials(device_type)
        
        config = SSHConfig(
            host=host,
            port=self.port_input.value(),
            username=username,
            password=password,
            timeout=10,
        )
        
        filename = os.path.basename(self._current_file)
        remote_path = f"{self.target_path_input.text()}/{filename}"
        
        self._transfer_worker = FileTransferWorker(
            config,
            self._current_file,
            remote_path,
            resume=True,
        )
        
        self._transfer_worker.progress_updated.connect(self._on_transfer_progress)
        self._transfer_worker.transfer_status.connect(self._on_transfer_status)
        self._transfer_worker.transfer_finished.connect(self._on_transfer_finished)
        
        self.upload_btn.setEnabled(False)
        self.deploy_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        
        self._transfer_worker.start()
    
    def _on_transfer_progress(self, transferred: int, total: int):
        """传输进度更新"""
        if total > 0:
            progress = int((transferred / total) * 100)
            self.progress_bar.setValue(progress)
            
            # 计算速度
            transferred_mb = transferred / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self.progress_bar.setFormat(f"{progress}% ({transferred_mb:.1f}/{total_mb:.1f} MB)")
    
    def _on_transfer_status(self, status: str):
        """传输状态更新"""
        self.log_handler.info(status)
    
    def _on_transfer_finished(self, success: bool, message: str):
        """传输完成处理"""
        self.upload_btn.setEnabled(True)
        self.deploy_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        
        if success:
            self.log_handler.success(message)
            self.progress_bar.setValue(100)
            QtWidgets.QMessageBox.information(self, "上传成功", f"文件上传成功！\n{message}")
        else:
            self.log_handler.error(message)
            QtWidgets.QMessageBox.critical(self, "上传失败", f"文件上传失败：\n{message}")
        
        self._transfer_worker = None
    
    def _on_deploy(self):
        """一键部署"""
        if not self._current_file:
            return
        
        host = self.ip_input.text().strip()
        if not host:
            QtWidgets.QMessageBox.warning(self, "输入错误", "请输入 IP 地址")
            return
        
        # 直接从当前设备类型获取凭据，确保密码正确
        device_type = self.device_type_combo.currentText()
        username, password = self.device_manager.get_device_credentials(device_type)
        
        # 创建设备信息
        device = DeviceInfo(
            id="temp",
            name="临时设备",
            host=host,
            port=self.port_input.value(),
            device_type=device_type,
            username=username,
            password=password,
            target_path=self.target_path_input.text(),
        )
        
        # 解析部署命令
        commands = []
        cmd_text = self.cmd_text.toPlainText().strip()
        if cmd_text:
            commands = [cmd.strip() for cmd in cmd_text.split('\n') if cmd.strip()]
        
        self._deploy_worker = DeployWorker(
            device,
            self._current_file,
            self.target_path_input.text(),
            commands,
        )
        
        self._deploy_worker.deploy_step.connect(self._on_deploy_step)
        self._deploy_worker.deploy_progress.connect(self._on_deploy_progress)
        self._deploy_worker.deploy_log.connect(self._on_deploy_log)
        self._deploy_worker.deploy_finished.connect(self._on_deploy_finished)
        self._deploy_worker.file_progress.connect(self._on_transfer_progress)
        
        self.upload_btn.setEnabled(False)
        self.deploy_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        
        self.log_handler.info("开始一键部署...")
        self._deploy_worker.start()
    
    def _on_deploy_step(self, step: str):
        """部署步骤更新"""
        self.log_handler.info(f"当前步骤: {step}")
    
    def _on_deploy_progress(self, progress: int):
        """部署进度更新"""
        self.progress_bar.setValue(progress)
    
    def _on_deploy_log(self, level: str, message: str):
        """部署日志"""
        level_map = {
            "DEBUG": LogLevel.DEBUG,
            "INFO": LogLevel.INFO,
            "WARNING": LogLevel.WARNING,
            "ERROR": LogLevel.ERROR,
            "SUCCESS": LogLevel.SUCCESS,
        }
        log_level = level_map.get(level, LogLevel.INFO)
        self.log_handler.add_log(message, log_level)
    
    def _on_deploy_finished(self, success: bool, message: str):
        """部署完成处理"""
        self.upload_btn.setEnabled(True)
        self.deploy_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        
        if success:
            self.log_handler.success(message)
        else:
            self.log_handler.error(message)
        
        self._deploy_worker = None
    
    def _on_pause(self):
        """暂停/恢复"""
        if self._transfer_worker and self._transfer_worker.isRunning():
            if self._transfer_worker.is_paused():
                self._transfer_worker.resume_transfer()
                self.pause_btn.setText("暂停")
            else:
                self._transfer_worker.pause()
                self.pause_btn.setText("恢复")
    
    def _on_device_selected(self, device: DeviceInfo):
        """设备选择处理"""
        self.ip_input.setText(device.host)
        self.port_input.setValue(device.port)
        self.device_type_combo.setCurrentText(device.device_type)
        self.username_input.setText(device.username)
        self.password_input.setText(device.password)
        self.target_path_input.setText(device.target_path)
        
        self.log_handler.info(f"已选择设备: {device.name} ({device.host})")
    
    def _on_device_deleted(self, device_id: str):
        """设备删除处理"""
        self.log_handler.info(f"设备已删除: {device_id}")
    
    def _on_add_device(self):
        """添加设备"""
        dialog = DeviceDialog(self.device_manager, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.device_list_widget.refresh()
            self.log_handler.success("设备添加成功")
    
    def _on_edit_device(self):
        """编辑设备"""
        device = self.device_list_widget.get_selected_device()
        if not device:
            return
        
        dialog = DeviceDialog(self.device_manager, device, parent=self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.device_list_widget.refresh()
            self.log_handler.success("设备更新成功")
    
    def _load_recent_device(self):
        """加载最近连接的设备"""
        recent = self.recent_storage.load()
        if recent:
            self.ip_input.setText(recent.host)
            self.port_input.setValue(recent.port)
            self.device_type_combo.setCurrentText(recent.device_type)
            self.username_input.setText(recent.username)
            self.password_input.setText(recent.password)
            self.target_path_input.setText(recent.target_path)
            self.log_handler.info(f"已加载最近连接的设备: {recent.device_type}_{recent.host}")
            
            # 加载最后选择的文件
            if recent.last_file_path and os.path.exists(recent.last_file_path):
                self._current_file = recent.last_file_path
                self.file_path_label.setText(os.path.basename(recent.last_file_path))
                self.file_path_label.setStyleSheet("color: #000;")
                self.upload_btn.setEnabled(True)
                self.deploy_btn.setEnabled(True)
                self.log_handler.info(f"已加载上次选择的文件: {recent.last_file_path}")
    
    def _setup_ip_autocomplete(self):
        """设置IP地址自动补全"""
        ips = self.device_manager.get_all_device_ips()
        if ips:
            self._ip_completer = QtWidgets.QCompleter(ips, self)
            self._ip_completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
            self._ip_completer.setFilterMode(QtCore.Qt.MatchContains)
            self._ip_completer.activated.connect(self._on_ip_autocomplete_selected)
            self.ip_input.setCompleter(self._ip_completer)
    
    def _on_ip_autocomplete_selected(self, ip: str):
        """IP自动补全选中时处理"""
        device = self.device_manager.get_device_by_host(ip)
        if device:
            self.device_type_combo.setCurrentText(device.device_type)
            self.username_input.setText(device.username)
            self.password_input.setText(device.password)
            self.target_path_input.setText(device.target_path)
            self.log_handler.info(f"已选择设备: {device.name}")
    
    def _refresh_ip_autocomplete(self):
        """刷新IP自动补全列表"""
        ips = self.device_manager.get_all_device_ips()
        if self._ip_completer:
            model = QtCore.QStringListModel(ips, self)
            self._ip_completer.setModel(model)
    
    def _save_connection_success(self):
        """保存连接成功的设备信息"""
        host = self.ip_input.text().strip()
        device_type = self.device_type_combo.currentText()
        port = self.port_input.value()
        username = self.username_input.text()
        password = self.password_input.text()
        target_path = self.target_path_input.text()
        last_file_path = self._current_file if self._current_file else ""
        
        # 保存到最近连接设备
        recent_device = RecentDevice(
            host=host,
            port=port,
            device_type=device_type,
            username=username,
            password=password,
            target_path=target_path,
            last_file_path=last_file_path,
        )
        self.recent_storage.save(recent_device)
        
        # 更新或创建设备到管理列表
        self.device_manager.update_or_create_device(
            host=host,
            device_type=device_type,
            port=port,
            username=username,
            password=password,
            target_path=target_path,
        )
        
        # 刷新设备列表和IP自动补全
        self.device_list_widget.refresh()
        self._refresh_ip_autocomplete()
        
        self.log_handler.success(f"设备已保存: {device_type}_{host}")
    
    def _save_last_file_path(self, filepath: str):
        """保存最后选择的文件路径"""
        recent = self.recent_storage.load()
        if recent:
            # 更新文件路径
            recent.last_file_path = filepath
            self.recent_storage.save(recent)
        else:
            # 没有最近设备记录，创建一个空设备记录只保存文件路径
            empty_device = RecentDevice(
                host="",
                port=22,
                device_type="ERV",
                username="root",
                password="",
                target_path="/mmcblk1p2",
                last_file_path=filepath,
            )
            self.recent_storage.save(empty_device)
    
    def _update_cmd_info_bar(self):
        """更新命令执行页面的信息栏"""
        host = self.ip_input.text().strip()
        device_type = self.device_type_combo.currentText()
        if host:
            self.cmd_info_bar.setText(f"已连接: {device_type} ({host})")
            self.cmd_info_bar.setStyleSheet("""
                QLabel {
                    background-color: #ededed;
                    color: #07c160;
                    padding: 10px 15px;
                    border-bottom: 1px solid #d6d6d6;
                    font-size: 13px;
                    font-weight: bold;
                }
            """)
        else:
            self.cmd_info_bar.setText("未连接设备")
            self.cmd_info_bar.setStyleSheet("""
                QLabel {
                    background-color: #ededed;
                    color: #999;
                    padding: 10px 15px;
                    border-bottom: 1px solid #d6d6d6;
                    font-size: 13px;
                }
            """)
    
    def _add_command_history(self, text: str, msg_type: str = "system"):
        """
        添加命令历史记录 - 微信风格气泡
        
        Args:
            text: 显示文本
            msg_type: 消息类型 (command/result/system)
        """
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%H:%M")
        
        if msg_type == "command":
            # 用户发送的命令 - 右对齐，绿色气泡（微信发送消息风格）
            html = f'''
            <div style="margin: 8px 0; text-align: right; overflow: hidden;">
                <div style="display: inline-block; max-width: 75%; text-align: left;">
                    <div style="font-size: 11px; color: #999; margin-bottom: 2px; text-align: right;">{timestamp}</div>
                    <div style="background-color: #95ec69; color: #000; padding: 8px 12px; border-radius: 4px; 
                                word-wrap: break-word; font-size: 13px; line-height: 1.4;
                                box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                        {text}
                    </div>
                </div>
            </div>
            '''
        elif msg_type == "result":
            # 命令返回结果 - 左对齐，白色气泡（微信接收消息风格）
            # 转义HTML特殊字符
            escaped_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            # 处理空行和多余空格，优化显示
            lines = escaped_text.split('\n')
            # 过滤掉完全空的行，但保留有意义的空行（用于分隔）
            filtered_lines = []
            prev_empty = False
            for line in lines:
                stripped = line.rstrip()
                if stripped:
                    filtered_lines.append(stripped)
                    prev_empty = False
                elif not prev_empty:
                    # 只保留一个空行
                    filtered_lines.append('')
                    prev_empty = True
            # 限制最大行数，避免过长输出
            if len(filtered_lines) > 50:
                filtered_lines = filtered_lines[:50]
                filtered_lines.append('... (输出过长，已截断)')
            escaped_text = '\n'.join(filtered_lines)
            
            html = f'''
            <div style="margin: 8px 0; text-align: left; overflow: hidden;">
                <div style="display: inline-block; max-width: 90%; text-align: left;">
                    <div style="font-size: 11px; color: #999; margin-bottom: 2px;">{timestamp} 服务器</div>
                    <div style="background-color: #ffffff; color: #333; padding: 10px 14px; border-radius: 4px; 
                                word-wrap: break-word; font-size: 13px; line-height: 1.5;
                                box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                                font-family: 'Segoe UI', 'Microsoft YaHei', Consolas, monospace; 
                                white-space: pre-wrap; max-height: 400px; overflow-y: auto;">
                        {escaped_text}
                    </div>
                </div>
            </div>
            '''
        else:
            # 系统消息 - 居中，灰色小字
            html = f'''
            <div style="margin: 10px 0; text-align: center;">
                <span style="background-color: #dadada; color: #fff; font-size: 11px; padding: 3px 8px; border-radius: 3px;">
                    {text}
                </span>
            </div>
            '''
        
        self.cmd_history.append(html)
        
        # 滚动到底部
        scrollbar = self.cmd_history.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _on_send_command(self):
        """发送命令"""
        command = self.cmd_input.text().strip()
        if not command:
            return
        
        # 显示发送的命令
        self._add_command_history(command, "command")
        
        # 清空输入框
        self.cmd_input.clear()
        
        # 禁用发送按钮
        self.send_btn.setEnabled(False)
        self.send_btn.setText("执行中...")
        
        # 获取连接信息
        host = self.ip_input.text().strip()
        if not host:
            self._add_command_history("错误：请先输入IP地址并连接设备", "result")
            self.send_btn.setEnabled(True)
            self.send_btn.setText("发送")
            return
        
        # 在后台线程执行命令
        QtCore.QTimer.singleShot(100, lambda: self._execute_remote_command(host, command))
    
    def _execute_remote_command(self, host: str, command: str):
        """
        在后台执行远程命令
        
        Args:
            host: 主机地址
            command: 要执行的命令
        """
        try:
            # 直接从当前设备类型获取凭据
            device_type = self.device_type_combo.currentText()
            username, password = self.device_manager.get_device_credentials(device_type)
            
            # 创建临时SSH客户端
            from .ssh_client import SSHClient, SSHConfig
            config = SSHConfig(
                host=host,
                port=self.port_input.value(),
                username=username,
                password=password,
                timeout=30,
            )
            
            client = SSHClient(config)
            
            # 连接并执行命令
            if client.connect(require_sftp=False):
                try:
                    success, stdout, stderr = client.execute_command(command, timeout=60)
                    
                    # 显示结果
                    if success:
                        if stdout:
                            self._add_command_history(stdout, "result")
                        else:
                            self._add_command_history("(命令执行成功，无输出)", "result")
                    else:
                        result = "命令执行失败"
                        if stderr:
                            result += f":\n{stderr}"
                        self._add_command_history(result, "result")
                        
                finally:
                    client.disconnect()
            else:
                self._add_command_history("错误：无法连接到设备，请先进行连接测试", "result")
                
        except Exception as e:
            self._add_command_history(f"执行异常: {str(e)}", "result")
        
        finally:
            # 恢复发送按钮
            self.send_btn.setEnabled(True)
            self.send_btn.setText("发送")


class DeviceDialog(QtWidgets.QDialog):
    """设备编辑对话框"""
    
    def __init__(self, device_manager: DeviceManager, device: Optional[DeviceInfo] = None, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.device = device
        self._setup_ui()
        
        if device:
            self.setWindowTitle("编辑设备")
            self._load_device(device)
        else:
            self.setWindowTitle("添加设备")
    
    def _setup_ui(self):
        """设置 UI"""
        self.setMinimumWidth(350)
        
        layout = QtWidgets.QFormLayout(self)
        
        # 名称
        self.name_input = QtWidgets.QLineEdit()
        layout.addRow("设备名称:", self.name_input)
        
        # IP 地址
        self.host_input = QtWidgets.QLineEdit()
        self.host_input.setPlaceholderText("192.168.1.100")
        layout.addRow("IP 地址:", self.host_input)
        
        # 端口
        self.port_input = QtWidgets.QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(22)
        layout.addRow("端口:", self.port_input)
        
        # 设备类型
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(self.device_manager.get_device_types())
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        layout.addRow("设备类型:", self.type_combo)
        
        # 用户名
        self.username_input = QtWidgets.QLineEdit("root")
        layout.addRow("用户名:", self.username_input)
        
        # 密码
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addRow("密码:", self.password_input)
        
        # 目标路径
        self.path_input = QtWidgets.QLineEdit("/mmcblk1p2")
        layout.addRow("目标路径:", self.path_input)
        
        # 描述
        self.desc_input = QtWidgets.QLineEdit()
        layout.addRow("描述:", self.desc_input)
        
        # 按钮
        btn_layout = QtWidgets.QHBoxLayout()
        self.ok_btn = QtWidgets.QPushButton("确定")
        self.cancel_btn = QtWidgets.QPushButton("取消")
        
        self.ok_btn.clicked.connect(self._on_ok)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addRow("", btn_layout)
        
        # 初始化凭据
        self._on_type_changed(self.type_combo.currentText())
    
    def _load_device(self, device: DeviceInfo):
        """加载设备信息"""
        self.name_input.setText(device.name)
        self.host_input.setText(device.host)
        self.port_input.setValue(device.port)
        self.type_combo.setCurrentText(device.device_type)
        self.username_input.setText(device.username)
        self.password_input.setText(device.password)
        self.path_input.setText(device.target_path)
        self.desc_input.setText(device.description)
    
    def _on_type_changed(self, device_type: str):
        """设备类型变化"""
        username, password = self.device_manager.get_device_credentials(device_type)
        self.username_input.setText(username)
        self.password_input.setText(password)
    
    def _on_ok(self):
        """确定按钮"""
        name = self.name_input.text().strip()
        host = self.host_input.text().strip()
        
        if not name:
            QtWidgets.QMessageBox.warning(self, "验证错误", "请输入设备名称")
            return
        
        if not host:
            QtWidgets.QMessageBox.warning(self, "验证错误", "请输入 IP 地址")
            return
        
        if self.device:
            # 更新现有设备
            self.device_manager.update_device(
                self.device.id,
                name=name,
                host=host,
                port=self.port_input.value(),
                device_type=self.type_combo.currentText(),
                username=self.username_input.text(),
                password=self.password_input.text(),
                target_path=self.path_input.text(),
                description=self.desc_input.text(),
            )
        else:
            # 创建新设备
            self.device_manager.create_device(
                name=name,
                host=host,
                device_type=self.type_combo.currentText(),
                port=self.port_input.value(),
                description=self.desc_input.text(),
            )
            # 更新凭据
            device = self.device_manager.get_device_by_host(host)
            if device:
                self.device_manager.update_device(
                    device.id,
                    username=self.username_input.text(),
                    password=self.password_input.text(),
                    target_path=self.path_input.text(),
                )
        
        self.accept()