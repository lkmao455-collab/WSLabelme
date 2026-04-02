# -*- coding: utf-8 -*-
"""
日志处理模块

提供日志记录、显示、导出功能。
支持不同级别的日志和颜色区分。
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Callable
from PyQt5 import QtCore


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


@dataclass
class LogEntry:
    """日志条目数据类"""
    timestamp: datetime
    level: LogLevel
    message: str
    source: str = ""  # 日志来源（如设备IP）
    
    def __str__(self) -> str:
        """转换为字符串格式"""
        time_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        if self.source:
            return f"[{time_str}] [{self.level.value}] [{self.source}] {self.message}"
        return f"[{time_str}] [{self.level.value}] {self.message}"


class LogHandler(QtCore.QObject):
    """
    日志处理器类
    
    管理日志的添加、存储和通知。
    使用 Qt 信号机制通知 UI 更新。
    """
    
    # 日志添加信号
    log_added = QtCore.pyqtSignal(LogEntry)
    # 日志清除信号
    logs_cleared = QtCore.pyqtSignal()
    # 最大日志数量
    MAX_LOGS = 1000
    
    # 日志级别颜色映射（用于 UI 显示）
    LEVEL_COLORS = {
        LogLevel.DEBUG: "#808080",      # 灰色
        LogLevel.INFO: "#000000",       # 黑色
        LogLevel.WARNING: "#FFA500",    # 橙色
        LogLevel.ERROR: "#FF0000",      # 红色
        LogLevel.SUCCESS: "#008000",    # 绿色
    }
    
    def __init__(self, max_logs: int = MAX_LOGS):
        """
        初始化日志处理器
        
        Args:
            max_logs: 最大日志数量，超过时自动清理旧日志
        """
        super().__init__()
        self._logs: List[LogEntry] = []
        self._max_logs = max_logs
        self._callbacks: List[Callable[[LogEntry], None]] = []
    
    def add_log(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        source: str = "",
    ) -> LogEntry:
        """
        添加日志
        
        Args:
            message: 日志消息
            level: 日志级别
            source: 日志来源
            
        Returns:
            LogEntry: 创建的日志条目
        """
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            source=source,
        )
        
        self._logs.append(entry)
        
        # 清理旧日志
        if len(self._logs) > self._max_logs:
            self._logs = self._logs[-self._max_logs:]
        
        # 发送信号
        self.log_added.emit(entry)
        
        # 调用回调
        for callback in self._callbacks:
            try:
                callback(entry)
            except Exception:
                pass
        
        return entry
    
    def debug(self, message: str, source: str = ""):
        """添加 DEBUG 级别日志"""
        return self.add_log(message, LogLevel.DEBUG, source)
    
    def info(self, message: str, source: str = ""):
        """添加 INFO 级别日志"""
        return self.add_log(message, LogLevel.INFO, source)
    
    def warning(self, message: str, source: str = ""):
        """添加 WARNING 级别日志"""
        return self.add_log(message, LogLevel.WARNING, source)
    
    def error(self, message: str, source: str = ""):
        """添加 ERROR 级别日志"""
        return self.add_log(message, LogLevel.ERROR, source)
    
    def success(self, message: str, source: str = ""):
        """添加 SUCCESS 级别日志"""
        return self.add_log(message, LogLevel.SUCCESS, source)
    
    def get_logs(self, level: Optional[LogLevel] = None) -> List[LogEntry]:
        """
        获取日志列表
        
        Args:
            level: 过滤的日志级别，None 表示所有级别
            
        Returns:
            List[LogEntry]: 日志条目列表
        """
        if level is None:
            return self._logs.copy()
        return [log for log in self._logs if log.level == level]
    
    def get_logs_by_source(self, source: str) -> List[LogEntry]:
        """
        根据来源获取日志
        
        Args:
            source: 日志来源
            
        Returns:
            List[LogEntry]: 日志条目列表
        """
        return [log for log in self._logs if log.source == source]
    
    def clear_logs(self):
        """清除所有日志"""
        self._logs.clear()
        self.logs_cleared.emit()
    
    def get_last_n_logs(self, n: int) -> List[LogEntry]:
        """
        获取最后 N 条日志
        
        Args:
            n: 日志数量
            
        Returns:
            List[LogEntry]: 日志条目列表
        """
        return self._logs[-n:] if n < len(self._logs) else self._logs.copy()
    
    def export_logs(self, filepath: str, level: Optional[LogLevel] = None) -> bool:
        """
        导出日志到文件
        
        Args:
            filepath: 导出文件路径
            level: 过滤的日志级别，None 表示所有级别
            
        Returns:
            bool: 导出成功返回 True
        """
        try:
            logs = self.get_logs(level)
            with open(filepath, 'w', encoding='utf-8') as f:
                for log in logs:
                    f.write(str(log) + '\n')
            return True
        except Exception as e:
            self.error(f"导出日志失败: {e}")
            return False
    
    def register_callback(self, callback: Callable[[LogEntry], None]):
        """
        注册日志回调函数
        
        Args:
            callback: 回调函数，接收 LogEntry 参数
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[LogEntry], None]):
        """
        注销日志回调函数
        
        Args:
            callback: 要注销的回调函数
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def get_log_count(self) -> int:
        """
        获取日志数量
        
        Returns:
            int: 日志数量
        """
        return len(self._logs)
    
    def get_level_color(self, level: LogLevel) -> str:
        """
        获取日志级别的颜色
        
        Args:
            level: 日志级别
            
        Returns:
            str: 颜色代码（HTML 格式）
        """
        return self.LEVEL_COLORS.get(level, "#000000")
    
    def get_statistics(self) -> dict:
        """
        获取日志统计信息
        
        Returns:
            dict: 各级别日志数量统计
        """
        stats = {level: 0 for level in LogLevel}
        for log in self._logs:
            stats[log.level] += 1
        return {level.value: count for level, count in stats.items()}