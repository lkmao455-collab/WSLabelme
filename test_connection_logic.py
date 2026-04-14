#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试训练管理dock的连接按钮逻辑
"""

import sys
import time
import socket
import subprocess
import threading
from unittest.mock import MagicMock, patch

sys.path.insert(0, r'E:\shangweiji\WSLabelme\labelme')

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt

# 测试用例1: 模拟快速连接场景
def test_fast_connection():
    """测试连接非常快的情况（信号可能在事件循环前发出）"""
    print("=" * 60)
    print("测试用例1: 快速连接场景")
    print("=" * 60)

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    from labelme.training_client_manager import TrainingClientManager

    manager = TrainingClientManager("127.0.0.1", 8888)

    connected_received = [False]
    connection_error_received = [False]
    connect_result = [None]

    def on_connected(success):
        print(f"  -> connected 信号接收: success={success}")
        connected_received[0] = True
        connect_result[0] = success

    def on_error(msg):
        print(f"  -> connection_error 信号接收: {msg}")
        connection_error_received[0] = True
        connect_result[0] = False

    manager.connected.connect(on_connected)
    manager.connection_error.connect(on_error)

    # 模拟快速连接: 先发出信号再进入事件循环
    print("  发起连接...")
    manager.connect_server("127.0.0.1", 8888)

    # 等待2秒让连接线程执行
    time.sleep(2)

    # 检查是否收到信号
    print(f"  2秒后 - connected_received: {connected_received[0]}")
    print(f"  2秒后 - connection_error_received: {connection_error_received[0]}")
    print(f"  2秒后 - is_connected: {manager.is_connected()}")

    # 如果服务器没有运行，应该会收到 connection_error
    if not connected_received[0] and not connection_error_received[0]:
        print("  ⚠️ 警告: 2秒后仍未收到任何信号！可能存在信号丢失问题")
        print("  继续等待3秒...")
        time.sleep(3)
        print(f"  5秒后 - connected_received: {connected_received[0]}")
        print(f"  5秒后 - connection_error_received: {connection_error_received[0]}")

    print()
    return connect_result[0] if connect_result[0] is not None else False


# 测试用例2: 测试端口检测和连接协同
def test_port_detection_connection_race():
    """测试端口检测和连接之间的竞争条件"""
    print("=" * 60)
    print("测试用例2: 端口检测与连接竞争条件")
    print("=" * 60)

    # 模拟 unified_training_widget.py 中的 _ensure_server_running 逻辑
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    from labelme.training_client_manager import TrainingClientManager

    # 问题分析:
    # 1. try_manager_connect() 调用 connect_server()
    # 2. connect_server() 启动后台线程执行连接
    # 3. timer_check 启动检查连接结果
    # 4. 但如果连接线程执行很快，在 timer_check 启动前就已经发出信号
    #    那么 on_temp_connected 就收不到信号

    print("  问题分析:")
    print("  1. try_manager_connect() 调用 connect_server()")
    print("  2. connect_server() 启动后台线程执行连接")
    print("  3. timer_check 启动检查 connect_result 变量")
    print("  4. 如果信号在 timer_check 启动前发出，on_temp_connected 收不到信号")
    print()

    return True


# 测试用例3: 测试信号顺序
def test_signal_order():
    """测试信号发出顺序"""
    print("=" * 60)
    print("测试用例3: 信号发出顺序")
    print("=" * 60)

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    from labelme.training_client_manager import TrainingClientManager

    manager = TrainingClientManager("127.0.0.1", 8888)

    signal_order = []

    def on_connected(success):
        signal_order.append(f"connected({success})")
        print(f"  -> connected 信号接收: success={success}")

    def on_error(msg):
        signal_order.append(f"connection_error({msg})")
        print(f"  -> connection_error 信号接收: {msg}")

    manager.connected.connect(on_connected)
    manager.connection_error.connect(on_error)

    print("  发起连接...")
    manager.connect_server("127.0.0.1", 8888)

    # 等待3秒
    time.sleep(3)

    print(f"  信号顺序: {signal_order}")
    print(f"  is_connected: {manager.is_connected()}")
    print()

    return signal_order


# 测试用例4: 模拟已运行服务器的检测
def test_server_already_running_detection():
    """测试检测已运行服务器并连接的逻辑"""
    print("=" * 60)
    print("测试用例4: 服务器已运行检测逻辑")
    print("=" * 60)

    # 问题: _ensure_server_running 中检测端口可用后调用 try_manager_connect
    # 然后进入事件循环等待 connect_result
    # 但如果 connect_server 是异步的，信号可能在事件循环启动前发出

    print("  当前逻辑问题:")
    print("  - try_manager_connect() 调用 connect_server() 后立即返回")
    print("  - 然后 timer_check 启动等待 connect_result 变化")
    print("  - 但 connect_server 在后台线程中可能立即发出 connected 信号")
    print("  - 导致 on_temp_connected 收不到信号，timer_check 永远等待")
    print()

    return True


if __name__ == "__main__":
    print("\n训练管理Dock连接按钮逻辑测试\n")

    test_port_detection_connection_race()
    test_server_already_running_detection()
    test_signal_order()
    test_fast_connection()

    print("\n测试完成！")
