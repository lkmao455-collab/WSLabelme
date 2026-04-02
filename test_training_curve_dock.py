#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练曲线 dock 测试
"""

import sys
from PyQt5 import QtCore, QtWidgets
from labelme.widgets import TrainingCurveDock


class TestWindow(QtWidgets.QMainWindow):
    """测试窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("训练曲线 Dock 测试")
        self.resize(1000, 800)
        
        # 创建训练曲线 dock
        self.loss_dock = TrainingCurveDock("损失曲线", self, curve_type='loss')
        self.acc_dock = TrainingCurveDock("准确率曲线", self, curve_type='accuracy')
        
        # 添加 dock 到窗口
        self.addDockWidget(QtCore.LeftDockWidgetArea, self.loss_dock)
        self.addDockWidget(QtCore.RightDockWidgetArea, self.acc_dock)
        
        # 使用 splitDockWidget 垂直分割
        self.splitDockWidget(self.loss_dock, self.acc_dock, QtCore.Qt.Vertical)
        
        # 创建中心 widget
        central_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        
        # 添加按钮用于测试
        btn_layout = QtWidgets.QHBoxLayout()
        
        self.start_btn = QtWidgets.QPushButton("开始训练")
        self.start_btn.clicked.connect(self.start_training)
        btn_layout.addWidget(self.start_btn)
        
        self.clear_btn = QtWidgets.QPushButton("清除曲线")
        self.clear_btn.clicked.connect(self.clear_curves)
        btn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(btn_layout)
        
        # 添加说明
        label = QtWidgets.QLabel("""
        <h2>训练曲线 Dock 测试</h2>
        <p>1. 点击"开始训练"按钮，模拟训练过程并更新曲线</p>
        <p>2. 点击"清除曲线"按钮，清空曲线数据</p>
        <p>3. 可以拖动 dock 窗口调整位置</p>
        <p>4. dock 窗口没有关闭按钮（符合设计要求）</p>
        """)
        label.setWordWrap(True)
        layout.addWidget(label)
        
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # 定时器用于模拟训练
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_training)
        self.current_epoch = 0
        self.max_epochs = 100
        self.epochs = []
        self.losses = []
        self.accuracies = []
    
    def start_training(self):
        """开始训练"""
        self.current_epoch = 0
        self.epochs = []
        self.losses = []
        self.accuracies = []
        self.timer.start(100)  # 每 100ms 更新一次
        self.start_btn.setEnabled(False)
    
    def update_training(self):
        """更新训练"""
        self.current_epoch += 1
        
        if self.current_epoch > self.max_epochs:
            self.timer.stop()
            self.start_btn.setEnabled(True)
            return
        
        # 模拟数据
        loss = 5.0 * (0.95 ** self.current_epoch)
        accuracy = 0.2 + 0.75 * (1 - 0.95 ** self.current_epoch)
        
        self.epochs.append(self.current_epoch)
        self.losses.append(loss)
        self.accuracies.append(accuracy)
        
        # 更新曲线
        self.loss_dock.update_curve(self.epochs, self.losses)
        self.acc_dock.update_curve(self.epochs, self.accuracies)
    
    def clear_curves(self):
        """清除曲线"""
        self.loss_dock.clear_curve()
        self.acc_dock.clear_curve()
        self.start_btn.setEnabled(True)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())
