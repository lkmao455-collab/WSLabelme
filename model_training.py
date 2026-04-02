#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI模型训练模块

本模块提供模型训练的核心功能，基于 Qt 信号/槽机制实现异步训练流程控制。
训练过程在独立的后台线程中运行，通过信号向 UI 层报告日志、完成状态和错误信息。

主要类：
    ModelTrainer - 模型训练器，管理训练的启动、停止和状态查询

使用示例：
    trainer = ModelTrainer()
    trainer.training_log_updated.connect(on_log)
    trainer.training_finished.connect(on_finish)
    trainer.start_training()
"""

import sys
import time
import threading
from PyQt5 import QtCore, QtWidgets


class ModelTrainer(QtCore.QObject):
    """
    模型训练器类

    继承 QObject 以支持 Qt 信号/槽通信，在后台线程中执行训练任务，
    并通过信号将训练进度、日志和错误信息传递给 UI 层。

    Attributes:
        _is_training (bool): 当前是否正在训练
        _training_thread (threading.Thread): 训练工作线程
        _stop_requested (bool): 是否收到停止训练的请求
    """

    # ==================== 信号定义 ====================
    training_started = QtCore.pyqtSignal()           # 训练开始时发出
    training_stopped = QtCore.pyqtSignal()           # 训练被用户手动停止时发出
    training_log_updated = QtCore.pyqtSignal(str)    # 训练日志更新时发出，携带日志文本
    training_finished = QtCore.pyqtSignal()          # 训练正常完成时发出
    training_error = QtCore.pyqtSignal(str)          # 训练出错时发出，携带错误信息

    def __init__(self):
        super().__init__()
        self._is_training = False        # 训练状态标志
        self._training_thread = None     # 后台训练线程引用
        self._stop_requested = False     # 外部停止请求标志

    def is_training(self):
        """检查当前是否正在执行训练任务

        Returns:
            bool: True 表示正在训练，False 表示空闲
        """
        return self._is_training

    def start_training(self):
        """启动模型训练

        如果已经在训练中，则直接返回不重复启动。
        创建一个守护线程运行 _training_worker，并发出 training_started 信号。
        """
        if self._is_training:
            return

        self._is_training = True
        self._stop_requested = False
        # 使用守护线程，主进程退出时自动终止
        self._training_thread = threading.Thread(target=self._training_worker)
        self._training_thread.daemon = True
        self._training_thread.start()
        self.training_started.emit()

    def stop_training(self):
        """请求停止训练

        设置停止标志，训练循环会在下一轮迭代时检测到该标志并退出。
        立即发出 training_stopped 信号通知 UI。
        """
        if not self._is_training:
            return

        self._stop_requested = True
        self.training_stopped.emit()

    def _training_worker(self):
        """训练工作线程的执行体

        在后台线程中模拟训练过程（100 个 epoch），每个 epoch 产生一条日志。
        支持通过 _stop_requested 标志中途停止。
        训练结束后（无论正常完成还是异常）将 _is_training 重置为 False。
        """
        try:
            # 模拟训练过程：遍历 100 个 epoch
            for epoch in range(1, 101):
                # 检查是否收到停止请求
                if self._stop_requested:
                    self.training_log_updated.emit("训练已停止")
                    break

                # 构造并发送模拟训练日志（loss 递减、accuracy 递增）
                log_message = f"Epoch {epoch}/100 - Loss: {0.5/epoch:.4f} - Accuracy: {95.0 + 0.05*epoch:.2f}%"
                self.training_log_updated.emit(log_message)

                # 模拟每个 epoch 的训练耗时
                time.sleep(0.1)

            # 训练循环结束后，根据是否为主动停止发出不同信号
            if not self._stop_requested:
                self.training_log_updated.emit("训练完成！")
                self.training_finished.emit()
            else:
                self.training_log_updated.emit("训练已手动停止")

        except Exception as e:
            # 捕获训练过程中的异常，通过信号上报
            error_msg = f"训练过程中发生错误: {str(e)}"
            self.training_log_updated.emit(error_msg)
            self.training_error.emit(error_msg)
        finally:
            # 无论成功、停止还是异常，都重置训练状态
            self._is_training = False