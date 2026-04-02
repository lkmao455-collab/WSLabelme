# SSH 模型部署模块

一个完整的 SSH 模型文件传输和部署解决方案，集成到 Labelme 中作为 Dock 面板。

## 功能特性

### 基础功能
- ✅ **SSH 连接配置** - IP、端口、用户名、密码配置
- ✅ **设备类型选择** - 支持 ERV/GSV/BRV/AFRV/CRV/GSV2/AFSV/GHV 等设备类型
- ✅ **自动凭据匹配** - 根据设备类型自动填充用户名和密码
- ✅ **文件选择和传输** - 支持选择本地文件上传到远程设备
- ✅ **进度显示** - 实时显示传输进度和速度
- ✅ **多线程处理** - 所有耗时操作在独立线程中执行

### 高级功能
- ✅ **断点续传** - 支持上传中断后继续传输
- ✅ **多设备管理** - 添加、编辑、删除、保存设备列表
- ✅ **日志面板** - 实时显示操作日志，支持导出
- ✅ **一键部署** - 自动完成连接、上传、执行命令的完整流程
- ✅ **MD5 完整性校验** - 传输完成后自动校验文件完整性
- ✅ **自动重传机制** - 校验失败时自动重传（最多3次）

## 安装依赖

```bash
pip install paramiko
```

## 使用方法

### 1. 在 Labelme 中集成

在 `labelme/app.py` 中添加以下代码：

```python
from labelme.widgets import DeployDockWidget

# 在 __init__ 方法中创建 Dock
self.deploy_dock = DeployDockWidget(self)
self.addDockWidget(Qt.RightDockWidgetArea, self.deploy_dock)

# 添加到视图菜单
view_menu.addAction(self.deploy_dock.toggleViewAction())
```

### 2. 独立运行测试

```bash
python test_ssh_deploy.py
```

### 3. 作为模块导入

```python
from labelme.ssh_deploy import DeployDockWidget
from labelme.ssh_deploy.ssh_client import SSHClient, SSHConfig
from labelme.ssh_deploy.device_manager import DeviceManager
```

## 模块结构

```
ssh_deploy/
├── __init__.py          # 模块入口，导出 DeployDockWidget
├── ssh_client.py        # SSH 连接和 SFTP 传输
├── device_manager.py    # 设备管理
├── log_handler.py       # 日志处理
├── deploy_worker.py     # 多线程工作类
├── deploy_dock.py       # Dock 面板 UI
└── README.md            # 说明文档
```

## 设备类型和凭据

| 设备类型 | 用户名 | 密码 |
|---------|--------|------|
| ERV, GSV2 | root | root |
| GSV, CRV, GHV | root | SenvisionTech |
| AFRV, AFSV | root | 1 |
| BRV | root | root |

## 界面说明

### 部署标签页
- **连接配置**: 输入 IP、端口，选择设备类型
- **连接测试**: 测试 SSH 连接是否成功
- **文件选择**: 选择要上传的模型文件
- **目标路径**: 默认 `/mmcblk1p2`
- **操作按钮**: 上传文件 / 一键部署 / 暂停
- **部署命令**: 可选的部署后执行命令

### 设备管理标签页
- 显示已保存的设备列表
- 支持添加、编辑、删除设备
- 选择设备自动填充连接信息
- 设备列表保存到本地 JSON 文件

### 日志标签页
- 实时显示操作日志
- 不同级别日志用不同颜色显示
- 支持清除和导出日志
- 自动滚动到最新日志

## 断点续传说明

上传文件时，模块会自动：
1. 检查远程文件是否已存在
2. 获取远程文件大小
3. 从断点位置继续上传
4. 如果文件已完整存在，提示无需上传

## MD5 完整性校验

### 功能说明

文件传输完成后，系统会自动进行 MD5 完整性校验，确保文件传输的完整性和可靠性：

1. **本地 MD5 计算** - 传输前计算本地文件的 MD5 值
2. **文件传输** - 上传文件到远程设备
3. **远程 MD5 计算** - 通过 SSH 执行 `md5sum` 命令获取远程文件 MD5
4. **MD5 对比** - 对比本地和远程 MD5 值
5. **自动重传** - 校验失败时自动重传（最多3次）

### 使用方式

MD5 校验默认启用，可以通过参数控制：

```python
from ssh_deploy import FileTransferWorker, DeployWorker

# 文件传输 - 启用 MD5 校验（默认）
worker = FileTransferWorker(
    config=ssh_config,
    local_path="/path/to/local/file",
    remote_path="/path/to/remote/file",
    enable_md5_verify=True,  # 启用 MD5 校验
    max_retries=3,           # 最大重试次数
)

# 一键部署 - 启用 MD5 校验（默认）
deploy_worker = DeployWorker(
    device=device_info,
    local_path="/path/to/local/file",
    remote_path="/mmcblk1p2",
    enable_md5_verify=True,  # 启用 MD5 校验
    max_retries=3,           # 最大重试次数
)
```

### UI 状态显示

传输过程中会显示以下状态：
- "正在计算本地 MD5..."
- "开始上传文件 (filename)..."
- "正在校验 MD5..."
- "校验失败，正在重试（1/3）..."
- "校验成功"
- "传输失败（已重试3次）"

### 日志记录

每次传输都会记录详细的 MD5 信息：
```
[INFO] 本地文件 MD5: a1b2c3d4e5f6... (filename)
[INFO] 正在校验文件完整性: filename
[INFO] 本地 MD5: a1b2c3d4e5f6...
[INFO] 远程 MD5: a1b2c3d4e5f6...
[SUCCESS] 文件传输成功并通过 MD5 校验: filename
```

### 异常处理

MD5 校验模块处理了以下异常情况：
- 远程 `md5sum` 命令执行失败
- SSH 连接中断
- 远程文件不存在
- 权限不足
- MD5 格式无效

### 技术实现

- **本地 MD5**: Python `hashlib` 模块，分块读取避免内存占用
- **远程 MD5**: 通过 `paramiko.exec_command` 执行 `md5sum` 命令
- **重传策略**: 封装为 retry 函数，带计数器和状态回调
- **文件清理**: 每次重传前删除远端不完整文件

## 一键部署流程

1. **连接设备** - 建立 SSH 连接
2. **上传文件** - 传输模型文件到目标路径（支持 MD5 校验）
3. **执行命令** - 执行用户指定的部署命令
4. **完成部署** - 显示部署结果

## 异常处理

模块处理了以下异常情况：
- SSH 连接失败
- 认证失败
- 文件不存在
- 网络中断
- 权限问题
- 命令执行失败

## 配置文件

设备列表保存在用户目录下的 `.ssh_deploy_devices.json` 文件中。

## 注意事项

1. 确保目标设备已开启 SSH 服务
2. 确保网络连接正常
3. 确保有足够的磁盘空间
4. 大文件传输可能需要较长时间

## 开发说明

### 添加新的设备类型

在 `device_manager.py` 中修改 `DEVICE_CREDENTIALS` 字典：

```python
DEVICE_CREDENTIALS = {
    "NEW_DEVICE": ("username", "password"),
    # ...
}
```

### 自定义部署命令

在部署标签页的"部署后命令"文本框中输入，每行一个命令：

```bash
chmod +x /mmcblk1p2/deploy.sh
/mmcblk1p2/deploy.sh
systemctl restart myservice
```

## 许可证

与 Labelme 项目使用相同的许可证。