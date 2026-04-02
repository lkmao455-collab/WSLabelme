# -*- coding: utf-8 -*-
"""
SSH 模型部署模块

提供通过 SSH 向远端 Linux 设备传输模型文件的功能，
支持多设备管理、自动部署、断点续传和 MD5 完整性校验。
"""

import logging

# 配置日志输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from .ssh_client import SSHClient, SSHConfig
from .device_manager import DeviceManager, DeviceInfo
from .recent_device import RecentDeviceStorage, RecentDevice
from .deploy_worker import (
    DeployWorker,
    ConnectionTestWorker,
    FileTransferWorker,
    BatchDeployWorker,
)
from .log_handler import LogHandler, LogLevel
from .deploy_dock import DeployDockWidget

__version__ = "1.1.0"
__all__ = [
    # SSH 客户端
    'SSHClient',
    'SSHConfig',
    # 设备管理
    'DeviceManager',
    'DeviceInfo',
    # 最近连接设备
    'RecentDeviceStorage',
    'RecentDevice',
    # 部署工作线程
    'DeployWorker',
    'ConnectionTestWorker',
    'FileTransferWorker',
    'BatchDeployWorker',
    # 日志处理
    'LogHandler',
    'LogLevel',
    # UI 组件
    'DeployDockWidget',
]
