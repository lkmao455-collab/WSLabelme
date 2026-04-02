#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将 icon.ico 转换为与 icon_bak.png 相同格式的 PNG 图片
"""
import os
from PIL import Image

# 源文件路径
ico_path = r"E:\标注工具\labelme\dist\Labelme\_internal\labelme\icons\icon.ico"
bak_png_path = None
output_png_path = r"E:\标注工具\labelme\dist\Labelme\_internal\labelme\icons\icon.png"

# 查找 icon_bak.png 文件
search_paths = [
    r"E:\标注工具\labelme\dist\Labelme\_internal\labelme\icons\icon_bak.png",
    r"E:\标注工具\labelme\labelme\icons\icon_bak.png",
    r"E:\标注工具\labelme\icon_bak.png",
]

for path in search_paths:
    if os.path.exists(path):
        bak_png_path = path
        print(f"Found icon_bak.png at: {bak_png_path}")
        break

if not bak_png_path:
    print("Warning: icon_bak.png not found, will use default PNG format")

# 检查源文件是否存在
if not os.path.exists(ico_path):
    print(f"Error: Source file not found: {ico_path}")
    exit(1)

print(f"Converting {ico_path} to PNG format...")

# 读取 icon.ico
try:
    ico_image = Image.open(ico_path)
    print(f"Original ICO size: {ico_image.size}")
    print(f"Original ICO mode: {ico_image.mode}")
    
    # 如果找到了 icon_bak.png，读取其格式信息
    if bak_png_path:
        bak_image = Image.open(bak_png_path)
        print(f"Reference PNG size: {bak_image.size}")
        print(f"Reference PNG mode: {bak_image.mode}")
        
        # 转换为与参考图片相同的模式
        if bak_image.mode == 'RGBA':
            if ico_image.mode != 'RGBA':
                ico_image = ico_image.convert('RGBA')
        elif bak_image.mode == 'RGB':
            if ico_image.mode != 'RGB':
                ico_image = ico_image.convert('RGB')
        
        # 如果尺寸不同，调整为与参考图片相同的尺寸
        if ico_image.size != bak_image.size:
            print(f"Resizing from {ico_image.size} to {bak_image.size}")
            ico_image = ico_image.resize(bak_image.size, Image.Resampling.LANCZOS)
    else:
        # 如果没有参考图片，转换为 RGBA（支持透明背景）
        if ico_image.mode != 'RGBA':
            ico_image = ico_image.convert('RGBA')
    
    # 保存为 PNG
    output_dir = os.path.dirname(output_png_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    
    ico_image.save(output_png_path, 'PNG')
    print(f"Successfully converted to: {output_png_path}")
    print(f"Output size: {ico_image.size}")
    print(f"Output mode: {ico_image.mode}")
    
except Exception as e:
    print(f"Error converting icon: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
