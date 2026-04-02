# flake8: noqa

import logging


__appname__ = "Heyfocus Label"  # 原值: "labelme"

# Semantic Versioning 2.0.0: https://semver.org/
# 1. MAJOR version when you make incompatible API changes;
# 2. MINOR version when you add functionality in a backwards-compatible manner;
# 3. PATCH version when you make backwards-compatible bug fixes.
# e.g., 1.0.0a0, 1.0.0a1, 1.0.0b0, 1.0.0rc0, 1.0.0, 1.0.0.post0
__version__ = "0.1.3"

# 发布时间：格式为 YYYY-MM-DD HH:MM:SS
# 此时间会在代码提交时自动更新（通过 Git hook）
__publish_time__ = "2026-04-02 12:28:05"

from labelme.label_file import LabelFile
from labelme import testing
from labelme import utils
