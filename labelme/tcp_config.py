# -*- coding: utf-8 -*-
"""
TCP客户端配置文件管理模块
用于加载、保存和管理TCP客户端配置
"""

import os
import os.path as osp
import sys
import yaml
from loguru import logger
from typing import Dict, Any


def get_config_path() -> str:
    """
    获取TCP配置文件路径
    
    Returns:
        str: 配置文件路径 (~/.labelme_tcp_config.yaml)
    """
    if getattr(sys, "frozen", False):
        app_dir = osp.dirname(sys.executable)
    else:
        package_dir = osp.dirname(osp.abspath(__file__))
        app_dir = osp.dirname(package_dir)
    return osp.join(app_dir, ".labelme_tcp_config.yaml")


def get_default_config() -> Dict[str, Any]:
    """
    获取默认TCP配置
    
    Returns:
        dict: 默认配置字典
    """
    return {
        "host": "127.0.0.1",
        "port": 10012,
        "message": "labelme",
        "interval": 2,  # 发送间隔（秒）
        "reconnect_interval": 5,  # 重连间隔（秒）
    }


def load_tcp_config() -> Dict[str, Any]:
    """
    加载TCP配置文件
    如果配置文件不存在，则创建新文件并写入默认配置
    
    Returns:
        dict: TCP配置字典
    """
    config_path = get_config_path()
    legacy_config_path = osp.join(osp.expanduser("~"), ".labelme_tcp_config.yaml")
    
    # 如果配置文件不存在，创建新文件并写入默认配置
    if not osp.exists(config_path):
        if osp.exists(legacy_config_path):
            try:
                os.makedirs(osp.dirname(config_path), exist_ok=True)
                with open(legacy_config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or get_default_config()
                save_tcp_config(config)
                logger.info(f"已迁移TCP配置到: {config_path}")
                return config
            except Exception as e:
                logger.warning(f"迁移TCP配置失败: {e}")
        logger.info(f"TCP配置文件不存在，创建新配置文件: {config_path}")
        default_config = get_default_config()
        save_tcp_config(default_config)
        return default_config
    
    # 加载现有配置
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            if config is None:
                logger.warning("配置文件为空，使用默认配置")
                config = get_default_config()
                save_tcp_config(config)
            else:
                # 验证配置完整性，缺失的字段使用默认值
                default_config = get_default_config()
                for key, default_value in default_config.items():
                    if key not in config:
                        logger.warning(f"配置文件中缺少字段 '{key}'，使用默认值: {default_value}")
                        config[key] = default_value
            logger.info(f"成功加载TCP配置: {config_path}")
            return config
    except Exception as e:
        logger.error(f"加载TCP配置文件失败: {e}，使用默认配置")
        default_config = get_default_config()
        save_tcp_config(default_config)
        return default_config


def save_tcp_config(config: Dict[str, Any]) -> bool:
    """
    保存TCP配置到文件
    
    Args:
        config: 配置字典
        
    Returns:
        bool: 是否保存成功
    """
    config_path = get_config_path()
    
    try:
        # 确保目录存在
        config_dir = osp.dirname(config_path)
        if config_dir and not osp.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        # 保存配置
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True)
        logger.info(f"成功保存TCP配置: {config_path}")
        return True
    except Exception as e:
        logger.error(f"保存TCP配置文件失败: {e}")
        return False
