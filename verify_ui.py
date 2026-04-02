#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI图像标注与训练系统验证脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_files():
    """验证文件存在性"""
    files_to_check = [
        'mainform.ui',
        'main.py',
        'model_training.py',
        'model_usage.py',
        'run_ai_system.py',
        'labelme/config/default_config.yaml'
    ]
    
    missing_files = []
    for file in files_to_check:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("Missing files:", missing_files)
        return False
    else:
        print("All required files exist")
        return True

def verify_config():
    """验证配置文件"""
    try:
        import yaml
        with open('labelme/config/default_config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 检查redo快捷键是否存在
        if 'shortcuts' in config and 'redo' in config['shortcuts']:
            print("Redo shortcut configured correctly")
            return True
        else:
            print("Redo shortcut not found in config")
            return False
    except Exception as e:
        print(f"Config verification error: {e}")
        return False

if __name__ == "__main__":
    success = True
    success &= verify_files()
    success &= verify_config()
    
    if success:
        print("\nUI verification passed! The new interface is ready.")
    else:
        print("\nUI verification failed!")
    
    sys.exit(0 if success else 1)