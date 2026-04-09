# flake8: noqa

import json
import os
import os.path as osp
from collections import defaultdict
from datetime import datetime

from loguru import logger
from PyQt5 import QtCore
from PyQt5 import QtWidgets

import labelme.utils

# 文件头部说明:
# 本模块定义了Labelme中的格式转换对话框组件。
# 主要功能包括：将Labelme JSON格式转换为COCO、YOLO、VOC等常用数据集格式。
# 支持批量转换和格式特定的选项配置。


class FormatConvertDialog(QtWidgets.QDialog):
    """
    格式转换对话框类

    提供一个完整的格式转换界面，包括：
    - 输入目录选择（包含Labelme JSON文件的目录）
    - 输出目录选择
    - 目标格式选择（COCO、YOLO、VOC等）
    - 格式特定选项配置
    - 转换进度显示
    """

    # 支持的格式列表
    SUPPORTED_FORMATS = [
        ("COCO", "coco", "COCO JSON格式（用于目标检测、实例分割）"),
        ("YOLO", "yolo", "YOLO格式（用于目标检测）"),
        ("VOC", "voc", "Pascal VOC格式（用于目标检测、语义分割）"),
    ]

    def __init__(self, parent=None, input_dir=None):
        """
        初始化格式转换对话框

        Args:
            parent: 父窗口对象
            input_dir: 默认输入目录
        """
        super(FormatConvertDialog, self).__init__(parent)

        self.setWindowTitle(self.tr("格式转换"))
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        # 初始化变量
        self.input_dir = input_dir or ""
        self.output_dir = ""
        self.label_list = []

        self._init_ui()

    def _init_ui(self):
        """初始化用户界面"""
        layout = QtWidgets.QVBoxLayout()

        # 输入目录选择
        input_group = QtWidgets.QGroupBox(self.tr("输入目录 (Labelme JSON 文件)"))
        input_layout = QtWidgets.QHBoxLayout()
        self.input_edit = QtWidgets.QLineEdit(self)
        self.input_edit.setReadOnly(True)
        self.input_edit.setText(self.input_dir)
        input_btn = QtWidgets.QPushButton(self.tr("浏览..."), self)
        input_btn.clicked.connect(self._browse_input)
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(input_btn)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # 输出目录选择
        output_group = QtWidgets.QGroupBox(self.tr("输出目录"))
        output_layout = QtWidgets.QHBoxLayout()
        self.output_edit = QtWidgets.QLineEdit(self)
        self.output_edit.setReadOnly(True)
        output_btn = QtWidgets.QPushButton(self.tr("浏览..."), self)
        output_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(output_btn)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # 目标格式选择
        format_group = QtWidgets.QGroupBox(self.tr("目标格式"))
        format_layout = QtWidgets.QVBoxLayout()
        self.format_combo = QtWidgets.QComboBox(self)
        for name, key, desc in self.SUPPORTED_FORMATS:
            self.format_combo.addItem(f"{name} - {desc}", key)
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        format_layout.addWidget(self.format_combo)

        # 格式特定选项
        self.options_widget = QtWidgets.QWidget(self)
        options_layout = QtWidgets.QVBoxLayout(self.options_widget)
        options_layout.setContentsMargins(0, 0, 0, 0)

        # COCO选项
        self.coco_options = QtWidgets.QWidget(self)
        coco_layout = QtWidgets.QFormLayout(self.coco_options)
        self.coco_info_name = QtWidgets.QLineEdit(self)
        self.coco_info_name.setText("labelme_dataset")
        coco_layout.addRow(self.tr("数据集名称:"), self.coco_info_name)
        self.coco_info_desc = QtWidgets.QLineEdit(self)
        self.coco_info_desc.setText("从 Labelme 格式转换")
        coco_layout.addRow(self.tr("描述:"), self.coco_info_desc)
        options_layout.addWidget(self.coco_options)

        # YOLO选项
        self.yolo_options = QtWidgets.QWidget(self)
        yolo_layout = QtWidgets.QFormLayout(self.yolo_options)
        self.yolo_norm = QtWidgets.QCheckBox(self.tr("归一化坐标"), self)
        self.yolo_norm.setChecked(True)
        yolo_layout.addRow(self.yolo_norm)
        options_layout.addWidget(self.yolo_options)
        self.yolo_options.hide()

        # VOC选项
        self.voc_options = QtWidgets.QWidget(self)
        voc_layout = QtWidgets.QFormLayout(self.voc_options)
        self.voc_no_difficult = QtWidgets.QCheckBox(self.tr("将所有标记为非困难样本"), self)
        self.voc_no_difficult.setChecked(True)
        voc_layout.addRow(self.voc_no_difficult)
        options_layout.addWidget(self.voc_options)
        self.voc_options.hide()

        format_layout.addWidget(self.options_widget)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # 标签列表
        label_group = QtWidgets.QGroupBox(self.tr("标签列表 (将从 JSON 文件中自动检测)"))
        label_layout = QtWidgets.QVBoxLayout()
        self.label_list_widget = QtWidgets.QListWidget(self)
        self.label_list_widget.setMaximumHeight(100)
        label_layout.addWidget(self.label_list_widget)
        refresh_btn = QtWidgets.QPushButton(self.tr("刷新标签列表"), self)
        refresh_btn.clicked.connect(self._refresh_label_list)
        label_layout.addWidget(refresh_btn)
        label_group.setLayout(label_layout)
        layout.addWidget(label_group)

        # 进度显示
        progress_group = QtWidgets.QGroupBox(self.tr("进度"))
        progress_layout = QtWidgets.QVBoxLayout()
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        self.status_label = QtWidgets.QLabel(self.tr("就绪"), self)
        progress_layout.addWidget(self.status_label)
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # 按钮
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        self.convert_btn = QtWidgets.QPushButton(self.tr("转换"), self)
        self.convert_btn.setIcon(labelme.utils.newIcon("done"))
        self.convert_btn.clicked.connect(self._do_convert)
        self.convert_btn.setEnabled(False)
        btn_layout.addWidget(self.convert_btn)
        cancel_btn = QtWidgets.QPushButton(self.tr("取消"), self)
        cancel_btn.setIcon(labelme.utils.newIcon("undo"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # 如果输入目录已设置，自动刷新标签列表
        if self.input_dir:
            self._refresh_label_list()

    def _browse_input(self):
        """浏览输入目录"""
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            self.tr("选择输入目录"),
            self.input_dir or "."
        )
        if dir_path:
            self.input_dir = dir_path
            self.input_edit.setText(dir_path)
            self._refresh_label_list()
            self._update_convert_button()

    def _browse_output(self):
        """浏览输出目录"""
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            self.tr("选择输出目录"),
            self.output_dir or "."
        )
        if dir_path:
            self.output_dir = dir_path
            self.output_edit.setText(dir_path)
            self._update_convert_button()

    def _update_convert_button(self):
        """更新转换按钮状态"""
        enabled = bool(self.input_dir and self.output_dir and self.label_list)
        self.convert_btn.setEnabled(enabled)

    def _on_format_changed(self, index):
        """格式选择改变时更新选项显示"""
        format_key = self.format_combo.currentData()
        self.coco_options.setVisible(format_key == "coco")
        self.yolo_options.setVisible(format_key == "yolo")
        self.voc_options.setVisible(format_key == "voc")

    def _refresh_label_list(self):
        """从JSON文件中刷新标签列表"""
        if not self.input_dir or not osp.exists(self.input_dir):
            return

        self.label_list_widget.clear()
        self.label_list = []
        labels = set()

        try:
            for filename in os.listdir(self.input_dir):
                if not filename.endswith(".json"):
                    continue
                json_path = osp.join(self.input_dir, filename)
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for shape in data.get("shapes", []):
                            labels.add(shape.get("label", ""))
                except Exception as e:
                    logger.warning(f"Failed to parse {filename}: {e}")

            self.label_list = sorted(list(labels))
            self.label_list_widget.addItems(self.label_list)
            self.status_label.setText(self.tr(f"Found {len(self.label_list)} labels"))
            self._update_convert_button()
        except Exception as e:
            logger.error(f"Failed to refresh label list: {e}")
            self.status_label.setText(self.tr(f"Error: {e}"))

    def _do_convert(self):
        """执行转换"""
        format_key = self.format_combo.currentData()

        try:
            if format_key == "coco":
                self._convert_to_coco()
            elif format_key == "yolo":
                self._convert_to_yolo()
            elif format_key == "voc":
                self._convert_to_voc()

            QtWidgets.QMessageBox.information(
                self,
            self.tr("转换完成"),
            self.tr(f"成功转换为 {format_key.upper()} 格式!")
            )
            self.accept()
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            QtWidgets.QMessageBox.critical(
                self,
                self.tr("转换失败"),
                str(e)
            )

    def _convert_to_coco(self):
        """转换为COCO格式"""
        coco_data = {
            "info": {
                "description": self.coco_info_desc.text(),
                "version": "1.0",
                "year": datetime.now().year,
                "contributor": "Labelme",
                "date_created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "licenses": [{"id": 1, "name": "Unknown", "url": ""}],
            "images": [],
            "annotations": [],
            "categories": []
        }

        # 创建类别映射
        category_map = {}
        for idx, label in enumerate(self.label_list):
            if label:  # 跳过空标签
                category_map[label] = idx + 1
                coco_data["categories"].append({
                    "id": idx + 1,
                    "name": label,
                    "supercategory": ""
                })

        image_id = 0
        annotation_id = 0

        json_files = [f for f in os.listdir(self.input_dir) if f.endswith(".json")]
        total = len(json_files)

        for idx, filename in enumerate(json_files):
            json_path = osp.join(self.input_dir, filename)

            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                image_id += 1
                image_info = {
                    "id": image_id,
                    "file_name": data.get("imagePath", ""),
                    "height": data.get("imageHeight", 0),
                    "width": data.get("imageWidth", 0),
                    "license": 1
                }
                coco_data["images"].append(image_info)

                for shape in data.get("shapes", []):
                    label = shape.get("label", "")
                    if label not in category_map:
                        continue

                    points = shape.get("points", [])
                    if not points:
                        continue

                    annotation_id += 1
                    shape_type = shape.get("shape_type", "polygon")

                    # 计算bbox
                    if shape_type == "rectangle":
                        x1, y1 = points[0]
                        x2, y2 = points[1]
                        x = min(x1, x2)
                        y = min(y1, y2)
                        w = abs(x2 - x1)
                        h = abs(y2 - y1)
                    else:
                        xs = [p[0] for p in points]
                        ys = [p[1] for p in points]
                        x = min(xs)
                        y = min(ys)
                        w = max(xs) - x
                        h = max(ys) - y

                    # 计算面积
                    area = w * h

                    # 生成segmentation
                    if shape_type in ["polygon", "rectangle"]:
                        segmentation = []
                        for p in points:
                            segmentation.extend([float(p[0]), float(p[1])])
                        segmentation = [segmentation] if len(segmentation) >= 6 else []
                    else:
                        segmentation = []

                    annotation = {
                        "id": annotation_id,
                        "image_id": image_id,
                        "category_id": category_map[label],
                        "bbox": [float(x), float(y), float(w), float(h)],
                        "area": float(area),
                        "segmentation": segmentation,
                        "iscrowd": 0
                    }
                    coco_data["annotations"].append(annotation)

                # 更新进度
                progress = int((idx + 1) / total * 100)
                self.progress_bar.setValue(progress)
                QtWidgets.QApplication.processEvents()

            except Exception as e:
                logger.warning(f"Failed to process {filename}: {e}")

        # 保存COCO文件
        output_file = osp.join(self.output_dir, "annotations.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(coco_data, f, indent=2, ensure_ascii=False)

        logger.info(f"COCO format saved to {output_file}")
        self.status_label.setText(self.tr(f"Saved to {output_file}"))

    def _convert_to_yolo(self):
        """转换为YOLO格式"""
        # 创建输出目录结构
        images_dir = osp.join(self.output_dir, "images")
        labels_dir = osp.join(self.output_dir, "labels")
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(labels_dir, exist_ok=True)

        # 创建类别映射
        category_map = {}
        for idx, label in enumerate(self.label_list):
            if label:
                category_map[label] = idx

        # 保存类别文件
        with open(osp.join(self.output_dir, "classes.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(self.label_list))

        json_files = [f for f in os.listdir(self.input_dir) if f.endswith(".json")]
        total = len(json_files)
        normalize = self.yolo_norm.isChecked()

        for idx, filename in enumerate(json_files):
            json_path = osp.join(self.input_dir, filename)

            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                img_width = data.get("imageWidth", 1)
                img_height = data.get("imageHeight", 1)
                base_name = osp.splitext(filename)[0]

                yolo_lines = []
                for shape in data.get("shapes", []):
                    label = shape.get("label", "")
                    if label not in category_map:
                        continue

                    points = shape.get("points", [])
                    if not points:
                        continue

                    category_id = category_map[label]
                    shape_type = shape.get("shape_type", "polygon")

                    # 计算bbox中心点和宽高
                    if shape_type == "rectangle":
                        x1, y1 = points[0]
                        x2, y2 = points[1]
                        x = (x1 + x2) / 2
                        y = (y1 + y2) / 2
                        w = abs(x2 - x1)
                        h = abs(y2 - y1)
                    else:
                        xs = [p[0] for p in points]
                        ys = [p[1] for p in points]
                        x = (min(xs) + max(xs)) / 2
                        y = (min(ys) + max(ys)) / 2
                        w = max(xs) - min(xs)
                        h = max(ys) - min(ys)

                    # 归一化
                    if normalize:
                        x /= img_width
                        y /= img_height
                        w /= img_width
                        h /= img_height

                    yolo_lines.append(f"{category_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")

                # 保存YOLO标签文件
                label_file = osp.join(labels_dir, f"{base_name}.txt")
                with open(label_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(yolo_lines))

                # 更新进度
                progress = int((idx + 1) / total * 100)
                self.progress_bar.setValue(progress)
                QtWidgets.QApplication.processEvents()

            except Exception as e:
                logger.warning(f"Failed to process {filename}: {e}")

        self.status_label.setText(self.tr(f"YOLO format saved to {self.output_dir}"))

    def _convert_to_voc(self):
        """转换为Pascal VOC格式"""
        # 创建输出目录结构
        ann_dir = osp.join(self.output_dir, "Annotations")
        img_dir = osp.join(self.output_dir, "JPEGImages")
        sets_dir = osp.join(self.output_dir, "ImageSets", "Main")
        os.makedirs(ann_dir, exist_ok=True)
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(sets_dir, exist_ok=True)

        json_files = [f for f in os.listdir(self.input_dir) if f.endswith(".json")]
        total = len(json_files)
        image_names = []

        for idx, filename in enumerate(json_files):
            json_path = osp.join(self.input_dir, filename)

            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                img_width = data.get("imageWidth", 0)
                img_height = data.get("imageHeight", 0)
                img_path = data.get("imagePath", "")
                base_name = osp.splitext(osp.basename(img_path))[0]
                if not base_name:
                    base_name = osp.splitext(filename)[0]

                image_names.append(base_name)

                # 创建VOC XML
                xml_content = self._create_voc_xml(
                    base_name, img_path, img_width, img_height,
                    data.get("shapes", []), self.label_list
                )

                # 保存XML文件
                xml_file = osp.join(ann_dir, f"{base_name}.xml")
                with open(xml_file, "w", encoding="utf-8") as f:
                    f.write(xml_content)

                # 更新进度
                progress = int((idx + 1) / total * 100)
                self.progress_bar.setValue(progress)
                QtWidgets.QApplication.processEvents()

            except Exception as e:
                logger.warning(f"Failed to process {filename}: {e}")

        # 保存数据集划分文件
        trainval_file = osp.join(sets_dir, "trainval.txt")
        with open(trainval_file, "w", encoding="utf-8") as f:
            f.write("\n".join(image_names))

        self.status_label.setText(self.tr(f"VOC format saved to {self.output_dir}"))

    def _create_voc_xml(self, filename, img_path, width, height, shapes, label_list):
        """创建VOC格式的XML内容"""
        xml = [
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
            "<annotation>",
            f"  <filename>{osp.basename(img_path)}</filename>",
            "  <size>",
            f"    <width>{width}</width>",
            f"    <height>{height}</height>",
            "    <depth>3</depth>",
            "  </size>",
            "  <segmented>0</segmented>"
        ]

        for shape in shapes:
            label = shape.get("label", "")
            points = shape.get("points", [])
            if not points or label not in label_list:
                continue

            shape_type = shape.get("shape_type", "polygon")

            # 计算bbox
            if shape_type == "rectangle":
                x1, y1 = points[0]
                x2, y2 = points[1]
                xmin, xmax = sorted([x1, x2])
                ymin, ymax = sorted([y1, y2])
            else:
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                xmin, xmax = min(xs), max(xs)
                ymin, ymax = min(ys), max(ys)

            # 确保坐标有效
            xmin = max(0, int(xmin))
            ymin = max(0, int(ymin))
            xmax = min(width, int(xmax))
            ymax = min(height, int(ymax))

            xml.extend([
                "  <object>",
                f"    <name>{label}</name>",
                "    <pose>Unspecified</pose>",
                "    <truncated>0</truncated>",
                "    <difficult>0</difficult>" if self.voc_no_difficult.isChecked() else "    <difficult>0</difficult>",
                "    <bndbox>",
                f"      <xmin>{xmin}</xmin>",
                f"      <ymin>{ymin}</ymin>",
                f"      <xmax>{xmax}</xmax>",
                f"      <ymax>{ymax}</ymax>",
                "    </bndbox>",
                "  </object>"
            ])

        xml.append("</annotation>")
        return "\n".join(xml)
