#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练可视化模块

本模块提供训练过程的可视化功能，使用 matplotlib 绘制损失和准确率曲线。
支持多任务对比显示。
"""

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from collections import defaultdict
import numpy as np


class TrainingVisualizer:
    """
    训练可视化器
    
    用于绘制训练过程中的损失和准确率曲线，支持多任务对比。
    
    Attributes:
        font_path (str): 中文字体路径，用于正常显示中文标签
        tasks_data (dict): 存储多个任务的数据
    """
    
    def __init__(self, font_path=None):
        """
        初始化可视化器
        
        Args:
            font_path (str, optional): 中文字体文件路径。如果为 None，将尝试使用系统默认中文字体
        """
        self.tasks_data = defaultdict(lambda: {
            'epochs': [],
            'losses': [],
            'accuracies': []
        })
        
        # 设置中文字体
        self._setup_chinese_font(font_path)
    
    def _setup_chinese_font(self, font_path=None):
        """
        设置中文字体，确保图表能正常显示中文
        
        Args:
            font_path (str, optional): 字体文件路径
        """
        try:
            if font_path:
                # 使用指定的字体文件
                font_prop = fm.FontProperties(fname=font_path)
                plt.rcParams['font.sans-serif'] = [font_prop.get_name()]
            else:
                # 尝试使用系统默认中文字体
                # Windows 系统通常有中文字体
                import platform
                system = platform.system()
                
                if system == 'Windows':
                    # Windows 系统中文字体
                    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
                elif system == 'Darwin':
                    # macOS 系统中文字体
                    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC', 'PingFang SC']
                else:
                    # Linux 系统，尝试使用常见中文字体
                    plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'SimHei']
            
            # 确保负号能正常显示
            plt.rcParams['axes.unicode_minus'] = False
            
        except Exception as e:
            print(f"警告：设置中文字体失败：{e}")
            print("图表中的中文可能无法正常显示")
    
    def add_task_data(self, task_name, epochs, losses, accuracies):
        """
        添加任务数据
        
        Args:
            task_name (str): 任务名称
            epochs (list): 轮次列表
            losses (list): 损失值列表
            accuracies (list): 准确率列表
        """
        self.tasks_data[task_name]['epochs'] = epochs
        self.tasks_data[task_name]['losses'] = losses
        self.tasks_data[task_name]['accuracies'] = accuracies
    
    def plot_loss_curves(self, save_path=None, show=True, figsize=(12, 6)):
        """
        绘制损失曲线图
        
        Args:
            save_path (str, optional): 保存路径。如果为 None，则不保存
            show (bool): 是否显示图表
            figsize (tuple): 图表大小 (宽，高)
        
        Returns:
            fig: matplotlib 图形对象
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(self.tasks_data)))
        
        for idx, (task_name, data) in enumerate(self.tasks_data.items()):
            if data['epochs'] and data['losses']:
                ax.plot(data['epochs'], data['losses'], 
                       label=task_name, 
                       color=colors[idx],
                       linewidth=2,
                       marker='o',
                       markersize=3)
        
        ax.set_xlabel('轮次 (Epoch)', fontsize=12)
        ax.set_ylabel('损失 (Loss)', fontsize=12)
        ax.set_title('训练损失曲线', fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim(left=0)
        
        # 优化布局
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"损失曲线图已保存到：{save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def plot_accuracy_curves(self, save_path=None, show=True, figsize=(12, 6)):
        """
        绘制准确率曲线图
        
        Args:
            save_path (str, optional): 保存路径。如果为 None，则不保存
            show (bool): 是否显示图表
            figsize (tuple): 图表大小 (宽，高)
        
        Returns:
            fig: matplotlib 图形对象
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(self.tasks_data)))
        
        for idx, (task_name, data) in enumerate(self.tasks_data.items()):
            if data['epochs'] and data['accuracies']:
                ax.plot(data['epochs'], data['accuracies'], 
                       label=task_name, 
                       color=colors[idx],
                       linewidth=2,
                       marker='s',
                       markersize=3)
        
        ax.set_xlabel('轮次 (Epoch)', fontsize=12)
        ax.set_ylabel('准确率 (Accuracy)', fontsize=12)
        ax.set_title('训练准确率曲线', fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0, top=1.05)  # 准确率通常在 0-1 之间
        
        # 优化布局
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"准确率曲线图已保存到：{save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def plot_both_curves(self, save_path=None, show=True, figsize=(14, 6)):
        """
        并排绘制损失和准确率曲线图
        
        Args:
            save_path (str, optional): 保存路径。如果为 None，则不保存
            show (bool): 是否显示图表
            figsize (tuple): 每个子图的大小
        
        Returns:
            fig: matplotlib 图形对象
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(self.tasks_data)))
        
        # 绘制损失曲线
        for idx, (task_name, data) in enumerate(self.tasks_data.items()):
            if data['epochs'] and data['losses']:
                ax1.plot(data['epochs'], data['losses'], 
                        label=task_name, 
                        color=colors[idx],
                        linewidth=2,
                        marker='o',
                        markersize=3)
        
        ax1.set_xlabel('轮次 (Epoch)', fontsize=11)
        ax1.set_ylabel('损失 (Loss)', fontsize=11)
        ax1.set_title('训练损失曲线', fontsize=13, fontweight='bold')
        ax1.legend(loc='best', fontsize=9)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.set_xlim(left=0)
        
        # 绘制准确率曲线
        for idx, (task_name, data) in enumerate(self.tasks_data.items()):
            if data['epochs'] and data['accuracies']:
                ax2.plot(data['epochs'], data['accuracies'], 
                        label=task_name, 
                        color=colors[idx],
                        linewidth=2,
                        marker='s',
                        markersize=3)
        
        ax2.set_xlabel('轮次 (Epoch)', fontsize=11)
        ax2.set_ylabel('准确率 (Accuracy)', fontsize=11)
        ax2.set_title('训练准确率曲线', fontsize=13, fontweight='bold')
        ax2.legend(loc='best', fontsize=9)
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.set_xlim(left=0)
        ax2.set_ylim(bottom=0, top=1.05)
        
        # 优化布局
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"训练曲线图已保存到：{save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def clear_data(self):
        """清除所有任务数据"""
        self.tasks_data.clear()


# 使用示例
if __name__ == '__main__':
    # 创建可视化器
    visualizer = TrainingVisualizer()
    
    # 添加示例数据
    task1_epochs = list(range(0, 3500, 100))
    task1_losses = [9.0 * (0.99 ** i) for i in task1_epochs]
    task1_accuracies = [0.1 + 0.85 * (1 - 0.995 ** i) for i in task1_epochs]
    
    task2_epochs = list(range(0, 3500, 100))
    task2_losses = [8.0 * (0.99 ** i) for i in task2_epochs]
    task2_accuracies = [0.15 + 0.80 * (1 - 0.995 ** i) for i in task2_epochs]
    
    # 添加任务数据
    visualizer.add_task_data('任务 1', task1_epochs, task1_losses, task1_accuracies)
    visualizer.add_task_data('任务 2', task2_epochs, task2_losses, task2_accuracies)
    
    # 绘制并排图表
    visualizer.plot_both_curves()
