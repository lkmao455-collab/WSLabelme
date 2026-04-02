# -*- coding: utf-8 -*-
"""
部署工作线程模块

提供多线程的 SSH 连接测试、文件传输、一键部署功能。
使用 PyQt5 的 QThread 和信号机制实现线程安全。
"""

import logging
import os
import time
from typing import Optional, List, Callable, Tuple

from PyQt5 import QtCore

from .ssh_client import SSHClient, SSHConfig
from .device_manager import DeviceInfo
from .log_handler import LogHandler, LogLevel


class ConnectionTestWorker(QtCore.QThread):
    """
    连接测试工作线程
    
    在独立线程中测试 SSH 连接，避免阻塞 UI。
    """
    
    # 连接测试结果信号
    connection_tested = QtCore.pyqtSignal(bool, str)  # (成功, 消息)
    
    def __init__(self, config: SSHConfig, parent=None):
        """
        初始化连接测试线程
        
        Args:
            config: SSH 配置
            parent: 父对象
        """
        super().__init__(parent)
        self.config = config
        self._is_running = False
    
    def run(self):
        """执行连接测试"""
        self._is_running = True
        logger = logging.getLogger(__name__)
        
        logger.info(f"[ConnectionTestWorker] 开始连接测试线程")
        logger.info(f"[ConnectionTestWorker] 目标: {self.config.host}:{self.config.port}")
        logger.info(f"[ConnectionTestWorker] 用户名: {self.config.username}")
        logger.info(f"[ConnectionTestWorker] 密码: {self.config.password}")
        logger.info(f"[ConnectionTestWorker] 超时设置: {self.config.timeout}秒")
        
        try:
            logger.info(f"[ConnectionTestWorker] 创建SSHClient实例...")
            client = SSHClient(self.config)
            
            logger.info(f"[ConnectionTestWorker] 调用test_connection()...")
            success, message = client.test_connection()
            
            logger.info(f"[ConnectionTestWorker] 测试结果: success={success}, message={message}")
            self.connection_tested.emit(success, message)
        except Exception as e:
            logger.error(f"[ConnectionTestWorker] 测试异常: {type(e).__name__}: {str(e)}")
            self.connection_tested.emit(False, f"测试失败: {str(e)}")
        finally:
            logger.info(f"[ConnectionTestWorker] 连接测试线程结束")
            self._is_running = False
    
    def stop(self):
        """停止测试"""
        self._is_running = False
        self.wait(1000)


class FileTransferWorker(QtCore.QThread):
    """
    文件传输工作线程
    
    在独立线程中执行文件上传，支持断点续传、MD5校验和自动重传。
    """
    
    # 传输进度信号
    progress_updated = QtCore.pyqtSignal(int, int)  # (已传输, 总大小)
    # 传输状态信号
    transfer_status = QtCore.pyqtSignal(str)  # 状态消息
    # 传输完成信号
    transfer_finished = QtCore.pyqtSignal(bool, str)  # (成功, 消息)
    # 传输暂停信号
    transfer_paused = QtCore.pyqtSignal()
    # 传输恢复信号
    transfer_resumed = QtCore.pyqtSignal()
    # 日志信号
    log_message = QtCore.pyqtSignal(str, str)  # (级别, 消息)
    # MD5校验进度信号
    md5_verification_status = QtCore.pyqtSignal(str)  # 校验状态消息
    
    def __init__(
        self,
        config: SSHConfig,
        local_path: str,
        remote_path: str,
        resume: bool = True,
        enable_md5_verify: bool = True,
        max_retries: int = 3,
        parent=None,
    ):
        """
        初始化文件传输线程
        
        Args:
            config: SSH 配置
            local_path: 本地文件路径
            remote_path: 远程文件路径
            resume: 是否启用断点续传
            enable_md5_verify: 是否启用 MD5 校验
            max_retries: 最大重试次数
            parent: 父对象
        """
        super().__init__(parent)
        self.config = config
        self.local_path = local_path
        self.remote_path = remote_path
        self.resume = resume
        self.enable_md5_verify = enable_md5_verify
        self.max_retries = max_retries
        
        self._is_running = False
        self._is_paused = False
        self._client: Optional[SSHClient] = None
        self._transferred = 0
        self._total_size = 0
        
        # MD5 校验相关
        self._local_md5: Optional[str] = None
        self._remote_md5: Optional[str] = None
        self._retry_count = 0
    
    def run(self):
        """执行文件传输"""
        self._is_running = True
        
        try:
            # 检查本地文件
            if not os.path.exists(self.local_path):
                self.transfer_finished.emit(False, f"本地文件不存在: {self.local_path}")
                return
            
            self._total_size = os.path.getsize(self.local_path)
            filename = os.path.basename(self.local_path)
            
            # 建立连接
            self.transfer_status.emit("正在连接服务器...")
            self._client = SSHClient(self.config)
            
            if not self._client.connect():
                self.transfer_finished.emit(False, "连接失败")
                return
            
            self.transfer_status.emit("连接成功")
            self.log_message.emit("INFO", f"SSH 连接成功: {self.config.host}")
            
            # 根据是否启用 MD5 校验选择传输方式
            if self.enable_md5_verify:
                self._run_with_md5_verification(filename)
            else:
                self._run_without_verification(filename)
                
        except Exception as e:
            self.log_message.emit("ERROR", f"传输异常: {str(e)}")
            self.transfer_finished.emit(False, f"传输错误: {str(e)}")
        finally:
            if self._client:
                self._client.disconnect()
            self._is_running = False
    
    def _run_with_md5_verification(self, filename: str):
        """
        执行带 MD5 校验的文件传输
        
        Args:
            filename: 文件名
        """
        # 使用带校验的上传方法
        success, message = self._client.upload_file_with_verification(
            local_path=self.local_path,
            remote_path=self.remote_path,
            progress_callback=self._on_progress,
            status_callback=self._on_status,
            log_callback=self._on_log,
            max_retries=self.max_retries,
            resume=self.resume,
        )
        
        self.transfer_finished.emit(success, message)
    
    def _run_without_verification(self, filename: str):
        """
        执行不带 MD5 校验的文件传输（传统方式）
        
        Args:
            filename: 文件名
        """
        # 检查断点续传
        if self.resume:
            remote_size = self._client.get_remote_file_size(self.remote_path)
            if remote_size == self._total_size:
                self.transfer_finished.emit(True, "文件已存在，无需上传")
                return
            elif remote_size > 0:
                self.transfer_status.emit(f"断点续传: 从 {remote_size}/{self._total_size} 继续")
                self._transferred = remote_size
        
        self.transfer_status.emit(f"开始上传文件 ({filename})...")
        
        # 上传文件
        success = self._client.upload_file(
            self.local_path,
            self.remote_path,
            progress_callback=self._on_progress,
            resume=self.resume,
        )
        
        if success:
            self.log_message.emit("SUCCESS", f"文件上传完成: {filename}")
            self.transfer_finished.emit(True, "传输完成")
        else:
            self.log_message.emit("ERROR", f"文件上传失败: {filename}")
            self.transfer_finished.emit(False, "传输失败")
    
    def _on_progress(self, transferred: int, total: int):
        """
        进度回调
        
        Args:
            transferred: 已传输字节数
            total: 总字节数
        """
        # 处理暂停
        while self._is_paused and self._is_running:
            time.sleep(0.1)
        
        if not self._is_running:
            raise InterruptedError("传输已取消")
        
        self._transferred = transferred
        self.progress_updated.emit(transferred, total)
    
    def _on_status(self, message: str):
        """
        状态回调
        
        Args:
            message: 状态消息
        """
        self.transfer_status.emit(message)
        # 如果是 MD5 相关状态，也发送到 MD5 校验状态信号
        if "MD5" in message or "校验" in message:
            self.md5_verification_status.emit(message)
    
    def _on_log(self, level: str, message: str):
        """
        日志回调
        
        Args:
            level: 日志级别
            message: 日志消息
        """
        self.log_message.emit(level, message)
    
    def pause(self):
        """暂停传输"""
        self._is_paused = True
        self.transfer_paused.emit()
        self.transfer_status.emit("传输已暂停")
    
    def resume_transfer(self):
        """恢复传输"""
        self._is_paused = False
        self.transfer_resumed.emit()
        self.transfer_status.emit("传输已恢复")
    
    def stop(self):
        """停止传输"""
        self._is_running = False
        self._is_paused = False
        self.wait(2000)
    
    def is_paused(self) -> bool:
        """
        检查是否暂停
        
        Returns:
            bool: 已暂停返回 True
        """
        return self._is_paused
    
    def get_md5_values(self) -> Tuple[Optional[str], Optional[str]]:
        """
        获取 MD5 值
        
        Returns:
            Tuple[Optional[str], Optional[str]]: (本地MD5, 远程MD5)
        """
        return self._local_md5, self._remote_md5
    
    def get_retry_count(self) -> int:
        """
        获取重试次数
        
        Returns:
            int: 重试次数
        """
        return self._retry_count



class DeployWorker(QtCore.QThread):
    """
    一键部署工作线程
    
    在独立线程中执行完整的部署流程：
    1. 连接设备
    2. 上传文件（支持 MD5 校验和自动重传）
    3. 执行部署命令
    """
    
    # 部署步骤信号
    deploy_step = QtCore.pyqtSignal(str)  # 当前步骤
    # 部署进度信号
    deploy_progress = QtCore.pyqtSignal(int)  # 进度百分比
    # 部署日志信号
    deploy_log = QtCore.pyqtSignal(str, str)  # (级别, 消息)
    # 部署完成信号
    deploy_finished = QtCore.pyqtSignal(bool, str)  # (成功, 消息)
    # 文件传输进度信号
    file_progress = QtCore.pyqtSignal(int, int)  # (已传输, 总大小)
    # MD5 校验状态信号
    md5_verification_status = QtCore.pyqtSignal(str)  # 校验状态消息
    
    def __init__(
        self,
        device: DeviceInfo,
        local_path: str,
        remote_path: str = "/mmcblk1p2",
        deploy_commands: Optional[List[str]] = None,
        enable_md5_verify: bool = True,
        max_retries: int = 3,
        parent=None,
    ):
        """
        初始化部署线程
        
        Args:
            device: 设备信息
            local_path: 本地文件路径
            remote_path: 远程目标路径
            deploy_commands: 部署后执行的命令列表
            enable_md5_verify: 是否启用 MD5 校验
            max_retries: 最大重试次数
            parent: 父对象
        """
        super().__init__(parent)
        self.device = device
        self.local_path = local_path
        self.remote_path = remote_path
        self.deploy_commands = deploy_commands or []
        self.enable_md5_verify = enable_md5_verify
        self.max_retries = max_retries
        
        self._is_running = False
        self._client: Optional[SSHClient] = None
        
        # 创建 SSH 配置
        self.config = SSHConfig(
            host=device.host,
            port=device.port,
            username=device.username,
            password=device.password,
            timeout=10,
        )
        
        # MD5 校验相关
        self._local_md5: Optional[str] = None
        self._remote_md5: Optional[str] = None
        self._retry_count = 0
    
    def run(self):
        """执行一键部署"""
        self._is_running = True
        
        try:
            # 步骤 1: 连接设备
            self._update_step("连接设备", 10)
            self._log("正在连接设备...", LogLevel.INFO)
            
            self._client = SSHClient(self.config)
            if not self._client.connect():
                self._finish(False, "连接设备失败")
                return
            
            self._log("设备连接成功", LogLevel.SUCCESS)
            
            # 步骤 2: 上传文件
            self._update_step("上传文件", 40)
            self._log("开始上传文件...", LogLevel.INFO)
            
            filename = os.path.basename(self.local_path)
            remote_file_path = f"{self.remote_path}/{filename}"
            
            # 确保目标目录存在
            self._client.create_remote_directory(self.remote_path)
            
            # 根据是否启用 MD5 校验选择传输方式
            if self.enable_md5_verify:
                upload_success = self._upload_with_verification(filename, remote_file_path)
            else:
                upload_success = self._upload_without_verification(filename, remote_file_path)
            
            if not upload_success:
                self._finish(False, "文件上传失败")
                return
            
            self._log("文件上传完成", LogLevel.SUCCESS)
            
            # 步骤 3: 执行部署命令
            if self.deploy_commands:
                self._update_step("执行部署命令", 80)
                self._log("开始执行部署命令...", LogLevel.INFO)
                
                for i, command in enumerate(self.deploy_commands):
                    self._log(f"执行命令 [{i+1}/{len(self.deploy_commands)}]: {command}", LogLevel.INFO)
                    
                    success, stdout, stderr = self._client.execute_command(
                        command,
                        timeout=60,
                        get_output=True,
                    )
                    
                    if stdout:
                        self._log(f"输出: {stdout}", LogLevel.DEBUG)
                    if stderr:
                        self._log(f"错误: {stderr}", LogLevel.WARNING)
                    
                    if not success:
                        self._finish(False, f"命令执行失败: {command}")
                        return
                
                self._log("部署命令执行完成", LogLevel.SUCCESS)
            
            # 部署完成
            self._update_step("部署完成", 100)
            self._finish(True, "部署成功完成")
            
        except Exception as e:
            self._log(f"部署错误: {str(e)}", LogLevel.ERROR)
            self._finish(False, f"部署失败: {str(e)}")
        finally:
            if self._client:
                self._client.disconnect()
            self._is_running = False
    
    def _upload_with_verification(self, filename: str, remote_file_path: str) -> bool:
        """
        使用 MD5 校验上传文件
        
        Args:
            filename: 文件名
            remote_file_path: 远程文件路径
            
        Returns:
            bool: 上传成功返回 True
        """
        self._log(f"启用 MD5 校验上传: {filename}", LogLevel.INFO)
        
        success, message = self._client.upload_file_with_verification(
            local_path=self.local_path,
            remote_path=remote_file_path,
            progress_callback=self._on_file_progress,
            status_callback=self._on_status,
            log_callback=self._on_log,
            max_retries=self.max_retries,
            resume=True,
        )
        
        return success
    
    def _upload_without_verification(self, filename: str, remote_file_path: str) -> bool:
        """
        不使用 MD5 校验上传文件（传统方式）
        
        Args:
            filename: 文件名
            remote_file_path: 远程文件路径
            
        Returns:
            bool: 上传成功返回 True
        """
        self._log(f"传统方式上传: {filename}", LogLevel.INFO)
        
        success = self._client.upload_file(
            self.local_path,
            remote_file_path,
            progress_callback=self._on_file_progress,
            resume=True,
        )
        
        return success
    
    def _on_status(self, message: str):
        """
        状态回调
        
        Args:
            message: 状态消息
        """
        # 如果是 MD5 相关状态，发送到 MD5 校验状态信号
        if "MD5" in message or "校验" in message:
            self.md5_verification_status.emit(message)
    
    def _on_log(self, level: str, message: str):
        """
        日志回调
        
        Args:
            level: 日志级别
            message: 日志消息
        """
        # 转换日志级别并发射信号
        level_map = {
            "DEBUG": LogLevel.DEBUG,
            "INFO": LogLevel.INFO,
            "WARNING": LogLevel.WARNING,
            "ERROR": LogLevel.ERROR,
            "SUCCESS": LogLevel.SUCCESS,
        }
        log_level = level_map.get(level, LogLevel.INFO)
        self._log(message, log_level)
    
    def _update_step(self, step: str, progress: int):
        """
        更新部署步骤
        
        Args:
            step: 步骤名称
            progress: 进度百分比
        """
        self.deploy_step.emit(step)
        self.deploy_progress.emit(progress)
    
    def _log(self, message: str, level: LogLevel = LogLevel.INFO):
        """
        记录日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        self.deploy_log.emit(level.value, message)
    
    def _on_file_progress(self, transferred: int, total: int):
        """
        文件传输进度回调
        
        Args:
            transferred: 已传输字节数
            total: 总字节数
        """
        self.file_progress.emit(transferred, total)
        
        # 计算整体进度（10-70% 用于文件传输）
        if total > 0:
            file_progress = int((transferred / total) * 60)
            self.deploy_progress.emit(10 + file_progress)
    
    def _finish(self, success: bool, message: str):
        """
        完成部署
        
        Args:
            success: 是否成功
            message: 完成消息
        """
        self.deploy_finished.emit(success, message)
    
    def stop(self):
        """停止部署"""
        self._is_running = False
        self.wait(3000)


class BatchDeployWorker(QtCore.QThread):
    """
    批量部署工作线程
    
    同时向多个设备部署文件。
    """
    
    # 单个设备部署完成信号
    device_deployed = QtCore.pyqtSignal(str, bool, str)  # (设备ID, 成功, 消息)
    # 总体进度信号
    batch_progress = QtCore.pyqtSignal(int, int)  # (已完成, 总数)
    # 批量部署完成信号
    batch_finished = QtCore.pyqtSignal(int, int)  # (成功数, 失败数)
    
    def __init__(
        self,
        devices: List[DeviceInfo],
        local_path: str,
        remote_path: str = "/mmcblk1p2",
        deploy_commands: Optional[List[str]] = None,
        parent=None,
    ):
        """
        初始化批量部署线程
        
        Args:
            devices: 设备列表
            local_path: 本地文件路径
            remote_path: 远程目标路径
            deploy_commands: 部署命令列表
            parent: 父对象
        """
        super().__init__(parent)
        self.devices = devices
        self.local_path = local_path
        self.remote_path = remote_path
        self.deploy_commands = deploy_commands or []
        
        self._is_running = False
        self._success_count = 0
        self._failed_count = 0
    
    def run(self):
        """执行批量部署"""
        self._is_running = True
        self._success_count = 0
        self._failed_count = 0
        
        total = len(self.devices)
        
        for i, device in enumerate(self.devices):
            if not self._is_running:
                break
            
            # 创建单个设备的部署线程
            worker = DeployWorker(
                device,
                self.local_path,
                self.remote_path,
                self.deploy_commands,
            )
            
            # 连接信号
            worker.deploy_finished.connect(
                lambda success, msg, d=device: self._on_device_finished(d, success, msg)
            )
            
            # 启动并等待完成
            worker.start()
            worker.wait()
            
            # 更新总体进度
            self.batch_progress.emit(i + 1, total)
        
        self.batch_finished.emit(self._success_count, self._failed_count)
        self._is_running = False
    
    def _on_device_finished(self, device: DeviceInfo, success: bool, message: str):
        """
        单个设备部署完成回调
        
        Args:
            device: 设备信息
            success: 是否成功
            message: 完成消息
        """
        if success:
            self._success_count += 1
        else:
            self._failed_count += 1
        
        self.device_deployed.emit(device.id, success, message)
    
    def stop(self):
        """停止批量部署"""
        self._is_running = False
        self.wait(5000)