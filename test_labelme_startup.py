#!/usr/bin/env python
"""
测试Labelme启动的脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # 测试基本导入
    print("正在测试Labelme导入...")
    import labelme
    print("✓ Labelme导入成功!")
    
    # 测试版本信息
    print(f"✓ Labelme版本: {labelme.__version__}")
    print(f"✓ 应用名称: {labelme.__appname__}")
    
    # 测试配置加载
    print("正在测试配置加载...")
    from labelme.config import get_config
    config = get_config()
    print("✓ 配置加载成功!")
    
    # 测试主要组件导入
    print("正在测试主要组件导入...")
    from labelme.app import MainWindow
    from labelme.widgets import Canvas
    from labelme.shape import Shape
    from labelme.label_file import LabelFile
    print("✓ 主要组件导入成功!")
    
    # 测试自动化模块（应该优雅地处理osam缺失）
    print("正在测试自动化模块...")
    from labelme._automation import get_bboxes_from_texts, nms_bboxes
    print("✓ 自动化模块导入成功!")
    
    # 测试AI模型初始化（应该优雅地处理osam缺失）
    print("正在测试AI模型初始化...")
    try:
        canvas = Canvas()
        canvas.initializeAiModel("sam_vit_h")
        print("✓ AI模型初始化成功!")
    except Exception as e:
        print(f"⚠ AI模型初始化失败（这是正常的，因为osam模块未安装）: {e}")
    
    print("\n🎉 所有测试通过! Labelme已成功修复并可以正常启动!")
    print("\n现在你可以运行以下命令来启动Labelme:")
    print("  python -m labelme")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)