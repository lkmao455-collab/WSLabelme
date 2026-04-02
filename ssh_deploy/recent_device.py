# -*- coding: utf-8 -*-
"""
最近连接设备存储模块

使用简单的TXT文件存储最近一次连接成功的设备信息。
"""

import os
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class RecentDevice:
    """最近连接设备信息"""
    host: str
    port: int
    device_type: str
    username: str
    password: str
    target_path: str = "/mmcblk1p2"
    last_file_path: str = ""  # 最后选择的文件路径
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class RecentDeviceStorage:
    """
    最近连接设备存储类
    
    使用TXT文件存储最近一次连接成功的设备信息。
    文件格式：
        host=192.168.5.10
        port=22
        device_type=BRV
        username=root
        password=root
        target_path=/mmcblk1p2
        last_file_path=/path/to/file.pt
        timestamp=2026-03-31T17:00:00
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化存储
        
        Args:
            config_file: 配置文件路径，默认为用户目录下的 .ssh_deploy_recent.txt
        """
        if config_file is None:
            home_dir = os.path.expanduser("~")
            config_file = os.path.join(home_dir, ".ssh_deploy_recent.txt")
        
        self.config_file = config_file
    
    def save(self, device: RecentDevice) -> bool:
        """
        保存最近连接的设备
        
        Args:
            device: 最近连接设备信息
            
        Returns:
            bool: 保存成功返回 True
        """
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(f"host={device.host}\n")
                f.write(f"port={device.port}\n")
                f.write(f"device_type={device.device_type}\n")
                f.write(f"username={device.username}\n")
                f.write(f"password={device.password}\n")
                f.write(f"target_path={device.target_path}\n")
                f.write(f"last_file_path={device.last_file_path}\n")
                f.write(f"timestamp={device.timestamp}\n")
            
            return True
            
        except Exception as e:
            print(f"保存最近设备失败: {e}")
            return False
    
    def load(self) -> Optional[RecentDevice]:
        """
        加载最近连接的设备
        
        Returns:
            Optional[RecentDevice]: 最近连接设备信息，不存在返回 None
        """
        if not os.path.exists(self.config_file):
            return None
        
        try:
            data = {}
            with open(self.config_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        data[key.strip()] = value.strip()
            
            if not data or 'host' not in data:
                return None
            
            return RecentDevice(
                host=data.get('host', ''),
                port=int(data.get('port', 22)),
                device_type=data.get('device_type', 'ERV'),
                username=data.get('username', 'root'),
                password=data.get('password', ''),
                target_path=data.get('target_path', '/mmcblk1p2'),
                last_file_path=data.get('last_file_path', ''),
                timestamp=data.get('timestamp', ''),
            )
            
        except Exception as e:
            print(f"加载最近设备失败: {e}")
            return None
    
    def clear(self) -> bool:
        """
        清除最近连接设备记录
        
        Returns:
            bool: 清除成功返回 True
        """
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
            return True
        except Exception as e:
            print(f"清除最近设备失败: {e}")
            return False