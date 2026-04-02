#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
脚本用于检查打包状态并将exe文件移动到myapp文件夹
"""
import os
import shutil
import time
from pathlib import Path

def check_and_move():
    """检查打包是否完成，如果完成则移动exe文件"""
    dist_dir = Path("dist")
    exe_name = "Labelme.exe"
    exe_path = dist_dir / exe_name
    myapp_dir = Path("myapp")
    
    # 检查exe文件是否存在
    if exe_path.exists():
        print(f"找到exe文件: {exe_path}")
        
        # 创建myapp文件夹
        myapp_dir.mkdir(exist_ok=True)
        print(f"创建/确认myapp文件夹: {myapp_dir}")
        
        # 移动exe文件
        dest_path = myapp_dir / exe_name
        if dest_path.exists():
            print(f"目标文件已存在，删除旧文件...")
            dest_path.unlink()
        
        shutil.move(str(exe_path), str(dest_path))
        print(f"成功将 {exe_name} 移动到 {dest_path}")
        
        # 检查是否有其他依赖文件需要移动（如果是onedir模式）
        if dist_dir.exists():
            other_files = list(dist_dir.glob("*"))
            if other_files:
                print(f"\n注意: dist文件夹中还有其他文件，可能需要一起移动:")
                for f in other_files:
                    if f.is_file() and f.suffix != '.exe':
                        print(f"  - {f.name}")
        
        return True
    else:
        print(f"exe文件尚未生成: {exe_path}")
        return False

if __name__ == "__main__":
    max_wait = 3600  # 最多等待1小时
    check_interval = 30  # 每30秒检查一次
    waited = 0
    
    print("等待打包完成...")
    while waited < max_wait:
        if check_and_move():
            break
        time.sleep(check_interval)
        waited += check_interval
        print(f"已等待 {waited} 秒，继续检查...")
    
    if waited >= max_wait:
        print("等待超时，请手动检查打包状态")
