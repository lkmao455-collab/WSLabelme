#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试训练曲线 dock 是否能正常显示
"""

import sys
import os

# 确保使用本地源码
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5 import QtCore, QtWidgets
from labelme.widgets import TrainingCurveDock


class TestWindow(QtWidgets.QMainWindow):
    """测试窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("训练曲线 Dock 显示测试")
        self.resize(1200, 800)
        
        print("创建损失曲线 dock...")
        self.loss_dock = TrainingCurveDock("损失曲线", self, curve_type='loss')
        print(f"损失曲线 dock 创建完成，最小尺寸：{self.loss_dock.minimumSize()}")
        
        print("创建准确率曲线 dock...")
        self.acc_dock = TrainingCurveDock("准确率曲线", self, curve_type='accuracy')
        print(f"准确率曲线 dock 创建完成，最小尺寸：{self.acc_dock.minimumSize()}")
        
        # 添加 dock 到底部区域
        print("添加 dock 到底部区域...")
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.loss_dock)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.acc_dock)
        
        # 水平分割
        print("水平分割 dock...")
        self.splitDockWidget(self.loss_dock, self.acc_dock, QtCore.Qt.Horizontal)
        
        # 确保显示
        print("调用 show() 和 raise_()...")
        self.loss_dock.show()
        self.acc_dock.show()
        self.loss_dock.raise_()
        self.acc_dock.raise_()
        
        # 创建中心 widget
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        print("窗口初始化完成")
        
        # 模拟一些数据
        epochs = list(range(0, 100, 5))
        losses = [5.0 * (0.95 ** i) for i in epochs]
        accuracies = [0.2 + 0.75 * (1 - 0.95 ** i) for i in epochs]
        
        print("更新曲线数据...")
        self.loss_dock.update_curve(epochs, losses)
        self.acc_dock.update_curve(epochs, accuracies)
        
        print("测试窗口准备显示")


def main():
    print("启动测试应用...")
    app = QtWidgets.QApplication(sys.argv)
    
    print("创建测试窗口...")
    window = TestWindow()
    
    print("显示窗口...")
    window.show()
    
    print("进入事件循环...")
    return app.exec_()


if __name__ == '__main__':
    print("=" * 60)
    print("训练曲线 Dock 显示测试")
    print("=" * 60)
    
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
