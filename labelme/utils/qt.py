import os.path as osp
from math import sqrt

import numpy as np
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

# 文件头部说明:
# 本模块提供了Labelme中Qt界面组件的工具函数。
# 主要功能包括：图标创建、按钮创建、动作创建、菜单管理、验证器、
# 几何计算等。这些函数简化了Qt界面组件的创建和管理，是Labelme
# 用户界面开发的基础工具。

here = osp.dirname(osp.abspath(__file__))


def newIcon(icon):
    """
    创建图标
    
    根据图标名称创建QIcon对象，图标文件位于icons目录中。
    
    Args:
        icon: 图标名称（不包含扩展名）
        
    Returns:
        QtGui.QIcon: 创建的图标对象
    """
    icons_dir = osp.join(here, "../icons")
    return QtGui.QIcon(osp.join(":/", icons_dir, "%s.png" % icon))


def newButton(text, icon=None, slot=None):
    """
    创建按钮
    
    创建一个QPushButton对象，可选择设置图标和点击事件。
    
    Args:
        text: 按钮文本
        icon: 图标名称（可选）
        slot: 点击事件处理函数（可选）
        
    Returns:
        QtWidgets.QPushButton: 创建的按钮对象
    """
    b = QtWidgets.QPushButton(text)
    if icon is not None:
        b.setIcon(newIcon(icon))
    if slot is not None:
        b.clicked.connect(slot)
    return b


def newAction(
    parent,
    text,
    slot=None,
    shortcut=None,
    icon=None,
    tip=None,
    checkable=False,
    enabled=True,
    checked=False,
):
    """
    创建动作
    
    创建一个QAction对象，用于菜单项、工具栏按钮等。
    可以设置快捷键、图标、提示信息、检查状态等。
    
    Args:
        parent: 父对象
        text: 动作文本
        slot: 触发事件处理函数（可选）
        shortcut: 快捷键（可选）
        icon: 图标名称（可选）
        tip: 提示文本（可选）
        checkable: 是否可检查（可选）
        enabled: 是否启用（可选）
        checked: 是否选中（可选）
        
    Returns:
        QtWidgets.QAction: 创建的动作对象
    """
    """Create a new action and assign callbacks, shortcuts, etc."""
    a = QtWidgets.QAction(text, parent)
    if icon is not None:
        a.setIconText(text.replace(" ", "\n"))
        a.setIcon(newIcon(icon))
    if shortcut is not None:
        if isinstance(shortcut, (list, tuple)):
            a.setShortcuts(shortcut)
        else:
            a.setShortcut(shortcut)
    if tip is not None:
        a.setToolTip(tip)
        a.setStatusTip(tip)
    if slot is not None:
        a.triggered.connect(slot)
    if checkable:
        a.setCheckable(True)
    a.setEnabled(enabled)
    a.setChecked(checked)
    return a


def addActions(widget, actions):
    """
    向组件添加动作列表
    
    将动作列表添加到指定的组件中，支持分隔符和子菜单。
    
    Args:
        widget: 目标组件（菜单、工具栏等）
        actions: 动作列表，可以包含None（分隔符）、QMenu（子菜单）、QAction（动作）
    """
    for action in actions:
        if action is None:
            widget.addSeparator()
        elif isinstance(action, QtWidgets.QMenu):
            widget.addMenu(action)
        else:
            widget.addAction(action)


def labelValidator():
    """
    创建标签验证器
    
    创建一个正则表达式验证器，用于验证标签输入。
    验证规则：不能以空格或制表符开头，至少包含一个非空白字符。
    
    Returns:
        QtGui.QRegExpValidator: 标签验证器
    """
    return QtGui.QRegExpValidator(QtCore.QRegExp(r"^[^ \t].+"), None)


class struct(object):
    """
    简单的结构体类
    
    提供一个简单的类，可以动态添加属性，类似于C语言的结构体。
    用于创建包含多个字段的数据结构。
    """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def distance(p):
    """
    计算点到原点的距离
    
    计算给定点到坐标原点(0,0)的欧几里得距离。
    
    Args:
        p: 点对象，需要有x()和y()方法
        
    Returns:
        float: 距离值
    """
    return sqrt(p.x() * p.x() + p.y() * p.y())


def distancetoline(point, line):
    """
    计算点到线段的距离
    
    计算给定点到线段的最短距离。
    
    Args:
        point: 点对象，需要有x()和y()方法
        line: 线段，包含两个点对象的元组
        
    Returns:
        float: 点到线段的最短距离
    """
    p1, p2 = line
    p1 = np.array([p1.x(), p1.y()])
    p2 = np.array([p2.x(), p2.y()])
    p3 = np.array([point.x(), point.y()])
    
    # 检查投影点是否在线段外
    if np.dot((p3 - p1), (p2 - p1)) < 0:
        # 投影点在p1外侧，返回到p1的距离
        return np.linalg.norm(p3 - p1)
    if np.dot((p3 - p2), (p1 - p2)) < 0:
        # 投影点在p2外侧，返回到p2的距离
        return np.linalg.norm(p3 - p2)
    if np.linalg.norm(p2 - p1) == 0:
        # 线段退化为点，返回到该点的距离
        return np.linalg.norm(p3 - p1)
    
    # 计算点到线段的垂直距离
    return np.linalg.norm(np.cross(p2 - p1, p1 - p3)) / np.linalg.norm(p2 - p1)


def fmtShortcut(text):
    """
    格式化快捷键显示文本
    
    将快捷键文本格式化为HTML格式，用于美观显示。
    
    Args:
        text: 快捷键文本，如"Ctrl+S"
        
    Returns:
        str: 格式化后的HTML文本
    """
    mod, key = text.split("+", 1)
    return "<b>%s</b>+<b>%s</b>" % (mod, key)
