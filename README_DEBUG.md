# Labelme 调试配置说明

## 运行 Labelme

### 方式1：使用批处理脚本（推荐）
直接双击运行 `run_labelme.bat`，脚本会自动：
- 查找 conda 环境 `labelme`
- 使用该环境中的 Python 运行 Labelme
- 支持传递命令行参数

### 方式2：使用 PowerShell 脚本
在 PowerShell 中运行：
```powershell
.\run_labelme.ps1
```

或者传递参数：
```powershell
.\run_labelme.ps1 --help
```

### 方式3：使用 VS Code F5 调试

**首次设置（必须）**：
1. 运行 `setup_debug.bat` 自动配置 VS Code
   - 脚本会自动查找 conda 环境并更新配置
   - 完成后即可直接使用 F5 调试

**或者手动设置**：
1. 在 VS Code 中按 `Ctrl+Shift+P`
2. 输入 "Python: Select Interpreter"
3. 选择 conda 环境 `labelme` 中的 Python
   - 路径通常是：`D:\ProgramData\anaconda3\envs\labelme\python.exe`

**开始调试**：
- 按 `F5` 开始调试
- 或点击调试面板中的 "Python: Labelme" 配置

## 环境说明

所有脚本使用与 `check_and_move.ps1` 相同的 conda 环境检测逻辑：
- 环境名称：`labelme`
- 自动查找常见的 conda 安装路径
- 支持使用 `conda run` 作为备选方案
- PowerShell 脚本提供更可靠的检测机制

## 故障排除

### 问题：ModuleNotFoundError: No module named 'yaml'
**原因**：VS Code 使用了系统 Python 而不是 conda 环境

**解决方法**：
1. 运行 `setup_debug.bat` 重新配置
2. 或手动选择 Python 解释器：
   - 按 `Ctrl+Shift+P`
   - 输入 "Python: Select Interpreter"
   - 选择 `D:\ProgramData\anaconda3\envs\labelme\python.exe`

### 问题：找不到 conda 环境
1. 确认 conda 已安装并在 PATH 中
2. 确认环境名称是 `labelme`
3. 运行 `find_conda_python.ps1` 查看详细诊断信息
4. 如果 conda 命令可用，脚本会自动使用 `conda run` 作为备选方案
