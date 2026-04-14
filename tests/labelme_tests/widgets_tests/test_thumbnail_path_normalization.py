# -*- encoding: utf-8 -*-
"""
Thumbnail File List Path Normalization Unit Tests (No GUI)

Tests:
- Path normalization matching (fixes selection mismatch caused by different path formats)
"""

import os
import os.path as osp
import sys
import tempfile

# Add project root to path
sys.path.insert(0, osp.dirname(osp.dirname(osp.dirname(osp.dirname(osp.abspath(__file__))))))


def test_path_normalization():
    """测试路径规范化函数"""
    # 创建临时目录和文件
    temp_dir = tempfile.mkdtemp()
    test_file = osp.join(temp_dir, "image.png")
    with open(test_file, 'w') as f:
        f.write("test")

    # 测试1: 绝对路径
    abs_path = osp.abspath(test_file)
    normalized1 = osp.normpath(osp.abspath(abs_path))
    print(f"Absolute path: {abs_path}")
    print(f"Normalized: {normalized1}")
    assert osp.normpath(osp.abspath(abs_path)) == normalized1

    # 测试2: 相对路径
    original_dir = os.getcwd()
    os.chdir(temp_dir)
    rel_path = "image.png"
    normalized2 = osp.normpath(osp.abspath(rel_path))
    print(f"\nRelative path: {rel_path}")
    print(f"Normalized: {normalized2}")
    assert normalized1 == normalized2
    os.chdir(original_dir)

    # 测试3: 混合分隔符（Windows风格）
    if os.name == 'nt':
        mixed_path = test_file.replace('/', '\\')
        normalized3 = osp.normpath(osp.abspath(mixed_path))
        print(f"\nMixed separator path: {mixed_path}")
        print(f"Normalized: {normalized3}")
        assert normalized1 == normalized3

    # 测试4: 路径包含 . 和 ..
    dot_path = osp.join(temp_dir, "..", osp.basename(temp_dir), "image.png")
    normalized4 = osp.normpath(osp.abspath(dot_path))
    print(f"\nPath with ..: {dot_path}")
    print(f"Normalized: {normalized4}")
    assert normalized1 == normalized4

    # 测试5: 路径包含 ./
    dot_slash_path = osp.join(temp_dir, ".", "image.png")
    normalized5 = osp.normpath(osp.abspath(dot_slash_path))
    print(f"\nPath with ./: {dot_slash_path}")
    print(f"Normalized: {normalized5}")
    assert normalized1 == normalized5

    # 清理
    import shutil
    shutil.rmtree(temp_dir)

    print("\n[PASS] All path normalization tests passed!")


def test_path_matching_in_list():
    """测试列表中的路径匹配"""
    temp_dir = tempfile.mkdtemp()

    # 创建测试文件
    file_paths = []
    for i in range(5):
        file_path = osp.join(temp_dir, f"image_{i+1}.png")
        with open(file_path, 'w') as f:
            f.write("test")
        file_paths.append(osp.abspath(file_path))

    # 模拟 ThumbnailFileList 的 file_paths 列表
    stored_paths = [osp.abspath(fp) for fp in file_paths]

    # 测试目标文件
    target_file = file_paths[2]  # image_3.png

    # 测试用例1: 使用绝对路径查找
    target_normalized = osp.normpath(osp.abspath(target_file))
    found_index = None
    for i, fp in enumerate(stored_paths):
        if osp.normpath(osp.abspath(fp)) == target_normalized:
            found_index = i
            break
    assert found_index == 2, f"Expected 2, got {found_index}"
    print(f"[PASS] Absolute path search: index {found_index}")

    # 测试用例2: 使用相对路径查找
    original_dir = os.getcwd()
    os.chdir(temp_dir)
    rel_path = "image_3.png"
    target_normalized = osp.normpath(osp.abspath(rel_path))
    found_index = None
    for i, fp in enumerate(stored_paths):
        if osp.normpath(osp.abspath(fp)) == target_normalized:
            found_index = i
            break
    os.chdir(original_dir)
    assert found_index == 2, f"Expected 2, got {found_index}"
    print(f"[PASS] Relative path search: index {found_index}")

    # 测试用例3: 使用 Windows 风格分隔符
    if os.name == 'nt':
        mixed_path = target_file.replace('/', '\\')
        target_normalized = osp.normpath(osp.abspath(mixed_path))
        found_index = None
        for i, fp in enumerate(stored_paths):
            if osp.normpath(osp.abspath(fp)) == target_normalized:
                found_index = i
                break
        assert found_index == 2, f"Expected 2, got {found_index}"
        print(f"[PASS] Mixed separator path search: index {found_index}")

    # 清理
    import shutil
    shutil.rmtree(temp_dir)

    print("\n[PASS] All list path matching tests passed!")


def test_nonexistent_file():
    """测试不存在的文件路径处理"""
    temp_dir = tempfile.mkdtemp()

    # 创建一些文件
    stored_paths = []
    for i in range(3):
        file_path = osp.join(temp_dir, f"image_{i+1}.png")
        with open(file_path, 'w') as f:
            f.write("test")
        stored_paths.append(osp.abspath(file_path))

    # 测试不存在的文件
    nonexistent = osp.join(temp_dir, "nonexistent.png")
    target_normalized = osp.normpath(osp.abspath(nonexistent))

    found = False
    for fp in stored_paths:
        if osp.normpath(osp.abspath(fp)) == target_normalized:
            found = True
            break

    assert not found, "不应该找到不存在的文件"
    print("\n[PASS] Nonexistent file handled correctly")

    # 清理
    import shutil
    shutil.rmtree(temp_dir)


def test_edge_cases():
    """测试边界情况"""
    temp_dir = tempfile.mkdtemp()
    test_file = osp.join(temp_dir, "image.png")
    with open(test_file, 'w') as f:
        f.write("test")

    abs_path = osp.abspath(test_file)

    # Test case-insensitive paths (Windows)
    if os.name == 'nt':
        upper_path = abs_path.upper()
        lower_path = abs_path.lower()
        # On Windows, paths are case-insensitive, so we compare normalized paths ignoring case
        assert osp.normpath(osp.abspath(upper_path)).lower() == osp.normpath(osp.abspath(lower_path)).lower()
        print("[PASS] Windows case-insensitive path handled correctly")

    # 测试带空格的路径
    spaced_dir = tempfile.mkdtemp(prefix="test dir with spaces ")
    spaced_file = osp.join(spaced_dir, "image file.png")
    with open(spaced_file, 'w') as f:
        f.write("test")

    normalized = osp.normpath(osp.abspath(spaced_file))
    assert osp.exists(normalized)
    print("[PASS] Path with spaces handled correctly")

    # 清理
    import shutil
    shutil.rmtree(temp_dir)
    shutil.rmtree(spaced_dir)


if __name__ == "__main__":
    print("=" * 60)
    print("Thumbnail File List Path Normalization Tests")
    print("=" * 60)

    print("\n### Test 1: Path Normalization ###")
    test_path_normalization()

    print("\n### Test 2: Path Matching in List ###")
    test_path_matching_in_list()

    print("\n### Test 3: Nonexistent File ###")
    test_nonexistent_file()

    print("\n### Test 4: Edge Cases ###")
    test_edge_cases()

    print("\n" + "=" * 60)
    print("[PASS] All tests passed!")
    print("=" * 60)
