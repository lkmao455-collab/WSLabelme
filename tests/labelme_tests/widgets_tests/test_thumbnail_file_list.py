# -*- encoding: utf-8 -*-
"""
缩略图文件列表组件的单元测试

测试内容：
- 路径规范化匹配（解决不同路径格式导致的选中错位问题）
- setCurrentFile 方法
- setFileLabeled 方法
- currentRow 方法
- _scrollToFile 方法
"""

import os
import os.path as osp
import tempfile

import pytest
from PyQt5 import QtCore

from labelme.widgets import ThumbnailFileList


@pytest.mark.gui
class TestThumbnailFileList:
    """ThumbnailFileList 组件测试类"""

    @pytest.fixture
    def widget(self, qtbot):
        """创建测试用的 ThumbnailFileList 实例"""
        widget = ThumbnailFileList()
        qtbot.addWidget(widget)
        return widget

    @pytest.fixture
    def temp_image_files(self):
        """创建临时图像文件用于测试"""
        temp_dir = tempfile.mkdtemp()
        image_files = []
        for i in range(5):
            # 创建简单的图像文件
            img_path = osp.join(temp_dir, f"image_{i+1}.png")
            with open(img_path, 'wb') as f:
                # 创建一个最小的有效PNG文件
                f.write(self._create_minimal_png())
            image_files.append(img_path)
        yield image_files
        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

    def _create_minimal_png(self):
        """创建一个最小的有效 PNG 图像数据"""
        # 1x1 像素的透明 PNG
        return bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG 签名
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 像素
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
            0x89, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x44, 0x41,  # IDAT chunk
            0x54, 0x08, 0xD7, 0x63, 0xFC, 0xCF, 0xC0, 0x00,
            0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x05, 0xFE,
            0xD7, 0x18, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45,  # IEND chunk
            0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
        ])

    def test_setCurrentFile_with_normalized_path(self, widget, temp_image_files):
        """测试 setCurrentFile 能正确处理不同格式的路径"""
        # 添加文件到列表
        for i, file_path in enumerate(temp_image_files):
            widget.addFile(file_path, index=i+1, is_labeled=False)

        target_file = temp_image_files[2]  # image_3.png

        # 测试1: 使用绝对路径
        widget.setCurrentFile(target_file)
        assert widget.current_file is not None
        assert osp.normpath(osp.abspath(widget.current_file)) == osp.normpath(osp.abspath(target_file))

        # 测试2: 使用相对路径（如果可能）
        rel_path = osp.relpath(target_file)
        widget.setCurrentFile(rel_path)
        assert osp.normpath(osp.abspath(widget.current_file)) == osp.normpath(osp.abspath(target_file))

        # 测试3: 使用混合分隔符的路径（Windows 风格）
        mixed_path = target_file.replace('/', '\\')
        widget.setCurrentFile(mixed_path)
        assert osp.normpath(osp.abspath(widget.current_file)) == osp.normpath(osp.abspath(target_file))

    def test_setCurrentFile_selection_highlight(self, widget, temp_image_files):
        """测试 setCurrentFile 正确高亮选中项"""
        # 添加文件到列表
        for i, file_path in enumerate(temp_image_files):
            widget.addFile(file_path, index=i+1, is_labeled=False)

        target_file = temp_image_files[2]

        # 使用相对路径调用 setCurrentFile
        rel_path = osp.relpath(target_file)
        widget.setCurrentFile(rel_path)

        # 验证对应的 ThumbnailItem 被选中
        for item in widget.items:
            if osp.normpath(osp.abspath(item.file_path)) == osp.normpath(osp.abspath(target_file)):
                assert item.selected is True
            else:
                assert item.selected is False

    def test_setFileLabeled_with_path_normalization(self, widget, temp_image_files):
        """测试 setFileLabeled 能正确处理不同格式的路径"""
        # 添加文件到列表
        for i, file_path in enumerate(temp_image_files):
            widget.addFile(file_path, index=i+1, is_labeled=False)

        target_file = temp_image_files[2]

        # 使用相对路径标记为已标注
        rel_path = osp.relpath(target_file)
        widget.setFileLabeled(rel_path, is_labeled=True)

        # 验证对应项被标记为已标注
        found = False
        for item in widget.items:
            if osp.normpath(osp.abspath(item.file_path)) == osp.normpath(osp.abspath(target_file)):
                assert item.is_labeled is True
                found = True
        assert found is True

    def test_currentRow_with_path_normalization(self, widget, temp_image_files):
        """测试 currentRow 能正确返回当前选中的行号"""
        # 添加文件到列表
        for i, file_path in enumerate(temp_image_files):
            widget.addFile(file_path, index=i+1, is_labeled=False)

        # 选中第3个文件（索引2）
        target_file = temp_image_files[2]
        widget.setCurrentFile(target_file)

        # 验证 currentRow 返回正确的索引
        assert widget.currentRow() == 2

        # 使用相对路径再次设置
        rel_path = osp.relpath(target_file)
        widget.setCurrentFile(rel_path)
        assert widget.currentRow() == 2

    def test_setFileLabeled_does_not_move_current_file(self, widget, temp_image_files):
        """测试标记当前文件为已标注时不会移动它"""
        # 添加文件到列表
        for i, file_path in enumerate(temp_image_files):
            widget.addFile(file_path, index=i+1, is_labeled=False)

        target_file = temp_image_files[2]

        # 先选中文件
        widget.setCurrentFile(target_file)

        # 获取选中前的索引
        original_index = widget.currentRow()

        # 标记为已标注（使用相对路径）
        rel_path = osp.relpath(target_file)
        widget.setFileLabeled(rel_path, is_labeled=True)

        # 验证文件位置没有变化（因为是当前文件）
        assert widget.currentRow() == original_index

    def test_path_matching_edge_cases(self, widget, temp_image_files):
        """测试路径匹配的各种边界情况"""
        # 添加文件到列表
        for i, file_path in enumerate(temp_image_files):
            widget.addFile(file_path, index=i+1, is_labeled=False)

        target_file = temp_image_files[0]

        # 测试各种路径格式
        test_paths = [
            target_file,  # 原始绝对路径
            osp.relpath(target_file),  # 相对路径
            target_file.replace('\\', '/'),  # Unix风格分隔符
            target_file.upper() if os.name == 'nt' else target_file,  # Windows大小写不敏感
            target_file.lower() if os.name == 'nt' else target_file,  # Windows大小写不敏感
        ]

        for test_path in test_paths:
            widget.setCurrentFile(test_path)
            assert widget.current_file is not None
            # 验证选中的项是正确的
            for item in widget.items:
                expected_selected = osp.normpath(osp.abspath(item.file_path)) == osp.normpath(osp.abspath(target_file))
                assert item.selected == expected_selected

    def test_nonexistent_file(self, widget, temp_image_files):
        """测试处理不存在的文件路径"""
        # 添加文件到列表
        for i, file_path in enumerate(temp_image_files):
            widget.addFile(file_path, index=i+1, is_labeled=False)

        # 尝试设置一个不存在的文件
        nonexistent_file = "/path/to/nonexistent/image.png"
        widget.setCurrentFile(nonexistent_file)

        # 不应该有任何项被选中
        for item in widget.items:
            assert item.selected is False

    def test_setFileLabeled_move_to_labeled_section(self, widget, temp_image_files):
        """测试非当前文件被标记为已标注时移动到已标注区域"""
        # 添加文件到列表（全部未标注）
        for i, file_path in enumerate(temp_image_files):
            widget.addFile(file_path, index=i+1, is_labeled=False)

        # 选中第一个文件
        widget.setCurrentFile(temp_image_files[0])

        # 将第5个文件标记为已标注（不是当前文件）
        widget.setFileLabeled(temp_image_files[4], is_labeled=True)

        # 验证第5个文件移动到了已标注区域（索引0位置）
        assert widget.items[0].file_path == temp_image_files[4]
        assert widget.items[0].is_labeled is True

        # 验证其他文件位置相应调整
        # 原索引0的文件应该在索引1
        assert widget.items[1].file_path == temp_image_files[0]

    def test_fileSelected_signal_emitted(self, widget, temp_image_files, qtbot):
        """测试 fileSelected 信号正确发射"""
        # 添加文件到列表
        for i, file_path in enumerate(temp_image_files):
            widget.addFile(file_path, index=i+1, is_labeled=False)

        target_file = temp_image_files[2]

        # 监听信号
        with qtbot.waitSignal(widget.fileSelected, timeout=1000) as blocker:
            widget.setCurrentFile(target_file)

        # 验证信号参数
        assert osp.normpath(osp.abspath(blocker.args[0])) == osp.normpath(osp.abspath(target_file))


@pytest.mark.gui
def test_thumbnail_file_list_basic(qtbot):
    """基本功能测试"""
    widget = ThumbnailFileList()
    qtbot.addWidget(widget)

    assert widget.count() == 0
    assert widget.current_file is None
    assert widget.currentRow() == -1


@pytest.mark.gui
def test_thumbnail_file_list_clear(qtbot, temp_image_files):
    """测试清空功能"""
    widget = ThumbnailFileList()
    qtbot.addWidget(widget)

    # 添加文件
    for i, file_path in enumerate(temp_image_files[:3]):
        widget.addFile(file_path, index=i+1, is_labeled=False)

    assert widget.count() == 3

    # 清空
    widget.clear()
    assert widget.count() == 0
    assert widget.current_file is None
    assert len(widget.items) == 0
    assert len(widget.file_paths) == 0
