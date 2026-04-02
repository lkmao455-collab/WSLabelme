# -*- coding: utf-8 -*-
"""
SSH 客户端模块

提供 SSH 连接和 SFTP/SCP 文件传输功能，支持断点续传和 MD5 完整性校验。
自动适配不支持SFTP的设备（如dropbear），使用SCP命令传输。
"""

import hashlib
import logging
import os
import socket
import stat
import time
from dataclasses import dataclass
from typing import Optional, Callable, List, Tuple

import paramiko
from paramiko import SSHClient as ParamikoSSHClient
from paramiko.ssh_exception import (
    AuthenticationException,
    SSHException,
    NoValidConnectionsError,
)


@dataclass
class SSHConfig:
    """SSH 配置数据类"""
    host: str
    port: int = 22
    username: str = "root"
    password: str = ""
    timeout: int = 10
    
    def __post_init__(self):
        """验证配置"""
        if not self.host:
            raise ValueError("主机地址不能为空")
        if self.port < 1 or self.port > 65535:
            raise ValueError("端口号必须在 1-65535 之间")


class SSHClient:
    """
    SSH 客户端类
    
    提供 SSH 连接、SFTP 文件传输、远程命令执行等功能。
    支持断点续传和进度回调。
    """
    
    # 设备类型与凭据的映射
    DEVICE_CREDENTIALS = {
        'ERV': ('root', 'root'),
        'GSV2': ('root', 'root'),
        'GSV': ('root', 'SenvisionTech'),
        'CRV': ('root', 'SenvisionTech'),
        'GHV': ('root', 'SenvisionTech'),
        'AFRV': ('root', '1'),
        'AFSV': ('root', '1'),
        'BRV': ('root', 'root'),  # 默认凭据
    }
    
    def __init__(self, config: SSHConfig):
        """
        初始化 SSH 客户端
        
        Args:
            config: SSH 配置对象
        """
        self.config = config
        self._ssh: Optional[ParamikoSSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None
        self._transport: Optional[paramiko.Transport] = None
        
    @classmethod
    def get_device_credentials(cls, device_type: str) -> Tuple[str, str]:
        """
        获取设备类型的默认凭据
        
        Args:
            device_type: 设备类型
            
        Returns:
            Tuple[str, str]: (用户名, 密码)
        """
        return cls.DEVICE_CREDENTIALS.get(device_type.upper(), ('root', 'root'))
    
    @classmethod
    def get_supported_device_types(cls) -> List[str]:
        """
        获取支持的设备类型列表
        
        Returns:
            List[str]: 设备类型列表
        """
        return list(cls.DEVICE_CREDENTIALS.keys())
    
    def connect(self, require_sftp: bool = True) -> bool:
        """
        建立 SSH 连接
        
        Args:
            require_sftp: 是否需要 SFTP 功能，默认为 True
        
        Returns:
            bool: 连接成功返回 True，否则返回 False
            
        Raises:
            AuthenticationException: 认证失败
            SSHException: SSH 连接错误
            socket.timeout: 连接超时
        """
        logger = logging.getLogger(__name__)
        logger.info(f"[SSH连接] 开始连接到 {self.config.host}:{self.config.port}")
        logger.info(f"[SSH连接] 用户名: {self.config.username}, 超时时间: {self.config.timeout}秒")
        
        try:
            logger.info(f"[SSH连接] 创建SSH客户端实例...")
            self._ssh = ParamikoSSHClient()
            self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            logger.info(f"[SSH连接] 已设置主机密钥策略为AutoAddPolicy")
            
            logger.info(f"[SSH连接] 正在建立TCP连接...")
            self._ssh.connect(
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                timeout=self.config.timeout,
                look_for_keys=False,
                allow_agent=False,
            )
            logger.info(f"[SSH连接] TCP连接建立成功")
            
            # 创建 SFTP 客户端（可选）
            if require_sftp:
                logger.info(f"[SSH连接] 正在打开SFTP通道...")
                try:
                    self._sftp = self._ssh.open_sftp()
                    logger.info(f"[SSH连接] SFTP通道打开成功")
                except SSHException as e:
                    logger.warning(f"[SSH连接] SFTP通道打开失败: {str(e)}，设备可能不支持SFTP")
                    # 某些设备（如dropbear）不支持SFTP，但SSH命令执行仍然可用
                    self._sftp = None
            else:
                logger.info(f"[SSH连接] 跳过SFTP通道打开（仅测试SSH连接）")
            
            logger.info(f"[SSH连接] 连接成功完成")
            return True
            
        except AuthenticationException as e:
            logger.error(f"[SSH连接] 认证失败: {str(e)}")
            raise AuthenticationException(f"认证失败: {str(e)}")
        except socket.timeout as e:
            logger.error(f"[SSH连接] 连接超时: {str(e)}, 超时设置: {self.config.timeout}秒")
            raise TimeoutError(f"连接超时 ({self.config.timeout}秒)")
        except NoValidConnectionsError as e:
            logger.error(f"[SSH连接] 无法连接到 {self.config.host}:{self.config.port}: {str(e)}")
            raise ConnectionError(f"无法连接到 {self.config.host}:{self.config.port}")
        except Exception as e:
            logger.error(f"[SSH连接] SSH连接错误: {type(e).__name__}: {str(e)}")
            raise SSHException(f"SSH 连接错误: {str(e)}")
    
    def disconnect(self):
        """断开 SSH 连接"""
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None
            
        if self._ssh:
            try:
                self._ssh.close()
            except Exception:
                pass
            self._ssh = None
            
        if self._transport:
            try:
                self._transport.close()
            except Exception:
                pass
            self._transport = None
    
    def is_connected(self) -> bool:
        """
        检查连接状态
        
        Returns:
            bool: 已连接返回 True
        """
        # 只检查SSH连接，SFTP可选
        if self._ssh is None:
            return False
        
        try:
            # 发送 keepalive 检查连接
            self._ssh.get_transport().send_ignore()
            return True
        except Exception:
            return False
    
    def has_sftp(self) -> bool:
        """
        检查SFTP是否可用
        
        Returns:
            bool: SFTP可用返回 True
        """
        return self._sftp is not None
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        测试连接
        
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        logger = logging.getLogger(__name__)
        logger.info(f"[连接测试] 开始测试连接到 {self.config.host}:{self.config.port}")
        
        try:
            # 连接测试不需要SFTP，只验证SSH连接
            logger.info(f"[连接测试] 调用connect()方法（不要求SFTP）...")
            self.connect(require_sftp=False)
            logger.info(f"[连接测试] connect()成功，准备执行验证命令...")
            
            # 执行简单命令验证连接
            logger.info(f"[连接测试] 执行远程命令: echo 'connected'")
            stdin, stdout, stderr = self._ssh.exec_command('echo "connected"')
            result = stdout.read().decode().strip()
            error_output = stderr.read().decode().strip()
            
            logger.info(f"[连接测试] 命令输出: {result}")
            if error_output:
                logger.warning(f"[连接测试] 命令错误输出: {error_output}")
            
            if result == "connected":
                logger.info(f"[连接测试] 验证成功")
                return True, "SSH连接成功！设备已响应。"
            logger.warning(f"[连接测试] 验证失败，返回结果: {result}")
            return False, "连接验证失败"
            
        except AuthenticationException as e:
            logger.error(f"[连接测试] 认证失败异常: {str(e)}")
            return False, f"认证失败: {str(e)}"
        except TimeoutError as e:
            logger.error(f"[连接测试] 连接超时异常: {str(e)}")
            return False, f"连接超时: {str(e)}"
        except ConnectionError as e:
            logger.error(f"[连接测试] 连接错误异常: {str(e)}")
            return False, f"连接错误: {str(e)}"
        except Exception as e:
            logger.error(f"[连接测试] 未知异常: {type(e).__name__}: {str(e)}")
            return False, f"连接失败: {str(e)}"
        finally:
            logger.info(f"[连接测试] 断开连接...")
            self.disconnect()
            logger.info(f"[连接测试] 测试结束")
    
    def get_remote_file_size(self, remote_path: str) -> int:
        """
        获取远程文件大小
        
        Args:
            remote_path: 远程文件路径
            
        Returns:
            int: 文件大小（字节），文件不存在返回 -1
        """
        logger = logging.getLogger(__name__)
        
        # 尝试使用SFTP
        if self._sftp:
            try:
                stat_info = self._sftp.stat(remote_path)
                return stat_info.st_size
            except FileNotFoundError:
                return -1
            except Exception as e:
                logger.warning(f"[SFTP] 获取文件大小失败: {str(e)}，尝试使用SSH命令")
        
        # 使用SSH命令获取文件大小
        if self._ssh:
            try:
                success, stdout, stderr = self.execute_command(f'stat -c %s "{remote_path}" 2>/dev/null || echo -1', timeout=10)
                if success and stdout.strip() != '-1':
                    return int(stdout.strip())
                return -1
            except Exception as e:
                logger.warning(f"[SSH] 获取文件大小失败: {str(e)}")
                return -1
        
        raise RuntimeError("SSH 未连接")
    
    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        resume: bool = True,
        enable_md5_verify: bool = True,
    ) -> bool:
        """
        上传文件到远程服务器
        
        自动选择传输方式：优先SFTP，失败则使用SCP（SSH命令传输）。
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            progress_callback: 进度回调函数 (已传输字节, 总字节)
            resume: 是否启用断点续传（SCP模式不支持断点续传）
            enable_md5_verify: 是否启用MD5校验（SCP模式默认启用）
            
        Returns:
            bool: 上传成功返回 True
            
        Raises:
            FileNotFoundError: 本地文件不存在
            RuntimeError: 上传过程中出错
        """
        logger = logging.getLogger(__name__)
        
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"本地文件不存在: {local_path}")
        
        # 尝试使用SFTP上传
        if self._sftp:
            try:
                logger.info(f"[SFTP] 尝试使用SFTP上传文件")
                result = self._upload_via_sftp(local_path, remote_path, progress_callback, resume)
                logger.info(f"[SFTP] 文件上传成功")
                return result
            except Exception as e:
                logger.warning(f"[SFTP] SFTP上传失败: {str(e)}，切换到SCP模式")
        
        # SFTP不可用或失败，使用SCP（SSH命令传输）
        if self._ssh:
            logger.info(f"[SCP] 使用SSH命令传输文件")
            result = self._upload_via_scp(local_path, remote_path, progress_callback, enable_md5_verify)
            logger.info(f"[SCP] 文件上传成功")
            return result
        
        raise RuntimeError("SSH 未连接")
    
    def _upload_via_sftp(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        resume: bool = True,
    ) -> bool:
        """
        通过SFTP上传文件
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            progress_callback: 进度回调函数
            resume: 是否启用断点续传
            
        Returns:
            bool: 上传成功返回 True
        """
        if not self._sftp:
            raise RuntimeError("SFTP 未连接")
        
        local_size = os.path.getsize(local_path)
        remote_size = 0
        
        # 检查远程文件是否存在，获取已传输大小
        if resume:
            remote_size = self.get_remote_file_size(remote_path)
            if remote_size == local_size:
                # 文件已完整存在
                if progress_callback:
                    progress_callback(local_size, local_size)
                return True
            elif remote_size > local_size:
                # 远程文件比本地文件大，删除重新上传
                self._sftp.remove(remote_path)
                remote_size = 0
        
        try:
            # 打开本地文件
            with open(local_path, 'rb') as local_file:
                # 如果需要断点续传，seek 到断点位置
                if resume and remote_size > 0:
                    local_file.seek(remote_size)
                
                # 打开远程文件（追加模式用于断点续传）
                mode = 'ab' if resume and remote_size > 0 else 'wb'
                
                with self._sftp.file(remote_path, mode) as remote_file:
                    # 设置远程文件权限
                    if mode == 'wb':
                        try:
                            self._sftp.chmod(remote_path, 0o644)
                        except Exception:
                            pass
                    
                    # 传输数据
                    transferred = remote_size
                    chunk_size = 8192  # 8KB 块大小
                    
                    while True:
                        data = local_file.read(chunk_size)
                        if not data:
                            break
                        
                        remote_file.write(data)
                        transferred += len(data)
                        
                        if progress_callback:
                            progress_callback(transferred, local_size)
            
            return True
            
        except Exception as e:
            raise RuntimeError(f"SFTP上传失败: {str(e)}")
    
    def _upload_via_scp(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        enable_md5_verify: bool = True,
    ) -> bool:
        """
        通过SSH通道上传文件
        
        适用于不支持SFTP的设备（如dropbear）。
        使用SSH通道直接传输数据，支持MD5校验。
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            progress_callback: 进度回调函数
            enable_md5_verify: 是否启用MD5校验
            
        Returns:
            bool: 上传成功返回 True
        """
        if not self._ssh:
            raise RuntimeError("SSH 未连接")
        
        logger = logging.getLogger(__name__)
        local_size = os.path.getsize(local_path)
        filename = os.path.basename(local_path)
        
        logger.info(f"[SCP] 准备上传文件: {filename} ({local_size} bytes)")
        
        # 确保远程目录存在
        remote_dir = os.path.dirname(remote_path)
        if remote_dir:
            self._create_remote_directory_via_ssh(remote_dir)
        
        # 检查远程文件是否已存在且大小相同
        remote_size = self.get_remote_file_size(remote_path)
        if remote_size == local_size:
            # 如果启用MD5校验，验证文件完整性
            if enable_md5_verify:
                logger.info(f"[SCP] 文件已存在，验证MD5...")
                verify_success, local_md5, remote_md5, verify_msg = self.verify_file_integrity(local_path, remote_path)
                if verify_success:
                    logger.info(f"[SCP] MD5校验通过，跳过上传")
                    if progress_callback:
                        progress_callback(local_size, local_size)
                    return True
                else:
                    logger.warning(f"[SCP] MD5不匹配，重新上传: {verify_msg}")
            else:
                logger.info(f"[SCP] 文件已存在且大小相同，跳过上传")
                if progress_callback:
                    progress_callback(local_size, local_size)
                return True
        
        # 删除已存在的不完整文件
        if remote_size > 0:
            logger.info(f"[SCP] 删除已存在的不完整文件")
            self.execute_command(f'rm -f "{remote_path}"', timeout=10)
        
        # 计算本地MD5（用于传输后校验）
        local_md5 = None
        if enable_md5_verify:
            try:
                local_md5 = self.calculate_local_md5(local_path)
                logger.info(f"[SCP] 本地MD5: {local_md5}")
            except Exception as e:
                logger.warning(f"[SCP] 计算本地MD5失败: {str(e)}")
        
        try:
            # 方式1：使用SSH通道直接传输（高效）
            logger.info(f"[SCP] 使用SSH通道直接传输...")
            
            # 打开SSH会话通道
            transport = self._ssh.get_transport()
            if not transport or not transport.is_active():
                raise RuntimeError("SSH传输通道不可用")
            
            channel = transport.open_session()
            # 使用cat命令接收数据
            channel.exec_command(f'cat > "{remote_path}"')
            
            # 分块传输数据并支持进度回调
            chunk_size = 65536  # 64KB 块大小
            transferred = 0
            
            with open(local_path, 'rb') as local_file:
                while True:
                    # 检查通道是否仍然活跃
                    if channel.closed:
                        raise RuntimeError("SSH通道已关闭")
                    
                    data = local_file.read(chunk_size)
                    if not data:
                        break
                    
                    # 发送数据
                    channel.sendall(data)
                    transferred += len(data)
                    
                    if progress_callback:
                        progress_callback(transferred, local_size)
            
            # 关闭写入端，等待命令完成
            channel.shutdown_write()
            
            # 等待命令执行完成
            exit_status = channel.recv_exit_status()
            if exit_status != 0:
                # 读取错误输出
                stderr = channel.recv_stderr(4096).decode('utf-8', errors='ignore')
                raise RuntimeError(f"远程命令执行失败: {stderr}")
            
            # 关闭通道
            channel.close()
            
            logger.info(f"[SCP] 文件传输完成: {filename} ({local_size} bytes)")
            
            # 设置文件权限
            self.execute_command(f'chmod 644 "{remote_path}"', timeout=10)
            
            # MD5校验
            if enable_md5_verify and local_md5:
                logger.info(f"[SCP] 正在进行MD5校验...")
                try:
                    success, remote_md5 = self.calculate_remote_md5(remote_path, timeout=60)
                    if success:
                        logger.info(f"[SCP] 远程MD5: {remote_md5}")
                        if local_md5 == remote_md5:
                            logger.info(f"[SCP] MD5校验通过")
                        else:
                            logger.error(f"[SCP] MD5校验失败: 本地={local_md5}, 远程={remote_md5}")
                            # 删除不完整的文件
                            self.execute_command(f'rm -f "{remote_path}"', timeout=10)
                            raise RuntimeError(f"MD5校验失败: 文件传输不完整")
                    else:
                        logger.warning(f"[SCP] 无法获取远程MD5: {remote_md5}")
                except Exception as e:
                    logger.warning(f"[SCP] MD5校验异常: {str(e)}")
            
            return True
            
        except Exception as e:
            logger.error(f"[SCP] 传输异常: {str(e)}")
            # 清理不完整的文件
            try:
                self.execute_command(f'rm -f "{remote_path}"', timeout=10)
            except Exception:
                pass
            raise RuntimeError(f"SCP上传失败: {str(e)}")
    
    def _create_remote_directory_via_ssh(self, remote_path: str) -> bool:
        """
        通过SSH命令创建远程目录
        
        Args:
            remote_path: 远程目录路径
            
        Returns:
            bool: 创建成功返回 True
        """
        if not self._ssh:
            raise RuntimeError("SSH 未连接")
        
        try:
            # 使用mkdir -p创建目录（包括父目录）
            success, stdout, stderr = self.execute_command(f'mkdir -p "{remote_path}"', timeout=10)
            return success
        except Exception as e:
            raise RuntimeError(f"创建目录失败: {str(e)}")
    
    def execute_command(
        self,
        command: str,
        timeout: int = 30,
        get_output: bool = True,
    ) -> Tuple[bool, str, str]:
        """
        在远程服务器执行命令
        
        Args:
            command: 要执行的命令
            timeout: 命令执行超时时间（秒）
            get_output: 是否获取输出
            
        Returns:
            Tuple[bool, str, str]: (是否成功, stdout, stderr)
        """
        if not self._ssh:
            raise RuntimeError("SSH 未连接")
        
        try:
            stdin, stdout, stderr = self._ssh.exec_command(command, timeout=timeout)
            
            if get_output:
                stdout_data = stdout.read().decode('utf-8', errors='ignore')
                stderr_data = stderr.read().decode('utf-8', errors='ignore')
                exit_code = stdout.channel.recv_exit_status()
                return exit_code == 0, stdout_data, stderr_data
            else:
                exit_code = stdout.channel.recv_exit_status()
                return exit_code == 0, "", ""
                
        except Exception as e:
            raise RuntimeError(f"命令执行失败: {str(e)}")
    
    def create_remote_directory(self, remote_path: str, mode: int = 0o755) -> bool:
        """
        创建远程目录
        
        Args:
            remote_path: 远程目录路径
            mode: 目录权限
            
        Returns:
            bool: 创建成功返回 True
        """
        logger = logging.getLogger(__name__)
        
        # 尝试使用SFTP
        if self._sftp:
            try:
                self._sftp.mkdir(remote_path)
                self._sftp.chmod(remote_path, mode)
                return True
            except IOError as e:
                if 'File exists' in str(e):
                    return True
                logger.warning(f"[SFTP] 创建目录失败: {str(e)}，尝试使用SSH命令")
        
        # 使用SSH命令创建目录
        if self._ssh:
            return self._create_remote_directory_via_ssh(remote_path)
        
        raise RuntimeError("SSH 未连接")
    
    def remote_path_exists(self, remote_path: str) -> bool:
        """
        检查远程路径是否存在
        
        Args:
            remote_path: 远程路径
            
        Returns:
            bool: 存在返回 True
        """
        logger = logging.getLogger(__name__)
        
        # 尝试使用SFTP
        if self._sftp:
            try:
                self._sftp.stat(remote_path)
                return True
            except FileNotFoundError:
                return False
            except Exception as e:
                logger.warning(f"[SFTP] 检查路径失败: {str(e)}，尝试使用SSH命令")
        
        # 使用SSH命令检查路径
        if self._ssh:
            try:
                success, stdout, stderr = self.execute_command(f'test -e "{remote_path}"', timeout=10)
                return success
            except Exception:
                return False
        
        raise RuntimeError("SSH 未连接")
    
    def calculate_local_md5(self, local_path: str) -> str:
        """
        计算本地文件的 MD5 值
        
        Args:
            local_path: 本地文件路径
            
        Returns:
            str: MD5 值（32位小写十六进制字符串）
            
        Raises:
            FileNotFoundError: 本地文件不存在
            RuntimeError: 计算失败
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"本地文件不存在: {local_path}")
        
        try:
            md5_hash = hashlib.md5()
            with open(local_path, 'rb') as f:
                # 分块读取，避免大文件占用过多内存
                for chunk in iter(lambda: f.read(8192), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest().lower()
        except Exception as e:
            raise RuntimeError(f"计算本地 MD5 失败: {str(e)}")
    
    def calculate_remote_md5(self, remote_path: str, timeout: int = 30) -> Tuple[bool, str]:
        """
        计算远程文件的 MD5 值
        
        通过 SSH 执行 md5sum 命令获取远端文件的 MD5 值。
        兼容输出格式：md5 + 文件名
        
        Args:
            remote_path: 远程文件路径
            timeout: 命令执行超时时间（秒）
            
        Returns:
            Tuple[bool, str]: (是否成功, MD5值或错误信息)
            
        Raises:
            RuntimeError: SSH 未连接
        """
        logger = logging.getLogger(__name__)
        
        if not self._ssh:
            logger.error("[远程MD5] SSH 未连接")
            raise RuntimeError("SSH 未连接")
        
        try:
            # 检查SSH连接状态
            if not self.is_connected():
                logger.error("[远程MD5] SSH会话已断开")
                return False, "SSH会话已断开"
            
            # 执行 md5sum 命令
            command = f'md5sum "{remote_path}"'
            logger.info(f"[远程MD5] 执行命令: {command}")
            success, stdout, stderr = self.execute_command(command, timeout=timeout)
            
            logger.info(f"[远程MD5] 命令执行结果: success={success}, stdout='{stdout[:100] if stdout else ''}', stderr='{stderr[:100] if stderr else ''}'")
            
            if not success:
                # 命令执行失败
                error_msg = stderr.strip() if stderr else "命令执行失败"
                logger.error(f"[远程MD5] 命令失败: {error_msg}")
                return False, f"md5sum 命令执行失败: {error_msg}"
            
            if not stdout:
                logger.error("[远程MD5] 输出为空")
                return False, "md5sum 返回为空"
            
            # 解析输出格式："md5_value  filename"
            # 只取第一个字段（MD5值）
            parts = stdout.strip().split()
            if len(parts) < 1:
                logger.error(f"[远程MD5] 无法解析输出: '{stdout}'")
                return False, "无法解析 md5sum 输出"
            
            remote_md5 = parts[0].lower()
            
            # 验证 MD5 格式（32位十六进制）
            if len(remote_md5) != 32 or not all(c in '0123456789abcdef' for c in remote_md5):
                logger.error(f"[远程MD5] 无效格式: {remote_md5}")
                return False, f"无效的 MD5 值格式: {remote_md5}"
            
            logger.info(f"[远程MD5] 计算结果: {remote_md5}")
            return True, remote_md5
            
        except Exception as e:
            logger.error(f"[远程MD5] 异常: {type(e).__name__}: {str(e)}")
            return False, f"计算远程 MD5 失败: {str(e)}"
    
    def verify_file_integrity(
        self,
        local_path: str,
        remote_path: str,
        timeout: int = 30,
    ) -> Tuple[bool, str, str, str]:
        """
        验证文件完整性（MD5 校验）
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            timeout: 命令执行超时时间（秒）
            
        Returns:
            Tuple[bool, str, str, str]: (是否一致, 本地MD5, 远程MD5, 消息)
            
        Raises:
            FileNotFoundError: 本地文件不存在
            RuntimeError: 校验过程出错
        """
        logger = logging.getLogger(__name__)
        
        # 计算本地 MD5
        local_md5 = self.calculate_local_md5(local_path)
        logger.info(f"[MD5校验] 本地MD5: {local_md5}")
        
        # 获取远程 MD5
        try:
            success, remote_md5_or_error = self.calculate_remote_md5(remote_path, timeout)
            
            if not success:
                # 无法获取远程 MD5
                error_msg = remote_md5_or_error
                logger.error(f"[MD5校验] 获取远程MD5失败: {error_msg}")
                return False, local_md5, "", f"获取远程 MD5 失败: {error_msg}"
            
            remote_md5 = remote_md5_or_error
            logger.info(f"[MD5校验] 远程MD5: {remote_md5}")
            
            # 对比 MD5
            if local_md5 == remote_md5:
                logger.info(f"[MD5校验] 校验通过")
                return True, local_md5, remote_md5, "MD5 校验通过"
            else:
                logger.error(f"[MD5校验] MD5不匹配: 本地={local_md5}, 远程={remote_md5}")
                return False, local_md5, remote_md5, f"MD5 不匹配: 本地={local_md5}, 远程={remote_md5}"
                
        except Exception as e:
            error_msg = f"校验异常: {str(e)}"
            logger.error(f"[MD5校验] {error_msg}")
            return False, local_md5, "", error_msg
    
    def remove_remote_file(self, remote_path: str) -> bool:
        """
        删除远程文件
        
        Args:
            remote_path: 远程文件路径
            
        Returns:
            bool: 删除成功返回 True，文件不存在也返回 True
        """
        logger = logging.getLogger(__name__)
        
        # 尝试使用SFTP
        if self._sftp:
            try:
                self._sftp.remove(remote_path)
                return True
            except FileNotFoundError:
                # 文件不存在，视为删除成功
                return True
            except Exception as e:
                logger.warning(f"[SFTP] 删除文件失败: {str(e)}，尝试使用SSH命令")
        
        # 使用SSH命令删除文件
        if self._ssh:
            try:
                self.execute_command(f'rm -f "{remote_path}"', timeout=10)
                return True
            except Exception as e:
                logger.warning(f"[SSH] 删除文件失败: {str(e)}")
                return False
        
        raise RuntimeError("SSH 未连接")
    
    def upload_file_with_verification(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None,
        max_retries: int = 3,
        resume: bool = True,
    ) -> Tuple[bool, str]:
        """
        上传文件并验证完整性（带自动重传）
        
        功能流程：
        1. 计算本地文件 MD5
        2. 上传文件（支持断点续传）
        3. 计算远程文件 MD5
        4. 对比 MD5，不一致则自动重传
        5. 最多重试 max_retries 次
        
        Args:
            local_path: 本地文件路径
            remote_path: 远程文件路径
            progress_callback: 进度回调函数 (已传输字节, 总字节)
            status_callback: 状态回调函数 (状态消息)
            log_callback: 日志回调函数 (级别, 消息)
            max_retries: 最大重试次数（默认3次）
            resume: 是否启用断点续传
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        if not os.path.exists(local_path):
            return False, f"本地文件不存在: {local_path}"
        
        # 检查SSH连接（不再强制要求SFTP）
        if not self._ssh:
            return False, "SSH 未连接"
        
        # 检测传输模式
        transport_mode = "SFTP" if self._sftp else "SCP"
        
        local_size = os.path.getsize(local_path)
        filename = os.path.basename(local_path)
        
        def log(level: str, message: str):
            if log_callback:
                log_callback(level, message)
        
        def status(message: str):
            if status_callback:
                status_callback(message)
        
        log("INFO", f"传输模式: {transport_mode}")
        
        # 计算本地 MD5
        try:
            status("正在计算本地 MD5...")
            local_md5 = self.calculate_local_md5(local_path)
            log("INFO", f"本地文件 MD5: {local_md5} ({filename})")
        except Exception as e:
            return False, f"计算本地 MD5 失败: {str(e)}"
        
        # 重传循环
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    status(f"校验失败，正在重试（{attempt}/{max_retries}）...")
                    log("WARNING", f"第 {attempt} 次尝试上传: {filename}")
                    
                    # 检查SSH连接状态，如果断开则重新连接
                    if not self.is_connected():
                        log("INFO", "SSH连接已断开，正在重新连接...")
                        try:
                            self.connect(require_sftp=self._sftp is not None)
                            log("INFO", "SSH重新连接成功")
                        except Exception as conn_e:
                            log("ERROR", f"SSH重新连接失败: {str(conn_e)}")
                            return False, f"SSH重新连接失败: {str(conn_e)}"
                    
                    # 删除远端不完整文件
                    try:
                        self.remove_remote_file(remote_path)
                        log("INFO", f"已删除远端不完整文件: {remote_path}")
                    except Exception as e:
                        log("WARNING", f"删除远端文件失败: {str(e)}")
                    # 短暂延迟，避免立即重传
                    time.sleep(0.5)
                else:
                    status(f"开始上传文件 ({filename})...")
                
                # 上传文件
                upload_success = self.upload_file(
                    local_path,
                    remote_path,
                    progress_callback=progress_callback,
                    resume=resume if attempt == 1 else False,  # 重传时不使用断点续传
                )
                
                if not upload_success:
                    log("ERROR", f"上传失败: {filename}")
                    if attempt < max_retries:
                        continue
                    else:
                        return False, f"上传失败（已重试{max_retries}次）"
                
                # 上传完成，进行 MD5 校验
                status("正在校验 MD5...")
                log("INFO", f"正在校验文件完整性: {filename}")
                
                verify_success, calc_local_md5, remote_md5, verify_msg = self.verify_file_integrity(
                    local_path,
                    remote_path,
                    timeout=30,
                )
                
                log("INFO", f"本地 MD5: {local_md5}")
                log("INFO", f"远程 MD5: {remote_md5 if remote_md5 else '获取失败'}")
                
                if verify_success:
                    status("校验成功")
                    log("SUCCESS", f"文件传输成功并通过 MD5 校验: {filename}")
                    return True, "传输成功并通过 MD5 校验"
                else:
                    log("ERROR", f"MD5 校验失败: {verify_msg}")
                    log("ERROR", f"本地MD5={local_md5}, 远程MD5={remote_md5 if remote_md5 else 'None'}")
                    if attempt < max_retries:
                        continue
                    else:
                        status(f"传输失败（已重试{max_retries}次）")
                        return False, f"MD5 校验失败（已重试{max_retries}次）: {verify_msg}"
                        
            except Exception as e:
                error_msg = f"传输异常: {str(e)}"
                log("ERROR", error_msg)
                if attempt < max_retries:
                    continue
                else:
                    status(f"传输失败（已重试{max_retries}次）")
                    return False, f"{error_msg}（已重试{max_retries}次）"
        
        return False, "传输失败（未知错误）"
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()
        return False
