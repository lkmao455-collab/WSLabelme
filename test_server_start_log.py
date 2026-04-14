#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试服务器启动过程中的详细日志输出
"""

import sys
import time
import socket

sys.path.insert(0, r'E:\shangweiji\WSLabelme\labelme')

from PyQt5 import QtCore, QtWidgets


def test_server_start_logs():
    """测试服务器启动时的日志输出"""
    print("=" * 60)
    print("测试: 服务器启动过程日志输出")
    print("=" * 60)

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    # 模拟 unified_training_widget 的日志方法
    logs = []

    def mock_log(msg, level="info"):
        logs.append((level, msg))
        print(f"  [{level.upper()}] {msg}")

    # 模拟 _ensure_server_running 的关键逻辑，带详细日志
    host, port = "127.0.0.1", 8888

    print("\n1. 模拟进程检查...")
    mock_log("[服务器启动检查] 进程检查: 未运行")

    print("\n2. 模拟查找可执行文件...")
    exe_path = r"E:\shangweiji\WSLabelme\labelme\training_server.exe"
    mock_log(f"[服务器启动检查] 查找可执行文件: {exe_path}")

    print("\n3. 模拟启动服务器进程...")
    mock_log(f"[服务器启动检查] 启动服务器进程: {exe_path}")
    mock_log("[服务器启动检查] 服务器进程已启动，PID: 12345")

    print("\n4. 模拟端口检测循环...")
    port_check_count = 0
    port_available = False

    for i in range(15):  # 模拟15次检测
        port_check_count += 1
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            port_available = True
            mock_log(f"[服务器启动检查] 端口检测成功 (第{port_check_count}次检测)")
            mock_log(f"[服务器启动检查] 端口 {port} 已开放，开始尝试 manager 连接")
            break
        else:
            if port_check_count % 5 == 0:
                mock_log(f"[服务器启动检查] 端口 {port} 仍未开放 (已检测{port_check_count}次)")

        # 每10秒输出状态报告
        if i > 0 and i % 10 == 0:
            mock_log(f"[服务器启动检查] 状态报告 (已运行 00:{i:02d}):")
            mock_log(f"  - 进程状态: {'运行中' if True else '未运行'}")
            mock_log(f"  - 端口状态: {'可用' if port_available else '检测中'}")
            mock_log(f"  - 端口检测: {port_check_count} 次尝试")

        time.sleep(0.1)

    print("\n5. 模拟 manager 连接...")
    if port_available:
        mock_log(f"[服务器启动检查] 发起 manager 连接: {host}:{port}")
        mock_log("[服务器启动检查] 收到 connected 信号: success=True")
        mock_log("[服务器启动检查] 通过信号变量检测到连接成功")

    print("\n6. 最终状态报告...")
    mock_log("[服务器启动检查] 最终状态报告:")
    mock_log(f"  - 总耗时: 00:01")
    mock_log(f"  - 端口检测: {port_check_count} 次")
    mock_log(f"  - Manager连接尝试: 1 次")
    mock_log(f"  - 连接成功: True")
    mock_log(f"  - 进程仍在运行: True")
    mock_log("训练服务器已启动并成功连接")

    print("\n" + "=" * 60)
    print("日志输出测试完成")
    print("=" * 60)

    # 统计日志数量
    server_start_logs = [l for l in logs if "[服务器启动检查]" in l[1]]
    print(f"\n共输出 {len(logs)} 条日志，其中服务器启动检查日志 {len(server_start_logs)} 条")

    return True


def test_real_port_detection():
    """测试真实的端口检测逻辑"""
    print("\n" + "=" * 60)
    print("测试: 真实端口检测")
    print("=" * 60)

    host, port = "127.0.0.1", 8888

    print(f"\n检测端口 {port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print(f"  [结果] 端口 {port} 已开放")
            return True
        else:
            print(f"  [结果] 端口 {port} 未开放 (错误码: {result})")
            return False
    except Exception as e:
        print(f"  [错误] 检测失败: {e}")
        return False


if __name__ == "__main__":
    print("\n服务器启动日志输出测试\n")

    test_server_start_logs()
    test_real_port_detection()

    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)
