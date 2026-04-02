# MIT License
# Copyright (c) Kentaro Wada

# 文件头部说明:
# 本模块提供了Labelme中图像处理的核心工具函数。
# 主要功能包括：图像格式转换（Base64、数组、PIL、Qt等格式之间的转换）、
# EXIF方向信息处理、图像数据编码解码等。
# 这些函数是Labelme图像处理的基础，被广泛用于图像的加载、保存和显示。

import base64
import io

import numpy as np
import PIL.ExifTags
import PIL.Image
import PIL.ImageOps


def img_data_to_pil(img_data):
    """
    将图像数据转换为PIL图像对象
    
    将字节形式的图像数据转换为PIL.Image对象，便于后续处理。
    
    Args:
        img_data: 图像数据字节
        
    Returns:
        PIL.Image: PIL图像对象
    """
    f = io.BytesIO()
    f.write(img_data)
    img_pil = PIL.Image.open(f)
    return img_pil


def img_data_to_arr(img_data):
    """
    将图像数据转换为numpy数组
    
    将字节形式的图像数据转换为numpy数组格式，便于数值计算和处理。
    
    Args:
        img_data: 图像数据字节
        
    Returns:
        numpy.ndarray: 图像数组
    """
    img_pil = img_data_to_pil(img_data)
    img_arr = np.array(img_pil)
    return img_arr


def img_b64_to_arr(img_b64):
    """
    将Base64编码的图像转换为numpy数组
    
    将Base64编码的图像字符串解码并转换为numpy数组格式。
    
    Args:
        img_b64: Base64编码的图像字符串
        
    Returns:
        numpy.ndarray: 图像数组
    """
    img_data = base64.b64decode(img_b64)
    img_arr = img_data_to_arr(img_data)
    return img_arr


def img_pil_to_data(img_pil):
    """
    将PIL图像对象转换为图像数据
    
    将PIL.Image对象转换为字节形式的图像数据，便于保存或传输。
    
    Args:
        img_pil: PIL图像对象
        
    Returns:
        bytes: 图像数据字节
    """
    f = io.BytesIO()
    img_pil.save(f, format="PNG")
    img_data = f.getvalue()
    return img_data


def img_arr_to_b64(img_arr):
    """
    将numpy数组转换为Base64编码
    
    将numpy数组格式的图像转换为Base64编码的字符串，便于存储和传输。
    
    Args:
        img_arr: 图像数组
        
    Returns:
        str: Base64编码的图像字符串
    """
    img_data = img_arr_to_data(img_arr)
    img_b64 = base64.b64encode(img_data).decode("utf-8")
    return img_b64


def img_arr_to_data(img_arr):
    """
    将numpy数组转换为图像数据
    
    将numpy数组格式的图像转换为字节形式的图像数据。
    
    Args:
        img_arr: 图像数组
        
    Returns:
        bytes: 图像数据字节
    """
    img_pil = PIL.Image.fromarray(img_arr)
    img_data = img_pil_to_data(img_pil)
    return img_data


def img_data_to_png_data(img_data):
    """
    将图像数据转换为PNG格式数据
    
    将任意格式的图像数据转换为PNG格式的字节数据。
    
    Args:
        img_data: 图像数据字节
        
    Returns:
        bytes: PNG格式的图像数据
    """
    with io.BytesIO() as f:
        f.write(img_data)
        img = PIL.Image.open(f)

        with io.BytesIO() as f:
            img.save(f, "PNG")
            f.seek(0)
            return f.read()


def img_qt_to_arr(img_qt):
    """
    将Qt图像对象转换为numpy数组
    
    将Qt框架中的图像对象转换为numpy数组格式，便于处理。
    
    Args:
        img_qt: Qt图像对象
        
    Returns:
        numpy.ndarray: 图像数组
    """
    w, h, d = img_qt.size().width(), img_qt.size().height(), img_qt.depth()
    bytes_ = img_qt.bits().asstring(w * h * d // 8)
    img_arr = np.frombuffer(bytes_, dtype=np.uint8).reshape((h, w, d // 8))
    return img_arr


def apply_exif_orientation(image):
    """
    应用EXIF方向信息校正图像
    
    根据图像的EXIF信息中的方向标记，自动旋转或翻转图像以获得正确的显示方向。
    这在处理手机拍摄的照片时特别重要，因为这些照片通常包含方向信息。
    
    Args:
        image: PIL图像对象
        
    Returns:
        PIL.Image: 应用方向校正后的图像
    """
    try:
        exif = image._getexif()
    except AttributeError:
        exif = None

    if exif is None:
        return image

    # 提取有效的EXIF标签
    exif = {PIL.ExifTags.TAGS[k]: v for k, v in exif.items() if k in PIL.ExifTags.TAGS}

    orientation = exif.get("Orientation", None)

    # 根据EXIF方向标记进行相应的图像变换
    if orientation == 1:
        # 正常方向，无需处理
        return image
    elif orientation == 2:
        # 左右镜像
        return PIL.ImageOps.mirror(image)
    elif orientation == 3:
        # 旋转180度
        return image.transpose(PIL.Image.ROTATE_180)
    elif orientation == 4:
        # 上下翻转
        return PIL.ImageOps.flip(image)
    elif orientation == 5:
        # 旋转270度后左右镜像
        return PIL.ImageOps.mirror(image.transpose(PIL.Image.ROTATE_270))
    elif orientation == 6:
        # 旋转270度
        return image.transpose(PIL.Image.ROTATE_270)
    elif orientation == 7:
        # 旋转90度后左右镜像
        return PIL.ImageOps.mirror(image.transpose(PIL.Image.ROTATE_90))
    elif orientation == 8:
        # 旋转90度
        return image.transpose(PIL.Image.ROTATE_90)
    else:
        # 未知方向，返回原图
        return image
