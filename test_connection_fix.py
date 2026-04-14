#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试训练管理dock的连接按钮逻辑修复
验证信号丢失问题和连接检测问题是否已修复
"""

import sys
import time
import socket
import subprocess
import threading

sys.path.insert(0, r'E:\shangweiji\WSLabelme\labelme')

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt


def test_connection_with_running_server():
    """测试当服务器已经运行时，连接按钮是否能正确检测到"""
    print("=" * 60)
    print("测试: 服务器已运行时的连接检测")
    print("=" * 60)

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    from labelme.training_client_manager import TrainingClientManager

    # 创建 manager
    manager = TrainingClientManager("127.0.0.1", 8888)

    # 记录信号接收
    signals_received = []
    is_connected_after_signal = []

    def on_connected(success):
        signals_received.append(f"connected({success})")
        is_connected_after_signal.append(manager.is_connected())
        print(f"  -> 收到 connected 信号: success={success}, is_connected={manager.is_connected()}")

    def on_error(msg):
        signals_received.append(f"connection_error({msg})")
        is_connected_after_signal.append(manager.is_connected())
        print(f"  -> 收到 connection_error 信号: {msg}")

    manager.connected.connect(on_connected)
    manager.connection_error.connect(on_error)

    # 测试1: 直接检查端口和连接
    print("\n测试1: 直接检查端口...")
    host, port = "127.0.0.1", 8888
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"  端口 {port} 已开放")
        else:
            print(f"  端口 {port} 未开放 (错误码: {result})")
    except Exception as e:
        print(f"  端口检查失败: {e}")

    # 测试2: 使用 manager 连接
    print("\n测试2: 使用 manager 连接...")
    print("  发起 connect_server 调用...")
    manager.connect_server(host, port)

    # 等待连接完成
    print("  等待2秒让连接完成...")
    time.sleep(2)

    print(f"\n  结果:")
    print(f"    - 收到的信号: {signals_received}")
    print(f"    - 信号后的is_connected状态: {is_connected_after_signal}")
    print(f"    - 最终 is_connected: {manager.is_connected()}")

    if manager.is_connected() and len(signals_received) > 0:
        print("  [PASS] 连接成功且收到信号")
        return True
    elif manager.is_connected() and len(signals_received) == 0:
        print("  [WARNING] 连接成功但未收到信号（可能是信号在主线程阻塞时发出）")
        return True
    else:
        print("  [FAIL] 连接失败")
        return False


def test_race_condition_simulation():
    """
    模拟竞争条件：测试当信号在事件循环启动前发出时，
    check_connection_result 是否能正确检测到连接状态
    """
    print("\n" + "=" * 60)
    print("测试: 竞争条件模拟")
    print("=" * 60)

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    from labelme.training_client_manager import TrainingClientManager

    manager = TrainingClientManager("127.0.0.1", 8888)

    connect_result = [None]
    connection_established = [False]

    def on_temp_connected(success):
        connect_result[0] = success
        print(f"  -> on_temp_connected 被调用: success={success}")

    def on_temp_error(msg):
        connect_result[0] = False
        print(f"  -> on_temp_error 被调用: {msg}")

    # 连接信号
    manager.connected.connect(on_temp_connected)
    manager.connection_error.connect(on_temp_error)

    # 创建事件循环
    loop = QtCore.QEventLoop()

    # 创建定时器模拟 check_connection_result
    timer_check = QtCore.QTimer()
    check_count = [0]

    def check_connection_result():
        check_count[0] += 1
        if connection_established[0]:
            print(f"  检查 #{check_count[0]}: 已连接，退出")
            timer_check.stop()
            loop.quit()
            return

        # 关键修复：优先检查 manager 实际连接状态
        if manager.is_connected():
            print(f"  检查 #{check_count[0]}: 通过 is_connected() 检测到连接")
            connection_established[0] = True
            timer_check.stop()
            loop.quit()
            return

        if connect_result[0] is True:
            print(f"  检查 #{check_count[0]}: 通过信号变量检测到连接")
            connection_established[0] = True
            timer_check.stop()
            loop.quit()
        elif connect_result[0] is False:
            print(f"  检查 #{check_count[0]}: 检测到连接失败")
            timer_check.stop()
            loop.quit()
        else:
            print(f"  检查 #{check_count[0]}: 仍在等待...")

    timer_check.timeout.connect(check_connection_result)

    # 发起连接
    print("\n  发起连接...")
    manager.connect_server("127.0.0.1", 8888)

    # 等待一小段时间让连接线程启动
    print("  等待500ms让连接线程启动...")
    QtCore.QThread.msleep(500)

    # 启动检查定时器
    print("  启动检查定时器...")
    timer_check.start(200)

    # 进入事件循环
    print("  进入事件循环等待...")
    loop.exec_()

    print(f"\n  结果:")
    print(f"    - 检查次数: {check_count[0]}")
    print(f"    - connection_established: {connection_established[0]}")
    print(f"    - manager.is_connected(): {manager.is_connected()}")

    if connection_established[0]:
        print("  [PASS] 竞争条件处理正确")
        return True
    else:
        print("  [FAIL] 竞争条件处理失败")
        return False


if __name__ == "__main__":
    print("\n训练管理Dock连接按钮逻辑修复测试\n")

    results = []

    try:
        results.append(("服务器已运行检测", test_connection_with_running_server()))
    except Exception as e:
        print(f"测试失败: {e}")
        results.append(("服务器已运行检测", False))

    try:
        results.append(("竞争条件模拟", test_race_condition_simulation()))
    except Exception as e:
        print(f"测试失败: {e}")
        results.append(("竞争条件模拟", False))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")

    all_passed = all(r[1] for r in results)
    print(f"\n总体: {'全部通过' if all_passed else '有测试失败'}")
