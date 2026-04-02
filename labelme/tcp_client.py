# -*- coding: utf-8 -*-
"""
TCP客户端线程模块
用于在后台线程中连接TCP服务器并定期发送数据
"""

import socket
import time
from typing import Optional
from PyQt5 import QtCore
from loguru import logger

from labelme.tcp_config import load_tcp_config


class TcpClientThread(QtCore.QThread):
    """
    TCP客户端线程类
    在后台线程中连接TCP服务器，定期发送消息
    """
    
    # 信号：连接状态改变
    connection_status_changed = QtCore.pyqtSignal(bool, str)  # (connected, message)
    
    def __init__(self, parent=None):
        """
        初始化TCP客户端线程
        
        Args:
            parent: 父对象
        """
        super().__init__(parent)
        self._running = False
        self._socket: Optional[socket.socket] = None
        self._config = None
        self._connected = False
        
    def load_config(self):
        """加载TCP配置"""
        self._config = load_tcp_config()
        logger.info(f"TCP客户端配置已加载: {self._config}")
    
    def connect_to_server(self) -> bool:
        """
        连接到TCP服务器
        
        Returns:
            bool: 是否连接成功
        """
        if not self._config:
            self.load_config()
        
        host = self._config.get("host", "127.0.0.1")
        port = self._config.get("port", 10012)
        
        try:
            # 如果已有连接，先关闭
            if self._socket:
                try:
                    self._socket.close()
                except:
                    pass
                self._socket = None
            
            # 创建新的socket连接
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(5)  # 设置连接超时5秒
            self._socket.connect((host, port))
            self._socket.settimeout(None)  # 连接成功后取消超时设置
            
            self._connected = True
            logger.info(f"TCP客户端已连接到服务器 {host}:{port}")
            self.connection_status_changed.emit(True, f"已连接到 {host}:{port}")
            
            # 连接成功后立即发送一次状态消息，避免启动顺序导致的状态不同步
            message = self._config.get("message", "labelme") if self._config else "labelme"
            if not self.send_message(message):
                logger.warning("TCP客户端连接成功但首次消息发送失败，将在后续重试")
                self._connected = False
                self.connection_status_changed.emit(False, "首次消息发送失败")
                return False
            
            return True
            
        except socket.timeout:
            # logger.warning(f"连接TCP服务器超时: {host}:{port}")
            self.connection_status_changed.emit(False, f"连接超时: {host}:{port}")
            return False
        except ConnectionRefusedError:
            # logger.warning(f"TCP服务器拒绝连接: {host}:{port}")
            self.connection_status_changed.emit(False, f"服务器拒绝连接: {host}:{port}")
            return False
        except Exception as e:
            logger.error(f"连接TCP服务器失败: {host}:{port}, 错误: {e}")
            self.connection_status_changed.emit(False, f"连接失败: {str(e)}")
            return False
    
    def send_message(self, message: str) -> bool:
        """
        发送消息到服务器
        
        Args:
            message: 要发送的消息
            
        Returns:
            bool: 是否发送成功
        """
        if not self._socket or not self._connected:
            return False
        
        try:
            # 将消息编码为UTF-8字节并发送
            data = message.encode('utf-8')
            self._socket.sendall(data)
            logger.debug(f"TCP客户端已发送消息: {message}")
            return True
        except socket.error as e:
            logger.error(f"发送TCP消息失败: {e}")
            self._connected = False
            self.connection_status_changed.emit(False, f"发送失败: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"发送TCP消息时发生异常: {e}")
            self._connected = False
            return False
    
    def disconnect_from_server(self):
        """断开与服务器的连接"""
        if self._socket:
            try:
                self._socket.close()
                logger.info("TCP客户端已断开连接")
            except:
                pass
            finally:
                self._socket = None
                self._connected = False
                self.connection_status_changed.emit(False, "已断开连接")
    
    def stop(self):
        """停止TCP客户端线程"""
        logger.info("正在停止TCP客户端线程...")
        self._running = False
        self.disconnect_from_server()
        # 等待线程结束
        if self.isRunning():
            self.wait(3000)  # 最多等待3秒
    
    def run(self):
        """
        线程主函数
        连接服务器并定期发送消息
        """
        self._running = True
        
        # 加载配置
        if not self._config:
            self.load_config()
        
        host = self._config.get("host", "127.0.0.1")
        port = self._config.get("port", 10012)
        message = self._config.get("message", "labelme")
        interval = self._config.get("interval", 2)
        reconnect_interval = self._config.get("reconnect_interval", 5)
        
        logger.info(f"TCP客户端线程启动: {host}:{port}, 消息: {message}, 间隔: {interval}秒")
        
        while self._running:
            # 如果未连接，尝试连接
            if not self._connected:
                if not self.connect_to_server():
                    # 连接失败，等待重连间隔后重试
                    # logger.info(f"等待 {reconnect_interval} 秒后重试连接...")
                    for _ in range(reconnect_interval * 10):  # 每0.1秒检查一次
                        if not self._running:
                            break
                        time.sleep(0.1)
                    continue
            
            # 如果已连接，发送消息
            if self._connected:
                if not self.send_message(message):
                    # 发送失败，标记为未连接，下次循环会重连
                    self._connected = False
                else:
                    # 发送成功，等待指定间隔
                    for _ in range(int(interval * 10)):  # 每0.1秒检查一次
                        if not self._running:
                            break
                        time.sleep(0.1)
            else:
                # 未连接状态，短暂等待后重试
                time.sleep(0.1)
        
        # 清理资源
        self.disconnect_from_server()
        logger.info("TCP客户端线程已停止")
