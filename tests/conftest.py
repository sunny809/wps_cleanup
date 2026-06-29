"""共享 Fixtures：临时目录、模拟的扫描结果、模拟的 CleanResult。"""

import os
import sys
import tempfile
from typing import List

import pytest

# 确保能找到 wps_cleanup 包
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wps_cleanup.cleaner import CleanResult
from wps_cleanup.config import SafetyLevel, Category


@pytest.fixture
def tmp_workspace():
    """创建临时工作目录，内含模拟的 WPS 缓存文件结构。"""
    with tempfile.TemporaryDirectory() as root:
        # 插件缓存目录
        addons = os.path.join(root, "addons", "pool", "win-i386")
        os.makedirs(addons)
        _touch(os.path.join(addons, "plugin_a.dll"), size=1024)
        _touch(os.path.join(addons, "plugin_b.dat"), size=2048)
        _touch(os.path.join(addons, "config.json"), size=512)

        # 备份目录
        backup = os.path.join(root, "office6", "backup")
        os.makedirs(backup)
        _touch(os.path.join(backup, "doc1.wpsbak"), size=50_000)
        _touch(os.path.join(backup, "doc2.wpsbak"), size=120_000)

        # 云缓存
        cloud = os.path.join(root, "filecache")
        os.makedirs(cloud)
        _touch(os.path.join(cloud, "cache_001.dat"), size=8_000)

        # 空目录
        empty_dir = os.path.join(root, "empty")
        os.makedirs(empty_dir)

        yield root


def _touch(path: str, size: int = 0):
    """创建指定大小的文件。"""
    with open(path, "wb") as f:
        if size > 0:
            f.write(b"x" * size)


@pytest.fixture
def sample_scan_results(tmp_workspace) -> List[dict]:
    """模拟 scan_all() 返回的结果。"""
    from wps_cleanup.config import CleanupItem, SafetyLevel, Category

    items = [
        CleanupItem(
            name="插件缓存",
            path_template=os.path.join(tmp_workspace, "addons", "pool", "win-i386"),
            description="测试",
            category=Category.PLUGIN_CACHE,
            safety=SafetyLevel.SAFE,
        ),
        CleanupItem(
            name="本地备份",
            path_template=os.path.join(tmp_workspace, "office6", "backup"),
            description="测试",
            category=Category.LOCAL_BACKUP,
            safety=SafetyLevel.CAUTION,
        ),
        CleanupItem(
            name="云缓存",
            path_template=os.path.join(tmp_workspace, "filecache"),
            description="测试",
            category=Category.CLOUD_CACHE,
            safety=SafetyLevel.CAUTION,
        ),
        CleanupItem(
            name="不存在的目录",
            path_template=os.path.join(tmp_workspace, "not_exists"),
            description="测试",
            category=Category.FEATURE_CACHE,
            safety=SafetyLevel.SAFE,
        ),
    ]

    from wps_cleanup.scanner import scan_item
    results = []
    for item in items:
        r = scan_item(item)
        if r is not None:
            # 手动修正 resolved_path（scan_item 会用 resolve_path 重写路径）
            r["item"] = item
            r["resolved_path"] = item.path_template
            r["exists"] = os.path.exists(item.path_template)
            # 重新扫描大小
            if r["exists"]:
                total = 0
                count = 0
                for dirpath, _, filenames in os.walk(item.path_template):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        try:
                            total += os.path.getsize(fp)
                            count += 1
                        except OSError:
                            pass
                r["total_size"] = total
                r["file_count"] = count
            results.append(r)
    return results


@pytest.fixture
def sample_clean_results() -> List[CleanResult]:
    """模拟清理后返回的结果。"""
    return [
        CleanResult(
            name="插件缓存",
            resolved_path=r"C:\mock\addons\pool\win-i386",
            success=True,
            deleted_files=3,
            deleted_size=3584,
            deleted_file_paths=[
                r"C:\mock\addons\pool\win-i386\plugin_a.dll",
                r"C:\mock\addons\pool\win-i386\plugin_b.dat",
                r"C:\mock\addons\pool\win-i386\config.json",
            ],
            category="插件与组件缓存",
            safety="✅ 可安全删除",
        ),
        CleanResult(
            name="本地备份",
            resolved_path=r"C:\mock\office6\backup",
            success=True,
            deleted_files=2,
            deleted_size=170_000,
            deleted_file_paths=[
                r"C:\mock\office6\backup\doc1.wpsbak",
                r"C:\mock\office6\backup\doc2.wpsbak",
            ],
            category="本地备份与自动恢复",
            safety="⚠️ 可清理，但需谨慎",
        ),
        CleanResult(
            name="失败项",
            resolved_path=r"C:\mock\locked",
            success=False,
            deleted_files=0,
            deleted_size=0,
            error="文件被占用",
            category="插件与组件缓存",
            safety="✅ 可安全删除",
        ),
    ]
