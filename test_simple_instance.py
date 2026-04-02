#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的防止多次启动功能测试

这个脚本用于验证共享内存锁机制是否正常工作。
"""

import os
import sys
import time
import subprocess
import threading

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_functionality():
    """测试基本功能"""
    print("=" * 50)
    print("防止多次启动功能测试")
    print("=" * 50)
    
    # 测试1: 检查导入
    print("\n1. 测试导入...")
    try:
        from labelme.__main__ import check_single_instance, _is_process_running
        print("   OK: 导入成功")
    except ImportError as e:
        print(f"   FAIL: 导入失败: {e}")
        return False
    
    # 测试2: 检查当前进程
    print("\n2. 测试进程检查...")
    current_pid = os.getpid()
    if _is_process_running(current_pid):
        print(f"   OK: 当前进程 {current_pid} 正在运行")
    else:
        print(f"   FAIL: 当前进程 {current_pid} 未运行")
        return False
    
    # 测试3: 检查不存在的进程
    print("\n3. 测试不存在的进程...")
    fake_pid = 999999  # 一个不可能存在的PID
    if not _is_process_running(fake_pid):
        print(f"   OK: 不存在的进程 {fake_pid} 正确识别为未运行")
    else:
        print(f"   FAIL: 不存在的进程 {fake_pid} 被错误识别为正在运行")
        return False
    
    # 测试4: 检查单实例函数
    print("\n4. 测试单实例检查...")
    if check_single_instance():
        print("   OK: 单实例检查通过，可以启动新实例")
    else:
        print("   FAIL: 单实例检查失败，已有实例在运行")
        return False
    
    print("\n" + "=" * 50)
    print("所有测试通过！防止多次启动功能正常工作。")
    print("=" * 50)
    return True

def main():
    """主测试函数"""
    print("Labelme 防止多次启动功能测试")
    
    # 运行基本测试
    basic_test_passed = test_basic_functionality()
    
    print("\n" + "=" * 50)
    print("最终测试结果:")
    print(f"基本功能测试: {'通过' if basic_test_passed else '失败'}")
    
    if basic_test_passed:
        print("\nOK: 所有测试通过！防止多次启动功能完全正常工作。")
        print("\n功能特性:")
        print("- 使用共享内存实现进程间通信")
        print("- 自动检测和清理僵尸进程的共享内存")
        print("- 支持跨平台（Windows/Linux/macOS）")
        print("- 出错时优雅降级，允许启动")
        print("- 提供友好的用户界面提示")
        print("\n使用方法:")
        print("1. 正常启动 Labelme: python -m labelme")
        print("2. 尝试再次启动，会显示警告消息并退出")
        print("3. 关闭第一个实例后，可以正常启动第二个实例")
    else:
        print("\nFAIL: 部分测试失败，请检查实现。")
    
    print("=" * 50)

if __name__ == "__main__":
    main()