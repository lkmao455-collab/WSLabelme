# flake8: noqa

"""
缩略图文件列表组件

该组件提供了一个横向滚动的缩略图列表，用于显示文件夹中的图像文件。
每个缩略图显示图像预览和序号，支持点击选择文件。
"""

import os.path as osp

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from loguru import logger


class ThumbnailItem(QtWidgets.QFrame):
    """单个缩略图项"""
    
    clicked = QtCore.pyqtSignal(str)  # 发送文件路径
    
    def __init__(self, file_path, index, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.index = index
        self.selected = False
        
        self.setFixedSize(100, 80)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setCursor(QtGui.QCursor(Qt.PointingHandCursor))
        
        # 设置样式
        self.updateStyle()
        
        # 布局
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        
        # 序号标签
        self.index_label = QtWidgets.QLabel(str(index), self)
        self.index_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.index_label.setStyleSheet("color: #333; font-size: 10px; font-weight: bold;")
        layout.addWidget(self.index_label)
        
        # 缩略图标签
        self.thumb_label = QtWidgets.QLabel(self)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setFixedSize(80, 60)
        layout.addWidget(self.thumb_label, alignment=Qt.AlignCenter)
        
        # 加载缩略图
        self.loadThumbnail()
    
    def loadThumbnail(self):
        """加载图像缩略图"""
        try:
            image = QtGui.QImage(self.file_path)
            if not image.isNull():
                # 缩放图像以适应固定大小
                scaled = image.scaled(
                    80, 60,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                pixmap = QtGui.QPixmap.fromImage(scaled)
                self.thumb_label.setPixmap(pixmap)
            else:
                # 加载失败显示默认图标
                self.thumb_label.setText("?")
                self.thumb_label.setStyleSheet("color: #999; font-size: 20px;")
        except Exception as e:
            logger.warning(f"Failed to load thumbnail for {self.file_path}: {e}")
            self.thumb_label.setText("?")
            self.thumb_label.setStyleSheet("color: #999; font-size: 20px;")
    
    def setSelected(self, selected):
        """设置选中状态"""
        self.selected = selected
        self.updateStyle()
    
    def updateStyle(self):
        """更新样式"""
        if self.selected:
            self.setStyleSheet("""
                ThumbnailItem {
                    background-color: #e0e0e0;
                    border: 2px solid #ff6b6b;
                    border-radius: 4px;
                }
            """)
        else:
            self.setStyleSheet("""
                ThumbnailItem {
                    background-color: #f5f5f5;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }
                ThumbnailItem:hover {
                    background-color: #e8e8e8;
                    border: 1px solid #999;
                }
            """)
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.file_path)
        super().mousePressEvent(event)


class ThumbnailFileList(QtWidgets.QWidget):
    """缩略图文件列表组件"""
    
    fileSelected = QtCore.pyqtSignal(str)  # 文件被选中时发送
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.items = []  # ThumbnailItem列表
        self.file_paths = []  # 文件路径列表
        self.current_file = None  # 当前选中的文件
        
        # 主布局
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 左滚动按钮
        self.left_btn = QtWidgets.QPushButton("◀", self)
        self.left_btn.setFixedSize(30, 80)
        self.left_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                border: none;
                font-size: 16px;
                color: #666;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
        """)
        self.left_btn.clicked.connect(self.scrollLeft)
        layout.addWidget(self.left_btn)
        
        # 滚动区域
        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFixedHeight(90)
        
        # 缩略图容器
        self.container = QtWidgets.QWidget(self)
        self.container_layout = QtWidgets.QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(5, 5, 5, 5)
        self.container_layout.setSpacing(5)
        self.container_layout.addStretch()
        
        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)
        
        # 右滚动按钮
        self.right_btn = QtWidgets.QPushButton("▶", self)
        self.right_btn.setFixedSize(30, 80)
        self.right_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                border: none;
                font-size: 16px;
                color: #666;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
        """)
        self.right_btn.clicked.connect(self.scrollRight)
        layout.addWidget(self.right_btn)
    
    def clear(self):
        """清空列表"""
        # 移除所有缩略图项
        while self.container_layout.count() > 1:  # 保留stretch
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.items = []
        self.file_paths = []
        self.current_file = None
    
    def addFile(self, file_path, index=None):
        """添加文件到列表"""
        if index is None:
            index = len(self.items) + 1
        
        self.file_paths.append(file_path)
        
        # 创建缩略图项
        thumb_item = ThumbnailItem(file_path, index)
        thumb_item.clicked.connect(self.onItemClicked)
        
        # 插入到stretch之前
        self.container_layout.insertWidget(len(self.items), thumb_item)
        self.items.append(thumb_item)
    
    def setCurrentFile(self, file_path):
        """设置当前选中的文件"""
        self.current_file = file_path
        
        for item in self.items:
            item.setSelected(item.file_path == file_path)
            
            # 确保选中项可见
            if item.file_path == file_path:
                self.scroll_area.ensureWidgetVisible(item, 50, 0)
    
    def onItemClicked(self, file_path):
        """缩略图项被点击"""
        self.setCurrentFile(file_path)
        self.fileSelected.emit(file_path)
    
    def scrollLeft(self):
        """向左滚动"""
        scrollbar = self.scroll_area.horizontalScrollBar()
        scrollbar.setValue(scrollbar.value() - 100)
    
    def scrollRight(self):
        """向右滚动"""
        scrollbar = self.scroll_area.horizontalScrollBar()
        scrollbar.setValue(scrollbar.value() + 100)
    
    def count(self):
        """返回文件数量"""
        return len(self.items)
    
    def setCurrentRow(self, row):
        """设置当前选中的行（兼容旧接口）"""
        if 0 <= row < len(self.file_paths):
            self.setCurrentFile(self.file_paths[row])
    
    def currentRow(self):
        """获取当前选中的行（兼容旧接口）"""
        if self.current_file and self.current_file in self.file_paths:
            return self.file_paths.index(self.current_file)
        return -1
    
    def repaint(self):
        """重绘组件（兼容旧接口）"""
        super().repaint()
        for item in self.items:
            item.update()
    
    def findItems(self, text, flags=None):
        """查找项目（兼容旧接口，返回空列表）"""
        # 缩略图列表不支持查找，返回空列表
        return []
    
    def setCurrentItem(self, item):
        """设置当前项目（兼容旧接口）"""
        pass
