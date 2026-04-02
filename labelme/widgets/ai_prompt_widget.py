from PyQt5 import QtWidgets
from loguru import logger

# 文件头部说明:
# 本模块定义了Labelme中的AI提示组件。
# 主要功能包括：AI文本提示输入、NMS参数设置（IoU阈值、分数阈值）等。
# 这是用户与AI模型交互，进行智能标注的重要界面组件。

class AiPromptWidget(QtWidgets.QWidget):
    """
    AI提示主组件类
    
    提供AI标注所需的所有参数输入界面，包括文本提示和NMS参数。
    """
    def __init__(self, on_submit, parent=None):
        """
        初始化AI提示组件
        
        Args:
            on_submit: 提交按钮点击时的回调函数
            parent: 父窗口对象
        """
        super().__init__(parent=parent)

        # 设置垂直布局
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setSpacing(0)

        # 添加文本提示组件
        text_prompt_widget = _TextPromptWidget(on_submit=on_submit, parent=self)
        text_prompt_widget.setMaximumWidth(400)
        text_prompt_widget.setVisible(False)
        self.layout().addWidget(text_prompt_widget)

        # 添加NMS参数组件
        nms_params_widget = _NmsParamsWidget(parent=self)
        nms_params_widget.setMaximumWidth(400)
        nms_params_widget.setVisible(False)
        self.layout().addWidget(nms_params_widget)

    def get_text_prompt(self) -> str:
        """
        获取文本提示内容
        
        Returns:
            str: 用户输入的文本提示
        """
        if (
            (layout := self.layout()) is None
            or (item := layout.itemAt(0)) is None
            or (widget := item.widget()) is None
        ):
            logger.warning("Cannot get text prompt")
            return ""
        return widget.get_text_prompt()

    def get_iou_threshold(self) -> float:
        """
        获取IoU阈值
        
        Returns:
            float: IoU阈值
        """
        if (
            (layout := self.layout()) is None
            or (item := layout.itemAt(1)) is None
            or (widget := item.widget()) is None
        ):
            logger.warning("Cannot get IoU threshold")
            return _IouThresholdWidget.default_iou_threshold
        return widget.get_iou_threshold()

    def get_score_threshold(self) -> float:
        """
        获取分数阈值
        
        Returns:
            float: 分数阈值
        """
        if (
            (layout := self.layout()) is None
            or (item := layout.itemAt(1)) is None
            or (widget := item.widget()) is None
        ):
            logger.warning("Cannot get score threshold")
            return _ScoreThresholdWidget.default_score_threshold
        return widget.get_score_threshold()


class _TextPromptWidget(QtWidgets.QWidget):
    """
    文本提示组件类
    
    提供文本输入界面，用于输入AI模型的提示文本。
    """
    def __init__(self, on_submit, parent=None):
        """
        初始化文本提示组件
        
        Args:
            on_submit: 提交按钮点击时的回调函数
            parent: 父窗口对象
        """
        super().__init__(parent=parent)

        # 设置水平布局
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        # 添加标签
        label = QtWidgets.QLabel(self.tr("AI Prompt"))
        self.layout().addWidget(label)

        # 添加文本输入框
        texts_widget = QtWidgets.QLineEdit(self)
        texts_widget.setPlaceholderText(self.tr("e.g., dog,cat,bird"))
        self.layout().addWidget(texts_widget)

        # 添加提交按钮
        submit_button = QtWidgets.QPushButton(text="Submit", parent=self)
        submit_button.clicked.connect(slot=on_submit)
        self.layout().addWidget(submit_button)

    def get_text_prompt(self) -> str:
        """
        获取文本提示内容
        
        Returns:
            str: 用户输入的文本提示
        """
        if (
            (layout := self.layout()) is None
            or (item := layout.itemAt(1)) is None
            or (widget := item.widget()) is None
        ):
            logger.warning("Cannot get text prompt")
            return ""
        return widget.text()


class _NmsParamsWidget(QtWidgets.QWidget):
    """
    NMS参数组件类
    
    提供非极大值抑制（NMS）相关的参数设置界面。
    """
    def __init__(self, parent=None):
        """
        初始化NMS参数组件
        
        Args:
            parent: 父窗口对象
        """
        super().__init__(parent=parent)

        # 设置水平布局
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        # 添加分数阈值组件
        self.layout().addWidget(_ScoreThresholdWidget(parent=parent))
        # 添加IoU阈值组件
        self.layout().addWidget(_IouThresholdWidget(parent=parent))

    def get_score_threshold(self) -> float:
        """
        获取分数阈值
        
        Returns:
            float: 分数阈值
        """
        if (
            (layout := self.layout()) is None
            or (item := layout.itemAt(0)) is None
            or (widget := item.widget()) is None
        ):
            logger.warning("Cannot get score threshold")
            return _ScoreThresholdWidget.default_score_threshold
        return widget.get_value()

    def get_iou_threshold(self) -> float:
        """
        获取IoU阈值
        
        Returns:
            float: IoU阈值
        """
        if (
            (layout := self.layout()) is None
            or (item := layout.itemAt(1)) is None
            or (widget := item.widget()) is None
        ):
            logger.warning("Cannot get IoU threshold")
            return _IouThresholdWidget.default_iou_threshold
        return widget.get_value()


class _ScoreThresholdWidget(QtWidgets.QWidget):
    """
    分数阈值组件类
    
    提供分数阈值的设置界面，用于过滤低置信度的检测结果。
    """
    default_score_threshold: float = 0.1  # 默认分数阈值

    def __init__(self, parent=None):
        """
        初始化分数阈值组件
        
        Args:
            parent: 父窗口对象
        """
        super().__init__(parent=parent)

        # 设置水平布局
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        # 添加标签
        label = QtWidgets.QLabel(self.tr("Score Threshold"))
        self.layout().addWidget(label)

        # 添加数值输入框
        threshold_widget: QtWidgets.QWidget = QtWidgets.QDoubleSpinBox()
        threshold_widget.setRange(0, 1)      # 范围0-1
        threshold_widget.setSingleStep(0.05) # 步长0.05
        threshold_widget.setValue(self.default_score_threshold)  # 默认值
        self.layout().addWidget(threshold_widget)

    def get_value(self) -> float:
        """
        获取分数阈值
        
        Returns:
            float: 分数阈值
        """
        if (
            (layout := self.layout()) is None
            or (item := layout.itemAt(1)) is None
            or (widget := item.widget()) is None
        ):
            logger.warning("Cannot get score threshold")
            return self.default_score_threshold
        return widget.value()


class _IouThresholdWidget(QtWidgets.QWidget):
    """
    IoU阈值组件类
    
    提供IoU（交并比）阈值的设置界面，用于NMS算法中的重叠检测。
    """
    default_iou_threshold: float = 0.5  # 默认IoU阈值

    def __init__(self, parent=None):
        """
        初始化IoU阈值组件
        
        Args:
            parent: 父窗口对象
        """
        super().__init__(parent=parent)

        # 设置水平布局
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        # 添加标签
        label = QtWidgets.QLabel(self.tr("IoU Threshold"))
        self.layout().addWidget(label)

        # 添加数值输入框
        threshold_widget: QtWidgets.QWidget = QtWidgets.QDoubleSpinBox()
        threshold_widget.setRange(0, 1)      # 范围0-1
        threshold_widget.setSingleStep(0.05) # 步长0.05
        threshold_widget.setValue(self.default_iou_threshold)  # 默认值
        self.layout().addWidget(threshold_widget)

    def get_value(self) -> float:
        """
        获取IoU阈值
        
        Returns:
            float: IoU阈值
        """
        if (
            (layout := self.layout()) is None
            or (item := layout.itemAt(1)) is None
            or (widget := item.widget()) is None
        ):
            logger.warning("Cannot get IoU threshold")
            return self.default_iou_threshold
        return widget.value()
