#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终脚本：检查打包是否完成，并将exe文件移动到myapp文件夹
"""
import os
import shutil
from pathlib import Path

def main():
    """主函数"""
    # 定义路径
    dist_dir = Path("dist")
    exe_name = "Labelme.exe"
    exe_path = dist_dir / exe_name
    myapp_dir = Path("myapp")
    
    print("=" * 50)
    print("检查打包状态并移动exe文件")
    print("=" * 50)
    
    # 检查exe文件是否存在
    if exe_path.exists():
        print(f"[OK] 找到exe文件: {exe_path}")
        print(f"  文件大小: {exe_path.stat().st_size / (1024*1024):.2f} MB")
        
        # 创建myapp文件夹
        myapp_dir.mkdir(exist_ok=True)
        print(f"[OK] myapp文件夹已准备: {myapp_dir}")
        
        # 目标路径
        dest_path = myapp_dir / exe_name
        
        # 如果目标文件已存在，先删除
        if dest_path.exists():
            print(f"[WARN] 目标文件已存在，删除旧文件...")
            dest_path.unlink()
        
        # 移动exe文件
        try:
            shutil.move(str(exe_path), str(dest_path))
            print(f"[OK] 成功将 {exe_name} 移动到 {dest_path.absolute()}")
            print("\n" + "=" * 50)
            print("打包完成！exe文件已移动到myapp文件夹")
            print("=" * 50)
            return True
        except Exception as e:
            print(f"[ERROR] 移动文件时出错: {e}")
            return False
    else:
        print(f"[INFO] exe文件尚未生成: {exe_path}")
        print("\n提示: 打包可能还在进行中，请稍后再运行此脚本")
        print("或者检查 dist 文件夹中是否有其他文件")
        
        # 列出dist文件夹中的内容
        if dist_dir.exists():
            files = list(dist_dir.iterdir())
            if files:
                print(f"\ndist文件夹中的内容:")
                for f in files:
                    size = f.stat().st_size / (1024*1024) if f.is_file() else 0
                    print(f"  - {f.name} ({size:.2f} MB)" if f.is_file() else f"  - {f.name}/ (目录)")
        
        return False

if __name__ == "__main__":
    main()
