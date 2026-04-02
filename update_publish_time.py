#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动更新发布时间的脚本
在 Git commit 时自动更新 labelme/__init__.py 中的 __publish_time__

使用方法：
1. 作为 Git pre-commit hook 使用
2. 或手动运行：python update_publish_time.py
"""

import os
import os.path as osp
import re
from datetime import datetime

def update_publish_time():
    """更新 __init__.py 中的 __publish_time__"""
    # 获取项目根目录
    script_dir = osp.dirname(osp.abspath(__file__))
    init_file = osp.join(script_dir, "labelme", "__init__.py")
    
    if not osp.exists(init_file):
        print(f"错误：找不到文件 {init_file}")
        return False
    
    # 读取文件内容
    with open(init_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 生成当前时间（格式：YYYY-MM-DD HH:MM:SS）
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 替换 __publish_time__ 的值
    pattern = r'__publish_time__\s*=\s*"[^"]*"'
    replacement = f'__publish_time__ = "{current_time}"'
    
    new_content = re.sub(pattern, replacement, content)
    
    # 如果内容有变化，写入文件
    if new_content != content:
        with open(init_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"已更新发布时间为: {current_time}")
        return True
    else:
        print(f"发布时间已是最新: {current_time}")
        return False

if __name__ == "__main__":
    update_publish_time()
