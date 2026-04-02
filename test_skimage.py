#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试skimage导入
"""

try:
    import skimage
    print("✓ skimage imported successfully")
    print(f"skimage version: {skimage.__version__}")
    
    # 测试常用子模块
    import skimage.io
    import skimage.color
    import skimage.transform
    import skimage.util
    print("✓ skimage submodules imported successfully")
    
except Exception as e:
    print(f"✗ skimage import failed: {e}")
    sys.exit(1)