import re

from loguru import logger
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import labelme.utils

# 文件头部说明:
# 本模块定义了Labelme中的标签对话框组件。
# 主要功能包括：标签输入、标签历史管理、标签标志管理、标签描述等。
# 这是用户在标注过程中输入和管理标签信息的主要界面组件。

# TODO(unknown):
# - Calculate optimal position so as not to go out of screen area.


class LabelQLineEdit(QtWidgets.QLineEdit):
    """
    自定义标签输入框
    
    继承自QLineEdit，增加了对列表控件的支持，允许通过上下键在标签列表中导航。
    """
    def setListWidget(self, list_widget):
        """
        设置关联的列表控件
        
        Args:
            list_widget: QListWidget对象
        """
        self.list_widget = list_widget

    def keyPressEvent(self, e):
        """
        键盘事件处理
        
        重写键盘事件处理，支持上下键在标签列表中导航。
        
        Args:
            e: 键盘事件对象
        """
        if e.key() in [QtCore.Qt.Key_Up, QtCore.Qt.Key_Down]:
            # 如果按下上下键，将事件传递给关联的列表控件
            self.list_widget.keyPressEvent(e)
        else:
            # 其他按键正常处理
            super(LabelQLineEdit, self).keyPressEvent(e)


class LabelDialog(QtWidgets.QDialog):
    """
    标签对话框类
    
    提供一个完整的标签输入和管理界面，包括：
    - 标签文本输入
    - 标签历史列表
    - 标签标志（flags）管理
    - 标签描述输入
    - 自动完成功能
    """
    def __init__(
        self,
        text="Enter object label",
        parent=None,
        labels=None,
        sort_labels=True,
        show_text_field=True,
        completion="startswith",
        fit_to_content=None,
        flags=None,
    ):
        """
        初始化标签对话框
        
        Args:
            text: 输入框的占位符文本
            parent: 父窗口对象
            labels: 标签历史列表
            sort_labels: 是否对标签进行排序
            show_text_field: 是否显示文本输入框
            completion: 自动完成模式，可选"startswith"或"contains"
            fit_to_content: 内容适配设置
            flags: 标签标志配置字典
        """
        if fit_to_content is None:
            fit_to_content = {"row": False, "column": True}
        self._fit_to_content = fit_to_content

        super(LabelDialog, self).__init__(parent)
        
        # 创建标签输入框
        self.edit = LabelQLineEdit(self)
        self.edit.setPlaceholderText(text)
        self.edit.setValidator(labelme.utils.labelValidator())  # 设置标签验证器
        self.edit.editingFinished.connect(self.postProcess)     # 连接编辑完成信号
        if flags:
            self.edit.textChanged.connect(self.updateFlags)     # 连接文本变化信号
        
        # 创建组ID输入框
        self.edit_group_id = QtWidgets.QLineEdit(self)
        self.edit_group_id.setPlaceholderText("Group ID")
        self.edit_group_id.setValidator(
            QtGui.QRegExpValidator(QtCore.QRegExp(r"\d*"), None)  # 只允许数字
        )
        
        # 创建主布局
        layout = QtWidgets.QVBoxLayout()
        
        # 添加文本输入区域
        if show_text_field:
            layout_edit = QtWidgets.QHBoxLayout()
            layout_edit.addWidget(self.edit, 6)        # 标签输入框占6份空间
            layout_edit.addWidget(self.edit_group_id, 2)  # 组ID输入框占2份空间
            layout.addLayout(layout_edit)
        
        # 添加按钮区域
        self.buttonBox = bb = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self,
        )
        bb.button(bb.Ok).setIcon(labelme.utils.newIcon("done"))      # 确定按钮图标
        bb.button(bb.Cancel).setIcon(labelme.utils.newIcon("undo"))  # 取消按钮图标
        bb.accepted.connect(self.validate)  # 连接确定按钮
        bb.rejected.connect(self.reject)    # 连接取消按钮
        layout.addWidget(bb)
        
        # 添加标签列表
        self.labelList = QtWidgets.QListWidget(self)
        if self._fit_to_content["row"]:
            self.labelList.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        if self._fit_to_content["column"]:
            self.labelList.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        self._sort_labels = sort_labels
        if labels:
            self.labelList.addItems(labels)  # 添加标签历史
        if self._sort_labels:
            self.labelList.sortItems()  # 排序标签
        else:
            # 如果不排序，允许拖拽重新排序
            self.labelList.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        
        # 连接标签列表事件
        self.labelList.currentItemChanged.connect(self.labelSelected)      # 当前项变化
        self.labelList.itemDoubleClicked.connect(self.labelDoubleClicked)  # 双击确认
        self.labelList.setFixedHeight(150)  # 设置固定高度
        self.edit.setListWidget(self.labelList)  # 设置输入框的关联列表
        layout.addWidget(self.labelList)
        
        # 添加标签标志区域
        if flags is None:
            flags = {}
        self._flags = flags
        self.flagsLayout = QtWidgets.QVBoxLayout()
        self.resetFlags()  # 重置标志
        layout.addItem(self.flagsLayout)
        self.edit.textChanged.connect(self.updateFlags)  # 连接文本变化信号
        
        # 添加标签描述区域
        self.editDescription = QtWidgets.QTextEdit(self)
        self.editDescription.setPlaceholderText("Label description")
        self.editDescription.setFixedHeight(50)
        layout.addWidget(self.editDescription)
        
        self.setLayout(layout)
        
        # 设置自动完成
        completer = QtWidgets.QCompleter()
        if completion == "startswith":
            completer.setCompletionMode(QtWidgets.QCompleter.InlineCompletion)
            # Default settings.
            # completer.setFilterMode(QtCore.Qt.MatchStartsWith)
        elif completion == "contains":
            completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
            completer.setFilterMode(QtCore.Qt.MatchContains)
        else:
            raise ValueError("Unsupported completion: {}".format(completion))
        completer.setModel(self.labelList.model())
        self.edit.setCompleter(completer)

    def addLabelHistory(self, label):
        """
        添加标签到历史列表
        
        Args:
            label: 标签文本
        """
        if self.labelList.findItems(label, QtCore.Qt.MatchExactly):
            return  # 如果标签已存在，则不重复添加
        self.labelList.addItem(label)
        if self._sort_labels:
            self.labelList.sortItems()

    def labelSelected(self, item):
        """
        标签选择事件处理
        
        当用户在标签列表中选择一个标签时，将其文本设置到输入框中。
        
        Args:
            item: 选中的列表项
        """
        self.edit.setText(item.text())

    def validate(self):
        """
        验证输入并接受对话框
        
        检查输入框中的文本是否有效，如果有效则接受对话框。
        """
        if not self.edit.isEnabled():
            self.accept()
            return

        text = self.edit.text()
        if hasattr(text, "strip"):
            text = text.strip()
        else:
            text = text.trimmed()
        if text:
            self.accept()

    def labelDoubleClicked(self, item):
        """
        标签双击事件处理
        
        双击标签列表中的项目时，直接确认选择。
        
        Args:
            item: 双击的列表项
        """
        self.validate()

    def postProcess(self):
        """
        输入后处理
        
        对输入的标签文本进行清理（去除首尾空白）。
        """
        text = self.edit.text()
        if hasattr(text, "strip"):
            text = text.strip()
        else:
            text = text.trimmed()
        self.edit.setText(text)

    def updateFlags(self, label_new):
        """
        更新标签标志
        
        根据新的标签文本，更新相关的标志状态。
        
        Args:
            label_new: 新的标签文本
        """
        # 保持共享标志的状态
        flags_old = self.getFlags()

        flags_new = {}
        for pattern, keys in self._flags.items():
            if re.match(pattern, label_new):
                for key in keys:
                    flags_new[key] = flags_old.get(key, False)
        self.setFlags(flags_new)

    def deleteFlags(self):
        """
        删除所有标志控件
        
        清空标志布局中的所有控件。
        """
        for i in reversed(range(self.flagsLayout.count())):
            item = self.flagsLayout.itemAt(i).widget()
            self.flagsLayout.removeWidget(item)
            item.setParent(None)

    def resetFlags(self, label=""):
        """
        重置标志状态
        
        根据标签文本重置标志状态。
        
        Args:
            label: 标签文本
        """
        flags = {}
        for pattern, keys in self._flags.items():
            if re.match(pattern, label):
                for key in keys:
                    flags[key] = False
        self.setFlags(flags)

    def setFlags(self, flags):
        """
        设置标志控件
        
        根据标志字典创建相应的复选框控件。
        
        Args:
            flags: 标志字典
        """
        self.deleteFlags()
        for key in flags:
            item = QtWidgets.QCheckBox(key, self)
            item.setChecked(flags[key])
            self.flagsLayout.addWidget(item)
            item.show()

    def getFlags(self):
        """
        获取当前标志状态
        
        Returns:
            dict: 当前标志状态字典
        """
        flags = {}
        for i in range(self.flagsLayout.count()):
            item = self.flagsLayout.itemAt(i).widget()
            flags[item.text()] = item.isChecked()
        return flags

    def getGroupId(self):
        """
        获取组ID
        
        Returns:
            int or None: 组ID，如果为空则返回None
        """
        group_id = self.edit_group_id.text()
        if group_id:
            return int(group_id)
        return None

    def popUp(self, text=None, move=True, flags=None, group_id=None, description=None):
        """
        显示对话框
        
        弹出标签对话框，允许用户输入或选择标签。
        
        Args:
            text: 初始标签文本
            move: 是否移动到鼠标位置
            flags: 初始标志状态
            group_id: 初始组ID
            description: 初始描述文本
            
        Returns:
            tuple: (标签文本, 标志字典, 组ID, 描述文本) 或 (None, None, None, None)
        """
        # 根据内容调整列表高度和宽度
        if self._fit_to_content["row"]:
            self.labelList.setMinimumHeight(
                self.labelList.sizeHintForRow(0) * self.labelList.count() + 2
            )
        if self._fit_to_content["column"]:
            self.labelList.setMinimumWidth(self.labelList.sizeHintForColumn(0) + 2)
        
        # 设置初始文本
        if text is None:
            text = self.edit.text()
        
        # 设置描述文本
        if description is None:
            description = ""
        self.editDescription.setPlainText(description)
        
        # 设置标志
        if flags:
            self.setFlags(flags)
        else:
            self.resetFlags(text)
        
        # 设置标签文本和选择
        self.edit.setText(text)
        self.edit.setSelection(0, len(text))
        
        # 设置组ID
        if group_id is None:
            self.edit_group_id.clear()
        else:
            self.edit_group_id.setText(str(group_id))
        
        # 在列表中查找并选中匹配的标签
        items = self.labelList.findItems(text, QtCore.Qt.MatchFixedString)
        if items:
            if len(items) != 1:
                logger.warning("Label list has duplicate '{}'".format(text))
            self.labelList.setCurrentItem(items[0])
            row = self.labelList.row(items[0])
            # 检查 completer 是否存在，避免 AttributeError
            completer = self.edit.completer()
            if completer is not None:
                completer.setCurrentRow(row)
        
        # 设置焦点和位置
        self.edit.setFocus(QtCore.Qt.PopupFocusReason)
        if move:
            self.move(QtGui.QCursor.pos())
        
        # 显示对话框并返回结果
        if self.exec_():
            return (
                self.edit.text(),
                self.getFlags(),
                self.getGroupId(),
                self.editDescription.toPlainText(),
            )
        else:
            return None, None, None, None
