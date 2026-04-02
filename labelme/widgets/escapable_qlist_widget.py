from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

# 文件头部说明:
# 本模块定义了Labelme中的可逃逸列表组件。
# 主要功能包括：支持ESC键清除选择，提供更好的键盘交互体验。
# 这是其他列表组件的基础类，提供了基本的键盘事件处理功能。

class EscapableQListWidget(QtWidgets.QListWidget):
    """
    可逃逸列表组件类
    
    继承自QListWidget，增加了ESC键清除选择的功能。
    提供了更好的键盘交互体验。
    """
    def keyPressEvent(self, event):
        """
        键盘事件处理
        
        重写键盘事件处理，支持ESC键清除当前选择。
        
        Args:
            event: 键盘事件对象
        """
        super(EscapableQListWidget, self).keyPressEvent(event)
        if event.key() == Qt.Key_Escape:  # 如果按下ESC键
            self.clearSelection()          # 清除所有选择
