#!/usr/bin/env python3
"""
测试训练服务器检测逻辑
用于诊断服务器已启动但检测不到的问题
"""

import subprocess
import socket
import sys
import os


def check_process_running():
    """检查 training_server.exe 进程是否存在"""
    print("=" * 50)
    print("1. 检测 training_server.exe 进程")
    print("=" * 50)

    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq training_server.exe"],
            capture_output=True,
            text=True,
            timeout=5
        )
        print(f"命令执行结果:")
        print(f"  返回码: {result.returncode}")
        print(f"  stdout:\n{result.stdout}")
        print(f"  stderr: {result.stderr}")

        is_running = "training_server.exe" in result.stdout
        print(f"\n检测结果: {'✓ 进程存在' if is_running else '✗ 进程不存在'}")
        return is_running
    except Exception as e:
        print(f"✗ 检测失败: {e}")
        return False


def check_port_open(host, port):
    """检查端口是否开放"""
    print("\n" + "=" * 50)
    print(f"2. 检测端口 {host}:{port}")
    print("=" * 50)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print(f"✓ 端口 {host}:{port} 已开放")
            return True
        else:
            print(f"✗ 端口 {host}:{port} 未开放 (错误码: {result})")
            print(f"  错误说明: {get_socket_error(result)}")
            return False
    except Exception as e:
        print(f"✗ 检测失败: {e}")
        return False


def get_socket_error(code):
    """获取 socket 错误码说明"""
    errors = {
        10061: "连接被拒绝 (服务器未运行或端口未监听)",
        10060: "连接超时 (服务器无响应)",
        10051: "网络不可达",
        111: "连接被拒绝",
        110: "连接超时",
    }
    return errors.get(code, "未知错误")


def find_training_server_exe():
    """查找 training_server.exe 的路径"""
    print("\n" + "=" * 50)
    print("3. 查找 training_server.exe 文件")
    print("=" * 50)

    exe_name = "training_server.exe"

    # 1. 如果是打包环境，在 exe 所在目录查找
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        exe_path = os.path.join(exe_dir, exe_name)
        print(f"打包环境，检查: {exe_path}")
        if os.path.exists(exe_path):
            print(f"✓ 找到: {exe_path}")
            return exe_path
        print(f"✗ 不存在")
    else:
        print("非打包环境 (Python 解释器运行)")

    # 2. 在项目根目录查找（labelme 包的上两级）
    current_file = os.path.abspath(__file__)
    # 从测试脚本位置推断项目根目录
    # tests/ -> 项目根目录
    project_root = os.path.dirname(os.path.dirname(current_file))
    exe_path = os.path.join(project_root, exe_name)
    print(f"检查项目根目录: {exe_path}")
    if os.path.exists(exe_path):
        print(f"✓ 找到: {exe_path}")
        return exe_path
    print(f"✗ 不存在")

    # 3. 检查 training_client/training_server.exe
    exe_path = os.path.join(project_root, "training_client", exe_name)
    print(f"检查 training_client: {exe_path}")
    if os.path.exists(exe_path):
        print(f"✓ 找到: {exe_path}")
        return exe_path
    print(f"✗ 不存在")

    print("\n✗ 未找到 training_server.exe")
    return None


def main():
    print("训练服务器检测测试脚本")
    print("=" * 50)
    print()

    # 默认配置
    host = "127.0.0.1"
    port = 8765

    # 检测进程
    process_running = check_process_running()

    # 检测端口
    port_open = check_port_open(host, port)

    # 查找 exe
    exe_path = find_training_server_exe()

    # 汇总结果
    print("\n" + "=" * 50)
    print("检测结果汇总")
    print("=" * 50)
    print(f"进程检测: {'✓ 通过' if process_running else '✗ 未通过'}")
    print(f"端口检测: {'✓ 通过' if port_open else '✗ 未通过'}")
    print(f"文件查找: {'✓ 找到' if exe_path else '✗ 未找到'}")

    print("\n分析:")
    if process_running and port_open:
        print("✓ 服务器已正常启动并监听端口")
    elif process_running and not port_open:
        print("! 警告: 进程存在但端口未开放")
        print("  可能原因:")
        print("  - 服务器正在启动中，尚未完成初始化")
        print("  - 服务器监听了不同的端口")
        print("  - 服务器异常退出")
    elif not process_running and port_open:
        print("! 警告: 端口开放但进程不存在")
        print("  可能原因:")
        print("  - 其他程序占用了该端口")
        print("  - 检测逻辑有问题")
    else:
        print("✗ 服务器未运行")

    return 0 if (process_running and port_open) else 1


if __name__ == "__main__":
    sys.exit(main())
