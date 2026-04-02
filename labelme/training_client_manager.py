# -*- coding: utf-8 -*-
"""
训练客户端管理器模块

本模块将 training_client 封装为 Qt 信号/槽风格的异步管理器，
提供与远程训练服务器的通信功能，所有网络操作在独立线程中执行，
避免阻塞 UI。

主要类：
    TrainingClientManager - 训练客户端管理器，管理远程训练任务

使用示例：
    manager = TrainingClientManager(host="127.0.0.1", port=8888)
    manager.connected.connect(on_connected)
    manager.task_created.connect(on_task_created)
    manager.connect_server()
"""

import sys
import time
import threading
import weakref
from typing import Dict, Any, Optional, List
from datetime import datetime

from PyQt5 import QtCore, QtWidgets
from loguru import logger

# 导入 training_client 模块
sys.path.insert(0, r'e:\shangweiji\WSLabelme\labelme')
from training_client.training_client import TrainingClient, MessageProtocol


class TrainingClientManager(QtCore.QObject):
    """
    训练客户端管理器类

    封装 TrainingClient，提供 Qt 信号/槽机制，所有网络操作在后台线程执行。
    支持连接管理、任务创建、训练控制、进度监控等功能。

    Attributes:
        _client (TrainingClient): 底层训练客户端
        _host (str): 服务器地址
        _port (int): 服务器端口
        _monitor_thread (threading.Thread): 监控线程
        _stop_monitoring (bool): 停止监控标志
        _current_task_id (str): 当前监控的任务 ID
    """

    # ==================== 信号定义 ====================
    connected = QtCore.pyqtSignal(bool)  # 连接成功/失败
    connection_error = QtCore.pyqtSignal(str)  # 连接错误信息

    task_created = QtCore.pyqtSignal(str)  # 任务创建成功，返回 task_id
    task_creation_failed = QtCore.pyqtSignal(str)  # 任务创建失败信息

    training_started = QtCore.pyqtSignal(str)  # 训练启动成功，返回 task_id
    training_start_failed = QtCore.pyqtSignal(str, str)  # (task_id, error_msg)

    training_stopped = QtCore.pyqtSignal(str)  # 训练停止成功，返回 task_id
    training_stop_failed = QtCore.pyqtSignal(str, str)  # (task_id, error_msg)

    task_deleted = QtCore.pyqtSignal(str)  # 任务删除成功，返回 task_id
    task_deletion_failed = QtCore.pyqtSignal(str, str)  # (task_id, error_msg)

    progress_updated = QtCore.pyqtSignal(str, dict)  # (task_id, progress_data)
    status_changed = QtCore.pyqtSignal(str, dict)  # (task_id, status_data)

    task_list_updated = QtCore.pyqtSignal(list)  # 任务列表更新
    task_list_failed = QtCore.pyqtSignal(str)  # 获取任务列表失败

    error_occurred = QtCore.pyqtSignal(str)  # 通用错误信息
    log_message = QtCore.pyqtSignal(str)  # 日志消息

    def __init__(self, host: str = "127.0.0.1", port: int = 8888):
        """
        初始化训练客户端管理器

        Args:
            host: 服务器地址，默认 "127.0.0.1"
            port: 服务器端口，默认 8888
        """
        super().__init__()
        self._host = host
        self._port = port
        self._client = None  # 不在初始化时创建客户端
        self._monitor_thread = None
        self._stop_monitoring = False
        self._current_task_id = None
        self._lock = threading.Lock()
        self._list_tasks_lock = threading.Lock()
        self._disposed = False
        # 心跳检测相关
        self._heartbeat_thread = None
        self._stop_heartbeat = False
        self._heartbeat_interval = 3.0  # 心跳间隔（秒）
        logger.info(f"[TrainingManager] 初始化完成，目标服务器: {host}:{port}")

    def get_host(self) -> str:
        """获取服务器地址"""
        return self._host

    def get_port(self) -> int:
        """获取服务器端口"""
        return self._port

    def is_connected(self) -> bool:
        """检查是否已连接到服务器"""
        return self._client is not None and self._client.connected

    def get_current_task_id(self) -> Optional[str]:
        """获取当前监控的任务 ID"""
        with self._lock:
            return self._current_task_id

    def connect_server(self, host: str = None, port: int = None):
        """
        连接到训练服务器（异步）

        Args:
            host: 服务器地址，为 None 则使用初始化时的地址
            port: 服务器端口，为 None 则使用初始化时的端口
        """
        if self._disposed:
            logger.warning("[TrainingManager] 管理器已释放，无法连接")
            self.connection_error.emit("管理器已释放")
            return

        if host:
            self._host = host
        if port:
            self._port = port

        logger.info(f"[TrainingManager] 开始连接服务器: {self._host}:{self._port}")

        def _connect():
            try:
                # 如果已连接，先断开
                if self._client:
                    logger.info("[TrainingManager] 检测到已有客户端实例，先断开")
                    try:
                        self._client.disconnect()
                    except Exception as e:
                        logger.warning(f"[TrainingManager] 断开旧连接时出错: {e}")
                    finally:
                        self._client = None

                # 创建新的客户端连接
                logger.info("[TrainingManager] 创建新的 TrainingClient 实例")
                self._client = TrainingClient(self._host, self._port)

                logger.info("[TrainingManager] 执行 connect() 连接操作")
                if self._client.connect():
                    logger.info("[TrainingManager] socket 连接成功，开始 ping 测试")
                    # 测试连接
                    try:
                        if self._client.ping():
                            logger.info(f"[TrainingManager] ping 测试成功，服务器 {self._host}:{self._port} 响应正常")
                            self.connected.emit(True)
                            self.log_message.emit(f"已连接到服务器 {self._host}:{self._port}")
                            # 启动心跳检测线程
                            self._start_heartbeat()
                        else:
                            logger.warning(f"[TrainingManager] ping 测试失败：服务器 {self._host}:{self._port} 无响应")
                            # ping 失败时清理资源
                            try:
                                self._client.disconnect()
                            except:
                                pass
                            self._client = None
                            self.connected.emit(False)
                            self.connection_error.emit("服务器无响应")
                    except Exception as e:
                        logger.error(f"[TrainingManager] ping 测试异常: {e}")
                        # ping 异常时清理资源
                        try:
                            self._client.disconnect()
                        except:
                            pass
                        self._client = None
                        self.connected.emit(False)
                        self.connection_error.emit(f"Ping 测试失败：{str(e)}")
                else:
                    logger.error(f"[TrainingManager] 连接失败：无法连接到 {self._host}:{self._port}")
                    # 连接失败时清理资源
                    self._client = None
                    self.connected.emit(False)
                    self.connection_error.emit(f"无法连接到服务器 {self._host}:{self._port}")
            except Exception as e:
                logger.error(f"[TrainingManager] 连接过程异常: {e}")
                # 异常时清理资源
                if self._client:
                    try:
                        self._client.disconnect()
                    except:
                        pass
                    self._client = None
                self.connected.emit(False)
                self.connection_error.emit(f"连接异常：{str(e)}")

        thread = threading.Thread(target=_connect, daemon=True)
        thread.start()
        logger.info("[TrainingManager] 连接线程已启动")

    def disconnect_server(self):
        """断开服务器连接"""
        logger.info("[TrainingManager] 开始断开服务器连接")

        if self._disposed:
            logger.warning("[TrainingManager] 管理器已释放，跳过断开操作")
            return

        try:
            # 先停止心跳检测
            self._stop_heartbeat = True
            if self._heartbeat_thread and self._heartbeat_thread.is_alive():
                logger.info("[TrainingManager] 等待心跳线程停止")
                self._heartbeat_thread.join(timeout=2)
                logger.info("[TrainingManager] 心跳线程已停止")

            # 停止监控，避免线程访问已断开的连接
            with self._lock:
                self._stop_monitoring = True
            logger.info("[TrainingManager] 已设置停止监控标志")

            if self._monitor_thread and self._monitor_thread.is_alive():
                logger.info("[TrainingManager] 等待监控线程停止")
                self._monitor_thread.join(timeout=2)
                logger.info("[TrainingManager] 监控线程已停止")

            # 安全断开客户端连接
            if self._client:
                try:
                    logger.info("[TrainingManager] 执行 client.disconnect()")
                    self._client.disconnect()
                    logger.info("[TrainingManager] 客户端连接已断开")
                except Exception as e:
                    logger.warning(f"[TrainingManager] 断开客户端连接时出错: {e}")

            # 重置状态
            with self._lock:
                self._current_task_id = None

            logger.info("[TrainingManager] 服务器连接断开完成")
            self.log_message.emit("已断开服务器连接")
            # 发出断开连接信号，通知 UI 更新状态
            self.connected.emit(False)
        except Exception as e:
            if not self._disposed:
                logger.error(f"[TrainingManager] 断开连接异常: {e}")
                self.error_occurred.emit(f"断开连接异常：{str(e)}")

    def create_task(self, params: Dict[str, Any]):
        """
        创建训练任务（异步）

        Args:
            params: 训练参数字典
        """
        if self._disposed:
            self.task_creation_failed.emit("管理器已释放")
            return

        def _create():
            try:
                if not self._client or not self._client.connected:
                    self.task_creation_failed.emit("未连接到服务器")
                    return

                task_id = self._client.create_task(params)
                if task_id:
                    self.task_created.emit(task_id)
                    self.log_message.emit(f"任务创建成功：{task_id}")
                else:
                    self.task_creation_failed.emit("任务创建失败")
            except Exception as e:
                self.task_creation_failed.emit(f"创建任务异常：{str(e)}")

        thread = threading.Thread(target=_create, daemon=True)
        thread.start()

    def start_training(self, task_id: str):
        """
        启动训练任务（异步）

        Args:
            task_id: 任务 ID
        """
        if self._disposed:
            self.training_start_failed.emit(task_id, "管理器已释放")
            return

        def _start():
            try:
                if not self._client or not self._client.connected:
                    self.training_start_failed.emit(task_id, "未连接到服务器")
                    return

                if self._client.start_training(task_id):
                    self.training_started.emit(task_id)
                    self.log_message.emit(f"训练已启动：{task_id}")
                    # 屏蔽自动监控，使用 monitor_training 刷新
                    # self.start_monitoring(task_id)
                else:
                    self.training_start_failed.emit(task_id, "启动训练失败")
            except Exception as e:
                self.training_start_failed.emit(task_id, f"启动训练异常：{str(e)}")

        thread = threading.Thread(target=_start, daemon=True)
        thread.start()

    def stop_training(self, task_id: str):
        """
        停止训练任务（异步）

        Args:
            task_id: 任务 ID
        """
        if self._disposed:
            self.training_stop_failed.emit(task_id, "管理器已释放")
            return

        def _stop():
            try:
                if not self._client or not self._client.connected:
                    self.training_stop_failed.emit(task_id, "未连接到服务器")
                    return

                if self._client.stop_training(task_id):
                    self.training_stopped.emit(task_id)
                    self.log_message.emit(f"训练已停止：{task_id}")
                    with self._lock:
                        self._stop_monitoring = True
                else:
                    self.training_stop_failed.emit(task_id, "停止训练失败")
            except Exception as e:
                self.training_stop_failed.emit(task_id, f"停止训练异常：{str(e)}")

        thread = threading.Thread(target=_stop, daemon=True)
        thread.start()

    def delete_task(self, task_id: str):
        """
        删除训练任务（异步）

        Args:
            task_id: 任务 ID
        """
        if self._disposed:
            self.task_deletion_failed.emit(task_id, "管理器已释放")
            return

        def _delete():
            try:
                if not self._client or not self._client.connected:
                    self.task_deletion_failed.emit(task_id, "未连接到服务器")
                    return

                if self._client.delete_task(task_id):
                    self.task_deleted.emit(task_id)
                    self.log_message.emit(f"任务已删除：{task_id}")
                else:
                    self.task_deletion_failed.emit(task_id, "删除任务失败")
            except Exception as e:
                self.task_deletion_failed.emit(task_id, f"删除任务异常：{str(e)}")

        thread = threading.Thread(target=_delete, daemon=True)
        thread.start()

    def get_task_status(self, task_id: str):
        """
        获取任务状态（异步）

        Args:
            task_id: 任务 ID
        """
        if self._disposed:
            return

        def _get_status():
            try:
                if not self._client or not self._client.connected:
                    logger.warning(f"[TrainingManager] 获取任务状态失败：未连接到服务器")
                    self.error_occurred.emit("获取任务状态失败：未连接到服务器")
                    return

                logger.info(f"[TrainingManager] 正在获取任务 {task_id[:16]}... 的状态")
                status_data = self._client.get_task_status(task_id)
                if status_data:
                    logger.info(f"[TrainingManager] 获取任务状态成功：{status_data}")
                    self.status_changed.emit(task_id, status_data)
                else:
                    logger.warning(f"[TrainingManager] 获取任务状态失败：服务器返回空数据")
                    self.error_occurred.emit("获取任务状态失败：服务器返回空数据")
            except Exception as e:
                logger.error(f"[TrainingManager] 获取任务状态异常: {e}")
                self.error_occurred.emit(f"获取任务状态异常：{str(e)}")

        thread = threading.Thread(target=_get_status, daemon=True)
        thread.start()

    def get_progress(self, task_id: str):
        """
        获取训练进度（异步）

        Args:
            task_id: 任务 ID
        """
        if self._disposed:
            return

        def _get_progress():
            try:
                if not self._client or not self._client.connected:
                    return

                progress_data = self._client.get_progress(task_id)
                if progress_data:
                    self.progress_updated.emit(task_id, progress_data)
            except Exception as e:
                self.error_occurred.emit(f"获取训练进度异常：{str(e)}")

        thread = threading.Thread(target=_get_progress, daemon=True)
        thread.start()

    def list_tasks(self):
        """获取任务列表（异步）"""
        if self._disposed:
            self.task_list_failed.emit("管理器已释放")
            return

        def _list():
            # 使用锁防止并发请求
            if not self._list_tasks_lock.acquire(blocking=False):
                logger.debug("[TrainingManager] 已有任务列表请求在进行中，跳过")
                return
            try:
                if not self._client or not self._client.connected:
                    logger.warning("[TrainingManager] 获取任务列表失败：未连接到服务器")
                    self.task_list_failed.emit("未连接到服务器")
                    return

                logger.info("[TrainingManager] 正在获取任务列表...")
                data = self._client.list_tasks()
                if data:
                    tasks = data.get("tasks", [])
                    logger.info(f"[TrainingManager] 获取任务列表成功，共 {len(tasks)} 个任务")
                    self.task_list_updated.emit(tasks)
                else:
                    logger.warning("[TrainingManager] 获取任务列表失败：服务器返回空数据")
                    self.task_list_failed.emit("获取任务列表失败")
            except Exception as e:
                logger.error(f"[TrainingManager] 获取任务列表异常: {e}")
                self.task_list_failed.emit(f"获取任务列表异常：{str(e)}")
            finally:
                self._list_tasks_lock.release()

        thread = threading.Thread(target=_list, daemon=True)
        thread.start()

    def start_monitoring(self, task_id: str, poll_interval: float = 2.0, fast_poll_count: int = 5):
        """
        开始监控训练任务进度

        Args:
            task_id: 要监控的任务 ID
            poll_interval: 轮询间隔（秒）
            fast_poll_count: 初始快速轮询次数（前几次用更短间隔）
        """
        if self._disposed:
            return

        # 使用线程安全的方式设置状态
        with self._lock:
            if self._stop_monitoring and self._monitor_thread and self._monitor_thread.is_alive():
                # 等待之前的监控线程停止
                self._monitor_thread.join(timeout=2)
            self._current_task_id = task_id
            self._stop_monitoring = False

        def _monitor():
            try:
                self.log_message.emit(f"开始监控任务：{task_id}")
                poll_count = 0

                while True:
                    # 使用线程安全的方式读取停止标志
                    with self._lock:
                        if self._stop_monitoring:
                            break

                        # 检查客户端连接状态
                        if not self._client or not self._client.connected:
                            self.error_occurred.emit("监控中断：未连接到服务器")
                            break

                    try:
                        # 获取状态
                        status_data = self._client.get_task_status(task_id)
                        if status_data:
                            self.status_changed.emit(task_id, status_data)

                            # 如果任务已完成或出错，检查实际进度
                            status = status_data.get("status", "unknown")
                            if status in ["completed", "failed", "stopped"]:
                                # 获取进度确认是否真的完成
                                progress_data = self._client.get_progress(task_id)
                                if progress_data:
                                    self.progress_updated.emit(task_id, progress_data)
                                    progress_info = progress_data.get("progress", {})
                                    epoch = progress_info.get("epoch", 0)
                                    total_epochs = progress_info.get("total_epochs", 0)
                                    is_complete = total_epochs > 0 and epoch == total_epochs
                                    # completed 状态下，只有轮次真正跑完才结束监控
                                    if status == "completed" and not is_complete:
                                        self.log_message.emit(
                                            f"任务状态为completed但轮次为 {epoch}/{total_epochs}，继续监控..."
                                        )
                                    else:
                                        self.log_message.emit(f"任务 {task_id} 已结束，状态：{status}")
                                        break
                                else:
                                    if status == "completed":
                                        self.log_message.emit(f"任务状态为completed但未获取到轮次信息，继续监控...")
                                    else:
                                        self.log_message.emit(f"任务 {task_id} 已结束，状态：{status}")
                                        break
                            else:
                                # 获取进度
                                progress_data = self._client.get_progress(task_id)
                                if progress_data:
                                    self.progress_updated.emit(task_id, progress_data)
                        else:
                            # 状态获取失败，尝试获取进度
                            progress_data = self._client.get_progress(task_id)
                            if progress_data:
                                self.progress_updated.emit(task_id, progress_data)
                    except Exception as e:
                        self.error_occurred.emit(f"监控异常：{str(e)}")
                        break

                    poll_count += 1
                    # 前几次使用更短的间隔（0.5秒），之后使用正常间隔
                    current_interval = 0.5 if poll_count < fast_poll_count else poll_interval

                    # 等待下一次轮询（使用小片段睡眠，便于响应停止信号）
                    for _ in range(int(current_interval * 10)):
                        with self._lock:
                            if self._stop_monitoring:
                                break
                        time.sleep(0.1)

            except Exception as e:
                self.error_occurred.emit(f"监控线程异常：{str(e)}")
            finally:
                # 清理状态
                with self._lock:
                    self._current_task_id = None

        # 创建并启动监控线程
        self._monitor_thread = threading.Thread(target=_monitor, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        """停止监控"""
        with self._lock:
            self._stop_monitoring = True
            self._current_task_id = None
        self.log_message.emit("已停止监控")

    def cleanup(self):
        """
        清理资源

        在管理器不再需要时调用，释放所有资源
        """
        if self._disposed:
            return

        # 停止监控
        self.stop_monitoring()

        # 断开连接
        self.disconnect_server()

        # 标记为已释放
        self._disposed = True

    def _start_heartbeat(self):
        """启动心跳检测线程"""
        self._stop_heartbeat = False
        
        def _heartbeat_loop():
            logger.info("[TrainingManager] 心跳检测线程已启动")
            consecutive_failures = 0
            max_failures = 2  # 连续失败2次判定为断开
            
            while not self._stop_heartbeat:
                try:
                    # 等待心跳间隔（3秒）
                    for _ in range(int(self._heartbeat_interval * 10)):
                        if self._stop_heartbeat:
                            break
                        time.sleep(0.1)
                    
                    if self._stop_heartbeat:
                        break
                    
                    # 检查连接状态
                    if not self._client or not self._client.connected:
                        logger.warning("[TrainingManager] 心跳检测：客户端连接已失效，停止当前心跳线程")
                        self._handle_connection_lost("客户端连接已断开，请重新连接")
                        break
                    
                    # 发送心跳 ping
                    try:
                        if self._client.ping(timeout=3.0):
                            consecutive_failures = 0
                            logger.debug("[TrainingManager] 心跳检测成功")
                        else:
                            consecutive_failures += 1
                            logger.warning(f"[TrainingManager] 心跳检测失败 ({consecutive_failures}/{max_failures})")
                    except Exception as e:
                        consecutive_failures += 1
                        logger.warning(f"[TrainingManager] 心跳检测异常: {e} ({consecutive_failures}/{max_failures})")
                    
                    # 第一次失败，更新状态为网络异常
                    if consecutive_failures == 1:
                        logger.warning("[TrainingManager] 心跳检测失败一次，网络异常")
                        self.connection_error.emit("网络异常")
                    
                    # 连续失败超过阈值，判定当前连接已失效，不直接认定服务器退出
                    elif consecutive_failures >= max_failures:
                        logger.error("[TrainingManager] 心跳检测连续失败，判定当前连接已失效")
                        self._handle_connection_lost("与训练服务器的连接已断开，请重新连接")
                        break
                        
                except Exception as e:
                    logger.error(f"[TrainingManager] 心跳检测线程异常: {e}")
                    break
            
            logger.info("[TrainingManager] 心跳检测线程已退出")
        
        self._heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
    
    def _handle_connection_lost(self, reason: str = "服务器连接已断开"):
        """处理连接失效，不将其等同于服务器进程退出"""
        logger.info(f"[TrainingManager] 处理连接失效: {reason}")
        
        # 清理客户端资源
        if self._client:
            try:
                self._client.disconnect()
            except:
                pass
            self._client = None
        
        # 发出断开连接信号
        self.connected.emit(False)
        self.connection_error.emit(reason)
        self.log_message.emit(reason)
