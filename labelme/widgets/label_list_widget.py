from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QStyle

# 文件头部说明:
# 本模块定义了Labelme中的标签列表组件。
# 主要功能包括：标签项的显示、选择、拖拽排序、HTML格式支持等。
# 这是用户管理标注标签列表的主要界面组件。

# https://stackoverflow.com/a/2039745/4158863
class HTMLDelegate(QtWidgets.QStyledItemDelegate):
    """
    HTML委托类
    
    用于在列表视图中显示HTML格式的文本内容。
    支持富文本显示，包括颜色、字体样式等。
    """
    def __init__(self, parent=None):
        """
        初始化HTML委托
        
        Args:
            parent: 父对象
        """
        super(HTMLDelegate, self).__init__()
        self.doc = QtGui.QTextDocument(self)

    def paint(self, painter, option, index):
        """
        绘制列表项
        
        使用HTML格式绘制列表项的内容。
        
        Args:
            painter: 绘图画家对象
            option: 样式选项
            index: 模型索引
        """
        painter.save()

        options = QtWidgets.QStyleOptionViewItem(option)

        self.initStyleOption(options, index)
        self.doc.setHtml(options.text)
        options.text = ""

        style = (
            QtWidgets.QApplication.style()
            if options.widget is None
            else options.widget.style()
        )
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()

        if option.state & QStyle.State_Selected:
            ctx.palette.setColor(
                QPalette.Text,
                option.palette.color(QPalette.Active, QPalette.HighlightedText),
            )
        else:
            ctx.palette.setColor(
                QPalette.Text,
                option.palette.color(QPalette.Active, QPalette.Text),
            )

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options)

        if index.column() != 0:
            textRect.adjust(5, 0, 0, 0)

        thefuckyourshitup_constant = 4
        margin = (option.rect.height() - options.fontMetrics.height()) // 2
        margin = margin - thefuckyourshitup_constant
        textRect.setTop(textRect.top() + margin)

        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        self.doc.documentLayout().draw(painter, ctx)

        painter.restore()

    def sizeHint(self, option, index):
        """
        获取项的大小提示
        
        根据HTML内容计算合适的项大小。
        
        Args:
            option: 样式选项
            index: 模型索引
            
        Returns:
            QtCore.QSize: 项的大小
        """
        thefuckyourshitup_constant = 4
        return QtCore.QSize(
            int(self.doc.idealWidth()),
            int(self.doc.size().height() - thefuckyourshitup_constant),
        )


class LabelListWidgetItem(QtGui.QStandardItem):
    """
    标签列表项类
    
    继承自QStandardItem，用于表示标签列表中的单个项目。
    包含标签文本、形状对象、选中状态等信息。
    """
    def __init__(self, text=None, shape=None):
        """
        初始化标签列表项
        
        Args:
            text: 标签文本
            shape: 关联的形状对象
        """
        super(LabelListWidgetItem, self).__init__()
        self.setText(text or "")
        self.setShape(shape)

        # 设置项的属性
        self.setCheckable(True)           # 可检查
        self.setCheckState(Qt.Checked)    # 默认选中
        self.setEditable(False)           # 不可编辑
        self.setTextAlignment(Qt.AlignBottom)  # 文本对齐方式

    def clone(self):
        """
        克隆当前项
        
        Returns:
            LabelListWidgetItem: 克隆的项
        """
        return LabelListWidgetItem(self.text(), self.shape())

    def setShape(self, shape):
        """
        设置关联的形状对象
        
        Args:
            shape: 形状对象
        """
        self.setData(shape, Qt.UserRole)

    def shape(self):
        """
        获取关联的形状对象
        
        Returns:
            object: 形状对象
        """
        return self.data(Qt.UserRole)

    def __hash__(self):
        """
        获取对象的哈希值
        
        Returns:
            int: 对象ID作为哈希值
        """
        return id(self)

    def __repr__(self):
        """
        获取对象的字符串表示
        
        Returns:
            str: 对象的字符串表示
        """
        return '{}("{}")'.format(self.__class__.__name__, self.text())


class StandardItemModel(QtGui.QStandardItemModel):
    """
    标准项模型类
    
    继承自QStandardItemModel，增加了项被拖拽放下时的信号。
    """
    itemDropped = QtCore.pyqtSignal()

    def removeRows(self, *args, **kwargs):
        """
        移除行
        
        重写移除行方法，在移除后发射itemDropped信号。
        
        Returns:
            bool: 移除是否成功
        """
        ret = super().removeRows(*args, **kwargs)
        self.itemDropped.emit()
        return ret


class LabelListWidget(QtWidgets.QListView):
    """
    标签列表组件类
    
    继承自QListView，提供了完整的标签列表管理功能，包括：
    - 标签项的显示和选择
    - 拖拽排序
    - HTML格式支持
    - 项的增删改查
    """
    itemDoubleClicked = QtCore.pyqtSignal(LabelListWidgetItem)  # 双击信号
    itemSelectionChanged = QtCore.pyqtSignal(list, list)        # 选择变化信号

    def __init__(self, parent=None):
        """
        初始化标签列表组件
        
        Args:
            parent: 父窗口
        """
        super(LabelListWidget, self).__init__(parent)
        self._selectedItems = []

        # 设置模型（不设置WindowFlags，避免成为独立窗口）
        self.setModel(StandardItemModel())
        self.model().setItemPrototype(LabelListWidgetItem())
        self.setItemDelegate(HTMLDelegate())
        
        # 设置选择和拖拽模式
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

        # 连接信号
        self.doubleClicked.connect(self.itemDoubleClickedEvent)
        self.selectionModel().selectionChanged.connect(self.itemSelectionChangedEvent)

    def __len__(self):
        """
        获取列表长度
        
        Returns:
            int: 列表项数量
        """
        return self.model().rowCount()

    def __getitem__(self, i):
        """
        获取指定索引的项
        
        Args:
            i: 索引
            
        Returns:
            LabelListWidgetItem: 指定索引的项
        """
        return self.model().item(i)

    def __iter__(self):
        """
        迭代器支持
        
        Yields:
            LabelListWidgetItem: 列表中的每一项
        """
        for i in range(len(self)):
            yield self[i]

    @property
    def itemDropped(self):
        """
        获取项被拖拽放下的信号
        
        Returns:
            QtCore.pyqtSignal: 信号对象
        """
        return self.model().itemDropped

    @property
    def itemChanged(self):
        """
        获取项变化信号
        
        Returns:
            QtCore.pyqtSignal: 信号对象
        """
        return self.model().itemChanged

    def itemSelectionChangedEvent(self, selected, deselected):
        """
        项选择变化事件处理
        
        Args:
            selected: 新选中的项列表
            deselected: 取消选中的项列表
        """
        selected = [self.model().itemFromIndex(i) for i in selected.indexes()]
        deselected = [self.model().itemFromIndex(i) for i in deselected.indexes()]
        self.itemSelectionChanged.emit(selected, deselected)

    def itemDoubleClickedEvent(self, index):
        """
        项双击事件处理
        
        Args:
            index: 双击项的索引
        """
        self.itemDoubleClicked.emit(self.model().itemFromIndex(index))

    def selectedItems(self):
        """
        获取选中的项列表
        
        Returns:
            list: 选中的项列表
        """
        return [self.model().itemFromIndex(i) for i in self.selectedIndexes()]

    def scrollToItem(self, item):
        """
        滚动到指定项
        
        Args:
            item: 目标项
        """
        self.scrollTo(self.model().indexFromItem(item))

    def addItem(self, item):
        """
        添加项到列表
        
        Args:
            item: 要添加的项
            
        Raises:
            TypeError: 当item不是LabelListWidgetItem类型时
        """
        if not isinstance(item, LabelListWidgetItem):
            raise TypeError("item must be LabelListWidgetItem")
        self.model().setItem(self.model().rowCount(), 0, item)
        item.setSizeHint(self.itemDelegate().sizeHint(None, None))

    def removeItem(self, item):
        """
        从列表中移除项
        
        Args:
            item: 要移除的项
        """
        index = self.model().indexFromItem(item)
        self.model().removeRows(index.row(), 1)

    def selectItem(self, item):
        """
        选择指定项
        
        Args:
            item: 要选择的项
        """
        index = self.model().indexFromItem(item)
        self.selectionModel().select(index, QtCore.QItemSelectionModel.Select)

    def findItemByShape(self, shape):
        """
        根据形状查找项
        
        Args:
            shape: 要查找的形状对象
            
        Returns:
            LabelListWidgetItem: 找到的项
            
        Raises:
            ValueError: 当找不到对应形状的项时
        """
        for row in range(self.model().rowCount()):
            item = self.model().item(row, 0)
            if item.shape() == shape:
                return item
        raise ValueError("cannot find shape: {}".format(shape))

    def clear(self):
        """
        清空列表
        """
        self.model().clear()
