#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试编辑菜单问题的脚本"""
import sys
import os
import time
from PyQt5 import QtWidgets, QtCore, QtGui

# 添加当前目录到路径以便导入labelme模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from labelme.app import MainWindow
from labelme.config import get_config

class MenuTestWindow(MainWindow):
    """测试菜单问题的窗口"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 设置定时器来检查菜单状态
        QtCore.QTimer.singleShot(1000, self.test_menu)
    
    def test_menu(self):
        """测试编辑菜单"""
        print("=" * 60)
        print("开始测试编辑菜单...")
        
        # 检查菜单栏
        menu_bar = self.menuBar()
        print(f"菜单栏是否可见: {menu_bar.isVisible()}")
        print(f"菜单栏是否启用: {menu_bar.isEnabled()}")
        
        # 检查编辑菜单
        edit_menu = self.menus.edit
        print(f"编辑菜单是否可见: {edit_menu.isVisible()}")
        print(f"编辑菜单是否启用: {edit_menu.isEnabled()}")
        print(f"编辑菜单标题: '{edit_menu.title()}'")
        
        # 获取编辑菜单在菜单栏中的位置
        edit_menu_action = None
        for action in menu_bar.actions():
            if action.menu() == edit_menu:
                edit_menu_action = action
                break
        
        if edit_menu_action:
            print(f"编辑菜单动作: '{edit_menu_action.text()}'")
            print(f"编辑菜单动作是否启用: {edit_menu_action.isEnabled()}")
            print(f"编辑菜单动作是否可见: {edit_menu_action.isVisible()}")
            
            # 尝试触发编辑菜单
            print("\n尝试触发编辑菜单...")
            menu_bar.setActiveAction(edit_menu_action)
            edit_menu.popup(menu_bar.mapToGlobal(menu_bar.pos()))
            
            # 检查菜单是否弹出
            print(f"编辑菜单是否激活: {edit_menu.isActiveWindow()}")
            print(f"编辑菜单是否显示: {edit_menu.isVisible()}")
            
            # 等待菜单显示
            QtCore.QTimer.singleShot(500, self.check_menu_items)
        else:
            print("错误: 未找到编辑菜单动作!")
            self.close()
    
    def check_menu_items(self):
        """检查菜单项"""
        edit_menu = self.menus.edit
        
        # 获取菜单项
        actions = edit_menu.actions()
        print(f"\n编辑菜单中的动作数量: {len(actions)}")
        
        enabled_count = 0
        for i, action in enumerate(actions):
            if action is None or action.isSeparator():
                print(f"  动作[{i}]: 分隔符")
                continue
            enabled = action.isEnabled()
            visible = action.isVisible()
            if enabled:
                enabled_count += 1
            print(f"  动作[{i}]: '{action.text()}' - 启用: {enabled}, 可见: {visible}")
        
        print(f"启用的动作数量: {enabled_count}")
        print(f"禁用的动作数量: {len(actions) - enabled_count}")
        
        # 检查是否有任何动作是启用的
        if enabled_count == 0:
            print("\n警告: 所有编辑菜单动作都是禁用的!")
            print("这可能是正常的，因为:")
            print("1. 没有加载图像")
            print("2. 没有选中形状")
            print("许多编辑操作需要加载图像或选中形状后才能启用")
        else:
            print("\n至少有一些编辑菜单动作是启用的")
        
        # 关闭菜单
        edit_menu.hide()
        
        # 完成测试，关闭应用
        print("\n测试完成，关闭应用...")
        QtCore.QTimer.singleShot(1000, self.close)

def main():
    app = QtWidgets.QApplication(sys.argv)
    
    print("创建labelme主窗口...")
    config = get_config()
    window = MenuTestWindow(config=config)
    window.show()
    
    print("应用已启动，等待测试...")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()