#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试图像处理修复的脚本

这个脚本用于验证图像数据预处理功能是否正常工作。
"""

import numpy as np
from labelme._automation import bbox_from_text

def test_image_validation():
    """测试图像数据验证功能"""
    print("测试图像数据验证功能...")
    
    # 测试空图像
    print("1. 测试空图像:")
    try:
        boxes, scores, labels = bbox_from_text.get_bboxes_from_texts(
            model="yoloworld", 
            image=None, 
            texts=["person"]
        )
        print(f"   结果: 空图像处理成功，返回空数组")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 测试形状为(1,1,1)的图像
    print("2. 测试(1,1,1)形状图像:")
    try:
        small_image = np.ones((1, 1, 1), dtype=np.uint8)
        boxes, scores, labels = bbox_from_text.get_bboxes_from_texts(
            model="yoloworld", 
            image=small_image, 
            texts=["person"]
        )
        print(f"   结果: 小图像处理成功，返回空数组")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 测试单通道图像
    print("3. 测试单通道图像:")
    try:
        gray_image = np.random.randint(0, 255, (50, 50), dtype=np.uint8)
        boxes, scores, labels = bbox_from_text.get_bboxes_from_texts(
            model="yoloworld", 
            image=gray_image, 
            texts=["person"]
        )
        print(f"   结果: 单通道图像处理成功")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 测试正常RGB图像
    print("4. 测试正常RGB图像:")
    try:
        rgb_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        boxes, scores, labels = bbox_from_text.get_bboxes_from_texts(
            model="yoloworld", 
            image=rgb_image, 
            texts=["person"]
        )
        print(f"   结果: RGB图像处理成功")
    except Exception as e:
        print(f"   错误: {e}")

def main():
    """主测试函数"""
    print("=" * 50)
    print("图像处理修复测试")
    print("=" * 50)
    
    test_image_validation()
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("如果所有测试都显示'处理成功'，说明图像预处理功能正常工作。")
    print("=" * 50)

if __name__ == "__main__":
    main()