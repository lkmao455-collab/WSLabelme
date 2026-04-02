import json

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

# 文件头部说明:
# 本模块定义了Labelme中的文件对话框预览组件。
# 主要功能包括：JSON文件内容预览、图像文件缩略图预览等。
# 这是用户在选择文件时能够预览文件内容的重要功能组件。

class ScrollAreaPreview(QtWidgets.QScrollArea):
    """
    滚动区域预览类
    
    继承自QScrollArea，提供了一个可滚动的预览区域，
    用于显示文件内容的预览信息。
    """
    def __init__(self, *args, **kwargs):
        """
        初始化滚动预览区域
        
        Args:
            *args: 传递给父类的参数
            **kwargs: 传递给父类的关键字参数
        """
        super(ScrollAreaPreview, self).__init__(*args, **kwargs)

        self.setWidgetResizable(True)  # 设置内容可调整大小

        # 创建内容widget和布局
        content = QtWidgets.QWidget(self)
        self.setWidget(content)

        lay = QtWidgets.QVBoxLayout(content)

        # 创建标签用于显示预览内容
        self.label = QtWidgets.QLabel(content)
        self.label.setWordWrap(True)  # 设置文字自动换行

        lay.addWidget(self.label)

    def setText(self, text):
        """
        设置文本预览内容
        
        Args:
            text: 要显示的文本内容
        """
        self.label.setText(text)

    def setPixmap(self, pixmap):
        """
        设置图像预览内容
        
        Args:
            pixmap: QPixmap对象
        """
        self.label.setPixmap(pixmap)

    def clear(self):
        """
        清空预览内容
        """
        self.label.clear()


class FileDialogPreview(QtWidgets.QFileDialog):
    """
    文件对话框预览类
    
    继承自QFileDialog，增加了文件预览功能。
    支持JSON文件内容预览和图像文件缩略图预览。
    """
    def __init__(self, *args, **kwargs):
        """
        初始化文件对话框预览
        
        Args:
            *args: 传递给父类的参数
            **kwargs: 传递给父类的关键字参数
        """
        super(FileDialogPreview, self).__init__(*args, **kwargs)
        self.setOption(self.DontUseNativeDialog, True)  # 不使用原生对话框

        # 创建预览区域
        self.labelPreview = ScrollAreaPreview(self)
        self.labelPreview.setFixedSize(300, 300)  # 设置固定大小
        self.labelPreview.setHidden(True)  # 初始隐藏

        # 创建布局
        box = QtWidgets.QVBoxLayout()
        box.addWidget(self.labelPreview)
        box.addStretch()  # 添加弹性空间

        # 调整对话框大小，为预览区域预留空间
        self.setFixedSize(self.width() + 300, self.height())
        self.layout().addLayout(box, 1, 3, 1, 1)  # 添加到布局的指定位置
        
        # 连接当前文件变化信号
        self.currentChanged.connect(self.onChange)

    def onChange(self, path):
        """
        文件变化事件处理
        
        当用户选择不同文件时，根据文件类型显示相应的预览内容。
        
        Args:
            path: 选中的文件路径
        """
        if path.lower().endswith(".json"):
            # JSON文件预览
            with open(path, "r") as f:
                data = json.load(f)
                self.labelPreview.setText(json.dumps(data, indent=4, sort_keys=False))
            self.labelPreview.label.setAlignment(
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop
            )
            self.labelPreview.setHidden(False)
        else:
            # 图像文件预览
            pixmap = QtGui.QPixmap(path)
            if pixmap.isNull():
                # 如果图像加载失败，清空预览
                self.labelPreview.clear()
                self.labelPreview.setHidden(True)
            else:
                # 缩放图像以适应预览区域
                self.labelPreview.setPixmap(
                    pixmap.scaled(
                        self.labelPreview.width() - 30,  # 预留边距
                        self.labelPreview.height() - 30,
                        QtCore.Qt.KeepAspectRatio,        # 保持宽高比
                        QtCore.Qt.SmoothTransformation,   # 平滑变换
                    )
                )
                self.labelPreview.label.setAlignment(QtCore.Qt.AlignCenter)
                self.labelPreview.setHidden(False)
