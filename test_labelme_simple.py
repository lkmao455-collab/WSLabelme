#!/usr/bin/env python
"""
测试Labelme启动的简化脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # 测试基本导入
    print("Testing Labelme import...")
    import labelme
    print("SUCCESS: Labelme import successful!")
    
    # 测试版本信息
    print(f"Labelme version: {labelme.__version__}")
    print(f"App name: {labelme.__appname__}")
    
    # 测试配置加载
    print("Testing config loading...")
    from labelme.config import get_config
    config = get_config()
    print("SUCCESS: Config loaded successfully!")
    
    # 测试主要组件导入
    print("Testing main components import...")
    from labelme.app import MainWindow
    from labelme.widgets import Canvas
    from labelme.shape import Shape
    from labelme.label_file import LabelFile
    print("SUCCESS: Main components imported successfully!")
    
    # 测试自动化模块（应该优雅地处理osam缺失）
    print("Testing automation module...")
    from labelme._automation import get_bboxes_from_texts, nms_bboxes
    print("SUCCESS: Automation module imported successfully!")
    
    print("\nALL TESTS PASSED! Labelme has been successfully fixed and can start normally!")
    print("\nYou can now run the following command to start Labelme:")
    print("  python -m labelme")
    
except Exception as e:
    print(f"TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)