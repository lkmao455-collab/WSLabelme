#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单验证脚本
"""

import sys
import os

def check_files():
    """检查文件是否存在"""
    files = [
        'mainform.ui',
        'main.py', 
        'model_training.py',
        'model_usage.py',
        'run_ai_system.py'
    ]
    
    all_exist = True
    for f in files:
        if os.path.exists(f):
            print("[OK] " + f + " exists")
        else:
            print("[ERROR] " + f + " missing")
            all_exist = False
    
    return all_exist

def check_config():
    """检查配置文件中的redo快捷键"""
    try:
        with open('labelme/config/default_config.yaml', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'redo:' in content:
            print("[OK] redo shortcut found in config")
            return True
        else:
            print("[ERROR] redo shortcut not found in config")
            return False
    except Exception as e:
        print("[ERROR] Error reading config: " + str(e))
        return False

if __name__ == "__main__":
    print("Verifying AI Annotation System UI...")
    print("=" * 40)
    
    success = True
    success &= check_files()
    success &= check_config()
    
    print("=" * 40)
    if success:
        print("All checks passed! UI is ready.")
    else:
        print("Some checks failed!")
    
    sys.exit(0 if success else 1)