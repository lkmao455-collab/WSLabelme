#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练客户端模块 (Training Client)

本模块实现了 AI 模型训练客户端，用于与远程训练服务器进行通信，
完成训练任务的创建、启动、监控和删除等操作。

核心功能:
    - TrainingClient: 基础训练客户端类，提供底层通信接口
    - InteractiveClient: 交互式命令行客户端，提供友好的用户界面
    - MessageProtocol: 消息协议类，负责数据的打包和解包

通信协议:
    采用自定义 TCP 协议，数据包结构如下:
    ┌────────────┬────────────┬────────────┬────────────┐
    │   包头     │    长度    │   校验和   │    数据    │
    │  (4 字节)  │  (4 字节)  │  (4 字节)  │  (N 字节)  │
    │ 0x55AA55AA │ 数据字节数 │ CRC32 校验 │ JSON 字符串 │
    └────────────┴────────────┴────────────┴────────────┘

使用示例:
    # 基础用法
    from training_client import TrainingClient

    client = TrainingClient(host="127.0.0.1", port=8888)
    client.connect()
    client.ping()
    task_id = client.create_task({"epochs": 50, "batch_size": 32})
    client.start_training(task_id)
    client.monitor_training(task_id)
    client.disconnect()

    # 交互式用法
    from training_client import InteractiveClient

    client = InteractiveClient()
    client.run()

作者: WSLabelme Team
版本: 1.0.0
"""

import socket
import json
import time
import threading
import struct
import sys
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import argparse
from loguru import logger


# ============================================================================
# MessageProtocol 类 - 消息协议处理
# ============================================================================
# 原理说明:
# TCP 是流式协议，没有消息边界。为了解决"粘包"和"拆包"问题，
# 我们设计了自定义的应用层协议:
#
# 1. 包头 (Header): 固定魔数 0x55AA55AA，用于标识消息的开始位置
#    - 接收方通过搜索这个魔数来确定消息边界
#    - 使用大端序 ('>I') 保证跨平台兼容性
#
# 2. 长度 (Length): 数据部分的字节数
#    - 接收方根据长度精确读取数据，避免多读或少读
#    - 大端序 4 字节无符号整数，最大支持 4GB 数据
#
# 3. 校验和 (Checksum): 用于验证数据完整性
#    - 计算方法：所有数据字节累加，取低 32 位
#    - 防止传输过程中的数据损坏
#
# 4. 数据 (Data): UTF-8 编码的 JSON 字符串
#    - 包含命令类型、请求 ID、参数等信息
#    - JSON 格式便于跨语言和跨平台
# ============================================================================

class MessageProtocol:
    """
    消息协议类 - 负责消息的打包 (发送) 和解包 (接收)

    该类实现了自定义 TCP 协议的核心逻辑，确保消息在传输过程中的完整性和正确性。

    协议格式:
        [Header:4 字节][Length:4 字节][Checksum:4 字节][Data:N 字节]

    字节序:
        所有多字节整数都使用大端序 (网络字节序) '>I' 格式
        - '>': 大端序 (Big-Endian)
        - 'I': 4 字节无符号整数 (Unsigned Int)

    使用示例:
        # 打包消息
        message = {"command": "ping", "request_id": "123"}
        packed = MessageProtocol.pack(message)
        socket.sendall(packed)

        # 接收消息
        response = MessageProtocol.receive(socket, timeout=30)
        data = json.loads(response)
    """

    @staticmethod
    def calculate_checksum(data: bytes) -> int:
        """
        计算校验和

        原理:
            遍历数据的所有字节，累加后取低 32 位作为校验和。
            这是一种简单的校验方法，可以检测到大部分单字节和双字节错误。

            & 0xFFFFFFFF 操作确保结果始终在 32 位范围内 (0-4294967295)
            这相当于 C 语言中的 unsigned int 溢出行为

        Args:
            data: 需要计算校验和的原始字节数据

        Returns:
            32 位校验和 (范围: 0-4294967295)

        示例:
            >>> data = b'{"command": "ping"}'
            >>> checksum = MessageProtocol.calculate_checksum(data)
            >>> print(f"校验和：0x{checksum:08X}")
            校验和：0x1A2B3C4D (示例值)
        """
        checksum = 0
        for byte in data:
            checksum = (checksum + byte) & 0xFFFFFFFF  # 保持 32 位
        return checksum

    @staticmethod
    def pack(message: str) -> bytes:
        """
        消息打包 - 将 JSON 消息打包成二进制协议格式

        打包流程:
            1. 将输入消息编码为 UTF-8 字节
            2. 计算数据长度
            3. 计算校验和 (基于数据部分)
            4. 组装：包头 + 长度 + 校验和 + 数据

        Args:
            message: 要发送的 JSON 字符串

        Returns:
            打包后的二进制数据，格式为:
            [0x55AA55AA][length:4 字节][checksum:4 字节][data]

        示例:
            >>> packed = MessageProtocol.pack('{"command": "ping"}')
            >>> print(f"打包后长度：{len(packed)} 字节")
            打包后长度：38 字节
        """
        # 将 JSON 字符串编码为 UTF-8 字节
        data = message.encode('utf-8')
        # 获取数据长度
        length = len(data)
        # 计算校验和
        checksum = MessageProtocol.calculate_checksum(data)

        # 包头：固定魔数 0x55AA55AA (4 字节，大端序)
        # 0x55AA55AA 是一个容易识别的魔数，二进制表示为 01010101...
        header = struct.pack('>I', 0x55AA55AA)

        # 组装完整数据包
        return header + struct.pack('>I', length) + struct.pack('>I', checksum) + data

    @staticmethod
    def receive(conn: socket.socket, timeout: float = 30) -> Optional[str]:
        """
        消息接收 - 从 Socket 连接接收并解析消息

        这是本协议最复杂的部分，需要处理以下问题:

        1. 分块读取 (Chunked Reading):
            TCP 是流式协议，数据可能分多次到达。
            使用 while 循环确保读取完整的指定字节数。

        2. 超时处理 (Timeout Handling):
            设置 socket 超时，避免无限期等待。
            默认 30 秒超时，适用于大多数场景。

        3. 粘包/拆包处理 (Sticky/Split Packet):
            通过包头魔数识别消息边界。
            通过长度字段确定数据大小。

        4. 数据校验 (Data Validation):
            验证包头魔数是否正确。
            验证校验和是否匹配。

        接收流程:
            1. 读取 4 字节包头，验证是否为 0x55AA55AA
            2. 读取 4 字节长度，确定数据大小
            3. 读取 4 字节校验和，用于后续验证
            4. 根据长度读取数据部分
            5. 计算校验和并与预期值比较
            6. 验证通过后解码为字符串

        Args:
            conn: Socket 连接对象
            timeout: 读取超时时间 (秒)，默认 30 秒

        Returns:
            解析后的 JSON 字符串，失败时返回 None

        失败情况:
            - 包头验证失败：数据包损坏或协议不匹配
            - 校验和不匹配：数据在传输过程中损坏
            - 超时：服务器在指定时间内未响应
            - 连接断开：远程关闭连接

        注意:
            该方法会修改 socket 的超时设置，在 finally 块中恢复原值。
        """
        try:
            # 设置超时时间
            conn.settimeout(timeout)
            print(f"[MessageProtocol] 开始接收消息，超时: {timeout}秒")

            # ========== 步骤 1: 读取包头 (4 字节) ==========
            print("[MessageProtocol] 等待读取包头 (4字节)...")
            header_data = b''
            while len(header_data) < 4:
                chunk = conn.recv(4 - len(header_data))
                if not chunk:  # 连接断开
                    print("[MessageProtocol] 连接断开，无法读取包头")
                    return None
                header_data += chunk
            print(f"[MessageProtocol] 包头数据: {header_data.hex()}")

            # 解析包头 (大端序无符号整数)
            header = struct.unpack('>I', header_data)[0]
            print(f"[MessageProtocol] 包头值: 0x{header:08X}")

            # 验证包头魔数
            if header != 0x55AA55AA:
                print(f"[MessageProtocol] 消息包头验证失败，期望: 0x55AA55AA, 实际: 0x{header:08X}")
                return None

            # ========== 步骤 2: 读取长度 (4 字节) ==========
            print("[MessageProtocol] 等待读取长度 (4字节)...")
            length_data = b''
            while len(length_data) < 4:
                chunk = conn.recv(4 - len(length_data))
                if not chunk:
                    print("[MessageProtocol] 连接断开，无法读取长度")
                    return None
                length_data += chunk

            # 解析长度 (大端序无符号整数)
            length = struct.unpack('>I', length_data)[0]
            print(f"[MessageProtocol] 数据长度: {length} 字节")

            # ========== 步骤 3: 读取校验和 (4 字节) ==========
            print("[MessageProtocol] 等待读取校验和 (4字节)...")
            checksum_data = b''
            while len(checksum_data) < 4:
                chunk = conn.recv(4 - len(checksum_data))
                if not chunk:
                    print("[MessageProtocol] 连接断开，无法读取校验和")
                    return None
                checksum_data += chunk

            # 解析预期校验和 (大端序无符号整数)
            expected_checksum = struct.unpack('>I', checksum_data)[0]
            print(f"[MessageProtocol] 预期校验和: 0x{expected_checksum:08X}")

            # ========== 步骤 4: 读取数据部分 (N 字节) ==========
            print(f"[MessageProtocol] 等待读取数据 ({length}字节)...")
            data = b''
            while len(data) < length:
                # 分块读取，每块最大 4096 字节
                chunk = conn.recv(min(4096, length - len(data)))
                if not chunk:
                    print("[MessageProtocol] 连接断开，无法读取完整数据")
                    return None
                data += chunk
            print(f"[MessageProtocol] 数据读取完成: {len(data)} 字节")

            # ========== 步骤 5: 验证校验和 ==========
            actual_checksum = MessageProtocol.calculate_checksum(data)
            print(f"[MessageProtocol] 实际校验和: 0x{actual_checksum:08X}")
            if actual_checksum != expected_checksum:
                print("[MessageProtocol] 消息校验失败：校验和不匹配")
                return None

            # ========== 步骤 6: 解码并返回 ==========
            result = data.decode('utf-8')
            print(f"[MessageProtocol] 消息接收成功: {result[:100]}...")
            return result

        except socket.timeout:
            # 超时处理
            print(f"[MessageProtocol] 接收消息超时（{timeout}秒）")
            return None
        except Exception as e:
            # 其他异常处理
            print(f"[MessageProtocol] 接收消息失败：{e}")
            return None
        finally:
            # 恢复 socket 超时设置 (None = 无限等待)
            conn.settimeout(None)


# ============================================================================
# TrainingClient 类 - 训练客户端核心类
# ============================================================================
# 原理说明:
# TrainingClient 采用请求 - 响应 (Request-Response) 模式与服务器通信。
# 每个请求都有唯一的 request_id，用于匹配请求和响应。
#
# 请求格式:
# {
#     "command": "create_task",     # 命令类型
#     "request_id": "1234567890_1", # 唯一请求 ID (时间戳_计数器)
#     "timestamp": 1234567890.123,  # 时间戳
#     "params": {...}               # 命令参数 (可选)
# }
#
# 响应格式:
# {
#     "code": 100,       # 响应码 (100=成功，其他=失败)
#     "message": "...",  # 响应消息
#     "data": {...}      # 响应数据 (可选)
# }
#
# 响应码说明:
#     100 - 成功 (Success)
#     200 - 部分成功
#     400 - 请求错误 (参数无效)
#     404 - 未找到 (任务不存在)
#     500 - 服务器内部错误
# ============================================================================

class TrainingClient:
    """
    训练客户端类 - 与远程训练服务器通信的核心类

    提供训练任务的全生命周期管理:
    - 连接管理：connect(), disconnect()
    - 任务管理：create_task(), start_training(), stop_training(), delete_task()
    - 状态监控：get_task_status(), get_progress(), monitor_training()
    - 工具方法：ping(), list_tasks()

    属性:
        host (str): 服务器地址，默认 "127.0.0.1"
        port (int): 服务器端口，默认 8888
        socket: TCP Socket 对象
        connected (bool): 连接状态标志
        request_counter (int): 请求计数器，用于生成唯一 ID
        callbacks (Dict): 回调函数字典 (保留用于未来扩展)

    线程安全:
        本类不是线程安全的。如果在多线程环境中使用，
        需要外部加锁或使用同步机制。

    使用示例:
        client = TrainingClient(host="127.0.0.1", port=8888)

        # 连接并测试
        if client.connect():
            client.ping()

            # 创建训练任务
            params = {"epochs": 50, "batch_size": 32}
            task_id = client.create_task(params)

            # 启动并监控
            client.start_training(task_id)
            client.monitor_training(task_id)

            client.disconnect()
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8888):
        """
        初始化训练客户端

        Args:
            host: 训练服务器地址，默认本地地址
            port: 训练服务器端口，默认 8888

        示例:
            # 使用默认配置 (本地服务器)
            client = TrainingClient()

            # 连接远程服务器
            client = TrainingClient(host="192.168.1.100", port=8888)
        """
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.request_counter = 0
        self.callbacks: Dict[str, Callable] = {}
        self._socket_lock = threading.RLock()

    def connect(self) -> bool:
        """
        连接到训练服务器

        原理:
            1. 创建 TCP Socket (AF_INET=IPv4, SOCK_STREAM=TCP)
            2. 发起三次握手连接到指定地址
            3. 连接成功后设置标志位

        Returns:
            bool: 连接成功返回 True，失败返回 False

        异常处理:
            - ConnectionRefusedError: 服务器未运行或端口被防火墙阻止
            - OSError: 网络不可达或地址无效

        示例:
            client = TrainingClient()
            if client.connect():
                print("连接成功!")
            else:
                print("连接失败，请检查服务器是否运行")
        """
        with self._socket_lock:
            # 如果已有 socket，先关闭它（防止资源泄漏）
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None

            # 重置连接标志
            self.connected = False

            try:
                # 创建 IPv4 TCP Socket
                # AF_INET: 使用 IPv4 地址族
                # SOCK_STREAM: 使用 TCP 协议 (流式套接字)
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                # 发起连接 (TCP 三次握手)
                self.socket.connect((self.host, self.port))

                # 设置连接标志
                self.connected = True
                print(f"已连接到服务器 {self.host}:{self.port}")
                return True
            except Exception as e:
                # 记录错误并清理资源
                print(f"连接失败：{e}")
                if self.socket:
                    try:
                        self.socket.close()
                    except:
                        pass
                    self.socket = None
                self.connected = False
                return False

    def disconnect(self):
        """
        断开与服务器的连接

        原理:
            1. 关闭 Socket，发送 FIN 包 (TCP 四次挥手)
            2. 释放本地资源
            3. 重置连接状态

        注意:
            - 该方法会优雅地关闭连接，即使 Socket 已经损坏也不会抛出异常
            - 断开后如需重新连接，需要调用 connect() 方法

        示例:
            client.disconnect()
            print("已断开连接")
        """
        with self._socket_lock:
            # 先重置连接标志，防止其他线程继续使用
            self.connected = False

            if self.socket:
                try:
                    # 尝试优雅地关闭 socket
                    # 1. 先关闭写端，发送 FIN 包
                    self.socket.shutdown(socket.SHUT_RDWR)
                except (OSError, socket.error):
                    # socket 可能已关闭或从未连接
                    pass
                except Exception:
                    pass

                try:
                    # 2. 关闭 socket 文件描述符
                    self.socket.close()
                except:
                    pass  # 忽略关闭错误

            self.socket = None

    def send_request(self, command: str, data: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        发送请求并获取响应 (核心通信方法)

        这是所有其他方法的基础，实现了请求 - 响应模式的完整流程:

        发送流程:
            1. 生成唯一请求 ID (时间戳 + 计数器)
            2. 构造请求字典
            3. 序列化为 JSON 字符串
            4. 使用 MessageProtocol.pack() 打包
            5. 通过 Socket 发送

        接收流程:
            1. 使用 MessageProtocol.receive() 接收响应
            2. 解析 JSON 字符串
            3. 返回 Python 字典

        Args:
            command: 命令类型，如 "ping", "create_task", "start_training" 等
            data: 额外参数，将合并到请求字典中

        Returns:
            响应字典，包含 code, message, data 等字段
            失败时返回 None

        请求 ID 说明:
            格式: "{timestamp}_{counter}"
            例如："1710123456.789_1"

            作用:
            - 唯一标识每个请求
            - 用于请求 - 响应匹配 (未来扩展)
            - 便于日志追踪和调试

        示例:
            response = client.send_request("ping")
            if response and response.get("code") == 100:
                print("服务器响应正常")
        """
        with self._socket_lock:
            # 检查连接状态
            if not self.connected or not self.socket:
                logger.warning("[TrainingClient] 未连接到服务器")
                return None

            # 生成唯一请求 ID
            # 格式：时间戳_计数器 (例如："1710123456.789_1")
            self.request_counter += 1
            request_id = f"{time.time()}_{self.request_counter}"

            # 构造请求字典
            request = {
                "command": command,
                "request_id": request_id,
                "timestamp": time.time()
            }

            # 合并额外参数
            if data:
                request.update(data)

            try:
                # 将请求字典序列化为 JSON 字符串
                # ensure_ascii=False 保证中文字符正常显示
                message = json.dumps(request, ensure_ascii=False)

                # 使用协议打包并发送
                # sendall() 确保发送所有数据，而不是部分发送
                self.socket.sendall(MessageProtocol.pack(message))

                # 接收响应 (超时 60 秒)
                # 60 秒是一个合理的值，适用于大多数训练操作
                response_str = MessageProtocol.receive(self.socket, timeout=60)
                if not response_str:
                    logger.warning(f"[TrainingClient] 接收响应超时 (command={command})")
                    # 超时意味着连接可能已损坏，需要清理
                    self._invalidate_connection()
                    return None

                # 解析 JSON 响应
                response = json.loads(response_str)
                logger.debug(f"[TrainingClient] 收到响应: {response}")
                return response

            except json.JSONDecodeError as e:
                # JSON 解析失败
                logger.error(f"[TrainingClient] 响应 JSON 解析失败：{e}")
                return None
            except Exception as e:
                # 其他通信错误
                logger.error(f"[TrainingClient] 发送请求失败 (command={command}): {e}")
                # 发送或接收异常，连接已损坏
                self._invalidate_connection()
                return None

    def ping(self, timeout: float = 5.0) -> bool:
        """
        测试与服务器的连接

        原理:
            发送一个简单的 "ping" 命令，等待服务器返回 "pong" 响应。
            这是检查服务器是否在线、网络是否通畅的最简单方法。

        Args:
            timeout: 超时时间（秒），默认 5 秒

        Returns:
            bool: 服务器正常响应返回 True，否则返回 False

        使用场景:
            - 连接后立即调用，验证服务器可用性
            - 定期检查连接状态
            - 执行重要操作前的预检查

        示例:
            client.connect()
            if client.ping():
                print("服务器在线，可以开始操作")
            else:
                print("服务器无响应")
        """
        print(f"[TrainingClient] 发送 ping 请求，超时: {timeout}秒")
        response = self.send_request_with_timeout("ping", timeout=timeout)
        if response and response.get("code") == 100:
            # 服务器返回当前时间，可用于时钟同步参考
            server_time = response.get("server_time", "未知")
            print(f"[TrainingClient] ping 成功，服务器时间：{server_time}")
            return True
        print(f"[TrainingClient] ping 失败，响应: {response}")
        return False

    def send_request_with_timeout(self, command: str, data: Dict[str, Any] = None, timeout: float = 60) -> Optional[Dict[str, Any]]:
        """
        发送请求并获取响应（带自定义超时）

        Args:
            command: 命令类型
            data: 额外参数
            timeout: 超时时间（秒）

        Returns:
            响应字典，失败时返回 None
        """
        with self._socket_lock:
            # 检查连接状态
            if not self.connected or not self.socket:
                print("[TrainingClient] 未连接到服务器")
                return None

            # 生成唯一请求 ID
            self.request_counter += 1
            request_id = f"{time.time()}_{self.request_counter}"

            # 构造请求字典
            request = {
                "command": command,
                "request_id": request_id,
                "timestamp": time.time()
            }

            # 合并额外参数
            if data:
                request.update(data)

            try:
                # 将请求字典序列化为 JSON 字符串
                message = json.dumps(request, ensure_ascii=False)
                print(f"[TrainingClient] 发送请求: {message[:100]}...")

                # 使用协议打包并发送
                packed_data = MessageProtocol.pack(message)
                print(f"[TrainingClient] 打包后数据长度: {len(packed_data)} 字节")
                self.socket.sendall(packed_data)
                print(f"[TrainingClient] 数据已发送，等待响应...")

                # 接收响应（使用指定超时）
                response_str = MessageProtocol.receive(self.socket, timeout=timeout)
                if not response_str:
                    print(f"[TrainingClient] 接收响应超时（{timeout}秒）")
                    # 超时意味着连接可能已损坏，需要清理
                    self._invalidate_connection()
                    return None

                print(f"[TrainingClient] 收到响应: {response_str[:100]}...")

                # 解析 JSON 响应
                response = json.loads(response_str)
                return response

            except json.JSONDecodeError as e:
                print(f"[TrainingClient] 响应 JSON 解析失败：{e}")
                # JSON 解析失败不一定意味着连接损坏
                return None
            except Exception as e:
                print(f"[TrainingClient] 发送请求失败：{e}")
                # 发送或接收异常，连接已损坏
                self._invalidate_connection()
                return None

    def _invalidate_connection(self):
        """
        使连接无效并清理资源
        
        当检测到连接已损坏（超时、异常等）时调用此方法，
        确保 socket 被正确关闭，避免资源泄漏。
        """
        with self._socket_lock:
            self.connected = False
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
            self.socket = None

    def create_task(self, params: Dict[str, Any]) -> Optional[str]:
        """
        创建新的训练任务

        原理:
            向服务器发送训练参数，服务器创建任务并返回唯一任务 ID。
            任务 ID 是后续所有操作 (启动、停止、查询) 的标识符。

        Args:
            params: 训练参数字典，包含:
                - model_type (str): 模型类型，如 "detect", "segment", "classify"
                - image_size (int): 输入图像尺寸，默认 640
                - dataset (str): 数据集路径，默认 "data"
                - epochs (int): 训练轮次，默认 50
                - batch_size (int): 批次大小，默认 32
                - learning_rate (float): 学习率，默认 0.001
                - trainset_ratio (float): 训练集比例，默认 0.9

        Returns:
            str: 任务 ID (成功时)
            None: 失败时

        参数详解:
            model_type:
                - "detect": 目标检测 (YOLO 系列)
                - "segment": 语义分割
                - "classify": 图像分类

            epochs (训练轮次):
                - 太少 (<30): 模型可能欠拟合
                - 太多 (>200): 可能过拟合，训练时间过长
                - 建议：30-100，根据数据集大小调整

            batch_size (批次大小):
                - 太小 (<8): 训练不稳定
                - 太大 (>64): 内存需求高
                - 建议：16/32/64，根据 GPU 显存调整

            learning_rate (学习率):
                - 太小 (<0.0001): 收敛慢
                - 太大 (>0.01): 可能不收敛
                - 建议：0.001-0.005

        示例:
            params = {
                "model_type": "detect",
                "epochs": 50,
                "batch_size": 32,
                "learning_rate": 0.001
            }
            task_id = client.create_task(params)
            if task_id:
                print(f"任务创建成功：{task_id}")
        """
        response = self.send_request("create_task", {"params": params})

        if response and response.get("code") == 100:
            # 从响应数据中提取任务 ID
            task_id = response.get("data", {}).get("task_id")
            print(f"任务创建成功，ID: {task_id}")
            return task_id
        else:
            # 提取错误信息
            error_msg = response.get("message", "未知错误") if response else "无响应"
            print(f"任务创建失败：{error_msg}")
            return None

    def start_training(self, task_id: str) -> bool:
        """
        启动指定的训练任务

        原理:
            任务创建后处于"pending"状态，需要调用此方法开始训练。
            服务器收到命令后启动训练线程，开始迭代训练过程。

        Args:
            task_id: 任务 ID，由 create_task() 返回

        Returns:
            bool: 启动成功返回 True，失败返回 False

        注意:
            - 同一任务不能重复启动
            - 任务必须先创建才能启动

        示例:
            task_id = client.create_task(params)
            if task_id:
                if client.start_training(task_id):
                    print("训练已启动")
        """
        response = self.send_request("start_training", {"task_id": task_id})

        if response and response.get("code") == 100:
            print(f"训练任务 {task_id} 已启动")
            return True
        else:
            error_msg = response.get("message", "未知错误") if response else "无响应"
            print(f"启动训练失败：{error_msg}")
            return False

    def stop_training(self, task_id: str) -> bool:
        """
        停止正在运行的训练任务

        原理:
            向服务器发送停止信号，服务器设置停止标志位。
            训练线程在下一次迭代时检查标志位并优雅退出。
            这是一种"协作式"停止，不是强制终止。

        Args:
            task_id: 任务 ID

        Returns:
            bool: 停止成功返回 True，失败返回 False

        注意:
            - 训练停止需要一定时间 (等待当前迭代完成)
            - 已完成的训练无法停止

        示例:
            # 用户按下 Ctrl+C 时
            client.stop_training(task_id)
        """
        response = self.send_request("stop_training", {"task_id": task_id})

        if response and response.get("code") == 100:
            print(f"训练任务 {task_id} 已停止")
            return True
        else:
            error_msg = response.get("message", "未知错误") if response else "无响应"
            print(f"停止训练失败：{error_msg}")
            return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态信息

        返回的状态包含任务的完整信息:
        - status: 任务状态 ("pending", "running", "completed", "failed", "stopped")
        - progress: 总体进度 (0-1 之间的小数)
        - start_time: 开始时间 (时间戳)
        - params: 训练参数
        - metrics: 性能指标

        Args:
            task_id: 任务 ID

        Returns:
            dict: 任务状态字典，失败时返回 None

        状态说明:
            "pending":   已创建但未启动
            "running":   正在训练
            "completed": 训练完成
            "failed":    训练失败
            "stopped":   手动停止

        示例:
            status = client.get_task_status(task_id)
            if status:
                print(f"状态：{status['status']}")
                print(f"进度：{status['progress']*100:.1f}%")
        """
        response = self.send_request("get_task_status", {"task_id": task_id})

        if response and response.get("code") == 100:
            return response.get("data")
        else:
            error_msg = response.get("message", "未知错误") if response else "无响应"
            logger.warning(f"[TrainingClient] 获取任务状态失败：{error_msg}")
            return None

    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取训练进度详情

        返回的训练进度包含详细的训练指标:
        - epoch: 当前轮次
        - total_epochs: 总轮次
        - loss: 训练损失
        - accuracy: 训练准确率
        - val_loss: 验证损失
        - val_accuracy: 验证准确率
        - type: 模型类型

        Args:
            task_id: 任务 ID

        Returns:
            dict: 训练进度字典，包含 progress 字段

        与 get_task_status 的区别:
            - get_task_status: 返回任务整体状态 (状态、进度、时间等)
            - get_progress: 返回详细训练指标 (loss、accuracy 等)

        示例:
            progress = client.get_progress(task_id)
            if progress and "progress" in progress:
                p = progress["progress"]
                print(f"轮次 {p['epoch']}/{p['total_epochs']}")
                print(f"损失：{p['loss']:.4f}")
                print(f"准确率：{p['accuracy']:.4f}")
        """
        response = self.send_request("get_train_status", {
            "task_id": task_id,
        })

        if response and response.get("code") == 100:
            return response.get("data")
        else:
            error_msg = response.get("message", "未知错误") if response else "无响应"
            print(f"获取进度失败：{error_msg}")
            return None

    def long_poll_progress(self, task_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        长轮询获取进度更新

        原理:
            普通轮询：客户端频繁请求，服务器立即返回 (可能没有更新)
            长轮询：服务器有更新时才返回，减少无效请求

            长轮询的优势:
            - 减少网络流量
            - 降低服务器负载
            - 更快的更新响应

        Args:
            task_id: 任务 ID
            timeout: 等待超时时间 (秒)，默认 30 秒

        Returns:
            dict: 训练进度字典，超时或失败时返回 None

        注意:
            - 服务器需要支持长轮询功能
            - timeout 时间内无更新会返回超时

        示例:
            # 等待最多 30 秒，有更新立即返回
            progress = client.long_poll_progress(task_id, timeout=30)
        """
        response = self.send_request("get_long_train_status", {
            "task_id": task_id,
            "timeout": timeout
        })

        if response and response.get("code") == 100:
            return response.get("data")
        else:
            error_msg = response.get("message", "未知错误") if response else "无响应"
            print(f"长轮询失败：{error_msg}")
            return None

    def list_tasks(self) -> Optional[Dict[str, Any]]:
        """
        列出所有训练任务

        Returns:
            dict: 包含 tasks 列表的字典，每个任务包含:
                - task_id: 任务 ID
                - status: 状态
                - progress: 进度
                - params: 参数
                - start_time: 开始时间
            失败时返回 None

        示例:
            tasks = client.list_tasks()
            if tasks:
                for task in tasks.get("tasks", []):
                    print(f"任务 {task['task_id']}: {task['status']}")
        """
        response = self.send_request("list_tasks")

        if response and response.get("code") == 100:
            return response.get("data")
        else:
            error_msg = response.get("message", "未知错误") if response else "无响应"
            print(f"列出任务失败：{error_msg}")
            return None

    def delete_task(self, task_id: str) -> bool:
        """
        删除指定的训练任务

        原理:
            从服务器的任务列表中移除任务，释放相关资源。
            删除后无法恢复，需要谨慎操作。

        Args:
            task_id: 任务 ID

        Returns:
            bool: 删除成功返回 True，失败返回 False

        注意:
            - 运行中的任务无法删除
            - 删除操作不可恢复

        示例:
            if client.delete_task(task_id):
                print("任务已删除")
        """
        response = self.send_request("delete_task", {"task_id": task_id})

        if response and response.get("code") == 100:
            print(f"任务 {task_id} 已删除")
            return True
        else:
            error_msg = response.get("message", "未知错误") if response else "无响应"
            print(f"删除任务失败：{error_msg}")
            return False

    def monitor_training(self, task_id: str, poll_interval: float = 2.0, callback: Callable = None):
        """
        持续监控训练进度 (阻塞方法)

        原理:
            在一个循环中定期查询训练状态和进度，
            格式化输出训练信息，直到训练完成或出错。

        监控循环:
            1. 获取任务状态
            2. 获取训练进度 (epoch, loss, accuracy)
            3. 格式化输出
            4. 检查是否完成
            5. 等待指定时间后继续

        Args:
            task_id: 要监控的任务 ID
            poll_interval: 轮询间隔 (秒)，默认 2 秒
            callback: 回调函数，接收 (epoch, total_epochs, loss, accuracy, progress_data) 参数

        输出格式:
            [14:30:25] 轮次 1/50 | 损失：0.5234 | 准确率：0.7123
            [14:30:45] 轮次 2/50 | 损失：0.4521 | 准确率：0.7856
            ...

        注意:
            - 该方法是阻塞的，会一直运行直到训练完成
            - 按 Ctrl+C 可以中断监控
            - poll_interval 太小会增加服务器负载

        示例:
            client.start_training(task_id)
            client.monitor_training(task_id, poll_interval=2)  # 每 2 秒刷新一次
        """
        logger.info(f"[TrainingClient] 开始监控训练任务：{task_id}")

        try:
            while True:
                # 获取任务状态
                status_data = self.get_task_status(task_id)
                if not status_data:
                    logger.warning("[TrainingClient] 获取状态失败")
                    break

                status = status_data.get("status", "unknown")
                progress = status_data.get("progress", 0) * 100

                # 获取详细训练进度
                logger.debug(f"[TrainingClient] status_data: {status_data}")
                progress_data = self.get_progress(task_id)
                logger.debug(f"[TrainingClient] progress_data: {progress_data}")

                if progress_data:
                    progress_list = progress_data.get("progress", {})
                    if progress_list:
                        prog_type = progress_list.get("type", "detect")

                        epoch = progress_list.get("epoch", 0)
                        total_epochs = progress_list.get("total_epochs", 1)
                        loss = progress_list.get("loss", 0)
                        accuracy = progress_list.get("accuracy", 0)
                        val_loss = progress_list.get("val_loss", 0)
                        val_accuracy = progress_list.get("val_accuracy", 0)
                        ts = datetime.fromtimestamp(progress_list.get("timestamp", time.time()))

                        logger.info(f"[TrainingClient] [{ts.strftime('%H:%M:%S')}] "
                                    f"轮次 {epoch}/{total_epochs} | "
                                    f"损失：{loss:.4f} | "
                                    f"准确率：{accuracy:.4f}")

                        # 调用回调函数更新 UI
                        if callback:
                            try:
                                callback(epoch, total_epochs, loss, accuracy, progress_data)
                                logger.debug(f"[TrainingClient] 回调函数执行成功：epoch={epoch}, total_epochs={total_epochs}")
                            except Exception as e:
                                logger.warning(f"[TrainingClient] 回调函数执行失败：{e}")
                        
                        # 检查是否完成 - 只有当 epoch == total_epochs 时才确认完成
                        logger.debug(f"[TrainingClient] 检查完成条件：epoch={epoch}, total_epochs={total_epochs}, condition={epoch == total_epochs}")
                        if epoch == total_epochs:
                            logger.info(f"[TrainingClient] 训练完成 (epoch={epoch} == total_epochs={total_epochs})")
                            return
                    else:
                        logger.warning("[TrainingClient] progress is null")
                        # progress 为空时，不以 completed 状态直接判定完成，继续等待有效轮次
                        if status_data and status_data.get("status") in ["failed", "stopped"]:
                            logger.info(f"[TrainingClient] 任务状态为 {status_data.get('status')}，结束监控")
                            return
                else:
                    logger.warning("[TrainingClient] progress_data 为 None")
                    # 获取不到进度时，不以 completed 状态直接判定完成，继续等待有效轮次
                    if status_data and status_data.get("status") in ["failed", "stopped"]:
                        logger.info(f"[TrainingClient] 任务状态为 {status_data.get('status')}，结束监控")
                        return

                # 等待下一次轮询
                time.sleep(poll_interval)

        except KeyboardInterrupt:
            # 用户按下 Ctrl+C
            logger.info("[TrainingClient] 监控被用户中断")
        except Exception as e:
            # 其他异常
            logger.error(f"[TrainingClient] 监控出错：{e}")

        logger.info("[TrainingClient] 监控结束")


# ============================================================================
# InteractiveClient 类 - 交互式命令行客户端
# ============================================================================
# 原理说明:
# InteractiveClient 是 TrainingClient 的高层封装，提供:
# 1. 菜单驱动的用户界面
# 2. 交互式参数输入
# 3. 自动任务管理 (记录当前任务 ID)
# 4. 友好的错误提示
#
# 使用场景:
# - 快速测试训练功能
# - 不熟悉编程的用户
# - 命令行环境下的交互操作
# ============================================================================

class InteractiveClient:
    """
    交互式命令行客户端 - TrainingClient 的友好封装

    提供菜单驱动的用户界面，用户可以通过键盘输入选择操作，
    无需编写代码即可完成训练任务管理。

    功能菜单:
        1. 创建训练任务 - 输入参数创建新任务
        2. 开始训练 - 启动已创建的任务
        3. 监控训练进度 - 实时查看训练状态
        4. 停止训练 - 手动停止正在运行的训练
        5. 查看任务状态 - 查看任务的详细信息
        6. 列出所有任务 - 显示所有训练任务列表
        7. 删除任务 - 删除指定任务
        8. 退出 - 断开连接并退出程序

    属性:
        client (TrainingClient): 底层训练客户端
        current_task (str): 当前操作的任务 ID (自动记录)

    使用示例:
        client = InteractiveClient()
        client.run()
        # 然后按照菜单提示操作
    """

    def __init__(self, host="127.0.0.1", port=8888):
        """
        初始化交互式客户端

        Args:
            host: 服务器地址
            port: 服务器端口
        """
        self.client = TrainingClient(host, port)
        self.current_task = None  # 记录当前任务 ID，方便后续操作

    def run(self):
        """
        运行交互式客户端 (主循环)

        执行流程:
            1. 连接服务器
            2. 测试连接 (ping)
            3. 显示主菜单
            4. 等待用户输入
            5. 执行对应操作
            6. 返回步骤 3 (循环)
            7. 用户选择退出时断开连接

        异常处理:
            - KeyboardInterrupt: 用户按 Ctrl+C 优雅退出
            - Exception: 捕获并显示错误，继续运行
        """
        print("AI 模型训练客户端")
        print("=" * 50)

        # 连接服务器
        if not self.client.connect():
            print("连接服务器失败，退出")
            return

        # 测试连接
        if not self.client.ping():
            print("服务器无响应，退出")
            return

        # 主循环
        while True:
            print("\n" + "=" * 50)
            print("1. 创建训练任务")
            print("2. 开始训练")
            print("3. 监控训练进度")
            print("4. 停止训练")
            print("5. 查看任务状态")
            print("6. 列出所有任务")
            print("7. 删除任务")
            print("8. 退出")

            try:
                choice = input("\n请选择操作 (1-8): ").strip()

                if choice == "1":
                    self.create_task_interactive()
                elif choice == "2":
                    self.start_training_interactive()
                elif choice == "3":
                    self.monitor_training_interactive()
                elif choice == "4":
                    self.stop_training_interactive()
                elif choice == "5":
                    self.show_status_interactive()
                elif choice == "6":
                    self.list_tasks_interactive()
                elif choice == "7":
                    self.delete_task_interactive()
                elif choice == "8":
                    print("再见！")
                    break
                else:
                    print("无效选择，请重新输入")

            except KeyboardInterrupt:
                print("\n程序被中断")
                break
            except Exception as e:
                print(f"操作失败：{e}")

        # 断开连接
        self.client.disconnect()

    def create_task_interactive(self):
        """
        交互式创建训练任务

        通过命令行提示用户输入各项参数，
        然后调用 TrainingClient.create_task() 创建任务。
        """
        print("\n--- 创建训练任务 ---")

        # 基本参数
        model_type = input("模型类型 (默认：detect): ").strip() or "detect"
        image_size = input("训练轮次 (默认：640): ").strip()
        image_size = int(image_size) if image_size else 640

        dataset = input("数据集 (默认：data): ").strip() or "data"

        # 训练参数
        epochs = input("训练轮次 (默认：50): ").strip()
        epochs = int(epochs) if epochs else 50

        batch_size = input("批次大小 (默认：32): ").strip()
        batch_size = int(batch_size) if batch_size else 32

        learning_rate = input("学习率 (默认：0.001): ").strip()
        learning_rate = float(learning_rate) if learning_rate else 0.001

        trainset_ratio = input("训练集比例 (默认：0.9): ").strip()
        trainset_ratio = float(trainset_ratio) if trainset_ratio else 0.9

        # 构建参数字典
        params = {
            "model_type": model_type,
            "image_size": image_size,
            "dataset": dataset,
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "trainset_ratio": trainset_ratio
        }

        # 创建任务
        task_id = self.client.create_task(params)
        if task_id:
            self.current_task = task_id  # 记录当前任务
            print(f"当前任务已设置为：{task_id}")

    def start_training_interactive(self):
        """
        交互式启动训练

        如果有当前任务 (刚创建的)，直接使用；
        否则提示用户输入任务 ID。
        """
        print("\n--- 开始训练 ---")

        if not self.current_task:
            task_id = input("请输入任务 ID: ").strip()
            if not task_id:
                print("需要任务 ID")
                return
        else:
            task_id = self.current_task
            print(f"使用当前任务：{task_id}")

        if self.client.start_training(task_id):
            self.current_task = task_id
            print("训练已启动")

    def monitor_training_interactive(self):
        """
        交互式监控训练进度
        """
        print("\n--- 监控训练进度 ---")

        if not self.current_task:
            task_id = input("请输入任务 ID: ").strip()
            if not task_id:
                print("需要任务 ID")
                return
        else:
            task_id = self.current_task
            print(f"监控当前任务：{task_id}")

        poll_interval = input("轮询间隔 (秒，默认 2): ").strip()
        poll_interval = float(poll_interval) if poll_interval else 2.0

        self.client.monitor_training(task_id, poll_interval)

    def stop_training_interactive(self):
        """
        交互式停止训练
        """
        print("\n--- 停止训练 ---")

        task_id = input("请输入任务 ID: ").strip()
        if not task_id:
            print("需要任务 ID")
            return

        if self.client.stop_training(task_id):
            print("停止命令已发送")

    def show_status_interactive(self):
        """
        交互式查看任务状态

        显示任务的完整详细信息，包括:
        - 任务状态
        - 训练参数
        - 性能指标
        - 时间信息
        """
        print("\n--- 查看任务状态 ---")

        task_id = input("请输入任务 ID: ").strip()

        data = self.client.get_task_status(task_id)
        print("\n任务详情:")
        for key, value in data.items():
            if isinstance(value, dict):
                # 嵌套字典格式化输出
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            elif isinstance(value, list) and len(value) > 5:
                # 长列表只显示首尾
                print(f"  {key}: [{value[0]}, {value[1]}, ..., {value[-1]}] ({len(value)} items)")
            else:
                print(f"  {key}: {value}")

    def list_tasks_interactive(self):
        """
        交互式列出所有任务

        显示所有训练任务的摘要信息:
        - 任务 ID
        - 模型类型
        - 状态和进度
        - 训练轮次
        - 创建时间
        """
        print("\n--- 列出所有任务 ---")

        data = self.client.list_tasks()
        if data:
            tasks = data.get("tasks", [])
            print(f"\n找到 {len(tasks)} 个任务:")

            for task in tasks:
                task_id = task.get("task_id", "unknown")
                status = task.get("status", "unknown")
                progress = task.get("progress", 0) * 100
                model_type = task.get("params", {}).get("model_type", "unknown")
                epochs = task.get("params", {}).get("epochs", 0)
                created = datetime.fromtimestamp(task.get("start_time", 0))

                print(f"\n  ID: {task_id}")
                print(f"  模型：{model_type}")
                print(f"  状态：{status} ({progress:.1f}%)")
                print(f"  轮次：{epochs}")
                print(f"  创建时间：{created.strftime('%Y-%m-%d %H:%M:%S')}")

    def delete_task_interactive(self):
        """
        交互式删除任务

        删除前要求用户确认，防止误操作。
        """
        print("\n--- 删除任务 ---")

        task_id = input("请输入要删除的任务 ID: ").strip()
        if not task_id:
            print("需要任务 ID")
            return

        # 确认删除
        confirm = input(f"确认删除任务 {task_id}? (y/n): ").strip().lower()
        if confirm == 'y':
            if self.client.delete_task(task_id):
                # 如果删除的是当前任务，清空记录
                if self.current_task == task_id:
                    self.current_task = None
                print("任务已删除")
        else:
            print("取消删除")


# ============================================================================
# 命令行工具入口
# ============================================================================

def main():
    """
    命令行工具入口函数

    支持两种运行模式:
    1. 交互模式 (默认): 显示菜单，等待用户输入
    2. 命令行模式 (已注释): 直接执行指定命令

    命令行参数:
        --host: 服务器地址，默认 "127.0.0.1"
        --port: 服务器端口，默认 8888
        --interactive: 启用交互模式
        --command: 直接执行命令 (已注释)
        --task-id: 任务 ID (已注释)
        --params: 训练参数 JSON (已注释)

    使用示例:
        # 交互模式 (默认)
        python training_client.py

        # 指定服务器
        python training_client.py --host 192.168.1.100 --port 8888

        # 显式启用交互模式
        python training_client.py --interactive
    """
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="AI 模型训练客户端")
    parser.add_argument("--host", default="127.0.0.1", help="服务器地址")
    parser.add_argument("--port", type=int, default=8888, help="服务器端口")
    parser.add_argument("--interactive", action="store_true", help="交互模式")
    parser.add_argument("--command", help="直接执行命令")
    parser.add_argument("--task-id", help="任务 ID")
    parser.add_argument("--params", help="训练参数 JSON")

    args = parser.parse_args()

    if args.interactive:
        # 交互模式
        client = InteractiveClient(args.host, args.port)
        client.run()
    # 命令行模式已注释，如需要可以取消注释
    # elif args.command:
    #     # 命令行模式
    #     client = TrainingClient(args.host, args.port)

    #     if not client.connect():
    #         print("连接失败")
    #         return

    #     if args.command == "ping":
    #         client.ping()
    #     elif args.command == "create":
    #         if not args.params:
    #             print("需要参数 --params")
    #             return
    #         params = json.loads(args.params)
    #         client.create_task(params)
    #     elif args.command == "start":
    #         if not args.task_id:
    #             print("需要参数 --task-id")
    #             return
    #         client.start_training(args.task_id)
    #     elif args.command == "stop":
    #         if not args.task_id:
    #             print("需要参数 --task-id")
    #             return
    #         client.stop_training(args.task_id)
    #     elif args.command == "status":
    #         task_id = args.task_id if args.task_id else "all"
    #         data = client.get_task_status(task_id)
    #         if data:
    #             print(json.dumps(data, indent=2, ensure_ascii=False))
    #     elif args.command == "monitor":
    #         if not args.task_id:
    #             print("需要参数 --task-id")
    #             return
    #         client.monitor_training(args.task_id)
    #     elif args.command == "list":
    #         data = client.list_tasks()
    #         if data:
    #             print(json.dumps(data, indent=2, ensure_ascii=False))
    #     elif args.command == "delete":
    #         if not args.task_id:
    #             print("需要参数 --task-id")
    #             return
    #         client.delete_task(args.task_id)
    #     else:
    #         print(f"未知命令：{args.command}")

    #     client.disconnect()
    else:
        # 默认交互模式
        client = InteractiveClient(args.host, args.port)
        client.run()


if __name__ == "__main__":
    main()
