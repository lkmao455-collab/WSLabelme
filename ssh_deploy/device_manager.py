# -*- coding: utf-8 -*-
"""
设备管理模块

提供设备信息的存储、加载、管理功能。
支持 JSON 格式的设备列表持久化存储。
"""

import json
import os
import uuid
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class DeviceInfo:
    """
    设备信息数据类
    
    Attributes:
        id: 设备唯一标识符
        name: 设备名称
        host: IP 地址
        port: SSH 端口
        device_type: 设备类型
        username: SSH 用户名
        password: SSH 密码（加密存储）
        target_path: 默认目标路径
        description: 设备描述
        created_at: 创建时间
        updated_at: 更新时间
    """
    id: str
    name: str
    host: str
    port: int = 22
    device_type: str = "ERV"
    username: str = "root"
    password: str = ""
    target_path: str = "/mmcblk1p2"
    description: str = ""
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        """初始化时间戳"""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceInfo':
        """从字典创建实例"""
        # 过滤掉不存在的字段
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)
    
    def update_timestamp(self):
        """更新修改时间"""
        self.updated_at = datetime.now().isoformat()


class DeviceManager:
    """
    设备管理器类
    
    管理设备列表的增删改查操作，支持 JSON 文件持久化存储。
    """
    
    # 支持的设备类型
    DEVICE_TYPES = [
        "ERV",
        "GSV",
        "BRV",
        "AFRV",
        "CRV",
        "GSV2",
        "AFSV",
        "GHV",
    ]
    
    # 设备类型与默认凭据的映射
    DEFAULT_CREDENTIALS = {
        "ERV": ("root", "root"),
        "GSV2": ("root", "root"),
        "GSV": ("root", "SenvisionTech"),
        "CRV": ("root", "SenvisionTech"),
        "GHV": ("root", "SenvisionTech"),
        "AFRV": ("root", "1"),
        "AFSV": ("root", "1"),
        "BRV": ("root", "SenvisionTech"),
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化设备管理器
        
        Args:
            config_file: 设备列表配置文件路径，默认为用户目录下的 .ssh_deploy_devices.json
        """
        if config_file is None:
            # 默认存储在用户目录
            home_dir = os.path.expanduser("~")
            config_file = os.path.join(home_dir, ".ssh_deploy_devices.json")
        
        self.config_file = config_file
        self._devices: Dict[str, DeviceInfo] = {}
        self._load_devices()
    
    def _load_devices(self):
        """从文件加载设备列表"""
        if not os.path.exists(self.config_file):
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 支持两种格式：列表或字典
            if isinstance(data, list):
                for item in data:
                    device = DeviceInfo.from_dict(item)
                    self._devices[device.id] = device
            elif isinstance(data, dict):
                for device_id, item in data.items():
                    device = DeviceInfo.from_dict(item)
                    self._devices[device.id] = device
                    
        except json.JSONDecodeError as e:
            print(f"设备配置文件格式错误: {e}")
        except Exception as e:
            print(f"加载设备列表失败: {e}")
    
    def _save_devices(self):
        """保存设备列表到文件"""
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            # 转换为列表格式保存
            data = [device.to_dict() for device in self._devices.values()]
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存设备列表失败: {e}")
            raise
    
    def add_device(self, device: DeviceInfo) -> bool:
        """
        添加设备
        
        Args:
            device: 设备信息对象
            
        Returns:
            bool: 添加成功返回 True
        """
        if not device.id:
            # 生成唯一 ID
            import uuid
            device.id = str(uuid.uuid4())[:8]
        
        # 检查是否已存在
        if device.id in self._devices:
            return False
        
        device.update_timestamp()
        self._devices[device.id] = device
        self._save_devices()
        return True
    
    def update_device(self, device_id: str, **kwargs) -> bool:
        """
        更新设备信息
        
        Args:
            device_id: 设备 ID
            **kwargs: 要更新的字段
            
        Returns:
            bool: 更新成功返回 True
        """
        if device_id not in self._devices:
            return False
        
        device = self._devices[device_id]
        
        # 更新字段
        for key, value in kwargs.items():
            if hasattr(device, key):
                setattr(device, key, value)
        
        device.update_timestamp()
        self._save_devices()
        return True
    
    def delete_device(self, device_id: str) -> bool:
        """
        删除设备
        
        Args:
            device_id: 设备 ID
            
        Returns:
            bool: 删除成功返回 True
        """
        if device_id not in self._devices:
            return False
        
        del self._devices[device_id]
        self._save_devices()
        return True
    
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """
        获取设备信息
        
        Args:
            device_id: 设备 ID
            
        Returns:
            Optional[DeviceInfo]: 设备信息对象，不存在返回 None
        """
        return self._devices.get(device_id)
    
    def get_all_devices(self) -> List[DeviceInfo]:
        """
        获取所有设备列表
        
        Returns:
            List[DeviceInfo]: 设备信息列表
        """
        return list(self._devices.values())
    
    def get_device_by_host(self, host: str) -> Optional[DeviceInfo]:
        """
        根据 IP 地址查找设备
        
        Args:
            host: IP 地址
            
        Returns:
            Optional[DeviceInfo]: 设备信息对象，不存在返回 None
        """
        for device in self._devices.values():
            if device.host == host:
                return device
        return None
    
    def get_device_types(self) -> List[str]:
        """
        获取支持的设备类型列表
        
        Returns:
            List[str]: 设备类型列表
        """
        return self.DEVICE_TYPES.copy()
    
    def get_device_credentials(self, device_type: str) -> tuple:
        """
        获取设备类型的默认凭据
        
        Args:
            device_type: 设备类型
            
        Returns:
            tuple: (用户名, 密码)
        """
        return self.DEFAULT_CREDENTIALS.get(device_type.upper(), ("root", "root"))
    
    def create_device(
        self,
        name: str,
        host: str,
        device_type: str = "ERV",
        port: int = 22,
        description: str = "",
    ) -> DeviceInfo:
        """
        创建设备（自动填充凭据）
        
        Args:
            name: 设备名称
            host: IP 地址
            device_type: 设备类型
            port: SSH 端口
            description: 设备描述
            
        Returns:
            DeviceInfo: 创建设备信息对象
        """
        import uuid
        
        username, password = self.get_device_credentials(device_type)
        
        device = DeviceInfo(
            id=str(uuid.uuid4())[:8],
            name=name,
            host=host,
            port=port,
            device_type=device_type,
            username=username,
            password=password,
            description=description,
        )
        
        self.add_device(device)
        return device
    
    def duplicate_device(self, device_id: str, new_name: str) -> Optional[DeviceInfo]:
        """
        复制设备
        
        Args:
            device_id: 源设备 ID
            new_name: 新设备名称
            
        Returns:
            Optional[DeviceInfo]: 新设备信息对象
        """
        source = self.get_device(device_id)
        if not source:
            return None
        
        import uuid
        new_device = DeviceInfo(
            id=str(uuid.uuid4())[:8],
            name=new_name,
            host=source.host,
            port=source.port,
            device_type=source.device_type,
            username=source.username,
            password=source.password,
            target_path=source.target_path,
            description=f"复制自 {source.name}",
        )
        
        self.add_device(new_device)
        return new_device
    
    def export_devices(self, filepath: str) -> bool:
        """
        导出设备列表到文件
        
        Args:
            filepath: 导出文件路径
            
        Returns:
            bool: 导出成功返回 True
        """
        try:
            data = [device.to_dict() for device in self._devices.values()]
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"导出设备列表失败: {e}")
            return False
    
    def import_devices(self, filepath: str, merge: bool = False) -> bool:
        """
        从文件导入设备列表
        
        Args:
            filepath: 导入文件路径
            merge: 是否合并（True）还是覆盖（False）
            
        Returns:
            bool: 导入成功返回 True
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not merge:
                self._devices.clear()
            
            if isinstance(data, list):
                for item in data:
                    device = DeviceInfo.from_dict(item)
                    # 生成新 ID 避免冲突
                    if device.id in self._devices:
                        import uuid
                        device.id = str(uuid.uuid4())[:8]
                    self._devices[device.id] = device
            
            self._save_devices()
            return True
            
        except Exception as e:
            print(f"导入设备列表失败: {e}")
            return False
    
    def clear_all(self):
        """清空所有设备"""
        self._devices.clear()
        self._save_devices()
    
    def get_device_count(self) -> int:
        """
        获取设备数量
        
        Returns:
            int: 设备数量
        """
        return len(self._devices)
    
    def get_all_device_ips(self) -> List[str]:
        """
        获取所有设备的IP地址列表
        
        Returns:
            List[str]: IP地址列表
        """
        return [device.host for device in self._devices.values()]
    
    def update_or_create_device(
        self,
        host: str,
        device_type: str,
        port: int = 22,
        username: str = "",
        password: str = "",
        target_path: str = "/mmcblk1p2",
    ) -> DeviceInfo:
        """
        更新或创建设备
        
        根据IP地址和设备类型判断：
        - 如果IP和设备类型都相同，不更新
        - 如果IP相同但设备类型不同，更新设备类型
        - 如果IP不存在，创建新设备
        
        Args:
            host: IP 地址
            device_type: 设备类型
            port: SSH 端口
            username: 用户名
            password: 密码
            target_path: 目标路径
            
        Returns:
            DeviceInfo: 设备信息对象
        """
        # 查找是否有相同IP的设备
        existing_device = self.get_device_by_host(host)
        
        if existing_device:
            # IP存在，检查设备类型是否相同
            if existing_device.device_type.upper() == device_type.upper():
                # IP和类型都相同，不更新
                return existing_device
            else:
                # IP相同但类型不同，更新设备类型
                name = f"{device_type}_{host}"
                self.update_device(
                    existing_device.id,
                    name=name,
                    device_type=device_type,
                    username=username,
                    password=password,
                    target_path=target_path,
                )
                return self.get_device(existing_device.id)
        else:
            # IP不存在，创建新设备
            name = f"{device_type}_{host}"
            device = DeviceInfo(
                id=str(uuid.uuid4())[:8],
                name=name,
                host=host,
                port=port,
                device_type=device_type,
                username=username,
                password=password,
                target_path=target_path,
            )
            self.add_device(device)
            return device