from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

# 文件头部说明:
# 本模块定义了Labelme中的缩放控件。
# 主要功能包括：缩放比例的输入和显示，支持1%-1000%的缩放范围。
# 这是用户调整图像显示缩放比例的主要界面组件。

class ZoomWidget(QtWidgets.QSpinBox):
    """
    缩放控件类
    
    继承自QSpinBox，提供了一个专门用于设置缩放比例的数值输入控件。
    支持1%到1000%的缩放范围，带有百分号后缀显示。
    """
    def __init__(self, value=100, parent=None):
        """
        初始化缩放控件
        
        Args:
            value: 初始缩放值，默认为100%
            parent: 父窗口
        """
        super(ZoomWidget, self).__init__(parent)
        
        # 设置控件属性
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)  # 不显示上下按钮
        self.setRange(1, 1000)                                        # 设置数值范围1-1000
        self.setSuffix(" %")                                          # 添加百分号后缀
        self.setValue(value)                                          # 设置初始值
        self.setToolTip("Zoom Level")                                 # 设置工具提示
        self.setStatusTip(self.toolTip())                             # 设置状态栏提示
        self.setAlignment(QtCore.Qt.AlignCenter)                      # 文本居中对齐

    def minimumSizeHint(self):
        """
        获取最小尺寸提示
        
        重写此方法以提供合适的控件尺寸，确保能完整显示最大数值。
        
        Returns:
            QtCore.QSize: 最小尺寸
        """
        # 获取父类的最小高度
        height = super(ZoomWidget, self).minimumSizeHint().height()
        
        # 根据字体度量计算显示最大数值所需的宽度
        fm = QtGui.QFontMetrics(self.font())
        width = fm.width(str(self.maximum()))
        
        return QtCore.QSize(width, height)
