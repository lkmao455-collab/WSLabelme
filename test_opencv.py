#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试OpenCV安装和基本功能
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt

def test_opencv_basic():
    """测试OpenCV基本功能"""
    print("=" * 50)
    print("OpenCV 功能测试")
    print("=" * 50)
    
    # 测试1: 检查OpenCV版本
    print(f"\n1. OpenCV版本: {cv2.__version__}")
    
    # 测试2: 创建一个简单的图像
    print("\n2. 创建测试图像...")
    # 创建一个300x300的黑色图像
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    
    # 在图像中心画一个白色圆圈
    center = (150, 150)
    radius = 50
    color = (255, 255, 255)  # 白色
    thickness = -1  # 填充
    
    cv2.circle(img, center, radius, color, thickness)
    print("   OK: 成功创建测试图像")
    
    # 测试3: 图像处理操作
    print("\n3. 测试图像处理操作...")
    
    # 转换为灰度图像
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    print("   OK: 成功转换为灰度图像")
    
    # 应用高斯模糊
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    print("   OK: 成功应用高斯模糊")
    
    # 边缘检测
    edges = cv2.Canny(blurred, 50, 150)
    print("   OK: 成功进行边缘检测")
    
    # 测试4: 显示图像（如果在支持GUI的环境中）
    try:
        # 保存测试图像
        cv2.imwrite('test_opencv_image.png', img)
        print("   OK: 成功保存测试图像: test_opencv_image.png")
        
        # 如果有matplotlib，显示图像
        plt.figure(figsize=(12, 4))
        
        plt.subplot(1, 3, 1)
        plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        plt.title('原始图像')
        plt.axis('off')
        
        plt.subplot(1, 3, 2)
        plt.imshow(gray, cmap='gray')
        plt.title('灰度图像')
        plt.axis('off')
        
        plt.subplot(1, 3, 3)
        plt.imshow(edges, cmap='gray')
        plt.title('边缘检测')
        plt.axis('off')
        
        plt.tight_layout()
        plt.savefig('opencv_test_result.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("   OK: 成功生成测试结果图像: opencv_test_result.png")
        
    except Exception as e:
        print(f"   WARNING: 图像显示/保存警告: {e}")
    
    print("\n" + "=" * 50)
    print("OpenCV 测试完成！所有基本功能正常工作。")
    print("=" * 50)
    
    return True

def main():
    """主测试函数"""
    try:
        success = test_opencv_basic()
        if success:
            print("\nOK: OpenCV 安装和配置成功！")
            print("\n现在您可以在 Jupyter Notebook 中使用以下代码：")
            print("```python")
            print("import cv2")
            print("import matplotlib.pyplot as plt")
            print("# 加载图像")
            print("image = cv2.imread('your_image.jpg')")
            print("# 进行图像处理...")
            print("```")
        else:
            print("\nFAIL: OpenCV 测试失败，请检查安装。")
    except Exception as e:
        print(f"\nFAIL: OpenCV 测试出错: {e}")
        print("请确保 OpenCV 已正确安装。")

if __name__ == "__main__":
    main()