import base64
import contextlib
import io
import json
import os.path as osp

import PIL.Image
from loguru import logger

from labelme import __version__
from labelme import utils

PIL.Image.MAX_IMAGE_PIXELS = None


@contextlib.contextmanager
def open(name, mode):
    """
    文件打开上下文管理器
    
    提供统一的文件打开方式，确保使用UTF-8编码。
    
    Args:
        name: 文件路径
        mode: 打开模式（"r"或"w"）
    """
    assert mode in ["r", "w"]
    encoding = "utf-8"
    yield io.open(name, mode, encoding=encoding)
    return


class LabelFileError(Exception):
    """
    LabelFile操作异常类
    
    用于处理LabelFile操作过程中可能出现的各种异常。
    """
    pass


class LabelFile(object):
    """
    标注文件类
    
    负责处理Labelme标注文件的加载、保存和管理。标注文件采用JSON格式，
    包含图像信息、标注形状、标志位等数据。
    
    主要功能：
    - 加载和保存JSON格式的标注文件
    - 处理图像数据的编码和解码
    - 验证图像尺寸信息
    - 管理标注形状数据
    """
    suffix = ".json"  # 标注文件的扩展名

    def __init__(self, filename=None):
        """
        初始化LabelFile对象
        
        Args:
            filename: 标注文件路径（可选）
        """
        self.shapes = []        # 标注形状列表
        self.imagePath = None   # 图像文件路径
        self.imageData = None   # 图像数据（base64编码）
        if filename is not None:
            self.load(filename)
        self.filename = filename  # 标注文件路径

    @staticmethod
    def load_image_file(filename):
        """
        加载图像文件
        
        从指定路径加载图像文件，并处理EXIF方向信息，将图像转换为字节数据。
        
        Args:
            filename: 图像文件路径
            
        Returns:
            bytes: 图像的字节数据，如果加载失败返回None
        """
        try:
            image_pil = PIL.Image.open(filename)
        except IOError:
            logger.error("Failed opening image file: {}".format(filename))
            return

        # 根据EXIF信息应用图像方向
        image_pil = utils.apply_exif_orientation(image_pil)

        with io.BytesIO() as f:
            ext = osp.splitext(filename)[1].lower()
            if ext in [".jpg", ".jpeg"]:
                format = "JPEG"
            else:
                format = "PNG"
            image_pil.save(f, format=format)
            f.seek(0)
            return f.read()

    def load(self, filename):
        """
        加载标注文件
        
        从JSON文件中加载标注数据，包括图像信息、标注形状、标志位等。
        
        Args:
            filename: 标注文件路径
            
        Raises:
            LabelFileError: 当文件加载失败时抛出异常
        """
        # 定义主要数据键
        keys = [
            "version",        # Labelme版本
            "imageData",      # 图像数据（base64编码）
            "imagePath",      # 图像文件路径
            "shapes",         # 多边形标注
            "flags",          # 图像级别标志
            "imageHeight",    # 图像高度
            "imageWidth",     # 图像宽度
        ]
        
        # 定义形状数据键
        shape_keys = [
            "label",         # 标签名称
            "points",        # 顶点坐标
            "group_id",      # 组ID
            "shape_type",    # 形状类型
            "flags",         # 形状标志
            "description",   # 描述信息
            "mask",          # 掩码数据
        ]
        
        try:
            with open(filename, "r") as f:
                data = json.load(f)

            # 解码图像数据
            if data["imageData"] is not None:
                imageData = base64.b64decode(data["imageData"])
            else:
                # 从标注文件路径计算相对图像路径
                imagePath = osp.join(osp.dirname(filename), data["imagePath"])
                imageData = self.load_image_file(imagePath)
            
            # 获取标志位，如果没有则使用空字典
            flags = data.get("flags") or {}
            imagePath = data["imagePath"]
            
            # 检查图像尺寸信息
            self._check_image_height_and_width(
                base64.b64encode(imageData).decode("utf-8"),
                data.get("imageHeight"),
                data.get("imageWidth"),
            )
            
            # 处理标注形状数据
            shapes = [
                dict(
                    label=s["label"],
                    points=s["points"],
                    shape_type=s.get("shape_type", "polygon"),
                    flags=s.get("flags", {}),
                    description=s.get("description"),
                    group_id=s.get("group_id"),
                    mask=utils.img_b64_to_arr(s["mask"]).astype(bool)
                    if s.get("mask")
                    else None,
                    # 保存其他未处理的数据
                    other_data={k: v for k, v in s.items() if k not in shape_keys},
                )
                for s in data["shapes"]
            ]
        except Exception as e:
            raise LabelFileError(e)

        # 处理其他未识别的数据
        otherData = {}
        for key, value in data.items():
            if key not in keys:
                otherData[key] = value

        # 只有在所有数据加载完成后才替换现有数据
        self.flags = flags
        self.shapes = shapes
        self.imagePath = imagePath
        self.imageData = imageData
        self.filename = filename
        self.otherData = otherData

    @staticmethod
    def _check_image_height_and_width(imageData, imageHeight, imageWidth):
        """
        检查并验证图像尺寸信息
        
        比较JSON文件中记录的图像尺寸与实际图像数据的尺寸，
        如果不匹配则使用实际尺寸并记录错误日志。
        
        Args:
            imageData: base64编码的图像数据
            imageHeight: JSON中记录的图像高度
            imageWidth: JSON中记录的图像宽度
            
        Returns:
            tuple: (实际高度, 实际宽度)
        """
        img_arr = utils.img_b64_to_arr(imageData)
        if imageHeight is not None and img_arr.shape[0] != imageHeight:
            logger.error(
                "imageHeight does not match with imageData or imagePath, "
                "so getting imageHeight from actual image."
            )
            imageHeight = img_arr.shape[0]
        if imageWidth is not None and img_arr.shape[1] != imageWidth:
            logger.error(
                "imageWidth does not match with imageData or imagePath, "
                "so getting imageWidth from actual image."
            )
            imageWidth = img_arr.shape[1]
        return imageHeight, imageWidth

    def save(
        self,
        filename,
        shapes,
        imagePath,
        imageHeight,
        imageWidth,
        imageData=None,
        otherData=None,
        flags=None,
    ):
        """
        保存标注文件
        
        将标注数据保存为JSON格式的文件，包括图像信息、标注形状、标志位等。
        
        Args:
            filename: 要保存的文件路径
            shapes: 标注形状列表
            imagePath: 图像文件路径
            imageHeight: 图像高度
            imageWidth: 图像宽度
            imageData: 图像数据（可选）
            otherData: 其他数据（可选）
            flags: 标志位字典（可选）
            
        Raises:
            LabelFileError: 当文件保存失败时抛出异常
        """
        # 如果提供了图像数据，先进行base64编码
        if imageData is not None:
            imageData = base64.b64encode(imageData).decode("utf-8")
            # 检查并验证图像尺寸
            imageHeight, imageWidth = self._check_image_height_and_width(
                imageData, imageHeight, imageWidth
            )
        
        # 处理可选参数的默认值
        if otherData is None:
            otherData = {}
        if flags is None:
            flags = {}
        
        # 构建JSON数据结构
        data = dict(
            version=__version__,      # Labelme版本信息
            flags=flags,              # 图像级别标志
            shapes=shapes,            # 标注形状列表
            imagePath=imagePath,      # 图像文件路径
            imageData=imageData,      # 图像数据（base64编码）
            imageHeight=imageHeight,  # 图像高度
            imageWidth=imageWidth,    # 图像宽度
        )
        
        # 添加其他未处理的数据
        for key, value in otherData.items():
            assert key not in data, f"Key '{key}' already exists in data"
            data[key] = value
        
        # 保存JSON文件
        try:
            with open(filename, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.filename = filename
        except Exception as e:
            raise LabelFileError(e)

    @staticmethod
    def is_label_file(filename):
        """
        判断文件是否为标注文件
        
        通过检查文件扩展名来判断指定文件是否为Labelme标注文件。
        
        Args:
            filename: 文件路径
            
        Returns:
            bool: 如果是标注文件返回True，否则返回False
        """
        return osp.splitext(filename)[1].lower() == LabelFile.suffix
