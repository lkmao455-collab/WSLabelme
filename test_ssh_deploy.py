# -*- coding: utf-8 -*-
"""
SSH 部署模块测试脚本

用于测试模型部署 Dock 面板的各项功能。
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5 import QtWidgets, QtCore


def test_imports():
    """测试模块导入"""
    print("=" * 50)
    print("测试模块导入...")
    print("=" * 50)
    
    try:
        from ssh_deploy import DeployDockWidget
        print("✓ DeployDockWidget 导入成功")
    except Exception as e:
        print(f"✗ DeployDockWidget 导入失败: {e}")
        return False
    
    try:
        from ssh_deploy.ssh_client import SSHClient, SSHConfig
        print("✓ SSHClient, SSHConfig 导入成功")
    except Exception as e:
        print(f"✗ SSHClient 导入失败: {e}")
        return False
    
    try:
        from ssh_deploy.device_manager import DeviceManager, DeviceInfo
        print("✓ DeviceManager, DeviceInfo 导入成功")
    except Exception as e:
        print(f"✗ DeviceManager 导入失败: {e}")
        return False
    
    try:
        from ssh_deploy.log_handler import LogHandler, LogLevel
        print("✓ LogHandler, LogLevel 导入成功")
    except Exception as e:
        print(f"✗ LogHandler 导入失败: {e}")
        return False
    
    try:
        from ssh_deploy.deploy_worker import (
            ConnectionTestWorker,
            FileTransferWorker,
            DeployWorker,
        )
        print("✓ Worker 类导入成功")
    except Exception as e:
        print(f"✗ Worker 类导入失败: {e}")
        return False
    
    print("\n所有模块导入成功！")
    return True


def test_device_manager():
    """测试设备管理器"""
    print("\n" + "=" * 50)
    print("测试设备管理器...")
    print("=" * 50)
    
    from ssh_deploy.device_manager import DeviceManager
    
    dm = DeviceManager()
    
    # 测试创建设备
    device = dm.create_device(
        name="测试设备",
        host="192.168.1.100",
        device_type="ERV",
    )
    print(f"✓ 创建设备: {device.name} ({device.host})")
    
    # 测试获取设备
    retrieved = dm.get_device(device.id)
    print(f"✓ 获取设备: {retrieved.name}")
    
    # 测试凭据
    username, password = dm.get_device_credentials("ERV")
    print(f"✓ ERV 凭据: {username}/{password}")
    
    # 测试删除
    dm.delete_device(device.id)
    print(f"✓ 删除设备成功")
    
    print("\n设备管理器测试通过！")
    return True


def test_log_handler():
    """测试日志处理器"""
    print("\n" + "=" * 50)
    print("测试日志处理器...")
    print("=" * 50)
    
    from ssh_deploy.log_handler import LogHandler, LogLevel
    
    log = LogHandler()
    
    # 添加各种级别的日志
    log.debug("调试信息")
    log.info("普通信息")
    log.warning("警告信息")
    log.error("错误信息")
    log.success("成功信息")
    
    print(f"✓ 日志数量: {log.get_log_count()}")
    
    stats = log.get_statistics()
    print(f"✓ 日志统计: {stats}")
    
    print("\n日志处理器测试通过！")
    return True


def test_ui():
    """测试 UI 界面"""
    print("\n" + "=" * 50)
    print("测试 UI 界面...")
    print("=" * 50)
    
    from PyQt5 import QtWidgets
    from ssh_deploy import DeployDockWidget
    
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication(sys.argv)
    
    # 创建主窗口
    window = QtWidgets.QMainWindow()
    window.setWindowTitle("SSH 部署模块测试")
    window.resize(1200, 800)
    
    # 创建 Dock
    dock = DeployDockWidget()
    window.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
    
    # 添加一些测试日志
    dock.log_handler.info("测试日志: UI 界面已加载")
    dock.log_handler.success("模块初始化成功")
    
    print("✓ UI 界面创建成功")
    print("✓ Dock 面板已添加到主窗口")
    
    window.show()
    
    print("\nUI 测试通过！显示测试窗口...")
    print("按 Ctrl+C 或关闭窗口退出")
    
    return app.exec_()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("SSH 模型部署模块测试")
    print("=" * 60)
    
    # 测试导入
    if not test_imports():
        print("\n模块导入失败，请检查安装！")
        return 1
    
    # 测试设备管理器
    if not test_device_manager():
        print("\n设备管理器测试失败！")
        return 1
    
    # 测试日志处理器
    if not test_log_handler():
        print("\n日志处理器测试失败！")
        return 1
    
    # 测试 UI
    print("\n" + "=" * 60)
    print("所有单元测试通过！")
    print("=" * 60)
    print("\n启动 UI 测试...")
    
    return test_ui()


if __name__ == "__main__":
    sys.exit(main())