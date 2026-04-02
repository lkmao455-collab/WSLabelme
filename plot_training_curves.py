#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练曲线绘制示例

本示例展示如何从训练客户端获取数据并绘制损失和准确率曲线
"""

import sys
import os
from training_visualization import TrainingVisualizer

# 示例 1: 使用模拟数据
def example_with_simulated_data():
    """使用模拟数据演示"""
    print("=" * 60)
    print("示例 1: 使用模拟数据")
    print("=" * 60)
    
    # 创建可视化器
    visualizer = TrainingVisualizer()
    
    # 模拟多个任务的训练数据
    tasks = [
        ('任务 1 - 目标检测', 5000, 0.98, 0.002),
        ('任务 2 - 分类', 5000, 0.95, 0.0015),
        ('任务 3 - 分割', 5000, 0.92, 0.001),
    ]
    
    for task_name, max_epochs, final_loss, loss_decay in tasks:
        epochs = list(range(max_epochs))
        # 模拟损失递减
        losses = [final_loss + (9.0 - final_loss) * (1 - loss_decay) ** i for i in epochs]
        # 模拟准确率递增
        accuracies = [0.1 + (final_loss - 0.1) * (1 - (1 - loss_decay/2) ** i) for i in epochs]
        
        # 每隔一定轮次采样一次，减少数据点
        sample_rate = 100
        sampled_epochs = epochs[::sample_rate]
        sampled_losses = losses[::sample_rate]
        sampled_accuracies = accuracies[::sample_rate]
        
        visualizer.add_task_data(task_name, sampled_epochs, sampled_losses, sampled_accuracies)
    
    # 绘制并排图表
    visualizer.plot_both_curves(save_path='training_curves_simulated.png')
    
    print("图表已保存：training_curves_simulated.png")
    print()


# 示例 2: 从训练客户端获取数据（需要实际运行训练任务）
def example_with_training_client():
    """使用训练客户端实际数据演示"""
    print("=" * 60)
    print("示例 2: 使用训练客户端实际数据")
    print("=" * 60)
    
    try:
        from training_client.training_client import TrainingClient
        
        # 创建客户端
        client = TrainingClient()
        
        # 获取所有任务
        tasks = client.get_all_tasks()
        
        if not tasks:
            print("没有找到训练任务")
            return
        
        print(f"找到 {len(tasks)} 个任务")
        
        # 创建可视化器
        visualizer = TrainingVisualizer()
        
        # 为每个任务收集数据
        for task in tasks:
            task_id = task.get('id')
            task_name = task.get('name', f'Task {task_id}')
            
            # 获取训练进度
            progress = client.get_progress(task_id)
            
            if progress and 'progress' in progress:
                p = progress['progress']
                
                # 提取数据
                epochs = p.get('epoch', [])
                losses = p.get('loss', [])
                accuracies = p.get('accuracy', [])
                
                # 如果是单个值，转换为列表
                if isinstance(epochs, (int, float)):
                    epochs = [epochs]
                    losses = [losses] if isinstance(losses, (int, float)) else []
                    accuracies = [accuracies] if isinstance(accuracies, (int, float)) else []
                
                if epochs:
                    visualizer.add_task_data(task_name, epochs, losses, accuracies)
                    print(f"添加了任务数据：{task_name}")
        
        # 绘制图表
        if visualizer.tasks_data:
            visualizer.plot_both_curves(save_path='training_curves_real.png')
            print("图表已保存：training_curves_real.png")
        else:
            print("没有可用的训练数据")
            
    except Exception as e:
        print(f"使用训练客户端时出错：{e}")
        print("请确保训练客户端已正确配置并且有训练任务")


# 示例 3: 从日志文件解析数据
def example_from_log_file(log_file_path):
    """从训练日志文件解析数据"""
    print("=" * 60)
    print("示例 3: 从日志文件解析数据")
    print("=" * 60)
    
    import re
    
    visualizer = TrainingVisualizer()
    
    # 用于存储解析的数据
    current_task = '默认任务'
    epochs_data = []
    losses_data = []
    accuracies_data = []
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # 匹配训练日志格式，例如：
                # "Epoch 1/100 - Loss: 2.345 - Accuracy: 0.567"
                # "[INFO] Epoch 1, Loss: 2.345, Accuracy: 0.567"
                
                # 匹配轮次、损失、准确率
                match = re.search(r'Epoch[:\s]*(\d+).*?Loss[:\s]*([\d.]+).*?Accuracy[:\s]*([\d.]+)', line, re.IGNORECASE)
                
                if match:
                    epoch = int(match.group(1))
                    loss = float(match.group(2))
                    accuracy = float(match.group(3))
                    
                    epochs_data.append(epoch)
                    losses_data.append(loss)
                    accuracies_data.append(accuracy)
        
        if epochs_data:
            visualizer.add_task_data(current_task, epochs_data, losses_data, accuracies_data)
            visualizer.plot_both_curves(save_path='training_curves_from_log.png')
            print("图表已保存：training_curves_from_log.png")
        else:
            print("日志文件中没有找到训练数据")
            
    except FileNotFoundError:
        print(f"日志文件不存在：{log_file_path}")
    except Exception as e:
        print(f"解析日志文件时出错：{e}")


if __name__ == '__main__':
    # 运行示例 1（模拟数据）
    example_with_simulated_data()
    
    # 运行示例 2（需要实际的训练客户端）
    # example_with_training_client()
    
    # 运行示例 3（需要提供日志文件路径）
    # example_from_log_file('path/to/your/training.log')
    
    print("=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)
