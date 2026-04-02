#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试训练服务器连接"""

import sys
sys.path.insert(0, r'e:\shangweiji\WSLabelme\labelme')
from training_client.training_client import TrainingClient

print("=" * 50)
print("测试训练服务器连接")
print("=" * 50)

client = TrainingClient('127.0.0.1', 8888)

print("\n1. 连接服务器...")
connected = client.connect()
print(f"   结果: {connected}")

if connected:
    print("\n2. 测试 ping (3秒超时)...")
    ping_result = client.ping(timeout=3)
    print(f"   结果: {ping_result}")
    
    if not ping_result:
        print("\n3. 尝试直接创建任务...")
        params = {'model_type': 'detect', 'epochs': 1, 'batch_size': 8}
        task_id = client.create_task(params)
        print(f"   结果: {task_id}")
    
    print("\n4. 断开连接...")
    client.disconnect()
    print("   完成")

print("\n" + "=" * 50)
print("测试结束")
print("=" * 50)
