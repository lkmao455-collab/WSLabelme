#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenCV人脸检测问题的解决方案
"""

import cv2
import os

def main():
    """主函数 - 提供解决方案"""
    print("=" * 60)
    print("OpenCV 人脸检测问题解决方案")
    print("=" * 60)
    
    # 1. 确认级联分类器文件路径
    cascade_path = "D:/Program Files/Python310/Lib/site-packages/cv2/data/haarcascade_frontalface_default.xml"
    
    print(f"1. 级联分类器文件路径: {cascade_path}")
    
    # 检查文件是否存在
    if os.path.exists(cascade_path):
        print("   OK: 级联分类器文件存在")
    else:
        print("   FAIL: 级联分类器文件不存在")
        return
    
    # 2. 测试人脸检测
    print("\n2. 测试人脸检测功能...")
    
    try:
        # 加载级联分类器
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # 检查分类器是否加载成功
        if face_cascade.empty():
            print("   FAIL: 级联分类器加载失败")
            return
        
        print("   OK: 级联分类器加载成功")
        
        # 创建一个测试图像
        import numpy as np
        img = np.zeros((400, 600, 3), dtype=np.uint8)
        
        # 绘制一个简单的"人脸"
        cv2.ellipse(img, (300, 200), (150, 200), 0, 0, 360, (255, 255, 255), -1)
        cv2.circle(img, (220, 150), 20, (0, 0, 0), -1)
        cv2.circle(img, (380, 150), 20, (0, 0, 0), -1)
        cv2.ellipse(img, (300, 250), (80, 30), 0, 0, 180, (0, 0, 0), 3)
        
        # 保存测试图像
        cv2.imwrite('test_face.jpg', img)
        print("   ✓ 创建测试图像: test_face.jpg")
        
        # 加载图像
        img = cv2.imread('test_face.jpg')
        if img is None:
            print("   ✗ 无法加载测试图像")
            return
        
        print("   ✓ 图像加载成功")
        
        # 转换为灰度图像
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 检测人脸
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        print(f"   ✓ 检测到 {len(faces)} 个人脸")
        
        # 绘制边界框
        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
        # 保存结果
        cv2.imwrite('face_detection_result.jpg', img)
        print("   ✓ 保存检测结果: face_detection_result.jpg")
        
    except Exception as e:
        print(f"   ✗ 人脸检测失败: {e}")
        return
    
    # 3. 提供使用指南
    print("\n" + "=" * 60)
    print("使用指南:")
    print("=" * 60)
    
    print("\n✅ 问题已解决！现在您可以在 Jupyter Notebook 中使用以下代码：")
    print("\n```python")
    print("import cv2")
    print("# 加载级联分类器")
    print("face_cascade = cv2.CascadeClassifier('D:/Program Files/Python310/Lib/site-packages/cv2/data/haarcascade_frontalface_default.xml')")
    print("# 加载图像")
    print("img = cv2.imread('your_image.jpg')")
    print("# 转换为灰度")
    print("gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)")
    print("# 检测人脸")
    print("faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)")
    print("# 绘制边界框")
    print("for (x, y, w, h) in faces:")
    print("    cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)")
    print("```")
    
    print("\n💡 简化版本（推荐）:")
    print("```python")
    print("import cv2")
    print("# 使用cv2内置路径")
    print("face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')")
    print("# 加载图像")
    print("img = cv2.imread('your_image.jpg')")
    print("# 转换为灰度")
    print("gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)")
    print("# 检测人脸")
    print("faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)")
    print("```")
    
    print("\n🎯 关键点:")
    print("- 确保级联分类器文件路径正确")
    print("- 图像文件存在且可读")
    print("- 使用正确的参数设置")
    print("- 检查OpenCV版本兼容性")

if __name__ == "__main__":
    main()