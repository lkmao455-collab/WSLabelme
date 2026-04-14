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

    def __init__(self, file_path, index, is_labeled=False, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.index = index
        self.selected = False
        self.is_labeled = is_labeled

        # 拖动检测相关
        self._drag_start_pos = None
        self._is_dragging = False
        self._drag_threshold = 5  # 拖动阈值（像素）

        self.setFixedSize(100, 80)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setCursor(QtGui.QCursor(Qt.PointingHandCursor))

        # 设置样式
        self.updateStyle()

        # 布局
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        # 序号标签 - 已标注显示绿色，未标注显示灰色
        self.index_label = QtWidgets.QLabel(str(index), self)
        self.index_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        if self.is_labeled:
            self.index_label.setStyleSheet("color: #28a745; font-size: 10px; font-weight: bold;")
        else:
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
        """鼠标按下事件 - 只记录位置用于点击检测"""
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
            self._is_dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 只在本地检测是否开始拖动"""
        if self._drag_start_pos is not None and not self._is_dragging:
            distance = (event.pos() - self._drag_start_pos).manhattanLength()
            if distance > self._drag_threshold:
                self._is_dragging = True
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件 - 如果不是拖动则触发点击"""
        if event.button() == Qt.LeftButton:
            # 只有在没有发生拖动时才触发点击
            if not self._is_dragging and self._drag_start_pos is not None:
                self.clicked.emit(self.file_path)
            self._drag_start_pos = None
            self._is_dragging = False
        super().mouseReleaseEvent(event)


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

        # 鼠标拖动滚动相关
        self._drag_start_x = 0
        self._scroll_start_value = 0
        self._is_dragging = False
        self._drag_threshold = 5  # 拖动阈值（像素）

    def mousePressEvent(self, event):
        """鼠标按下事件 - 只在空白区域记录位置"""
        if event.button() == Qt.LeftButton:
            self._drag_start_x = event.globalPos().x()
            self._scroll_start_value = self.scroll_area.horizontalScrollBar().value()
            self._is_dragging = False
            self._local_drag_start_pos = event.globalPos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 检测并开始拖动滚动"""
        if hasattr(self, '_local_drag_start_pos') and not self._is_dragging:
            distance = abs(event.globalPos().x() - self._local_drag_start_pos.x())
            if distance > self._drag_threshold:
                self._is_dragging = True
                self.setCursor(Qt.ClosedHandCursor)
        if self._is_dragging:
            delta = self._drag_start_x - event.globalPos().x()
            new_value = self._scroll_start_value + delta
            scrollbar = self.scroll_area.horizontalScrollBar()
            scrollbar.setValue(new_value)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件 - 结束拖动"""
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            if hasattr(self, '_local_drag_start_pos'):
                del self._local_drag_start_pos
            self.unsetCursor()
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        """鼠标离开事件 - 取消拖动"""
        self._is_dragging = False
        self.unsetCursor()
        super().leaveEvent(event)

    def eventFilter(self, obj, event):
        """事件过滤器 - 处理缩略图项的拖动"""
        if isinstance(obj, ThumbnailItem):
            if event.type() == QtCore.QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    # 记录拖动起始位置
                    self._drag_start_x = event.globalPos().x()
                    self._scroll_start_value = self.scroll_area.horizontalScrollBar().value()
                    self._is_dragging = False
                    self._drag_start_pos = event.globalPos()
                    return False  # 不阻止，让子部件处理点击
            elif event.type() == QtCore.QEvent.MouseMove:
                if hasattr(self, '_drag_start_pos') and not self._is_dragging:
                    # 检测是否超过拖动阈值
                    distance = abs(event.globalPos().x() - self._drag_start_pos.x())
                    if distance > self._drag_threshold:
                        self._is_dragging = True
                        self.setCursor(Qt.ClosedHandCursor)
                if self._is_dragging:
                    # 执行拖动滚动
                    delta = self._drag_start_x - event.globalPos().x()
                    new_value = self._scroll_start_value + delta
                    self.scroll_area.horizontalScrollBar().setValue(new_value)
                    return True  # 阻止事件，避免触发点击
            elif event.type() == QtCore.QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    was_dragging = self._is_dragging
                    self._is_dragging = False
                    if hasattr(self, '_drag_start_pos'):
                        del self._drag_start_pos
                    self.unsetCursor()
                    if was_dragging:
                        return True  # 阻止事件，避免触发点击
        return super().eventFilter(obj, event)
    
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
    
    def addFile(self, file_path, index=None, is_labeled=False):
        """添加文件到列表"""
        if index is None:
            index = len(self.items) + 1

        self.file_paths.append(file_path)

        # 创建缩略图项
        thumb_item = ThumbnailItem(file_path, index, is_labeled)
        thumb_item.clicked.connect(self.onItemClicked)

        # 为缩略图项安装事件过滤器以支持拖动
        thumb_item.installEventFilter(self)

        # 插入到stretch之前
        self.container_layout.insertWidget(len(self.items), thumb_item)
        self.items.append(thumb_item)
    
    def setCurrentFile(self, file_path):
        """设置当前选中的文件"""
        # 规范化路径以便正确匹配
        normalized_path = osp.normpath(osp.abspath(file_path))
        self.current_file = normalized_path

        for item in self.items:
            item.setSelected(osp.normpath(osp.abspath(item.file_path)) == normalized_path)

        # 延迟滚动到选中项，确保布局已更新
        QtCore.QTimer.singleShot(50, lambda: self._scrollToFile(file_path))

    def _scrollToFile(self, file_path):
        """滚动到指定文件位置"""
        normalized_path = osp.normpath(osp.abspath(file_path))
        for item in self.items:
            if osp.normpath(osp.abspath(item.file_path)) == normalized_path:
                self.scroll_area.ensureWidgetVisible(item, 50, 0)
                break
    
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
        if self.current_file:
            for i, fp in enumerate(self.file_paths):
                if osp.normpath(osp.abspath(fp)) == osp.normpath(osp.abspath(self.current_file)):
                    return i
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

    def setFileLabeled(self, file_path, is_labeled=True):
        """设置指定文件的标注状态，并在变为已标注时移动到已标注区域最右边"""
        # 规范化路径以便正确匹配
        normalized_target_path = osp.normpath(osp.abspath(file_path))

        # 找到对应的项
        target_item = None
        target_index = -1
        for i, item in enumerate(self.items):
            if osp.normpath(osp.abspath(item.file_path)) == normalized_target_path:
                target_item = item
                target_index = i
                break

        if target_item is None:
            return

        # 更新标注状态
        target_item.is_labeled = is_labeled
        # 更新序号标签颜色
        if is_labeled:
            target_item.index_label.setStyleSheet("color: #28a745; font-size: 10px; font-weight: bold;")
        else:
            target_item.index_label.setStyleSheet("color: #333; font-size: 10px; font-weight: bold;")
        target_item.update()

        # 如果变为已标注，将其移动到已标注区域的最右边
        # 但如果是当前正在查看的文件，不移动它（避免索引错乱）
        if is_labeled and target_index >= 0 and normalized_target_path != self.current_file:
            # 找到最后一个已标注文件的位置
            last_labeled_index = -1
            for i, item in enumerate(self.items):
                if item.is_labeled:
                    last_labeled_index = i

            # 如果当前位置在最后一个已标注文件之后，需要移动
            if target_index > last_labeled_index:
                # 从当前位置移除
                self.items.pop(target_index)
                self.file_paths.pop(target_index)

                # 插入到已标注区域最后（即 last_labeled_index+1 位置）
                insert_pos = last_labeled_index + 1
                self.items.insert(insert_pos, target_item)
                self.file_paths.insert(insert_pos, target_item.file_path)

                # 从布局中移除并重新插入
                self.container_layout.removeWidget(target_item)
                self.container_layout.insertWidget(insert_pos, target_item)

                # 更新所有项的序号
                self._updateIndices()

                # 注意：不在这里滚动，由 setCurrentFile 统一处理滚动

    def removeFile(self, file_path):
        """从列表中移除指定文件"""
        normalized_path = osp.normpath(osp.abspath(file_path))

        # 找到对应的项
        target_index = -1
        for i, item in enumerate(self.items):
            if osp.normpath(osp.abspath(item.file_path)) == normalized_path:
                target_index = i
                break

        if target_index < 0:
            return False  # 文件不在列表中

        # 获取要删除的项
        target_item = self.items[target_index]

        # 从布局中移除
        self.container_layout.removeWidget(target_item)
        target_item.deleteLater()

        # 从列表中移除
        self.items.pop(target_index)
        self.file_paths.pop(target_index)

        # 如果删除的是当前选中的文件，清除当前选中
        if self.current_file == normalized_path:
            self.current_file = None

        # 更新所有项的序号
        self._updateIndices()

        return True

    def getPreviousFile(self, file_path):
        """获取指定文件的前一个文件路径"""
        normalized_path = osp.normpath(osp.abspath(file_path))

        for i, fp in enumerate(self.file_paths):
            if osp.normpath(osp.abspath(fp)) == normalized_path:
                if i > 0:
                    return self.file_paths[i - 1]
                break
        return None

    def getNextFile(self, file_path):
        """获取指定文件的后一个文件路径"""
        normalized_path = osp.normpath(osp.abspath(file_path))

        for i, fp in enumerate(self.file_paths):
            if osp.normpath(osp.abspath(fp)) == normalized_path:
                if i < len(self.file_paths) - 1:
                    return self.file_paths[i + 1]
                break
        return None

    def _updateIndices(self):
        """更新所有项的序号显示"""
        for i, item in enumerate(self.items):
            item.index = i + 1
            item.index_label.setText(str(item.index))
