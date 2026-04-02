import argparse
import os
import os.path as osp

import numpy as np
import numpy.typing as npt
import imgviz
import PIL.Image
from loguru import logger

from labelme.label_file import LabelFile
from labelme import utils

# 文件头部说明:
# 本模块是Labelme的命令行工具，用于导出JSON标注文件为标准数据集格式。
# 主要功能包括：生成图像文件、标签文件、可视化文件和标签名称文件。
# 这是数据导出和格式转换的重要工具，用于机器学习训练和数据共享。

def main():
    """
    主函数
    
    将JSON标注文件导出为标准数据集格式，包括原始图像、标签图像、
    可视化图像和标签名称文件。
    """
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser()
    parser.add_argument("json_file")      # JSON文件路径
    parser.add_argument("-o", "--out", default=None)  # 输出目录
    args = parser.parse_args()

    json_file = args.json_file

    # 确定输出目录
    if args.out is None:
        # 如果未指定输出目录，使用JSON文件名（不含扩展名）创建目录
        out_dir = osp.splitext(osp.basename(json_file))[0]
        out_dir = osp.join(osp.dirname(json_file), out_dir)
    else:
        out_dir = args.out
    
    # 创建输出目录
    if not osp.exists(out_dir):
        os.mkdir(out_dir)

    # 读取JSON标注文件
    label_file: LabelFile = LabelFile(filename=json_file)

    # 将图像数据转换为numpy数组
    image: npt.NDArray[np.uint8] = utils.img_data_to_arr(label_file.imageData)

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
    lbl, _ = utils.shapes_to_label(image.shape, label_file.shapes, label_name_to_value)

    # 创建标签名称列表
    label_names = [None] * (max(label_name_to_value.values()) + 1)
    for name, value in label_name_to_value.items():
        label_names[value] = name

    # 生成标签可视化图像
    lbl_viz = imgviz.label2rgb(
        lbl, imgviz.asgray(image), label_names=label_names, loc="rb"
    )

    # 保存各种输出文件
    PIL.Image.fromarray(image).save(osp.join(out_dir, "img.png"))           # 原始图像
    utils.lblsave(osp.join(out_dir, "label.png"), lbl)                      # 标签图像
    PIL.Image.fromarray(lbl_viz).save(osp.join(out_dir, "label_viz.png"))   # 可视化图像

    # 保存标签名称文件
    with open(osp.join(out_dir, "label_names.txt"), "w") as f:
        for lbl_name in label_names:
            f.write(lbl_name + "\n")

    logger.info("Saved to: {}".format(out_dir))


if __name__ == "__main__":
    main()
