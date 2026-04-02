# 训练客户端完全指南

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `training_client.py` | 主程序（消息协议、训练客户端、交互式界面） |
| `test_training_client.py` | 单元测试（32 个测试用例） |
| `run_tests.py` | 测试运行脚本 |
| `run_tests_report.py` | 生成测试报告的脚本 |
| `generate_ppt.py` | PPT 生成脚本 |
| `training_flowchart.html` | 详细流程图（HTML） |
| `训练客户端技术详解.pptx` | 培训 PPT |

---

## 🚀 快速开始

### 1. 运行交互式客户端

```bash
python training_client.py
```

### 2. 运行测试

```bash
# 运行所有测试
python run_tests.py -v

# 生成测试报告
python run_tests_report.py
```

### 3. 查看流程图

在浏览器中打开 `training_flowchart.html`

---

## 📊 系统架构

```
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ TrainingClient   │ ───► │  TCP/IP 网络      │ ───► │ TrainingServer   │
│ (客户端)         │      │ 127.0.0.1:8888   │      │ (训练服务器)     │
└──────────────────┘      └──────────────────┘      └──────────────────┘
         ▲
         │ 封装
         │
┌──────────────────┐
│ InteractiveClient│
│ (交互式界面)     │
└──────────────────┘
```

---

## 🔄 完整工作流程

```
1. 创建客户端 ──► 2. 连接服务器 ──► 3. 验证连接
                                            │
                                            ▼
6. 断开连接 ◄── 5. 监控进度 ◄── 4. 创建并启动任务
```

### 详细步骤

| 步骤 | 方法 | 说明 |
|------|------|------|
| 1 | `TrainingClient()` | 实例化客户端 |
| 2 | `connect()` | 建立 TCP 连接 |
| 3 | `ping()` | 验证服务器响应 |
| 4 | `create_task(params)` | 创建训练任务 |
| 5 | `start_training(task_id)` | 启动训练 |
| 6 | `monitor_training(task_id)` | 监控进度 |
| 7 | `disconnect()` | 断开连接 |

---

## 📨 消息协议

### 数据结构

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│  包头 (4B)  │  长度 (4B)  │ 校验和 (4B) │  数据 (NB)  │
│ 0x55AA55AA  │  数据字节数  │  完整性验证  │  JSON 字符串 │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

### 协议详解

1. **包头 (Header)**: 固定值 `0x55AA55AA`，大端序 4 字节
   - 用于识别消息起始位置
   - 接收方通过此值判断消息边界

2. **长度 (Length)**: 数据部分的字节数，大端序 4 字节
   - 用于确定需要读取的字节数

3. **校验和 (Checksum)**: 数据部分所有字节累加和的低 32 位
   - 计算方法：`checksum = (sum(bytes)) & 0xFFFFFFFF`
   - 用于验证数据完整性

4. **数据 (Data)**: UTF-8 编码的 JSON 字符串
   - 包含命令类型、请求 ID、参数等

---

## 📦 MessageProtocol 类

### 方法说明

#### calculate_checksum(data)
```python
计算数据的校验和

参数：
    data: bytes - 要计算校验和的数据

返回：
    int - 32 位校验和
```

#### pack(message)
```python
将消息打包成协议格式

参数：
    message: str - JSON 字符串

返回：
    bytes - 打包后的二进制数据
```

#### receive(conn, timeout)
```python
从 Socket 连接接收并解析消息

参数：
    conn: socket.socket - Socket 连接
    timeout: float - 超时时间（秒）

返回：
    str | None - 解析后的消息，失败返回 None
```

---

## 🛠️ TrainingClient 类

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `host` | str | 服务器地址（默认：127.0.0.1） |
| `port` | int | 服务器端口（默认：8888） |
| `socket` | socket | TCP Socket 对象 |
| `connected` | bool | 连接状态 |
| `request_counter` | int | 请求计数器 |

### 核心方法

#### 连接类

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `connect()` | 无 | bool | 连接到服务器 |
| `disconnect()` | 无 | None | 断开连接 |
| `ping()` | 无 | bool | 测试连接 |
| `send_request()` | command, data | dict | 发送请求 |

#### 任务管理类

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `create_task()` | params: dict | task_id | 创建任务 |
| `start_training()` | task_id: str | bool | 启动训练 |
| `stop_training()` | task_id: str | bool | 停止训练 |
| `get_task_status()` | task_id: str | dict | 获取状态 |
| `delete_task()` | task_id: str | bool | 删除任务 |

#### 监控类

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `get_progress()` | task_id: str | dict | 获取进度 |
| `long_poll_progress()` | task_id, timeout | dict | 长轮询 |
| `list_tasks()` | 无 | dict | 列出任务 |
| `monitor_training()` | task_id, interval | None | 监控训练 |

---

## 📋 create_task 参数详解

| 参数 | 类型 | 默认值 | 说明 | 建议 |
|------|------|--------|------|------|
| `model_type` | str | "detect" | 模型类型 | detect/segment/classify |
| `image_size` | int | 640 | 图像尺寸 | 320-1280 |
| `dataset` | str | "data" | 数据集路径 | 确保路径存在 |
| `epochs` | int | 50 | 训练轮次 | 30-100 |
| `batch_size` | int | 32 | 批次大小 | 16/32/64 |
| `learning_rate` | float | 0.001 | 学习率 | 0.001-0.01 |
| `trainset_ratio` | float | 0.9 | 训练集占比 | 0.8-0.95 |

### 参数影响

**epochs（训练轮次）**
- 太少：模型欠拟合
- 太多：可能过拟合，训练时间长
- 建议：根据数据集大小调整

**batch_size（批次大小）**
- 太小：训练不稳定
- 太大：内存需求高
- 建议：根据 GPU 显存调整

**learning_rate（学习率）**
- 太小：收敛慢
- 太大：可能不收敛
- 建议：使用学习率衰减

---

## 💻 代码示例

### 基础用法

```python
from training_client import TrainingClient
import time

# 1. 创建客户端
client = TrainingClient(host="127.0.0.1", port=8888)

# 2. 连接
if not client.connect():
    print("连接失败")
    exit()

# 3. 验证
if not client.ping():
    print("服务器无响应")
    client.disconnect()
    exit()

# 4. 创建任务
params = {
    "model_type": "detect",
    "epochs": 50,
    "batch_size": 32
}
task_id = client.create_task(params)

# 5. 启动训练
client.start_training(task_id)

# 6. 监控进度
while True:
    progress = client.get_progress(task_id)
    if progress:
        p = progress.get("progress", {})
        epoch = p.get("epoch", 0)
        total = p.get("total_epochs", 1)
        print(f"进度：{epoch}/{total}")
        if epoch >= total:
            break
    time.sleep(2)

# 7. 断开
client.disconnect()
```

### 带错误处理

```python
def train_with_error_handling():
    client = TrainingClient()
    try:
        # 连接
        if not client.connect():
            return False

        # 创建任务
        task_id = client.create_task({
            "model_type": "detect",
            "epochs": 50
        })
        if not task_id:
            return False

        # 启动训练
        client.start_training(task_id)

        # 监控（带超时）
        timeout = 3600
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = client.get_task_status(task_id)
            if status["status"] == "completed":
                return True
            elif status["status"] == "failed":
                return False
            time.sleep(5)

        return False  # 超时

    except Exception as e:
        print(f"异常：{e}")
        return False
    finally:
        client.disconnect()
```

---

## 📈 响应码

| 响应码 | 含义 | 处理建议 |
|--------|------|----------|
| 100 | 成功 | 继续处理 |
| 200 | 部分成功 | 检查 message |
| 400 | 请求错误 | 检查参数 |
| 404 | 未找到 | 检查 task_id |
| 500 | 服务器错误 | 联系管理员 |

---

## ❓ 常见问题

### Q1: 连接失败怎么办？
**A:** 检查服务器是否启动，确认地址和端口正确

### Q2: 任务创建失败？
**A:** 检查参数格式，确保 dataset 路径存在

### Q3: 训练进度一直为 0？
**A:** 确认任务已启动（调用 start_training）

### Q4: 如何停止训练？
**A:** 调用 `stop_training(task_id)` 或删除任务

### Q5: 长轮询和普通查询的区别？
**A:** 长轮询会等待数据更新，减少无效请求

---

## 📚 附录

### 请求结构

```json
{
    "command": "create_task",
    "request_id": "1234567890_1",
    "timestamp": 1234567890.123,
    "params": {
        "model_type": "detect",
        "epochs": 50
    }
}
```

### 响应结构

```json
{
    "code": 100,
    "message": "success",
    "data": {
        "task_id": "abc123",
        "status": "training"
    }
}
```

---

**最后更新**: 2026-03-23
