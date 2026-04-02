#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运行单元测试脚本
"""
import unittest
import sys
import os


def run_tests(verbosity=2):
    """
    运行所有测试用例

    Args:
        verbosity: 输出详细程度 (0=安静，1=简单，2=详细)

    Returns:
        bool: 是否全部通过
    """
    # 确保当前目录在路径中
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # 发现测试
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=os.path.dirname(os.path.abspath(__file__)),
        pattern='test_*.py'
    )

    # 运行测试
    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        failfast=False,
        buffer=False
    )
    result = runner.run(suite)

    # 打印摘要
    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    print(f"运行测试数：{result.testsRun}")
    print(f"成功：{result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败：{len(result.failures)}")
    print(f"错误：{len(result.errors)}")
    print(f"跳过：{len(result.skipped)}")

    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\n出错的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}")

    return result.wasSuccessful()


def run_specific_test(test_name, verbosity=2):
    """
    运行指定的测试类或测试方法

    Args:
        test_name: 测试类名或测试方法名 (如：TestMessageProtocol 或 test_pack_structure)
        verbosity: 输出详细程度

    Returns:
        bool: 是否通过
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # 导入测试模块
    import test_training_client

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 查找测试
    if hasattr(test_training_client, test_name):
        test_class = getattr(test_training_client, test_name)
        if isinstance(test_class, type):
            # 是测试类
            suite.addTests(loader.loadTestsFromTestCase(test_class))
        else:
            # 是测试方法，需要找到所属的类
            for name in dir(test_training_client):
                obj = getattr(test_training_client, name)
                if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
                    if hasattr(obj, test_name):
                        suite.addTest(obj(test_name))
                        break
    else:
        print(f"未找到测试：{test_name}")
        return False

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='运行单元测试')
    parser.add_argument(
        '--test', '-t',
        type=str,
        help='运行指定的测试类或方法'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='安静模式，减少输出'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出模式'
    )

    args = parser.parse_args()

    # 设置详细程度
    if args.quiet:
        verbosity = 0
    elif args.verbose:
        verbosity = 2
    else:
        verbosity = 1

    # 运行测试
    if args.test:
        success = run_specific_test(args.test, verbosity)
    else:
        success = run_tests(verbosity)

    # 退出码
    sys.exit(0 if success else 1)
