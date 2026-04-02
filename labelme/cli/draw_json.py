#!/usr/bin/env python

import argparse

import imgviz
import matplotlib.pyplot as plt

from labelme import utils
from labelme.label_file import LabelFile

# 文件头部说明:
# 本模块是Labelme的命令行工具，用于可视化JSON标注文件。
# 主要功能包括：读取JSON标注文件、显示原始图像、显示标注标签图像等。
# 这是开发者和用户查看和验证标注结果的重要工具。

def main():
    """
    主函数
    
    解析命令行参数，读取JSON标注文件，并显示原始图像和标注标签图像。
    """
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file")  # 添加JSON文件参数
    args = parser.parse_args()

    # 读取JSON标注文件
    label_file = LabelFile(args.json_file)
    img = utils.img_data_to_arr(label_file.imageData)  # 将图像数据转换为数组

    # 创建标签名称到数值的映射字典
    label_name_to_value = {"_background_": 0}
    for shape in sorted(label_file.shapes, key=lambda x: x["label"]):
        label_name = shape["label"]
        if label_name in label_name_to_value:
            label_value = label_name_to_value[label_name]
        else:
            label_value = len(label_name_to_value)
            label_name_to_value[label_name] = label_value
    
    # 将形状数据转换为标签数组
    lbl, _ = utils.shapes_to_label(img.shape, label_file.shapes, label_name_to_value)

    # 创建标签名称列表
    label_names = [None] * (max(label_name_to_value.values()) + 1)
    for name, value in label_name_to_value.items():
        label_names[value] = name
    
    # 生成标签可视化图像
    lbl_viz = imgviz.label2rgb(
        lbl,                           # 标签数组
        imgviz.asgray(img),            # 灰度背景图像
        label_names=label_names,       # 标签名称列表
        font_size=30,                  # 字体大小
        loc="rb",                      # 图例位置（右下角）
    )

    # 显示图像
    plt.subplot(121)  # 创建子图1
    plt.imshow(img)   # 显示原始图像
    plt.subplot(122)  # 创建子图2
    plt.imshow(lbl_viz)  # 显示标签可视化图像
    plt.show()        # 显示图像窗口


if __name__ == "__main__":
    main()
