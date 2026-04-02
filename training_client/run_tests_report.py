#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运行单元测试并生成报告
"""
import unittest
import sys
import os
import json
from datetime import datetime
from html import escape


class HTMLTestResult(unittest.TextTestResult):
    """HTML 格式的测试结果"""

    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.test_details = []

    def startTest(self, test):
        super().startTest(test)
        self.current_test = test
        self.start_time = datetime.now()

    def addSuccess(self, test):
        super().addSuccess(test)
        self.test_details.append({
            'name': str(test),
            'status': 'PASS',
            'duration': (datetime.now() - self.start_time).total_seconds(),
            'error': None
        })

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.test_details.append({
            'name': str(test),
            'status': 'FAIL',
            'duration': (datetime.now() - self.start_time).total_seconds(),
            'error': self._exc_info_to_string(err, test)
        })

    def addError(self, test, err):
        super().addError(test, err)
        self.test_details.append({
            'name': str(test),
            'status': 'ERROR',
            'duration': (datetime.now() - self.start_time).total_seconds(),
            'error': self._exc_info_to_string(err, test)
        })

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.test_details.append({
            'name': str(test),
            'status': 'SKIP',
            'duration': (datetime.now() - self.start_time).total_seconds(),
            'error': reason
        })


class HTMLTestRunner(unittest.TextTestRunner):
    """HTML 测试报告运行器"""

    def __init__(self, stream=sys.stderr, descriptions=2, verbosity=1, output_dir='test_report'):
        super().__init__(stream, descriptions, verbosity)
        self.output_dir = output_dir

    def _makeResult(self):
        return HTMLTestResult(self.stream, self.descriptions, self.verbosity)

    def run(self, test):
        result = super().run(test)
        self._generate_report(result)
        return result

    def _generate_report(self, result):
        """生成 HTML 报告"""
        os.makedirs(self.output_dir, exist_ok=True)

        # 准备报告数据
        total = result.testsRun
        passed = total - len(result.failures) - len(result.errors) - len(result.skipped)
        failed = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped)
        duration = sum(d.get('duration', 0) for d in getattr(result, 'test_details', []))

        # 生成 HTML
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>单元测试报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #333; margin-bottom: 20px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .card h3 {{ color: #666; font-size: 14px; margin-bottom: 10px; }}
        .card .value {{ font-size: 32px; font-weight: bold; }}
        .card.pass .value {{ color: #52c41a; }}
        .card.fail .value {{ color: #ff4d4f; }}
        .card.error .value {{ color: #fa8c16; }}
        .card.total .value {{ color: #1890ff; }}
        .info {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .info p {{ margin: 5px 0; color: #666; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #fafafa; font-weight: 600; color: #333; }}
        tr:hover {{ background: #f9f9f9; }}
        .status {{ padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 500; }}
        .status.PASS {{ background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }}
        .status.FAIL {{ background: #fff2f0; color: #ff4d4f; border: 1px solid #ffccc7; }}
        .status.ERROR {{ background: #fff7e6; color: #fa8c16; border: 1px solid #ffd591; }}
        .status.SKIP {{ background: #f0f5ff; color: #1890ff; border: 1px solid #adc6ff; }}
        .error-detail {{ background: #fff2f0; padding: 10px; border-radius: 4px; margin-top: 8px; font-family: monospace; font-size: 12px; white-space: pre-wrap; color: #5c0011; display: none; }}
        .toggle-btn {{ cursor: pointer; color: #1890ff; text-decoration: underline; font-size: 12px; }}
        .duration {{ color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 单元测试报告</h1>

        <div class="summary">
            <div class="card total"><h3>总计</h3><div class="value">{total}</div></div>
            <div class="card pass"><h3>通过</h3><div class="value">{passed}</div></div>
            <div class="card fail"><h3>失败</h3><div class="value">{failed}</div></div>
            <div class="card error"><h3>错误</h3><div class="value">{errors}</div></div>
            <div class="card" style="pass"><h3>跳过</h3><div class="value">{skipped}</div></div>
        </div>

        <div class="info">
            <p><strong>生成时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>执行时长:</strong> {duration:.2f} 秒</p>
            <p><strong>通过率:</strong> {(passed/total*100) if total > 0 else 0:.1f}%</p>
        </div>

        <h2 style="margin-bottom: 15px; color: #333;">测试详情</h2>
        <table>
            <thead>
                <tr>
                    <th>测试名称</th>
                    <th>状态</th>
                    <th>耗时</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
'''

        # 添加测试详情
        for detail in getattr(result, 'test_details', []):
            test_name = escape(detail['name'])
            status = detail['status']
            duration = f"{detail['duration']:.3f}s"
            error_html = ""
            if detail['error']:
                error_escaped = escape(detail['error'])
                error_html = f'''<div class="error-detail" id="error-{id(detail)}">{error_escaped}</div>'''

            html += f'''
                <tr>
                    <td>{test_name}</td>
                    <td><span class="status {status}">{status}</span>{error_html}</td>
                    <td class="duration">{duration}</td>
                    <td>
                        {f'<span class="toggle-btn" onclick="toggleError(\'error-{id(detail)}\')">查看详情</span>' if detail['error'] else '-'}
                    </td>
                </tr>
'''

        html += '''
            </tbody>
        </table>
    </div>

    <script>
        function toggleError(id) {
            const el = document.getElementById(id);
            el.style.display = el.style.display === 'none' || el.style.display === '' ? 'block' : 'none';
        }
    </script>
</body>
</html>
'''

        # 写入文件
        report_path = os.path.join(self.output_dir, 'test_report.html')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"\n[REPORT] Test report generated: {report_path}")

        # 同时生成 JSON 报告
        json_report = {
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'skipped': skipped,
                'duration': duration,
                'pass_rate': (passed/total*100) if total > 0 else 0
            },
            'generated_at': datetime.now().isoformat(),
            'tests': getattr(result, 'test_details', [])
        }

        json_path = os.path.join(self.output_dir, 'test_report.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)

        print(f"[REPORT] JSON report generated: {json_path}")


def run_tests(output_dir='test_report'):
    """运行所有测试并生成报告"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # 发现测试
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=os.path.dirname(os.path.abspath(__file__)),
        pattern='test_*.py'
    )

    # 运行测试并生成报告
    runner = HTMLTestRunner(verbosity=2, output_dir=output_dir)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='运行单元测试并生成报告')
    parser.add_argument(
        '--output', '-o',
        default='test_report',
        help='报告输出目录 (默认：test_report)'
    )

    args = parser.parse_args()

    success = run_tests(output_dir=args.output)
    sys.exit(0 if success else 1)
