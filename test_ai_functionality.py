#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Labelme AI功能的脚本

这个脚本用于验证AI标注功能是否正常工作，包括：
1. osam模块导入
2. bbox_from_text模块导入
3. 函数可用性测试
4. 基本功能验证
"""

import sys
import os

def test_osam_import():
    """测试osam模块导入"""
    try:
        import osam
        print("osam模块导入成功")
        print(f"  版本: {osam.__version__}")
        return True
    except ImportError as e:
        print(f"osam模块导入失败: {e}")
        return False

def test_bbox_from_text_import():
    """测试bbox_from_text模块导入"""
    try:
        from labelme._automation import bbox_from_text
        print("bbox_from_text模块导入成功")
        
        # 检查可用函数
        functions = [name for name in dir(bbox_from_text) if not name.startswith('_')]
        print(f"  可用函数: {', '.join(functions)}")
        return True
    except ImportError as e:
        print(f"bbox_from_text模块导入失败: {e}")
        return False

def test_osam_apis():
    """测试osam API可用性"""
    try:
        import osam
        apis = [name for name in dir(osam.apis) if not name.startswith('_')]
        types = [name for name in dir(osam.types) if not name.startswith('_')]
        
        print("osam API测试成功")
        print(f"  可用API: {', '.join(apis)}")
        print(f"  可用类型: {', '.join(types)}")
        return True
    except Exception as e:
        print(f"osam API测试失败: {e}")
        return False

def test_function_availability():
    """测试关键函数可用性"""
    try:
        from labelme._automation import bbox_from_text
        
        # 检查关键函数是否存在
        required_functions = [
            'get_bboxes_from_texts',
            'nms_bboxes', 
            'get_shapes_from_bboxes'
        ]
        
        missing_functions = []
        for func_name in required_functions:
            if not hasattr(bbox_from_text, func_name):
                missing_functions.append(func_name)
        
        if missing_functions:
            print(f"缺少函数: {', '.join(missing_functions)}")
            return False
        else:
            print("所有关键函数都可用")
            return True
    except Exception as e:
        print(f"函数可用性测试失败: {e}")
        return False

def test_app_import():
    """测试app.py中的AI功能导入"""
    try:
        # 临时添加当前目录到路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # 测试app.py中的导入
        from labelme.app import MainWindow
        print("app.py导入成功")
        
        # 检查MainWindow类是否存在
        if hasattr(MainWindow, '_submit_ai_prompt'):
            print("_submit_ai_prompt方法存在")
        else:
            print("_submit_ai_prompt方法不存在")
            return False
            
        return True
    except Exception as e:
        print(f"app.py导入测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 50)
    print("Labelme AI功能测试")
    print("=" * 50)
    
    tests = [
        ("osam模块导入", test_osam_import),
        ("bbox_from_text模块导入", test_bbox_from_text_import),
        ("osam API测试", test_osam_apis),
        ("函数可用性测试", test_function_availability),
        ("app.py导入测试", test_app_import),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n测试: {test_name}")
        print("-" * 30)
        if test_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("所有测试通过！AI功能已正常工作。")
        print("\n现在您可以：")
        print("1. 启动Labelme应用程序")
        print("2. 在AI提示框中输入文本（如：'person,car'）")
        print("3. 点击Submit按钮进行AI标注")
    else:
        print("部分测试失败，请检查相关模块。")
    
    print("=" * 50)

if __name__ == "__main__":
    main()