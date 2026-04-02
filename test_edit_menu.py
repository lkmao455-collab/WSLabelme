#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试编辑菜单问题"""

import sys
import os
from PyQt5 import QtWidgets, QtCore

# 添加当前目录到路径以便导入labelme模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from labelme.app import MainWindow
from labelme.config import get_config

class DebugMainWindow(MainWindow):
    """添加调试功能的MainWindow"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 添加编辑菜单的调试信号
        if hasattr(self, 'menus') and hasattr(self.menus, 'edit'):
            self.menus.edit.aboutToShow.connect(self.on_edit_menu_about_to_show)
            self.menus.edit.aboutToHide.connect(self.on_edit_menu_about_to_hide)
            
            # 检查编辑菜单的enabled状态
            print(f"编辑菜单是否可用: {self.menus.edit.isEnabled()}")
            print(f"编辑菜单是否可见: {self.menus.edit.isVisible()}")
            
            # 检查编辑菜单下的动作数量
            actions = self.menus.edit.actions()
            print(f"编辑菜单中的动作数量: {len(actions)}")
            
            enabled_count = sum(1 for action in actions if action.isEnabled())
            print(f"编辑菜单中启用的动作数量: {enabled_count}")
            
            # 打印每个动作的状态
            for i, action in enumerate(actions):
                if action is None or action.isSeparator():
                    print(f"  动作[{i}]: 分隔符")
                else:
                    print(f"  动作[{i}]: '{action.text()}' - 启用: {action.isEnabled()}, 可见: {action.isVisible()}")
    
    def on_edit_menu_about_to_show(self):
        print("=== 编辑菜单即将显示 ===")
        print(f"当前是否有图像加载: {self.image.isNull()}")
        print(f"是否有形状: {not self.noShapes()}")
    
    def on_edit_menu_about_to_hide(self):
        print("=== 编辑菜单即将隐藏 ===")

def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # 创建一个简单的窗口来测试菜单点击
    test_window = QtWidgets.QMainWindow()
    test_window.setWindowTitle("测试菜单点击")
    
    # 创建一个按钮来模拟点击编辑菜单
    button = QtWidgets.QPushButton("点击这里然后点击编辑菜单")
    test_window.setCentralWidget(button)
    
    # 创建labelme主窗口
    print("创建labelme主窗口...")
    config = get_config()
    window = DebugMainWindow(config=config)
    window.show()
    
    # 显示测试窗口
    test_window.show()
    
    print("=" * 60)
    print("请执行以下操作:")
    print("1. 观察labelme窗口的编辑菜单是否可以点击")
    print("2. 如果菜单可以点击，查看是否展开")
    print("3. 如果菜单项是灰色的，这是正常行为（需要加载图像后启用）")
    print("4. 如果菜单完全不能点击或展开，则是问题所在")
    print("=" * 60)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()