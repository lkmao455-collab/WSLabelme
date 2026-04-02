import PIL.Image
import PIL.ImageEnhance
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage

# 文件头部说明:
# 本模块定义了Labelme中的亮度对比度调整对话框组件。
# 主要功能包括：图像亮度和对比度的实时调整，支持滑块控制和预览。
# 这是用户调整图像显示效果的重要工具组件。

class BrightnessContrastDialog(QtWidgets.QDialog):
    """
    亮度对比度调整对话框类
    
    继承自QDialog，提供了一个用于调整图像亮度和对比度的对话框界面。
    支持实时预览调整效果。
    """
    _base_value = 50  # 基准值，用于计算调整比例

    def __init__(self, img, callback, parent=None):
        """
        初始化亮度对比度对话框
        
        Args:
            img: PIL图像对象，要调整的原始图像
            callback: 回调函数，用于更新调整后的图像
            parent: 父窗口对象
        """
        super(BrightnessContrastDialog, self).__init__(parent)
        self.setModal(True)  # 设置为模态对话框
        self.setWindowTitle("Brightness/Contrast")  # 设置窗口标题

        # 创建滑块和布局字典
        sliders = {}
        layouts = {}
        
        # 为亮度和对比度创建控件
        for title in ["Brightness:", "Contrast:"]:
            layout = QtWidgets.QHBoxLayout()
            
            # 创建标签
            title_label = QtWidgets.QLabel(self.tr(title))
            title_label.setFixedWidth(75)
            layout.addWidget(title_label)
            
            # 创建滑块
            slider = QtWidgets.QSlider(Qt.Horizontal)
            slider.setRange(0, 3 * self._base_value)  # 范围0-150
            slider.setValue(self._base_value)         # 初始值50
            layout.addWidget(slider)
            
            # 创建数值显示标签
            value_label = QtWidgets.QLabel(f"{slider.value() / self._base_value:.2f}")
            value_label.setAlignment(Qt.AlignRight)
            layout.addWidget(value_label)
            
            # 连接信号
            slider.valueChanged.connect(self.onNewValue)  # 连接调整事件
            slider.valueChanged.connect(
                lambda: value_label.setText(f"{slider.value() / self._base_value:.2f}")
            )  # 连接数值显示更新
            
            layouts[title] = layout
            sliders[title] = slider

        # 保存滑块引用
        self.slider_brightness = sliders["Brightness:"]
        self.slider_contrast = sliders["Contrast:"]
        del sliders

        # 设置主布局
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(layouts["Brightness:"])
        layout.addLayout(layouts["Contrast:"])
        del layouts
        self.setLayout(layout)

        # 验证输入参数
        assert isinstance(img, PIL.Image.Image)
        self.img = img
        self.callback = callback

    def onNewValue(self, _):
        """
        滑块值变化事件处理
        
        当用户调整亮度或对比度滑块时，实时计算并应用调整效果。
        
        Args:
            _: 滑块值变化信号（未使用）
        """
        # 计算调整比例
        brightness = self.slider_brightness.value() / self._base_value
        contrast = self.slider_contrast.value() / self._base_value

        img = self.img
        
        # 应用亮度调整
        if brightness != 1:
            img = PIL.ImageEnhance.Brightness(img).enhance(brightness)
        
        # 应用对比度调整
        if contrast != 1:
            img = PIL.ImageEnhance.Contrast(img).enhance(contrast)

        # 转换为QImage格式
        qimage = QImage(
            img.tobytes(), img.width, img.height, img.width * 3, QImage.Format_RGB888
        )
        
        # 调用回调函数更新显示
        self.callback(qimage)
