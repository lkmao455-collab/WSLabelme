from PyQt5 import QtCore
from PyQt5 import QtWidgets

# 文件头部说明:
# 本模块定义了Labelme中的工具栏组件。
# 主要功能包括：工具按钮的布局管理、样式设置、居中对齐等。
# 这是用户界面中工具按钮的主要容器组件。

class ToolBar(QtWidgets.QToolBar):
    """
    自定义工具栏类
    
    继承自QToolBar，提供了自定义的工具栏布局和样式。
    主要用于在Labelme界面中显示各种工具按钮。
    """
    def __init__(self, title):
        """
        初始化工具栏
        
        Args:
            title: 工具栏标题
        """
        super(ToolBar, self).__init__(title)
        
        # 获取布局并设置边距和间距
        layout = self.layout()
        m = (0, 0, 0, 0)  # 上、右、下、左边距都设为0
        layout.setSpacing(0)           # 设置控件间距为0
        layout.setContentsMargins(*m)  # 设置内容边距
        self.setContentsMargins(*m)    # 设置工具栏边距
        
        # 不设置 FramelessWindowHint，停靠工具栏使用默认标志即可，避免渲染异常

    def addAction(self, action):
        """
        添加动作到工具栏
        
        重写addAction方法，将普通的QAction转换为QToolButton添加到工具栏中。
        
        Args:
            action: 要添加的动作对象
            
        Returns:
            QToolButton: 创建的工具按钮
        """
        if isinstance(action, QtWidgets.QWidgetAction):
            # 如果是WidgetAction，直接使用父类方法添加
            return super(ToolBar, self).addAction(action)
        
        # 创建工具按钮
        btn = QtWidgets.QToolButton()
        btn.setDefaultAction(action)                    # 设置默认动作
        btn.setToolButtonStyle(self.toolButtonStyle())  # 设置按钮样式
        btn.setVisible(action.isVisible())              # 根据action的可见性设置按钮可见性
        self.addWidget(btn)                             # 添加到工具栏

        # 居中对齐所有工具按钮
        for i in range(self.layout().count()):
            if isinstance(self.layout().itemAt(i).widget(), QtWidgets.QToolButton):
                self.layout().itemAt(i).setAlignment(QtCore.Qt.AlignCenter)
        
        return btn
