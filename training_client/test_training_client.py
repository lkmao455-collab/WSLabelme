# test_training_client.py
"""
TrainingClient 模块的单元测试
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import socket
import json
import time
import struct
from datetime import datetime

from training_client import MessageProtocol, TrainingClient, InteractiveClient


class TestMessageProtocol(unittest.TestCase):
    """测试消息协议类"""

    def test_calculate_checksum_basic(self):
        """测试基本校验和计算"""
        data = b"hello"
        checksum = MessageProtocol.calculate_checksum(data)
        self.assertIsInstance(checksum, int)
        self.assertGreaterEqual(checksum, 0)
        self.assertLessEqual(checksum, 0xFFFFFFFF)

    def test_calculate_checksum_empty(self):
        """测试空数据的校验和"""
        checksum = MessageProtocol.calculate_checksum(b"")
        self.assertEqual(checksum, 0)

    def test_calculate_checksum_consistency(self):
        """测试相同数据产生相同校验和"""
        data = b"test data"
        checksum1 = MessageProtocol.calculate_checksum(data)
        checksum2 = MessageProtocol.calculate_checksum(data)
        self.assertEqual(checksum1, checksum2)

    def test_pack_structure(self):
        """测试打包后的消息结构"""
        message = "test"
        packed = MessageProtocol.pack(message)

        # 包头 4 字节 + 长度 4 字节 + 校验和 4 字节 + 数据
        expected_length = 4 + 4 + 4 + len(message.encode('utf-8'))
        self.assertEqual(len(packed), expected_length)

    def test_pack_header(self):
        """测试包头是否正确"""
        packed = MessageProtocol.pack("test")
        header = struct.unpack('>I', packed[:4])[0]
        self.assertEqual(header, 0x55AA55AA)

    def test_pack_length(self):
        """测试消息长度是否正确"""
        message = "hello world"
        packed = MessageProtocol.pack(message)
        length = struct.unpack('>I', packed[4:8])[0]
        self.assertEqual(length, len(message.encode('utf-8')))

    def test_pack_and_unpack_roundtrip(self):
        """测试打包和解包的往返"""
        message = "test message 123"
        packed = MessageProtocol.pack(message)

        # 模拟接收端解包
        header = struct.unpack('>I', packed[:4])[0]
        self.assertEqual(header, 0x55AA55AA)

        length = struct.unpack('>I', packed[4:8])[0]
        checksum = struct.unpack('>I', packed[8:12])[0]
        data = packed[12:12+length]

        # 验证校验和
        calculated_checksum = MessageProtocol.calculate_checksum(data)
        self.assertEqual(checksum, calculated_checksum)

        # 验证数据
        self.assertEqual(data.decode('utf-8'), message)

    def test_pack_unicode(self):
        """测试 Unicode 消息打包"""
        message = "你好世界"
        packed = MessageProtocol.pack(message)
        length = struct.unpack('>I', packed[4:8])[0]
        self.assertEqual(length, len(message.encode('utf-8')))


class TestMessageProtocolReceive(unittest.TestCase):
    """测试消息接收功能"""

    @patch('socket.socket')
    def test_receive_normal(self, mock_socket_class):
        """测试正常接收消息"""
        mock_conn = Mock()
        message = "test response"
        packed = MessageProtocol.pack(message)

        # 分块接收
        mock_conn.recv.side_effect = [
            packed[:4],   # 包头
            packed[4:8],  # 长度
            packed[8:12], # 校验和
            packed[12:],  # 数据
            b''           # 结束
        ]

        result = MessageProtocol.receive(mock_conn)
        self.assertEqual(result, message)

    @patch('socket.socket')
    def test_receive_timeout(self, mock_socket_class):
        """测试接收超时"""
        mock_conn = Mock()
        mock_conn.recv.side_effect = socket.timeout()

        result = MessageProtocol.receive(mock_conn, timeout=0.1)
        self.assertIsNone(result)

    @patch('socket.socket')
    def test_receive_invalid_header(self, mock_socket_class):
        """测试无效包头"""
        mock_conn = Mock()
        # 发送错误的包头
        bad_header = struct.pack('>I', 0xDEADBEEF)
        mock_conn.recv.return_value = bad_header

        result = MessageProtocol.receive(mock_conn)
        self.assertIsNone(result)


class TestTrainingClient(unittest.TestCase):
    """测试训练客户端"""

    def setUp(self):
        """设置测试环境"""
        self.client = TrainingClient("127.0.0.1", 8888)

    def tearDown(self):
        """清理测试环境"""
        self.client.disconnect()

    def test_init(self):
        """测试初始化"""
        client = TrainingClient("192.168.1.1", 9999)
        self.assertEqual(client.host, "192.168.1.1")
        self.assertEqual(client.port, 9999)
        self.assertFalse(client.connected)
        self.assertIsNone(client.socket)
        self.assertEqual(client.request_counter, 0)

    @patch('socket.socket')
    def test_connect_success(self, mock_socket_class):
        """测试连接成功"""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        client = TrainingClient()
        result = client.connect()

        self.assertTrue(result)
        self.assertTrue(client.connected)
        self.assertIsNotNone(client.socket)
        mock_socket.connect.assert_called_once_with(("127.0.0.1", 8888))

    @patch('socket.socket')
    def test_connect_failure(self, mock_socket_class):
        """测试连接失败"""
        mock_socket_class.side_effect = socket.error("Connection refused")

        client = TrainingClient()
        result = client.connect()

        self.assertFalse(result)
        self.assertFalse(client.connected)

    def test_disconnect(self):
        """测试断开连接"""
        self.client.socket = Mock()
        self.client.connected = True

        self.client.disconnect()

        self.assertFalse(self.client.connected)
        self.assertIsNone(self.client.socket)

    @patch.object(TrainingClient, 'connect')
    def test_send_request_success(self, mock_connect):
        """测试发送请求成功"""
        self.client.connected = True
        self.client.socket = Mock()

        response_message = json.dumps({"code": 100, "data": {"result": "ok"}})
        packed_response = MessageProtocol.pack(response_message)

        # 模拟接收响应
        chunks = [
            packed_response[:4],
            packed_response[4:8],
            packed_response[8:12],
            packed_response[12:],
            b''
        ]
        self.client.socket.recv.side_effect = chunks

        result = self.client.send_request("test_command", {"param": "value"})

        self.assertIsNotNone(result)
        self.assertEqual(result.get("code"), 100)
        self.assertEqual(self.client.request_counter, 1)

    def test_send_request_not_connected(self):
        """测试未连接时发送请求"""
        self.client.connected = False

        result = self.client.send_request("test")

        self.assertIsNone(result)

    @patch.object(TrainingClient, 'connect')
    def test_ping_success(self, mock_connect):
        """测试 ping 成功"""
        self.client.connected = True
        self.client.socket = Mock()

        response = json.dumps({"code": 100, "server_time": "2024-01-01 12:00:00"})
        packed = MessageProtocol.pack(response)

        self.client.socket.recv.side_effect = [
            packed[:4], packed[4:8], packed[8:12], packed[12:], b''
        ]

        result = self.client.ping()
        self.assertTrue(result)

    @patch.object(TrainingClient, 'connect')
    def test_ping_failure(self, mock_connect):
        """测试 ping 失败"""
        self.client.connected = True
        self.client.socket = Mock()

        response = json.dumps({"code": 500, "message": "error"})
        packed = MessageProtocol.pack(response)

        self.client.socket.recv.side_effect = [
            packed[:4], packed[4:8], packed[8:12], packed[12:], b''
        ]

        result = self.client.ping()
        self.assertFalse(result)

    @patch.object(TrainingClient, 'connect')
    def test_create_task_success(self, mock_connect):
        """测试创建任务成功"""
        self.client.connected = True
        self.client.socket = Mock()

        response = json.dumps({
            "code": 100,
            "data": {"task_id": "task_123"}
        })
        packed = MessageProtocol.pack(response)

        self.client.socket.recv.side_effect = [
            packed[:4], packed[4:8], packed[8:12], packed[12:], b''
        ]

        result = self.client.create_task({"epochs": 50})
        self.assertEqual(result, "task_123")

    @patch.object(TrainingClient, 'connect')
    def test_create_task_failure(self, mock_connect):
        """测试创建任务失败"""
        self.client.connected = True
        self.client.socket = Mock()

        response = json.dumps({
            "code": 500,
            "message": "Invalid parameters"
        })
        packed = MessageProtocol.pack(response)

        self.client.socket.recv.side_effect = [
            packed[:4], packed[4:8], packed[8:12], packed[12:], b''
        ]

        result = self.client.create_task({"epochs": 50})
        self.assertIsNone(result)

    @patch.object(TrainingClient, 'connect')
    def test_start_training_success(self, mock_connect):
        """测试开始训练成功"""
        self.client.connected = True
        self.client.socket = Mock()

        response = json.dumps({"code": 100})
        packed = MessageProtocol.pack(response)

        self.client.socket.recv.side_effect = [
            packed[:4], packed[4:8], packed[8:12], packed[12:], b''
        ]

        result = self.client.start_training("task_123")
        self.assertTrue(result)

    @patch.object(TrainingClient, 'connect')
    def test_stop_training_success(self, mock_connect):
        """测试停止训练成功"""
        self.client.connected = True
        self.client.socket = Mock()

        response = json.dumps({"code": 100})
        packed = MessageProtocol.pack(response)

        self.client.socket.recv.side_effect = [
            packed[:4], packed[4:8], packed[8:12], packed[12:], b''
        ]

        result = self.client.stop_training("task_123")
        self.assertTrue(result)

    @patch.object(TrainingClient, 'connect')
    def test_get_task_status_success(self, mock_connect):
        """测试获取任务状态成功"""
        self.client.connected = True
        self.client.socket = Mock()

        status_data = {
            "status": "training",
            "progress": 0.5,
            "task_id": "task_123"
        }
        response = json.dumps({"code": 100, "data": status_data})
        packed = MessageProtocol.pack(response)

        self.client.socket.recv.side_effect = [
            packed[:4], packed[4:8], packed[8:12], packed[12:], b''
        ]

        result = self.client.get_task_status("task_123")
        self.assertIsNotNone(result)
        self.assertEqual(result.get("status"), "training")
        self.assertEqual(result.get("progress"), 0.5)

    @patch.object(TrainingClient, 'connect')
    def test_get_progress_success(self, mock_connect):
        """测试获取训练进度成功"""
        self.client.connected = True
        self.client.socket = Mock()

        progress_data = {
            "progress": {
                "type": "detect",
                "epoch": 10,
                "total_epochs": 50,
                "loss": 0.05,
                "accuracy": 0.95
            }
        }
        response = json.dumps({"code": 100, "data": progress_data})
        packed = MessageProtocol.pack(response)

        self.client.socket.recv.side_effect = [
            packed[:4], packed[4:8], packed[8:12], packed[12:], b''
        ]

        result = self.client.get_progress("task_123")
        self.assertIsNotNone(result)
        self.assertEqual(result.get("progress", {}).get("epoch"), 10)

    @patch.object(TrainingClient, 'connect')
    def test_list_tasks_success(self, mock_connect):
        """测试列出任务成功"""
        self.client.connected = True
        self.client.socket = Mock()

        tasks_data = {
            "tasks": [
                {"task_id": "task_1", "status": "training", "progress": 0.3},
                {"task_id": "task_2", "status": "completed", "progress": 1.0}
            ]
        }
        response = json.dumps({"code": 100, "data": tasks_data})
        packed = MessageProtocol.pack(response)

        self.client.socket.recv.side_effect = [
            packed[:4], packed[4:8], packed[8:12], packed[12:], b''
        ]

        result = self.client.list_tasks()
        self.assertIsNotNone(result)
        self.assertEqual(len(result.get("tasks", [])), 2)

    @patch.object(TrainingClient, 'connect')
    def test_delete_task_success(self, mock_connect):
        """测试删除任务成功"""
        self.client.connected = True
        self.client.socket = Mock()

        response = json.dumps({"code": 100})
        packed = MessageProtocol.pack(response)

        self.client.socket.recv.side_effect = [
            packed[:4], packed[4:8], packed[8:12], packed[12:], b''
        ]

        result = self.client.delete_task("task_123")
        self.assertTrue(result)


class TestInteractiveClient(unittest.TestCase):
    """测试交互式客户端"""

    def setUp(self):
        """设置测试环境"""
        self.interactive_client = InteractiveClient()

    def test_init(self):
        """测试初始化"""
        self.assertIsInstance(self.interactive_client.client, TrainingClient)
        self.assertIsNone(self.interactive_client.current_task)

    @patch.object(TrainingClient, 'connect', return_value=False)
    def test_run_connect_failure(self, mock_connect):
        """测试运行时连接失败"""
        with patch('builtins.input', return_value='8'):  # 选择退出
            self.interactive_client.run()

        self.assertFalse(self.interactive_client.client.connected)


class TestMessageProtocolEdgeCases(unittest.TestCase):
    """测试边界情况"""

    def test_pack_empty_message(self):
        """测试打包空消息"""
        packed = MessageProtocol.pack("")
        length = struct.unpack('>I', packed[4:8])[0]
        self.assertEqual(length, 0)

    def test_pack_large_message(self):
        """测试打包大消息"""
        message = "x" * 10000
        packed = MessageProtocol.pack(message)
        length = struct.unpack('>I', packed[4:8])[0]
        self.assertEqual(length, 10000)

    def test_checksum_overflow(self):
        """测试校验和溢出处理"""
        # 大量数据测试校验和不会溢出
        data = b"x" * 100000
        checksum = MessageProtocol.calculate_checksum(data)
        self.assertLessEqual(checksum, 0xFFFFFFFF)


if __name__ == '__main__':
    unittest.main()
