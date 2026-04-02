import os.path as osp
import shutil
import sys

import yaml
from loguru import logger

here = osp.dirname(osp.abspath(__file__))

# 文件头部说明:
# 本模块是Labelme配置管理模块。
# 主要功能包括：配置文件加载、配置项验证、配置合并等。
# 这是Labelme应用程序配置管理的核心模块，支持默认配置、用户配置和命令行配置。

def update_dict(target_dict, new_dict, validate_item=None):
    """
    更新字典配置
    
    递归地将新配置字典合并到目标字典中，支持嵌套字典。
    
    Args:
        target_dict: 目标字典
        new_dict: 新配置字典
        validate_item: 验证函数，用于验证配置项
    """
    for key, value in new_dict.items():
        if validate_item:
            validate_item(key, value)
        if key not in target_dict:
            logger.warning("Skipping unexpected key in config: {}".format(key))
            continue
        if isinstance(target_dict[key], dict) and isinstance(value, dict):
            # 如果都是字典，递归合并
            update_dict(target_dict[key], value, validate_item=validate_item)
        else:
            # 否则直接赋值
            target_dict[key] = value


# -----------------------------------------------------------------------------

def _get_app_dir():
    if getattr(sys, "frozen", False):
        return osp.dirname(sys.executable)
    package_dir = osp.dirname(osp.dirname(osp.abspath(__file__)))
    return osp.dirname(package_dir)


def get_default_config():
    """
    获取默认配置
    
    从默认配置文件加载配置，并在用户目录创建配置文件副本。
    
    Returns:
        dict: 默认配置字典
    
    Raises:
        FileNotFoundError: 当配置文件不存在时
        yaml.YAMLError: 当配置文件格式错误时
    """
    config_file = osp.join(here, "default_config.yaml")
    try:
        with open(config_file, encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("Default config file not found: {}".format(config_file))
        raise
    except yaml.YAMLError as e:
        logger.error("Error parsing config file {}: {}".format(config_file, e))
        raise

    # 将默认配置保存到应用目录 .labelmerc
    user_config_file = osp.join(_get_app_dir(), ".labelmerc")
    legacy_config_file = osp.join(osp.expanduser("~"), ".labelmerc")
    if not osp.exists(user_config_file):
        try:
            if osp.exists(legacy_config_file):
                shutil.copy(legacy_config_file, user_config_file)
            else:
                shutil.copy(config_file, user_config_file)
        except Exception as e:
            logger.warning("Failed to save config to {}: {}".format(user_config_file, e))

    return config


def validate_config_item(key, value):
    """
    验证配置项
    
    对特定的配置项进行有效性验证。
    
    Args:
        key: 配置项键名
        value: 配置项值
        
    Raises:
        ValueError: 当配置项值无效时抛出异常
    """
    if key == "validate_label" and value not in [None, "exact"]:
        raise ValueError(
            "Unexpected value for config key 'validate_label': {}".format(value)
        )
    if key == "shape_color" and value not in [None, "auto", "manual"]:
        raise ValueError(
            "Unexpected value for config key 'shape_color': {}".format(value)
        )
    if key == "labels" and value is not None and len(value) != len(set(value)):
        raise ValueError(
            "Duplicates are detected for config key 'labels': {}".format(value)
        )


def get_config(config_file_or_yaml=None, config_from_args=None):
    """
    获取配置
    
    按优先级合并多个配置源：默认配置 -> 文件配置 -> 命令行配置。
    
    Args:
        config_file_or_yaml: 配置文件路径或YAML字符串
        config_from_args: 命令行参数配置
        
    Returns:
        dict: 合并后的配置字典
    """
    # 1. 获取默认配置
    config = get_default_config()

    # 2. 加载文件或YAML配置
    # 2. 加载文件或 YAML 配置
    if config_file_or_yaml is not None:
        try:
            config_from_yaml = yaml.safe_load(config_file_or_yaml)
            if not isinstance(config_from_yaml, dict):
                # 如果不是字典，说明是文件路径
                config_file = config_from_yaml
                with open(config_file, encoding='utf-8') as f:
                    logger.info("Loading config file from: {}".format(config_file))
                    config_from_yaml = yaml.safe_load(f)
            # 合并配置
            update_dict(config, config_from_yaml, validate_item=validate_config_item)
        except FileNotFoundError:
            logger.error("Config file not found: {}".format(config_file_or_yaml))
            raise
        except yaml.YAMLError as e:
            logger.error("Error parsing config {}: {}".format(config_file_or_yaml, e))
            raise
        except Exception as e:
            logger.error("Error loading config: {}".format(e))
            raise

    # 3. 合并命令行配置
    if config_from_args is not None:
        update_dict(config, config_from_args, validate_item=validate_config_item)

    return config
