# -*- encoding: utf-8 -*-

import html

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from .escapable_qlist_widget import EscapableQListWidget

# 文件头部说明:
# 本模块定义了Labelme中的唯一标签列表组件。
# 主要功能包括：标签项的唯一性管理、标签显示、颜色标识等。
# 这是用户管理唯一标签列表的重要界面组件。

class UniqueLabelQListWidget(EscapableQListWidget):
    """
    唯一标签列表组件类
    
    继承自EscapableQListWidget，提供了标签项的唯一性管理功能。
    确保每个标签只出现一次，并支持带颜色的标签显示。
    """
    def mousePressEvent(self, event):
        """
        鼠标按下事件处理
        
        重写鼠标按下事件，当点击空白区域时清除选择。
        
        Args:
            event: 鼠标事件对象
        """
        super(UniqueLabelQListWidget, self).mousePressEvent(event)
        if not self.indexAt(event.pos()).isValid():
            self.clearSelection()

    def findItemByLabel(self, label):
        """
        根据标签文本查找项
        
        Args:
            label: 要查找的标签文本
            
        Returns:
            QListWidgetItem: 找到的项，如果不存在则返回None
        """
        for row in range(self.count()):
            item = self.item(row)
            if item.data(Qt.UserRole) == label:
                return item

    def createItemFromLabel(self, label):
        """
        根据标签创建新项
        
        Args:
            label: 标签文本
            
        Returns:
            QListWidgetItem: 创建的新项
            
        Raises:
            ValueError: 当标签已存在时抛出异常
        """
        if self.findItemByLabel(label):
            raise ValueError("Item for label '{}' already exists".format(label))

        item = QtWidgets.QListWidgetItem()
        item.setData(Qt.UserRole, label)
        return item

    def setItemLabel(self, item, label, color=None):
        """
        设置项的标签显示
        
        Args:
            item: 要设置的列表项
            label: 标签文本
            color: 颜色元组 (R, G, B)，如果为None则不显示颜色标识
        """
        qlabel = QtWidgets.QLabel(self)
        if color is None:
            qlabel.setText("{}".format(label))
        else:
            # 使用HTML格式显示带颜色的标签
            qlabel.setText(
                '{} <font color="#{:02x}{:02x}{:02x}">●</font>'.format(
                    html.escape(label), *color  # 转义HTML特殊字符并展开颜色元组
                )
            )
        qlabel.setAlignment(Qt.AlignBottom)  # 标签底部对齐

        item.setSizeHint(qlabel.sizeHint())  # 设置项的大小提示

        self.setItemWidget(item, qlabel)  # 将标签设置为项的widget
