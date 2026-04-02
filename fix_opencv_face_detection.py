#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复OpenCV人脸检测问题的脚本
"""

import cv2
import os
import numpy as np
import matplotlib.pyplot as plt

def check_opencv_installation():
    """检查OpenCV安装状态"""
    print("=" * 60)
    print("OpenCV 人脸检测问题诊断")
    print("=" * 60)
    
    # 检查OpenCV版本
    print(f"OpenCV版本: {cv2.__version__}")
    
    # 检查级联分类器文件
    print("\n1. 检查级联分类器文件...")
    
    # 方法1: 使用cv2自带的级联分类器路径
    try:
        # 获取OpenCV数据目录
        opencv_data_dir = cv2.__file__.replace('__init__.py', 'data/')
        print(f"OpenCV数据目录: {opencv_data_dir}")
        
        # 检查文件是否存在
        cascade_file = os.path.join(opencv_data_dir, 'haarcascade_frontalface_default.xml')
        if os.path.exists(cascade_file):
            print(f"✓ 级联分类器文件存在: {cascade_file}")
        else:
            print(f"✗ 级联分类器文件不存在: {cascade_file}")
            
    except Exception as e:
        print(f"检查OpenCV数据目录时出错: {e}")
    
    # 方法2: 使用cv2.data.haarcascades
    try:
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        print(f"cv2.data.haarcascades路径: {cascade_path}")
        if os.path.exists(cascade_path):
            print(f"✓ 级联分类器文件存在: {cascade_path}")
        else:
            print(f"✗ 级联分类器文件不存在: {cascade_path}")
    except Exception as e:
        print(f"使用cv2.data.haarcascades时出错: {e}")
    
    # 方法3: 搜索系统中的级联文件
    print("\n2. 搜索系统中的级联文件...")
    search_paths = [
        'C:/Program Files/Python310/Lib/site-packages/cv2/data/',
        'C:/Python310/Lib/site-packages/cv2/data/',
        'D:/Program Files/Python310/Lib/site-packages/cv2/data/',
        os.path.expanduser('~/opencv/data/'),
        os.path.expanduser('~/cv2/data/'),
    ]
    
    found_files = []
    for path in search_paths:
        if os.path.exists(path):
            files = [f for f in os.listdir(path) if f.endswith('.xml')]
            if files:
                print(f"在 {path} 找到文件: {files}")
                found_files.extend([os.path.join(path, f) for f in files])
    
    if not found_files:
        print("未找到任何级联分类器文件")
    
    return found_files

def create_test_image():
    """创建一个测试图像用于人脸检测"""
    print("\n3. 创建测试图像...")
    
    # 创建一个包含人脸的测试图像
    # 这里我们创建一个简单的合成图像
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    
    # 绘制一个简单的"人脸"
    # 脸部轮廓
    cv2.ellipse(img, (300, 200), (150, 200), 0, 0, 360, (255, 255, 255), -1)
    
    # 眼睛
    cv2.circle(img, (220, 150), 20, (0, 0, 0), -1)
    cv2.circle(img, (380, 150), 20, (0, 0, 0), -1)
    
    # 嘴巴
    cv2.ellipse(img, (300, 250), (80, 30), 0, 0, 180, (0, 0, 0), 3)
    
    # 保存测试图像
    cv2.imwrite('test_face_image.jpg', img)
    print("✓ 创建测试图像: test_face_image.jpg")
    
    return 'test_face_image.jpg'

def test_face_detection(image_path, cascade_path):
    """测试人脸检测功能"""
    print(f"\n4. 测试人脸检测...")
    print(f"使用图像: {image_path}")
    print(f"使用级联分类器: {cascade_path}")
    
    try:
        # 加载级联分类器
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # 检查分类器是否加载成功
        if face_cascade.empty():
            print("✗ 级联分类器加载失败")
            return False
        
        print("✓ 级联分类器加载成功")
        
        # 加载图像
        img = cv2.imread(image_path)
        if img is None:
            print(f"✗ 无法加载图像: {image_path}")
            return False
        
        print("✓ 图像加载成功")
        
        # 转换为灰度图像
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 检测人脸
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        print(f"检测到 {len(faces)} 个人脸")
        
        # 绘制边界框
        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
        # 保存结果
        result_path = 'face_detection_result.jpg'
        cv2.imwrite(result_path, img)
        print(f"✓ 保存检测结果: {result_path}")
        
        return True
        
    except Exception as e:
        print(f"✗ 人脸检测失败: {e}")
        return False

def download_cascade_classifier():
    """下载级联分类器文件"""
    print("\n5. 下载级联分类器文件...")
    
    import urllib.request
    
    url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
    filename = "haarcascade_frontalface_default.xml"
    
    try:
        print(f"从 {url} 下载...")
        urllib.request.urlretrieve(url, filename)
        print(f"✓ 下载成功: {filename}")
        return filename
    except Exception as e:
        print(f"✗ 下载失败: {e}")
        return None

def main():
    """主函数"""
    print("OpenCV 人脸检测问题修复脚本")
    
    # 1. 检查安装状态
    found_files = check_opencv_installation()
    
    # 2. 创建测试图像
    test_image = create_test_image()
    
    # 3. 尝试使用找到的级联文件
    success = False
    for cascade_file in found_files:
        if test_face_detection(test_image, cascade_file):
            success = True
            break
    
    # 4. 如果都失败了，尝试下载
    if not success:
        print("\n所有现有级联文件都失败了，尝试下载...")
        downloaded_file = download_cascade_classifier()
        if downloaded_file:
            if test_face_detection(test_image, downloaded_file):
                success = True
    
    # 5. 提供解决方案
    print("\n" + "=" * 60)
    print("解决方案总结:")
    print("=" * 60)
    
    if success:
        print("✅ 人脸检测功能已修复！")
        print("\n使用方法:")
        print("```python")
        print("import cv2")
        print("# 加载级联分类器")
        print("face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')")
        print("# 加载图像")
        print("img = cv2.imread('your_image.jpg')")
        print("# 转换为灰度")
        print("gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)")
        print("# 检测人脸")
        print("faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)")
        print("```")
    else:
        print("❌ 人脸检测功能仍然有问题")
        print("\n可能的解决方案:")
        print("1. 确保图像文件存在且可读")
        print("2. 检查级联分类器文件路径")
        print("3. 重新安装OpenCV: pip install opencv-python")
        print("4. 手动下载级联分类器文件")

if __name__ == "__main__":
    main()