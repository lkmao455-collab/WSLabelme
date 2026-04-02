#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI图像标注与训练系统测试脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ui_components():
    """测试UI组件"""
    try:
        # 测试导入
        from main import AIAnnotationMainWindow
        from model_training import ModelTrainer
        from model_usage import ModelUsageManager
        
        print("✓ 所有模块导入成功")
        
        # 测试模型训练器
        trainer = ModelTrainer()
        assert hasattr(trainer, 'start_training')
        assert hasattr(trainer, 'stop_training')
        assert hasattr(trainer, 'is_training')
        print("✓ 模型训练器功能正常")
        
        # 测试模型使用管理器
        usage_manager = ModelUsageManager()
        assert hasattr(usage_manager, 'download_to_camera')
        assert hasattr(usage_manager, 'download_to_local')
        assert hasattr(usage_manager, 'get_current_model_info')
        print("✓ 模型使用管理器功能正常")
        
        # 测试配置文件
        from labelme.config import get_config
        config = get_config()
        assert 'shortcuts' in config
        assert 'redo' in config['shortcuts']
        print("✓ 配置文件包含redo快捷键")
        
        print("\n所有测试通过！新UI界面已准备就绪。")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_ui_components()
    sys.exit(0 if success else 1)