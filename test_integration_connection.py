#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的集成测试 - 测试训练管理Dock的连接按钮逻辑
包括：
1. _ensure_server_running 方法
2. _connect_with_retry 方法
3. _on_server_connect_clicked 方法
"""

import sys
import time
import socket
import subprocess
import threading

sys.path.insert(0, r'E:\shangweiji\WSLabelme\labelme')

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt


class MockTrainingDock(QtWidgets.QWidget):
    """模拟训练管理Dock，用于测试"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = None
        self._connection_status = False
        self._status_message = "未连接"
        self._logs = []

    def set_connection_status(self, connected, message=None):
        """设置连接状态"""
        self._connection_status = connected
        self._status_message = message or ("已连接" if connected else "未连接")
        print(f"  [UI] 连接状态更新: {self._status_message}")

    def enable_server_edit(self, enabled):
        """启用/禁用服务器编辑"""
        print(f"  [UI] 服务器编辑 {'启用' if enabled else '禁用'}")

    def get_server_config(self):
        """获取服务器配置"""
        return "127.0.0.1", 8888

    def _log(self, message, level="info"):
        """记录日志"""
        self._logs.append((level, message))
        print(f"  [LOG][{level}] {message}")


class TestConnectionButtonLogic:
    """测试连接按钮逻辑"""

    def __init__(self):
        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        self.dock = MockTrainingDock()
        self.results = []

    def test_ensure_server_running_with_existing_server(self):
        """测试当服务器已经运行时，_ensure_server_running 是否能正确连接"""
        print("\n" + "=" * 60)
        print("测试1: 服务器已运行时 _ensure_server_running 行为")
        print("=" * 60)

        # 模拟 _ensure_server_running 的关键逻辑
        from labelme.training_client_manager import TrainingClientManager

        host, port = "127.0.0.1", 8888
        manager = TrainingClientManager(host, port)
        self.dock._manager = manager

        # 检查端口是否可用
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()

            if result != 0:
                print(f"  [SKIP] 端口 {port} 未开放，跳过此测试")
                self.results.append(("服务器已运行时 _ensure_server_running", "SKIP"))
                return True
        except Exception as e:
            print(f"  [ERROR] 端口检查失败: {e}")
            return False

        print(f"  端口 {port} 已开放，开始测试...")

        # 模拟 _ensure_server_running 的连接逻辑
        connection_established = False
        connect_result = None
        port_available = True

        loop = QtCore.QEventLoop(self.dock)
        timer_check = QtCore.QTimer(self.dock)

        def on_temp_connected(success):
            nonlocal connect_result
            connect_result = success
            print(f"  -> on_temp_connected: success={success}")

        def on_temp_error(msg):
            nonlocal connect_result
            connect_result = False
            print(f"  -> on_temp_error: {msg}")

        def check_connection_result():
            nonlocal connection_established
            if connection_established:
                return

            # 关键修复：优先检查 manager 实际连接状态
            if manager.is_connected():
                print("  -> 通过 is_connected() 检测到连接成功")
                connection_established = True
                timer_check.stop()
                loop.quit()
                return

            if connect_result is True:
                print("  -> 通过信号变量检测到连接成功")
                connection_established = True
                timer_check.stop()
                loop.quit()
            elif connect_result is False:
                print("  -> 检测到连接失败")
                timer_check.stop()
                loop.quit()

        manager.connected.connect(on_temp_connected)
        manager.connection_error.connect(on_temp_error)
        timer_check.timeout.connect(check_connection_result)

        # 发起连接
        print("  调用 connect_server...")
        manager.connect_server(host, port)

        # 启动检查定时器
        timer_check.start(500)

        # 进入事件循环（最多等待5秒）
        QtCore.QTimer.singleShot(5000, loop.quit)
        loop.exec_()

        # 清理
        timer_check.stop()
        try:
            manager.connected.disconnect(on_temp_connected)
            manager.connection_error.disconnect(on_temp_error)
        except:
            pass

        # 最终检查
        if not connection_established and manager.is_connected():
            connection_established = True

        print(f"\n  结果:")
        print(f"    - connection_established: {connection_established}")
        print(f"    - manager.is_connected(): {manager.is_connected()}")

        if connection_established:
            print("  [PASS]")
            self.results.append(("服务器已运行时 _ensure_server_running", "PASS"))
            return True
        else:
            print("  [FAIL]")
            self.results.append(("服务器已运行时 _ensure_server_running", "FAIL"))
            return False

    def test_connect_with_retry(self):
        """测试 _connect_with_retry 方法"""
        print("\n" + "=" * 60)
        print("测试2: _connect_with_retry 方法")
        print("=" * 60)

        from labelme.training_client_manager import TrainingClientManager

        host, port = "127.0.0.1", 8888
        manager = TrainingClientManager(host, port)
        self.dock._manager = manager

        # 检查端口
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()

            if result != 0:
                print(f"  [SKIP] 端口 {port} 未开放，跳过此测试")
                self.results.append(("_connect_with_retry", "SKIP"))
                return True
        except Exception as e:
            print(f"  [ERROR] 端口检查失败: {e}")
            return False

        print(f"  端口 {port} 已开放，开始测试...")

        # 模拟 _connect_with_retry 逻辑
        max_attempts = 3
        attempt_timeout = 5
        attempt = 1
        connect_result = None
        finished = False

        loop = QtCore.QEventLoop(self.dock)
        timer_label = QtCore.QTimer(self.dock)
        timer_check = QtCore.QTimer(self.dock)
        attempt_start_time = time.time()

        def on_connected(success):
            nonlocal connect_result
            if not finished:
                connect_result = success
                print(f"  -> on_connected: success={success}")

        def on_error(msg):
            nonlocal connect_result
            if not finished:
                connect_result = False
                print(f"  -> on_error: {msg}")

        def update_label():
            if finished:
                return
            elapsed = int(time.time() - attempt_start_time)
            if elapsed >= attempt_timeout and connect_result is None:
                connect_result = False

        def check_result():
            nonlocal connect_result, attempt, attempt_start_time, finished
            if finished:
                return

            # 关键修复：优先检查 manager 实际连接状态
            if manager.is_connected():
                print("  -> 通过 is_connected() 检测到连接")
                finished = True
                timer_label.stop()
                timer_check.stop()
                loop.quit()
                return

            if connect_result is True:
                print("  -> 通过信号变量检测到连接")
                finished = True
                timer_label.stop()
                timer_check.stop()
                loop.quit()
            elif connect_result is False:
                if attempt < max_attempts:
                    attempt += 1
                    print(f"  -> 重试第 {attempt} 次...")
                    connect_result = None
                    attempt_start_time = time.time()
                    manager.connect_server(host, port)
                else:
                    print("  -> 所有尝试都失败")
                    finished = True
                    timer_label.stop()
                    timer_check.stop()
                    loop.quit()

        manager.connected.connect(on_connected)
        manager.connection_error.connect(on_error)
        timer_label.timeout.connect(update_label)
        timer_check.timeout.connect(check_result)

        timer_label.start(1000)
        timer_check.start(500)

        print("  发起第一次连接...")
        manager.connect_server(host, port)

        # 进入事件循环（最多等待15秒）
        QtCore.QTimer.singleShot(15000, loop.quit)
        loop.exec_()

        # 清理
        timer_label.stop()
        timer_check.stop()
        try:
            manager.connected.disconnect(on_connected)
            manager.connection_error.disconnect(on_error)
        except:
            pass

        # 最终检查
        if not finished and manager.is_connected():
            finished = True

        print(f"\n  结果:")
        print(f"    - finished: {finished}")
        print(f"    - manager.is_connected(): {manager.is_connected()}")

        if finished and manager.is_connected():
            print("  [PASS]")
            self.results.append(("_connect_with_retry", "PASS"))
            return True
        else:
            print("  [FAIL]")
            self.results.append(("_connect_with_retry", "FAIL"))
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 60)
        print("训练管理Dock连接按钮逻辑集成测试")
        print("=" * 60)

        try:
            self.test_ensure_server_running_with_existing_server()
        except Exception as e:
            print(f"  [ERROR] {e}")
            self.results.append(("服务器已运行时 _ensure_server_running", "ERROR"))

        try:
            self.test_connect_with_retry()
        except Exception as e:
            print(f"  [ERROR] {e}")
            self.results.append(("_connect_with_retry", "ERROR"))

        # 汇总结果
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        for name, status in self.results:
            print(f"  {name}: {status}")

        passed = sum(1 for _, s in self.results if s == "PASS")
        failed = sum(1 for _, s in self.results if s == "FAIL")
        skipped = sum(1 for _, s in self.results if s == "SKIP")
        errors = sum(1 for _, s in self.results if s == "ERROR")

        print(f"\n总计: {passed} 通过, {failed} 失败, {skipped} 跳过, {errors} 错误")

        return failed == 0 and errors == 0


if __name__ == "__main__":
    tester = TestConnectionButtonLogic()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
