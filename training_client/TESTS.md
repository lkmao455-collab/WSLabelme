# Training Client 单元测试

## 运行测试

### 方式 1: 使用测试脚本（推荐）

```bash
# 运行所有测试
python run_tests.py

# 详细输出
python run_tests.py -v

# 安静模式
python run_tests.py -q

# 运行指定测试类
python run_tests.py -t TestMessageProtocol -v

# 运行指定测试方法
python run_tests.py -t test_pack_structure -v
```

### 方式 2: 使用 unittest 模块

```bash
# 运行所有测试
python -m unittest test_training_client -v

# 运行指定测试类
python -m unittest test_training_client.TestMessageProtocol -v

# 运行指定测试方法
python -m unittest test_training_client.TestMessageProtocol.test_pack_structure -v
```

## 测试覆盖

| 类 | 测试用例数 | 说明 |
|----|-----------|------|
| MessageProtocol | 8 | 消息协议打包/解包 |
| MessageProtocolReceive | 3 | 消息接收功能 |
| MessageProtocolEdgeCases | 3 | 边界情况测试 |
| TrainingClient | 16 | 训练客户端功能 |
| InteractiveClient | 2 | 交互式客户端 |
| **总计** | **32** | |

## 测试说明

### MessageProtocol 测试
- `test_calculate_checksum_*` - 校验和计算
- `test_pack_*` - 消息打包功能
- `test_receive_*` - 消息接收功能

### TrainingClient 测试
- `test_init` - 初始化
- `test_connect_*` - 连接功能
- `test_disconnect` - 断开连接
- `test_send_request_*` - 发送请求
- `test_ping_*` - 心跳测试
- `test_create_task_*` - 创建任务
- `test_start/stop_training_*` - 启动/停止训练
- `test_get_task_status_*` - 获取状态
- `test_get_progress_*` - 获取进度
- `test_list_tasks_*` - 列出任务
- `test_delete_task_*` - 删除任务

### InteractiveClient 测试
- `test_init` - 初始化
- `test_run_connect_failure` - 连接失败处理
