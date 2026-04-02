#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练曲线实时显示组件

提供训练过程中损失和准确率的实时曲线显示
"""

import sys
from PyQt5 import QtCore, QtWidgets, QtGui
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib as mpl
import matplotlib.font_manager as fm


class TrainingCurveCanvas(FigureCanvas):
    """训练曲线画布组件"""
    point_selected = QtCore.pyqtSignal(str, float, float)
    
    def __init__(self, parent=None, title="", xlabel="轮次", ylabel=""):
        # 创建图形对象
        self.figure = Figure(figsize=(5, 3), dpi=100)
        self.axes = self.figure.add_subplot(111)
        
        super(TrainingCurveCanvas, self).__init__(self.figure)
        
        self.setParent(parent)
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        
        # 设置大小策略，使画布能够正确扩展
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setMinimumSize(200, 150)
        
        # 设置中文字体
        self._setup_chinese_font()
        
        # 数据存储
        self.epochs = []
        self.values = []
        self.line = None
        self.series = {}
        self._pick_tolerance = 8
        self._selected_annotation = None
        
        # 初始化图表
        self._init_plot()
        self.mpl_connect('button_press_event', self._on_click)
    
    def _setup_chinese_font(self):
        """设置中文字体"""
        try:
            import platform
            system = platform.system()

            # 安全地获取字体列表，避免字体缓存损坏导致崩溃
            try:
                font_names = {f.name for f in fm.fontManager.ttflist}
            except (AttributeError, KeyError, TypeError):
                # 字体管理器可能未初始化或损坏，使用默认字体
                font_names = set()

            if system == 'Windows':
                preferred = ['Microsoft YaHei', 'SimHei', 'SimSun']
            elif system == 'Darwin':
                preferred = ['PingFang SC', 'Arial Unicode MS', 'Heiti SC']
            else:
                preferred = ['WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'SimHei']

            available = [name for name in preferred if name in font_names]
            if available:
                mpl.rcParams['font.sans-serif'] = available
                mpl.rcParams['axes.unicode_minus'] = False
            else:
                # 如果没有找到中文字体，使用默认 sans-serif 字体
                mpl.rcParams['font.sans-serif'] = ['sans-serif']
                mpl.rcParams['axes.unicode_minus'] = False
        except Exception as e:
            # 字体设置失败不影响程序运行，使用默认设置
            try:
                mpl.rcParams['font.sans-serif'] = ['sans-serif']
                mpl.rcParams['axes.unicode_minus'] = False
            except Exception:
                pass  # 如果连默认设置都失败，静默忽略
    
    def _init_plot(self):
        """初始化图表"""
        self.axes.clear()
        self.axes.set_title(self.title, fontsize=10, fontweight='bold')
        self.axes.set_xlabel(self.xlabel, fontsize=9)
        self.axes.set_ylabel(self.ylabel, fontsize=9)
        self.axes.grid(True, alpha=0.3, linestyle='--')
        self.axes.set_xlim(left=0)
        
        if self.ylabel == "损失 (Loss)":
            self.axes.set_ylim(bottom=0)
        elif self.ylabel == "准确率 (Accuracy)":
            self.axes.set_ylim(bottom=0, top=1.05)
        
        self.figure.tight_layout()
    
    def update_data(self, epochs, values):
        """更新数据并重绘"""
        self.epochs = epochs
        self.values = values
        self.update_series("default", epochs, values, label=None)

    def update_series(self, series_key, epochs, values, label=None):
        """更新指定序列数据并重绘"""
        self.series[series_key] = {
            "epochs": list(epochs),
            "values": list(values),
            "label": label,
        }
        self._redraw()

    def _redraw(self):
        """重绘图表 - 增强边界条件检查"""
        try:
            self.axes.clear()
            self._selected_annotation = None

            max_value = None
            for series_key, data in self.series.items():
                epochs = data.get("epochs") or []
                values = data.get("values") or []
                if not epochs or not values:
                    continue
                label = data.get("label")
                line_label = label if label else None
                self.axes.plot(
                    epochs,
                    values,
                    linewidth=2,
                    marker='o',
                    markersize=2,
                    label=line_label,
                )
                # 安全地获取最后一个值
                if len(values) > 0:
                    current_value = values[-1]
                    if max_value is None or current_value > max_value:
                        max_value = current_value

            if max_value is not None:
                self.axes.set_title(f"{self.title} (当前：{max_value:.4f})", fontsize=9, fontweight='bold')
            else:
                self.axes.set_title(self.title, fontsize=10, fontweight='bold')

            self.axes.set_xlabel(self.xlabel, fontsize=9)
            self.axes.set_ylabel(self.ylabel, fontsize=9)
            self.axes.grid(True, alpha=0.3, linestyle='--')
            self.axes.set_xlim(left=0)

            if self.ylabel == "损失 (Loss)":
                self.axes.set_ylim(bottom=0)
            elif self.ylabel == "准确率 (Accuracy)":
                max_series_value = 1.05
                for data in self.series.values():
                    values = data.get("values") or []
                    if values:
                        max_series_value = max(max_series_value, max(values) * 1.05)
                self.axes.set_ylim(bottom=0, top=max_series_value)

            if any(data.get("label") for data in self.series.values()):
                self.axes.legend(loc="best", fontsize=7)

            self.figure.tight_layout()
            self.draw()
        except Exception as e:
            # 绘制失败时不崩溃，仅记录错误
            try:
                self.axes.clear()
                self.axes.set_title(f"{self.title} (绘制失败)", fontsize=10, fontweight='bold')
                self.axes.text(0.5, 0.5, "图表绘制失败", ha='center', va='center', transform=self.axes.transAxes)
                self.figure.tight_layout()
                self.draw()
            except Exception:
                pass  # 如果连错误显示都失败，静默忽略

    def _on_click(self, event):
        """处理点击事件 - 增强边界条件检查"""
        try:
            if event.inaxes != self.axes:
                if self._selected_annotation is not None:
                    self._selected_annotation.remove()
                    self._selected_annotation = None
                    self.draw_idle()
                return
            if event.x is None or event.y is None:
                return

            best = None
            best_dist = None
            for series_key, data in self.series.items():
                epochs = data.get("epochs") or []
                values = data.get("values") or []
                if not epochs or not values:
                    continue
                label = data.get("label") or series_key
                for epoch, value in zip(epochs, values):
                    try:
                        x, y = self.axes.transData.transform((epoch, value))
                        dist = (x - event.x) ** 2 + (y - event.y) ** 2
                        if best_dist is None or dist < best_dist:
                            best_dist = dist
                            best = (label, epoch, value)
                    except (ValueError, TypeError):
                        # 坐标转换失败，跳过该点
                        continue

            if best_dist is None or best is None:
                if self._selected_annotation is not None:
                    self._selected_annotation.remove()
                    self._selected_annotation = None
                    self.draw_idle()
                return
            if best_dist <= self._pick_tolerance ** 2:
                label, epoch, value = best
                if self._selected_annotation is not None:
                    self._selected_annotation.remove()
                    self._selected_annotation = None
                try:
                    self._selected_annotation = self.axes.annotate(
                        f"{label}\n{int(epoch)} : {value:.4f}",
                        xy=(epoch, value),
                        xytext=(8, 8),
                        textcoords="offset points",
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.4", alpha=0.9),
                        fontsize=8,
                    )
                    self.draw_idle()
                    self.point_selected.emit(label, float(epoch), float(value))
                except (ValueError, TypeError, OverflowError):
                    # 标注创建失败，静默忽略
                    if self._selected_annotation is not None:
                        self._selected_annotation.remove()
                        self._selected_annotation = None
                    self.draw_idle()
            else:
                if self._selected_annotation is not None:
                    self._selected_annotation.remove()
                    self._selected_annotation = None
                    self.draw_idle()
        except Exception as e:
            # 点击处理失败，静默忽略
            pass
    
    def clear_data(self):
        """清除数据"""
        self.epochs = []
        self.values = []
        self.series = {}
        self._init_plot()
        self.draw()


class TrainingCurveDock(QtWidgets.QDockWidget):
    """训练曲线 Dock 窗口"""
    
    def __init__(self, title, parent=None, curve_type='loss'):
        """
        初始化训练曲线 Dock
        
        Args:
            title: Dock 标题
            parent: 父窗口
            curve_type: 曲线类型 ('loss' 或 'accuracy')
        """
        super(TrainingCurveDock, self).__init__(title, parent)
        self.setObjectName(f"{curve_type.title()}CurveDock")
        
        self.curve_type = curve_type
        
        # 创建画布组件
        ylabel = "损失 (Loss)" if curve_type == 'loss' else "准确率 (Accuracy)"
        self.canvas = TrainingCurveCanvas(self, title=title, xlabel="轮次 (Epoch)", ylabel=ylabel)
        self.info_label = QtWidgets.QLabel("Click a point to view value")
        self.info_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.info_label.setStyleSheet("padding: 4px;")
        self.canvas.point_selected.connect(self._on_point_selected)

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.info_label, 0)
        container.setLayout(layout)
        
        # 设置 dock 内容
        self.setWidget(container)
        
        # 设置最小尺寸
        self.setMinimumSize(250, 200)
        
        # 设置 dock 特性：可移动、可浮动，但不可关闭
        features = QtWidgets.QDockWidget.DockWidgetFloatable | QtWidgets.QDockWidget.DockWidgetMovable
        self.setFeatures(features)
    
    def update_curve(self, epochs, values):
        """更新曲线数据"""
        self.canvas.update_data(epochs, values)

    def update_task_curve(self, task_id, epochs, values, label=None):
        """更新指定任务曲线数据"""
        self.canvas.update_series(task_id, epochs, values, label=label)

    def _on_point_selected(self, label, epoch, value):
        self.info_label.setText(f"{label} | epoch: {int(epoch)} | value: {value:.4f}")
    
    def clear_curve(self):
        """清除曲线"""
        self.canvas.clear_data()


class RealtimeTrainingCurvesWidget(QtWidgets.QWidget):
    """实时训练曲线组件（包含两个曲线）"""
    
    def __init__(self, parent=None):
        super(RealtimeTrainingCurvesWidget, self).__init__(parent)
        
        # 创建主布局
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 创建损失曲线画布
        self.loss_canvas = TrainingCurveCanvas(
            self, 
            title="训练损失", 
            xlabel="轮次 (Epoch)", 
            ylabel="损失 (Loss)"
        )
        
        # 创建准确率曲线画布
        self.acc_canvas = TrainingCurveCanvas(
            self, 
            title="训练准确率", 
            xlabel="轮次 (Epoch)", 
            ylabel="准确率 (Accuracy)"
        )
        
        # 添加到布局
        layout.addWidget(self.loss_canvas)
        layout.addWidget(self.acc_canvas)
        
        self.setLayout(layout)
    
    def update_curves(self, epochs, losses, accuracies):
        """更新两条曲线"""
        self.loss_canvas.update_data(epochs, losses)
        self.acc_canvas.update_data(epochs, accuracies)
    
    def clear_curves(self):
        """清除所有曲线"""
        self.loss_canvas.clear_data()
        self.acc_canvas.clear_data()


if __name__ == '__main__':
    # 测试代码
    app = QtWidgets.QApplication(sys.argv)
    
    # 创建测试窗口
    window = QtWidgets.QMainWindow()
    window.setWindowTitle("训练曲线测试")
    window.resize(800, 600)
    
    # 创建中心 widget
    central_widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout()
    
    # 创建两个 dock
    loss_dock = TrainingCurveDock("损失曲线", window, curve_type='loss')
    acc_dock = TrainingCurveDock("准确率曲线", window, curve_type='accuracy')
    
    # 添加 dock 到窗口
    window.addDockWidget(QtCore.LeftDockWidgetArea, loss_dock)
    window.addDockWidget(QtCore.RightDockWidgetArea, acc_dock)
    
    # 模拟数据更新
    import time
    
    def update_data():
        epochs = list(range(0, 100, 5))
        losses = [5.0 * (0.95 ** i) for i in epochs]
        accuracies = [0.2 + 0.75 * (1 - 0.95 ** i) for i in epochs]
        
        loss_dock.update_curve(epochs, losses)
        acc_dock.update_curve(epochs, accuracies)
    
    # 定时器模拟实时更新
    timer = QtCore.QTimer()
    timer.timeout.connect(update_data)
    timer.start(500)
    
    window.setCentralWidget(central_widget)
    window.show()
    
    sys.exit(app.exec_())
