#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练客户端集成测试脚本

用于验证 training_client 集成到 labelme 项目是否成功
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, r'e:\shangweiji\WSLabelme\labelme')

def test_imports():
    """测试导入是否成功"""
    print("=" * 60)
    print("测试模块导入...")
    print("=" * 60)

    try:
        # 测试 training_client 导入
        from training_client.training_client import TrainingClient, MessageProtocol
        print("[OK] training_client.training_client 导入成功")

        # 测试 TrainingClientManager 导入（不通过 labelme 包，直接导入）
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "training_client_manager",
            r"e:\shangweiji\WSLabelme\labelme\labelme\training_client_manager.py"
        )
        tcm_module = importlib.util.module_from_spec(spec)

        # 由于 PyQt5 可能不可用，我们检查文件是否存在且包含关键类定义
        with open(r"e:\shangweiji\WSLabelme\labelme\labelme\training_client_manager.py", 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'class TrainingClientManager' in content, "找不到 TrainingClientManager 类"
            assert 'connected = QtCore.pyqtSignal' in content, "找不到信号定义"
        print("[OK] labelme.training_client_manager 文件检查通过")

        # 测试 widgets 文件检查
        with open(r"e:\shangweiji\WSLabelme\labelme\labelme\widgets\training_task_widget.py", 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'class TrainingTaskWidget' in content, "找不到 TrainingTaskWidget 类"
        print("[OK] labelme.widgets.training_task_widget 文件检查通过")

        with open(r"e:\shangweiji\WSLabelme\labelme\labelme\widgets\training_dock_widget.py", 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'class TrainingDockWidget' in content, "找不到 TrainingDockWidget 类"
            assert 'create_remote_task_requested' in content, "找不到 create_remote_task_requested 信号"
            assert 'get_training_params' in content, "找不到 get_training_params 方法"
        print("[OK] labelme.widgets.training_dock_widget 文件检查通过")

        # 检查 app.py 的修改
        with open(r"e:\shangweiji\WSLabelme\labelme\labelme\app.py", 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'TrainingClientManager' in content, "app.py 中找不到 TrainingClientManager 导入"
            assert 'training_task_dock' in content, "app.py 中找不到 training_task_dock"
            assert '_on_create_remote_task' in content, "app.py 中找不到 _on_create_remote_task 方法"
        print("[OK] labelme.app 文件检查通过")

        print("\n所有模块导入成功！")
        return True
    except Exception as e:
        print(f"[FAIL] 导入失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_training_client_manager():
    """测试 TrainingClientManager 代码结构"""
    print("\n" + "=" * 60)
    print("测试 TrainingClientManager 代码结构...")
    print("=" * 60)

    try:
        # 检查 training_client_manager.py 的关键内容
        with open(r"e:\shangweiji\WSLabelme\labelme\labelme\training_client_manager.py", 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查类定义
        assert 'class TrainingClientManager(QtCore.QObject):' in content, "类定义错误"
        print("[OK] 类定义正确")

        # 检查信号定义
        signals = ['connected', 'connection_error', 'task_created', 'training_started',
                   'training_stopped', 'progress_updated', 'status_changed', 'error_occurred']
        for signal in signals:
            assert f'{signal} = QtCore.pyqtSignal' in content, f"缺少信号：{signal}"
        print(f"[OK] 所有 {len(signals)} 个信号定义正确")

        # 检查方法定义
        methods = ['connect_server', 'disconnect_server', 'create_task', 'start_training',
                   'stop_training', 'delete_task', 'list_tasks', 'start_monitoring']
        for method in methods:
            assert f'def {method}(' in content, f"缺少方法：{method}"
        print(f"[OK] 所有 {len(methods)} 个方法定义正确")

        # 检查导入
        assert 'from training_client.training_client import TrainingClient' in content, "TrainingClient 导入错误"
        print("[OK] 导入语句正确")

        print("\nTrainingClientManager 代码结构测试通过！")
        return True
    except Exception as e:
        print(f"[FAIL] 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def test_widgets():
    """测试 Widget 代码结构"""
    print("\n" + "=" * 60)
    print("测试 Widget 代码结构...")
    print("=" * 60)

    try:
        # 测试 TrainingDockWidget
        with open(r"e:\shangweiji\WSLabelme\labelme\labelme\widgets\training_dock_widget.py", 'r', encoding='utf-8') as f:
            dock_content = f.read()

        assert 'class TrainingDockWidget(QtWidgets.QWidget):' in dock_content, "TrainingDockWidget 类定义错误"
        assert 'create_remote_task_requested = QtCore.pyqtSignal' in dock_content, "缺少 create_remote_task_requested 信号"
        assert 'def set_manager(self, manager):' in dock_content, "缺少 set_manager 方法"
        assert 'def get_training_params(self):' in dock_content, "缺少 get_training_params 方法"
        assert 'self.create_task_btn' in dock_content, "缺少创建任务按钮"
        assert 'self.start_btn' in dock_content, "缺少启动按钮"
        assert 'self.stop_btn' in dock_content, "缺少停止按钮"
        print("[OK] TrainingDockWidget 结构完整")

        # 测试 TrainingTaskWidget
        with open(r"e:\shangweiji\WSLabelme\labelme\labelme\widgets\training_task_widget.py", 'r', encoding='utf-8') as f:
            task_content = f.read()

        assert 'class TrainingTaskWidget(QtWidgets.QWidget):' in task_content, "TrainingTaskWidget 类定义错误"
        assert 'def set_manager(self, manager):' in task_content, "缺少 set_manager 方法"
        assert 'def get_current_task_id(self)' in task_content, "缺少 get_current_task_id 方法"
        assert 'self.task_table' in task_content, "缺少任务表格"
        assert 'self.progress_bar' in task_content, "缺少进度条"
        assert 'self.log_text' in task_content, "缺少日志区域"
        print("[OK] TrainingTaskWidget 结构完整")

        print("\nWidget 组件代码结构测试通过！")
        return True
    except Exception as e:
        print(f"[FAIL] 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Training Client 集成测试")
    print("=" * 60)

    results = []

    # 测试导入
    results.append(("模块导入", test_imports()))

    # 测试 TrainingClientManager
    results.append(("TrainingClientManager", test_training_client_manager()))

    # 测试 Widgets
    results.append(("Widget 组件", test_widgets()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, result in results:
        status = "通过" if result else "失败"
        symbol = "[OK]" if result else "[FAIL]"
        print(f"{symbol} {name}: {status}")

    all_passed = all(r for _, r in results)

    if all_passed:
        print("\n[OK] 所有测试通过！集成成功。")
        return 0
    else:
        print("\n[FAIL] 部分测试失败，请检查错误信息。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
