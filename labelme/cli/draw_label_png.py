import argparse
import os

import imgviz
import matplotlib.pyplot as plt
import numpy as np
from loguru import logger

# 文件头部说明:
# 本模块是Labelme的命令行工具，用于可视化标签PNG图像。
# 主要功能包括：显示标签图像、显示带叠加的标签图像、显示标签值统计等。
# 这是开发者和用户查看和验证标签图像的重要工具。

def main():
    """
    主函数
    
    解析命令行参数，读取标签PNG文件和可选的原始图像文件，
    并显示标签图像的可视化结果。
    """
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("label_png", help="label PNG file")  # 标签PNG文件
    parser.add_argument(
        "--labels",
        help="labels list (comma separated text or file)",
        default=None,
    )  # 标签名称列表
    parser.add_argument("--image", help="image file", default=None)  # 原始图像文件
    args = parser.parse_args()

    # 处理标签名称
    if args.labels is not None:
        if os.path.exists(args.labels):
            # 如果标签文件存在，从文件读取标签名称
            with open(args.labels) as f:
                label_names = [label.strip() for label in f]
        else:
            # 否则从命令行参数解析标签名称
            label_names = args.labels.split(",")
    else:
        label_names = None

    # 处理原始图像
    if args.image is not None:
        image = imgviz.io.imread(args.image)  # 读取原始图像
    else:
        image = None

    # 读取标签图像
    label = imgviz.io.imread(args.label_png)
    label = label.astype(np.int32)  # 转换为整数类型
    label[label == 255] = -1  # 将255标记为-1（通常表示忽略区域）

    # 获取唯一的标签值
    unique_label_values = np.unique(label)

    # 记录标签信息
    logger.info("Label image shape: {}".format(label.shape))
    logger.info("Label values: {}".format(unique_label_values.tolist()))
    if label_names is not None:
        logger.info(
            "Label names: {}".format(
                [
                    "{}:{}".format(label_value, label_names[label_value])
                    for label_value in unique_label_values
                ]
            )
        )

    # 确定子图数量
    if args.image:
        num_cols = 2  # 如果有原始图像，显示两列
    else:
        num_cols = 1  # 否则只显示一列

    # 创建显示窗口
    plt.figure(figsize=(num_cols * 6, 5))

    # 显示标签图像
    plt.subplot(1, num_cols, 1)
    plt.title(args.label_png)
    label_viz = imgviz.label2rgb(
        label=label, label_names=label_names, font_size=label.shape[1] // 30
    )
    plt.imshow(label_viz)

    # 如果有原始图像，显示叠加效果
    if image is not None:
        plt.subplot(1, num_cols, 2)
        label_viz_with_overlay = imgviz.label2rgb(
            label=label,
            image=image,
            label_names=label_names,
            font_size=label.shape[1] // 30,
        )
        plt.title("{}\n{}".format(args.label_png, args.image))
        plt.imshow(label_viz_with_overlay)

    plt.tight_layout()  # 调整子图布局
    plt.show()          # 显示图像窗口


if __name__ == "__main__":
    main()
