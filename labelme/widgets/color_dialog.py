from PyQt5 import QtWidgets

# 文件头部说明:
# 本模块定义了Labelme中的颜色选择对话框组件。
# 主要功能包括：颜色选择、透明度支持、恢复默认颜色等。
# 这是用户选择和设置颜色的主要界面组件。

class ColorDialog(QtWidgets.QColorDialog):
    """
    自定义颜色对话框类
    
    继承自QColorDialog，增加了透明度通道支持和恢复默认颜色功能。
    提供了更友好的颜色选择界面。
    """
    def __init__(self, parent=None):
        """
        初始化颜色对话框
        
        Args:
            parent: 父窗口对象
        """
        super(ColorDialog, self).__init__(parent)
        
        # 设置对话框选项
        self.setOption(QtWidgets.QColorDialog.ShowAlphaChannel)  # 显示透明度通道
        # Mac原生对话框不支持我们的恢复按钮，所以不使用原生对话框
        self.setOption(QtWidgets.QColorDialog.DontUseNativeDialog)
        
        # 添加恢复默认按钮
        # 默认值在调用时设置，这样可以在不同元素的对话框之间工作
        self.default = None
        self.bb = self.layout().itemAt(1).widget()  # 获取按钮框
        self.bb.addButton(QtWidgets.QDialogButtonBox.RestoreDefaults)  # 添加恢复默认按钮
        self.bb.clicked.connect(self.checkRestore)  # 连接按钮点击事件

    def getColor(self, value=None, title=None, default=None):
        """
        获取颜色值
        
        显示颜色对话框并返回用户选择的颜色。
        
        Args:
            value: 初始颜色值
            title: 对话框标题
            default: 默认颜色值
            
        Returns:
            QColor: 用户选择的颜色，如果取消则返回None
        """
        self.default = default  # 设置默认颜色
        
        if title:
            self.setWindowTitle(title)  # 设置窗口标题
            
        if value:
            self.setCurrentColor(value)  # 设置当前颜色
            
        return self.currentColor() if self.exec_() else None  # 显示对话框并返回结果

    def checkRestore(self, button):
        """
        检查并处理恢复默认按钮点击事件
        
        当用户点击恢复默认按钮时，将颜色恢复为默认值。
        
        Args:
            button: 被点击的按钮
        """
        # 检查是否点击了恢复默认按钮且存在默认颜色
        if (
            self.bb.buttonRole(button) & QtWidgets.QDialogButtonBox.ResetRole
            and self.default
        ):
            self.setCurrentColor(self.default)  # 恢复默认颜色
