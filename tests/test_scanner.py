"""测试 scanner 模块：扫描逻辑、大小计算、汇总。"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wps_cleanup.scanner import (
    scan_item,
    get_total_cleanable,
    get_category_summary,
)
from wps_cleanup.config import (
    CleanupItem,
    Category,
    SafetyLevel,
)


class TestScanItem:
    """单项目扫描测试。"""

    def test_scan_existing_directory(self, tmp_workspace):
        """扫描存在的目录应返回正确文件数和大小。"""
        item = CleanupItem(
            name="测试目录",
            path_template=os.path.join(tmp_workspace, "addons", "pool", "win-i386"),
            description="",
            category=Category.PLUGIN_CACHE,
            safety=SafetyLevel.SAFE,
        )
        result = scan_item(item)
        # 手动修正路径（scan_item 内部会调用 resolve_path 重写路径）
        result["resolved_path"] = item.path_template

        assert result["exists"] is True
        assert result["file_count"] == 3
        assert result["total_size"] == 1024 + 2048 + 512  # 3584

    def test_scan_nonexistent_path(self):
        """扫描不存在的路径应返回 exists=False。"""
        item = CleanupItem(
            name="不存在",
            path_template=r"C:\Path\That\Does\Not\Exist\12345",
            description="",
            category=Category.PLUGIN_CACHE,
            safety=SafetyLevel.SAFE,
        )
        result = scan_item(item)
        assert result["exists"] is False
        assert result["file_count"] == 0
        assert result["total_size"] == 0

    def test_scan_empty_directory(self, tmp_workspace):
        """扫描空目录应返回 0 文件。"""
        item = CleanupItem(
            name="空目录",
            path_template=os.path.join(tmp_workspace, "empty"),
            description="",
            category=Category.FEATURE_CACHE,
            safety=SafetyLevel.SAFE,
        )
        result = scan_item(item)
        result["resolved_path"] = item.path_template

        assert result["exists"] is True
        assert result["file_count"] == 0
        assert result["total_size"] == 0

    def test_scan_single_file(self, tmp_workspace):
        """扫描单个文件应正确识别。"""
        file_path = os.path.join(tmp_workspace, "single_file.tmp")
        with open(file_path, "wb") as f:
            f.write(b"hello")

        item = CleanupItem(
            name="单个文件",
            path_template=file_path,
            description="",
            category=Category.FEATURE_CACHE,
            safety=SafetyLevel.SAFE,
        )
        result = scan_item(item)
        result["resolved_path"] = item.path_template

        assert result["exists"] is True
        assert result["file_count"] == 1
        assert result["total_size"] == 5


class TestSummaryFunctions:
    """汇总函数测试。"""

    def test_get_total_cleanable(self, sample_scan_results):
        """应正确汇总存在的项。"""
        total_files, total_size = get_total_cleanable(sample_scan_results)
        assert total_files == 3 + 2 + 1  # 3项存在
        assert total_size == 3584 + 170_000 + 8_000

    def test_get_total_cleanable_empty(self):
        """空列表应返回零。"""
        total_files, total_size = get_total_cleanable([])
        assert total_files == 0
        assert total_size == 0

    def test_get_category_summary(self, sample_scan_results):
        """应按类别正确汇总。"""
        summary = get_category_summary(sample_scan_results)

        assert "插件与组件缓存" in summary
        files, size = summary["插件与组件缓存"]
        assert files == 3
        assert size == 3584

        assert "本地备份与自动恢复" in summary
        files, size = summary["本地备份与自动恢复"]
        assert files == 2
        assert size == 170_000

    def test_no_category_for_nonexistent(self):
        """不存在的项不应出现在汇总中。"""
        from wps_cleanup.config import CleanupItem, Category, SafetyLevel

        item = CleanupItem(
            name="不存在",
            path_template=r"C:\nonexistent",
            description="",
            category=Category.PLUGIN_CACHE,
            safety=SafetyLevel.SAFE,
        )
        result = scan_item(item)
        summary = get_category_summary([result])
        # 不存在的项没有文件，不应该出现在汇总中或应该为 0
        for cat_name, (files, size) in summary.items():
            assert files == 0
            assert size == 0
