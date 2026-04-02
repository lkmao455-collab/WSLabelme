#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI图像标注与训练系统启动脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from main import main
    main()